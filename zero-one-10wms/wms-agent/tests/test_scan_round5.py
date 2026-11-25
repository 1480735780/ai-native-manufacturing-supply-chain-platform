"""F-015 阶段1 回归测试：告警详情 / 认领 / 已读 / 真实 in_app。

覆盖实施方案阶段1 的退出条件：
- 告警详情（含证据、规则参数、事件流水、触发扫描）；
- 认领：他人已认领 409，ack 不等同于认领；
- 游标分页 (lastSeenAt, alertId) 不漏不重；
- 站内通知按稳定 user_id 隔离，已读只影响本人；
- notification_mode=in_app 时通知在告警事务内写成 sent。

Memory 后端的队列/告警契约与 PG 的对齐由 tests/test_scan_store_contract.py 保证。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.scan import router as scan_router
from app.scan.repository import MemoryScanStore
from app.scan.service import run_scan
from app.security import Principal, require_principal
from app.tools.gateway_client import GatewayClient

TOKEN = "header.payload.signature"
NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)


def _user(
    name: str = "tester", authorities: tuple[str, ...] = ("ckjl",),
    user_id: str = "u-1", **kw: Any,
) -> Principal:
    return Principal(user_id=user_id, user_name=name, authorities=authorities, **kw)


def _other(user_id: str = "u-2", name: str = "other") -> Principal:
    return Principal(user_id=user_id, user_name=name, authorities=("ckjl",))


def _gateway(handler) -> GatewayClient:
    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))


def _ok(data: dict[str, Any]):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 10000, "data": data})

    return _gateway(handler)


def _no_up_row(row_id: str, age_hours: float) -> dict[str, Any]:
    return {
        "rowId": row_id, "noticeId": f"N-{row_id}", "goods_id": "G1", "tin_id": "T1",
        "bin_id": "B1", "cus_code": "C1",
        "create_date": (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat(),
    }


def _client(principal: Principal, store: MemoryScanStore) -> TestClient:
    app = create_app()
    app.state.scan_store = store
    app.dependency_overrides[require_principal] = lambda: principal
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    return TestClient(app)


async def _seed_alert(
    store: MemoryScanStore, *, fingerprint: str = "fp-1", severity: str = "P1",
    warehouse: str = "W01", last_seen_at: str | None = None,
    notification: dict[str, Any] | None = None,
) -> int:
    alert = {
        "fingerprint": fingerprint, "severity": severity, "ruleId": "NOUP-OVERDUE",
        "ruleVersion": "v0.2.0", "objectType": "no_up_goods", "objectId": f"O-{fingerprint}",
        "dimension": {"warehouse": warehouse}, "title": "NOUP-OVERDUE P1",
        "evidence": {"noticeId": "N1"}, "suggestedActions": ["MOVE_TO_BIN"],
        "warehouseId": warehouse, "scanId": "scan-seed", "traceId": "trace-seed",
        "lastSeenAt": last_seen_at or NOW.isoformat(),
    }
    result = await store.upsert_alert(alert, notification=notification)
    return result.alert_id


# ---------- 告警详情 ----------

async def test_alert_detail_returns_evidence_events_and_scan() -> None:
    store = MemoryScanStore()
    await store.insert_run({
        "scanId": "scan-seed", "trigger": "manual", "actorType": "user", "actorId": "tester",
        "status": "succeeded", "partial": False, "sourceStatus": [], "configHash": "h",
        "ruleVersion": "expiry=v0.2.0", "scanTypes": ["no_up"], "requestId": None,
        "scheduleSlot": None, "scanKey": "scan-seed", "queuedAt": NOW.isoformat(),
        "startedAt": NOW.isoformat(), "finishedAt": NOW.isoformat(), "attempt": 1,
        "counts": {}, "errorSummary": None, "warehouse": "W01", "dryRun": False,
        "notificationMode": "dry_run", "payloadHash": "sha256:p", "traceId": "trace-seed",
    })
    alert_id = await _seed_alert(store)

    client = _client(_user(), store)
    resp = client.get(f"/agent/alerts/{alert_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["alertId"] == alert_id
    assert data["evidence"]["noticeId"] == "N1"          # 证据链可见
    assert data["ruleParams"] == {}                      # 规则参数可见
    assert data["events"] and data["events"][0]["eventType"] == "created"
    assert data["scan"]["scanId"] == "scan-seed"        # 触发扫描可追溯


async def test_alert_detail_hides_out_of_scope_warehouse() -> None:
    store = MemoryScanStore()
    alert_id = await _seed_alert(store, warehouse="W02")
    client = _client(_user(warehouse_scope=("W01",)), store)
    resp = client.get(f"/agent/alerts/{alert_id}")
    # GET 端点沿用既有约定：业务码在 body 里（与 GET /agent/alerts 一致）
    assert resp.json()["code"] == 9997
    assert resp.json()["data"] is None


# ---------- 认领 ----------

async def test_claim_alert_sets_assignee_and_blocks_other_user() -> None:
    store = MemoryScanStore()
    alert_id = await _seed_alert(store)

    client = _client(_user(user_id="u-1", name="tester"), store)
    resp = client.post(f"/agent/alerts/{alert_id}/claim")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["assignee"] == "tester" and data["assigneeUserId"] == "u-1"
    assert data["claimedAt"]

    # 他人再认领 → 409
    other_client = _client(_other(), store)
    conflict = other_client.post(f"/agent/alerts/{alert_id}/claim")
    assert conflict.status_code == 409 and conflict.json()["code"] == 9996


async def test_claim_requires_alert_permission() -> None:
    store = MemoryScanStore()
    alert_id = await _seed_alert(store)
    client = _client(_user(authorities=("insp_read",)), store)
    resp = client.post(f"/agent/alerts/{alert_id}/claim")
    assert resp.status_code == 403 and resp.json()["code"] == 9997


async def test_ack_does_not_take_ownership() -> None:
    """ack 只确认，不改 assignee（认领是独立动作）。"""
    store = MemoryScanStore()
    alert_id = await _seed_alert(store)
    client = _client(_user(), store)
    resp = client.post(f"/agent/alerts/{alert_id}/ack", json={})
    assert resp.status_code == 200
    detail = await store.get_alert(alert_id)
    assert detail["state"] == "acknowledged"
    assert detail["acknowledgedBy"] == "tester"
    assert not detail.get("assignee")


async def test_close_reason_and_deadline_surface_on_alert_and_detail() -> None:
    """关闭信息（解决原因/忽略截止）必须随告警主体返回，前端抽屉直接展示而不必翻事件流。"""
    store = MemoryScanStore()
    resolved_id = await _seed_alert(store)
    ignored_id = await _seed_alert(store, fingerprint="fp-ignore")

    client = _client(_user(), store)
    assert client.post(f"/agent/alerts/{resolved_id}/resolve", json={"reason": "已联系客户"}).status_code == 200
    assert client.post(f"/agent/alerts/{ignored_id}/ignore", json={"reason": "重复告警"}).status_code == 200

    resolved = await store.get_alert(resolved_id)
    assert resolved["state"] == "resolved"
    assert resolved["resolvedReason"] == "已联系客户" and resolved["resolvedAt"]
    assert resolved["ignoredUntil"] is None

    ignored = await store.get_alert(ignored_id)
    assert ignored["state"] == "ignored"
    assert ignored["resolvedReason"] == "重复告警" and ignored["ignoredUntil"]

    # 详情端点（抽屉数据源）也要带上这些字段
    detail = client.get(f"/agent/alerts/{ignored_id}").json()["data"]
    assert detail["resolvedReason"] == "重复告警" and detail["ignoredUntil"]
    # rule_version 随列表/详情返回（抽屉"规则"行需要），PG 与 memory 同形状
    assert detail["ruleVersion"] == "v0.2.0"
    listed = client.get("/agent/alerts/page?pageSize=50").json()["data"]["items"]
    assert all(row["ruleVersion"] == "v0.2.0" for row in listed)
    # 新建告警在创建时即带这三个键，保证双后端返回形状一致
    fresh_id = await _seed_alert(store, fingerprint="fp-fresh")
    fresh = (await store.get_alert(fresh_id))
    assert fresh["resolvedReason"] is None and fresh["resolvedAt"] is None and fresh["ignoredUntil"] is None


# ---------- 游标分页 ----------

async def test_alerts_page_cursor_has_no_gap_or_duplicate() -> None:
    store = MemoryScanStore()
    for i in range(5):
        await _seed_alert(
            store, fingerprint=f"fp-{i}",
            last_seen_at=(NOW + timedelta(seconds=i)).isoformat(),
        )

    client = _client(_user(), store)
    first = client.get("/agent/alerts/page", params={"pageSize": 2}).json()["data"]
    assert [a["fingerprint"] for a in first["items"]] == ["fp-4", "fp-3"]

    cursor = first["nextCursor"]
    second = client.get("/agent/alerts/page", params={
        "pageSize": 2, "lastSeenAt": cursor["lastSeenAt"], "lastAlertId": cursor["lastAlertId"],
    }).json()["data"]
    assert [a["fingerprint"] for a in second["items"]] == ["fp-2", "fp-1"]

    cursor = second["nextCursor"]
    third = client.get("/agent/alerts/page", params={
        "pageSize": 2, "lastSeenAt": cursor["lastSeenAt"], "lastAlertId": cursor["lastAlertId"],
    }).json()["data"]
    assert [a["fingerprint"] for a in third["items"]] == ["fp-0"]


async def test_alerts_page_rejects_out_of_scope_filter() -> None:
    store = MemoryScanStore()
    await _seed_alert(store, warehouse="W01")
    client = _client(_user(warehouse_scope=("W01",)), store)
    resp = client.get("/agent/alerts/page", params={"warehouseId": "W02"})
    assert resp.json()["code"] == 9997 and resp.json()["data"] is None


# ---------- 通知与已读 ----------

async def test_notifications_are_isolated_by_stable_user_id() -> None:
    store = MemoryScanStore()
    await _seed_alert(
        store, fingerprint="fp-mine",
        notification={
            "recipients": ["tester"], "recipientUserId": "u-1", "status": "sent",
            "payloadDigest": "fp-mine", "scope": "trace-seed",
        },
    )

    mine = _client(_user(user_id="u-1", name="tester"), store)
    resp = mine.get("/agent/notifications")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 1 and items[0]["recipientUserId"] == "u-1"
    assert items[0]["status"] == "sent" and items[0]["sentAt"]

    # 同名不同稳定 id 的人看不到
    other = _client(_other(user_id="u-9", name="tester"), store)
    assert other.get("/agent/notifications").json()["data"]["items"] == []


async def test_notification_read_is_owner_only() -> None:
    store = MemoryScanStore()
    await _seed_alert(
        store, fingerprint="fp-read",
        notification={
            "recipients": ["tester"], "recipientUserId": "u-1", "status": "sent",
            "payloadDigest": "fp-read", "scope": "trace-seed",
        },
    )
    mine = _client(_user(user_id="u-1", name="tester"), store)
    notification_id = mine.get("/agent/notifications").json()["data"]["items"][0]["notificationId"]

    other = _client(_other(user_id="u-9", name="tester"), store)
    denied = other.post(f"/agent/notifications/{notification_id}/read")
    assert denied.status_code == 404 and denied.json()["code"] == 9999

    ok = mine.post(f"/agent/notifications/{notification_id}/read")
    assert ok.status_code == 200
    assert ok.json()["data"]["readAt"]

    # 已读后 unreadOnly 不再返回
    unread = mine.get("/agent/notifications", params={"unreadOnly": True}).json()["data"]["items"]
    assert unread == []


# ---------- in_app 真实投递 ----------

async def test_in_app_notification_written_as_sent_inside_alert_transaction() -> None:
    store = MemoryScanStore()
    gateway = _ok({
        "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
        "rows": [_no_up_row("R1", age_hours=9)],
    })
    run = await run_scan(
        scan_id="scan-inapp", scan_types=["no_up"], principal=_user(), token=TOKEN,
        client=gateway, store=store, allowed_warehouses=["W01"],
        notification_mode="in_app",
    )
    assert run["counts"]["alertsCreated"] == 1
    assert run["counts"]["notifications"] == 1
    note = store.notifications[0]
    assert note["status"] == "sent"          # 站内信无外部投递环节，直接 sent
    assert note["recipientUserId"] == "u-1"  # 稳定 id 随通知落库，供已读隔离


async def test_dry_run_notification_mode_still_records_notification() -> None:
    """notification_mode=dry_run：告警照常落库，通知只记 dry_run 不发送。"""
    store = MemoryScanStore()
    gateway = _ok({
        "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
        "rows": [_no_up_row("R1", age_hours=9)],
    })
    run = await run_scan(
        scan_id="scan-dry", scan_types=["no_up"], principal=_user(), token=TOKEN,
        client=gateway, store=store, allowed_warehouses=["W01"],
        notification_mode="dry_run",
    )
    assert run["counts"]["alertsCreated"] == 1
    assert run["counts"]["notifications"] == 1
    assert store.notifications[0]["status"] == "dry_run"


async def test_request_dry_run_creates_no_alert_and_no_notification() -> None:
    store = MemoryScanStore()
    gateway = _ok({
        "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
        "rows": [_no_up_row("R1", age_hours=9)],
    })
    run = await run_scan(
        scan_id="scan-reqdry", scan_types=["no_up"], principal=_user(), token=TOKEN,
        client=gateway, store=store, allowed_warehouses=["W01"],
        dry_run=True, notification_mode="in_app",
    )
    assert run["counts"]["findings"] == 1
    assert run["counts"]["alertsCreated"] == 0
    assert run["counts"]["notifications"] == 0
    assert store.alerts == {} and store.notifications == []


async def test_service_account_cannot_read_notifications() -> None:
    store = MemoryScanStore()
    svc = Principal(
        user_id="svc", user_name="agent-inspector", authorities=("insp_read",),
        warehouse_scope=("W01",), token_use="agent_service",
    )
    client = _client(svc, store)
    resp = client.get("/agent/notifications")
    assert resp.status_code == 403 and resp.json()["code"] == 9997
