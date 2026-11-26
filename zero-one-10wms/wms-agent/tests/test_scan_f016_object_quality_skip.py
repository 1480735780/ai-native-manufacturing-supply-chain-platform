"""F-016 第三轮复审回归：对象级数据质量跳过只冻结该对象，不冻结同规则其它对象。

审计 m01655：旧实现把质量跳过当作整条规则级，一条远古 NaN / 未知地点坏行
会让同规则所有正常对象的旧告警永不自动关闭、并禁止降级。本文件验证
service._auto_resolve_cleared 与 _persist_findings 按 (rule_id, object_id) 粒度处理。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.scan.repository import MemoryScanStore
from app.scan.rules.base import Finding, RuleContext, RuleEvaluation
from app.scan.service import _auto_resolve_cleared, _persist_findings, DEFAULT_CONFIG

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)


def _hours_ago(hours: float) -> str:
    return (NOW - timedelta(hours=hours)).isoformat()


def _ctx() -> RuleContext:
    return RuleContext(warehouse="W01", now=NOW)


def _seed_temperature_alert(store: MemoryScanStore, *, object_id: str, fingerprint: str,
                            severity: str = "P0") -> None:
    asyncio.run(store.upsert_alert({
        "fingerprint": fingerprint,
        "severity": severity,
        "ruleId": "TEMP-EXCURSION",
        "ruleVersion": "v0.2.1",
        "objectType": "temperature_location",
        "objectId": object_id,
        "dimension": {"warehouse": "W01", "kind": "excursion"},
        "title": f"TEMP-EXCURSION {severity} {object_id}",
        "evidence": {},
        "suggestedActions": [],
        "warehouseId": "W01",
        "lastSeenAt": _hours_ago(100),
    }))


def test_object_quality_skip_freezes_only_that_object() -> None:
    """A 地点有坏行被对象级跳过，B 地点的旧告警仍应正常自动关闭。"""
    store = MemoryScanStore()
    _seed_temperature_alert(store, object_id="W01|一号冷库", fingerprint="fp-a-old")
    _seed_temperature_alert(store, object_id="W01|常温库A", fingerprint="fp-b-old")

    # 本次没有任何 finding：两个地点的旧条件都"消失"了
    counts: dict = {}
    asyncio.run(_auto_resolve_cleared(
        store, evaluations={}, rule_ok={"TEMP-EXCURSION": True}, findings={},
        scan_id="scan-obj", warehouse="W01", trace_id="trace-obj",
        started_at=NOW.isoformat(), dry_run=False, partial=False, counts=counts,
        # 仅 A 地点本次存在数据质量坏行
        quality_skipped_objects={("TEMP-EXCURSION", "W01|一号冷库")},
    ))

    assert counts.get("alertsAutoResolved") == 1
    states = {a["objectId"]: a["state"] for a in store.alerts.values()}
    # A 被冻结保持 open，B 正常关闭
    assert states["W01|一号冷库"] == "open"
    assert states["W01|常温库A"] == "resolved"


def test_rule_level_quality_skip_still_freezes_whole_rule() -> None:
    """整条规则级跳过（如温度 partial 源）仍冻结该规则全部对象。"""
    store = MemoryScanStore()
    _seed_temperature_alert(store, object_id="W01|一号冷库", fingerprint="fp-a-old")
    _seed_temperature_alert(store, object_id="W01|常温库A", fingerprint="fp-b-old")

    evaluation = RuleEvaluation()
    evaluation.skip("TEMP-EXCURSION")
    counts: dict = {}
    asyncio.run(_auto_resolve_cleared(
        store, evaluations={"temperature": evaluation},
        rule_ok={"TEMP-EXCURSION": True}, findings={},
        scan_id="scan-rule", warehouse="W01", trace_id="trace-rule",
        started_at=NOW.isoformat(), dry_run=False, partial=False, counts=counts,
    ))

    assert counts.get("alertsAutoResolved") is None
    assert all(a["state"] == "open" for a in store.alerts.values())


def test_persist_findings_no_downgrade_applies_per_object() -> None:
    """对象级跳过只阻止该对象的降级，同规则其它对象仍可正常降级。"""
    a = Finding(
        rule_id="TEMP-EXCURSION", rule_version="v0.2.1", severity="P1",
        object_type="temperature_location", object_id="W01|一号冷库",
        dimension={"warehouse": "W01", "kind": "excursion"}, evidence={},
    )
    b = Finding(
        rule_id="TEMP-EXCURSION", rule_version="v0.2.1", severity="P1",
        object_type="temperature_location", object_id="W01|常温库A",
        dimension={"warehouse": "W01", "kind": "excursion"}, evidence={},
    )

    store = MemoryScanStore()
    # 用 finding 的真实指纹 seed 旧 P0，确保 upsert 走"更新"分支而非"新建"
    for finding, title in ((a, "A P0"), (b, "B P0")):
        asyncio.run(store.upsert_alert({
            **finding.to_alert(),
            "severity": "P0",
            "title": title,
            "warehouseId": "W01",
            "lastSeenAt": _hours_ago(100),
        }))

    counts: dict = {
        "alertsCreated": 0, "alertsEscalated": 0, "alertsUpdated": 0,
        "alertsSuppressed": 0, "alertsReplayed": 0,
        "notifications": 0, "notificationsUnrouted": 0,
    }
    asyncio.run(_persist_findings(
        {a.fingerprint: a, b.fingerprint: b}, store, "scan-dg", "W01",
        NOW.isoformat(), "dry_run", counts, trace_id="trace-dg",
        config=DEFAULT_CONFIG, actor_type="system", actor_id="scanner",
        configured_recipients=[],
        no_downgrade_objects={("TEMP-EXCURSION", "W01|一号冷库")},
    ))

    by_object = {x["objectId"]: x["severity"] for x in store.alerts.values()}
    # A 被对象级跳过保护，保持 P0；B 无保护，降级为 P1
    assert by_object["W01|一号冷库"] == "P0"
    assert by_object["W01|常温库A"] == "P1"
