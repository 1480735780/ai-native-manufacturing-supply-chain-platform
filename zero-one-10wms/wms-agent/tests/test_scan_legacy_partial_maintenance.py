"""旧格式 SCAN-PARTIAL 告警的安全收敛回归。"""

from __future__ import annotations

import pytest

from app.scan.maintenance import (
    LEGACY_RESOLVE_REASON,
    is_legacy_partial_alert,
    legacy_source,
    resolve_legacy_scan_partial_alerts,
)
from app.scan.repository import MemoryScanStore

pytestmark = pytest.mark.asyncio


def _alert(
    alert_id: str,
    *,
    object_id: str,
    source: str,
    rule_version: str = "v1",
    state: str = "open",
) -> dict:
    return {
        "fingerprint": f"sha256:{alert_id}",
        "ruleId": "SCAN-PARTIAL",
        "ruleVersion": rule_version,
        "severity": "P2",
        "objectType": "scan_source",
        "objectId": object_id,
        "dimension": {"warehouse": "W01", "source": source},
        "title": f"SCAN-PARTIAL P2 {object_id}",
        "evidence": {"reason": "source partial", "source": source},
        "suggestedActions": ["RETRY_SCAN"],
        "lastSeenAt": "2026-11-26T10:00:00+00:00",
        "scanId": object_id if object_id.startswith("scan-") else f"scan-{alert_id}",
        "traceId": f"trace-{alert_id}",
        "state": state,
        "warehouseId": "W01",
    }


async def _save_run(
    store: MemoryScanStore,
    scan_id: str,
    *,
    status: str,
    finished_at: str | None,
    source: str = "no_up",
    source_status: str = "ok",
    truncated: bool = False,
) -> None:
    await store.save_run({
        "scanId": scan_id,
        "status": status,
        "partial": source_status != "ok",
        "warehouse": "W01",
        "startedAt": "2026-11-26T09:00:00+00:00",
        "finishedAt": finished_at,
        "sourceStatus": [{
            "source": source,
            "status": source_status,
            "truncated": truncated,
        }],
    })


async def _seed(store: MemoryScanStore, *, with_healthy: bool = True) -> None:
    await store.upsert_alert(_alert(
        "legacy-1", object_id="scan-31f29699a8df4d35", source="no_up",
    ))
    await store.upsert_alert(_alert(
        "legacy-2", object_id="scan-ae5e4c80ec63428b", source="no_up",
    ))
    await store.upsert_alert(_alert(
        "current-1", object_id="delay", source="delay",
    ))
    await store.upsert_alert(_alert(
        "current-2", object_id="expiry", source="expiry", state="resolved",
    ))
    await _save_run(
        store, "scan-31f29699a8df4d35", status="succeeded",
        finished_at="2026-11-26T10:05:00+00:00", source_status="partial",
        truncated=True,
    )
    await _save_run(
        store, "scan-ae5e4c80ec63428b", status="succeeded",
        finished_at="2026-11-26T10:10:00+00:00", source_status="partial",
        truncated=True,
    )
    if with_healthy:
        await _save_run(
            store, "scan-healthy", status="succeeded",
            finished_at="2026-11-26T11:00:00+00:00",
        )


async def test_is_legacy_partial_alert_rules():
    legacy = _alert("x", object_id="scan-abc", source="no_up")
    assert is_legacy_partial_alert(legacy) is True
    assert legacy_source(legacy) == "no_up"
    assert is_legacy_partial_alert(_alert("y", object_id="no_up", source="no_up")) is False
    assert is_legacy_partial_alert(_alert(
        "z", object_id="scan-abc", source="no_up", rule_version="v2",
    )) is False
    assert is_legacy_partial_alert(_alert(
        "w", object_id="scan-abc", source="no_up", state="resolved",
    )) is False
    missing_source = _alert("m", object_id="scan-missing", source="no_up")
    missing_source["dimension"]["source"] = "scan-missing"
    missing_source["evidence"]["source"] = "scan-missing"
    assert legacy_source(missing_source) is None


async def test_dry_run_reports_without_changing_state():
    store = MemoryScanStore()
    await _seed(store)
    result = await resolve_legacy_scan_partial_alerts(store, dry_run=True)
    assert result["legacyActive"] == 2
    assert result["dryRun"] is True
    assert result["resolvedAlertIds"] == []
    assert sorted(result["wouldResolveAlertIds"]) == sorted(
        int(a["alertId"]) for a in store.alerts.values()
        if str(a.get("objectId") or "").startswith("scan-")
    )
    states = {a["objectId"]: a["state"] for a in store.alerts.values()}
    assert states["scan-31f29699a8df4d35"] == "open"


async def test_resolves_only_after_later_healthy_scan_and_is_idempotent():
    store = MemoryScanStore()
    await _seed(store)
    first = await resolve_legacy_scan_partial_alerts(store)
    assert first["legacyActive"] == 2
    assert len(first["resolvedAlertIds"]) == 2
    assert first["skipped"] == []

    by_object = {a["objectId"]: a for a in store.alerts.values()}
    assert by_object["scan-31f29699a8df4d35"]["state"] == "resolved"
    assert "scan-healthy" in by_object["scan-31f29699a8df4d35"]["resolvedReason"]
    assert LEGACY_RESOLVE_REASON.split(":")[0] in by_object["scan-31f29699a8df4d35"]["resolvedReason"]
    assert by_object["delay"]["state"] == "open"

    events = [e for e in store.events if e.get("eventType") == "transition"]
    assert len(events) == 2

    second = await resolve_legacy_scan_partial_alerts(store)
    assert second["legacyActive"] == 0
    assert second["resolvedAlertIds"] == []


async def test_no_later_healthy_scan_keeps_legacy_alert_open():
    store = MemoryScanStore()
    await _seed(store, with_healthy=False)
    result = await resolve_legacy_scan_partial_alerts(store)
    assert result["resolvedAlertIds"] == []
    assert {item["reason"] for item in result["skipped"]} == {"no_later_healthy_scan"}
    assert all(a["state"] == "open" for a in store.alerts.values() if a["objectId"].startswith("scan-"))


async def test_current_partial_for_same_source_blocks_legacy_resolution():
    store = MemoryScanStore()
    await _seed(store)
    await store.upsert_alert(_alert("current-no-up", object_id="no_up", source="no_up"))
    result = await resolve_legacy_scan_partial_alerts(store)
    assert result["resolvedAlertIds"] == []
    assert {item["reason"] for item in result["skipped"]} == {"current_partial_active"}


async def test_pagination_covers_more_than_200_partial_alerts():
    store = MemoryScanStore()
    for index in range(205):
        await store.upsert_alert(_alert(
            f"legacy-{index}", object_id=f"scan-{index:04d}", source="no_up",
        ))
    result = await resolve_legacy_scan_partial_alerts(store, dry_run=True)
    assert result["pages"] >= 2
    assert result["legacyActive"] == 205
    assert result["resolvedAlertIds"] == []
    assert len(result["skipped"]) == 205
