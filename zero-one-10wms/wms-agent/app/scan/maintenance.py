"""旧格式 SCAN-PARTIAL 告警的一次性安全收敛。

只关闭同时满足以下条件的旧格式活动告警：
- 能确定仓库与来源；
- 触发扫描已结束；
- 同来源在触发扫描结束后已有成功且未截断的健康扫描；
- 当前不存在同来源的新格式活动告警。

任何证据缺失都跳过，宁可留下旧告警也不误关仍处于 partial 的来源。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.scan.repository import ACTIVE_STATES, TERMINAL_RUN_STATES, ScanStore, _parse_iso
from app.scan.service import SCAN_PARTIAL_RULE_ID, SCAN_PARTIAL_RULE_VERSION

LEGACY_PARTIAL_OBJECT_PREFIX = "scan-"
LEGACY_RESOLVE_REASON = (
    "legacy_object_id_migration: 旧格式 objectId=scan-<id> 已按来源收敛，"
    "同来源后续健康扫描={healthy_scan_id}"
)


def is_legacy_partial_alert(alert: dict[str, Any]) -> bool:
    if str(alert.get("ruleId") or "") != SCAN_PARTIAL_RULE_ID:
        return False
    if str(alert.get("ruleVersion") or "") != SCAN_PARTIAL_RULE_VERSION:
        return False
    if str(alert.get("state") or "") not in ACTIVE_STATES:
        return False
    return str(alert.get("objectId") or "").startswith(LEGACY_PARTIAL_OBJECT_PREFIX)


def legacy_source(alert: dict[str, Any]) -> str | None:
    for container in (alert.get("dimension"), alert.get("evidence")):
        if not isinstance(container, dict):
            continue
        source = str(container.get("source") or "").strip()
        if source and not source.startswith(LEGACY_PARTIAL_OBJECT_PREFIX):
            return source
    return None


async def _list_active_partial_alerts(
    store: ScanStore, *, page_size: int = 200,
) -> tuple[list[dict[str, Any]], int]:
    alerts: list[dict[str, Any]] = []
    cursor_at: str | None = None
    cursor_id: int | None = None
    pages = 0
    while True:
        page = await store.list_alerts_page(
            {"ruleId": SCAN_PARTIAL_RULE_ID},
            last_seen_at=cursor_at,
            last_alert_id=cursor_id,
            page_size=page_size,
        )
        pages += 1
        if not page:
            break
        alerts.extend(
            dict(alert) for alert in page
            if str(alert.get("state") or "") in ACTIVE_STATES
        )
        if len(page) < page_size:
            break
        last = page[-1]
        cursor_at = str(last.get("lastSeenAt") or "")
        cursor_id = int(last["alertId"])
    return alerts, pages


async def resolve_legacy_scan_partial_alerts(
    store: ScanStore, *, dry_run: bool = False,
) -> dict[str, Any]:
    active_alerts, pages = await _list_active_partial_alerts(store)
    legacy = [alert for alert in active_alerts if is_legacy_partial_alert(alert)]
    current_by_source: set[tuple[str, str]] = set()
    for alert in active_alerts:
        if is_legacy_partial_alert(alert):
            continue
        source = str(alert.get("objectId") or "")
        if source:
            current_by_source.add((str(alert.get("warehouseId") or ""), source))

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    skipped: list[dict[str, Any]] = []
    for alert in legacy:
        source = legacy_source(alert)
        warehouse = str(alert.get("warehouseId") or "")
        if not warehouse or not source:
            skipped.append({
                "alertId": alert.get("alertId"),
                "objectId": alert.get("objectId"),
                "reason": "source_or_warehouse_missing",
            })
            continue
        grouped[(warehouse, source)].append(alert)

    resolved: list[int] = []
    would_resolve: list[int] = []
    for (warehouse, source), alerts in sorted(grouped.items()):
        if (warehouse, source) in current_by_source:
            for alert in alerts:
                skipped.append({
                    "alertId": alert.get("alertId"),
                    "objectId": alert.get("objectId"),
                    "reason": "current_partial_active",
                })
            continue

        cutoffs: list[Any] = []
        unavailable = False
        for alert in alerts:
            run = await store.get_run(str(alert.get("scanId") or ""))
            if run is None or run.get("status") not in TERMINAL_RUN_STATES:
                unavailable = True
                break
            finished = _parse_iso(run.get("finishedAt"))
            if finished is None:
                unavailable = True
                break
            cutoffs.append(finished)
            cutoffs.append(_parse_iso(alert.get("lastSeenAt")))
        if unavailable:
            for alert in alerts:
                skipped.append({
                    "alertId": alert.get("alertId"),
                    "objectId": alert.get("objectId"),
                    "reason": "source_scan_not_finished",
                })
            continue

        cutoff = max(moment for moment in cutoffs if moment is not None)
        healthy = await store.find_healthy_source_scan(
            warehouse=warehouse,
            source=source,
            after_iso=cutoff.isoformat(),
        )
        if healthy is None:
            for alert in alerts:
                skipped.append({
                    "alertId": alert.get("alertId"),
                    "objectId": alert.get("objectId"),
                    "reason": "no_later_healthy_scan",
                })
            continue

        for alert in alerts:
            alert_id = int(alert["alertId"])
            if dry_run:
                would_resolve.append(alert_id)
                continue
            closed = await store.transition_alert(
                alert_id,
                "resolved",
                reason=LEGACY_RESOLVE_REASON.format(
                    healthy_scan_id=healthy.get("scanId") or "unknown"
                ),
                actor_type="system",
                actor_id="maintenance:legacy_scan_partial",
            )
            if closed is None:
                skipped.append({
                    "alertId": alert_id,
                    "objectId": alert.get("objectId"),
                    "reason": "state_changed_concurrently",
                })
            else:
                resolved.append(alert_id)

    return {
        "scanned": len(active_alerts),
        "pages": pages,
        "legacyActive": len(legacy),
        "dryRun": dry_run,
        "resolvedAlertIds": resolved,
        "wouldResolveAlertIds": would_resolve,
        "skipped": skipped,
        "objectIds": [alert.get("objectId") for alert in legacy],
    }


def main(argv: list[str] | None = None) -> int:
    import asyncio
    import json
    import os
    import sys

    from app.scan.repository import build_scan_store

    args = list(sys.argv[1:] if argv is None else argv)
    backend = os.getenv("WMS_AGENT_STORE_BACKEND", "memory")
    db_url = os.getenv("WMS_AGENT_DB_URL", "")
    store = build_scan_store(backend, db_url)
    result = asyncio.run(resolve_legacy_scan_partial_alerts(store, dry_run="--apply" not in args))
    result["storeBackend"] = backend
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - 运维入口
    raise SystemExit(main())
