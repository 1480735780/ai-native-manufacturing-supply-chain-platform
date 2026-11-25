"""指标日聚合与长窗口回看（阶段7.7，ADR-020）。

指标接口在 ``METRICS_REALTIME_HOURS``（90 天）内读实时数据；更长的窗口由两段拼成：

* **日聚合**：每个仓库、每个业务时区的自然日一行（``agent_metric_daily``），内容是可加总的
  计数与总量（``build_rollup``）。``run_metric_rollup`` 按天补算——缺哪天补哪天、最旧优先、
  每轮限批；保留任务每天先跑它，所以告警与扫描证据归档后历史指标不会随线上行消失。
* **实时尾段**：最后一个已聚合日的结束时刻到现在，仍按实时口径取数。

两段合并（``merge_rollup``）后渲染（``render_rollup``），键与实时快照一致；分位数（p50 / p90）
无法由日聚合还原，长窗口里为 None，并以 ``mode=dailyRollup`` 与 ``coverage`` 标明口径。
窗口上限 ``METRICS_MAX_HOURS``（2 年），超过上限不返回。
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.scan.metrics import (
    MAX_FAILURE_REASONS,
    NOTIFICATION_STATUSES,
    SOURCE_STATUSES,
    SUMMED_COUNT_KEYS,
    TERMINAL_RUN_STATES,
    _count,
    _in_window,
    _seconds,
    build_metrics,
)
from app.scan.repository import AUTO_RESOLVE_EVENT, _parse_iso

if TYPE_CHECKING:  # 仅类型标注，运行时不产生循环导入
    from app.scan.repository import ScanStore

# 实时口径的窗口上限：与在线保留期一致，避免无界聚合
METRICS_REALTIME_HOURS = 24 * 90
# 指标接口的窗口上限：2 年；90 天至 2 年读日聚合
METRICS_MAX_HOURS = 24 * 730
DEFAULT_TIMEZONE = "Asia/Shanghai"
# 补算范围覆盖最长的在线保留期（180 天）：更早的日期数据已归档，无法再按实时口径聚合
DEFAULT_HISTORY_DAYS = 180
# 每轮最多补算的「仓库 · 日」数（每个 = 5 条聚合查询）
DEFAULT_MAX_BATCHES = 400

_MAX_KEYS = frozenset({"max", "maxDurationMs"})
_FAILURE_REASONS_LIMIT = 5
# 注意：run_metric_rollup 的参数名 timezone（业务时区名）会遮蔽 datetime.timezone，固定时刻在此预先取出
_UTC = timezone.utc


class RollupError(ValueError):
    """日聚合参数非法（时区、时间基准）：拒绝执行，不带着错误口径写聚合表。"""


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(str(name or DEFAULT_TIMEZONE))
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise RollupError(f"retention_timezone 非法: {exc}") from exc


def day_bounds(day: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    """业务时区自然日 ``day`` 的 ``[start, end)``（带时区的绝对时刻）。"""
    start = datetime(day.year, day.month, day.day, tzinfo=zone)
    nxt = day + timedelta(days=1)
    end = datetime(nxt.year, nxt.month, nxt.day, tzinfo=zone)
    return start, end


def _total_bucket() -> dict[str, Any]:
    return {"samples": 0, "total": 0.0, "max": None}


def _add_sample(bucket: dict[str, Any], value: float | None) -> None:
    if value is None:
        return
    bucket["samples"] += 1
    bucket["total"] += value
    top = bucket["max"]
    bucket["max"] = value if top is None else max(top, value)


def build_rollup(
    *,
    runs: list[dict[str, Any]],
    event_counts: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    notification_counts: list[dict[str, Any]],
    summary_counts: list[dict[str, Any]],
    window_from: datetime,
    window_to: datetime,
) -> dict[str, Any]:
    """把一段窗口的原始聚合行变成**可加总**文档（计数、总量、最大值、按名称分组的计数）。

    与 ``app.scan.metrics.build_metrics`` 同口径：扫描与摘要按扫描开始时间、事件按事件时间、
    通知按创建 / 已读时间入窗（由存储层保证）；这里不做窗口过滤。
    """
    by_status: Counter[str] = Counter(str(run.get("status") or "") for run in runs)
    by_trigger: Counter[str] = Counter(str(run.get("trigger") or "manual") for run in runs)
    durations = _total_bucket()
    failures: Counter[str] = Counter()
    summed: Counter[str] = Counter()
    sources: dict[str, dict[str, Any]] = {}
    partial = 0
    for run in runs:
        partial += 1 if run.get("partial") else 0
        _add_sample(
            durations, _seconds(_parse_iso(run.get("startedAt")), _parse_iso(run.get("finishedAt"))),
        )
        for entry in run.get("sourceStatus") or []:
            if not isinstance(entry, dict):
                continue
            bucket = sources.setdefault(
                str(entry.get("source") or "unknown"),
                {
                    "scans": 0, "ok": 0, "partial": 0, "error": 0, "timeout": 0, "rows": 0,
                    "timed": 0, "durationMsTotal": 0.0, "maxDurationMs": None, "withoutTiming": 0,
                },
            )
            bucket["scans"] += 1
            status = str(entry.get("status") or "")
            if status in SOURCE_STATUSES:
                bucket[status] += 1
            bucket["rows"] += int(entry.get("rows") or 0)
            duration_ms = entry.get("durationMs")
            if isinstance(duration_ms, (int, float)) and not isinstance(duration_ms, bool):
                bucket["timed"] += 1
                bucket["durationMsTotal"] += float(duration_ms)
                top = bucket["maxDurationMs"]
                bucket["maxDurationMs"] = (
                    float(duration_ms) if top is None else max(top, float(duration_ms))
                )
            else:
                bucket["withoutTiming"] += 1
        if run.get("status") not in TERMINAL_RUN_STATES:
            continue
        if run.get("status") == "failed":
            failures[str(run.get("errorSummary") or "unknown")] += 1
        counts = run.get("counts") or {}
        for key in SUMMED_COUNT_KEYS:
            summed[key] += int(counts.get(key) or 0)

    claim, resolve_manual, resolve_auto = _total_bucket(), _total_bucket(), _total_bucket()
    claimed = 0
    for alert in alerts:
        first_seen = _parse_iso(alert.get("firstSeenAt"))
        claimed_at = _parse_iso(alert.get("claimedAt"))
        if _in_window(claimed_at, window_from, window_to):
            claimed += 1
            _add_sample(claim, _seconds(first_seen, claimed_at))
        resolved_at = _parse_iso(alert.get("resolvedAt"))
        if _in_window(resolved_at, window_from, window_to):
            duration = _seconds(first_seen, resolved_at)
            if duration is None:
                continue
            if str(alert.get("resolvedReason") or "").startswith(AUTO_RESOLVE_EVENT + ":"):
                _add_sample(resolve_auto, duration)
            else:
                _add_sample(resolve_manual, duration)

    notifications: dict[str, Any] = {status: 0 for status in NOTIFICATION_STATUSES}
    notifications.update({"other": 0, "read": 0, "unrouted": summed["notificationsUnrouted"]})
    by_status_notes: Counter[str] = Counter()
    read = 0
    for row in notification_counts:
        count = int(row.get("count") or 0)
        if row.get("createdInWindow"):
            by_status_notes[str(row.get("status") or "unknown")] += count
        if row.get("readInWindow"):
            read += count
    for status, count in by_status_notes.items():
        if status in NOTIFICATION_STATUSES:
            notifications[status] += count
        else:
            notifications["other"] += count
    notifications["read"] = read

    llm: dict[str, Any] = {
        "calls": summed["llmCalls"], "failures": summed["llmFailures"],
        "promptTokens": summed["promptTokens"], "completionTokens": summed["completionTokens"],
        "summariesLlm": 0, "summariesTemplate": 0, "byModel": {}, "fallbackReasons": {},
    }
    for row in summary_counts:
        count = int(row.get("summaries") or 0)
        is_llm = str(row.get("summarySource") or "") == "llm"
        llm["summariesLlm" if is_llm else "summariesTemplate"] += count
        model = str(row.get("model") or "unknown") if is_llm else "template"
        entry = llm["byModel"].setdefault(
            model, {"summaries": 0, "promptTokens": 0, "completionTokens": 0},
        )
        entry["summaries"] += count
        entry["promptTokens"] += int(row.get("promptTokens") or 0)
        entry["completionTokens"] += int(row.get("completionTokens") or 0)
        reason = row.get("fallbackReason")
        if reason:
            key = str(reason)
            llm["fallbackReasons"][key] = int(llm["fallbackReasons"].get(key) or 0) + count

    return {
        "scans": {
            "total": len(runs),
            "succeeded": by_status.get("succeeded", 0),
            "failed": by_status.get("failed", 0),
            "cancelled": by_status.get("cancelled", 0),
            "inProgress": sum(by_status.get(state, 0) for state in ("queued", "running")),
            "partial": partial,
            "byTrigger": {
                "manual": by_trigger.get("manual", 0),
                "schedule": by_trigger.get("schedule", 0),
                "retry": by_trigger.get("retry", 0),
            },
            "durationSeconds": durations,
            "failures": {reason: count for reason, count in failures.items()},
        },
        "sources": sources,
        "alerts": {
            "created": _count(event_counts, "created"),
            "escalated": _count(event_counts, "escalated"),
            "suppressed": summed["alertsSuppressed"],
            "replayed": summed["alertsReplayed"],
            "autoResolved": _count(event_counts, AUTO_RESOLVE_EVENT),
            "staleCheckSkipped": summed["staleCheckSkipped"],
            "acknowledged": _count(event_counts, "transition", "acknowledged"),
            "closedManually": _count(event_counts, "transition", "resolved"),
            "ignored": _count(event_counts, "transition", "ignored"),
        },
        "handling": {
            "claimed": claimed,
            "claim": claim,
            "resolve": {"manual": resolve_manual, "auto": resolve_auto},
        },
        "notifications": notifications,
        "llm": llm,
    }


def _merge_into(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict):
            child = target.get(key)
            if not isinstance(child, dict):
                child = {}
                target[key] = child
            _merge_into(child, value)
        elif key in _MAX_KEYS:
            # 最大值：None 表示「没有样本」，合并时不能拿 None 去比较
            current = target.get(key)
            if value is None:
                target[key] = current
            else:
                target[key] = value if current is None else max(current, value)
        else:
            target[key] = (target.get(key) or 0) + (value or 0)


def merge_rollups(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """逐键相加；``max`` / ``maxDurationMs`` 取最大值；按名称分组的计数取并集后相加。"""
    merged: dict[str, Any] = {}
    for doc in docs:
        if isinstance(doc, dict):
            _merge_into(merged, doc)
    return merged


def _render_distribution(bucket: dict[str, Any] | None) -> dict[str, Any]:
    bucket = bucket or {}
    samples = int(bucket.get("samples") or 0)
    top = bucket.get("max")
    return {
        "samples": samples,
        "avg": round(float(bucket.get("total") or 0.0) / samples, 3) if samples else None,
        "p50": None,  # 分位数无法由日聚合还原
        "p90": None,
        "max": round(float(top), 3) if top is not None else None,
    }


def render_rollup(
    merged: dict[str, Any],
    *,
    active: dict[str, Any],
    unread: int,
    window_from: datetime,
    window_to: datetime,
    generated_at: datetime | None,
    coverage: dict[str, Any],
) -> dict[str, Any]:
    """把合并后的加总文档渲染成与实时快照同键的响应（另带 ``mode`` 与 ``coverage``）。"""
    scans = dict(merged.get("scans") or {})
    scans["durationSeconds"] = _render_distribution(scans.get("durationSeconds"))
    scans["failures"] = [
        {"errorSummary": reason, "count": count}
        for reason, count in sorted(
            (scans.get("failures") or {}).items(),
            key=lambda item: (-int(item[1] or 0), str(item[0])),
        )[:MAX_FAILURE_REASONS]
    ]
    sources: dict[str, dict[str, Any]] = {}
    for name, bucket in sorted((merged.get("sources") or {}).items()):
        total = int(bucket.get("scans") or 0)
        timed = int(bucket.get("timed") or 0)
        top = bucket.get("maxDurationMs")
        sources[name] = {
            "scans": total,
            "ok": int(bucket.get("ok") or 0),
            "partial": int(bucket.get("partial") or 0),
            "error": int(bucket.get("error") or 0),
            "timeout": int(bucket.get("timeout") or 0),
            "rows": int(bucket.get("rows") or 0),
            "avgRows": round(int(bucket.get("rows") or 0) / total, 1) if total else 0.0,
            "avgDurationMs": (
                round(float(bucket.get("durationMsTotal") or 0.0) / timed, 1) if timed else None
            ),
            "maxDurationMs": round(float(top), 1) if top is not None else None,
            "withoutTiming": int(bucket.get("withoutTiming") or 0),
        }
    handling = dict(merged.get("handling") or {})
    resolve = handling.pop("resolve", {}) or {}
    handling["claimDurationSeconds"] = _render_distribution(handling.pop("claim", None))
    handling["resolveDurationSeconds"] = {
        "manual": _render_distribution(resolve.get("manual")),
        "auto": _render_distribution(resolve.get("auto")),
    }
    llm = dict(merged.get("llm") or {})
    by_model = llm.pop("byModel", {}) or {}
    fallbacks = llm.pop("fallbackReasons", {}) or {}
    llm["byModel"] = [
        {"model": model, **counts}
        for model, counts in sorted(
            by_model.items(),
            key=lambda item: (-int(item[1].get("summaries") or 0), str(item[0])),
        )
    ]
    llm["fallbackReasons"] = [
        {"reason": reason, "count": count}
        for reason, count in sorted(
            fallbacks.items(), key=lambda item: (-int(item[1] or 0), str(item[0])),
        )[:_FAILURE_REASONS_LIMIT]
    ]
    calls = int(llm.get("calls") or 0)
    llm["failureRate"] = round(int(llm.get("failures") or 0) / calls, 3) if calls else 0.0
    moment = generated_at or window_to
    return {
        "window": {
            "from": window_from.isoformat(),
            "to": window_to.isoformat(),
            "hours": round((window_to - window_from).total_seconds() / 3600, 3),
        },
        "generatedAt": moment.isoformat(),
        "mode": "dailyRollup",
        "coverage": coverage,
        "scans": scans,
        "sources": sources,
        "alerts": {**(merged.get("alerts") or {}), "active": active},
        "handling": handling,
        "notifications": {**(merged.get("notifications") or {}), "unread": unread},
        "llm": llm,
    }


async def collect_inputs(
    store: ScanStore, *, window_from: datetime, window_to: datetime, warehouses: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """一段窗口的 5 类原始聚合行（实时口径；输入已由存储层按窗口与仓库过滤）。"""
    started_from, started_to = window_from.isoformat(), window_to.isoformat()
    return {
        "runs": await store.list_runs_for_metrics(
            started_from=started_from, started_to=started_to, warehouses=warehouses,
        ),
        "event_counts": await store.count_alert_events(
            created_from=started_from, created_to=started_to, warehouses=warehouses,
        ),
        "alerts": await store.list_alert_handling(
            touched_from=started_from, touched_to=started_to, warehouses=warehouses,
        ),
        "notification_counts": await store.count_notifications(
            created_from=started_from, created_to=started_to, warehouses=warehouses,
        ),
        "summary_counts": await store.aggregate_scan_summaries(
            started_from=started_from, started_to=started_to, warehouses=warehouses,
        ),
    }


async def run_metric_rollup(
    store: ScanStore,
    *,
    warehouses: list[str],
    now: datetime | None = None,
    timezone: str = DEFAULT_TIMEZONE,
    history_days: int = DEFAULT_HISTORY_DAYS,
    max_batches: int = DEFAULT_MAX_BATCHES,
) -> dict[str, Any]:
    """补齐最近 ``history_days`` 天（不含今天，今天尚未结束）的日聚合，返回可核对的报告。

    只算缺失的「仓库 · 日」，已有的不重算（重跑幂等）；最旧优先，每轮最多 ``max_batches`` 个，
    ``remaining > 0`` 时需要再跑一轮。
    """
    moment = now or datetime.now(_UTC)
    if moment.tzinfo is None:
        raise RollupError("now 必须带时区")
    if int(history_days) < 1:
        raise RollupError(f"history_days 必须 ≥ 1，当前 {history_days}")
    zone = _zone(timezone)
    targets = sorted({str(warehouse) for warehouse in (warehouses or []) if warehouse})
    today = moment.astimezone(zone).date()
    first = today - timedelta(days=int(history_days))
    report: dict[str, Any] = {
        "timezone": timezone,
        "fromDate": first.isoformat(),
        "toDate": (today - timedelta(days=1)).isoformat(),
        "expected": int(history_days) * len(targets),
        "existing": 0, "computed": 0, "remaining": 0, "dates": [],
    }
    if not targets:
        return report
    existing = await store.list_metric_daily(
        date_from=first.isoformat(), date_to=today.isoformat(), warehouses=targets,
    )
    have = {(str(row.get("metricDate")), str(row.get("warehouse"))) for row in existing}
    pending = [
        (first + timedelta(days=offset), warehouse)
        for offset in range(int(history_days))
        for warehouse in targets
        if ((first + timedelta(days=offset)).isoformat(), warehouse) not in have
    ]
    computed: list[tuple[date, str]] = []
    for day, warehouse in pending[: max(1, int(max_batches))]:
        start, end = day_bounds(day, zone)
        inputs = await collect_inputs(store, window_from=start, window_to=end, warehouses=[warehouse])
        rollup = build_rollup(**inputs, window_from=start, window_to=end)
        await store.save_metric_daily([{
            "metricDate": day.isoformat(), "warehouse": warehouse,
            "timezone": timezone, "metrics": rollup,
        }])
        computed.append((day, warehouse))
    report.update({
        "existing": len(have),
        "computed": len(computed),
        "remaining": len(pending) - len(computed),
        "dates": sorted({day.isoformat() for day, _warehouse in computed}),
    })
    return report


async def long_window_metrics(
    store: ScanStore,
    *,
    window_from: datetime,
    window_to: datetime,
    warehouses: list[str],
    timezone: str = DEFAULT_TIMEZONE,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """超过实时上限的窗口：日聚合（整日且结束时刻不晚于 90 天前）+ 实时尾段。"""
    zone = _zone(timezone)
    horizon = window_to - timedelta(hours=METRICS_REALTIME_HOURS)
    daily_days: list[date] = []
    day = window_from.astimezone(zone).date()
    last_full_day = window_to.astimezone(zone).date() - timedelta(days=1)
    while day <= last_full_day:
        _start, end = day_bounds(day, zone)
        if end > horizon:
            break
        daily_days.append(day)
        day += timedelta(days=1)
    rows: list[dict[str, Any]] = []
    if daily_days:
        rows = await store.list_metric_daily(
            date_from=daily_days[0].isoformat(),
            date_to=(daily_days[-1] + timedelta(days=1)).isoformat(),
            warehouses=warehouses,
        )
    # 实时尾段从最后一个已聚合日的结束时刻起算：没有日聚合时整段都按实时取数
    real_time_from = day_bounds(daily_days[-1], zone)[1] if daily_days else window_from
    inputs = await collect_inputs(
        store, window_from=real_time_from, window_to=window_to, warehouses=warehouses,
    )
    real_time = build_metrics(
        **inputs, window_from=real_time_from, window_to=window_to, generated_at=window_to,
    )
    docs = [row["metrics"] for row in rows if isinstance(row.get("metrics"), dict)]
    docs.append(build_rollup(**inputs, window_from=real_time_from, window_to=window_to))
    merged = merge_rollups(docs)
    covered = {str(row.get("metricDate")) for row in rows}
    coverage = {
        "realTimeFrom": real_time_from.isoformat(),
        "realTimeHours": round((window_to - real_time_from).total_seconds() / 3600, 3),
        "dailyDays": len(daily_days),
        "dailyFrom": daily_days[0].isoformat() if daily_days else None,
        "dailyTo": daily_days[-1].isoformat() if daily_days else None,
        # 没有任何仓库聚合行的日期：日聚合尚未补算到，这段时间的计数会被低估
        "missingDays": sum(1 for day in daily_days if day.isoformat() not in covered),
    }
    return render_rollup(
        merged,
        active=real_time["alerts"]["active"],
        unread=int(real_time["notifications"].get("unread") or 0),
        window_from=window_from,
        window_to=window_to,
        generated_at=generated_at,
        coverage=coverage,
    )


__all__ = [
    "DEFAULT_HISTORY_DAYS",
    "DEFAULT_MAX_BATCHES",
    "DEFAULT_TIMEZONE",
    "METRICS_MAX_HOURS",
    "METRICS_REALTIME_HOURS",
    "RollupError",
    "build_rollup",
    "day_bounds",
    "long_window_metrics",
    "merge_rollups",
    "render_rollup",
    "run_metric_rollup",
]
