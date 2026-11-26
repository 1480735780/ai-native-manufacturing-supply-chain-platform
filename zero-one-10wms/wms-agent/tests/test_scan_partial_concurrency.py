"""SCAN-PARTIAL 并发误关窗口回归（审计 m04299 第 3 组）。

缺陷：告警 `lastSeenAt` 原取「扫描开始时间」（`ctx.now`）。慢扫描（partial 超时重试）
可能在并发健康扫描已经开始之后才落库，此时健康扫描的 `last_seen_at < started_at`
条件会把「刚写入」的告警当成旧告警关掉；PG 侧还用数据库 `now()`，DB 时钟落后
agent 时同样有窗口。修复：
  1. 落库时 `lastSeenAt = 落库时刻`（agent 侧时间），Memory/PG 一致；
  2. PG 的两次 UPDATE 改为 `COALESCE(%s::timestamptz, now())`，不再用库时钟。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.scan.repository import MemoryScanStore
from app.scan.rules.base import Finding, RuleContext
from app.scan.service import (
    DEFAULT_CONFIG,
    SCAN_PARTIAL_RULE_ID,
    SCAN_PARTIAL_RULE_VERSION,
    _auto_resolve_cleared,
    _persist_findings,
)

pytestmark = pytest.mark.asyncio

REPO = Path(__file__).resolve().parents[1]


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _counts() -> dict:
    return {
        "alertsCreated": 0,
        "alertsUpdated": 0,
        "alertsEscalated": 0,
        "alertsSuppressed": 0,
        "notifications": 0,
    }


def _partial_alert(store_alerts, source: str = "no_up") -> dict:
    rows = list(store_alerts.values()) if isinstance(store_alerts, dict) else list(store_alerts)
    matched = [a for a in rows if a["ruleId"] == SCAN_PARTIAL_RULE_ID and a["objectId"] == source]
    assert matched, "SCAN-PARTIAL alert not found"
    return matched[-1]


def _partial_finding(scan_id: str) -> Finding:
    ctx = RuleContext(warehouse="W01", now=datetime.now(timezone.utc))
    return Finding(
        rule_id=SCAN_PARTIAL_RULE_ID,
        rule_version=SCAN_PARTIAL_RULE_VERSION,
        severity="P2",
        object_type="scan_source",
        object_id="no_up",
        dimension={"warehouse": "W01", "source": "no_up"},
        evidence={"reason": "source partial", "source": "no_up", "scanId": scan_id},
        suggested_actions=("RETRY_SCAN",),
    ), ctx


async def _save_partial_run(
    store: MemoryScanStore, scan_id: str, *, started_at: str, finished_at: str,
) -> None:
    await store.save_run({
        "scanId": scan_id,
        "status": "succeeded",
        "partial": True,
        "warehouse": "W01",
        "startedAt": started_at,
        "finishedAt": finished_at,
        "sourceStatus": [{"source": "no_up", "status": "partial", "truncated": True}],
    })


async def test_persist_uses_write_time_not_scan_start():
    """lastSeenAt 必须等于落库时刻，而不是扫描开始时间。"""
    store = MemoryScanStore()
    finding, ctx = _partial_finding("scan-slow")
    started_at = ctx.now - timedelta(minutes=30)  # 慢扫描：30 分钟前开始
    counts = _counts()
    await _persist_findings(
        {finding.fingerprint: finding},
        store,
        "scan-slow",
        "W01",
        _iso(started_at),
        "dry_run",
        counts,
        trace_id="trace-slow",
        config=DEFAULT_CONFIG,
        actor_type="user",
        actor_id="tester",
        configured_recipients=["admin"],
        recipient_user_id="admin",
    )
    alert = _partial_alert(store.alerts)
    persisted = datetime.fromisoformat(alert["lastSeenAt"])
    # 用开始时间会恰好等于 started_at；修复后应明显晚于开始时间。
    assert persisted > started_at + timedelta(minutes=29)


async def test_concurrent_healthy_scan_cannot_close_alert_written_after_its_start():
    """健康扫描 started_at 早于告警落库时刻 → 不得关闭（并发误关窗口）。"""
    store = MemoryScanStore()
    finding, ctx = _partial_finding("scan-slow")
    counts = _counts()
    await _persist_findings(
        {finding.fingerprint: finding},
        store,
        "scan-slow",
        "W01",
        _iso(ctx.now - timedelta(minutes=30)),
        "dry_run",
        counts,
        trace_id="trace-slow",
        config=DEFAULT_CONFIG,
        actor_type="user",
        actor_id="tester",
        configured_recipients=["admin"],
        recipient_user_id="admin",
    )
    before = dict(_partial_alert(store.alerts))

    # 并发健康扫描：5 分钟前开始；partial 扫描在健康扫描开始后才结束。
    healthy_started = datetime.now(timezone.utc) - timedelta(minutes=5)
    await _save_partial_run(
        store,
        "scan-slow",
        started_at=_iso(ctx.now - timedelta(minutes=30)),
        finished_at=_iso(datetime.now(timezone.utc) - timedelta(minutes=1)),
    )
    resolve_counts: dict[str, int] = {}
    await _auto_resolve_cleared(
        store,
        evaluations={},
        rule_ok={SCAN_PARTIAL_RULE_ID: True},
        findings={},
        scan_id="scan-healthy",
        warehouse="W01",
        trace_id="trace-healthy",
        started_at=_iso(healthy_started),
        dry_run=False,
        partial=False,
        counts=resolve_counts,
        scanned_sources={"no_up"},
    )

    after = _partial_alert(store.alerts)
    assert after["state"] == "open", "并发健康扫描不得关闭在其开始之后落库的 partial 告警"
    assert after["alertId"] == before["alertId"]


async def test_serial_healthy_scan_still_closes_old_partial_alert():
    """串行场景（告警早于本次扫描）仍必须关闭，避免修复把正常关闭也挡掉。"""
    store = MemoryScanStore()
    finding, ctx = _partial_finding("scan-slow")
    counts = _counts()
    await _persist_findings(
        {finding.fingerprint: finding},
        store,
        "scan-slow",
        "W01",
        _iso(ctx.now - timedelta(minutes=30)),
        "dry_run",
        counts,
        trace_id="trace-slow",
        config=DEFAULT_CONFIG,
        actor_type="user",
        actor_id="tester",
        configured_recipients=["admin"],
        recipient_user_id="admin",
    )
    alert = _partial_alert(store.alerts)
    # 人为把 lastSeenAt 回拨到 20 分钟前，模拟「告警确实早于本次扫描」。
    alert["lastSeenAt"] = _iso(datetime.now(timezone.utc) - timedelta(minutes=20))
    await _save_partial_run(
        store,
        "scan-slow",
        started_at=_iso(ctx.now - timedelta(minutes=30)),
        finished_at=_iso(datetime.now(timezone.utc) - timedelta(minutes=10)),
    )

    resolve_counts: dict[str, int] = {}
    await _auto_resolve_cleared(
        store,
        evaluations={},
        rule_ok={SCAN_PARTIAL_RULE_ID: True},
        findings={},
        scan_id="scan-healthy",
        warehouse="W01",
        trace_id="trace-healthy",
        started_at=_iso(datetime.now(timezone.utc) - timedelta(minutes=5)),
        dry_run=False,
        partial=False,
        counts=resolve_counts,
        scanned_sources={"no_up"},
    )

    after = _partial_alert(store.alerts)
    assert after["state"] == "resolved"
    assert resolve_counts.get("alertsAutoResolved") == 1


async def test_pg_alert_updates_use_agent_timestamp():
    """PG 两次 UPDATE 不再用库时钟 now()，避免 DB 时钟落后造成同类窗口。"""
    source = (REPO / "app" / "scan" / "repository.py").read_text(encoding="utf-8")
    assert "last_seen_at = now()" not in source
    assert source.count("last_seen_at = COALESCE(%s::timestamptz, now())") == 2
