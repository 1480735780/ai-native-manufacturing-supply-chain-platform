"""巡检指标聚合（阶段7）：把存储层的只读聚合结果拼成一份口径固定的指标快照。

原则
----
- 只读：不改任何业务状态，不触发扫描 / 关闭 / 通知。
- 口径显式、可复核：
  * 扫描按 ``started_at`` 入窗（窗口左闭右开）；在途扫描计入总数，不计入耗时与 counts 求和；
  * 告警的新建 / 升级 / 认领 / 自动关闭 / 人工状态流转取事件表，按**事件时间**入窗
    （事件是耐久事实，扫描记录被清理后仍然成立）；
  * 扫描 ``counts`` 求和只用于「不留事件行」的事实：抑制、重放、未路由通知、LLM 用量；
  * 认领 / 关闭时长按**动作发生时间**入窗，起点是该告警的首次发现时间；
  * 活跃告警是**当前快照**，与时间窗无关；
- 不猜测：历史扫描没有取数耗时的计入 ``withoutTiming``；时间为负（时钟错乱）的样本丢弃。
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.scan.repository import (
    ACTIVE_STATES,
    AUTO_RESOLVE_EVENT,
    SEVERITY_RANK,
    _parse_iso,
)

TERMINAL_RUN_STATES = ("succeeded", "failed", "cancelled")
SOURCE_STATUSES = ("ok", "partial", "error", "timeout")
NOTIFICATION_STATUSES = ("sent", "pending", "failed")
# 只在窗口内「终态」扫描的 counts 上求和的键（这些事实不落事件行）
SUMMED_COUNT_KEYS = (
    "alertsSuppressed",
    "alertsReplayed",
    "staleCheckSkipped",
    "notificationsUnrouted",
    "llmCalls",
    "llmFailures",
    "promptTokens",
    "completionTokens",
    "summariesLlm",
    "summariesTemplate",
)
MAX_FAILURE_REASONS = 5
AUTO_RESOLVE_REASON_PREFIX = AUTO_RESOLVE_EVENT + ":"


def _in_window(moment: datetime | None, lo: datetime, hi: datetime) -> bool:
    return moment is not None and lo <= moment < hi


def _seconds(start: datetime | None, end: datetime | None) -> float | None:
    """两个时间之差（秒）；缺任一端或为负（时钟错乱）返回 None（不进样本）。"""
    if start is None or end is None:
        return None
    delta = (end - start).total_seconds()
    return delta if delta >= 0 else None


def _percentile(ordered: list[float], ratio: float) -> float:
    """最近秩分位数：不做插值，样本少时不虚构精度。"""
    index = max(0, min(len(ordered) - 1, math.ceil(ratio * len(ordered)) - 1))
    return round(ordered[index], 3)


def _distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"samples": 0, "avg": None, "p50": None, "p90": None, "max": None}
    ordered = sorted(values)
    return {
        "samples": len(ordered),
        "avg": round(sum(ordered) / len(ordered), 3),
        "p50": _percentile(ordered, 0.5),
        "p90": _percentile(ordered, 0.9),
        "max": round(ordered[-1], 3),
    }


def _count(event_counts: list[dict[str, Any]], event_type: str, to_state: str | None = None) -> int:
    return sum(
        int(row.get("count") or 0)
        for row in event_counts
        if row.get("eventType") == event_type
        and (to_state is None or row.get("toState") == to_state)
    )


def _build_scans(runs: list[dict[str, Any]]) -> tuple[dict[str, Any], Counter[str]]:
    by_status: Counter[str] = Counter(str(run.get("status") or "") for run in runs)
    by_trigger: Counter[str] = Counter(str(run.get("trigger") or "manual") for run in runs)
    durations: list[float] = []
    failures: Counter[str] = Counter()
    summed: Counter[str] = Counter()
    for run in runs:
        started, finished = _parse_iso(run.get("startedAt")), _parse_iso(run.get("finishedAt"))
        duration = _seconds(started, finished)
        if duration is not None:
            durations.append(duration)
        if run.get("status") not in TERMINAL_RUN_STATES:
            continue
        if run.get("status") == "failed":
            failures[str(run.get("errorSummary") or "unknown")] += 1
        counts = run.get("counts") or {}
        for key in SUMMED_COUNT_KEYS:
            summed[key] += int(counts.get(key) or 0)
    scans = {
        "total": len(runs),
        "succeeded": by_status.get("succeeded", 0),
        "failed": by_status.get("failed", 0),
        "cancelled": by_status.get("cancelled", 0),
        "inProgress": sum(by_status.get(state, 0) for state in ("queued", "running")),
        "partial": sum(1 for run in runs if run.get("partial")),
        "byTrigger": {
            "manual": by_trigger.get("manual", 0),
            "schedule": by_trigger.get("schedule", 0),
            "retry": by_trigger.get("retry", 0),
        },
        "durationSeconds": _distribution(durations),
        "failures": [
            {"errorSummary": reason, "count": count}
            for reason, count in sorted(failures.items(), key=lambda item: (-item[1], item[0]))[
                :MAX_FAILURE_REASONS
            ]
        ],
    }
    return scans, summed


def _build_sources(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    raw: dict[str, dict[str, Any]] = {}
    for run in runs:
        for entry in run.get("sourceStatus") or []:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("source") or "unknown")
            bucket = raw.setdefault(
                name,
                {
                    "scans": 0, "ok": 0, "partial": 0, "error": 0, "timeout": 0, "rows": 0,
                    "withoutTiming": 0, "durations": [],
                },
            )
            bucket["scans"] += 1
            status = str(entry.get("status") or "")
            if status in SOURCE_STATUSES:
                bucket[status] += 1
            bucket["rows"] += int(entry.get("rows") or 0)
            duration = entry.get("durationMs")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool):
                bucket["durations"].append(float(duration))
            else:
                bucket["withoutTiming"] += 1
    sources: dict[str, dict[str, Any]] = {}
    for name in sorted(raw):
        bucket = raw[name]
        durations = bucket["durations"]
        sources[name] = {
            "scans": bucket["scans"],
            "ok": bucket["ok"],
            "partial": bucket["partial"],
            "error": bucket["error"],
            "timeout": bucket["timeout"],
            "rows": bucket["rows"],
            "avgRows": round(bucket["rows"] / bucket["scans"], 1) if bucket["scans"] else 0.0,
            "avgDurationMs": round(sum(durations) / len(durations), 1) if durations else None,
            "maxDurationMs": round(max(durations), 1) if durations else None,
            "withoutTiming": bucket["withoutTiming"],
        }
    return sources


def _build_alerts(
    event_counts: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    summed: Counter[str],
) -> dict[str, Any]:
    active = [alert for alert in alerts if alert.get("state") in ACTIVE_STATES]
    by_severity: Counter[str] = Counter(str(alert.get("severity") or "") for alert in active)
    by_rule: Counter[str] = Counter(str(alert.get("ruleId") or "") for alert in active)
    return {
        "created": _count(event_counts, "created"),
        "escalated": _count(event_counts, "escalated"),
        "suppressed": summed["alertsSuppressed"],
        "replayed": summed["alertsReplayed"],
        "autoResolved": _count(event_counts, AUTO_RESOLVE_EVENT),
        "staleCheckSkipped": summed["staleCheckSkipped"],
        "acknowledged": _count(event_counts, "transition", "acknowledged"),
        "closedManually": _count(event_counts, "transition", "resolved"),
        "ignored": _count(event_counts, "transition", "ignored"),
        "active": {
            "total": len(active),
            "open": sum(1 for alert in active if alert.get("state") == "open"),
            "acknowledged": sum(1 for alert in active if alert.get("state") == "acknowledged"),
            "bySeverity": {
                severity: by_severity.get(severity, 0)
                for severity in sorted(SEVERITY_RANK, key=SEVERITY_RANK.get, reverse=True)
            },
            "byRule": [
                {"ruleId": rule_id, "count": count}
                for rule_id, count in sorted(by_rule.items(), key=lambda item: (-item[1], item[0]))
            ],
        },
    }


def _build_handling(
    alerts: list[dict[str, Any]], window_from: datetime, window_to: datetime,
) -> dict[str, Any]:
    claim_durations: list[float] = []
    manual_resolves: list[float] = []
    auto_resolves: list[float] = []
    claimed_in_window = 0
    for alert in alerts:
        first_seen = _parse_iso(alert.get("firstSeenAt"))
        claimed_at = _parse_iso(alert.get("claimedAt"))
        if _in_window(claimed_at, window_from, window_to):
            claimed_in_window += 1
            duration = _seconds(first_seen, claimed_at)
            if duration is not None:
                claim_durations.append(duration)
        resolved_at = _parse_iso(alert.get("resolvedAt"))
        if _in_window(resolved_at, window_from, window_to):
            duration = _seconds(first_seen, resolved_at)
            if duration is None:
                continue
            if str(alert.get("resolvedReason") or "").startswith(AUTO_RESOLVE_REASON_PREFIX):
                auto_resolves.append(duration)
            else:
                manual_resolves.append(duration)
    return {
        "claimed": claimed_in_window,
        "claimDurationSeconds": _distribution(claim_durations),
        "resolveDurationSeconds": {
            "manual": _distribution(manual_resolves),
            "auto": _distribution(auto_resolves),
        },
    }


def _build_notifications(
    notification_counts: list[dict[str, Any]], summed: Counter[str],
) -> dict[str, Any]:
    by_status: Counter[str] = Counter()
    read = unread = 0
    for row in notification_counts:
        count = int(row.get("count") or 0)
        if row.get("createdInWindow"):
            by_status[str(row.get("status") or "unknown")] += count
        if row.get("readInWindow"):
            read += count
        if row.get("unreadNow"):
            unread += count
    notifications: dict[str, Any] = {
        status: by_status.get(status, 0) for status in NOTIFICATION_STATUSES
    }
    notifications["other"] = sum(
        count for status, count in by_status.items() if status not in NOTIFICATION_STATUSES
    )
    notifications.update(
        {"read": read, "unread": unread, "unrouted": summed["notificationsUnrouted"]}
    )
    return notifications


def _build_llm(
    summary_counts: list[dict[str, Any]], summed: Counter[str],
) -> dict[str, Any]:
    by_model: dict[str, dict[str, int]] = {}
    fallbacks: Counter[str] = Counter()
    for row in summary_counts:
        count = int(row.get("summaries") or 0)
        if row.get("summarySource") == "llm":
            model = str(row.get("model") or "unknown")
            bucket = by_model.setdefault(model, {"summaries": 0, "promptTokens": 0, "completionTokens": 0})
            bucket["summaries"] += count
            bucket["promptTokens"] += int(row.get("promptTokens") or 0)
            bucket["completionTokens"] += int(row.get("completionTokens") or 0)
        elif row.get("fallbackReason"):
            fallbacks[str(row.get("fallbackReason"))] += count
    calls, failures = summed["llmCalls"], summed["llmFailures"]
    return {
        "calls": calls,
        "failures": failures,
        "failureRate": round(failures / calls, 4) if calls else 0.0,
        "promptTokens": summed["promptTokens"],
        "completionTokens": summed["completionTokens"],
        "summariesLlm": summed["summariesLlm"],
        "summariesTemplate": summed["summariesTemplate"],
        "byModel": [
            {"model": model, **by_model[model]}
            for model in sorted(
                by_model, key=lambda name: (-by_model[name]["summaries"], name)
            )
        ],
        "fallbackReasons": [
            {"reason": reason, "count": count}
            for reason, count in sorted(fallbacks.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


def build_metrics(
    *,
    runs: list[dict[str, Any]],
    event_counts: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    notification_counts: list[dict[str, Any]],
    summary_counts: list[dict[str, Any]],
    window_from: datetime,
    window_to: datetime,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """纯函数：输入是 ScanStore 的 5 个只读聚合结果，输出一份指标快照。"""
    scans, summed = _build_scans(runs)
    hours = (window_to - window_from).total_seconds() / 3600
    return {
        "window": {
            "from": window_from.isoformat(),
            "to": window_to.isoformat(),
            "hours": round(hours, 3),
        },
        "generatedAt": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "scans": scans,
        "sources": _build_sources(runs),
        "alerts": _build_alerts(event_counts, alerts, summed),
        "handling": _build_handling(alerts, window_from, window_to),
        "notifications": _build_notifications(notification_counts, summed),
        "llm": _build_llm(summary_counts, summed),
    }
