"""阶段5 自动化测试：安全自动 resolved + 最小内部调度。

覆盖用户阶段5 清单中的必测项：
1. 条件消失才关闭；
2. partial / 超时 / 分页漂移不关；
3. 数据质量跳过不关；
4. 乱序扫描不关；
5. ignored 终态不复活；
6. 条件复发新建告警；
7. 用户操作与自动关闭并发以状态条件为准；
8. fake clock 覆盖窗口边界 / 重启 / 重复槽；
9. 调度关闭时不入队；
10. retry 复用原配置快照。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.config import Settings
from app.scan import router as scan_router
from app.scan.config import ScanCron, load_scan_config, parse_scan_cron
from app.scan.repository import AUTO_RESOLVE_EVENT, MemoryScanStore
from app.scan.scheduler import ScanScheduler, current_slot
from app.scan.service import enqueue_scan, run_scan
from app.security import Principal
from app.tools.gateway_client import GatewayClient

TOKEN = "header.payload.signature"
NOUP_PATH = "/daycheck/no-up/get-no-up-goods-page"
SHANGHAI = ZoneInfo("Asia/Shanghai")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _user(name: str = "tester", authorities: tuple[str, ...] = ("ckjl",), user_id: str = "u-1") -> Principal:
    return Principal(user_id=user_id, user_name=name, authorities=authorities)


def _service(warehouse: str = "W01") -> Principal:
    return Principal(
        user_id="agent-inspector",
        user_name="agent-inspector",
        authorities=("insp_read",),
        warehouse_scope=(warehouse,),
        token_use="agent_service",
    )


def _ok(data: dict) -> httpx.Response:
    return httpx.Response(200, json={"code": 10000, "data": data})


def _page(rows: list[dict], total: int | None = None, pages: int | None = None) -> dict:
    """网关分页 DTO 形状：rows / total / pages。"""
    return {
        "rows": rows,
        "total": len(rows) if total is None else total,
        "pages": 1 if pages is None else pages,
    }


def _no_up_row(row_id: str = "R1", age_hours: float = 500.0, **overrides) -> dict:
    # 上游 create_date 是本地时间（规则按 ctx.now 的时区解释裸时间）
    created = datetime.now(timezone.utc).astimezone() - timedelta(hours=age_hours)
    row = {
        "rowId": row_id,
        "noticeId": f"N-{row_id}",
        "goods_id": f"G-{row_id}",
        "bin_id": f"B-{row_id}",
        "tin_id": f"T-{row_id}",
        "cus_code": "C1",
        "shp_ming_cheng": "小蓝管",
        "create_date": created.strftime("%Y-%m-%d %H:%M:%S"),
    }
    row.update(overrides)
    return row


def _gateway(handler) -> GatewayClient:
    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))


def _settings(**overrides) -> Settings:
    payload = {"WMS_AGENT_SCAN_LEASE_SECONDS": 60}
    payload.update({f"WMS_AGENT_{key.upper()}": value for key, value in overrides.items()})
    return Settings(_env_file=None, **payload)


def _client(principal: Principal, store: MemoryScanStore):
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.security import require_principal

    app = create_app()
    app.state.scan_store = store
    app.dependency_overrides[require_principal] = lambda: principal
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    return TestClient(app)


async def _seed_alert(
    store: MemoryScanStore,
    *,
    fingerprint: str = "fp-1",
    severity: str = "P1",
    warehouse: str = "W01",
    object_id: str | None = None,
    last_seen_at: str | None = None,
    rule_id: str = "NOUP-OVERDUE",
    rule_version: str = "v0.2.0",
) -> int:
    """直接写一条告警（存储层用例，不经过规则指纹）。"""
    alert = {
        "fingerprint": fingerprint,
        "severity": severity,
        "ruleId": rule_id,
        "ruleVersion": rule_version,
        "objectType": "no_up_goods",
        "objectId": object_id or f"O-{fingerprint}",
        "dimension": {"warehouse": warehouse},
        "title": f"{rule_id} {severity}",
        "evidence": {},
        "suggestedActions": [],
        "warehouseId": warehouse,
        "scanId": "scan-seed",
        "traceId": "trace-seed",
        "lastSeenAt": last_seen_at or datetime.now(timezone.utc).isoformat(),
    }
    result = await store.upsert_alert(alert)
    return result.alert_id


async def _scan_no_up(
    store: MemoryScanStore,
    *,
    rows: list[dict],
    scan_id: str = "scan-auto",
    handler=None,
):
    """跑一次 no_up 扫描（rows 为空且未给 handler 时返回空页）。"""

    if handler is None:
        def handler(request: httpx.Request) -> httpx.Response:
            return _ok(_page(rows))

    gateway = _gateway(handler)
    return await run_scan(
        scan_id=scan_id,
        scan_types=["no_up"],
        principal=_user(),
        token=TOKEN,
        client=gateway,
        store=store,
        allowed_warehouses=["W01"],
        notification_mode="dry_run",
    )


def _only_alert(store: MemoryScanStore) -> dict:
    """排除 SCAN-PARTIAL 元告警后的唯一业务告警。"""
    alerts = [a for a in store.alerts.values() if a["ruleId"] != "SCAN-PARTIAL"]
    assert len(alerts) == 1, alerts
    return alerts[0]


# ---------------------------------------------------------------------------
# 1. 条件消失才关闭
# ---------------------------------------------------------------------------


async def test_auto_resolve_closes_alert_when_condition_disappears():
    store = MemoryScanStore()
    # 第一次扫描：超期 → 产生告警
    first = await _scan_no_up(store, rows=[_no_up_row("R1", 500.0)], scan_id="scan-1")
    assert first["counts"]["alertsCreated"] == 1
    alert = _only_alert(store)
    assert alert["state"] == "open"
    alert_id = alert["alertId"]

    # 第二次扫描：同一对象不再超期 → 自动关闭
    second = await _scan_no_up(store, rows=[_no_up_row("R1", 0.5)], scan_id="scan-2")
    assert second["counts"]["alertsAutoResolved"] == 1
    assert store.alerts[alert_id]["state"] == "resolved"
    assert store.alerts[alert_id]["resolvedReason"]
    events = [event for event in store.events if event["alertId"] == alert_id]
    assert any(event["eventType"] == AUTO_RESOLVE_EVENT for event in events)
    assert any(event["toState"] == "resolved" for event in events)
    # 事件保留 traceId 与 scanId
    auto_event = next(event for event in events if event["eventType"] == AUTO_RESOLVE_EVENT)
    assert auto_event["traceId"]
    assert auto_event["actorType"] == "system"
    assert auto_event["actorId"] == "scan-2"


async def test_auto_resolve_when_source_legitimately_returns_zero_rows():
    """真实 e2e 捕获的缺陷：对象已上架/被删后，第二次扫描源完整返回 0 行，求值结果为空。

    此时规则同样“已评估且未命中”，必须关闭；不能因为求值里没出现该规则就跳过。
    """
    store = MemoryScanStore()
    first = await _scan_no_up(
        store, rows=[_no_up_row("R1", 500.0), _no_up_row("R2", 300.0)], scan_id="scan-1",
    )
    assert first["counts"]["alertsCreated"] == 2
    second = await _scan_no_up(store, rows=[], scan_id="scan-2")
    assert second["partial"] is False
    assert second["counts"]["findings"] == 0
    assert second["counts"]["alertsAutoResolved"] == 2
    assert second["counts"]["staleCheckSkipped"] == 0
    assert {a["state"] for a in store.alerts.values()} == {"resolved"}
    # 0 行没有可记录的覆盖对象，但关闭事件仍带本次扫描的 trace 与 scanId
    auto_events = [e for e in store.events if e["eventType"] == AUTO_RESOLVE_EVENT]
    assert len(auto_events) == 2
    assert {e["actorId"] for e in auto_events} == {"scan-2"}
    assert {e["traceId"] for e in auto_events} == {second["traceId"]}


async def test_scan_type_registers_all_rules_even_without_findings():
    """取数可信时按扫描类型登记全部规则：expiry 0 行 → 三条规则都参与自动关闭判定。"""
    from app.scan.service import SCAN_TYPE_RULE_IDS

    assert SCAN_TYPE_RULE_IDS == {
        "expiry": ("EXP-EXPIRED", "EXP-NEAR", "EXP-WATCH"),
        "no_up": ("NOUP-OVERDUE",),
        "delay": ("DELAY-OVERDUE",),
        "backlog": ("BACKLOG-GROWTH",),
    }
    store = MemoryScanStore()
    await _seed_alert(store, fingerprint="fp-exp", rule_id="EXP-NEAR", object_id="W01|C1|G1|D1")

    def handler(request: httpx.Request) -> httpx.Response:
        return _ok(_page([]))

    run = await run_scan(
        scan_id="scan-exp-empty", scan_types=["expiry"], principal=_user(), token=TOKEN,
        client=_gateway(handler), store=store, allowed_warehouses=["W01"],
        notification_mode="dry_run",
    )
    assert run["partial"] is False
    assert run["counts"]["alertsAutoResolved"] == 1


async def test_malformed_backlog_snapshot_disables_auto_resolve():
    """backlog 快照形状不完整 / 数值全非法 ≠ “已评估且正常”：禁用本次自动关闭。"""
    from app.scan.rules.backlog import RULE_ID as BACKLOG_RULE_ID
    from app.scan.rules.base import RuleContext
    from app.scan.service import _evaluate_backlog
    from app.scan.sources.base import SourceResult

    ctx = RuleContext(warehouse="W01", now=datetime.now(timezone.utc))
    shape_bad = SourceResult(
        source="backlog", endpoint="/dashboard/query-pend-snapshot", pages=1,
        rows=[{"queueType": "receipt", "value": 1.0}],
    )
    all_invalid = SourceResult(
        source="backlog", endpoint="/dashboard/query-pend-snapshot", pages=1,
        rows=[{"queueType": q, "value": -1} for q in ("receipt", "to_up", "pick")],
    )
    for source in (shape_bad, all_invalid):
        evaluation, saved = await _evaluate_backlog(
            MemoryScanStore(), source, {}, ctx, "scan-x", "trace-x", "h",
        )
        assert saved == 0
        assert evaluation.findings == []
        assert evaluation.data_quality_skipped == [BACKLOG_RULE_ID]
    # 源本身不可信时不额外标记（由 source_trusted 兜底）
    failed = SourceResult(source="backlog", endpoint="/x", status="error")
    evaluation, saved = await _evaluate_backlog(MemoryScanStore(), failed, {}, ctx, "s", "t", "h")
    assert saved == 0 and evaluation.data_quality_skipped == []


async def test_auto_resolve_records_coverage_objects():
    store = MemoryScanStore()
    await _scan_no_up(store, rows=[_no_up_row("R1", 0.5)], scan_id="scan-cov")
    coverage = await store.list_evaluated_objects("scan-cov")
    assert coverage
    assert {row["ruleId"] for row in coverage} == {"NOUP-OVERDUE"}
    assert {row["objectId"] for row in coverage} == {"N-R1|G-R1|T-R1"}


async def test_coverage_is_idempotent_across_retries():
    store = MemoryScanStore()
    await _scan_no_up(store, rows=[_no_up_row("R1", 0.5)], scan_id="scan-cov")
    stored = await store.list_evaluated_objects("scan-cov")
    assert stored
    saved = await store.save_evaluated_objects(stored)
    assert saved == 0


# ---------------------------------------------------------------------------
# 2. partial / 分页漂移 不关
# ---------------------------------------------------------------------------


async def test_partial_scan_does_not_auto_resolve():
    store = MemoryScanStore()
    await _scan_no_up(store, rows=[_no_up_row("R1", 500.0)], scan_id="scan-hit")
    alert = _only_alert(store)
    assert alert["state"] == "open"

    # 源返回不完整分页 → partial
    def handler(request: httpx.Request) -> httpx.Response:
        return _ok(_page([], total=99, pages=9))

    result = await _scan_no_up(store, rows=[], scan_id="scan-partial", handler=handler)
    assert result["partial"] is True
    assert result["counts"]["alertsAutoResolved"] == 0
    assert store.alerts[alert["alertId"]]["state"] == "open"


async def test_page_drift_does_not_auto_resolve():
    store = MemoryScanStore()
    await _scan_no_up(store, rows=[_no_up_row("R1", 500.0)], scan_id="scan-hit2")
    alert = _only_alert(store)

    # 每页返回同一行 → 跨页重复稳定键 → page_drift
    def handler(request: httpx.Request) -> httpx.Response:
        return _ok(_page([_no_up_row("R1", 0.5)], total=20, pages=3))

    result = await _scan_no_up(store, rows=[], scan_id="scan-drift", handler=handler)
    assert result["partial"] is True
    assert any("page_drift" in (s.get("errorSummary") or "") for s in result["sourceStatus"])
    assert result["counts"]["alertsAutoResolved"] == 0
    assert store.alerts[alert["alertId"]]["state"] == "open"


async def test_source_error_does_not_auto_resolve():
    store = MemoryScanStore()
    await _scan_no_up(store, rows=[_no_up_row("R1", 500.0)], scan_id="scan-hit3")
    alert = _only_alert(store)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"code": 9999, "message": "boom"})

    result = await _scan_no_up(store, rows=[], scan_id="scan-error", handler=handler)
    assert result["partial"] is True
    assert result["counts"]["alertsAutoResolved"] == 0
    assert store.alerts[alert["alertId"]]["state"] == "open"


# ---------------------------------------------------------------------------
# 3. 数据质量跳过不关
# ---------------------------------------------------------------------------


async def test_missing_timestamp_prevents_auto_resolve():
    store = MemoryScanStore()
    await _scan_no_up(store, rows=[_no_up_row("R1", 500.0)], scan_id="scan-hit4")
    alert = _only_alert(store)

    row = _no_up_row("R1", 0.5)
    row["create_date"] = ""
    result = await _scan_no_up(store, rows=[row], scan_id="scan-quality")
    assert result["counts"]["alertsAutoResolved"] == 0
    assert store.alerts[alert["alertId"]]["state"] == "open"


async def test_future_timestamp_prevents_auto_resolve():
    store = MemoryScanStore()
    await _scan_no_up(store, rows=[_no_up_row("R1", 500.0)], scan_id="scan-hit5")
    alert = _only_alert(store)

    row = _no_up_row("R1", 0.5)
    row["create_date"] = (datetime.now(timezone.utc) + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
    result = await _scan_no_up(store, rows=[row], scan_id="scan-future")
    assert result["counts"]["alertsAutoResolved"] == 0
    assert store.alerts[alert["alertId"]]["state"] == "open"


# ---------------------------------------------------------------------------
# 4. 乱序扫描不关
# ---------------------------------------------------------------------------


async def test_alert_refreshed_by_newer_scan_is_not_closed():
    store = MemoryScanStore()
    # 告警的最后出现时间晚于本次扫描开始时间 → 说明它被更新的扫描续期过，本次不能关
    alert_id = await _seed_alert(
        store,
        fingerprint="fp-order",
        object_id="N-1|G-1|T-1",
        last_seen_at=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    )
    result = await _scan_no_up(store, rows=[_no_up_row("R1", 0.5)], scan_id="scan-old")
    assert result["counts"]["alertsAutoResolved"] == 0
    assert store.alerts[alert_id]["state"] == "open"


# ---------------------------------------------------------------------------
# 5. ignored 终态不复活
# ---------------------------------------------------------------------------


async def test_ignored_alert_is_not_auto_resolved():
    store = MemoryScanStore()
    await _scan_no_up(store, rows=[_no_up_row("R1", 500.0)], scan_id="scan-hit6")
    alert = _only_alert(store)
    ignored = await store.transition_alert(
        alert["alertId"],
        "ignored",
        reason="人工忽略",
        ignored_until=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        actor_type="user",
        actor_id="tester",
    )
    assert ignored is not None
    assert store.alerts[alert["alertId"]]["state"] == "ignored"

    result = await _scan_no_up(store, rows=[_no_up_row("R1", 0.5)], scan_id="scan-ignored")
    assert result["counts"]["alertsAutoResolved"] == 0
    assert store.alerts[alert["alertId"]]["state"] == "ignored"


# ---------------------------------------------------------------------------
# 6. 条件复发新建
# ---------------------------------------------------------------------------


async def test_recurrence_creates_new_alert_after_resolution():
    store = MemoryScanStore()
    await _scan_no_up(store, rows=[_no_up_row("R1", 500.0)], scan_id="scan-rec-1")
    first_alert = _only_alert(store)
    await _scan_no_up(store, rows=[_no_up_row("R1", 0.5)], scan_id="scan-rec-2")
    assert store.alerts[first_alert["alertId"]]["state"] == "resolved"

    # 条件复发 → 新建告警
    await _scan_no_up(store, rows=[_no_up_row("R1", 500.0)], scan_id="scan-rec-3")
    active = [
        a
        for a in store.alerts.values()
        if a["ruleId"] == "NOUP-OVERDUE" and a["state"] in ("open", "acknowledged")
    ]
    assert len(active) == 1
    assert active[0]["alertId"] != first_alert["alertId"]


# ---------------------------------------------------------------------------
# 7. 用户操作与自动关闭并发
# ---------------------------------------------------------------------------


async def test_user_resolution_wins_over_auto_resolve():
    store = MemoryScanStore()
    await _scan_no_up(store, rows=[_no_up_row("R1", 500.0)], scan_id="scan-race")
    alert = _only_alert(store)
    resolved = await store.transition_alert(
        alert["alertId"],
        "resolved",
        reason="人工处理",
        actor_type="user",
        actor_id="tester",
    )
    assert resolved is not None

    result = await _scan_no_up(store, rows=[_no_up_row("R1", 0.5)], scan_id="scan-race-2")
    assert result["counts"]["alertsAutoResolved"] == 0
    assert [e for e in store.events if e["eventType"] == AUTO_RESOLVE_EVENT] == []
    assert store.alerts[alert["alertId"]]["state"] == "resolved"


async def test_auto_resolve_is_not_repeatable():
    store = MemoryScanStore()
    alert_id = await _seed_alert(store, fingerprint="fp-race2", object_id="N-1|G-1|T-1")
    now_iso = datetime.now(timezone.utc).isoformat()
    closed = await store.auto_resolve_alert(
        alert_id,
        reason="条件消失",
        scan_id="scan-race2",
        trace_id="trace-race2",
        before_iso=now_iso,
        rule_id="NOUP-OVERDUE",
        rule_version="v0.2.0",
        warehouse="W01",
    )
    assert closed is True
    again = await store.auto_resolve_alert(
        alert_id,
        reason="条件消失",
        scan_id="scan-race2",
        trace_id="trace-race2",
        before_iso=now_iso,
        rule_id="NOUP-OVERDUE",
        rule_version="v0.2.0",
        warehouse="W01",
    )
    assert again is False
    auto_events = [e for e in store.events if e["eventType"] == AUTO_RESOLVE_EVENT]
    assert len(auto_events) == 1


async def test_auto_resolve_rejects_rule_version_mismatch():
    store = MemoryScanStore()
    alert_id = await _seed_alert(
        store,
        fingerprint="fp-ver",
        object_id="N-1|G-1|T-1",
        rule_version="v0.1.0",
    )
    closed = await store.auto_resolve_alert(
        alert_id,
        reason="条件消失",
        scan_id="scan-ver",
        trace_id="trace-ver",
        before_iso=datetime.now(timezone.utc).isoformat(),
        rule_id="NOUP-OVERDUE",
        rule_version="v0.2.0",
        warehouse="W01",
    )
    assert closed is False
    assert store.alerts[alert_id]["state"] == "open"


async def test_auto_resolve_rejects_other_warehouse():
    store = MemoryScanStore()
    alert_id = await _seed_alert(
        store,
        fingerprint="fp-wh",
        object_id="N-1|G-1|T-1",
        warehouse="W02",
    )
    closed = await store.auto_resolve_alert(
        alert_id,
        reason="条件消失",
        scan_id="scan-wh",
        trace_id="trace-wh",
        before_iso=datetime.now(timezone.utc).isoformat(),
        rule_id="NOUP-OVERDUE",
        rule_version="v0.2.0",
        warehouse="W01",
    )
    assert closed is False
    assert store.alerts[alert_id]["state"] == "open"


# ---------------------------------------------------------------------------
# 8. fake clock：调度窗口边界 / 重启 / 重复槽
# ---------------------------------------------------------------------------


def _scheduler_config(tmp_path, *, enabled: bool = True, cron: str = "*/15 7-23 * * *"):
    import yaml

    document = {
        "version": "v0.2.0",
        "warehouses": ["W01"],
        "scan": {
            "pageSize": 100,
            "maxPages": 20,
            "requestTimeoutSeconds": 3,
            "sourceBudgetSeconds": 30,
            "scanBudgetSeconds": 120,
            "concurrency": 1,
        },
        "rules": {
            "expiry": {"expiredDays": 0, "nearDays": 7, "nearRatio": 0.3333, "watchDays": 30},
            "noUp": {"p0Hours": 8, "p1Hours": 4, "p2Hours": 2},
            "delay": {"p0Hours": 24, "p1Hours": 2, "p2Hours": 0},
            "backlog": {"growthRatio": 0.30, "absoluteDelta": 10, "baselineScans": 3, "consecutiveForP1": 3},
        },
        "routing": [],
        "notifications": {"mode": "dry_run", "recipients": []},
        "schedule": {"enabled": enabled, "scanTypes": ["expiry"], "cron": cron, "timezone": "Asia/Shanghai"},
    }
    path = tmp_path / "scan.yaml"
    path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return load_scan_config(path)


def test_current_slot_inside_window_and_aligned():
    slot = current_slot(datetime(2026, 11, 25, 7, 0, tzinfo=SHANGHAI), "Asia/Shanghai", "*/15 7-23 * * *")
    assert slot is not None
    assert slot.slot_id == "20261125T0700"


def test_current_slot_outside_window_is_none():
    # 窗口按小时判定：07:00–23:00 闭区间
    assert current_slot(datetime(2026, 11, 25, 3, 0, tzinfo=SHANGHAI), "Asia/Shanghai", "*/15 7-23 * * *") is None
    assert current_slot(datetime(2026, 11, 25, 6, 45, tzinfo=SHANGHAI), "Asia/Shanghai", "*/15 7-23 * * *") is None
    # 上界闭区间：23:45 仍在窗口内
    upper = current_slot(datetime(2026, 11, 25, 23, 45, tzinfo=SHANGHAI), "Asia/Shanghai", "*/15 7-23 * * *")
    assert upper is not None and upper.slot_id == "20261125T2345"


def test_current_slot_minute_must_align():
    assert current_slot(datetime(2026, 11, 25, 7, 7, tzinfo=SHANGHAI), "Asia/Shanghai", "*/15 7-23 * * *") is None


def test_parse_scan_cron_rejects_invalid_expressions():
    assert parse_scan_cron("*/15 7-23 * * *") == ScanCron(minute_step=15, hour_start=7, hour_end=23)
    with pytest.raises(ValueError):
        parse_scan_cron("0 7-23 * * *")
    with pytest.raises(ValueError):
        parse_scan_cron("*/15 7-23 * * 1")
    with pytest.raises(ValueError):
        parse_scan_cron("*/7 7-23 * * *")
    with pytest.raises(ValueError):
        parse_scan_cron("*/15 24-23 * * *")


async def test_scheduler_disabled_does_not_enqueue(tmp_path):
    store = MemoryScanStore()
    config = _scheduler_config(tmp_path, enabled=False)
    scheduler = ScanScheduler(store, _settings(), config, clock=lambda: datetime.now(timezone.utc))
    assert scheduler.enabled is False
    assert await scheduler.tick() is None
    assert store.runs == {}


async def test_scheduler_enqueues_once_per_slot(tmp_path):
    store = MemoryScanStore()
    config = _scheduler_config(tmp_path, enabled=True)
    moment = datetime(2026, 11, 25, 14, 30, tzinfo=SHANGHAI)
    scheduler = ScanScheduler(store, _settings(), config, clock=lambda: moment)
    slot_id = await scheduler.tick()
    assert slot_id == "20261125T1430"
    assert len(store.runs) == 1
    run = next(iter(store.runs.values()))
    assert run["scheduleSlot"] == "20261125T1430"
    assert run["trigger"] == "schedule"
    assert run["actorType"] == "service"
    assert run["configSnapshot"]
    assert run["configVersion"] == "v0.2.0"

    # 同一槽位重复 tick → 不重复入队
    assert await scheduler.tick() is None
    assert len(store.runs) == 1


async def test_scheduler_restart_same_slot_is_deduplicated(tmp_path):
    store = MemoryScanStore()
    config = _scheduler_config(tmp_path, enabled=True)
    moment = datetime(2026, 11, 25, 14, 30, tzinfo=SHANGHAI)
    first = ScanScheduler(store, _settings(), config, clock=lambda: moment)
    await first.tick()
    # 模拟进程重启：新实例、同一槽位 → 唯一索引幂等
    second = ScanScheduler(store, _settings(), config, clock=lambda: moment)
    slot_id = await second.tick()
    assert slot_id == "20261125T1430"
    assert len(store.runs) == 1


async def test_scheduler_skips_slot_outside_window(tmp_path):
    store = MemoryScanStore()
    config = _scheduler_config(tmp_path, enabled=True)
    moment = datetime(2026, 11, 25, 2, 30, tzinfo=SHANGHAI)
    scheduler = ScanScheduler(store, _settings(), config, clock=lambda: moment)
    assert await scheduler.tick() is None
    assert store.runs == {}


async def test_scheduler_does_not_backfill_missed_slots(tmp_path):
    store = MemoryScanStore()
    config = _scheduler_config(tmp_path, enabled=True)
    # 服务在 14:47 才起来 → 当前槽位不对齐 → 不入队，更不补跑 14:30
    moment = datetime(2026, 11, 25, 14, 47, tzinfo=SHANGHAI)
    scheduler = ScanScheduler(store, _settings(), config, clock=lambda: moment)
    assert await scheduler.tick() is None
    assert store.runs == {}


# ---------------------------------------------------------------------------
# 9. 调度默认关闭
# ---------------------------------------------------------------------------


def test_schedule_disabled_by_default_in_repo_config():
    from pathlib import Path

    repo_config = Path(__file__).resolve().parents[1] / "config" / "scan.yaml"
    loaded = load_scan_config(repo_config)
    assert loaded.document.schedule.enabled is False
    assert loaded.document.schedule.scanTypes == ["expiry", "no_up", "delay", "backlog"]


# ---------------------------------------------------------------------------
# 10. retry 复用原配置快照
# ---------------------------------------------------------------------------


def _admin(name: str = "admin", user_id: str = "a-1") -> Principal:
    return Principal(user_id=user_id, user_name=name, authorities=("gly",))


def _origin_run(scan_id: str, **overrides) -> dict:
    """一条可重试的原扫描记录：默认由管理员 admin 本人发起，且带配置快照。"""
    run = {
        "scanId": scan_id,
        "trigger": "manual",
        "actorType": "user",
        "actorId": "admin",
        "actorUserId": "a-1",
        "status": "succeeded",
        "configHash": "sha256:deadbeef",
        "configSnapshot": '{"version":"v0.2.0","rules":{"noUp":{"p0Hours":3}}}',
        "configVersion": "v0.2.0",
        "ruleVersion": "no_up=v0.2.0",
        "scanTypes": ["no_up"],
        "scanKey": scan_id,
        "warehouse": "W01",
        "notificationMode": "dry_run",
        "dryRun": False,
        "payloadHash": "sha256:payload",
        "traceId": "trace-" + scan_id,
    }
    run.update(overrides)
    return run


async def test_retry_reuses_original_config_snapshot():
    store = MemoryScanStore()
    original = _origin_run("scan-origin")
    await store.insert_run(original)
    client = _client(_admin(), store)
    response = client.post("/agent/scans/scan-origin/retry")
    assert response.status_code == 202
    body = response.json()
    assert body["data"]["retryOf"] == "scan-origin"
    assert body["data"]["configHash"] == original["configHash"]

    new_run = await store.get_run(body["data"]["scanId"])
    assert new_run["configSnapshot"] == original["configSnapshot"]
    assert new_run["configHash"] == original["configHash"]
    assert new_run["configVersion"] == "v0.2.0"
    assert new_run["scanTypes"] == ["no_up"]
    assert new_run["warehouse"] == "W01"
    assert new_run["scanId"] != "scan-origin"
    assert new_run["traceId"] != "trace-origin"
    # 审计归属（V010）：记录谁点了重试；根来源是原扫描自己的发起人与触发方式
    assert body["data"]["trigger"] == "retry"
    assert new_run["trigger"] == "retry"
    assert new_run["actorType"] == "user" and new_run["actorId"] == "admin"
    assert new_run["actorUserId"] == "a-1"
    assert new_run["retryOfScanId"] == "scan-origin"
    assert new_run["originActorType"] == "user"
    assert new_run["originActorId"] == "admin"
    assert new_run["originTrigger"] == "manual"


async def test_retry_of_retry_points_to_previous_and_keeps_root_origin():
    """链式重试：每条重试指向被重试的那一条；根来源始终是首次触发的人/服务与方式。"""
    store = MemoryScanStore()
    await store.insert_run(_origin_run(
        "scan-slot", trigger="schedule", actorType="service",
        actorId="agent-inspector", actorUserId=None,
    ))
    client = _client(_admin(), store)
    first = client.post("/agent/scans/scan-slot/retry").json()["data"]
    first_run = await store.get_run(first["scanId"])
    assert first_run["retryOfScanId"] == "scan-slot"

    second = client.post(f"/agent/scans/{first['scanId']}/retry")
    assert second.status_code == 202
    second_run = await store.get_run(second.json()["data"]["scanId"])
    assert second_run["trigger"] == "retry"
    assert second_run["retryOfScanId"] == first["scanId"]
    assert second_run["actorType"] == "user" and second_run["actorId"] == "admin"
    # 根来源不会被链式重试改写成「上一条重试」
    assert second_run["originActorType"] == "service"
    assert second_run["originActorId"] == "agent-inspector"
    assert second_run["originTrigger"] == "schedule"


async def test_retry_record_belongs_to_the_admin_who_retried():
    """重试记录归发起重试的管理员；别的管理员不能重试它，但可以直接重试那条服务账号扫描。"""
    store = MemoryScanStore()
    await store.insert_run(_origin_run(
        "scan-slot", trigger="schedule", actorType="service",
        actorId="agent-inspector", actorUserId=None,
    ))
    first = _client(_admin(), store).post("/agent/scans/scan-slot/retry").json()["data"]
    other = _admin(name="other-admin", user_id="a-2")
    denied = _client(other, store).post(f"/agent/scans/{first['scanId']}/retry")
    assert denied.status_code == 403
    assert denied.json()["message"] == "无权重试该扫描：原扫描不属于当前用户"
    assert _client(other, store).post("/agent/scans/scan-slot/retry").status_code == 202


async def test_enqueue_rejects_retry_without_retry_of():
    """不允许出现「标成重试却追溯不到原扫描」的记录。"""
    with pytest.raises(ValueError, match="retry_of"):
        await enqueue_scan(
            MemoryScanStore(), principal=_admin(), scan_types=["no_up"], warehouse="W01",
            config_snapshot="{}", config_hash_value="sha256:x", config_version="v0.2.0",
            notification_mode="dry_run", trigger="retry",
        )


async def test_retry_by_admin_keeps_scheduled_scan_config_and_flags():
    store = MemoryScanStore()
    original = _origin_run(
        "scan-slot",
        status="failed",
        trigger="schedule",
        actorType="service",
        actorId="agent-inspector",
        actorUserId=None,
        scanTypes=["expiry", "backlog"],
        scheduleSlot="20261125T1730",
        notificationMode="dry_run",
        dryRun=True,
    )
    await store.insert_run(original)
    response = _client(_admin(), store).post("/agent/scans/scan-slot/retry")
    assert response.status_code == 202

    new_run = await store.get_run(response.json()["data"]["scanId"])
    # 复用项：配置快照、规则类型、通知模式、dryRun
    assert new_run["scanTypes"] == ["expiry", "backlog"]
    assert new_run["configSnapshot"] == original["configSnapshot"]
    assert new_run["configVersion"] == "v0.2.0"
    assert new_run["warehouse"] == "W01"
    assert new_run["notificationMode"] == "dry_run"
    assert new_run["dryRun"] is True
    # 重试是一条新的扫描：归属发起重试的管理员（trigger=retry），不复用调度槽位；
    # 根来源保留定时扫描的服务身份，不冒充它。
    assert new_run["trigger"] == "retry"
    assert new_run["actorType"] == "user"
    assert new_run["actorId"] == "admin"
    assert new_run["actorUserId"] == "a-1"
    assert new_run["retryOfScanId"] == "scan-slot"
    assert new_run["originActorType"] == "service"
    assert new_run["originActorId"] == "agent-inspector"
    assert new_run["originTrigger"] == "schedule"
    assert not new_run.get("scheduleSlot")


async def test_executed_retry_keeps_attribution_and_records_service_executor():
    """worker 执行重试记录：归属字段原样保留，执行者仍由服务令牌决定。"""
    store = MemoryScanStore()
    await store.insert_run(_origin_run("scan-origin", status="failed"))
    queued = _client(_admin(), store).post("/agent/scans/scan-origin/retry").json()["data"]
    claimed = await store.claim_next_queued("worker-1")
    assert claimed is not None and claimed["scanId"] == queued["scanId"]

    await run_scan(
        scan_id=claimed["scanId"],
        scan_types=["no_up"],
        principal=_service(),
        token=TOKEN,
        client=_gateway(lambda request: _ok(_page([]))),
        store=store,
        allowed_warehouses=["W01"],
        notification_mode="dry_run",
        executor_type="service",
        executor_id="agent-inspector",
        actor_type=claimed.get("actorType"),
        trigger=claimed.get("trigger"),
        actor_id=claimed.get("actorId"),
        claimed=claimed,
        lease_owner="worker-1",
    )

    done = await store.get_run(claimed["scanId"])
    assert done["status"] == "succeeded"
    assert done["trigger"] == "retry" and done["retryOfScanId"] == "scan-origin"
    assert done["actorType"] == "user" and done["actorId"] == "admin"
    assert done["actorUserId"] == "a-1" and done["originTrigger"] == "manual"
    assert done["executorType"] == "service" and done["executorId"] == "agent-inspector"


async def test_retry_without_snapshot_returns_conflict():
    store = MemoryScanStore()
    await store.insert_run(_origin_run("scan-legacy", configSnapshot=None, configVersion=None))
    response = _client(_admin(), store).post("/agent/scans/scan-legacy/retry")
    assert response.status_code == 409


async def test_retry_unknown_scan_returns_not_found():
    store = MemoryScanStore()
    response = _client(_admin(), store).post("/agent/scans/scan-missing/retry")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "label, principal",
    [
        ("ckjl", _user("ckjl001", authorities=("ckjl",))),
        ("cg", _user("cg001", authorities=("cg",))),
        ("unrelated_role", _user("cw001", authorities=("cw",))),
        ("trigger_permission_code", _user("op001", authorities=("inspection:scan:trigger",))),
        ("read_only_code", _user("ro001", authorities=("insp_read",))),
        ("service_account", _service()),
    ],
)
async def test_retry_is_admin_only(label, principal):
    """retry 是管理员接口：能发起扫描（can_trigger_scan）不等于能重试扫描。"""
    store = MemoryScanStore()
    # 原扫描归属调用方本人，仍然 403。
    await store.insert_run(_origin_run("scan-mine", actorId=principal.user_name))
    response = _client(principal, store).post("/agent/scans/scan-mine/retry")
    assert response.status_code == 403, label
    assert response.json()["code"] == 9997
    assert response.json()["message"] == "仅管理员可重试扫描"
    assert list(store.runs) == ["scan-mine"]


async def test_retry_rejects_service_account_even_for_scheduled_scan():
    store = MemoryScanStore()
    await store.insert_run(
        _origin_run(
            "scan-slot",
            trigger="schedule",
            actorType="service",
            actorId="agent-inspector",
            actorUserId=None,
        )
    )
    response = _client(_service(), store).post("/agent/scans/scan-slot/retry")
    assert response.status_code == 403
    assert response.json()["message"] == "仅管理员可重试扫描"
    assert list(store.runs) == ["scan-slot"]


async def test_retry_rejects_other_users_manual_scan():
    store = MemoryScanStore()
    await store.insert_run(_origin_run("scan-other", actorId="other", actorUserId="u-2"))
    response = _client(_admin(), store).post("/agent/scans/scan-other/retry")
    assert response.status_code == 403
    assert response.json()["code"] == 9997
    assert response.json()["message"] == "无权重试该扫描：原扫描不属于当前用户"
    assert list(store.runs) == ["scan-other"]


async def test_retry_rejects_scan_outside_token_warehouse_scope():
    store = MemoryScanStore()
    await store.insert_run(_origin_run("scan-w1", warehouse="W01"))
    scoped_admin = Principal(
        user_id="a-1", user_name="admin", authorities=("gly",), warehouse_scope=("W02",)
    )
    response = _client(scoped_admin, store).post("/agent/scans/scan-w1/retry")
    assert response.status_code == 403
    assert list(store.runs) == ["scan-w1"]


async def test_retry_by_admin_does_not_reveal_scan_existence_to_non_admin():
    """非管理员探测他人扫描：得到的是管理员限制的 403，而不是 404/409。"""
    store = MemoryScanStore()
    await store.insert_run(_origin_run("scan-other", actorId="other"))
    probe = _client(_user("ckjl001", authorities=("ckjl",)), store)
    existing = probe.post("/agent/scans/scan-other/retry")
    missing = probe.post("/agent/scans/scan-missing/retry")
    assert existing.status_code == missing.status_code == 403
    assert existing.json() == missing.json()
    assert list(store.runs) == ["scan-other"]


# ---------------------------------------------------------------------------
# enqueue_scan 幂等
# ---------------------------------------------------------------------------


async def test_enqueue_scan_is_idempotent_for_same_schedule_slot():
    store = MemoryScanStore()
    principal = _service()
    run_a, outcome_a = await enqueue_scan(
        store,
        principal=principal,
        scan_types=["expiry"],
        warehouse="W01",
        config_snapshot="{}",
        config_hash_value="h",
        config_version="v0.2.0",
        notification_mode="dry_run",
        schedule_slot="20261125T1430",
    )
    assert outcome_a == "created"
    run_b, outcome_b = await enqueue_scan(
        store,
        principal=principal,
        scan_types=["expiry"],
        warehouse="W01",
        config_snapshot="{}",
        config_hash_value="h",
        config_version="v0.2.0",
        notification_mode="dry_run",
        schedule_slot="20261125T1430",
    )
    assert outcome_b == "idempotent"
    assert run_b["scanId"] == run_a["scanId"]
    assert len(store.runs) == 1


async def test_enqueue_scan_records_snapshot_and_version():
    store = MemoryScanStore()
    snapshot = '{"version":"v0.2.0"}'
    run, outcome = await enqueue_scan(
        store,
        principal=_user(),
        scan_types=["expiry"],
        warehouse="W01",
        config_snapshot=snapshot,
        config_hash_value="sha256:abc",
        config_version="v0.2.0",
        notification_mode="dry_run",
        request_id="req-1",
        actor_user_id="u-1",
    )
    assert outcome == "created"
    assert run["configSnapshot"] == snapshot
    assert run["configVersion"] == "v0.2.0"
    assert run["configHash"] == "sha256:abc"
    assert run["actorUserId"] == "u-1"
