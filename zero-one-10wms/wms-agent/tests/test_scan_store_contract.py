"""扫描存储契约测试：Memory 与 Postgres 两个后端跑同一份用例。

评审结论：此前只有 Memory 测试，掩盖了 PG 的租约漏写、attempt 归零、旧 worker 覆盖新结果
等差异。这里把队列/租约/告警事务的契约写成同一份断言，两个后端都必须满足。

- Memory 始终执行；
- PG 需要设置 ``WMS_AGENT_TEST_DB_URL``（例：
  ``postgresql://postgres:<口令>@127.0.0.1:5432/wms_agent_scan_test``），
  **库名必须包含 "test"**（否则拒绝在非测试库清表），未设置时跳过并给出原因；
- 每个用例前后清空巡检表（含 agent_backlog_observations，仅针对该测试库）；并发/行锁用例只在 PG 上跑。
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, AsyncIterator, Iterator
from unittest.mock import patch

import pytest

from app.scan.repository import (
    ARCHIVE_TABLE_ALERTS, ARCHIVE_TABLE_BACKLOG, ARCHIVE_TABLE_EVENTS, ARCHIVE_TABLE_EVALUATED,
    ARCHIVE_TABLE_NOTIFICATIONS, ARCHIVE_TABLE_OBSERVATIONS, ARCHIVE_TABLE_SCAN_RUNS,
    ARCHIVE_TABLE_SUMMARIES,
    MAX_ATTEMPTS, SCAN_BRIEF_KEYS, SEVERITY_RANK, MemoryScanStore, PostgresScanStore,
    ScanLeaseLostError,
    ScanStore, UPSERT_CREATED, UPSERT_ESCALATED, UPSERT_SUPPRESSED, UPSERT_UPDATED,
    _parse_iso, evidence_row_id,
)
from app.scan.retention import RetentionPolicy, run_retention
from app.storage.postgres import DDL_STATEMENTS

TABLES = (
    "agent_notifications", "agent_alert_events", "agent_alerts", "agent_scan_runs",
    "agent_scan_observations", "agent_backlog_observations", "agent_scan_evaluated_objects",
    "agent_scan_summaries", "agent_archive_rows", "agent_tool_calls", "agent_traces",
    "agent_metric_daily",
)
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def _pg_dsn() -> str | None:
    return os.environ.get("WMS_AGENT_TEST_DB_URL") or None


def _dbname(dsn: str) -> str:
    return dsn.rsplit("/", 1)[-1].split("?")[0].lower()


def _ensure_trace_tables(dsn: str) -> None:
    """问数 trace 表由另一套 DDL 负责（app/storage/postgres.py）；这里要清这两张表，先保证它们存在。"""
    import psycopg

    with psycopg.connect(dsn) as conn:
        for statement in DDL_STATEMENTS:
            conn.execute(statement)
        conn.commit()


def _clean_pg(dsn: str) -> None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        conn.execute(
            "TRUNCATE TABLE " + ", ".join(f"wms_agent.{t}" for t in TABLES)
            + " RESTART IDENTITY CASCADE"
        )
        conn.commit()


@pytest.fixture(params=["memory", "postgres"])
async def store(request: pytest.FixtureRequest) -> AsyncIterator[ScanStore]:
    if request.param == "memory":
        yield MemoryScanStore()
        return
    dsn = _pg_dsn()
    if not dsn:
        pytest.skip("未设置 WMS_AGENT_TEST_DB_URL，跳过真实 PG 契约测试")
    if "test" not in _dbname(dsn):
        pytest.fail("WMS_AGENT_TEST_DB_URL 库名必须包含 test（如 wms_agent_scan_test），拒绝在非测试库清表")
    pg = PostgresScanStore(dsn)
    assert await pg.ensure_schema() is True
    await asyncio.to_thread(_ensure_trace_tables, dsn)
    await asyncio.to_thread(_clean_pg, dsn)
    yield pg
    await asyncio.to_thread(_clean_pg, dsn)


@pytest.fixture
def pg_store(store: ScanStore) -> Iterator[PostgresScanStore]:
    """只对 PG 生效的用例：Memory 上跳过。"""
    if not isinstance(store, PostgresScanStore):
        pytest.skip("并发/行锁语义只在真实 PG 上验证")
    yield store


def _run(scan_id: str, *, queued_at: str | None = None, **overrides: Any) -> dict[str, Any]:
    run = {
        "scanId": scan_id, "trigger": "manual", "actorType": "user", "actorId": "tester",
        "status": "queued", "partial": False, "sourceStatus": [], "configHash": "h",
        "ruleVersion": "expiry=v0.2.0", "scanTypes": ["expiry"], "requestId": None,
        "scheduleSlot": None, "scanKey": scan_id,
        "queuedAt": queued_at or datetime.now(timezone.utc).isoformat(),
        "startedAt": None, "finishedAt": None, "attempt": 0, "counts": {},
        "errorSummary": None, "warehouse": "W01", "dryRun": False,
        "notificationMode": "dry_run", "payloadHash": "sha256:p", "traceId": "trace-t",
    }
    run.update(overrides)
    return run


def _alert(fp: str = "fp-1", severity: str = "P2", **overrides: Any) -> dict[str, Any]:
    alert = {
        "fingerprint": fp, "ruleId": "NOUP-OVERDUE", "ruleVersion": "v0.2.0",
        "severity": severity, "objectType": "no_up_goods", "objectId": "N1|G1|T1",
        "dimension": {"warehouse": "W01"}, "title": f"NOUP-OVERDUE {severity} N1|G1|T1",
        "evidence": {"ageHours": 9}, "suggestedActions": ["MOVE_TO_BIN"],
        "warehouseId": "W01", "scanId": "scan-a", "traceId": "trace-t",
        "lastSeenAt": NOW.isoformat(),
    }
    alert.update(overrides)
    return alert


NOTE = {"recipients": ["tester"], "status": "dry_run", "payloadDigest": "fp", "scope": "trace-t"}


def _events(store: ScanStore) -> list[dict[str, Any]]:
    if isinstance(store, MemoryScanStore):
        return list(store.events)
    import psycopg

    with psycopg.connect(store._dsn) as conn:  # noqa: SLF001 - 测试读取内部 DSN
        rows = conn.execute(
            "SELECT alert_id, event_type, from_state, to_state, from_severity, to_severity, trace_id, "
            "actor_type, actor_id, reason "
            "FROM wms_agent.agent_alert_events ORDER BY event_id"
        ).fetchall()
        conn.commit()
    return [
        {"alertId": r[0], "eventType": r[1], "fromState": r[2], "toState": r[3],
         "fromSeverity": r[4], "toSeverity": r[5], "traceId": r[6],
         "actorType": r[7], "actorId": r[8], "reason": r[9]}
        for r in rows
    ]


def _notifications(store: ScanStore) -> list[dict[str, Any]]:
    if isinstance(store, MemoryScanStore):
        return list(store.notifications)
    import psycopg

    with psycopg.connect(store._dsn) as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT alert_id, recipient, status, dedupe_key FROM wms_agent.agent_notifications "
            "ORDER BY notification_id"
        ).fetchall()
        conn.commit()
    return [
        {"alertId": r[0], "recipient": r[1], "status": r[2], "dedupeKey": r[3]} for r in rows
    ]


def _raw_run(store: ScanStore, scan_id: str) -> dict[str, Any]:
    """直接读列（不经 _row_to_run），确认落库的是列值而不是 JSON 里的计数。"""
    if isinstance(store, MemoryScanStore):
        run = store.runs[scan_id]
        return {
            "status": run.get("status"), "attempt": run.get("attempt"),
            "leaseOwner": run.get("leaseOwner"),
            "queuedAt": "set" if run.get("queuedAt") else None,
            "counts": run.get("counts"), "ruleVersion": run.get("ruleVersion"),
        }
    import psycopg

    with psycopg.connect(store._dsn) as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT status, attempt, lease_owner, queued_at IS NOT NULL, counts, rule_version "
            "FROM wms_agent.agent_scan_runs WHERE scan_id = %s",
            (scan_id,),
        ).fetchone()
        conn.commit()
    return {
        "status": row[0], "attempt": row[1], "leaseOwner": row[2],
        "queuedAt": "set" if row[3] else None, "counts": row[4], "ruleVersion": row[5],
    }


# ---------- 队列契约 ----------

async def test_config_snapshot_roundtrip(store: ScanStore) -> None:
    snapshot = '{"version":"v0.2.0","warehouses":["W01"]}'
    await store.insert_run(_run(
        "scan-config",
        configSnapshot=snapshot,
        configVersion="v0.2.0",
        configHash="sha256:config",
    ))
    saved = await store.get_run("scan-config")
    assert saved is not None
    assert saved["configSnapshot"] == snapshot
    assert saved["configVersion"] == "v0.2.0"
    assert saved["configHash"] == "sha256:config"


async def test_v007_config_columns_exist(pg_store: PostgresScanStore) -> None:
    import psycopg

    with psycopg.connect(pg_store._dsn) as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='wms_agent' AND table_name='agent_scan_runs' "
            "AND column_name IN ('config_snapshot','config_version')"
        ).fetchall()
        conn.commit()
    assert {row[0] for row in rows} == {"config_snapshot", "config_version"}


# V010：重试扫描的审计归属。归属字段只在入队时写入，执行阶段的写入不得改写它们。
RETRY_ATTRIBUTION = {
    "retryOfScanId": "scan-root",
    "originActorType": "service",
    "originActorId": "agent-inspector",
    "originTrigger": "schedule",
}


async def test_retry_attribution_roundtrip_and_survives_execution(store: ScanStore) -> None:
    await store.insert_run(_run("scan-retry", trigger="retry", **RETRY_ATTRIBUTION))
    await store.insert_run(_run("scan-plain"))
    saved = await store.get_run("scan-retry")
    assert saved is not None
    assert saved["trigger"] == "retry"
    for key, value in RETRY_ATTRIBUTION.items():
        assert saved[key] == value
    plain = await store.get_run("scan-plain")
    assert plain is not None
    assert plain["retryOfScanId"] is None and plain["originTrigger"] is None

    # 模拟 worker 领取并执行：只写可写字段，归属字段原样保留
    claimed = None
    for _ in range(2):  # 两条都在队列里，循环直到领到重试那条
        candidate = await store.claim_next_queued("worker-a")
        if candidate is not None and candidate["scanId"] == "scan-retry":
            claimed = candidate
            break
    assert claimed is not None
    executed = dict(claimed)
    executed.update(status="succeeded", counts={"findings": 0}, executorType="service")
    await store.save_run(executed, lease_owner="worker-a")
    done = await store.get_run("scan-retry")
    assert done is not None
    for key, value in RETRY_ATTRIBUTION.items():
        assert done[key] == value


async def test_v010_attribution_columns_exist(pg_store: PostgresScanStore) -> None:
    import psycopg

    with psycopg.connect(pg_store._dsn) as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='wms_agent' AND table_name='agent_scan_runs' "
            "AND column_name IN ('retry_of_scan_id','origin_actor_type',"
            "'origin_actor_id','origin_trigger')"
        ).fetchall()
        conn.commit()
    assert {row[0] for row in rows} == {
        "retry_of_scan_id", "origin_actor_type", "origin_actor_id", "origin_trigger",
    }


async def test_insert_then_claim_writes_lease_and_attempt(store: ScanStore) -> None:
    await store.insert_run(_run("scan-later", queued_at="2026-11-24T12:00:10+00:00"))
    await store.insert_run(_run("scan-earlier", queued_at="2026-11-24T12:00:05+00:00"))

    first = await store.claim_next_queued("worker-a")
    assert first is not None and first["scanId"] == "scan-earlier"
    assert first["status"] == "running"
    assert first["leaseOwner"] == "worker-a"
    assert first["leasedAt"] is not None
    assert first["attempt"] == 1
    assert first["payloadHash"] == "sha256:p" and first["traceId"] == "trace-t"
    raw = _raw_run(store, "scan-earlier")
    assert raw["status"] == "running" and raw["attempt"] == 1 and raw["leaseOwner"] == "worker-a"
    assert raw["queuedAt"] == "set"

    second = await store.claim_next_queued("worker-b")
    assert second is not None and second["scanId"] == "scan-later"
    assert await store.claim_next_queued("worker-c") is None


async def test_fenced_save_rejects_stale_owner_and_keeps_queue_columns(store: ScanStore) -> None:
    queued_at = datetime.now(timezone.utc).isoformat()
    await store.insert_run(_run("scan-1", queued_at=queued_at))
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None

    with pytest.raises(ScanLeaseLostError):
        await store.save_run({**claimed, "status": "succeeded", "counts": {"x": "stale"}}, lease_owner="worker-stale")
    untouched = await store.get_run("scan-1")
    assert untouched["status"] == "running" and untouched["counts"] == {}

    await store.save_run(
        {**claimed, "status": "succeeded", "counts": {"findings": 3}, "ruleVersion": "expiry=v0.2.0"},
        lease_owner="worker-a",
    )
    saved = await store.get_run("scan-1")
    assert saved["status"] == "succeeded" and saved["counts"] == {"findings": 3}
    assert saved["queuedAt"] is not None and saved["attempt"] == 1
    assert saved["leaseOwner"] is None and saved["leasedAt"] is None
    assert _raw_run(store, "scan-1")["attempt"] == 1
    assert "attempt" not in saved["counts"]


async def test_unfenced_save_never_touches_queue_columns(store: ScanStore) -> None:
    await store.insert_run(_run("scan-1", attempt=0))
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None
    # 非 fencing 路径（入队后补字段/测试直调）不得把 attempt/租约/入队时间改回去
    await store.save_run({
        **_run("scan-1"), "status": "running", "errorSummary": "patched",
        "startedAt": claimed["startedAt"],
    })
    raw = _raw_run(store, "scan-1")
    assert raw["attempt"] == 1 and raw["leaseOwner"] == "worker-a"
    got = await store.get_run("scan-1")
    assert got["status"] == "running" and got["errorSummary"] == "patched"


async def test_recover_is_bounded_by_attempt_column(store: ScanStore) -> None:
    await store.insert_run(_run("scan-1"))
    stale = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    attempts: list[int] = []
    for _ in range(MAX_ATTEMPTS):
        claimed = await store.claim_next_queued("worker")
        assert claimed is not None
        attempts.append(claimed["attempt"])
        if isinstance(store, MemoryScanStore):
            store.runs["scan-1"]["leasedAt"] = stale
        else:
            await asyncio.to_thread(_force_stale, store, stale)  # type: ignore[arg-type]
        assert await store.recover_stale(cutoff, 100) == 1
    final = await store.get_run("scan-1")
    assert attempts == [1, 2, 3]
    assert final["status"] == "failed" and final["errorSummary"] == "stale"
    assert final["attempt"] == MAX_ATTEMPTS  # attempt 列持久化，没有随 counts 重建归零
    assert await store.claim_next_queued("worker") is None


def _force_stale(pg: PostgresScanStore, stale: str) -> None:
    import psycopg

    with psycopg.connect(pg._dsn) as conn:  # noqa: SLF001
        conn.execute(
            "UPDATE wms_agent.agent_scan_runs SET leased_at = %s WHERE scan_id = 'scan-1'", (stale,)
        )
        conn.commit()


async def test_requeued_run_keeps_attempt_and_gets_new_lease(store: ScanStore) -> None:
    await store.insert_run(_run("scan-1"))
    first = await store.claim_next_queued("worker-a")
    assert first is not None and first["attempt"] == 1
    stale = (datetime.now(timezone.utc) - timedelta(seconds=600)).isoformat()
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    if isinstance(store, MemoryScanStore):
        store.runs["scan-1"]["leasedAt"] = stale
    else:
        await asyncio.to_thread(_force_stale, store, stale)  # type: ignore[arg-type]
    assert await store.recover_stale(cutoff, 100) == 1
    requeued = await store.get_run("scan-1")
    assert requeued["status"] == "queued" and requeued["attempt"] == 1
    assert requeued["leaseOwner"] is None and requeued["leasedAt"] is None
    again = await store.claim_next_queued("worker-b")
    assert again is not None and again["attempt"] == 2 and again["leaseOwner"] == "worker-b"


async def test_renew_lease_only_for_owner(store: ScanStore) -> None:
    await store.insert_run(_run("scan-1"))
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None
    assert await store.renew_lease("scan-1", "worker-b") is False
    assert await store.renew_lease("scan-1", "worker-a") is True
    assert await store.renew_lease("scan-missing", "worker-a") is False


async def test_get_run_by_scan_key_prefers_active_then_latest(store: ScanStore) -> None:
    await store.insert_run(_run("old", scanKey="k", status="succeeded", startedAt="2026-11-24T10:00:00+00:00"))
    await store.insert_run(_run("new", scanKey="k", status="succeeded", startedAt="2026-11-24T11:00:00+00:00"))
    found = await store.get_run_by_scan_key("k")
    assert found is not None and found["scanId"] == "new"
    await store.insert_run(_run("active", scanKey="k", status="queued"))
    found = await store.get_run_by_scan_key("k")
    assert found is not None and found["scanId"] == "active"


# ---------- 告警事务契约 ----------

async def test_upsert_lifecycle_events_and_notifications_are_atomic(store: ScanStore) -> None:
    created = await store.upsert_alert(_alert(), notification=NOTE)
    assert created.outcome == UPSERT_CREATED and created.notification_saved is True
    updated = await store.upsert_alert(_alert(scanId="scan-b"), notification=NOTE)
    assert updated.outcome == UPSERT_UPDATED and updated.previous_severity == "P2"
    escalated = await store.upsert_alert(
        _alert(severity="P1", scanId="scan-c", traceId="trace-c"),
        notification={**NOTE, "scope": "trace-c"},
    )
    assert escalated.outcome == UPSERT_ESCALATED and escalated.previous_severity == "P2"
    assert escalated.notification_saved is True

    notifications = _notifications(store)
    assert [n["dedupeKey"] for n in notifications] == [
        f"{created.alert_id}:created:P2:trace-t:tester",
        f"{created.alert_id}:escalated:P1:trace-c:tester",
    ]
    events = _events(store)
    assert [e["eventType"] for e in events] == ["created", "escalated"]
    assert events[1]["fromSeverity"] == "P2" and events[1]["toSeverity"] == "P1"
    assert events[1]["traceId"] == "trace-c"
    stored = await store.get_alert(created.alert_id)
    assert stored["severity"] == "P1" and stored["occurrenceCount"] == 3
    assert stored["firstSeverity"] == "P2"


async def test_notification_dedupe_replays_same_event_once(store: ScanStore) -> None:
    created = await store.upsert_alert(_alert(), notification=NOTE)
    assert created.notification_saved is True
    # 直接重放同一事件（模拟同一事务被重试）：去重键挡住第二条
    saved = await store.save_notification({
        "alertId": created.alert_id, "channel": "in_app", "recipient": "tester",
        "status": "dry_run", "payloadDigest": "fp",
        "dedupeKey": f"{created.alert_id}:created:P2:trace-t:tester",
    })
    assert saved is False
    assert len(_notifications(store)) == 1


async def test_ignored_suppresses_until_expiry_then_reopens(store: ScanStore) -> None:
    created = await store.upsert_alert(_alert(), notification=NOTE)
    until = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    assert await store.transition_alert(created.alert_id, "ignored", reason="已知", ignored_until=until, actor_id="tester") is not None

    suppressed = await store.upsert_alert(_alert(severity="P0", scanId="scan-b"), notification={**NOTE, "scope": "trace-b"})
    assert suppressed.outcome == UPSERT_SUPPRESSED and suppressed.alert_id == created.alert_id
    stored = await store.get_alert(created.alert_id)
    assert stored["state"] == "ignored" and stored["severity"] == "P2"
    assert stored["occurrenceCount"] == 1
    assert len(_notifications(store)) == 1
    assert [e["eventType"] for e in _events(store)] == ["created", "transition"]

    # 忽略到期（直接把 ignored_until 拨到过去）后条件仍在 → 新建告警
    if isinstance(store, MemoryScanStore):
        store.alerts[created.alert_id]["ignoredUntil"] = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    else:
        await asyncio.to_thread(_expire_ignore, store, created.alert_id)  # type: ignore[arg-type]
    reopened = await store.upsert_alert(_alert(scanId="scan-c"))
    assert reopened.outcome == UPSERT_CREATED and reopened.alert_id != created.alert_id


def _expire_ignore(pg: PostgresScanStore, alert_id: int) -> None:
    import psycopg

    with psycopg.connect(pg._dsn) as conn:  # noqa: SLF001
        conn.execute(
            "UPDATE wms_agent.agent_alerts SET ignored_until = now() - interval '1 second' WHERE alert_id = %s",
            (alert_id,),
        )
        conn.commit()


async def test_transition_writes_typed_event_and_rejects_illegal(store: ScanStore) -> None:
    created = await store.upsert_alert(_alert())
    assert await store.transition_alert(created.alert_id, "acknowledged", actor_id="tester") is not None
    assert await store.transition_alert(created.alert_id, "resolved", reason="done", actor_id="tester") is not None
    assert await store.transition_alert(created.alert_id, "acknowledged", actor_id="tester") is None  # 终态
    events = [e for e in _events(store) if e["eventType"] == "transition"]
    assert [(e["fromState"], e["toState"]) for e in events] == [("open", "acknowledged"), ("acknowledged", "resolved")]


async def test_list_alerts_filters_by_warehouse_scope(store: ScanStore) -> None:
    await store.upsert_alert(_alert("w01", warehouseId="W01"))
    await store.upsert_alert(_alert("w02", warehouseId="W02"))
    await store.upsert_alert(_alert("wnull", warehouseId=None))

    everything = await store.list_alerts({"warehouseIds": ["W01", "W02"]})
    assert {a["warehouseId"] for a in everything} == {"W01", "W02"}  # NULL 仓库不放行
    scoped = await store.list_alerts({"warehouseIds": ["W01"]})
    assert [a["warehouseId"] for a in scoped] == ["W01"]
    single = await store.list_alerts({"warehouseId": "W02"})
    assert [a["fingerprint"] for a in single] == ["w02"]
    got = await store.get_alert(single[0]["alertId"])
    assert got is not None and got["warehouseId"] == "W02"


# ---------- 阶段1：认领 / 游标分页 / 详情 / 通知已读 ----------

async def test_claim_alert_sets_assignee_and_rejects_other_user(store: ScanStore) -> None:
    created = await store.upsert_alert(_alert("fp-claim"))
    claimed = await store.claim_alert(created.alert_id, assignee="alice", assignee_user_id="u-alice")
    assert claimed is not None
    assert claimed["assignee"] == "alice" and claimed["assigneeUserId"] == "u-alice"
    assert claimed["claimedAt"] is not None
    # 已被他人认领 → None（路由层映射 409）
    assert await store.claim_alert(created.alert_id, assignee="bob", assignee_user_id="u-bob") is None
    # 同一 stable id 重复认领允许（幂等重试）
    again = await store.claim_alert(created.alert_id, assignee="alice", assignee_user_id="u-alice")
    assert again is not None and again["assigneeUserId"] == "u-alice"


async def test_claim_alert_rejects_terminal_alert(store: ScanStore) -> None:
    created = await store.upsert_alert(_alert("fp-terminal"))
    assert await store.transition_alert(created.alert_id, "resolved", reason="done", actor_id="t") is not None
    assert await store.claim_alert(created.alert_id, assignee="alice", assignee_user_id="u-alice") is None


async def test_list_alerts_page_cursor_covers_all_without_gap_or_dup(store: ScanStore) -> None:
    for i in range(5):
        await store.upsert_alert(_alert(f"fp-page-{i}"))
    seen: list[int] = []
    cursor_at: str | None = None
    cursor_id: int | None = None
    for _ in range(10):  # 最多翻 10 页，避免死循环
        page = await store.list_alerts_page({}, last_seen_at=cursor_at, last_alert_id=cursor_id, page_size=2)
        if not page:
            break
        seen.extend(int(a["alertId"]) for a in page)
        last = page[-1]
        cursor_at, cursor_id = last["lastSeenAt"], int(last["alertId"])
    assert len(seen) == 5
    assert len(set(seen)) == 5


async def test_find_healthy_source_scan_requires_successful_untruncated_after_cutoff(
    store: ScanStore,
) -> None:
    await store.save_run(_run(
        "scan-healthy-source", status="succeeded", finishedAt="2026-11-24T11:00:00+00:00",
        sourceStatus=[{"source": "no_up", "status": "ok", "truncated": False}],
    ))
    await store.save_run(_run(
        "scan-truncated-source", status="succeeded", finishedAt="2026-11-24T10:45:00+00:00",
        sourceStatus=[{"source": "no_up", "status": "ok", "truncated": True}],
    ))
    await store.save_run(_run(
        "scan-failed-source", status="failed", finishedAt="2026-11-24T10:50:00+00:00",
        sourceStatus=[{"source": "no_up", "status": "error", "truncated": True}],
    ))
    await store.save_run(_run(
        "scan-other-source", status="succeeded", finishedAt="2026-11-24T10:55:00+00:00",
        sourceStatus=[{"source": "delay", "status": "ok", "truncated": False}],
    ))

    found = await store.find_healthy_source_scan(
        warehouse="W01", source="no_up", after_iso="2026-11-24T10:15:00+00:00",
    )
    assert found is not None and found["scanId"] == "scan-healthy-source"
    assert await store.find_healthy_source_scan(
        warehouse="W01", source="no_up", after_iso="2026-11-24T11:00:00+00:00",
    ) is None


async def test_get_alert_detail_returns_evidence_events_and_scan(store: ScanStore) -> None:
    await store.insert_run(_run("scan-detail"))
    created = await store.upsert_alert(
        _alert("fp-detail", scanId="scan-detail", evidence={"ageHours": 9}),
        notification=NOTE,
    )
    detail = await store.get_alert_detail(created.alert_id)
    assert detail is not None
    assert detail["evidence"] == {"ageHours": 9}
    assert detail["ruleParams"] == {}
    assert [e["eventType"] for e in detail["events"]] == ["created"]
    assert detail["scan"] is not None and detail["scan"]["scanId"] == "scan-detail"
    assert await store.get_alert_detail(999999) is None


async def test_alert_detail_embeds_only_a_scan_brief(store: ScanStore) -> None:
    """告警详情内嵌的触发扫描只是状态摘要（阶段7）。

    告警详情对能看该仓库告警的人开放；完整扫描记录（配置快照、触发身份、执行者、
    租约、计数与错误明细）按 `can_view_scan` 只对本人/管理员可见，不能借详情带出。
    """
    await store.insert_run(_run(
        "scan-brief",
        trigger="schedule", actorType="service", actorId="agent-inspector", status="succeeded",
        configSnapshot='{"version":"v0.2.0"}', configHash="sha256:brief", configVersion="v0.2.0",
        counts={"findings": 1}, leaseOwner="worker-a", executorType="service",
        executorId="agent-inspector", scanTypes=["no_up"], scheduleSlot="20261125T2100",
        requestId="req-brief", traceId="trace-brief", errorSummary=None,
    ))
    created = await store.upsert_alert(_alert("fp-brief", scanId="scan-brief"), notification=NOTE)
    scan = (await store.get_alert_detail(created.alert_id))["scan"]

    assert scan["scanId"] == "scan-brief" and scan["trigger"] == "schedule" and scan["status"] == "succeeded"
    assert scan["scanTypes"] == ["no_up"] and scan["scheduleSlot"] == "20261125T2100"
    assert set(scan) <= set(SCAN_BRIEF_KEYS)
    for key in (
        "configSnapshot", "configHash", "configVersion", "actorType", "actorId", "actorUserId",
        "executorType", "executorId", "leaseOwner", "counts", "errorSummary", "requestId",
        "traceId", "scanKey", "attempt",
    ):
        assert key not in scan


async def test_notifications_are_isolated_by_stable_user_id(store: ScanStore) -> None:
    created = await store.upsert_alert(_alert("fp-note"))
    base = {
        "alertId": created.alert_id, "channel": "in_app", "recipient": "tester",
        "status": "sent", "payloadDigest": "d",
    }
    assert await store.save_notification({**base, "recipientUserId": "u-1", "dedupeKey": "k-1"})
    assert await store.save_notification({**base, "recipientUserId": "u-2", "dedupeKey": "k-2"})

    mine = await store.list_notifications(recipient_user_id="u-1", recipient="tester")
    assert len(mine) == 1
    assert mine[0]["recipientUserId"] == "u-1"
    assert mine[0]["readAt"] is None
    assert mine[0]["sentAt"] is not None  # in_app 事务内直接写成 sent

    # 他人通知不允许标记已读
    assert await store.mark_notification_read(mine[0]["notificationId"], recipient_user_id="u-2", recipient="tester") is None
    read = await store.mark_notification_read(mine[0]["notificationId"], recipient_user_id="u-1", recipient="tester")
    assert read is not None and read["readAt"] is not None
    assert await store.list_notifications(recipient_user_id="u-1", recipient="tester", unread_only=True) == []
    assert len(await store.list_notifications(recipient_user_id="u-2", recipient="tester")) == 1


# ---------- 只在真实 PG 上验证：并发领取 / 并发 upsert / ignored 行锁 ----------

async def test_concurrent_claim_gives_each_run_exactly_one_owner(pg_store: PostgresScanStore) -> None:
    for i in range(5):
        await pg_store.insert_run(_run(f"scan-{i}", queued_at=f"2026-11-24T12:00:0{i}+00:00"))
    claimed: list[tuple[str, str, int]] = []
    lock = threading.Lock()

    def worker(index: int) -> None:
        async def _claim() -> None:
            run = await pg_store.claim_next_queued(f"worker-{index}")
            if run is not None:
                with lock:
                    claimed.append((run["scanId"], run["leaseOwner"], run["attempt"]))

        asyncio.run(_claim())

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert len(claimed) == 5  # 5 条队列记录各被领取一次，没有重复领取
    assert len({scan_id for scan_id, _, _ in claimed}) == 5
    assert all(attempt == 1 for _, _, attempt in claimed)
    assert all(owner for _, owner, _ in claimed)


async def test_concurrent_upsert_same_fingerprint_yields_one_alert(pg_store: PostgresScanStore) -> None:
    results: list[Any] = []
    lock = threading.Lock()

    def upsert(index: int) -> None:
        async def _upsert() -> None:
            result = await pg_store.upsert_alert(_alert(scanId=f"scan-{index}"), notification=NOTE)
            with lock:
                results.append(result)

        asyncio.run(_upsert())

    threads = [threading.Thread(target=upsert, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    outcomes = sorted(r.outcome for r in results)
    assert outcomes.count(UPSERT_CREATED) == 1
    assert len({r.alert_id for r in results}) == 1
    alerts = await pg_store.list_alerts()
    assert len(alerts) == 1 and alerts[0]["occurrenceCount"] == 6
    assert [e["eventType"] for e in _events(pg_store)] == ["created"]
    assert len(_notifications(pg_store)) == 1


async def test_upsert_waits_for_concurrent_ignore_and_is_suppressed(pg_store: PostgresScanStore) -> None:
    """transition 的 FOR UPDATE 与 upsert 串行化：刚 ignored 的告警不会被并发 upsert 再插一条 open。"""
    created = await pg_store.upsert_alert(_alert())
    import psycopg

    blocker_ready = threading.Event()
    release = threading.Event()

    def ignore_txn() -> None:
        with psycopg.connect(pg_store._dsn) as conn:  # noqa: SLF001
            with conn.transaction():
                conn.execute(
                    "SELECT alert_id FROM wms_agent.agent_alerts WHERE alert_id = %s FOR UPDATE",
                    (created.alert_id,),
                )
                conn.execute(
                    "UPDATE wms_agent.agent_alerts SET state = 'ignored', "
                    "ignored_until = now() + interval '7 days' WHERE alert_id = %s",
                    (created.alert_id,),
                )
                blocker_ready.set()
                release.wait(timeout=30)

    thread = threading.Thread(target=ignore_txn)
    thread.start()
    assert blocker_ready.wait(timeout=30)

    async def _upsert() -> Any:
        return await pg_store.upsert_alert(_alert(scanId="scan-b"), notification={**NOTE, "scope": "trace-b"})

    task = asyncio.create_task(_upsert())
    await asyncio.sleep(0.6)
    assert not task.done(), "upsert 应被行锁阻塞，而不是抢先插入新 open"
    release.set()
    thread.join(timeout=30)
    result = await asyncio.wait_for(task, timeout=30)
    assert result.outcome == UPSERT_SUPPRESSED
    alerts = await pg_store.list_alerts()
    assert len(alerts) == 1 and alerts[0]["state"] == "ignored"


def test_severity_rank_is_shared() -> None:
    assert SEVERITY_RANK["P0"] > SEVERITY_RANK["P1"] > SEVERITY_RANK["P2"]


# ---------- V006 backlog 观测样本（阶段3） ----------

def _obs(scan_id: str, queue: str, value: str, observed_at: str, *, rule_version: str = "v0.2.0") -> dict[str, Any]:
    return {
        "scanId": scan_id, "warehouse": "W01", "queueType": queue, "value": value,
        "observedAt": observed_at, "ruleVersion": rule_version, "sourceStatus": "ok",
    }


async def test_backlog_observations_unique_per_scan_queue_and_stable_order(store: ScanStore) -> None:
    """唯一键 (scan_id, queue_type)：重放返回 0；基线按 (observed_at, observation_id) 升序；按 rule_version 隔离。"""
    first = await store.save_backlog_observations([
        _obs("scan-1", "receipt", "60", "2026-11-25T10:00:00+00:00"),
        _obs("scan-1", "to_up", "7", "2026-11-25T10:00:00+00:00"),
        _obs("scan-1", "pick", "45", "2026-11-25T10:00:00+00:00"),
    ])
    assert first == 3
    # 同一扫描重放（如 worker 重试）：全部被唯一键挡下
    replay = await store.save_backlog_observations([
        _obs("scan-1", "receipt", "999", "2026-11-25T10:00:00+00:00"),
        _obs("scan-1", "to_up", "999", "2026-11-25T10:00:00+00:00"),
    ])
    assert replay == 0
    # 同一队列不同扫描：追加
    later = await store.save_backlog_observations([_obs("scan-2", "receipt", "70", "2026-11-25T10:15:00+00:00")])
    assert later == 1
    # 旧规则版本的样本不混入新基线
    await store.save_backlog_observations([
        _obs("scan-old", "receipt", "5000", "2026-11-25T09:00:00+00:00", rule_version="v0.1.0"),
    ])

    baseline = await store.list_backlog_observations("W01", "receipt", rule_version="v0.2.0")
    # PG 的 NUMERIC(18,4) 回 "60.0000"，Memory 回 "60"：契约按数值比较，规则侧 to_decimal 同样按数值解析
    assert [(o["scanId"], Decimal(o["value"])) for o in baseline] == [("scan-1", Decimal(60)), ("scan-2", Decimal(70))]
    assert baseline[0]["observedAt"] <= baseline[1]["observedAt"]
    assert all(o["ruleVersion"] == "v0.2.0" for o in baseline)
    old = await store.list_backlog_observations("W01", "receipt", rule_version="v0.1.0")
    assert [Decimal(o["value"]) for o in old] == [Decimal(5000)]
    # 三队列互不聚合
    picks = await store.list_backlog_observations("W01", "pick", rule_version="v0.2.0")
    assert [Decimal(o["value"]) for o in picks] == [Decimal(45)]
    # limit 取最近的 N 条（丢最旧）
    recent = await store.list_backlog_observations("W01", "receipt", rule_version="v0.2.0", limit=1)
    assert [o["scanId"] for o in recent] == ["scan-2"]


async def test_backlog_observations_accept_java_zoned_datetime_observed_at(store: ScanStore) -> None:
    """真实 Dashboard 端点的 observedAt 是 Java ZonedDateTime.toString()（带 [Asia/Shanghai]）。

    源头由 parse_snapshot 去后缀；这里直接把原始形态喂给存储层，验证双后端都能落库并
    按时间排序（PG 曾因 InvalidDatetimeFormat 整次扫描 failed）。
    """
    java_ts = "2026-11-25T13:01:08.141234900+08:00[Asia/Shanghai]"
    saved = await store.save_backlog_observations([
        _obs("scan-java", "pick", "45", java_ts),
        _obs("scan-plain", "pick", "50", "2026-11-25T13:05:00+08:00"),
    ])
    assert saved == 2
    rows = await store.list_backlog_observations("W01", "pick", rule_version="v0.2.0")
    assert [o["scanId"] for o in rows] == ["scan-java", "scan-plain"]  # 13:01 → 13:05 稳定升序
    # 落库后不再带方括号
    assert all("[" not in str(o["observedAt"]) for o in rows)


async def test_concurrent_save_backlog_observations_honors_unique_constraint(pg_store: PostgresScanStore) -> None:
    """并发对同一 (scan_id, queue_type) 落样本：唯一约束保证只有一份，且新增总数恰为 3。"""
    rows = [_obs("scan-race", q, "10", "2026-11-25T10:30:00+00:00") for q in ("receipt", "to_up", "pick")]

    async def _save() -> int:
        return await pg_store.save_backlog_observations(rows)

    results = await asyncio.gather(_save(), _save(), _save())
    assert sum(results) == 3
    assert max(results) <= 3 and min(results) >= 0
    import psycopg

    with psycopg.connect(pg_store._dsn) as conn:  # noqa: SLF001
        count = conn.execute(
            "SELECT count(*) FROM wms_agent.agent_backlog_observations WHERE scan_id = %s", ("scan-race",)
        ).fetchone()[0]
    assert count == 3
    stored = await pg_store.list_backlog_observations("W01", "receipt", rule_version="v0.2.0")
    assert [o["scanId"] for o in stored] == ["scan-race"]


# ---------- V008 覆盖记录与自动关闭（阶段5） ----------


def _evaluated(
    scan_id: str = "scan-e1",
    rule_id: str = "NOUP-OVERDUE",
    object_id: str = "N1|G1|T1",
    dimension_hash: str = "sha256:dh1",
    warehouse: str = "W01",
) -> dict[str, Any]:
    return {
        "scanId": scan_id, "warehouse": warehouse, "ruleId": rule_id,
        "objectType": "no_up_goods", "objectId": object_id,
        "dimensionHash": dimension_hash, "evaluatedAt": NOW.isoformat(),
    }


async def test_evaluated_objects_unique_per_scan_rule_object(store: ScanStore) -> None:
    """唯一键 (scan_id, rule_id, object_id, dimension_hash)：重放返回 0，按扫描可读回。"""
    first = await store.save_evaluated_objects([
        _evaluated("scan-e1", object_id="N1|G1|T1"),
        _evaluated("scan-e1", object_id="N2|G2|T2"),
    ])
    assert first == 2
    replay = await store.save_evaluated_objects([
        _evaluated("scan-e1", object_id="N1|G1|T1"),
    ])
    assert replay == 0
    other_scan = await store.save_evaluated_objects([_evaluated("scan-e2", object_id="N1|G1|T1")])
    assert other_scan == 1

    rows = await store.list_evaluated_objects("scan-e1")
    assert {r["objectId"] for r in rows} == {"N1|G1|T1", "N2|G2|T2"}
    assert all(r["ruleId"] == "NOUP-OVERDUE" for r in rows)
    only_rule = await store.list_evaluated_objects("scan-e1", rule_id="NOUP-OVERDUE")
    assert len(only_rule) == 2
    assert await store.list_evaluated_objects("scan-e1", rule_id="DELAY-OVERDUE") == []


async def test_auto_resolve_updates_state_and_writes_condition_cleared_event(store: ScanStore) -> None:
    """自动关闭：条件 UPDATE + 同事务 condition_cleared 事件，保留 traceId 与 scanId。"""
    result = await store.upsert_alert(_alert(fp="fp-auto", lastSeenAt="2026-11-24T11:00:00+00:00"))
    alert_id = result.alert_id
    closed = await store.auto_resolve_alert(
        alert_id,
        reason="condition_cleared: NOUP-OVERDUE 对象 N1|G1|T1 在扫描 scan-e1 中未再命中",
        scan_id="scan-e1",
        trace_id="trace-auto",
        before_iso="2026-11-24T12:00:00+00:00",
        rule_id="NOUP-OVERDUE",
        rule_version="v0.2.0",
        warehouse="W01",
    )
    assert closed is True
    alert = await store.get_alert(alert_id)
    assert alert["state"] == "resolved"
    assert alert["resolvedReason"]
    events = [e for e in _events(store) if e["eventType"] == "condition_cleared"]
    assert len(events) == 1
    # fromState 必须是关闭前的真实状态：UPDATE … RETURNING 只看得到新值，
    # PG 实现曾把事件写成 resolved→resolved（真实 e2e 捕获）
    assert (events[0]["fromState"], events[0]["toState"]) == ("open", "resolved")
    assert events[0]["actorType"] == "system"
    assert events[0]["actorId"] == "scan-e1"
    assert events[0]["traceId"] == "trace-auto"

    # 重复关闭：状态条件不再满足 → 不重复关闭、不重复写事件
    again = await store.auto_resolve_alert(
        alert_id,
        reason="重复",
        scan_id="scan-e1",
        trace_id="trace-auto",
        before_iso="2026-11-24T12:00:00+00:00",
        rule_id="NOUP-OVERDUE",
        rule_version="v0.2.0",
        warehouse="W01",
    )
    assert again is False
    assert len([e for e in _events(store) if e["eventType"] == "condition_cleared"]) == 1


async def test_auto_resolve_from_acknowledged_keeps_previous_state(store: ScanStore) -> None:
    """已确认（acknowledged）的告警同样可被自动关闭，事件记录 acknowledged→resolved。"""
    result = await store.upsert_alert(_alert(fp="fp-auto-ack", lastSeenAt="2026-11-24T11:00:00+00:00"))
    alert_id = result.alert_id
    assert await store.transition_alert(alert_id, "acknowledged", actor_id="tester") is not None
    closed = await store.auto_resolve_alert(
        alert_id,
        reason="condition_cleared: NOUP-OVERDUE 已恢复",
        scan_id="scan-e2",
        trace_id="trace-auto-ack",
        before_iso="2026-11-24T12:00:00+00:00",
        rule_id="NOUP-OVERDUE",
        rule_version="v0.2.0",
        warehouse="W01",
    )
    assert closed is True
    events = [
        e for e in _events(store)
        if e["alertId"] == alert_id and e["eventType"] == "condition_cleared"
    ]
    assert len(events) == 1
    assert (events[0]["fromState"], events[0]["toState"]) == ("acknowledged", "resolved")
    assert events[0]["actorType"] == "system"
    assert events[0]["actorId"] == "scan-e2"
    assert events[0]["traceId"] == "trace-auto-ack"
    assert (await store.get_alert(alert_id))["state"] == "resolved"


async def test_auto_resolve_candidates_respect_state_warehouse_version_and_time(store: ScanStore) -> None:
    """候选查询：只取 open/acknowledged、本仓、指定规则、且 lastSeenAt 早于本次扫描开始。"""
    await store.upsert_alert(_alert(fp="fp-cand", lastSeenAt="2026-11-24T11:00:00+00:00"))
    await store.upsert_alert(_alert(fp="fp-new", lastSeenAt="2026-11-24T13:00:00+00:00"))
    await store.upsert_alert(_alert(fp="fp-other-wh", warehouseId="W02", lastSeenAt="2026-11-24T11:00:00+00:00"))
    await store.upsert_alert(_alert(fp="fp-other-rule", ruleId="DELAY-OVERDUE", lastSeenAt="2026-11-24T11:00:00+00:00"))

    candidates = await store.list_auto_resolve_candidates(
        warehouse="W01",
        rule_ids=["NOUP-OVERDUE"],
        before_iso="2026-11-24T12:00:00+00:00",
    )
    fingerprints = {c["objectId"] for c in candidates}
    assert "N1|G1|T1" in fingerprints
    # 只有一个候选满足全部条件（其余分别因时间/仓库/规则被排除）
    assert len(candidates) == 1

    # 忽略窗口内的告警不参与候选
    ignored = await store.upsert_alert(_alert(fp="fp-ign", lastSeenAt="2026-11-24T11:00:00+00:00"))
    await store.transition_alert(
        ignored.alert_id,
        "ignored",
        reason="人工忽略",
        ignored_until="2026-11-25T00:00:00+00:00",
        actor_type="user",
        actor_id="tester",
    )
    after_ignore = await store.list_auto_resolve_candidates(
        warehouse="W01",
        rule_ids=["NOUP-OVERDUE"],
        before_iso="2026-11-24T12:00:00+00:00",
    )
    assert len(after_ignore) == 1


async def test_auto_resolve_rejects_rule_version_mismatch(store: ScanStore) -> None:
    """规则版本不匹配的告警不得被自动关闭。"""
    result = await store.upsert_alert(
        _alert(fp="fp-ver", ruleVersion="v0.1.0", lastSeenAt="2026-11-24T11:00:00+00:00")
    )
    closed = await store.auto_resolve_alert(
        result.alert_id,
        reason="条件消失",
        scan_id="scan-e1",
        trace_id="trace-ver",
        before_iso="2026-11-24T12:00:00+00:00",
        rule_id="NOUP-OVERDUE",
        rule_version="v0.2.0",
        warehouse="W01",
    )
    assert closed is False
    alert = await store.get_alert(result.alert_id)
    assert alert["state"] == "open"


async def test_concurrent_auto_resolve_only_one_winner(pg_store: PostgresScanStore) -> None:
    """并发自动关闭：只有一条 UPDATE 命中状态条件，事件只写一次。"""
    result = await pg_store.upsert_alert(
        _alert(fp="fp-conc", lastSeenAt="2026-11-24T11:00:00+00:00")
    )
    alert_id = result.alert_id

    async def _close() -> bool:
        return await pg_store.auto_resolve_alert(
            alert_id,
            reason="条件消失",
            scan_id="scan-conc",
            trace_id="trace-conc",
            before_iso="2026-11-24T12:00:00+00:00",
            rule_id="NOUP-OVERDUE",
            rule_version="v0.2.0",
            warehouse="W01",
        )

    results = await asyncio.gather(_close(), _close(), _close())
    assert sum(1 for item in results if item) == 1
    events = [e for e in _events(pg_store) if e["eventType"] == "condition_cleared"]
    assert len(events) == 1


async def test_pg_partial_alert_commit_during_healthy_scan_is_not_resolved(
    pg_store: PostgresScanStore,
) -> None:
    """真实 PG：健康扫描查询时 partial 尚未提交，提交后也不能被该健康扫描关闭。"""
    partial_run = _run(
        "scan-partial-slow",
        status="running",
        partial=True,
        startedAt="2026-11-24T10:00:00+00:00",
        finishedAt=None,
        sourceStatus=[{"source": "no_up", "status": "partial", "truncated": True}],
    )
    await pg_store.save_run(partial_run)
    inserted = threading.Event()
    release = threading.Event()
    original_insert_event = pg_store._insert_event_sync

    def delayed_insert_event(*args: Any, **kwargs: Any) -> None:
        original_insert_event(*args, **kwargs)
        inserted.set()
        assert release.wait(5), "test did not release the open PG transaction"

    partial_alert = _alert(
        fp="fp-partial-slow",
        ruleId="SCAN-PARTIAL",
        ruleVersion="v1",
        objectId="no_up",
        dimension={"warehouse": "W01", "source": "no_up"},
        scanId="scan-partial-slow",
        lastSeenAt="2026-11-24T11:00:00+00:00",
    )
    healthy_started = "2026-11-24T11:30:00+00:00"
    with patch.object(pg_store, "_insert_event_sync", side_effect=delayed_insert_event):
        writer = asyncio.create_task(pg_store.upsert_alert(partial_alert))
        try:
            assert await asyncio.to_thread(inserted.wait, 5), "PG alert insert did not reach pre-commit"
            candidates = await pg_store.list_auto_resolve_candidates(
                warehouse="W01",
                rule_ids=["SCAN-PARTIAL"],
                before_iso=healthy_started,
            )
            assert candidates == [], "uncommitted alert must not be visible to the healthy scan"
        finally:
            release.set()
        created = await writer

    candidates = await pg_store.list_auto_resolve_candidates(
        warehouse="W01",
        rule_ids=["SCAN-PARTIAL"],
        before_iso=healthy_started,
    )
    assert candidates == [], "running source scan must fence the newly committed partial alert"

    await pg_store.save_run({
        **partial_run,
        "status": "succeeded",
        "finishedAt": "2026-11-24T11:40:00+00:00",
    })
    candidates = await pg_store.list_auto_resolve_candidates(
        warehouse="W01",
        rule_ids=["SCAN-PARTIAL"],
        before_iso=healthy_started,
    )
    assert candidates == [], "source scan finished after healthy start must remain fenced"
    assert await pg_store.auto_resolve_alert(
        created.alert_id,
        reason="condition_cleared",
        scan_id="scan-healthy",
        trace_id="trace-healthy",
        before_iso=healthy_started,
        rule_id="SCAN-PARTIAL",
        rule_version="v1",
        warehouse="W01",
    ) is False

    await pg_store.save_run({
        **partial_run,
        "status": "succeeded",
        "finishedAt": "2026-11-24T11:20:00+00:00",
    })
    candidates = await pg_store.list_auto_resolve_candidates(
        warehouse="W01",
        rule_ids=["SCAN-PARTIAL"],
        before_iso=healthy_started,
    )
    assert [item["alertId"] for item in candidates] == [created.alert_id]
    assert await pg_store.auto_resolve_alert(
        created.alert_id,
        reason="condition_cleared",
        scan_id="scan-healthy",
        trace_id="trace-healthy",
        before_iso=healthy_started,
        rule_id="SCAN-PARTIAL",
        rule_version="v1",
        warehouse="W01",
    ) is True


# ---------------------------------------------------------------------------
# V009：LLM 聚合摘要（阶段6）。摘要是扫描的派生数据：同一 (scan, rule, warehouse, customer)
# 只保留一行，重跑/重试覆盖不追加；判定事实（severity/objectCount）照存不改。
# ---------------------------------------------------------------------------


def _summary(scan_id: str = "scan-s1", **overrides: Any) -> dict[str, Any]:
    row = {
        "scanId": scan_id, "traceId": "trace-s1",
        "ruleId": "NOUP-OVERDUE", "ruleVersion": "v0.2.0",
        "warehouse": "W01", "customer": "C1", "severity": "P0",
        "objectCount": 2, "severityCounts": {"P0": 2, "P1": 0, "P2": 0},
        "sampleObjects": ["货A（已等待 10 小时）", "货B（已等待 9 小时）"],
        "summary": "仓库 W01 客户 C1 共 2 个对象上架超时。",
        "summarySource": "llm", "fallbackReason": None, "fallbackDetail": None,
        "suggestedActions": [{"code": "MOVE_TO_BIN", "text": "安排上架到货位"}],
        "model": "scripted-model", "promptTokens": 7, "completionTokens": 5,
        "llmDurationMs": 12,
    }
    row.update(overrides)
    return row


async def test_scan_summaries_round_trip_typed_fields(store: ScanStore) -> None:
    """摘要行写回读：JSON 字段还原为 list/dict，用量为 int，时间为 ISO 字符串，并带主键。"""
    assert await store.save_scan_summaries([_summary()]) == 1
    rows = await store.list_scan_summaries("scan-s1")
    assert len(rows) == 1
    row = rows[0]
    assert isinstance(row["summaryId"], int)
    assert (row["scanId"], row["traceId"], row["ruleId"], row["ruleVersion"]) == ("scan-s1", "trace-s1", "NOUP-OVERDUE", "v0.2.0")
    assert (row["warehouse"], row["customer"], row["severity"], row["objectCount"]) == ("W01", "C1", "P0", 2)
    assert row["severityCounts"] == {"P0": 2, "P1": 0, "P2": 0}
    assert row["sampleObjects"] == ["货A（已等待 10 小时）", "货B（已等待 9 小时）"]
    assert row["suggestedActions"] == [{"code": "MOVE_TO_BIN", "text": "安排上架到货位"}]
    assert row["summary"] == "仓库 W01 客户 C1 共 2 个对象上架超时。"
    assert (row["summarySource"], row["model"]) == ("llm", "scripted-model")
    assert (row["promptTokens"], row["completionTokens"], row["llmDurationMs"]) == (7, 5, 12)
    assert row.get("fallbackReason") is None and row.get("fallbackDetail") is None
    assert isinstance(row["createdAt"], str)
    assert datetime.fromisoformat(row["createdAt"]).tzinfo is not None


async def test_scan_summaries_upsert_is_idempotent_per_group(store: ScanStore) -> None:
    """同一 (scan, rule, warehouse, customer) 重复写入只覆盖、不追加；customer 为空的组同样成立。"""
    assert await store.save_scan_summaries([_summary(), _summary(customer="", ruleId="BACKLOG-GROWTH", objectCount=1, severity="P2")]) == 2
    assert await store.save_scan_summaries([_summary(summary="改写后的摘要", suggestedActions=[])]) == 1
    rows = await store.list_scan_summaries("scan-s1")
    assert len(rows) == 2
    by_rule = {r["ruleId"]: r for r in rows}
    assert by_rule["NOUP-OVERDUE"]["summary"] == "改写后的摘要"
    assert by_rule["NOUP-OVERDUE"]["suggestedActions"] == []
    assert by_rule["NOUP-OVERDUE"]["severity"] == "P0"  # 判定事实不被后写覆盖成别的值
    assert by_rule["BACKLOG-GROWTH"]["customer"] == "" and by_rule["BACKLOG-GROWTH"]["objectCount"] == 1
    ids = {r["summaryId"] for r in rows}
    assert len(ids) == 2


async def test_scan_summaries_list_orders_by_severity_then_object_count(store: ScanStore) -> None:
    """列表顺序：P0 在前，同级别对象多的在前，便于人工先看最紧急的一组。"""
    await store.save_scan_summaries([
        _summary(ruleId="EXP-WATCH", severity="P2", objectCount=9),
        _summary(ruleId="NOUP-OVERDUE", severity="P0", objectCount=2),
        _summary(ruleId="EXP-EXPIRED", severity="P0", objectCount=5),
        _summary(ruleId="DELAY-OVERDUE", severity="P1", objectCount=40),
    ])
    rows = await store.list_scan_summaries("scan-s1")
    assert [(r["ruleId"], r["severity"], r["objectCount"]) for r in rows] == [
        ("EXP-EXPIRED", "P0", 5), ("NOUP-OVERDUE", "P0", 2), ("DELAY-OVERDUE", "P1", 40), ("EXP-WATCH", "P2", 9),
    ]


async def test_scan_summaries_are_isolated_per_scan(store: ScanStore) -> None:
    """不同扫描（含重试产生的新 scanId）各写各的，查询不会串。"""
    await store.save_scan_summaries([_summary("scan-a"), _summary("scan-b", summary="重试那次")])
    assert [r["scanId"] for r in await store.list_scan_summaries("scan-a")] == ["scan-a"]
    assert [r["summary"] for r in await store.list_scan_summaries("scan-b")] == ["重试那次"]
    assert await store.list_scan_summaries("scan-missing") == []


async def test_scan_summaries_empty_write_and_source_coercion(store: ScanStore) -> None:
    """空列表不写；模板行可缺省 model/用量；未知来源一律按模板落库，绝不冒充 LLM。"""
    assert await store.save_scan_summaries([]) == 0
    await store.save_scan_summaries([
        _summary(summarySource="template", model=None, promptTokens=0, completionTokens=0, llmDurationMs=None,
                 fallbackReason="timeout", fallbackDetail="exceeded 8s"),
        _summary(customer="C9", summarySource="whatever-the-model-said"),
    ])
    rows = {r["customer"]: r for r in await store.list_scan_summaries("scan-s1")}
    template = rows["C1"]
    assert template["summarySource"] == "template"
    assert (template["fallbackReason"], template["fallbackDetail"]) == ("timeout", "exceeded 8s")
    assert not template.get("model") and not template.get("promptTokens")
    assert rows["C9"]["summarySource"] == "template"


async def test_scan_summaries_pg_constraints_reject_duplicate_and_unknown_source(pg_store: PostgresScanStore) -> None:
    """PG 侧由数据库自己兜底：唯一键 (scan_id, rule_id, warehouse, customer) 与来源枚举。"""
    import psycopg

    await pg_store.save_scan_summaries([_summary()])
    with psycopg.connect(pg_store._dsn) as conn:  # noqa: SLF001 - 测试读取内部 DSN
        stored = conn.execute(
            "SELECT jsonb_typeof(severity_counts), jsonb_typeof(suggested_actions), summary_source "
            "FROM wms_agent.agent_scan_summaries WHERE scan_id = %s",
            ("scan-s1",),
        ).fetchone()
        assert stored == ("object", "array", "llm")
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(
                "INSERT INTO wms_agent.agent_scan_summaries "
                "(scan_id, rule_id, warehouse, customer, severity, object_count, summary, summary_source) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                ("scan-s1", "NOUP-OVERDUE", "W01", "C1", "P0", 1, "重复键", "template"),
            )
        conn.rollback()
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "INSERT INTO wms_agent.agent_scan_summaries "
                "(scan_id, rule_id, warehouse, customer, severity, object_count, summary, summary_source) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                ("scan-s1", "EXP-NEAR", "W01", "C2", "P1", 1, "非法来源", "model-said-so"),
            )
        conn.rollback()
    assert len(await pg_store.list_scan_summaries("scan-s1")) == 1


# ---------------------------------------------------------------------------
# 阶段7：只读指标聚合（Memory / PG 同口径）。
# 时间窗左闭右开；扫描与摘要按扫描 started_at，事件按事件时间，通知按创建 / 已读时间，
# 告警 = 当前活跃 ∪ 窗口内有认领 / 关闭动作。聚合值由 build_metrics 解释（test_scan_stage7.py）。
# ---------------------------------------------------------------------------

def _window(hours: float = 2) -> tuple[datetime, datetime]:
    """指标窗口围绕**测试执行时**的当前时间（左闭右开，右端点留 1 分钟余量）。

    事件 / 通知 / 事件行的 created_at 由数据库 now() 写入；全量套件要跑 100 秒以上，
    窗口不能在模块导入时计算，否则轮到这些用例时「现在」已经越过右端点。
    """
    to = datetime.now(timezone.utc) + timedelta(minutes=1)
    return to - timedelta(hours=hours), to


NOTE_SENT = {"recipients": ["tester"], "status": "sent", "payloadDigest": "fp", "scope": "trace-t"}


def _by_key(rows: list[dict[str, Any]], *keys: str) -> dict[tuple[Any, ...], dict[str, Any]]:
    return {tuple(row[key] for key in keys): row for row in rows}


def _event_total(rows: list[dict[str, Any]], event_type: str, to_state: str | None = None) -> int:
    return sum(
        int(row["count"]) for row in rows
        if row["eventType"] == event_type and (to_state is None or row["toState"] == to_state)
    )


async def test_metrics_runs_are_windowed_by_start_and_warehouse(store: ScanStore) -> None:
    w_from, w_to = _window()
    inside = w_to - timedelta(minutes=30)
    assert await store.insert_run(_run(
        "scan-in", startedAt=inside.isoformat(),
        finishedAt=(inside + timedelta(seconds=4)).isoformat(),
        status="succeeded", partial=True, trigger="retry",
        sourceStatus=[{"source": "expiry", "status": "ok", "rows": 6, "durationMs": 88}],
        counts={"alertsSuppressed": 3},
    ))
    # 窗口左端点：含
    assert await store.insert_run(_run("scan-edge", startedAt=w_from.isoformat(), status="failed",
                                       errorSummary="auth_failed:token_missing"))
    assert await store.insert_run(_run("scan-old", startedAt=(w_to - timedelta(days=10)).isoformat(),
                                       status="succeeded"))
    assert await store.insert_run(_run("scan-other", startedAt=inside.isoformat(), warehouse="W02"))
    # 尚未开始的排队记录：按入队时刻入窗（PG 的 started_at = COALESCE(%s, now())）
    assert await store.insert_run(_run("scan-queued", queuedAt=inside.isoformat()))

    rows = await store.list_runs_for_metrics(
        started_from=w_from.isoformat(), started_to=w_to.isoformat(), warehouses=["W01"],
    )
    assert [row["scanId"] for row in rows] == ["scan-edge", "scan-in", "scan-queued"]
    scan_in = rows[1]
    assert (scan_in["trigger"], scan_in["status"], scan_in["partial"]) == ("retry", "succeeded", True)
    assert scan_in["sourceStatus"] == [{"source": "expiry", "status": "ok", "rows": 6, "durationMs": 88}]
    assert scan_in["counts"] == {"alertsSuppressed": 3}
    # PG 按会话时区输出 ISO 字符串、Memory 按写入值原样返回：比较解析后的时间点
    assert _parse_iso(scan_in["finishedAt"]) == inside + timedelta(seconds=4)
    assert _parse_iso(scan_in["startedAt"]) == inside
    assert rows[0]["errorSummary"] == "auth_failed:token_missing"
    everything = await store.list_runs_for_metrics(
        started_from=w_from.isoformat(), started_to=w_to.isoformat(), warehouses=None,
    )
    assert {row["scanId"] for row in everything} == {"scan-edge", "scan-in", "scan-queued", "scan-other"}


async def test_metrics_alert_events_and_handling_share_one_definition(store: ScanStore) -> None:
    w_from, w_to = _window()
    a_id = (await store.upsert_alert(_alert("fp-a", "P1"), notification=NOTE_SENT)).alert_id
    # 同指纹、更高严重度 → 升级事件（换一次扫描：同 scan+trace 的重复写入算重放，不算升级）
    await store.upsert_alert(
        _alert("fp-a", "P0", scanId="scan-b", traceId="trace-u"),
        notification={**NOTE_SENT, "scope": "trace-esc"},
    )
    assert await store.claim_alert(a_id, assignee="admin", assignee_user_id="a-1") is not None
    b_id = (await store.upsert_alert(_alert("fp-b", "P2", warehouseId="W02"))).alert_id
    c_id = (await store.upsert_alert(_alert("fp-c", "P1"))).alert_id
    assert await store.transition_alert(
        c_id, "resolved", reason="人工处理完毕", actor_type="user", actor_id="admin",
    ) is not None
    d_id = (await store.upsert_alert(_alert("fp-d", "P2", warehouseId="W02"))).alert_id

    events = await store.count_alert_events(
        created_from=w_from.isoformat(), created_to=w_to.isoformat(), warehouses=["W01"],
    )
    assert _event_total(events, "created") == 2
    assert _event_total(events, "escalated") == 1
    assert _event_total(events, "claimed") == 1
    assert _event_total(events, "transition", "resolved") == 1
    other = await store.count_alert_events(
        created_from=w_from.isoformat(), created_to=w_to.isoformat(), warehouses=["W02"],
    )
    assert (_event_total(other, "created"), _event_total(other, "escalated")) == (2, 0)

    rows = await store.list_alert_handling(
        touched_from=w_from.isoformat(), touched_to=w_to.isoformat(), warehouses=["W01"],
    )
    by_id = {row["alertId"]: row for row in rows}
    assert set(by_id) == {a_id, c_id}  # a 当前活跃（已认领）；c 窗口内关闭；b / d 属 W02
    assert (by_id[a_id]["state"], by_id[a_id]["severity"]) == ("open", "P0")
    assert by_id[a_id]["claimedAt"] is not None
    assert (by_id[c_id]["state"], by_id[c_id]["resolvedReason"]) == ("resolved", "人工处理完毕")
    assert by_id[c_id]["resolvedAt"] is not None and by_id[c_id]["firstSeenAt"] is not None
    everything = await store.list_alert_handling(
        touched_from=w_from.isoformat(), touched_to=w_to.isoformat(), warehouses=None,
    )
    assert {row["alertId"] for row in everything} == {a_id, b_id, c_id, d_id}
    # 窗口内没有任何认领 / 关闭动作时，只剩当前活跃的
    past_from, past_to = w_to - timedelta(days=3), w_to - timedelta(days=2)
    past = await store.list_alert_handling(
        touched_from=past_from.isoformat(), touched_to=past_to.isoformat(), warehouses=None,
    )
    assert {row["alertId"] for row in past} == {a_id, b_id, d_id}


async def test_metrics_notifications_count_created_read_and_unread(store: ScanStore) -> None:
    w_from, w_to = _window()
    await store.upsert_alert(_alert("fp-n1", "P1"), notification={**NOTE_SENT, "recipients": ["admin", "ckjl001"]})
    await store.upsert_alert(_alert("fp-n2", "P2", warehouseId="W02"), notification={**NOTE_SENT, "scope": "trace-w2"})
    mine = await store.list_notifications(recipient="admin")
    assert len(mine) == 1 and mine[0]["status"] == "sent"
    assert await store.mark_notification_read(mine[0]["notificationId"], recipient="admin") is not None

    counts = await store.count_notifications(
        created_from=w_from.isoformat(), created_to=w_to.isoformat(), warehouses=["W01"],
    )
    table = _by_key(counts, "status", "channel", "createdInWindow", "readInWindow", "unreadNow")
    assert table[("sent", "in_app", True, True, False)]["count"] == 1  # admin：窗口内创建、已读
    assert table[("sent", "in_app", True, False, True)]["count"] == 1  # ckjl001：窗口内创建、未读
    everything = await store.count_notifications(
        created_from=w_from.isoformat(), created_to=w_to.isoformat(), warehouses=None,
    )
    assert sum(int(row["count"]) for row in everything) == 3
    assert sum(int(row["count"]) for row in everything if row["unreadNow"]) == 2
    assert sum(int(row["count"]) for row in everything if row["readInWindow"]) == 1


async def test_metrics_summaries_follow_the_scan_window(store: ScanStore) -> None:
    w_from, w_to = _window()
    recent = (w_to - timedelta(minutes=5)).isoformat()
    assert await store.insert_run(_run("scan-sum-in", startedAt=recent, status="succeeded"))
    assert await store.insert_run(_run("scan-sum-old", startedAt=(w_to - timedelta(days=30)).isoformat(),
                                       status="succeeded"))
    assert await store.insert_run(_run("scan-sum-w2", startedAt=recent, status="succeeded", warehouse="W02"))
    assert await store.save_scan_summaries([
        _summary("scan-sum-in", model="m-a", promptTokens=100, completionTokens=20),
        _summary("scan-sum-in", customer="C2", model="m-a", promptTokens=50, completionTokens=10),
        _summary("scan-sum-in", customer="C3", summarySource="template", fallbackReason="timeout",
                 model=None, promptTokens=0, completionTokens=0),
        _summary("scan-sum-old", model="m-old"),
        _summary("scan-sum-w2", model="m-w2"),
    ]) == 5

    rows = await store.aggregate_scan_summaries(
        started_from=w_from.isoformat(), started_to=w_to.isoformat(), warehouses=["W01"],
    )
    table = _by_key(rows, "summarySource", "fallbackReason", "model")
    assert set(table) == {("llm", None, "m-a"), ("template", "timeout", None)}
    assert (table[("llm", None, "m-a")]["summaries"],
            table[("llm", None, "m-a")]["promptTokens"],
            table[("llm", None, "m-a")]["completionTokens"]) == (2, 150, 30)
    assert table[("template", "timeout", None)]["summaries"] == 1
    everything = await store.aggregate_scan_summaries(
        started_from=(w_to - timedelta(days=40)).isoformat(), started_to=w_to.isoformat(), warehouses=None,
    )
    assert {key[2] for key in _by_key(everything, "summarySource", "fallbackReason", "model")} == {
        "m-a", "m-old", "m-w2", None,
    }


async def test_metrics_pg_excludes_backdated_events_from_window(pg_store: PostgresScanStore) -> None:
    """PG 上把一条事件回拨到窗口外：按事件时间入窗的聚合必须把它排除。"""
    w_from, w_to = _window()
    import psycopg

    alert_id = (await pg_store.upsert_alert(_alert("fp-old", "P1"))).alert_id
    with psycopg.connect(pg_store._dsn) as conn:  # noqa: SLF001 - 测试读取内部 DSN
        conn.execute(
            "UPDATE wms_agent.agent_alert_events SET created_at = %s WHERE alert_id = %s",
            ((w_to - timedelta(days=3)).isoformat(), alert_id),
        )
        conn.commit()
    inside = await pg_store.count_alert_events(
        created_from=w_from.isoformat(), created_to=w_to.isoformat(), warehouses=["W01"],
    )
    wide = await pg_store.count_alert_events(
        created_from=(w_to - timedelta(days=5)).isoformat(), created_to=w_to.isoformat(),
        warehouses=["W01"],
    )
    assert _event_total(inside, "created") == 0
    assert _event_total(wide, "created") == 1


# ---------------------------------------------------------------------------
# 阶段7.3：保留与归档契约（ADR-020）
# 两个后端跑同一份场景：先子后父、可重入、归档行能映射回接口形状。
# ---------------------------------------------------------------------------

DAY = timedelta(days=1)
RETENTION_NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
RETENTION_STEPS = [
    "notifications", "traces", "alerts", "summaries", "scanEvidence", "metricDaily", "archive",
]
COUNT_TABLES = (
    ("alerts", "agent_alerts"), ("events", "agent_alert_events"),
    ("notifications", "agent_notifications"), ("summaries", "agent_scan_summaries"),
    ("archive", "agent_archive_rows"), ("traces", "agent_traces"),
    ("toolCalls", "agent_tool_calls"), ("scans", "agent_scan_runs"),
    ("evaluated", "agent_scan_evaluated_objects"), ("observations", "agent_scan_observations"),
    ("backlog", "agent_backlog_observations"), ("metricDaily", "agent_metric_daily"),
)


def _pg_rows(store: ScanStore, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    import psycopg

    assert isinstance(store, PostgresScanStore)
    with psycopg.connect(store._dsn) as conn:  # noqa: SLF001 - 测试读取内部 DSN
        cur = conn.execute(sql, params)
        rows = cur.fetchall() if cur.description else []  # UPDATE/INSERT 没有结果集
        conn.commit()
    return [tuple(row) for row in rows]


async def _settle(
    store: ScanStore, alert_id: int, *, state: str, resolved_at: datetime | None = None,
    last_seen_at: datetime | None = None, ignored_until: datetime | None = None,
) -> None:
    """直接把告警改成指定状态与时间（接口只会写 now()）：两个后端同一语义。

    没给的时间保持原值（PG 的 last_seen_at 非空，不能写 NULL）。
    """
    values = (
        state,
        resolved_at.isoformat() if resolved_at else None,
        last_seen_at.isoformat() if last_seen_at else None,
        ignored_until.isoformat() if ignored_until else None,
    )
    if isinstance(store, MemoryScanStore):
        store.alerts[alert_id].update({
            "state": state, "resolvedAt": values[1], "ignoredUntil": values[3],
        })
        if last_seen_at is not None:
            store.alerts[alert_id]["lastSeenAt"] = values[2]
        return
    _pg_rows(
        store,
        "UPDATE wms_agent.agent_alerts SET state = %s, resolved_at = %s::timestamptz, "
        "last_seen_at = COALESCE(%s::timestamptz, last_seen_at), "
        "ignored_until = %s::timestamptz WHERE alert_id = %s",
        (*values, alert_id),
    )


async def _age_notification(store: ScanStore, alert_id: int, created_at: datetime) -> None:
    if isinstance(store, MemoryScanStore):
        for note in store.notifications:
            if note.get("alertId") == alert_id:
                note["createdAt"] = created_at.isoformat()
        return
    _pg_rows(
        store,
        "UPDATE wms_agent.agent_notifications SET created_at = %s::timestamptz WHERE alert_id = %s",
        (created_at.isoformat(), alert_id),
    )


async def _seed_traces(store: ScanStore, *, now: datetime) -> None:
    old, new = (now - 95 * DAY).isoformat(), (now - 10 * DAY).isoformat()
    if isinstance(store, MemoryScanStore):
        store.traces["trace-old"] = {"traceId": "trace-old", "createdAt": old}
        store.traces["trace-new"] = {"traceId": "trace-new", "createdAt": new}
        store.tool_calls.extend([
            {"traceId": "trace-old", "tool": "sql_query"},
            {"traceId": "trace-old", "tool": "schema_lookup"},
            {"traceId": "trace-new", "tool": "sql_query"},
        ])
        return
    _pg_rows(
        store,
        "INSERT INTO wms_agent.agent_traces (trace_id, status, created_at) "
        "VALUES (%s, 'ok', %s::timestamptz), (%s, 'ok', %s::timestamptz)",
        ("trace-old", old, "trace-new", new),
    )
    _pg_rows(
        store,
        "INSERT INTO wms_agent.agent_tool_calls (trace_id, seq, tool) VALUES "
        "('trace-old', 1, 'sql_query'), ('trace-old', 2, 'schema_lookup'), ('trace-new', 1, 'sql_query')",
    )


async def _seed_archive(store: ScanStore, *, now: datetime) -> None:
    """归档表里已有的两行：一行早于归档期（应被清掉），一行还在期内（应保留）。"""
    expired, kept = (now - 400 * DAY).isoformat(), (now - 10 * DAY).isoformat()
    if isinstance(store, MemoryScanStore):
        store.archive_rows[(ARCHIVE_TABLE_EVENTS, "999001")] = {
            "row": {"eventId": 999001}, "archivedAt": expired,
        }
        store.archive_rows[(ARCHIVE_TABLE_ALERTS, "999002")] = {
            "row": {"alertId": 999002}, "archivedAt": kept,
        }
        return
    _pg_rows(
        store,
        "INSERT INTO wms_agent.agent_archive_rows (table_name, row_id, row, archived_at) VALUES "
        "(%s, '999001', %s::jsonb, %s::timestamptz), (%s, '999002', %s::jsonb, %s::timestamptz)",
        (
            ARCHIVE_TABLE_EVENTS, json.dumps({"event_id": 999001}), expired,
            ARCHIVE_TABLE_ALERTS, json.dumps({"alert_id": 999002}), kept,
        ),
    )


async def _retention_counts(store: ScanStore) -> dict[str, int]:
    if isinstance(store, MemoryScanStore):
        return {
            "alerts": len(store.alerts), "events": len(store.events),
            "notifications": len(store.notifications),
            "summaries": len(store.scan_summaries), "archive": len(store.archive_rows),
            "traces": len(store.traces), "toolCalls": len(store.tool_calls),
            "scans": len(store.runs), "evaluated": len(store.evaluated_objects),
            "observations": len(store._observations),  # noqa: SLF001 - 测试读取内部索引
            "backlog": len(store.backlog_observations), "metricDaily": len(store.metric_daily),
        }
    return {
        name: int(_pg_rows(store, f"SELECT COUNT(*) FROM wms_agent.{table}")[0][0])
        for name, table in COUNT_TABLES
    }


async def _alert_ids(store: ScanStore) -> list[int]:
    if isinstance(store, MemoryScanStore):
        return sorted(store.alerts)
    return [int(row[0]) for row in _pg_rows(
        store, "SELECT alert_id FROM wms_agent.agent_alerts ORDER BY alert_id",
    )]


async def _seed_retention_scenario(store: ScanStore, *, now: datetime) -> dict[str, int]:
    def named(fp: str, severity: str, **extra: Any) -> dict[str, Any]:
        return _alert(fp, severity, objectId=f"N-{fp}|G-{fp}|T-{fp}", **extra)

    ids = {
        "settled": (await store.upsert_alert(named("fp-settled", "P0"), notification=NOTE_SENT)).alert_id,
        "ignoring": (await store.upsert_alert(named("fp-ignoring", "P1"), notification=NOTE_SENT)).alert_id,
        "ignored_old": (await store.upsert_alert(named("fp-ignored-old", "P1"), notification=NOTE_SENT)).alert_id,
        "open_old": (await store.upsert_alert(named("fp-open-old", "P2"), notification=NOTE_SENT)).alert_id,
        "recent": (await store.upsert_alert(named("fp-recent", "P2"), notification=NOTE_SENT)).alert_id,
    }
    await _settle(store, ids["settled"], state="resolved", resolved_at=now - 200 * DAY, last_seen_at=now - 201 * DAY)
    await _settle(store, ids["ignoring"], state="ignored", ignored_until=now + 10 * DAY, last_seen_at=now - 300 * DAY)
    await _settle(store, ids["ignored_old"], state="ignored", ignored_until=now - 199 * DAY, last_seen_at=now - 200 * DAY)
    await _settle(store, ids["open_old"], state="open", last_seen_at=now - 300 * DAY)
    await _settle(store, ids["recent"], state="resolved", resolved_at=now - 10 * DAY)
    await _age_notification(store, ids["open_old"], now - 100 * DAY)

    await _seed_traces(store, now=now)
    for scan_id, finished in (("scan-old", now - 200 * DAY), ("scan-new", now - 10 * DAY)):
        started = (finished - timedelta(minutes=5)).isoformat()
        await store.insert_run(_run(
            scan_id, queued_at=started, status="succeeded", startedAt=started,
            finishedAt=finished.isoformat(), scanTypes=["no_up"], ruleVersion="no_up=v0.2.0",
            traceId=f"trace-{scan_id}",
        ))
    await store.save_scan_summaries([
        _summary("scan-old", summary="旧扫描的摘要"),
        _summary("scan-new", summary="新扫描的摘要", customer="C2"),
    ])
    await _seed_archive(store, now=now)
    return ids


async def test_retention_archives_and_purges_in_foreign_key_safe_order(store: ScanStore) -> None:
    ids = await _seed_retention_scenario(store, now=RETENTION_NOW)

    report = await run_retention(store, policy=RetentionPolicy(), now=RETENTION_NOW)

    assert [step["step"] for step in report["steps"]] == RETENTION_STEPS
    assert report["totals"] == {
        # 挂在保留告警上的过期通知 1 条：归档（审计证据），不是删除
        "notificationsArchived": 1,
        "tracesDeleted": 1,
        # 结案 200 天的已解决告警、忽略窗口早已结束的告警；各带 1 条事件、1 条通知（随告警归档）
        "alertsArchived": 2, "eventsArchived": 2, "notificationsArchivedWithAlerts": 2,
        # scan-old 的摘要（摘要步）+ scan-old 这条终态扫描本身（证据步，子表已空）
        "summariesArchived": 1, "scansArchived": 1,
        "evaluatedObjectsArchived": 0, "observationsArchived": 0, "backlogObservationsArchived": 0,
        "metricRowsPurged": 0,
        # 归档表里 400 天前的那一行
        "archiveRowsPurged": 1,
    }
    assert report["moreRemaining"] is False
    # 先子后父：PG 上外键是 事件→告警、tool_calls→trace，顺序错了这里会直接报外键错误
    assert await _retention_counts(store) == {
        "alerts": 3, "events": 3, "notifications": 2, "summaries": 1,
        # 2 告警 + 2 事件 + 3 通知 + 1 摘要 + 1 扫描记录 + 1 条仍在归档期内的占位告警
        "archive": 10, "traces": 1, "toolCalls": 1,
        # 5 条告警各带 1 条命中观测（挂在各自的 scanId 上，与 scan-old 无关，不随它归档）
        "scans": 1, "evaluated": 0, "observations": 5, "backlog": 0, "metricDaily": 0,
    }
    assert await _alert_ids(store) == sorted(ids[key] for key in ("ignoring", "open_old", "recent"))

    # 扫描记录随证据离线；只读回落把它还原成接口形状（两个后端一致）
    assert await store.get_run("scan-old") is None
    archived_run = await store.get_archived_run("scan-old")
    assert archived_run is not None and archived_run["archived"] is True
    assert (archived_run["scanId"], archived_run["status"], archived_run["trigger"]) == (
        "scan-old", "succeeded", "manual",
    )
    assert archived_run["scanTypes"] == ["no_up"]
    assert archived_run["finishedAt"] is not None

    # 归档的摘要仍可经接口读到，且映射回与线上一致的形状
    archived = await store.list_scan_summaries("scan-old")
    assert [row["summary"] for row in archived] == ["旧扫描的摘要"]
    (row,) = archived
    assert row["archived"] is True
    assert isinstance(row["summaryId"], int)
    assert (row["ruleId"], row["severity"], row["objectCount"], row["summarySource"]) == (
        "NOUP-OVERDUE", "P0", 2, "llm",
    )
    assert row["severityCounts"] == {"P0": 2, "P1": 0, "P2": 0}
    assert row["sampleObjects"] == ["货A（已等待 10 小时）", "货B（已等待 9 小时）"]
    assert row["suggestedActions"] == [{"code": "MOVE_TO_BIN", "text": "安排上架到货位"}]
    assert (row["promptTokens"], row["completionTokens"], row["llmDurationMs"]) == (7, 5, 12)
    live = await store.list_scan_summaries("scan-new")
    assert [item["summary"] for item in live] == ["新扫描的摘要"]
    assert "archived" not in live[0]

    # 已归档的指纹再次出现：新建告警（不是命中一条已不存在的行）
    again = await store.upsert_alert(
        _alert("fp-settled", "P1", objectId="N-again|G|T", scanId="scan-again", traceId="trace-again"),
    )
    assert (again.outcome, again.alert_id != ids["settled"]) == (UPSERT_CREATED, True)

    # 可重入：再跑一轮什么都不动，归档表也不重复
    second = await run_retention(store, policy=RetentionPolicy(), now=RETENTION_NOW)
    assert set(second["totals"].values()) == {0}
    assert second["moreRemaining"] is False
    assert (await _retention_counts(store))["archive"] == 10


async def test_retention_batches_are_bounded_and_resumable(store: ScanStore) -> None:
    now = RETENTION_NOW
    for index in range(3):
        alert_id = (
            await store.upsert_alert(_alert(f"fp-old-{index}", "P1", objectId=f"N-old-{index}|G|T"))
        ).alert_id
        await _settle(store, alert_id, state="resolved", resolved_at=now - 300 * DAY, last_seen_at=now - 300 * DAY)

    seen = []
    for _ in range(4):
        report = await run_retention(store, policy=RetentionPolicy(), batch_size=1, max_batches=1, now=now)
        alerts_step = report["steps"][2]
        assert alerts_step["batches"] == 1
        seen.append(alerts_step["rows"])
    # 每轮只归档 1 条（按 alertId 升序），3 轮清空；第 4 轮为 0
    assert seen == [1, 1, 1, 0]
    assert await _alert_ids(store) == []
    counts = await _retention_counts(store)
    assert (counts["alerts"], counts["events"], counts["archive"]) == (0, 0, 6)  # 3 告警 + 3 条 created 事件


async def test_v011_archive_table_shape(pg_store: PostgresScanStore) -> None:
    columns = {
        row[0] for row in _pg_rows(
            pg_store,
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'wms_agent' AND table_name = 'agent_archive_rows'",
        )
    }
    assert columns == {"table_name", "row_id", "row", "archived_at"}
    primary_key = [
        row[0] for row in _pg_rows(
            pg_store,
            "SELECT a.attname FROM pg_index i JOIN pg_attribute a "
            "ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = 'wms_agent.agent_archive_rows'::regclass AND i.indisprimary "
            "ORDER BY array_position(i.indkey, a.attnum)",
        )
    ]
    assert primary_key == ["table_name", "row_id"]
    indexes = {
        row[0] for row in _pg_rows(
            pg_store,
            "SELECT indexname FROM pg_indexes "
            "WHERE schemaname = 'wms_agent' AND tablename = 'agent_archive_rows'",
        )
    }
    assert {"uq_archive_rows", "idx_archive_rows_archived_at", "idx_archive_rows_summary_scan"} <= indexes


async def test_notification_created_at_follows_caller_timestamp(store: ScanStore) -> None:
    """阶段 7.6 真实环境回归：PG 曾忽略调用方给的 createdAt（恒用 now()），与 Memory 后端不一致，
    导致「补写历史通知再按保留期清理」在两个后端上结果不同。"""
    created = await store.upsert_alert(_alert(fp="fp-created-at"))
    base = {"alertId": created.alert_id, "channel": "in_app", "recipient": "created-at-probe", "status": "sent"}
    when = datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc)
    assert await store.save_notification({**base, "payloadDigest": "digest-explicit", "createdAt": when.isoformat()})
    assert await store.save_notification({**base, "payloadDigest": "digest-default"})

    notes = {n["payloadDigest"]: n for n in await store.list_notifications(recipient="created-at-probe")}

    assert _parse_iso(notes["digest-explicit"]["createdAt"]) == when
    assert abs(
        (datetime.now(timezone.utc) - _parse_iso(notes["digest-default"]["createdAt"])).total_seconds()
    ) < 120


# ---------------------------------------------------------------------------
# 阶段7.7：扫描证据整批归档、通知归档、指标日聚合契约（ADR-020）
# ---------------------------------------------------------------------------

async def _archived_ids(store: ScanStore, table: str) -> list[str]:
    """某张表在归档库里的行号（两个后端同一口径）。"""
    if isinstance(store, MemoryScanStore):
        return sorted(row_id for (name, row_id) in store.archive_rows if name == table)
    return sorted(
        row[0] for row in _pg_rows(
            store,
            "SELECT row_id FROM wms_agent.agent_archive_rows WHERE table_name = %s ORDER BY row_id",
            (table,),
        )
    )


async def _seed_scan_evidence(store: ScanStore, *, now: datetime) -> dict[str, Any]:
    """两条早已完成的终态扫描（其中一条四类证据齐全），外加近期 / 排队中 / 运行中三条不该动的扫描。"""
    old_finished = now - 200 * DAY
    old_started = old_finished - timedelta(minutes=3)
    await store.insert_run(_run(
        "scan-ev-old", queued_at=(old_started - timedelta(seconds=30)).isoformat(), status="succeeded",
        startedAt=old_started.isoformat(), finishedAt=old_finished.isoformat(),
        scanTypes=["no_up", "backlog"], trigger="schedule", actorType="service", actorId="agent-inspector",
    ))
    older_finished = now - 181 * DAY
    await store.insert_run(_run(
        "scan-ev-older", queued_at=(older_finished - timedelta(minutes=2)).isoformat(), status="failed",
        startedAt=(older_finished - timedelta(minutes=1)).isoformat(),
        finishedAt=older_finished.isoformat(), scanTypes=["expiry"], errorSummary="probe",
    ))
    await store.save_scan_summaries([_summary("scan-ev-old", summary="旧证据扫描的摘要")])
    await store.save_evaluated_objects([
        {
            "scanId": "scan-ev-old", "ruleId": "NOUP-OVERDUE", "objectType": "no_up_goods",
            "objectId": f"N-ev-{index}|G|T", "dimensionHash": f"sha256:{index}", "warehouse": "W01",
            "evaluatedAt": old_started.isoformat(),
        }
        for index in range(3)
    ])
    created = await store.upsert_alert(
        _alert("fp-ev-old", "P1", objectId="N-ev-alert|G|T", scanId="scan-ev-old", traceId="trace-ev-old"),
    )
    await store.save_backlog_observations([
        {
            "scanId": "scan-ev-old", "warehouse": "W01", "queueType": queue, "value": 10 + offset,
            "observedAt": old_started.isoformat(), "ruleVersion": "v0.2.0", "sourceStatus": "ok",
        }
        for offset, queue in enumerate(("receipt", "pick"))
    ])

    recent_finished = now - 10 * DAY
    await store.insert_run(_run(
        "scan-ev-new", status="succeeded", startedAt=(recent_finished - timedelta(minutes=1)).isoformat(),
        finishedAt=recent_finished.isoformat(), scanTypes=["no_up"],
    ))
    await store.save_scan_summaries([_summary("scan-ev-new", summary="近期扫描的摘要")])
    # 排队 300 天、运行 300 天：状态不是终态，无论多久都不归档（可能仍在执行或等待接管）
    await store.insert_run(_run("scan-ev-queued", queued_at=(now - 300 * DAY).isoformat()))
    await store.insert_run(_run(
        "scan-ev-running", status="running", startedAt=(now - 300 * DAY).isoformat(), leaseOwner="worker-x",
    ))
    return {"alertId": created.alert_id, "fingerprint": (await store.get_alert(created.alert_id))["fingerprint"]}


async def test_scan_evidence_is_archived_as_one_unit_in_child_first_order(store: ScanStore) -> None:
    seeded = await _seed_scan_evidence(store, now=RETENTION_NOW)
    cutoff = (RETENTION_NOW - 180 * DAY).isoformat()

    # 一批一条：按完成时间从旧到新（200 天前完成的那条证据齐全）
    assert await store.archive_scan_evidence(cutoff, limit=1) == {
        "scans": 1, "summaries": 1, "evaluatedObjects": 3, "observations": 1, "backlogObservations": 2,
    }
    assert await store.get_run("scan-ev-old") is None
    assert await store.get_run("scan-ev-older") is not None
    assert await store.archive_scan_evidence(cutoff, limit=1) == {
        "scans": 1, "summaries": 0, "evaluatedObjects": 0, "observations": 0, "backlogObservations": 0,
    }
    assert await store.get_run("scan-ev-older") is None
    assert await store.archive_scan_evidence(cutoff, limit=1) == {
        "scans": 0, "summaries": 0, "evaluatedObjects": 0, "observations": 0, "backlogObservations": 0,
    }

    # 终态且超期的离线；近期 / 排队中 / 运行中的原样保留
    assert await store.get_run("scan-ev-old") is None
    for scan_id in ("scan-ev-new", "scan-ev-queued", "scan-ev-running"):
        assert await store.get_run(scan_id) is not None, scan_id
    archived = await store.get_archived_run("scan-ev-old")
    assert archived is not None and archived["archived"] is True
    assert (archived["status"], archived["trigger"], archived["actorType"], archived["actorId"]) == (
        "succeeded", "schedule", "service", "agent-inspector",
    )
    assert sorted(archived["scanTypes"]) == ["backlog", "no_up"]
    assert archived["finishedAt"] is not None
    assert await store.get_archived_run("scan-ev-new") is None

    # 子表行号与 evidence_row_id 一致：归档库里能按业务键定位；父表最后归档
    assert evidence_row_id("scan-ev-old", "NOUP-OVERDUE", "N-ev-0|G|T", "sha256:0") in (
        await _archived_ids(store, ARCHIVE_TABLE_EVALUATED)
    )
    assert evidence_row_id("scan-ev-old", "trace-ev-old", seeded["fingerprint"]) in (
        await _archived_ids(store, ARCHIVE_TABLE_OBSERVATIONS)
    )
    assert "scan-ev-old" in await _archived_ids(store, ARCHIVE_TABLE_SCAN_RUNS)
    assert len(await _archived_ids(store, ARCHIVE_TABLE_BACKLOG)) == 2
    assert len(await _archived_ids(store, ARCHIVE_TABLE_SUMMARIES)) == 1

    # 归档摘要仍可读；仍在线的告警，详情里的扫描简介读回落
    rows = await store.list_scan_summaries("scan-ev-old")
    assert [row["summary"] for row in rows] == ["旧证据扫描的摘要"]
    assert rows[0]["archived"] is True
    detail = await store.get_alert_detail(seeded["alertId"])
    assert detail is not None
    assert (detail["scan"]["scanId"], detail["scan"]["trigger"]) == ("scan-ev-old", "schedule")


async def test_notifications_are_archived_before_leaving_the_online_table(store: ScanStore) -> None:
    created = await store.upsert_alert(_alert(fp="fp-keep-note"))
    base = {"alertId": created.alert_id, "channel": "in_app", "recipient": "note-archive-probe", "status": "sent"}
    for key, age_days in (("note-old-1", 100), ("note-old-2", 120), ("note-old-3", 95), ("note-new", 3)):
        await store.save_notification({
            **base, "payloadDigest": key, "createdAt": (RETENTION_NOW - age_days * DAY).isoformat(),
        })
    cutoff = (RETENTION_NOW - 90 * DAY).isoformat()

    assert await store.archive_notifications_before(cutoff, limit=1) == 1  # 限批
    assert await store.archive_notifications_before(cutoff, limit=10) == 2
    assert await store.archive_notifications_before(cutoff, limit=10) == 0  # 可重入

    online = await store.list_notifications(recipient="note-archive-probe")
    assert [note["payloadDigest"] for note in online] == ["note-new"]
    assert len(await _archived_ids(store, ARCHIVE_TABLE_NOTIFICATIONS)) == 3


async def test_metric_daily_upserts_per_warehouse_day_and_lists_by_date_window(store: ScanStore) -> None:
    rows = [
        {"metricDate": "2026-11-20", "warehouse": "W01", "timezone": "Asia/Shanghai",
         "metrics": {"scans": {"total": 2}}},
        {"metricDate": "2026-11-21", "warehouse": "W01", "timezone": "Asia/Shanghai",
         "metrics": {"scans": {"total": 3}}},
        {"metricDate": "2026-11-21", "warehouse": "W02", "timezone": "Asia/Shanghai",
         "metrics": {"scans": {"total": 7}}},
    ]
    assert await store.save_metric_daily(rows) == 3
    # 同一「仓库 · 日」重算是覆盖，不是追加
    assert await store.save_metric_daily([{**rows[1], "metrics": {"scans": {"total": 5}}}]) == 1

    listed = await store.list_metric_daily(
        date_from="2026-11-20", date_to="2026-11-22", warehouses=["W01", "W02"],
    )
    assert [(row["metricDate"], row["warehouse"]) for row in listed] == [
        ("2026-11-20", "W01"), ("2026-11-21", "W01"), ("2026-11-21", "W02"),
    ]
    assert [row["metrics"]["scans"]["total"] for row in listed] == [2, 5, 7]
    assert {row["timezone"] for row in listed} == {"Asia/Shanghai"}
    assert all(row["updatedAt"] for row in listed)

    # 日期窗口左闭右开 + 仓库过滤 + 不传仓库不过滤
    assert [row["warehouse"] for row in await store.list_metric_daily(
        date_from="2026-11-21", date_to="2026-11-22", warehouses=["W02"],
    )] == ["W02"]
    assert await store.list_metric_daily(
        date_from="2026-11-21", date_to="2026-11-21", warehouses=["W01"],
    ) == []
    assert len(await store.list_metric_daily(
        date_from="2026-11-20", date_to="2026-11-22", warehouses=None,
    )) == 3

    assert await store.purge_metric_daily_before("2026-11-21", limit=10) == 1
    assert [row["metricDate"] for row in await store.list_metric_daily(
        date_from="2026-11-01", date_to="2026-12-01", warehouses=None,
    )] == ["2026-11-21", "2026-11-21"]
    assert await store.purge_metric_daily_before("2026-11-21", limit=10) == 0


async def test_v012_metric_daily_table_shape(pg_store: PostgresScanStore) -> None:
    import psycopg

    columns = {
        row[0] for row in _pg_rows(
            pg_store,
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'wms_agent' AND table_name = 'agent_metric_daily'",
        )
    }
    assert columns == {"metric_date", "warehouse", "timezone", "metrics", "created_at", "updated_at"}
    primary_key = [
        row[0] for row in _pg_rows(
            pg_store,
            "SELECT a.attname FROM pg_index i JOIN pg_attribute a "
            "ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = 'wms_agent.agent_metric_daily'::regclass AND i.indisprimary "
            "ORDER BY array_position(i.indkey, a.attnum)",
        )
    ]
    assert primary_key == ["metric_date", "warehouse"]
    indexes = {
        row[0] for row in _pg_rows(
            pg_store,
            "SELECT indexname FROM pg_indexes "
            "WHERE schemaname = 'wms_agent' AND tablename = 'agent_metric_daily'",
        )
    }
    assert {"uq_metric_daily", "idx_metric_daily_warehouse_date"} <= indexes
    # 「仓库 · 日」唯一由数据库保证：绕过 upsert 直接插入重复行会被拒绝
    insert = (
        "INSERT INTO wms_agent.agent_metric_daily (metric_date, warehouse, metrics) VALUES "
        "('2030-01-01', 'W01', '{}'::jsonb), ('2030-01-01', 'W01', '{}'::jsonb)"
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        _pg_rows(pg_store, insert)
    _pg_rows(pg_store, "DELETE FROM wms_agent.agent_metric_daily WHERE metric_date = '2030-01-01'")