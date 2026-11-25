"""阶段7.7：指标日聚合与长窗口回看（ADR-020）。

覆盖五件事：
1. 日聚合文档可加总、可合并、可渲染回与实时快照同键的响应；
2. 补算只补缺失的「仓库 · 日」，最旧优先、每轮限批、可重入；
3. 超过 90 天的指标窗口 = 日聚合 + 实时尾段，并以 mode / coverage 说明口径；
4. 补算接口仅管理员可用；
5. 保留任务先聚合再归档，补不齐则本轮不归档；已归档的扫描记录仍可通过只读接口读到。
存储层契约（双后端）见 tests/test_scan_store_contract.py。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.scan import router as scan_router
from app.scan.metrics_rollup import (
    METRICS_MAX_HOURS,
    METRICS_REALTIME_HOURS,
    RollupError,
    build_rollup,
    day_bounds,
    long_window_metrics,
    merge_rollups,
    render_rollup,
    run_metric_rollup,
)
from app.scan.repository import (
    ARCHIVE_TABLE_SCAN_RUNS,
    RUN_COLUMNS,
    MemoryScanStore,
    ScanStoreUnavailableError,
    run_from_archive,
)
from app.scan.retention import RetentionError, RetentionPolicy, RetentionScheduler, run_retention
from app.security import Principal, require_principal

UTC = timezone.utc
NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
DAY = timedelta(days=1)
ZONE = ZoneInfo("Asia/Shanghai")


def _iso(moment: datetime) -> str:
    return moment.isoformat()


def _user(name: str = "tester", authorities: tuple[str, ...] = ("ckjl",)) -> Principal:
    return Principal(user_id=f"u-{name}", user_name=name, authorities=authorities)


def _admin() -> Principal:
    return Principal(user_id="a-1", user_name="admin", authorities=("gly",))


def _service() -> Principal:
    return Principal(
        user_id="agent-inspector", user_name="agent-inspector", authorities=("insp_read",),
        warehouse_scope=("W01",), token_use="agent_service",
    )


def _client(principal: Principal, store: MemoryScanStore) -> TestClient:
    from app.main import create_app

    app = create_app()
    app.state.scan_store = store
    app.dependency_overrides[require_principal] = lambda: principal
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store
    return TestClient(app)


def _enabled_settings() -> Settings:
    return Settings(_env_file=None, **{"WMS_AGENT_RETENTION_ENABLED": "true"})


def _stored_run(
    scan_id: str, started: datetime, *, status: str = "succeeded", trigger: str = "manual",
    seconds: int = 60, error: str | None = None,
) -> dict[str, Any]:
    """存储层形状的扫描行（与 tests/test_scan_stage7.py 的 _stored_run 同口径）。"""
    return {
        "scanId": scan_id, "status": status, "trigger": trigger, "partial": False,
        "sourceStatus": [], "counts": {}, "errorSummary": error, "scanTypes": ["no_up"],
        "warehouse": "W01", "scanKey": scan_id, "traceId": f"trace-{scan_id}",
        "queuedAt": _iso(started), "startedAt": _iso(started),
        "finishedAt": _iso(started + timedelta(seconds=seconds)) if status != "running" else None,
    }


def _metric_run(
    scan_id: str, started: datetime, *, status: str = "succeeded", trigger: str = "manual",
    seconds: int = 10, error: str | None = None,
) -> dict[str, Any]:
    return {
        "scanId": scan_id, "status": status, "trigger": trigger, "partial": False,
        "startedAt": _iso(started), "finishedAt": _iso(started + timedelta(seconds=seconds)),
        "sourceStatus": [{"source": "no_up", "status": "ok", "rows": 2, "durationMs": 40}],
        "counts": {
            "alertsSuppressed": 1, "llmCalls": 2, "llmFailures": 1, "promptTokens": 100,
            "completionTokens": 20, "summariesLlm": 1, "summariesTemplate": 1,
        },
        "errorSummary": error,
    }


def _inputs(window_from: datetime, window_to: datetime, **overrides: Any) -> dict[str, list[dict[str, Any]]]:
    base: dict[str, list[dict[str, Any]]] = {
        "runs": [], "event_counts": [], "alerts": [], "notification_counts": [], "summary_counts": [],
    }
    base.update(overrides)
    return {**base, "window_from": window_from, "window_to": window_to}


# 1. 日聚合文档：可加总、可合并、可渲染


def test_build_rollup_is_additive_and_renders_the_snapshot_shape() -> None:
    day = datetime(2026, 11, 10, tzinfo=UTC)
    first = build_rollup(
        **_inputs(
            day, day + DAY,
            runs=[
                _metric_run("s1", day + timedelta(hours=1), seconds=4),
                _metric_run("s2", day + timedelta(hours=2), status="failed", seconds=6, error="ReadTimeout"),
            ],
            event_counts=[{"eventType": "created", "fromState": None, "toState": "open", "count": 3}],
            alerts=[{
                "alertId": 1, "firstSeenAt": _iso(day), "claimedAt": _iso(day + timedelta(hours=2)),
                "resolvedAt": None, "resolvedReason": None,
            }],
            notification_counts=[{
                "status": "sent", "channel": "in_app", "createdInWindow": True,
                "readInWindow": False, "unreadNow": True, "count": 5,
            }],
            summary_counts=[{
                "summarySource": "llm", "fallbackReason": None, "model": "m-a",
                "summaries": 2, "promptTokens": 300, "completionTokens": 60,
            }],
        ),
    )
    second = build_rollup(
        **_inputs(
            day + DAY, day + 2 * DAY,
            runs=[_metric_run("s3", day + DAY, trigger="schedule", seconds=10)],
            summary_counts=[{
                "summarySource": "template", "fallbackReason": "timeout", "model": None,
                "summaries": 1, "promptTokens": 0, "completionTokens": 0,
            }],
        ),
    )

    # 可加总文档：计数相加、总量相加、最大值取最大
    assert first["scans"] == {
        "total": 2, "succeeded": 1, "failed": 1, "cancelled": 0, "inProgress": 0, "partial": 0,
        "byTrigger": {"manual": 2, "schedule": 0, "retry": 0},
        "durationSeconds": {"samples": 2, "total": 10.0, "max": 6.0},
        "failures": {"ReadTimeout": 1},
    }
    assert second["scans"]["durationSeconds"] == {"samples": 1, "total": 10.0, "max": 10.0}
    assert first["alerts"]["suppressed"] == 2 and first["llm"]["calls"] == 4
    assert first["llm"]["byModel"] == {"m-a": {"summaries": 2, "promptTokens": 300, "completionTokens": 60}}
    assert first["llm"]["fallbackReasons"] == {}

    merged = merge_rollups([first, second])
    assert merged["scans"]["total"] == 3
    assert merged["scans"]["durationSeconds"] == {"samples": 3, "total": 20.0, "max": 10.0}

    rendered = render_rollup(
        merged, active={"total": 4}, unread=2, window_from=day, window_to=day + 2 * DAY,
        generated_at=NOW, coverage={"dailyDays": 2},
    )
    assert rendered["mode"] == "dailyRollup" and rendered["coverage"] == {"dailyDays": 2}
    assert rendered["window"] == {"from": _iso(day), "to": _iso(day + 2 * DAY), "hours": 48.0}
    assert rendered["generatedAt"] == _iso(NOW)
    # 分位数无法由日聚合还原：明确给出 None，而不是拿日均值冒充
    assert rendered["scans"] == {
        "total": 3, "succeeded": 2, "failed": 1, "cancelled": 0, "inProgress": 0, "partial": 0,
        "byTrigger": {"manual": 2, "schedule": 1, "retry": 0},
        "durationSeconds": {"samples": 3, "avg": 6.667, "p50": None, "p90": None, "max": 10.0},
        "failures": [{"errorSummary": "ReadTimeout", "count": 1}],
    }
    assert rendered["sources"]["no_up"] == {
        "scans": 3, "ok": 3, "partial": 0, "error": 0, "timeout": 0, "rows": 6, "avgRows": 2.0,
        "avgDurationMs": 40.0, "maxDurationMs": 40.0, "withoutTiming": 0,
    }
    assert rendered["alerts"]["created"] == 3 and rendered["alerts"]["active"] == {"total": 4}
    assert rendered["alerts"]["suppressed"] == 3  # 三条终态扫描的 counts 求和
    assert rendered["handling"] == {
        "claimed": 1,
        "claimDurationSeconds": {"samples": 1, "avg": 7200.0, "p50": None, "p90": None, "max": 7200.0},
        "resolveDurationSeconds": {
            "manual": {"samples": 0, "avg": None, "p50": None, "p90": None, "max": None},
            "auto": {"samples": 0, "avg": None, "p50": None, "p90": None, "max": None},
        },
    }
    assert rendered["notifications"] == {
        "sent": 5, "pending": 0, "failed": 0, "other": 0, "read": 0, "unrouted": 0, "unread": 2,
    }
    assert rendered["llm"] == {
        "calls": 6, "failures": 3, "failureRate": 0.5, "promptTokens": 300, "completionTokens": 60,
        "summariesLlm": 2, "summariesTemplate": 1,
        "byModel": [
            {"model": "m-a", "summaries": 2, "promptTokens": 300, "completionTokens": 60},
            {"model": "template", "summaries": 1, "promptTokens": 0, "completionTokens": 0},
        ],
        "fallbackReasons": [{"reason": "timeout", "count": 1}],
    }
    # 空窗口不丢键：零值文档照样能参与合并（没有数据的日期补出来的是全零行）
    empty = build_rollup(**_inputs(day, day))
    assert empty["scans"]["total"] == 0 and empty["sources"] == {}
    assert merge_rollups([empty, merged])["scans"]["total"] == 3
    assert merge_rollups([]) == {}


# 2. 补算：只补缺失、最旧优先、限批、可重入


async def test_run_metric_rollup_fills_only_missing_days_oldest_first_in_batches() -> None:
    store = MemoryScanStore()
    # 2026-11-21 11:00（北京时间）开始的一次扫描：落在 11-21 这个业务日
    await store.insert_run(_stored_run("scan-rollup", datetime(2026, 11, 21, 3, 0, tzinfo=UTC)))

    first = await run_metric_rollup(store, warehouses=["W01"], now=NOW, history_days=5, max_batches=2)
    assert (first["timezone"], first["fromDate"], first["toDate"], first["expected"]) == (
        "Asia/Shanghai", "2026-11-20", "2026-11-24", 5,  # 不含今天
    )
    assert (first["existing"], first["computed"], first["remaining"]) == (0, 2, 3)
    assert first["dates"] == ["2026-11-20", "2026-11-21"]  # 最旧优先
    second = await run_metric_rollup(store, warehouses=["W01"], now=NOW, history_days=5, max_batches=2)
    assert (second["existing"], second["computed"], second["remaining"]) == (2, 2, 1)
    last = await run_metric_rollup(store, warehouses=["W01"], now=NOW, history_days=5, max_batches=2)
    assert (last["existing"], last["computed"], last["remaining"]) == (4, 1, 0)
    again = await run_metric_rollup(store, warehouses=["W01"], now=NOW, history_days=5, max_batches=2)
    assert (again["existing"], again["computed"], again["remaining"]) == (5, 0, 0)  # 已有不重算

    rows = await store.list_metric_daily(
        date_from="2026-11-20", date_to="2026-11-25", warehouses=["W01"],
    )
    assert [row["metricDate"] for row in rows] == [
        "2026-11-20", "2026-11-21", "2026-11-22", "2026-11-23", "2026-11-24",
    ]
    by_date = {row["metricDate"]: row for row in rows}
    assert by_date["2026-11-21"]["metrics"]["scans"]["total"] == 1
    assert by_date["2026-11-20"]["metrics"]["scans"]["total"] == 0  # 没有数据的日期也落全零行
    assert {row["warehouse"] for row in rows} == {"W01"}
    assert {row["timezone"] for row in rows} == {"Asia/Shanghai"}

    with pytest.raises(RollupError, match="now 必须带时区"):
        await run_metric_rollup(store, warehouses=["W01"], now=datetime(2026, 11, 25, 12, 0))
    with pytest.raises(RollupError, match="history_days 必须 ≥ 1"):
        await run_metric_rollup(store, warehouses=["W01"], now=NOW, history_days=0)
    with pytest.raises(RollupError, match="retention_timezone 非法"):
        await run_metric_rollup(store, warehouses=["W01"], now=NOW, timezone="Mars/Olympus")
    nothing = await run_metric_rollup(store, warehouses=[], now=NOW)
    assert (nothing["expected"], nothing["computed"], nothing["remaining"]) == (0, 0, 0)


def test_day_bounds_follow_the_business_timezone() -> None:
    start, end = day_bounds(date(2026, 11, 25), ZONE)
    assert (start.isoformat(), end.isoformat()) == ("2026-11-25T00:00:00+08:00", "2026-11-26T00:00:00+08:00")
    # 北京时间 11-25 的自然日在 UTC 上跨日：从 11-24 16:00Z 起
    assert start.astimezone(UTC).isoformat() == "2026-11-24T16:00:00+00:00"


# 3. 长窗口 = 日聚合 + 实时尾段


async def test_long_window_metrics_combines_daily_rollup_and_realtime_tail() -> None:
    store = MemoryScanStore()
    now = NOW
    horizon = now - timedelta(hours=METRICS_REALTIME_HOURS)  # 2026-08-27 12:00Z = 北京时间 20:00
    assert horizon.astimezone(ZONE).isoformat() == "2026-08-27T20:00:00+08:00"
    rows = []
    for index, metric_date in enumerate(("2026-05-10", "2026-05-11", "2026-05-12")):
        rows.append({
            "metricDate": metric_date, "warehouse": "W01", "timezone": "Asia/Shanghai",
            "metrics": {
                "scans": {
                    "total": 10 + index, "succeeded": 10 + index, "failed": 0, "cancelled": 0,
                    "inProgress": 0, "partial": 0,
                    "byTrigger": {"manual": 10 + index, "schedule": 0, "retry": 0},
                    "durationSeconds": {"samples": 10 + index, "total": 50.0, "max": 9.0},
                    "failures": {},
                },
            },
        })
    await store.save_metric_daily(rows)
    await store.insert_run(_stored_run("scan-tail", now - timedelta(hours=1), status="failed", seconds=60, error="probe"))

    data = await long_window_metrics(
        store, window_from=now - timedelta(days=200), window_to=now, warehouses=["W01"], generated_at=now,
    )

    assert data["mode"] == "dailyRollup" and data["generatedAt"] == _iso(now)
    assert data["window"]["hours"] == 4800.0
    # 日聚合三天（10 + 11 + 12）加实时尾段的 1 次失败扫描
    assert data["scans"] == {
        "total": 34, "succeeded": 33, "failed": 1, "cancelled": 0, "inProgress": 0, "partial": 0,
        "byTrigger": {"manual": 34, "schedule": 0, "retry": 0},
        "durationSeconds": {"samples": 34, "avg": 6.176, "p50": None, "p90": None, "max": 60.0},
        "failures": [{"errorSummary": "probe", "count": 1}],
    }
    # 口径说明：哪些天读的是日聚合、从哪一刻起是实时、有几天还没补算（计数会被低估）
    # 200 天窗口的起点是 2026-05-09；可聚合的整日到 08-26（结束时刻不晚于 90 天前）
    assert data["coverage"] == {
        "realTimeFrom": "2026-08-27T00:00:00+08:00", "realTimeHours": 2180.0,
        "dailyDays": 110, "dailyFrom": "2026-05-09", "dailyTo": "2026-08-26", "missingDays": 107,
    }


async def test_metrics_endpoint_switches_to_daily_rollup_beyond_ninety_days() -> None:
    store = MemoryScanStore()
    client = _client(_admin(), store)

    realtime = client.get(f"/agent/scan/metrics?hours={METRICS_REALTIME_HOURS}").json()
    assert realtime["code"] == 10000 and "mode" not in realtime["data"]

    rolled = client.get("/agent/scan/metrics?hours=2200&warehouse=W01").json()
    assert rolled["code"] == 10000
    data = rolled["data"]
    assert data["mode"] == "dailyRollup"
    assert data["coverage"]["dailyDays"] > 0 and data["coverage"]["dailyFrom"]
    # 实时尾段从最后一个可聚合日的结束时刻起，可比 90 天多出不到一天
    assert data["coverage"]["realTimeHours"] <= METRICS_REALTIME_HOURS + 24
    assert data["scans"]["total"] == 0  # 空库：日聚合尚未补算，实时尾段也没有数据

    too_long = client.get(f"/agent/scan/metrics?hours={METRICS_MAX_HOURS + 1}")
    assert too_long.status_code == 422 and too_long.json()["code"] == 9995
    assert METRICS_MAX_HOURS == 24 * 730


# 4. 补算接口仅管理员


class _RollupListFailingStore(MemoryScanStore):
    async def list_metric_daily(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        raise ScanStoreUnavailableError("list metric daily for metrics failed: OperationalError")


class _RollupSaveFailingStore(MemoryScanStore):
    async def save_metric_daily(self, rows: list[dict[str, Any]]) -> int:
        raise ScanStoreUnavailableError("save metric daily for metrics failed: OperationalError")


async def test_rollup_endpoint_is_admin_only_and_reports_progress() -> None:
    for principal in (_user(), _user("cguser", ("cg",)), _service()):
        response = _client(principal, MemoryScanStore()).post("/agent/scan/metrics/rollup/run")
        assert response.status_code == 403
        assert response.json() == {"code": 9997, "message": "仅管理员可执行指标日聚合", "data": None}

    store = MemoryScanStore()
    response = _client(_admin(), store).post("/agent/scan/metrics/rollup/run")
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["timezone"] == "Asia/Shanghai"
    assert (report["expected"], report["existing"], report["computed"], report["remaining"]) == (180, 0, 180, 0)
    assert len(report["dates"]) == 180 and len(store.metric_daily) == 180  # 180 天 × 配置的 1 个仓库

    again = _client(_admin(), store).post("/agent/scan/metrics/rollup/run").json()["data"]
    assert (again["existing"], again["computed"], again["remaining"]) == (180, 0, 0)

    failing = _client(_admin(), _RollupListFailingStore()).post("/agent/scan/metrics/rollup/run")
    assert failing.status_code == 503 and failing.json()["code"] == 9998


# 5. 保留任务先聚合再归档


async def _seed_settled_alert(store: MemoryScanStore, *, now: datetime) -> int:
    created = await store.upsert_alert({
        "fingerprint": "fp-77-old", "ruleId": "NOUP-OVERDUE", "ruleVersion": "v0.2.0",
        "objectType": "no_up_goods", "objectId": "N-77|G|T", "dimension": {"warehouse": "W01"},
        "severity": "P0", "warehouseId": "W01", "title": "stage7.7 old alert", "evidence": {},
        "suggestedActions": [], "scanId": "scan-77-old", "traceId": "trace-77-old",
        "lastSeenAt": _iso(now - 201 * DAY),
    })
    store.alerts[created.alert_id].update({"state": "resolved", "resolvedAt": _iso(now - 200 * DAY)})
    return created.alert_id


async def test_scheduler_rolls_up_before_archiving() -> None:
    store = MemoryScanStore()
    alert_id = await _seed_settled_alert(store, now=NOW)
    scheduler = RetentionScheduler(store, _enabled_settings(), clock=lambda: NOW)

    report = await scheduler.tick(NOW)

    assert report is not None and report["rollup"]["remaining"] == 0
    assert len(store.metric_daily) == 180  # 归档之前，历史指标已经落进日聚合
    assert report["totals"]["alertsArchived"] == 1
    assert alert_id not in store.alerts and scheduler.last_run_day == "20261125"
    # 未到点 / 同一天只跑一次
    assert await scheduler.tick(NOW + timedelta(hours=1)) is None


async def test_scheduler_skips_archiving_when_rollup_cannot_be_completed() -> None:
    store = _RollupSaveFailingStore()
    alert_id = await _seed_settled_alert(store, now=NOW)
    scheduler = RetentionScheduler(store, _enabled_settings(), clock=lambda: NOW)

    with pytest.raises(ScanStoreUnavailableError):
        await scheduler.tick(NOW)

    # 宁可不动数据，也不让历史指标随归档消失；当天不重试
    assert alert_id in store.alerts and store.metric_daily == {}
    assert scheduler.last_run_day == "20261125"
    assert await scheduler.tick(NOW + timedelta(hours=1)) is None


async def test_manual_retention_round_does_not_require_rollup() -> None:
    store = MemoryScanStore()
    alert_id = await _seed_settled_alert(store, now=NOW)
    report = await run_retention(store, policy=RetentionPolicy(), now=NOW)
    assert report["totals"]["alertsArchived"] == 1
    assert store.metric_daily == {} and alert_id not in store.alerts


def test_invalid_policy_and_timezone_are_rejected_before_touching_the_store() -> None:
    with pytest.raises(RetentionError, match="metrics_days 必须 ≥ 1"):
        RetentionPolicy(metrics_days=0).validate()
    scheduler = RetentionScheduler(
        MemoryScanStore(), Settings(_env_file=None, **{
            "WMS_AGENT_RETENTION_ENABLED": "true", "WMS_AGENT_RETENTION_TIMEZONE": "Mars/Olympus",
        }),
    )
    with pytest.raises(RetentionError, match="retention_timezone 非法"):
        import asyncio

        asyncio.run(scheduler.tick(NOW))


# 6. 已归档的扫描记录仍可读


def test_run_from_archive_restores_the_online_shape() -> None:
    row: dict[str, Any] = {column: None for column in RUN_COLUMNS}
    row.update({
        "scan_id": "scan-gone", "status": "succeeded", "trigger": "schedule", "actor_type": "service",
        "actor_id": "agent-inspector", "partial": False, "source_status": [], "counts": {"llmCalls": 5},
        "scan_types": "expiry,backlog", "warehouse": "W01", "dry_run": False,
        "notification_mode": "dry_run", "trace_id": "trace-gone", "attempt": 1,
        "queued_at": _iso(NOW - 200 * DAY), "started_at": _iso(NOW - 200 * DAY),
        "finished_at": _iso(NOW - 200 * DAY + timedelta(seconds=5)),
        "retry_of_scan_id": "scan-root", "origin_trigger": "manual",
    })
    restored = run_from_archive(row)
    assert restored["archived"] is True and restored["scanId"] == "scan-gone"
    assert restored["scanTypes"] == ["expiry", "backlog"] and restored["counts"] == {"llmCalls": 5}
    assert restored["sourceStatus"] == [] and restored["trigger"] == "schedule"
    assert restored["startedAt"] == _iso(NOW - 200 * DAY)
    assert restored["retryOfScanId"] == "scan-root" and restored["originTrigger"] == "manual"
    assert restored["actorType"] == "service" and restored["executorType"] is None


async def test_archived_scan_is_readable_through_scan_endpoints() -> None:
    store = MemoryScanStore()
    archived = _stored_run(
        "scan-gone", NOW - 200 * DAY, trigger="schedule",
    )
    archived.update({"actorType": "service", "actorId": "agent-inspector", "scanTypes": ["expiry", "backlog"]})
    store.archive_rows[(ARCHIVE_TABLE_SCAN_RUNS, "scan-gone")] = {"row": archived, "archivedAt": _iso(NOW - 20 * DAY)}

    record = _client(_admin(), store).get("/agent/scans/scan-gone").json()
    assert record["code"] == 10000
    assert record["data"]["archived"] is True and record["data"]["scanId"] == "scan-gone"
    assert record["data"]["scanTypes"] == ["expiry", "backlog"] and record["data"]["trigger"] == "schedule"

    summaries = _client(_admin(), store).get("/agent/scans/scan-gone/summaries").json()
    assert summaries["code"] == 10000 and summaries["data"]["items"] == []
    assert summaries["data"]["scanId"] == "scan-gone"

    # 可见性不因「已归档」放宽：这条定时扫描的记录对业务角色仍不可见
    stranger = _client(_user(), store).get("/agent/scans/scan-gone").json()
    assert stranger["code"] == 9997
    missing = _client(_admin(), store).get("/agent/scans/never-existed").json()
    assert missing["code"] == 9999
