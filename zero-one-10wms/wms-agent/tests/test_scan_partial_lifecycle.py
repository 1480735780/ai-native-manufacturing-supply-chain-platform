"""SCAN-PARTIAL 元告警生命周期回归（审计 m03535）。

缺陷：SCAN-PARTIAL 的 object_id 原为 scan_id、指纹每次变化，且不在
SCAN_TYPE_RULE_IDS / rule_ok 中，导致每条 partial 告警永久 open
（健康扫描后仍挂着 6 条）。修复后按「仓库+来源」收敛：同一来源重复 partial
复用同一告警，该来源恢复健康时自动关闭，而扫描别的来源不得顺带关闭。
"""

from __future__ import annotations

import httpx
import pytest

from app.scan.repository import MemoryScanStore
from app.scan.service import run_scan
from app.security import Principal
from app.tools.gateway_client import GatewayClient

TOKEN = "header.payload.signature"
NOUP_PATH = "/daycheck/no-up/get-no-up-goods-page"

pytestmark = pytest.mark.asyncio


def _user() -> Principal:
    return Principal(user_id="u-1", user_name="tester", authorities=("ckjl",))


def _gateway(handler) -> GatewayClient:
    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))


def _page(rows: list[dict]) -> httpx.Response:
    return httpx.Response(
        200, json={"code": 10000, "data": {"rows": rows, "total": len(rows), "pages": 1}}
    )


def _bare_list() -> httpx.Response:
    """裸 List：分页 DTO 契约被破坏 → 取数标 partial（unexpected_list_payload）。"""
    return httpx.Response(200, json={"code": 10000, "data": []})


async def _scan(store: MemoryScanStore, scan_types: list[str], handler, *, scan_id: str):
    return await run_scan(
        scan_id=scan_id,
        scan_types=scan_types,
        principal=_user(),
        token=TOKEN,
        client=_gateway(handler),
        store=store,
        allowed_warehouses=["W01"],
        notification_mode="dry_run",
    )


def _partial_alerts(store: MemoryScanStore) -> list[dict]:
    return [a for a in store.alerts.values() if a["ruleId"] == "SCAN-PARTIAL"]


async def test_partial_fingerprint_is_stable_per_source():
    store = MemoryScanStore()
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == NOUP_PATH:
            return _bare_list()
        return _page([])

    first = await _scan(store, ["no_up"], handler, scan_id="scan-p1")
    assert first["partial"] is True
    alerts = _partial_alerts(store)
    assert len(alerts) == 1
    assert alerts[0]["objectId"] == "no_up"
    assert alerts[0]["objectType"] == "scan_source"
    assert alerts[0]["ruleVersion"] == "v1"
    assert alerts[0]["evidence"]["source"] == "no_up"
    fingerprint = alerts[0]["fingerprint"]

    # 同一来源再次 partial：指纹不变 ⇒ 复用同一条告警，不新增、不重复 open。
    second = await _scan(store, ["no_up"], handler, scan_id="scan-p2")
    assert second["partial"] is True
    alerts = _partial_alerts(store)
    assert len(alerts) == 1
    assert alerts[0]["fingerprint"] == fingerprint
    assert alerts[0]["scanId"] == "scan-p2"


async def test_healthy_scan_of_same_source_auto_resolves_partial_alert():
    store = MemoryScanStore()
    def partial_handler(request: httpx.Request) -> httpx.Response:
        return _bare_list()

    await _scan(store, ["no_up"], partial_handler, scan_id="scan-p3")
    alert_id = _partial_alerts(store)[0]["alertId"]
    assert store.alerts[alert_id]["state"] == "open"

    def healthy_handler(request: httpx.Request) -> httpx.Response:
        return _page([])

    run = await _scan(store, ["no_up"], healthy_handler, scan_id="scan-p4")
    assert run["partial"] is False
    assert store.alerts[alert_id]["state"] == "resolved"
    assert run["counts"]["alertsAutoResolved"] == 1


async def test_healthy_scan_of_other_source_keeps_partial_alert_open():
    store = MemoryScanStore()
    def partial_handler(request: httpx.Request) -> httpx.Response:
        return _bare_list()

    await _scan(store, ["no_up"], partial_handler, scan_id="scan-p5")
    alert_id = _partial_alerts(store)[0]["alertId"]

    # expiry 健康：本次没有扫描 no_up，不能顺带关掉它的 partial 告警。
    def healthy_handler(request: httpx.Request) -> httpx.Response:
        return _page([])

    run = await _scan(store, ["expiry"], healthy_handler, scan_id="scan-p6")
    assert run["partial"] is False
    assert store.alerts[alert_id]["state"] == "open"
    assert run["counts"]["staleCheckSkipped"] >= 1
