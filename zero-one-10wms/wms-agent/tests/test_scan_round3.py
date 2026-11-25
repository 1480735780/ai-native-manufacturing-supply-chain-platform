"""F-015 v0.2.0 第三轮闭环加固测试：权限边界、跨仓 403、告警操作校验。

使用 MemoryScanStore + httpx.MockTransport，不依赖 PG/Nacos/真实网络。
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
from app.security import (
    Principal, can_operate_alert, can_trigger_scan, can_view_alerts,
    require_principal,
)

TOKEN = "header.payload.signature"
EXP_PATH = "/stock/expiry-warning/query-all"


def _user(name: str = "tester", authorities: tuple[str, ...] = ("ckjl",)) -> Principal:
    """巡检页业务角色（仓库经理 ckjl）：可看、可发起、可操作。"""
    return Principal(user_id="u-1", user_name=name, authorities=authorities)


def _service(authorities: tuple[str, ...] = ("insp_read",)) -> Principal:
    return Principal(
        user_id="svc", user_name="agent-inspector", authorities=authorities,
        warehouse_scope=("W01",), token_use="agent_service",
    )


def _gateway() -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 10000, "data": {"rows": [], "total": 0}})
    return httpx.MockTransport(handler)


# ---------- P0 权限收紧（第四轮：view / trigger / handle 三种权限拆分） ----------

def test_plain_login_cannot_start_or_view() -> None:
    """仅登录（无任何巡检权限码）不能发起巡检、不能查看告警。"""
    plain = Principal(user_id="u", user_name="plain", authorities=())
    assert can_trigger_scan(plain) is False
    assert can_view_alerts(plain) is False
    assert can_operate_alert(plain) is False


def test_view_trigger_handle_are_independent() -> None:
    """只读权限码只能看；handle/trigger 权限码各管各的；业务角色三样都有。"""
    viewer = _user(authorities=("inspection:alert:view",))
    assert can_view_alerts(viewer) is True
    assert can_trigger_scan(viewer) is False   # 只读权限不能发起扫描
    assert can_operate_alert(viewer) is False  # 只读权限不能操作告警
    reader = _user(authorities=("insp_read",))
    assert can_view_alerts(reader) is True
    assert can_trigger_scan(reader) is False
    assert can_operate_alert(reader) is False
    trigger_only = _user(authorities=("inspection:scan:trigger",))
    assert can_trigger_scan(trigger_only) is True
    assert can_view_alerts(trigger_only) is False
    handler = _user(authorities=("inspection:alert:handle",))
    assert can_operate_alert(handler) is True
    assert can_trigger_scan(handler) is False
    # 菜单 MENU-DAILY-CHECK-05 对 cg/ckjl 可见，API 必须同样可用
    for role in ("ckjl", "cg"):
        business = _user(authorities=(role,))
        assert can_view_alerts(business) is True
        assert can_trigger_scan(business) is True
        assert can_operate_alert(business) is True


def test_service_account_can_only_trigger() -> None:
    """服务账号只允许 trigger（定时发起），不能看告警、不能操作。"""
    svc = _service()
    assert can_trigger_scan(svc) is True
    assert can_view_alerts(svc) is False
    assert can_operate_alert(svc) is False


def test_admin_can_do_all() -> None:
    admin = _user(authorities=("gly",))
    assert can_trigger_scan(admin) is True
    assert can_view_alerts(admin) is True
    assert can_operate_alert(admin) is True


def test_cross_warehouse_scan_forbidden() -> None:
    """POST 跨仓（不在配置/令牌范围）→ 403。"""
    app = create_app()
    store = MemoryScanStore()
    app.state.scan_store = store
    principal = _service()
    app.dependency_overrides[require_principal] = lambda: principal
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    with TestClient(app) as client:
        resp = client.post(
            "/agent/scan",
            json={"scanTypes": ["expiry"], "warehouse": "W02"},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
    assert resp.status_code == 403
    assert resp.json()["code"] == 9997


def test_service_cannot_operate_alert_via_api() -> None:
    """服务账号调用 ack/resolve/ignore → 403。"""
    app = create_app()
    store = MemoryScanStore()
    app.state.scan_store = store
    await_store = store
    # 塞一条 open 告警
    import asyncio
    asyncio.run(await_store.upsert_alert({
        "fingerprint": "fp-1", "severity": "P1", "state": "open", "warehouseId": "W01",
    }))
    app.dependency_overrides[require_principal] = lambda: _service()
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    with TestClient(app) as client:
        resp = client.post(
            "/agent/alerts/1/ack",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
    assert resp.status_code == 403


def test_resolve_requires_reason() -> None:
    """resolve/ignore 无 reason → 422。"""
    app = create_app()
    store = MemoryScanStore()
    app.state.scan_store = store
    import asyncio
    asyncio.run(store.upsert_alert({
        "fingerprint": "fp-2", "severity": "P1", "state": "open", "warehouseId": "W01",
    }))
    app.dependency_overrides[require_principal] = lambda: _user()
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    with TestClient(app) as client:
        resp = client.post(
            "/agent/alerts/1/resolve",
            json={},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
    assert resp.status_code == 422
    assert resp.json()["code"] == 9995


def test_invalid_transition_returns_409() -> None:
    """非法状态转移（open→open 不存在；resolved 是终态）→ 409。"""
    app = create_app()
    store = MemoryScanStore()
    app.state.scan_store = store
    import asyncio
    asyncio.run(store.upsert_alert({
        "fingerprint": "fp-3", "severity": "P1", "state": "open", "warehouseId": "W01",
    }))
    app.dependency_overrides[require_principal] = lambda: _user()
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    with TestClient(app) as client:
        # 先 resolved
        r1 = client.post(
            "/agent/alerts/1/resolve", json={"reason": "done"},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert r1.status_code == 200
        # 终态再 ack → 409
        r2 = client.post(
            "/agent/alerts/1/ack", json={"reason": "again"},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
    assert r2.status_code == 409


def test_post_returns_immediately_queued() -> None:
    """POST 只入队立即返回 202 queued，不等扫描执行。"""
    app = create_app()
    store = MemoryScanStore()
    app.state.scan_store = store
    app.dependency_overrides[require_principal] = lambda: _user()
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    with TestClient(app) as client:
        resp = client.post(
            "/agent/scan", json={"scanTypes": ["expiry"]},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
    assert resp.status_code == 202
    assert resp.json()["data"]["status"] == "queued"
    # 入队记录仍在队列（没有被同步消费）
    runs = [r for r in store.runs.values() if r["status"] == "queued"]
    assert len(runs) == 1
