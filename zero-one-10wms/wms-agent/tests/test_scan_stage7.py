"""阶段7：巡检指标（管理员只读 ``GET /agent/scan/metrics``）。

覆盖四层：
1. 纯函数口径（app/scan/metrics.py）：时间窗左闭右开、终态扫描才汇总 counts、
   事件类计数、活跃快照、认领 / 关闭时长、通知与 LLM 用量；
2. Memory 存储聚合与事件时间（PG 同口径的契约测试在 test_scan_store_contract.py）；
3. API 权限与参数：仅管理员、hours 边界、仓库按令牌范围收敛、存储故障 503；
4. 取数耗时写入 sourceStatus.durationMs；
5. 保留与归档（ADR-020）：策略校验、一轮执行的顺序与计数、限批与可重入、每日调度、
   管理员接口权限（PG 同口径的契约测试在 test_scan_store_contract.py）。
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, time as dtime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.config import Settings
from app.scan import router as scan_router
from app.scan.metrics import _distribution, build_metrics
from app.scan.repository import (
    ARCHIVE_TABLE_ALERTS,
    ARCHIVE_TABLE_EVENTS,
    ARCHIVE_TABLE_NOTIFICATIONS,
    ARCHIVE_TABLE_SCAN_RUNS,
    MemoryScanStore,
    ScanStoreUnavailableError,
)
from app.scan.retention import (
    RetentionError,
    RetentionPolicy,
    RetentionScheduler,
    parse_daily_at,
    run_retention,
)
from app.scan.service import run_scan
from app.scan.sources.base import SourceResult
from app.security import Principal, require_principal
from app.tools.gateway_client import GatewayClient

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
LO = NOW - timedelta(hours=24)
TOKEN = "token"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _user(
    name: str = "tester", authorities: tuple[str, ...] = ("ckjl",), user_id: str = "u-1",
    **extra: Any,
) -> Principal:
    return Principal(user_id=user_id, user_name=name, authorities=authorities, **extra)


def _admin(name: str = "admin", user_id: str = "a-1", **extra: Any) -> Principal:
    return Principal(user_id=user_id, user_name=name, authorities=("gly",), **extra)


def _service(warehouse: str = "W01") -> Principal:
    return Principal(
        user_id="agent-inspector", user_name="agent-inspector", authorities=("insp_read",),
        warehouse_scope=(warehouse,), token_use="agent_service",
    )


def _run(
    scan_id: str, *, started: datetime, finished: datetime | None = None,
    status: str = "succeeded", trigger: str = "manual", partial: bool = False,
    sources: list[dict[str, Any]] | None = None, counts: dict[str, Any] | None = None,
    error: str | None = None, warehouse: str = "W01",
) -> dict[str, Any]:
    return {
        "scanId": scan_id, "trigger": trigger, "status": status, "partial": partial,
        "startedAt": started.isoformat(),
        "finishedAt": finished.isoformat() if finished is not None else None,
        "sourceStatus": sources or [], "counts": counts or {}, "errorSummary": error,
        "warehouse": warehouse,
    }


def _alert(
    alert_id: int, state: str, severity: str, rule: str, *, first_seen: datetime | None = None,
    claimed: datetime | None = None, resolved: datetime | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "alertId": alert_id, "state": state, "severity": severity, "ruleId": rule,
        "firstSeenAt": first_seen.isoformat() if first_seen else None,
        "claimedAt": claimed.isoformat() if claimed else None,
        "resolvedAt": resolved.isoformat() if resolved else None,
        "resolvedReason": reason,
    }


def _metrics(
    *, runs: list[dict[str, Any]] | None = None,
    event_counts: list[dict[str, Any]] | None = None,
    alerts: list[dict[str, Any]] | None = None,
    notification_counts: list[dict[str, Any]] | None = None,
    summary_counts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return build_metrics(
        runs=runs or [], event_counts=event_counts or [], alerts=alerts or [],
        notification_counts=notification_counts or [],
        summary_counts=summary_counts or [],
        window_from=LO, window_to=NOW, generated_at=NOW,
    )


def _alert_row(fp: str = "fp-1", severity: str = "P1", **overrides: Any) -> dict[str, Any]:
    alert = {
        "fingerprint": fp, "ruleId": "NOUP-OVERDUE", "ruleVersion": "v0.2.0",
        "severity": severity, "objectType": "no_up_goods", "objectId": f"N-{fp}|G-{fp}|T-{fp}",
        "dimension": {"warehouse": "W01", "customer": "C1"}, "title": f"NOUP-OVERDUE {severity}",
        "evidence": {"ageHours": 9}, "suggestedActions": ["MOVE_TO_BIN"],
        "warehouseId": "W01", "scanId": "scan-metrics", "traceId": "trace-metrics",
        "lastSeenAt": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
    }
    alert.update(overrides)
    return alert


def _stored_run(scan_id: str, *, started: datetime, status: str = "succeeded") -> dict[str, Any]:
    return {
        "scanId": scan_id, "trigger": "manual", "actorType": "user", "actorId": "admin",
        "status": status, "partial": False, "sourceStatus": [], "configHash": "h",
        "ruleVersion": "no_up=v0.2.0", "scanTypes": ["no_up"], "requestId": None,
        "scheduleSlot": None, "scanKey": scan_id, "queuedAt": started.isoformat(),
        "startedAt": started.isoformat(), "finishedAt": None, "attempt": 0, "counts": {},
        "errorSummary": None, "warehouse": "W01", "dryRun": True,
        "notificationMode": "dry_run", "payloadHash": "sha256:p", "traceId": "trace-metrics",
    }


def _client(principal: Principal, store: Any) -> TestClient:
    from app.main import create_app

    app = create_app()
    app.state.scan_store = store
    app.dependency_overrides[require_principal] = lambda: principal
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    return TestClient(app)


def _ok(data: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json={"code": 10000, "data": data})


def _page(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"rows": rows, "total": len(rows), "pages": 1}


def _no_up_row(row_id: str, age_hours: float) -> dict[str, Any]:
    created = datetime.now(timezone.utc).astimezone() - timedelta(hours=age_hours)
    return {
        "rowId": row_id, "noticeId": f"N-{row_id}", "goods_id": f"G-{row_id}",
        "tin_id": f"T-{row_id}", "cus_code": "C1", "shp_ming_cheng": "小蓝管",
        "create_date": created.strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# 1. 纯函数口径
# ---------------------------------------------------------------------------


def test_distribution_uses_nearest_rank_and_reports_missing_samples() -> None:
    assert _distribution([]) == {"samples": 0, "avg": None, "p50": None, "p90": None, "max": None}
    ten = _distribution([10, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert ten == {"samples": 10, "avg": 5.5, "p50": 5, "p90": 9, "max": 10}
    assert _distribution([3]) == {"samples": 1, "avg": 3.0, "p50": 3, "p90": 3, "max": 3}


def test_metrics_sums_counts_of_terminal_runs_only() -> None:
    # 时间窗的筛选由存储层完成（见下方 Memory / 契约测试）；build_metrics 只解释已入窗的行。
    runs = [
        _run("first", started=LO, finished=LO + timedelta(seconds=2), trigger="retry"),
        _run(
            "failed", started=LO + timedelta(hours=1), status="failed",
            error="auth_failed:token_missing",
            counts={"alertsSuppressed": 3, "llmCalls": 2, "llmFailures": 1},
        ),
        _run("running", started=LO + timedelta(hours=2), status="running", counts={"alertsSuppressed": 100}),
        _run(
            "ok", started=LO + timedelta(hours=3),
            finished=LO + timedelta(hours=3, seconds=4), trigger="schedule", partial=True,
        ),
    ]
    metrics = _metrics(runs=runs)
    scans = metrics["scans"]
    assert scans["total"] == 4  # first / failed / running / ok
    assert (scans["succeeded"], scans["failed"], scans["cancelled"], scans["inProgress"]) == (2, 1, 0, 1)
    assert scans["partial"] == 1
    assert scans["byTrigger"] == {"manual": 2, "schedule": 1, "retry": 1}
    assert scans["durationSeconds"] == {"samples": 2, "avg": 3.0, "p50": 2.0, "p90": 4.0, "max": 4.0}
    assert scans["failures"] == [{"errorSummary": "auth_failed:token_missing", "count": 1}]
    # counts 只汇总终态扫描：在途扫描里的 100 不计入
    assert metrics["alerts"]["suppressed"] == 3
    assert (metrics["llm"]["calls"], metrics["llm"]["failures"]) == (2, 1)
    assert metrics["window"] == {"from": LO.isoformat(), "to": NOW.isoformat(), "hours": 24.0}
    assert metrics["generatedAt"] == NOW.isoformat()


def test_metrics_sources_aggregate_status_rows_and_timing() -> None:
    runs = [
        _run("a", started=LO, sources=[
            {"source": "expiry", "status": "ok", "rows": 6, "durationMs": 88},
            {"source": "no_up", "status": "timeout", "rows": 0, "durationMs": 3000},
        ]),
        _run("b", started=LO, sources=[
            {"source": "expiry", "status": "partial", "rows": 201, "durationMs": 120},
        ]),
        _run("c", started=LO, sources=[{"source": "backlog", "status": "ok", "rows": 1}]),
        _run("d", started=LO, sources=[{"source": "delay", "status": "error", "rows": 0, "durationMs": 50}]),
    ]
    sources = _metrics(runs=runs)["sources"]
    assert list(sources) == ["backlog", "delay", "expiry", "no_up"]
    assert sources["expiry"] == {
        "scans": 2, "ok": 1, "partial": 1, "error": 0, "timeout": 0, "rows": 207,
        "avgRows": 103.5, "avgDurationMs": 104.0, "maxDurationMs": 120.0, "withoutTiming": 0,
    }
    # 历史扫描没有取数耗时：计入 withoutTiming，不猜测
    assert sources["backlog"] == {
        "scans": 1, "ok": 1, "partial": 0, "error": 0, "timeout": 0, "rows": 1,
        "avgRows": 1.0, "avgDurationMs": None, "maxDurationMs": None, "withoutTiming": 1,
    }
    assert (sources["no_up"]["timeout"], sources["no_up"]["maxDurationMs"]) == (1, 3000.0)
    assert sources["delay"]["error"] == 1


def test_metrics_alert_handling_comes_from_events_and_active_snapshot() -> None:
    event_counts = [
        {"eventType": "created", "fromState": None, "toState": "open", "count": 2},
        {"eventType": "created", "fromState": None, "toState": "open", "count": 3},
        {"eventType": "escalated", "fromState": "open", "toState": "open", "count": 2},
        {"eventType": "condition_cleared", "fromState": "open", "toState": "resolved", "count": 1},
        {"eventType": "condition_cleared", "fromState": "acknowledged", "toState": "resolved", "count": 3},
        {"eventType": "claimed", "fromState": "open", "toState": "open", "count": 3},
        {"eventType": "transition", "fromState": "open", "toState": "acknowledged", "count": 1},
        {"eventType": "transition", "fromState": "acknowledged", "toState": "resolved", "count": 2},
        {"eventType": "transition", "fromState": "open", "toState": "ignored", "count": 1},
    ]
    alerts = [
        _alert(1, "open", "P0", "EXP-EXPIRED"),
        _alert(2, "acknowledged", "P2", "NOUP-OVERDUE"),
        _alert(3, "open", "P0", "EXP-EXPIRED"),
        _alert(4, "resolved", "P1", "NOUP-OVERDUE", first_seen=NOW - timedelta(hours=3),
               resolved=NOW - timedelta(hours=1), reason="已处理"),
        _alert(5, "resolved", "P0", "NOUP-OVERDUE", first_seen=NOW - timedelta(minutes=30),
               resolved=NOW - timedelta(minutes=10),
               reason="condition_cleared: NOUP-OVERDUE 对象未再命中"),
        _alert(6, "resolved", "P2", "NOUP-OVERDUE", first_seen=NOW - timedelta(days=4),
               resolved=NOW - timedelta(days=2), reason="已处理"),
        _alert(7, "resolved", "P2", "NOUP-OVERDUE", first_seen=NOW - timedelta(minutes=5),
               resolved=NOW - timedelta(minutes=10), reason="时钟错乱"),
        _alert(8, "open", "P1", "NOUP-OVERDUE", first_seen=NOW - timedelta(hours=1),
               claimed=NOW - timedelta(minutes=5)),
        _alert(9, "open", "P1", "NOUP-OVERDUE", first_seen=NOW - timedelta(days=3),
               claimed=NOW - timedelta(days=2)),
    ]
    metrics = _metrics(event_counts=event_counts, alerts=alerts)
    alerts_metrics = metrics["alerts"]
    assert alerts_metrics["created"] == 5  # 同类分组求和
    assert alerts_metrics["escalated"] == 2
    assert alerts_metrics["autoResolved"] == 4
    assert (alerts_metrics["acknowledged"], alerts_metrics["closedManually"], alerts_metrics["ignored"]) == (1, 2, 1)
    assert (alerts_metrics["suppressed"], alerts_metrics["replayed"], alerts_metrics["staleCheckSkipped"]) == (0, 0, 0)
    # 活跃告警是当前快照：与时间窗无关；已认领但未关闭的（8、9）仍然是活跃告警
    assert alerts_metrics["active"] == {
        "total": 5, "open": 4, "acknowledged": 1,
        "bySeverity": {"P0": 2, "P1": 2, "P2": 1},
        "byRule": [{"ruleId": "NOUP-OVERDUE", "count": 3}, {"ruleId": "EXP-EXPIRED", "count": 2}],
    }
    handling = metrics["handling"]
    assert handling["claimed"] == 1  # 告警 8；告警 9 的认领在窗口外

    def one(value: float) -> dict[str, Any]:
        return {"samples": 1, "avg": value, "p50": value, "p90": value, "max": value}

    assert handling["claimDurationSeconds"] == one(3300.0)
    # 人工关闭：1 小时前关闭、首次发现 3 小时前 → 7200s；自动关闭：30 分钟前发现 → 1200s
    assert handling["resolveDurationSeconds"]["manual"] == one(7200.0)
    assert handling["resolveDurationSeconds"]["auto"] == one(1200.0)  # 负样本（告警 7）与窗口外（告警 6）被丢弃


def test_metrics_notifications_and_llm_breakdown() -> None:
    notification_counts = [
        {"status": "sent", "channel": "in_app", "createdInWindow": True, "readInWindow": True, "unreadNow": False, "count": 3},
        {"status": "sent", "channel": "in_app", "createdInWindow": True, "readInWindow": False, "unreadNow": True, "count": 2},
        {"status": "sent", "channel": "in_app", "createdInWindow": False, "readInWindow": True, "unreadNow": False, "count": 4},
        {"status": "pending", "channel": "email", "createdInWindow": True, "readInWindow": False, "unreadNow": True, "count": 1},
        {"status": "queued", "channel": "sms", "createdInWindow": True, "readInWindow": False, "unreadNow": True, "count": 2},
    ]
    runs = [_run("llm", started=LO, counts={
        "llmCalls": 5, "llmFailures": 2, "promptTokens": 462, "completionTokens": 90,
        "summariesLlm": 3, "summariesTemplate": 2, "notificationsUnrouted": 6,
    })]
    summary_counts = [
        {"summarySource": "llm", "fallbackReason": None, "model": "m-a", "summaries": 2, "promptTokens": 300, "completionTokens": 60},
        {"summarySource": "llm", "fallbackReason": None, "model": "m-b", "summaries": 1, "promptTokens": 162, "completionTokens": 30},
        {"summarySource": "template", "fallbackReason": "timeout", "model": None, "summaries": 2, "promptTokens": 0, "completionTokens": 0},
    ]
    metrics = _metrics(runs=runs, notification_counts=notification_counts, summary_counts=summary_counts)
    assert metrics["notifications"] == {
        "sent": 5, "pending": 1, "failed": 0, "other": 2,  # 窗口内创建：3+2 / 1 / 2
        "read": 7, "unread": 5, "unrouted": 6,  # 已读按已读时间入窗（含更早创建的 4 条）
    }
    assert metrics["llm"] == {
        "calls": 5, "failures": 2, "failureRate": 0.4,
        "promptTokens": 462, "completionTokens": 90,
        "summariesLlm": 3, "summariesTemplate": 2,
        "byModel": [
            {"model": "m-a", "summaries": 2, "promptTokens": 300, "completionTokens": 60},
            {"model": "m-b", "summaries": 1, "promptTokens": 162, "completionTokens": 30},
        ],
        "fallbackReasons": [{"reason": "timeout", "count": 2}],
    }


def test_metrics_empty_window_is_all_zero_without_errors() -> None:
    metrics = _metrics()
    assert metrics["scans"]["total"] == 0
    assert metrics["scans"]["durationSeconds"]["samples"] == 0
    assert metrics["scans"]["failures"] == []
    assert metrics["sources"] == {}
    assert metrics["alerts"]["active"] == {
        "total": 0, "open": 0, "acknowledged": 0,
        "bySeverity": {"P0": 0, "P1": 0, "P2": 0}, "byRule": [],
    }
    assert metrics["handling"]["claimed"] == 0
    assert metrics["notifications"] == {
        "sent": 0, "pending": 0, "failed": 0, "other": 0, "read": 0, "unread": 0, "unrouted": 0,
    }
    assert metrics["llm"]["failureRate"] == 0.0 and metrics["llm"]["byModel"] == []


# ---------------------------------------------------------------------------
# 2. Memory 存储聚合（事件必须带时间，否则按事件时间入窗会漏计）
# ---------------------------------------------------------------------------


async def test_memory_events_carry_created_at_and_are_windowed() -> None:
    store = MemoryScanStore()
    alert_id = (await store.upsert_alert(_alert_row("fp-1"))).alert_id
    assert alert_id == 1
    assert store.events and all(event["createdAt"] for event in store.events)

    to = datetime.now(timezone.utc) + timedelta(minutes=1)
    from_ = to - timedelta(hours=2)
    rows = await store.count_alert_events(
        created_from=from_.isoformat(), created_to=to.isoformat(), warehouses=["W01"],
    )
    assert sum(row["count"] for row in rows if row["eventType"] == "created") == 1
    # 窗口外（前天）不计数；仓库范围外也不计数
    assert await store.count_alert_events(
        created_from=(to - timedelta(days=2)).isoformat(),
        created_to=(to - timedelta(days=1)).isoformat(), warehouses=["W01"],
    ) == []
    assert await store.count_alert_events(
        created_from=from_.isoformat(), created_to=to.isoformat(), warehouses=["W02"],
    ) == []


async def test_memory_runs_follow_start_window_and_warehouse() -> None:
    store = MemoryScanStore()
    started = datetime.now(timezone.utc) - timedelta(minutes=20)
    await store.insert_run(_stored_run("scan-in", started=started))
    await store.insert_run(_stored_run("scan-old", started=started - timedelta(days=40)))
    await store.insert_run({**_stored_run("scan-w2", started=started), "warehouse": "W02"})
    to = datetime.now(timezone.utc) + timedelta(minutes=1)
    from_ = to - timedelta(hours=1)

    rows = await store.list_runs_for_metrics(
        started_from=from_.isoformat(), started_to=to.isoformat(), warehouses=["W01"],
    )
    assert [row["scanId"] for row in rows] == ["scan-in"]
    assert (rows[0]["status"], rows[0]["trigger"], rows[0]["partial"]) == ("succeeded", "manual", False)
    assert rows[0]["sourceStatus"] == [] and rows[0]["counts"] == {}
    everything = await store.list_runs_for_metrics(
        started_from=from_.isoformat(), started_to=to.isoformat(), warehouses=None,
    )
    assert [row["scanId"] for row in everything] == ["scan-in", "scan-w2"]


# ---------------------------------------------------------------------------
# 3. API：权限、参数、仓库范围、存储故障
# ---------------------------------------------------------------------------


def test_metrics_require_scan_admin() -> None:
    store = MemoryScanStore()
    for principal in (
        _user(),  # ckjl：可发起扫描、可看告警，但不是管理员
        _user("cg", authorities=("cg",)),
        _user("cw", authorities=("cw",)),
        _user("reader", authorities=("inspection:alert:view",)),
        _service(),
    ):
        body = _client(principal, store).get("/agent/scan/metrics").json()
        assert (body["code"], body["data"]) == (9997, None), principal.user_name
        assert body["message"] == "仅管理员可查看巡检指标"


def test_metrics_returns_the_document_for_admin() -> None:
    store = MemoryScanStore()
    data = _client(_admin(), store).get("/agent/scan/metrics?hours=6").json()
    assert data["code"] == 10000
    document = data["data"]
    assert set(document) == {
        "window", "generatedAt", "scans", "sources", "alerts", "handling", "notifications", "llm",
    }
    assert document["window"]["hours"] == 6.0
    assert document["scans"]["total"] == 0
    assert document["alerts"]["active"]["total"] == 0
    assert document["llm"]["failureRate"] == 0.0


@pytest.mark.parametrize("hours", [0, 0.5, -1, 24 * 730 + 1, 100000])
def test_metrics_reject_out_of_range_hours(hours: float) -> None:
    response = _client(_admin(), MemoryScanStore()).get(f"/agent/scan/metrics?hours={hours}")
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 9995 and "hours" in body["message"]


def test_metrics_accept_window_up_to_online_retention() -> None:
    response = _client(_admin(), MemoryScanStore()).get("/agent/scan/metrics?hours=2160")
    assert response.status_code == 200 and response.json()["data"]["window"]["hours"] == 2160.0


async def _seed(store: MemoryScanStore, started: datetime) -> None:
    await store.insert_run(_stored_run("scan-seed", started=started))
    await store.upsert_alert(_alert_row("fp-seed"))


async def test_metrics_reflect_seeded_scan_and_alert() -> None:
    store = MemoryScanStore()
    await _seed(store, datetime.now(timezone.utc) - timedelta(minutes=5))
    document = _client(_admin(), store).get("/agent/scan/metrics").json()["data"]
    assert document["scans"]["total"] == 1
    assert document["scans"]["succeeded"] == 1
    assert document["alerts"]["created"] == 1
    assert document["alerts"]["active"] == {
        "total": 1, "open": 1, "acknowledged": 0,
        "bySeverity": {"P0": 0, "P1": 1, "P2": 0},
        "byRule": [{"ruleId": "NOUP-OVERDUE", "count": 1}],
    }


def test_metrics_warehouse_is_limited_to_token_scope() -> None:
    store = MemoryScanStore()
    # 令牌范围 W01+W02：请求 W02 不在生效范围（配置只有 W01）内 → 拒绝
    scoped = _admin(warehouse_scope=("W01", "W02"))
    body = _client(scoped, store).get("/agent/scan/metrics?warehouse=W02").json()
    assert body == {
        "code": 9997, "message": "无权查看仓库 W02 的巡检指标", "data": None,
    }
    ok = _client(scoped, store).get("/agent/scan/metrics?warehouse=W01").json()
    assert ok["code"] == 10000
    # 令牌范围只含 W02：与配置没有交集 → 整体拒绝，不回落到全量
    alien = _admin(warehouse_scope=("W02",))
    rejected = _client(alien, store).get("/agent/scan/metrics").json()
    assert rejected["code"] == 9997 and rejected["data"] is None


def test_metrics_store_failure_is_unavailable_not_empty_success() -> None:
    class _FailingStore(MemoryScanStore):
        async def list_runs_for_metrics(self, **kwargs: Any) -> list[dict[str, Any]]:
            raise ScanStoreUnavailableError("list runs for metrics failed: OperationalError")

    response = _client(_admin(), _FailingStore()).get("/agent/scan/metrics")
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == 9998 and "巡检存储不可用" in body["message"]


# ---------------------------------------------------------------------------
# 4. 取数耗时写入 sourceStatus
# ---------------------------------------------------------------------------


async def _scan(store: MemoryScanStore, handler: Any) -> dict[str, Any]:
    return await run_scan(
        scan_id="scan-timing", scan_types=["no_up"], principal=_user(), token=TOKEN,
        client=GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler)),
        store=store, allowed_warehouses=["W01"], notification_mode="dry_run",
    )


def test_source_result_without_timing_reports_none() -> None:
    assert SourceResult("backlog", "/dashboard/query-pend-snapshot").to_status()["durationMs"] is None


async def test_scan_records_source_duration_in_source_status() -> None:
    async def slow(request: httpx.Request) -> httpx.Response:  # 模拟一次 50ms 的上游调用
        await asyncio.sleep(0.05)
        return _ok(_page([_no_up_row("R1", 500)]))

    store = MemoryScanStore()
    run = await _scan(store, slow)
    assert run["status"] == "succeeded"
    status = run["sourceStatus"][0]
    assert (status["source"], status["status"], status["rows"]) == ("no_up", "ok", 1)
    assert isinstance(status["durationMs"], int) and status["durationMs"] >= 40
    # 落库后读回仍然带耗时（指标按 sourceStatus.durationMs 聚合）
    stored = await store.get_run("scan-timing")
    assert stored["sourceStatus"][0]["durationMs"] == status["durationMs"]


# ---------------------------------------------------------------------------
# 5. 保留与归档（ADR-020）
# ---------------------------------------------------------------------------

DAY = timedelta(days=1)
STEP_ORDER = [
    "notifications", "traces", "alerts", "summaries", "scanEvidence", "metricDaily", "archive",
]
KEPT = ("ignoring", "open_old", "resolved_recent", "resolved_but_seen")


def _iso(moment: datetime) -> str:
    return moment.isoformat()


def _retention_settings(**aliases: Any) -> Settings:
    """按环境变量名注入（Settings 字段带 validation_alias，按字段名传会被静默忽略）。"""
    return Settings(_env_file=None, **{f"WMS_AGENT_{k}": str(v) for k, v in aliases.items()})


def _enabled_settings(**aliases: Any) -> Settings:
    return _retention_settings(RETENTION_ENABLED="true", **aliases)


async def _seed_retention(store: MemoryScanStore, *, now: datetime = NOW) -> dict[str, int]:
    """覆盖各分支的一套数据：2 条该归档、4 条不该动的告警，外加通知 / trace / 摘要 / 旧归档行。"""

    async def alert(fp: str, **patch: Any) -> int:
        result = await store.upsert_alert(_alert_row(fp))
        store.alerts[result.alert_id].update(patch)
        return result.alert_id

    async def note(key: str, alert_id: int, age_days: int) -> None:
        await store.save_notification({
            "alertId": alert_id, "channel": "in_app", "recipient": "admin", "status": "sent",
            "payloadDigest": key, "dedupeKey": f"dk-{key}", "createdAt": _iso(now - age_days * DAY),
        })

    ids = {
        "settled": await alert(
            "fp-settled", state="resolved",
            resolvedAt=_iso(now - 200 * DAY), lastSeenAt=_iso(now - 201 * DAY),
        ),
        # 忽略窗口还没结束：即使很久没出现也不能归档
        "ignoring": await alert(
            "fp-ignoring", state="ignored", ignoredUntil=_iso(now + 10 * DAY),
            lastSeenAt=_iso(now - 300 * DAY),
        ),
        "ignored_old": await alert(
            "fp-ignored-old", state="ignored", ignoredUntil=_iso(now - 199 * DAY),
            lastSeenAt=_iso(now - 200 * DAY),
        ),
        "open_old": await alert("fp-open-old", lastSeenAt=_iso(now - 300 * DAY)),
        "resolved_recent": await alert(
            "fp-resolved-recent", state="resolved", resolvedAt=_iso(now - 10 * DAY),
        ),
        # 结案很久了但 5 天前又出现过（忽略窗口内被抑制同样会刷新 lastSeenAt）：不归档
        "resolved_but_seen": await alert(
            "fp-resolved-but-seen", state="resolved",
            resolvedAt=_iso(now - 200 * DAY), lastSeenAt=_iso(now - 5 * DAY),
        ),
    }
    await note("old-on-settled", ids["settled"], 100)
    await note("old-on-open", ids["open_old"], 100)
    await note("recent-on-settled", ids["settled"], 10)
    await note("recent-on-recent", ids["resolved_recent"], 10)

    store.traces["trace-old"] = {"traceId": "trace-old", "createdAt": _iso(now - 95 * DAY)}
    store.traces["trace-new"] = {"traceId": "trace-new", "createdAt": _iso(now - 10 * DAY)}
    store.tool_calls.extend([
        {"traceId": "trace-old", "tool": "sql_query"},
        {"traceId": "trace-old", "tool": "schema_lookup"},
        {"traceId": "trace-new", "tool": "sql_query"},
    ])

    for scan_id, finished in (("scan-old", now - 200 * DAY), ("scan-new", now - 10 * DAY)):
        run = _stored_run(scan_id, started=finished - timedelta(minutes=5))
        run["finishedAt"] = _iso(finished)
        await store.insert_run(run)

    def summary(scan_id: str, text: str) -> dict[str, Any]:
        return {
            "scanId": scan_id, "ruleId": "NOUP-OVERDUE", "ruleVersion": "v0.2.0", "warehouse": "W01",
            "customer": "C1", "severity": "P1", "objectCount": 1,
            "severityCounts": {"P0": 0, "P1": 1, "P2": 0}, "sampleObjects": [], "summary": text,
            "summarySource": "template", "suggestedActions": [], "model": None,
            "promptTokens": 0, "completionTokens": 0,
        }

    await store.save_scan_summaries(
        [summary("scan-old", "旧扫描的摘要"), summary("scan-new", "新扫描的摘要")]
    )

    # 归档表里已有的行：一条早于归档期（应被清掉），一条还在期内（应保留）
    store.archive_rows[(ARCHIVE_TABLE_EVENTS, "999001")] = {
        "row": {"eventId": 999001}, "archivedAt": _iso(now - 400 * DAY),
    }
    store.archive_rows[(ARCHIVE_TABLE_ALERTS, "999002")] = {
        "row": {"alertId": 999002}, "archivedAt": _iso(now - 10 * DAY),
    }
    return ids


class _RetentionFailingStore(MemoryScanStore):
    async def archive_notifications_before(self, cutoff_iso: str, *, limit: int) -> int:
        raise ScanStoreUnavailableError(
            "archive notifications for retention failed: OperationalError"
        )


async def test_retention_policy_defaults_validation_and_override() -> None:
    settings = _retention_settings()  # 不读 .env：没有覆盖值时就是代码默认
    policy = RetentionPolicy.from_settings(settings)
    assert policy.as_dict() == {
        "alerts_online_days": 180, "alerts_archive_days": 365,
        "notifications_days": 90, "trace_days": 90, "metrics_days": 730,
    }
    assert (settings.retention_enabled, settings.retention_batch_size, settings.retention_max_batches) == (
        False, 500, 20,
    )
    assert (settings.retention_daily_at, settings.retention_timezone) == ("02:30", "Asia/Shanghai")
    policy.validate()

    overridden = RetentionPolicy.from_settings(_retention_settings(
        RETENTION_ALERTS_ONLINE_DAYS="30", RETENTION_ARCHIVE_DAYS="60",
        RETENTION_NOTIFICATIONS_DAYS="7", RETENTION_TRACE_DAYS="14",
        RETENTION_METRICS_DAYS="365",
    ))
    assert overridden.as_dict() == {
        "alerts_online_days": 30, "alerts_archive_days": 60,
        "notifications_days": 7, "trace_days": 14, "metrics_days": 365,
    }

    # 0 天等于清空全表：拒绝执行，而且是在碰存储之前
    store = _RetentionFailingStore()
    with pytest.raises(RetentionError, match="alerts_online_days 必须 ≥ 1"):
        await run_retention(store, policy=RetentionPolicy(alerts_online_days=0), now=NOW)
    with pytest.raises(RetentionError, match="notifications_days 必须 ≥ 1"):
        RetentionPolicy(notifications_days=0).validate()
    with pytest.raises(RetentionError, match="trace_days 必须 ≥ 1"):
        RetentionPolicy(trace_days=0).validate()
    with pytest.raises(RetentionError, match="metrics_days 必须 ≥ 1"):
        RetentionPolicy(metrics_days=0).validate()
    with pytest.raises(RetentionError, match="alerts_archive_days 必须 ≥ 1"):
        RetentionPolicy(alerts_archive_days=0).validate()
    # 朴素时间无法算 cutoff：同样拒绝，不猜时区
    with pytest.raises(RetentionError, match="now 必须带时区"):
        await run_retention(store, policy=policy, now=datetime(2026, 11, 25, 12, 0))


def test_parse_daily_at_accepts_hh_mm_only() -> None:
    assert parse_daily_at("2:30") == dtime(2, 30)
    assert parse_daily_at(" 23:59 ") == dtime(23, 59)
    for bad in ("", "24:00", "12:60", "025:0", "noon", "2"):
        with pytest.raises(RetentionError):
            parse_daily_at(bad)


async def test_run_retention_archives_settled_alerts_and_purges_expired_data() -> None:
    store = MemoryScanStore()
    ids = await _seed_retention(store)
    report = await run_retention(store, policy=RetentionPolicy(), now=NOW)

    assert [step["step"] for step in report["steps"]] == STEP_ORDER
    assert report["cutoffs"] == {
        "notifications": _iso(NOW - 90 * DAY), "traces": _iso(NOW - 90 * DAY),
        "alertsOnline": _iso(NOW - 180 * DAY), "archive": _iso(NOW - 365 * DAY),
        "metricDaily": (NOW - 730 * DAY).date().isoformat(),
    }
    assert report["totals"] == {
        # 两条 100 天前的通知归档；近期但挂在被归档告警上的那条随告警归档
        "notificationsArchived": 2, "tracesDeleted": 1,
        "alertsArchived": 2, "eventsArchived": 2, "notificationsArchivedWithAlerts": 1,
        # scan-old 的摘要 + scan-old 这条终态扫描本身（连同子表，此处为空）
        "summariesArchived": 1, "scansArchived": 1,
        "evaluatedObjectsArchived": 0, "observationsArchived": 0, "backlogObservationsArchived": 0,
        "metricRowsPurged": 0, "archiveRowsPurged": 1,
    }
    assert report["moreRemaining"] is False

    # 线上只剩不该动的 4 条告警及其事件
    assert sorted(store.alerts) == sorted(ids[key] for key in KEPT)
    assert len(store.events) == 4
    assert all(event["alertId"] in store.alerts for event in store.events)

    # 归档：先事件后告警都落了归档表；过期归档行被清掉、期内的保留
    by_table: dict[str, list[dict[str, Any]]] = {}
    for (table, _row_id), entry in store.archive_rows.items():
        by_table.setdefault(table, []).append(entry["row"])
    assert {row.get("fingerprint") for row in by_table[ARCHIVE_TABLE_ALERTS]} == {
        "fp-settled", "fp-ignored-old", None,  # None = 归档表里原有的那行占位告警
    }
    assert {row.get("alertId") for row in by_table[ARCHIVE_TABLE_EVENTS]} == {
        ids["settled"], ids["ignored_old"],
    }
    assert ("agent_alert_events", "999001") not in store.archive_rows
    assert ("agent_alerts", "999002") in store.archive_rows
    # 通知是审计证据：离线而不是删除
    assert sorted(row.get("payloadDigest") for row in by_table[ARCHIVE_TABLE_NOTIFICATIONS]) == [
        "old-on-open", "old-on-settled", "recent-on-settled",
    ]
    # 扫描记录随证据整批归档：线上没了，但只读接口读回落并标记 archived
    assert [row.get("scanId") for row in by_table[ARCHIVE_TABLE_SCAN_RUNS]] == ["scan-old"]
    assert await store.get_run("scan-old") is None
    archived_run = await store.get_archived_run("scan-old")
    assert archived_run is not None and archived_run["archived"] is True
    assert archived_run["status"] == "succeeded"

    # 通知：过期的两条离线；挂在被归档告警上的近期通知随之离线；挂在保留告警上的保留
    assert [n["payloadDigest"] for n in store.notifications] == ["recent-on-recent"]
    # trace：先删工具调用再删 trace，近期的不动
    assert list(store.traces) == ["trace-new"]
    assert [call["traceId"] for call in store.tool_calls] == ["trace-new"]

    # 摘要：所属扫描早已完成的进归档，接口回落读到并标记 archived；近期的原样可读
    assert [row["scanId"] for row in store.scan_summaries.values()] == ["scan-new"]
    fallback = await store.list_scan_summaries("scan-old")
    assert [row["summary"] for row in fallback] == ["旧扫描的摘要"]
    assert fallback[0]["archived"] is True
    live = await store.list_scan_summaries("scan-new")
    assert [row["summary"] for row in live] == ["新扫描的摘要"]
    assert "archived" not in live[0]

    # fingerprint 索引没有悬空：已归档的指纹再次出现时新建告警，而不是命中不存在的行
    assert all(alert_id in store.alerts for alert_id in store._fp_index.values())  # noqa: SLF001
    again = await store.upsert_alert(_alert_row("fp-settled", scanId="scan-again", traceId="trace-again"))
    assert again.outcome == "created"
    assert again.alert_id not in ids.values()

    # 可重入：再跑一轮什么都不会动
    second = await run_retention(store, policy=RetentionPolicy(), now=NOW)
    assert set(second["totals"].values()) == {0}
    assert second["moreRemaining"] is False
    assert sorted(store.alerts) == sorted([*(ids[key] for key in KEPT), again.alert_id])


async def test_run_retention_is_bounded_per_run_and_converges() -> None:
    store = MemoryScanStore()
    ids = await _seed_retention(store)
    first = await run_retention(store, policy=RetentionPolicy(), batch_size=1, max_batches=1, now=NOW)

    for step in first["steps"]:
        # 指标日聚合表此时是空的：这一步如实报 0；其余每步都恰好处理 1 行
        expected_rows = 0 if step["step"] == "metricDaily" else 1
        assert (step["rows"], step["batches"]) == (expected_rows, 1), step
    # 每批都是满的：报告必须如实说「可能还有剩余」，不能声称已清完
    assert first["moreRemaining"] is True
    assert len(store.alerts) == 5  # 6 条里只归档了 alertId 最小的那条

    for _ in range(20):
        report = await run_retention(store, policy=RetentionPolicy(), batch_size=1, max_batches=1, now=NOW)
        if not report["moreRemaining"]:
            break
    assert report["moreRemaining"] is False
    assert sorted(store.alerts) == sorted(ids[key] for key in KEPT)
    # 2 条告警 + 2 条事件 + 3 条通知 + 1 条摘要 + 1 条扫描记录 + 1 条仍在归档期内的旧行
    assert len(store.archive_rows) == 10


async def test_retention_scheduler_runs_once_a_day_after_daily_at() -> None:
    store = MemoryScanStore()
    disabled = RetentionScheduler(store, _retention_settings(RETENTION_ENABLED="false"), clock=lambda: NOW)
    await disabled.start()
    assert await disabled.tick(NOW) is None

    scheduler = RetentionScheduler(store, _enabled_settings(), clock=lambda: NOW)
    # 2026-11-25 12:00 UTC = 当天 20:00（Asia/Shanghai），已过 02:30 → 执行
    report = await scheduler.tick(NOW)
    assert report is not None and report["policy"]["alerts_online_days"] == 180
    assert scheduler.last_run_day == "20261125"
    assert scheduler.last_report is report
    # 同一天不再重复
    assert await scheduler.tick(NOW + timedelta(hours=1)) is None

    # 前一天 17:00 UTC = 当天 01:00，还没到 02:30
    early = RetentionScheduler(store, _enabled_settings(), clock=lambda: NOW)
    assert await early.tick(datetime(2026, 11, 24, 17, 0, tzinfo=timezone.utc)) is None
    assert early.last_run_day is None

    # 第二天到点后照常执行
    next_day = await scheduler.tick(NOW + DAY)
    assert next_day is not None and next_day["startedAt"] == _iso(NOW + DAY)
    assert scheduler.last_run_day == "20261126"


async def test_retention_scheduler_failure_is_not_retried_same_day() -> None:
    scheduler = RetentionScheduler(
        _RetentionFailingStore(), _enabled_settings(), tick_seconds=0.01, clock=lambda: NOW,
    )
    with pytest.raises(ScanStoreUnavailableError):
        await scheduler.tick(NOW)
    # 删除类任务不按 tick 重试：当天占位已记，第二天才再试
    assert scheduler.last_run_day == "20261125"
    assert scheduler.last_report is None
    assert await scheduler.tick(NOW + timedelta(hours=3)) is None

    # 后台循环遇到同样的失败：只记错误，不向外抛，进程不退出
    background = RetentionScheduler(
        _RetentionFailingStore(), _enabled_settings(), tick_seconds=0.01, clock=lambda: NOW,
    )
    await background.start()
    for _ in range(200):
        if background.last_error is not None:
            break
        await asyncio.sleep(0.01)
    await background.stop()
    assert background.last_error is not None
    assert background.last_error.startswith("ScanStoreUnavailableError:")
    assert background.last_run_day == "20261125"


async def test_retention_scheduler_lifecycle_runs_in_background_once() -> None:
    scheduler = RetentionScheduler(
        MemoryScanStore(), _enabled_settings(), tick_seconds=0.01, clock=lambda: NOW,
    )
    await scheduler.start()
    for _ in range(200):
        if scheduler.last_report is not None:
            break
        await asyncio.sleep(0.01)
    await scheduler.stop()
    assert scheduler.last_report is not None
    assert scheduler.last_error is None
    assert scheduler.last_run_day == "20261125"

    off = RetentionScheduler(MemoryScanStore(), _retention_settings(RETENTION_ENABLED="false"))
    await off.start()
    assert off.last_run_day is None
    await off.stop()


async def test_retention_scheduler_rejects_invalid_schedule_config() -> None:
    bad_time = RetentionScheduler(MemoryScanStore(), _enabled_settings(RETENTION_DAILY_AT="25:00"))
    with pytest.raises(RetentionError, match="retention_daily_at"):
        await bad_time.tick(NOW)
    bad_zone = RetentionScheduler(MemoryScanStore(), _enabled_settings(RETENTION_TIMEZONE="Mars/Olympus"))
    with pytest.raises(RetentionError, match="retention_timezone"):
        await bad_zone.tick(NOW)


def test_retention_run_endpoint_is_admin_only() -> None:
    for principal in (_user(), _user("cguser", ("cg",)), _service()):
        response = _client(principal, MemoryScanStore()).post("/agent/scan/retention/run")
        assert response.status_code == 403
        assert response.json() == {"code": 9997, "message": "仅管理员可执行保留与归档", "data": None}


async def test_retention_run_endpoint_returns_report_for_admin() -> None:
    store = MemoryScanStore()
    await _seed_retention(store)
    response = _client(_admin(), store).post("/agent/scan/retention/run")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 10000
    data = body["data"]
    assert [step["step"] for step in data["steps"]] == STEP_ORDER
    assert data["policy"]["alerts_online_days"] == 180
    assert data["totals"]["alertsArchived"] == 2
    assert data["moreRemaining"] is False
    assert len(store.alerts) == 4


def test_retention_run_endpoint_reports_store_failure() -> None:
    response = _client(_admin(), _RetentionFailingStore()).post("/agent/scan/retention/run")

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == 9998 and "巡检存储不可用" in body["message"]


def test_retention_run_endpoint_rejects_invalid_policy() -> None:
    client = _client(_admin(), MemoryScanStore())
    client.app.dependency_overrides[scan_router._get_settings] = lambda: SimpleNamespace(  # noqa: SLF001
        retention_alerts_online_days=0, retention_alerts_archive_days=365,
        retention_notifications_days=90, retention_trace_days=90,
        retention_batch_size=500, retention_max_batches=20,
    )
    response = client.post("/agent/scan/retention/run")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 9995 and "alerts_online_days 必须 ≥ 1" in body["message"]


# ---------------------------------------------------------------------------
# 6. 生产安全门（ADR-021）：巡检路由逐条拒绝「无 token / 伪造 token」
#
# 实测：网关（zero-one-cloud-starter-gateway）对无 token 的请求直接转发、带 token 时只校验
# 「能解析成 JWT 且未登出」，不按资源角色拒绝。所以巡检端点的认证与授权只能由 agent 自己保证。
# 这里把这条保证固化成回归：巡检路由表里新增任何端点，只要漏挂 require_principal 就会失败。
# ---------------------------------------------------------------------------

_SWEEP_BODY = {
    "/scan": {"scanTypes": ["no_up"], "requestId": "stage7-sweep-1"},
    "/alerts/{alert_id}/resolve": {"reason": "sweep"},
    "/alerts/{alert_id}/ignore": {"reason": "sweep", "ignoredUntil": _iso(NOW + timedelta(days=1))},
}
_SWEEP_MUST_COVER = {
    ("POST", "/scan"),
    ("GET", "/scan/metrics"),
    ("POST", "/scan/retention/run"),
    ("POST", "/scan/metrics/rollup/run"),
    ("GET", "/scans/{scan_id}"),
    ("GET", "/scans/{scan_id}/summaries"),
    ("POST", "/scans/{scan_id}/retry"),
    ("GET", "/alerts"),
    ("GET", "/alerts/page"),
    ("GET", "/alerts/{alert_id}"),
    ("POST", "/alerts/{alert_id}/claim"),
    ("POST", "/alerts/{alert_id}/ack"),
    ("POST", "/alerts/{alert_id}/resolve"),
    ("POST", "/alerts/{alert_id}/ignore"),
    ("GET", "/notifications"),
    ("POST", "/notifications/{notification_id}/read"),
}


def _sweep_cases() -> list[tuple[str, str, str]]:
    """(方法, 声明路径, 实际请求路径)；路径参数用占位值替换。"""
    from fastapi.routing import APIRoute

    cases: list[tuple[str, str, str]] = []
    for route in scan_router.router.routes:
        methods = getattr(route, "methods", None) or set()
        if not methods:
            continue
        for method in sorted(methods - {"HEAD", "OPTIONS"}):
            concrete = (
                route.path.replace("{scan_id}", "scan-sweep")
                .replace("{alert_id}", "1")
                .replace("{notification_id}", "1")
            )
            cases.append((method, route.path, concrete))
    return cases


def _unpatched_client(monkeypatch, public_pem: str) -> TestClient:
    """不覆盖 require_principal 的真实应用；只把验签公钥换成测试密钥。"""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    from app import security as security_module
    from app.main import create_app

    monkeypatch.setattr(security_module, "load_public_key", lambda _path: load_pem_public_key(public_pem.encode()))
    app = create_app()
    app.state.scan_store = MemoryScanStore()
    return TestClient(app)


def test_scan_route_sweep_covers_every_endpoint() -> None:
    cases = _sweep_cases()
    assert cases, "巡检路由表为空"
    assert {(method, path) for method, path, _ in cases} == {(m, p) for m, p in _SWEEP_MUST_COVER}


def test_every_scan_route_rejects_missing_garbage_forged_and_expired_tokens(monkeypatch, rsa_keypair, token_factory) -> None:
    private_pem, public_pem = rsa_keypair
    import jwt as pyjwt

    client = _unpatched_client(monkeypatch, public_pem)
    forged_key = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    admin = {"user_name": "admin", "sub": "a-1", "authorities": ["gly"]}
    credentials = {
        "none": None,
        "garbage": "not-a-jwt",
        "forged": pyjwt.encode({**admin, "exp": int(time.time()) + 3600}, forged_key, algorithm="RS256"),
        "expired": token_factory(**admin, exp=int(time.time()) - 60),
        "alg-none": pyjwt.encode({**admin, "exp": int(time.time()) + 3600}, key="", algorithm="none"),
    }
    failures: list[str] = []
    for method, declared, concrete in _sweep_cases():
        path = "/agent" + concrete
        for label, token in credentials.items():
            headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
            response = client.request(method, path, json=_SWEEP_BODY.get(declared), headers=headers)
            ok = response.status_code == 401 and response.json().get("code") == 401
            if not ok:
                failures.append(f"{method} {declared} [{label}] -> {response.status_code} {response.text[:80]}")
    assert failures == [], "以下巡检路由未拒绝不可信凭据：\n" + "\n".join(failures)


def test_scan_route_sweep_positive_control_accepts_a_genuinely_signed_admin(monkeypatch, rsa_keypair, token_factory) -> None:
    """对照组：同一套路由对「验签公钥签出的管理员令牌」放行，证明上面的 401 来自凭据校验而非配置失灵。"""
    _, public_pem = rsa_keypair
    client = _unpatched_client(monkeypatch, public_pem)
    token = token_factory(user_name="admin", sub="a-1", authorities=["gly"])

    metrics = client.get("/agent/scan/metrics", headers={"Authorization": f"Bearer {token}"})
    assert metrics.status_code == 200 and metrics.json()["code"] == 10000
    unknown = client.get("/agent/scans/scan-sweep", headers={"Authorization": f"Bearer {token}"})
    assert unknown.status_code == 200 and unknown.json()["code"] == 9999
    assert client.app.dependency_overrides == {}
