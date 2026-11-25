"""F-015 效期纵向切片的确定性测试。

规则判定（是否存在/级别）必须完全确定性；mock gateway + 固定输入回放，
不依赖本地 .env、PG 或真实网络。测试不断言 LLM 文案（本切片不用 LLM）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.scan import router as scan_router
from app.scan.repository import MemoryScanStore
from app.scan.rules.base import RuleContext
from app.scan.rules.expiry import evaluate_expiry
from app.scan.service import run_scan
from app.security import Principal, require_principal
from app.tools.gateway_client import GatewayClient

NOW = datetime(2026, 11, 24, 9, 0, tzinfo=timezone.utc)
TOKEN = "header.payload.signature"
EXP_PATH = "/stock/expiry-warning/query-all"


def _ctx(warehouse: str = "W01") -> RuleContext:
    return RuleContext(warehouse=warehouse, now=NOW)


def _row(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": "S1", "resDate": 2.0, "guoqibili": "0.01", "bzhiQi": "360",
        "cusCode": "C1", "goodsId": "G1", "goodsProData": "2026-01-01",
        "dqr": "2026-11-26", "shpMingCheng": "小蓝管", "kuWeiBianMa": "KW-A-01",
    }
    row.update(overrides)
    return row


# ---------- rules ----------

def test_expired_is_p0() -> None:
    out = evaluate_expiry([_row(resDate=-1.0)], _ctx())
    assert len(out) == 1
    assert out[0].rule_id == "EXP-EXPIRED"
    assert out[0].severity == "P0"
    assert out[0].rule_degraded is False


def test_near_by_resdate_is_p1() -> None:
    out = evaluate_expiry([_row(resDate=3.0, guoqibili="0.9")], _ctx())
    assert len(out) == 1
    assert out[0].rule_id == "EXP-NEAR" and out[0].severity == "P1"


def test_near_by_ratio_is_p1() -> None:
    out = evaluate_expiry([_row(resDate=100.0, guoqibili="0.2", bzhiQi="360")], _ctx())
    assert len(out) == 1
    assert out[0].rule_id == "EXP-NEAR" and out[0].severity == "P1"


def test_ratio_parse_failure_falls_back_to_resdate_and_degrades() -> None:
    out = evaluate_expiry([_row(resDate=3.0, guoqibili="bad", bzhiQi="360")], _ctx())
    assert len(out) == 1
    assert out[0].severity == "P1"
    assert out[0].rule_degraded is True


def test_watch_is_p2() -> None:
    out = evaluate_expiry([_row(resDate=20.0, guoqibili="0.9")], _ctx())
    assert len(out) == 1
    assert out[0].rule_id == "EXP-WATCH" and out[0].severity == "P2"


def test_missing_resdate_is_skipped() -> None:
    out = evaluate_expiry([_row(resDate=None)], _ctx())
    assert out == []


def test_fingerprint_separates_object_id() -> None:
    a = evaluate_expiry([_row(id="S1", goodsId="G1")], _ctx())[0]
    b = evaluate_expiry([_row(id="S2", goodsId="G2")], _ctx())[0]
    assert a.fingerprint != b.fingerprint
    assert a.fingerprint.startswith("sha256:")


# ---------- source ----------

def _gateway(rows: list[dict[str, Any]], total: int | None = None) -> GatewayClient:
    total = len(rows) if total is None else total

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == EXP_PATH
        assert request.headers.get("Authorization") == f"Bearer {TOKEN}"
        return httpx.Response(200, json={
            "code": 10000,
            "data": {"rows": rows, "total": total},
        })

    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_source_dedupes_by_id() -> None:
    from app.scan.sources.expiry import fetch_expiry

    rows = [_row(id="S1"), _row(id="S1"), _row(id="S2")]
    result = await fetch_expiry(_gateway(rows), TOKEN)
    assert result.status == "ok"
    assert len(result.rows) == 2


@pytest.mark.asyncio
async def test_source_marks_error_as_partial() -> None:
    from app.scan.sources.expiry import fetch_expiry

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 9994, "data": None})

    client = GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))
    result = await fetch_expiry(client, TOKEN)
    assert result.status == "error"
    assert result.truncated is True


# ---------- service ----------

def _user_principal() -> Principal:
    return Principal(user_id="u-1", user_name="tester", authorities=["gly"])


def _service_principal(scope: tuple[str, ...] = ("W01",)) -> Principal:
    return Principal(
        user_id="svc", user_name="agent-inspector", authorities=["insp_read"],
        warehouse_scope=scope, token_use="agent_service",
    )


@pytest.mark.asyncio
async def test_manual_scan_creates_alerts_with_dry_run_notifications() -> None:
    """服务端通知模式 dry_run：告警照常落库，只写 dry_run 通知记录不发送。"""
    store = MemoryScanStore()
    rows = [_row(id="S1", resDate=-1.0), _row(id="S2", resDate=3.0)]
    run = await run_scan(
        scan_id="scan-test-1", scan_types=["expiry"], principal=_user_principal(),
        token=TOKEN, client=_gateway(rows), store=store,
        allowed_warehouses=["W01"], dry_run=False, notification_mode="dry_run",
    )
    assert run["status"] == "succeeded"
    assert run["trigger"] == "manual" and run["actorType"] == "user"
    assert run["partial"] is False
    assert run["counts"]["findings"] == 2
    assert run["counts"]["alertsCreated"] == 2
    assert len(store.notifications) == 2
    assert all(n["status"] == "dry_run" for n in store.notifications)
    assert len(await store.list_alerts()) == 2


@pytest.mark.asyncio
async def test_request_dry_run_skips_alerts_and_notifications() -> None:
    """请求级 dryRun=true：只算 findings 写 scan_runs，不落告警不发通知。"""
    store = MemoryScanStore()
    rows = [_row(id="S1", resDate=-1.0), _row(id="S2", resDate=3.0)]
    run = await run_scan(
        scan_id="scan-dry", scan_types=["expiry"], principal=_user_principal(),
        token=TOKEN, client=_gateway(rows), store=store,
        allowed_warehouses=["W01"], dry_run=True, notification_mode="in_app",
    )
    assert run["status"] == "succeeded"
    assert run["counts"]["findings"] == 2
    assert run["counts"]["alertsCreated"] == 0
    assert run["counts"]["notifications"] == 0
    assert len(store.notifications) == 0
    assert len(await store.list_alerts()) == 0


@pytest.mark.asyncio
async def test_service_scan_derives_schedule_trigger() -> None:
    store = MemoryScanStore()
    run = await run_scan(
        scan_id="scan-test-2", scan_types=["expiry"], principal=_service_principal(),
        token=TOKEN, client=_gateway([_row(id="S1")]), store=store,
        allowed_warehouses=["W01"], dry_run=True,
    )
    assert run["status"] == "succeeded"
    assert run["trigger"] == "schedule" and run["actorType"] == "service"


@pytest.mark.asyncio
async def test_service_scan_out_of_scope_fails() -> None:
    store = MemoryScanStore()
    run = await run_scan(
        scan_id="scan-test-3", scan_types=["expiry"],
        principal=_service_principal(scope=("W02",)), token=TOKEN,
        client=_gateway([_row(id="S1")]), store=store,
        allowed_warehouses=["W01"], dry_run=True,
    )
    assert run["status"] == "failed"
    assert run["errorSummary"] == "AuthError"


@pytest.mark.asyncio
async def test_rescan_updates_existing_alert_without_new_notification() -> None:
    store = MemoryScanStore()
    common = dict(
        scan_types=["expiry"], principal=_user_principal(), token=TOKEN,
        client=_gateway([_row(id="S1", resDate=-1.0)]), store=store,
        allowed_warehouses=["W01"], dry_run=False, notification_mode="dry_run",
    )
    first = await run_scan(scan_id="scan-a", **common)
    second = await run_scan(scan_id="scan-b", **common)
    assert first["counts"]["alertsCreated"] == 1
    assert second["counts"]["alertsUpdated"] == 1
    assert second["counts"]["alertsCreated"] == 0
    assert len(store.notifications) == 1
    assert (await store.list_alerts())[0]["occurrenceCount"] == 2


# ---------- router ----------

def _build_app() -> tuple[TestClient, MemoryScanStore]:
    app = create_app()
    store = MemoryScanStore()
    app.state.scan_store = store
    app.dependency_overrides[require_principal] = lambda: _user_principal()
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    app.dependency_overrides[scan_router.get_client] = lambda: _gateway(
        [_row(id="S1", resDate=-1.0), _row(id="S2", resDate=3.0)]
    )
    return TestClient(app), store


def _drain_queue(client: TestClient, store: MemoryScanStore) -> None:
    """测试辅助：POST 只入队，这里手动驱动一次 worker 消费（生产由 lifespan worker 完成）。"""
    import asyncio

    from app.scan.worker import execute_queued_scan

    app = client.app
    settings = app.state.settings
    override_client = app.dependency_overrides.get(scan_router.get_client)
    gateway = override_client() if override_client else scan_router.get_client(type("R", (), {"app": app})())

    async def _run() -> None:
        while True:
            claimed = await store.claim_next_queued()
            if claimed is None:
                break
            # token 注入避免真实服务令牌调用；JWT 不落库语义由生产路径保证
            await execute_queued_scan(claimed, store=store, settings=settings, client=gateway, token=TOKEN)

    asyncio.run(_run())


def test_scan_api_end_to_end() -> None:
    client, store = _build_app()
    # 不指定 dryRun：服务端通知模式 dry_run 仍落告警，只写 dry_run 通知记录
    resp = client.post(
        "/agent/scan",
        json={"scanTypes": ["expiry"]},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status_code == 202
    data = resp.json()["data"]
    scan_id = data["scanId"]
    assert data["status"] == "queued"

    _drain_queue(client, store)

    status = client.get(
        f"/agent/scans/{scan_id}", headers={"Authorization": f"Bearer {TOKEN}"}
    ).json()
    assert status["code"] == 10000
    assert status["data"]["status"] == "succeeded"
    assert status["data"]["counts"]["alertsCreated"] == 2

    alerts = client.get(
        "/agent/alerts", headers={"Authorization": f"Bearer {TOKEN}"}
    ).json()
    assert alerts["code"] == 10000
    assert len(alerts["data"]) == 2
    assert {a["severity"] for a in alerts["data"]} == {"P0", "P1"}


def test_scan_requires_jwt() -> None:
    app = create_app()
    app.state.scan_store = MemoryScanStore()
    with TestClient(app) as client:
        resp = client.post("/agent/scan", json={"scanTypes": ["expiry"]})
    assert resp.status_code == 401
