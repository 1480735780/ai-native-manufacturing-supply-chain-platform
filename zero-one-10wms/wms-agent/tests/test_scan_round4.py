"""F-015 第四轮缺陷修复回归测试（评审结论：队列与权限闭环未通过）。

覆盖评审点：租约/attempt 持久化/fencing、周期恢复有界、payload_hash/trace_id、
服务 scanKey、告警事务（事件+通知同事务、去重键含事件与级别）、ignored 显式 suppressed、
真实接收人路由、view/trigger/handle 拆分、跨仓过滤、单仓强制、ignoredUntil 校验、
分页完整性、执行身份取自令牌、心跳、迁移回滚守卫。

Memory 后端的队列/告警契约与 PG 的对齐由 tests/test_scan_store_contract.py 保证。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import ScanConfigError, Settings, ensure_single_scan_warehouse
from app.main import create_app
from app.scan import router as scan_router
from app.scan import worker as worker_module
from app.scan.migrations import runner as migration_runner
from app.scan.repository import (
    MAX_ATTEMPTS, MemoryScanStore, ScanLeaseLostError, UPSERT_CREATED, UPSERT_ESCALATED,
    UPSERT_REPLAYED, UPSERT_SUPPRESSED, UPSERT_UPDATED,
)
from app.scan.schemas import ScanRequest  # noqa: F401  (确保请求模型可导入)
from app.scan.config import canonical_json
from app.scan.service import DEFAULT_CONFIG, compute_scan_key, config_hash, run_scan
from app.scan.sources.no_up import ENDPOINT as NOUP_PATH, fetch_no_up
from app.scan.worker import (
    ScanWorker, execute_queued_scan, recover_stale_runs, validate_service_principal,
)
from app.security import Principal, require_principal
from app.tools.gateway_client import GatewayClient

TOKEN = "header.payload.signature"
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def _user(name: str = "tester", authorities: tuple[str, ...] = ("ckjl",), **kw: Any) -> Principal:
    return Principal(user_id="u-1", user_name=name, authorities=authorities, **kw)


def _admin() -> Principal:
    return _user("admin", authorities=("gly",))


def _service(scope: tuple[str, ...] = ("W01",), name: str = "agent-inspector") -> Principal:
    return Principal(
        user_id="svc", user_name=name, authorities=("insp_read",),
        warehouse_scope=scope, token_use="agent_service",
    )


def _gateway(handler) -> GatewayClient:
    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))


def _ok(data: dict[str, Any]):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 10000, "data": data})

    return _gateway(handler)


def _no_up_row(row_id: str, age_hours: float, *, distinct: bool = False) -> dict[str, Any]:
    """未上架行；distinct=True 时换通知单号，使 objectId（notice|goods|tin）与其他行不同。"""
    return {
        "rowId": row_id, "noticeId": f"N-{row_id}" if distinct else "N1",
        "goods_id": "G1", "tin_id": "T1", "bin_id": "B1",
        "cus_code": "C1",
        # 相对真实当前时间计算滞留时长（规则用 ctx.now 判定）
        "create_date": (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat(),
    }


def _queued(scan_id: str, *, queued_at: str | None = None, **overrides: Any) -> dict[str, Any]:
    # 队列记录必须自带入队时冻结的配置快照（V007），worker 只按快照执行。
    run = {
        "scanId": scan_id, "trigger": "manual", "actorType": "user", "actorId": "tester",
        "status": "queued", "partial": False, "sourceStatus": [],
        "configHash": config_hash(DEFAULT_CONFIG),
        "configSnapshot": canonical_json(DEFAULT_CONFIG),
        "configVersion": DEFAULT_CONFIG["version"],
        "ruleVersion": "expiry=v0.2.0", "scanTypes": ["no_up"], "requestId": None,
        "scheduleSlot": None, "scanKey": scan_id,
        "queuedAt": queued_at or datetime.now(timezone.utc).isoformat(),
        "startedAt": None, "finishedAt": None, "attempt": 0, "counts": {},
        "errorSummary": None, "warehouse": "W01", "dryRun": False,
        "notificationMode": "dry_run", "payloadHash": "sha256:payload", "traceId": "trace-abc",
    }
    run.update(overrides)
    return run


def _build_app(principal: Principal, store: MemoryScanStore, gateway: GatewayClient) -> TestClient:
    app = create_app()
    app.state.scan_store = store
    app.dependency_overrides[require_principal] = lambda: principal
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    app.dependency_overrides[scan_router.get_client] = lambda: gateway
    return TestClient(app)


def _settings(**overrides: Any) -> Settings:
    """Settings 字段带 validation_alias，必须按环境变量名传入（按字段名传会被静默忽略）。"""
    base = {"scan_lease_seconds": 60, "scan_worker_poll_seconds": 0.05}
    base.update(overrides)
    return Settings(_env_file=None, **{f"WMS_AGENT_{k.upper()}": v for k, v in base.items()})


# ---------- 队列：租约 / attempt / fencing ----------

async def test_claim_writes_lease_and_increments_attempt_in_queue_order() -> None:
    store = MemoryScanStore()
    await store.insert_run(_queued("scan-later", queuedAt="2026-11-24T12:00:10+00:00"))
    await store.insert_run(_queued("scan-earlier", queuedAt="2026-11-24T12:00:05+00:00"))

    first = await store.claim_next_queued("worker-a")
    assert first is not None and first["scanId"] == "scan-earlier"  # 按 queued_at 先进先出
    assert first["status"] == "running"
    assert first["leaseOwner"] == "worker-a" and first["leasedAt"]
    assert first["attempt"] == 1  # 领取即 +1，落 attempt 列
    second = await store.claim_next_queued("worker-a")
    assert second is not None and second["scanId"] == "scan-later"
    assert await store.claim_next_queued("worker-a") is None

    # 两个 worker 都崩溃（租约停在 600s 前）→ 周期恢复重新入队 → 再次领取 attempt 继续 +1
    stale = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    store.runs["scan-earlier"]["leasedAt"] = stale
    store.runs["scan-later"]["leasedAt"] = stale
    assert await store.recover_stale(cutoff, 100) == 2
    again = await store.claim_next_queued("worker-b")
    assert again is not None and again["attempt"] == 2
    assert again["leaseOwner"] == "worker-b"


async def test_fenced_save_rejects_stale_owner_and_keeps_queue_fields() -> None:
    store = MemoryScanStore()
    queued_at = datetime.now(timezone.utc).isoformat()
    await store.insert_run(_queued("scan-1", queuedAt=queued_at))
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None

    # 租约被别人接手：旧 worker 的回写必须被拒绝
    with pytest.raises(ScanLeaseLostError):
        await store.save_run({**claimed, "status": "succeeded"}, lease_owner="worker-stale")

    done = {**claimed, "status": "succeeded", "counts": {"findings": 1}}
    await store.save_run(done, lease_owner="worker-a")
    saved = await store.get_run("scan-1")
    assert saved["status"] == "succeeded"
    assert saved["queuedAt"] == queued_at  # 入队时间不被执行回写覆盖
    assert saved["attempt"] == 1  # attempt 列保留
    assert saved["payloadHash"] == "sha256:payload" and saved["traceId"] == "trace-abc"
    assert saved["leaseOwner"] is None and saved["leasedAt"] is None  # 终态释放租约


async def test_execution_keeps_attempt_queue_fields_and_rule_version() -> None:
    """worker 消费一条领取记录：attempt/queuedAt/payloadHash/traceId 原样保留，ruleVersion 回写。"""
    store = MemoryScanStore()
    gateway = _ok({"pageIndex": 1, "pageSize": 100, "total": 0, "pages": 0, "rows": []})
    await store.insert_run(_queued("scan-1"))
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None
    run = await execute_queued_scan(
        claimed, store=store, settings=_settings(), client=gateway, token=TOKEN
    )
    assert run["status"] == "succeeded"
    assert run["attempt"] == 1
    assert run["traceId"] == "trace-abc" and run["payloadHash"] == "sha256:payload"
    assert run["ruleVersion"] == "no_up=v0.2.0"
    assert run["executorType"] == "service" and run["executorId"] == "tester"
    assert run["trigger"] == "manual" and run["actorType"] == "user"
    assert "attempt" not in run["counts"]  # attempt 不再寄存在 counts 里


async def test_recover_requeue_is_bounded_by_max_attempts() -> None:
    """残留 running 反复恢复也不会无限重排：attempt 达到上限即 failed(stale)。"""
    store = MemoryScanStore()
    settings = _settings(scan_lease_seconds=60)
    await store.insert_run(_queued("scan-1"))
    stale = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
    attempts: list[int] = []
    for _ in range(MAX_ATTEMPTS + 2):
        claimed = await store.claim_next_queued("worker")
        if claimed is None:
            break
        attempts.append(claimed["attempt"])
        # 模拟 worker 崩溃：租约时间停在 600s 前，由周期恢复接管
        store.runs["scan-1"]["leasedAt"] = stale
        assert await recover_stale_runs(store, settings) == 1
    final = await store.get_run("scan-1")
    assert attempts == [1, 2, 3]
    assert final["status"] == "failed" and final["errorSummary"] == "stale"
    assert await store.claim_next_queued("worker") is None


# ---------- 入队字段：payload_hash / trace_id / scanKey ----------

def test_post_assigns_payload_hash_and_trace_and_alerts_inherit_trace() -> None:
    store = MemoryScanStore()
    client = _build_app(_admin(), store, _ok({"rows": [], "total": 0}))

    resp = client.post("/agent/scan", json={"scanTypes": ["no_up"]}, headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status_code == 202
    scan_id = resp.json()["data"]["scanId"]
    queued = store.runs[scan_id]
    assert queued["payloadHash"].startswith("sha256:")
    assert queued["traceId"].startswith("trace-")
    assert queued["attempt"] == 0 and queued["ruleVersion"] == "no_up=v0.2.0"

    gateway = _ok({
        "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
        "rows": [_no_up_row("R1", age_hours=9)],
    })
    claimed = asyncio.run(store.claim_next_queued("worker-a"))
    assert claimed is not None
    run = asyncio.run(execute_queued_scan(
        claimed, store=store, settings=_settings(), client=gateway, token=TOKEN
    ))
    assert run["status"] == "succeeded" and run["traceId"] == queued["traceId"]
    alerts = asyncio.run(store.list_alerts())
    assert len(alerts) == 1 and alerts[0]["traceId"] == queued["traceId"]
    assert all(e["traceId"] == queued["traceId"] for e in store.events)


def test_service_scan_key_includes_warehouse_and_requires_slot() -> None:
    chash = "sha256:cfg"
    w01 = compute_scan_key(
        principal=_service(), request_id=None, schedule_slot="2026-11-24T09:00+08:00",
        config_hash_value=chash, scan_types=["expiry"], warehouse="W01",
    )
    w02 = compute_scan_key(
        principal=_service(), request_id=None, schedule_slot="2026-11-24T09:00+08:00",
        config_hash_value=chash, scan_types=["expiry"], warehouse="W02",
    )
    assert w01 and w01 != w02
    # 无槽位的服务扫描不去重：否则所有无槽位定时扫描会撞成同一条
    assert compute_scan_key(
        principal=_service(), request_id=None, schedule_slot=None,
        config_hash_value=chash, scan_types=["expiry"], warehouse="W01",
    ) == ""


def test_service_post_without_slot_creates_independent_scans() -> None:
    store = MemoryScanStore()
    client = _build_app(_service(), store, _ok({"rows": [], "total": 0}))
    ids = set()
    for _ in range(2):
        resp = client.post(
            "/agent/scan", json={"scanTypes": ["expiry"], "warehouse": "W01"},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert resp.status_code == 202
        assert resp.json()["message"] == "ok"  # 不是 idempotent hit
        ids.add(resp.json()["data"]["scanId"])
    assert len(ids) == 2


async def test_get_run_by_scan_key_prefers_active_then_latest() -> None:
    store = MemoryScanStore()
    await store.insert_run(_queued("old", scanKey="k", status="succeeded", startedAt="2026-11-24T10:00:00+00:00"))
    await store.insert_run(_queued("new", scanKey="k", status="succeeded", startedAt="2026-11-24T11:00:00+00:00"))
    found = await store.get_run_by_scan_key("k")
    assert found is not None and found["scanId"] == "new"  # 不再取最早的历史记录
    await store.insert_run(_queued("active", scanKey="k", status="queued"))
    found = await store.get_run_by_scan_key("k")
    assert found is not None and found["scanId"] == "active"


# ---------- 告警事务：事件 + 通知同事务，去重键含事件与级别，ignored 显式 suppressed ----------

async def test_upsert_lifecycle_outcomes_events_and_notification_keys() -> None:
    store = MemoryScanStore()
    note = {"recipients": ["tester"], "status": "dry_run", "payloadDigest": "fp", "scope": "trace-1"}
    base = {"fingerprint": "fp-1", "severity": "P2", "ruleId": "NOUP-OVERDUE", "traceId": "trace-1",
            "scanId": "scan-a", "warehouseId": "W01", "lastSeenAt": NOW.isoformat()}

    created = await store.upsert_alert(base, notification=note)
    assert created.outcome == UPSERT_CREATED and created.notification_saved is True
    same = await store.upsert_alert({**base, "scanId": "scan-b"}, notification=note)
    assert same.outcome == UPSERT_UPDATED and same.previous_severity == "P2"
    escalated = await store.upsert_alert(
        {**base, "severity": "P1", "scanId": "scan-c"}, notification={**note, "scope": "trace-3"}
    )
    assert escalated.outcome == UPSERT_ESCALATED and escalated.previous_severity == "P2"
    assert escalated.notification_saved is True

    keys = [n["dedupeKey"] for n in store.notifications]
    # 去重键含事件类型 + 级别：升级通知不再被 created 的键吞掉
    assert keys == ["1:created:P2:trace-1:tester", "1:escalated:P1:trace-3:tester"]
    assert [e["eventType"] for e in store.events] == ["created", "escalated"]
    escalated_event = store.events[1]
    assert escalated_event["fromSeverity"] == "P2" and escalated_event["toSeverity"] == "P1"

    # 租约失效后同一扫描重放：同一 (scanId, traceId, fingerprint) → replayed，
    # 不增加 occurrence、不写事件/通知（fencing 不只保护扫描记录，还要挡住告警副作用）
    replay = await store.upsert_alert(
        {**base, "severity": "P1", "scanId": "scan-c"}, notification={**note, "scope": "trace-3"}
    )
    assert replay.outcome == UPSERT_REPLAYED
    assert replay.notification_saved is False
    assert len(store.notifications) == 2  # 无第三条通知
    assert [e["eventType"] for e in store.events] == ["created", "escalated"]  # 无新事件


async def test_ignored_suppresses_recurrence_explicitly() -> None:
    store = MemoryScanStore()
    note = {"recipients": ["tester"], "status": "dry_run", "payloadDigest": "fp", "scope": "t"}
    alert = {"fingerprint": "fp-ignored", "severity": "P1", "traceId": "t", "warehouseId": "W01",
             "lastSeenAt": NOW.isoformat()}
    created = await store.upsert_alert(alert, notification=note)
    assert created.outcome == UPSERT_CREATED
    ignored_until = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    assert await store.transition_alert(created.alert_id, "ignored", reason="已知", ignored_until=ignored_until)

    suppressed = await store.upsert_alert({**alert, "severity": "P0"}, notification={**note, "scope": "t2"})
    assert suppressed.outcome == UPSERT_SUPPRESSED
    assert suppressed.alert_id == created.alert_id
    assert suppressed.notification_saved is False
    assert len(store.notifications) == 1 and len(store.events) == 2  # created + transition
    stored = await store.get_alert(created.alert_id)
    assert stored["state"] == "ignored" and stored["severity"] == "P1"  # 被抑制：未改级别
    assert stored["occurrenceCount"] == 1

    # 忽略到期后条件仍在 → 新建告警（新 id）
    store.alerts[created.alert_id]["ignoredUntil"] = (NOW - timedelta(seconds=1)).isoformat()
    reopened = await store.upsert_alert({**alert, "lastSeenAt": (NOW + timedelta(days=8)).isoformat()})
    assert reopened.outcome == UPSERT_CREATED and reopened.alert_id != created.alert_id


async def test_scan_counts_escalation_and_suppression_with_real_routing() -> None:
    """no_up 同一对象从 P2 升到 P1 → 升级事件+通知；忽略后再扫 → alertsSuppressed，不通知。"""
    store = MemoryScanStore()

    def scan(scan_id: str, age_hours: float, principal: Principal, recipients=None):
        gateway = _ok({
            "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
            "rows": [_no_up_row("R1", age_hours=age_hours)],
        })
        return run_scan(
            scan_id=scan_id, scan_types=["no_up"], principal=principal, token=TOKEN,
            client=gateway, store=store, allowed_warehouses=["W01"],
            notification_mode="dry_run", recipients=recipients,
        )

    first = await scan("s1", 3, _user())          # P2
    assert first["counts"]["alertsCreated"] == 1 and first["counts"]["notifications"] == 1
    assert store.notifications[0]["recipient"] == "tester"  # 手动扫描推给发起人，不再是占位值
    second = await scan("s2", 6, _user())         # P1：升级
    assert second["counts"]["alertsEscalated"] == 1
    assert second["counts"]["alertsUpdated"] == 1
    assert second["counts"]["notifications"] == 1
    assert len(store.notifications) == 2
    assert [e["eventType"] for e in store.events] == ["created", "escalated"]
    third = await scan("s3", 6, _user())          # 仍是 P1：只更新，不通知
    assert third["counts"]["alertsEscalated"] == 0 and third["counts"]["notifications"] == 0
    assert len(store.notifications) == 2

    ignored_until = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    await store.transition_alert(1, "ignored", reason="维护中", ignored_until=ignored_until)
    fourth = await scan("s4", 30, _user())        # 被抑制：不计升级、不通知
    assert fourth["counts"]["alertsSuppressed"] == 1
    assert fourth["counts"]["alertsEscalated"] == 0
    assert fourth["counts"]["alertsUpdated"] == 0
    assert fourth["counts"]["notifications"] == 0
    assert len(store.notifications) == 2


async def test_scheduled_scan_uses_configured_recipients_or_counts_unrouted() -> None:
    store = MemoryScanStore()

    def scan(scan_id: str, recipients, row_id: str = "R1"):
        gateway = _ok({"pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
                       "rows": [_no_up_row(row_id, age_hours=9, distinct=True)]})
        return run_scan(
            scan_id=scan_id, scan_types=["no_up"], principal=_service(), token=TOKEN,
            client=gateway, store=store, allowed_warehouses=["W01"],
            notification_mode="dry_run", recipients=recipients,
        )

    unrouted = await scan("s1", [])
    assert unrouted["counts"]["alertsCreated"] == 1
    assert unrouted["counts"]["notificationsUnrouted"] == 1
    assert unrouted["counts"]["notifications"] == 0 and store.notifications == []

    routed = await scan("s2", ["zhangsan", "lisi"], row_id="R2")
    assert routed["counts"]["notifications"] == 1
    assert {n["recipient"] for n in store.notifications} == {"zhangsan", "lisi"}
    assert all("scan-owner" not in str(n["recipient"]) for n in store.notifications)


# ---------- 权限：跨仓过滤 / 单仓强制 / ignoredUntil ----------

def test_cross_warehouse_alerts_are_hidden_and_untouchable() -> None:
    store = MemoryScanStore()
    w01 = asyncio.run(store.upsert_alert({"fingerprint": "w01", "severity": "P1", "warehouseId": "W01"}))
    w02 = asyncio.run(store.upsert_alert({"fingerprint": "w02", "severity": "P1", "warehouseId": "W02"}))
    scoped = _user("zhangsan", ("ckjl",), warehouse_scope=("W01",))
    client = _build_app(scoped, store, _ok({"rows": [], "total": 0}))

    listed = client.get("/agent/alerts", headers={"Authorization": f"Bearer {TOKEN}"}).json()
    assert [a["alertId"] for a in listed["data"]] == [w01.alert_id]
    forbidden = client.get(
        "/agent/alerts", params={"warehouseId": "W02"}, headers={"Authorization": f"Bearer {TOKEN}"}
    ).json()
    assert forbidden["code"] == 9997
    ack_other = client.post(f"/agent/alerts/{w02.alert_id}/ack", headers={"Authorization": f"Bearer {TOKEN}"})
    assert ack_other.status_code == 403
    ack_own = client.post(f"/agent/alerts/{w01.alert_id}/ack", headers={"Authorization": f"Bearer {TOKEN}"})
    assert ack_own.status_code == 200

    # 管理员（无仓库 claim）也只能看到本部署配置的仓库
    admin_client = _build_app(_admin(), store, _ok({"rows": [], "total": 0}))
    admin_listed = admin_client.get("/agent/alerts", headers={"Authorization": f"Bearer {TOKEN}"}).json()
    assert [a["alertId"] for a in admin_listed["data"]] == [w01.alert_id]


def test_single_scan_warehouse_is_enforced() -> None:
    assert ensure_single_scan_warehouse(["W01"]) == "W01"
    assert ensure_single_scan_warehouse(["W01", "W01"]) == "W01"
    with pytest.raises(ScanConfigError):
        ensure_single_scan_warehouse(["W01", "W02"])
    with pytest.raises(ScanConfigError):
        ensure_single_scan_warehouse([])
    # 环境变量逗号分隔也能解析（此前 WMS_AGENT_SCAN_WAREHOUSES=W01 会按 JSON 解析失败）
    import os

    os.environ["WMS_AGENT_SCAN_WAREHOUSES"] = "W01"
    os.environ["WMS_AGENT_ALERT_RECIPIENTS"] = "zhangsan, lisi"
    try:
        settings = Settings(_env_file=None)
        assert settings.scan_warehouses == ["W01"]
        assert settings.alert_recipients == ["zhangsan", "lisi"]
        assert ensure_single_scan_warehouse(settings.scan_warehouses) == "W01"
    finally:
        del os.environ["WMS_AGENT_SCAN_WAREHOUSES"]
        del os.environ["WMS_AGENT_ALERT_RECIPIENTS"]


def test_ignored_until_is_validated_identically_for_both_backends() -> None:
    store = MemoryScanStore()
    asyncio.run(store.upsert_alert({"fingerprint": "fp", "severity": "P1", "warehouseId": "W01"}))
    client = _build_app(_user(), store, _ok({"rows": [], "total": 0}))
    headers = {"Authorization": f"Bearer {TOKEN}"}

    for bad in ("not-a-date", "2026-12-01T00:00:00", "2020-01-01T00:00:00+08:00"):
        resp = client.post("/agent/alerts/1/ignore", json={"reason": "r", "ignoredUntil": bad}, headers=headers)
        assert resp.status_code == 422, bad
        assert resp.json()["code"] == 9995
    # 三次非法请求都不能把告警改成 ignored（内存后端不再“返回 200”）
    assert client.get("/agent/alerts", headers=headers).json()["data"][0]["state"] == "open"

    ok = client.post(
        "/agent/alerts/1/ignore",
        json={"reason": "r", "ignoredUntil": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        headers=headers,
    )
    assert ok.status_code == 200 and ok.json()["data"]["state"] == "ignored"
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    assert ok.json()["data"]["ignoredUntil"].startswith(tomorrow)


# ---------- 分页完整性 ----------

async def test_source_completeness_checks() -> None:
    def paged(payload: dict[str, Any]):
        return _ok(payload)

    # total/pages 都缺失却返回了行（第 2 页为空）：不能首页即“完成”，也无法证明取全
    def no_total(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("pageIndex"))
        rows = [_no_up_row("R1", 9)] if page == 1 else []
        return httpx.Response(200, json={"code": 10000, "data": {"rows": rows}})

    result = await fetch_no_up(_gateway(no_total), TOKEN)
    assert result.status == "partial" and result.error_summary == "total_missing"
    assert len(result.rows) == 1

    # 声明 201 条、3 页，但第 2 页整页重复第 1 页（翻页漂移）
    def drifting(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("pageIndex"))
        rows = [_no_up_row(f"R{i}", 9) for i in range(100)] if page == 1 else (
            [_no_up_row("R0", 9)] if page == 3 else [_no_up_row(f"R{i}", 9) for i in range(100)]
        )
        return httpx.Response(200, json={"code": 10000, "data": {
            "pageIndex": page, "pageSize": 100, "total": 201, "pages": 3, "rows": rows}})

    result = await fetch_no_up(_gateway(drifting), TOKEN)
    assert result.status == "partial" and result.error_summary == "page_drift"

    # total 与实际行数不一致
    result = await fetch_no_up(paged({"total": 5, "pages": 1, "rows": [_no_up_row("R1", 9)]}), TOKEN)
    assert result.status == "partial" and result.error_summary.startswith("row_count_mismatch")

    # 只有 pages 没有 total：按声明页数走完即完整
    result = await fetch_no_up(paged({"pages": 1, "rows": [_no_up_row("R1", 9)]}), TOKEN)
    assert result.status == "ok" and len(result.rows) == 1


# ---------- worker：执行身份取自令牌 / 心跳 ----------

async def test_executor_identity_comes_from_service_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.scan import worker as worker_module

    store = MemoryScanStore()
    await store.insert_run(_queued("scan-1", trigger="schedule", actorType="service", actorId="agent-inspector"))
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None
    monkeypatch.setattr(worker_module, "acquire_service_token", lambda settings, warehouse: _async("svc.jwt"))
    monkeypatch.setattr(worker_module, "load_public_key", lambda path: "test-key")
    monkeypatch.setattr(
        worker_module, "decode_service_principal",
        lambda token, public_key: Principal(
            user_id="2", user_name="agent-inspector", authorities=("insp_read",),
            warehouse_scope=("W01",), token_use="agent_service",
        ),
    )
    run = await execute_queued_scan(claimed, store=store, settings=_settings(), client=_ok({"rows": [], "total": 0}))
    assert run["status"] == "succeeded"
    assert run["executorId"] == "agent-inspector"  # 令牌里的真实账号，不是角色名 insp_read
    assert run["executorType"] == "service"
    assert run["actorId"] == "agent-inspector" and run["trigger"] == "schedule"


def test_service_token_claim_validation_covers_all_claims() -> None:
    """服务令牌必须同时满足 token_use/角色/账号/仓库四项，任一缺失 fail-closed。"""
    settings = _settings()
    good = _service(scope=("W01",), name="agent-inspector")
    assert validate_service_principal(good, settings, "W01") is None

    cases = [
        ("auth_failed:token_use", Principal(
            user_id="svc", user_name="agent-inspector", authorities=("insp_read",),
            warehouse_scope=("W01",), token_use="user",
        )),
        ("auth_failed:authority", Principal(
            user_id="svc", user_name="agent-inspector", authorities=("ckjl",),
            warehouse_scope=("W01",), token_use="agent_service",
        )),
        ("auth_failed:account", _service(name="someone-else")),
        ("auth_failed:warehouse_scope", _service(scope=())),  # scope 为空也必须拒绝
        ("auth_failed:warehouse_scope", _service(scope=("W02",))),
    ]
    for expected, principal in cases:
        assert validate_service_principal(principal, settings, "W01") == expected
    # 本次仓库不在 scope 内（即使 scope 非空）同样拒绝
    assert validate_service_principal(good, settings, "W09") == "auth_failed:warehouse_scope"


async def test_service_token_scope_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.scan import worker as worker_module

    store = MemoryScanStore()
    await store.insert_run(_queued("scan-1", trigger="schedule", actorType="service"))
    claimed = await store.claim_next_queued("worker-a")
    monkeypatch.setattr(worker_module, "acquire_service_token", lambda settings, warehouse: _async("svc.jwt"))
    monkeypatch.setattr(worker_module, "load_public_key", lambda path: "test-key")
    monkeypatch.setattr(
        worker_module, "decode_service_principal",
        lambda token, public_key: Principal(
            user_id="2", user_name="agent-inspector", authorities=("insp_read",),
            warehouse_scope=("W02",), token_use="agent_service",
        ),
    )
    run = await execute_queued_scan(claimed, store=store, settings=_settings(), client=_ok({"rows": [], "total": 0}))
    assert run["status"] == "failed" and run["errorSummary"] == "auth_failed:warehouse_scope"


async def _async(value: str):
    return value


async def test_heartbeat_renews_lease_then_cancels_execution_when_lease_lost() -> None:
    store = MemoryScanStore()
    await store.insert_run(_queued("scan-1"))
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None
    worker = ScanWorker(store=store, settings=_settings(scan_lease_seconds=3), client=_ok({"rows": [], "total": 0}))
    assert worker._recovery_interval() == 1.0

    execution = asyncio.create_task(asyncio.sleep(30))
    heartbeat = asyncio.create_task(worker._heartbeat("scan-1", "worker-a", execution))
    await asyncio.sleep(1.3)
    leased_at = store.runs["scan-1"]["leasedAt"]
    assert leased_at != claimed["leasedAt"]  # 续租推进了 leased_at
    assert not execution.done()

    store.runs["scan-1"]["leaseOwner"] = "worker-b"  # 租约被别人接手
    await asyncio.sleep(1.3)
    assert execution.cancelled()
    heartbeat.cancel()
    await asyncio.gather(heartbeat, return_exceptions=True)


# ---------- 迁移：回滚守卫 ----------

async def test_migration_rollback_requires_applied_and_latest(monkeypatch: pytest.MonkeyPatch) -> None:
    async def applied(dsn: str) -> set[int]:
        return {1, 2}

    monkeypatch.setattr(migration_runner, "applied_versions", applied)
    monkeypatch.setattr(migration_runner, "_rollback_one_sync", lambda *a, **k: pytest.fail("不应执行 down"))
    with pytest.raises(migration_runner.MigrationError, match="latest"):
        await migration_runner.rollback_migration("postgresql://x", 1)
    # “未知版本”必须动态取：新增迁移（V008/V009…）后写死的 9 会变成合法版本
    unknown_version = max(item.version for item in migration_runner.discover_migrations()) + 1000
    with pytest.raises(migration_runner.MigrationError, match="unknown migration"):
        await migration_runner.rollback_migration("postgresql://x", unknown_version)

    async def only_two(dsn: str) -> set[int]:
        return {2}

    monkeypatch.setattr(migration_runner, "applied_versions", only_two)
    with pytest.raises(migration_runner.MigrationError, match="not applied"):
        await migration_runner.rollback_migration("postgresql://x", 1)
    discovered = [m.version for m in migration_runner.discover_migrations()]
    assert discovered == sorted(discovered)  # 按版本升序
    assert {1, 2}.issubset(discovered)  # 已应用的版本都可被发现（新增迁移不破坏此契约）


def test_scan_request_model_still_forbids_unknown_types() -> None:
    with pytest.raises(ValueError):
        ScanRequest(scanTypes=["unknown_type"])


# ---------------------------------------------------------------------------
# service-token 获取：对网关/Nacos 间歇性故障做有限重试，对确定性拒绝不重试
# ---------------------------------------------------------------------------

def _svc_settings() -> Settings:
    return Settings(
        _env_file=None,
        **{
            "WMS_AGENT_SERVICE_API_KEY": "k",
            "WMS_AGENT_SERVICE_KEY_ID": "kid",
            "WMS_AGENT_SERVICE_TOKEN_URL": "http://svc.test/login/service-token",
        },
    )


class _FlakyTransport(httpx.AsyncBaseTransport):
    """按预设序列返回响应/抛异常，用于模拟 Nacos 抖动。"""

    def __init__(self, script: list[object]) -> None:
        self.script = script
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def _ok_token_response() -> httpx.Response:
    return httpx.Response(200, json={"code": 10000, "data": {"token": "svc.jwt"}})


def _flaky_client(transport: "_FlakyTransport") -> "type[httpx.AsyncClient]":
    """返回 AsyncClient 子类：强制使用 flaky transport，忽略调用方传入的 timeout 等。"""
    real_cls = httpx.AsyncClient

    class _Client(real_cls):  # type: ignore[misc, valid-type]
        def __init__(self, **kw: object) -> None:
            kw.pop("transport", None)
            super().__init__(transport=transport, **kw)  # type: ignore[arg-type]

    return _Client


def test_service_token_retries_on_transient_502(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "SERVICE_TOKEN_RETRY_BASE_SECONDS", 0)
    transport = _FlakyTransport([
        httpx.Response(502, text=""), httpx.Response(503, text=""), _ok_token_response(),
    ])
    monkeypatch.setattr(httpx, "AsyncClient", _flaky_client(transport))

    token = asyncio.run(worker_module.acquire_service_token(_svc_settings(), "W01"))

    assert token == "svc.jwt"
    assert transport.calls == 3


def test_service_token_retries_on_transport_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "SERVICE_TOKEN_RETRY_BASE_SECONDS", 0)
    transport = _FlakyTransport([
        httpx.ReadTimeout("nacos"), _ok_token_response(),
    ])
    monkeypatch.setattr(httpx, "AsyncClient", _flaky_client(transport))

    token = asyncio.run(worker_module.acquire_service_token(_svc_settings(), "W01"))

    assert token == "svc.jwt"
    assert transport.calls == 2


def test_service_token_does_not_retry_on_deterministic_403(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "SERVICE_TOKEN_RETRY_BASE_SECONDS", 0)
    transport = _FlakyTransport([httpx.Response(403, json={"code": 9997})])
    monkeypatch.setattr(httpx, "AsyncClient", _flaky_client(transport))

    with pytest.raises(worker_module.ServiceTokenError, match="http_403"):
        asyncio.run(worker_module.acquire_service_token(_svc_settings(), "W01"))

    assert transport.calls == 1


def test_service_token_gives_up_after_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker_module, "SERVICE_TOKEN_RETRY_BASE_SECONDS", 0)
    transport = _FlakyTransport([httpx.ReadTimeout("nacos")] * worker_module.SERVICE_TOKEN_ATTEMPTS)
    monkeypatch.setattr(httpx, "AsyncClient", _flaky_client(transport))

    with pytest.raises(worker_module.ServiceTokenError, match="transport: ReadTimeout"):
        asyncio.run(worker_module.acquire_service_token(_svc_settings(), "W01"))

    assert transport.calls == worker_module.SERVICE_TOKEN_ATTEMPTS