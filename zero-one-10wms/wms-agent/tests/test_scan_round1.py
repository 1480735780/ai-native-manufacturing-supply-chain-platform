"""第一轮改造的回归测试：幂等、越权、worker 恢复、PG 故障拒绝、分页重试、告警状态机。

全部使用 MemoryScanStore / httpx.MockTransport，不依赖 PG、Nacos 或真实网络。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.scan import router as scan_router
from app.scan.repository import (
    MemoryScanStore,
    ScanStoreConflictError,
    ScanStoreUnavailableError,
    build_scan_store,
)
from app.scan.service import compute_scan_key, config_hash, DEFAULT_CONFIG
from app.scan.sources.expiry import ENDPOINT as EXP_ENDPOINT
from app.scan.sources.expiry import fetch_expiry
from app.scan.worker import recover_stale_runs
from app.security import (
    AuthError, Principal, can_view_scan, can_trigger_scan, is_scan_admin,
    check_warehouse_scope, require_principal,
)
from app.tools.gateway_client import GatewayClient

TOKEN = "header.payload.signature"
EXP_PATH = EXP_ENDPOINT


def _row(id: str, resDate: float = 3.0) -> dict[str, Any]:
    return {
        "id": id, "resDate": resDate, "guoqibili": "0.01", "bzhiQi": "360",
        "cusCode": "C1", "goodsId": "G1", "goodsProData": "2026-01-01",
        "dqr": "2026-11-26", "shpMingCheng": "小蓝管", "kuWeiBianMa": "KW-A-01",
    }


def _gateway(rows: list[dict[str, Any]]) -> GatewayClient:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == EXP_PATH
        return httpx.Response(200, json={"code": 10000, "data": {"rows": rows, "total": len(rows)}})

    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))


def _user(name: str = "tester", authorities: tuple[str, ...] = ("insp_read",)) -> Principal:
    return Principal(user_id="u-1", user_name=name, authorities=authorities)


def _service(scope: tuple[str, ...] = ("W01",)) -> Principal:
    return Principal(
        user_id="svc", user_name="agent-inspector", authorities=("insp_read",),
        warehouse_scope=scope, token_use="agent_service",
    )


def _run(**overrides: Any) -> dict[str, Any]:
    run = {
        "scanId": "scan-1", "trigger": "manual", "actorType": "user", "actorId": "tester",
        "status": "queued", "partial": False, "sourceStatus": [], "configHash": "h",
        "ruleVersion": "v1", "scanTypes": ["expiry"], "requestId": None,
        "scheduleSlot": None, "scanKey": "scan-1",
        "queuedAt": datetime.now(timezone.utc).isoformat(), "startedAt": None,
        "counts": {}, "errorSummary": None, "warehouse": "W01",
    }
    run.update(overrides)
    return run


# ---------- 幂等键与原子 upsert ----------

def test_compute_scan_key_manual_vs_service() -> None:
    chash = config_hash(DEFAULT_CONFIG)
    manual = compute_scan_key(
        principal=_user(), request_id="req-1", schedule_slot=None,
        config_hash_value=chash, scan_types=["expiry"],
    )
    assert manual  # 手动按 requestId
    service = compute_scan_key(
        principal=_service(), request_id=None, schedule_slot="slot-1",
        config_hash_value=chash, scan_types=["expiry"],
    )
    assert service and service != manual  # 定时按 scheduleSlot+configHash+scanTypes
    # 无幂等键时为空
    assert compute_scan_key(
        principal=_user(), request_id=None, schedule_slot=None,
        config_hash_value=chash, scan_types=["expiry"],
    ) == ""


@pytest.mark.asyncio
async def test_idempotent_insert_conflict_and_lookup() -> None:
    store = MemoryScanStore()
    run = _run(scanId="scan-a", requestId="req-1", scanKey="key-1")
    await store.insert_run(run)
    # 同 requestId + actorId 再入队 → 冲突（原子 upsert 的唯一约束）
    with pytest.raises(ScanStoreConflictError):
        await store.insert_run(_run(scanId="scan-b", requestId="req-1", scanKey="key-2"))
    found = await store.get_run_by_scan_key("key-1")
    assert found is not None and found["scanId"] == "scan-a"


@pytest.mark.asyncio
async def test_upsert_alert_returns_created_and_first_severity() -> None:
    store = MemoryScanStore()
    alert = {"fingerprint": "fp-1", "severity": "P1", "state": "open", "lastSeenAt": "2026-01-01"}
    created = await store.upsert_alert(alert)
    assert created.outcome == "created" and created.previous_severity is None
    # 复发（级别不升）：不新建，first_severity 锁定为首次级别
    again = await store.upsert_alert({**alert, "lastSeenAt": "2026-01-02"})
    assert again.alert_id == created.alert_id and again.outcome == "updated"
    assert again.previous_severity == "P1"
    assert (await store.list_alerts())[0]["occurrenceCount"] == 2
    assert (await store.list_alerts())[0]["firstSeverity"] == "P1"
    # 新建事件与告警同事务落库；复发（非升级）不写事件
    assert [e["eventType"] for e in store.events] == ["created"]


@pytest.mark.asyncio
async def test_alert_state_transition_and_conflict() -> None:
    store = MemoryScanStore()
    await store.upsert_alert({"fingerprint": "fp-1", "severity": "P1", "state": "open"})
    result = await store.transition_alert(1, "acknowledged", reason="收到", actor_id="tester")
    assert result is not None and result["state"] == "acknowledged"
    transitions = [e for e in store.events if e["eventType"] == "transition"]
    assert len(transitions) == 1 and transitions[0]["fromState"] == "open"
    # 进入终态 resolved 后，再转换 → None（路由映射 409）
    result_terminal = await store.transition_alert(1, "resolved", reason="已处理", actor_id="tester")
    assert result_terminal is not None and result_terminal["state"] == "resolved"
    result2 = await store.transition_alert(1, "acknowledged", actor_id="tester")
    assert result2 is None


# ---------- 角色 / 查询越权 ----------

def test_scan_permissions() -> None:
    assert can_trigger_scan(_user(authorities=("ckjl",))) is True  # 业务角色可发起
    assert can_trigger_scan(_user()) is False  # 人类用户持只读角色 insp_read 不能发起
    assert can_trigger_scan(_service()) is True  # 服务账号持 insp_read 只能 trigger
    service_no_auth = Principal(
        user_id="x", user_name="x", authorities=(), token_use="agent_service"
    )
    assert can_trigger_scan(service_no_auth) is False
    # 用户只能看自己的扫描
    assert can_view_scan(_user(), _run(actorId="tester")) is True
    assert can_view_scan(_user(), _run(actorId="other")) is False
    # 服务扫描仅管理员可见
    svc_run = _run(actorType="service", actorId="agent-inspector")
    assert can_view_scan(_user(), svc_run) is False
    assert can_view_scan(_user(authorities=("ROLE_ADMIN",)), svc_run) is True
    assert is_scan_admin(_user(authorities=("gly",))) is True  # gly 是管理员权限码


def test_warehouse_scope_guard() -> None:
    assert check_warehouse_scope(_service(("W01",)), "W01", ["W01", "W02"]) == "W01"
    with pytest.raises(AuthError):
        check_warehouse_scope(_service(("W01",)), "W02", ["W01", "W02"])


def test_get_scan_forbidden_for_other_user() -> None:
    client = TestClient(create_app())
    store = MemoryScanStore()
    store.runs["scan-1"] = _run(actorId="someone-else")
    app = client.app
    app.state.scan_store = store
    app.dependency_overrides[require_principal] = lambda: _user("tester")
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    resp = client.get("/agent/scans/scan-1", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 9997  # CODE_FORBIDDEN


# ---------- worker 恢复 / PG 故障拒绝 ----------

@pytest.mark.asyncio
async def test_recover_stale_running_runs() -> None:
    """租约过期：attempt 未耗尽 → 重新入队并清租约；用尽 → failed(stale)；未过期不动。"""
    store = MemoryScanStore()
    old = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
    store.runs["scan-old"] = _run(
        scanId="scan-old", status="running", queuedAt=old, startedAt=old,
        leasedAt=old, leaseOwner="w-old", attempt=1,
    )
    store.runs["scan-exhausted"] = _run(
        scanId="scan-exhausted", status="running", queuedAt=old, startedAt=old,
        leasedAt=old, leaseOwner="w-dead", attempt=3,
    )
    store.runs["scan-fresh"] = _run(
        scanId="scan-fresh", status="running",
        queuedAt=datetime.now(timezone.utc).isoformat(),
        leasedAt=datetime.now(timezone.utc).isoformat(), leaseOwner="w-live", attempt=1,
    )
    settings = Settings(WMS_AGENT_SCAN_LEASE_SECONDS=300)  # 字段带 validation_alias，须按环境变量名传
    recovered = await recover_stale_runs(store, settings)
    assert recovered == 2
    assert store.runs["scan-old"]["status"] == "queued"
    assert store.runs["scan-old"]["errorSummary"] == "stale_requeued"
    assert store.runs["scan-old"]["leaseOwner"] is None
    assert store.runs["scan-old"]["attempt"] == 1  # 领取时才 +1，不在恢复时改
    assert store.runs["scan-exhausted"]["status"] == "failed"
    assert store.runs["scan-exhausted"]["errorSummary"] == "stale"
    assert store.runs["scan-fresh"]["status"] == "running"


def test_build_scan_store_rejects_failure() -> None:
    with pytest.raises(ScanStoreUnavailableError):
        build_scan_store("postgres", "")  # PG 无 db_url → 故障拒绝，不降级内存
    with pytest.raises(ScanStoreUnavailableError):
        build_scan_store("redis", "x")  # 未知后端拒绝


# ---------- 分页完整性 ----------

@pytest.mark.asyncio
async def test_source_retries_5xx_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"error": "busy"})
        return httpx.Response(200, json={"code": 10000, "data": {"rows": [_row("S1")], "total": 1}})

    client = GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))
    result = await fetch_expiry(client, TOKEN)
    assert result.status == "ok" and calls["n"] == 2  # 重试 1 次成功


@pytest.mark.asyncio
async def test_source_4xx_no_retry_marks_partial() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": "bad"})

    client = GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))
    result = await fetch_expiry(client, TOKEN)
    assert calls["n"] == 1  # 4xx 不重试
    assert result.truncated is True and result.status == "error"
