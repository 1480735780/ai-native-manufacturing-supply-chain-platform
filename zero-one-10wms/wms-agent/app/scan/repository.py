"""巡检四张表的存储：schema `wms_agent`。

- `agent_scan_runs`：持久队列。领取写租约（lease_owner/leased_at）并把 `attempt` 列 +1；
  完成写入按租约 fencing，过期执行者不能覆盖新执行结果；
- `agent_alerts`：告警（按活动态 fingerprint 去重）；
- `agent_alert_events`：append-only 事件（created / escalated / transition）；
- `agent_notifications`：通知记录（dry_run 也落库，不发送）。

PG 不可用时**不降级内存**，而是抛 `ScanStoreUnavailableError`（PG 故障拒绝）。
内存后端仅由显式配置 `store_backend=memory` 选择，用于单测/离线回放；
两个后端共用同一份契约测试（tests/test_scan_store_contract.py），队列、租约、
告警事务语义必须逐条对齐，不能用内存实现掩盖 PG 差异。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import uuid
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

SCHEMA = "wms_agent"
ACTIVE_STATES = ("open", "acknowledged")
ACTIVE_RUN_STATES = ("queued", "running")
TERMINAL_RUN_STATES = ("succeeded", "failed", "cancelled")
# 总尝试次数上限（含首次）：attempt 在每次领取时 +1 且从不归零，超过即 failed(stale)。
MAX_ATTEMPTS = 3
SEVERITY_RANK = {"P0": 3, "P1": 2, "P2": 1}

# 告警状态机：open→acknowledged→resolved|ignored；open 也可直接进终态。
# 终态（resolved/ignored）不可再转移；ignored→open（复发）由 upsert 新建处理。
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"acknowledged", "resolved", "ignored"}),
    "acknowledged": frozenset({"resolved", "ignored"}),
}

# 告警 upsert 结果：created=新建；updated=复发（级别不高于更新前）；
# escalated=级别高于更新前；suppressed=被未到期的 ignored 抑制（未写任何行）；
# replayed=同一 (scanId, traceId, fingerprint) 已处理过（租约失效后重复执行），
#          不增加 occurrence、不写事件/通知，避免 fencing 保护扫描记录却漏掉告警副作用。
UPSERT_CREATED = "created"
UPSERT_UPDATED = "updated"
UPSERT_ESCALATED = "escalated"
UPSERT_SUPPRESSED = "suppressed"
UPSERT_REPLAYED = "replayed"

# 阶段5 自动关闭事件：条件消失（覆盖记录证明该对象本次未违反条件）时写 condition_cleared。
AUTO_RESOLVE_EVENT = "condition_cleared"


@dataclass(frozen=True)
class AlertUpsertResult:
    """upsert_alert 的返回值。suppressed 必须由调用方显式跳过 updated/escalated/notify。"""

    alert_id: int
    outcome: str
    severity: str | None
    previous_severity: str | None = None
    notification_saved: bool = False

    @property
    def created(self) -> bool:
        return self.outcome == UPSERT_CREATED


def _valid_transition(from_state: str, to_state: str) -> bool:
    return to_state in ALLOWED_TRANSITIONS.get(from_state, frozenset())


def _severity_rank(severity: str | None) -> int:
    return SEVERITY_RANK.get(str(severity or ""), 0)


def _parse_iso(value: Any) -> datetime | None:
    """解析 ISO 8601（兼容 'Z'），失败返回 None。"""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _in_window(moment: datetime | None, lo: datetime | None, hi: datetime | None) -> bool:
    """时间窗左闭右开 ``[lo, hi)``；任一端点或待判时间缺失都算不在窗口内（不猜测）。"""
    return moment is not None and lo is not None and hi is not None and lo <= moment < hi


def _sorted_grouped(grouped: dict[tuple[Any, ...], Any]) -> list[tuple[tuple[Any, ...], Any]]:
    """分组结果排序：与 PG 的 ``ORDER BY … NULLS LAST`` 对齐（None 排在最后）。"""
    return sorted(
        grouped.items(),
        key=lambda item: tuple(
            (value is None, "" if value is None else str(value)) for value in item[0]
        ),
    )


def _json_list(value: Any) -> list[Any]:
    """JSON 数组字段的容错解析：非数组（缺失 / 坏数据 / 对象）一律当空列表。"""
    parsed = _safe_json(value)
    return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []


# 归档表（V011）登记的来源表名。ARCHIVE_TABLES 的顺序即清理顺序：先子后父
# （事件 / 通知 → 告警；评估覆盖 / 命中观测 / 积压样本 / 摘要 → 扫描记录）。
ARCHIVE_TABLE_ALERTS = "agent_alerts"
ARCHIVE_TABLE_EVENTS = "agent_alert_events"
ARCHIVE_TABLE_NOTIFICATIONS = "agent_notifications"
ARCHIVE_TABLE_SUMMARIES = "agent_scan_summaries"
ARCHIVE_TABLE_EVALUATED = "agent_scan_evaluated_objects"
ARCHIVE_TABLE_OBSERVATIONS = "agent_scan_observations"
ARCHIVE_TABLE_BACKLOG = "agent_backlog_observations"
ARCHIVE_TABLE_SCAN_RUNS = "agent_scan_runs"
ARCHIVE_TABLES = (
    ARCHIVE_TABLE_EVENTS, ARCHIVE_TABLE_NOTIFICATIONS, ARCHIVE_TABLE_EVALUATED,
    ARCHIVE_TABLE_OBSERVATIONS, ARCHIVE_TABLE_BACKLOG, ARCHIVE_TABLE_SUMMARIES,
    ARCHIVE_TABLE_ALERTS, ARCHIVE_TABLE_SCAN_RUNS,
)
ARCHIVE_TABLE_KEYS = {
    ARCHIVE_TABLE_EVENTS: "events",
    ARCHIVE_TABLE_NOTIFICATIONS: "notifications",
    ARCHIVE_TABLE_EVALUATED: "evaluatedObjects",
    ARCHIVE_TABLE_OBSERVATIONS: "observations",
    ARCHIVE_TABLE_BACKLOG: "backlogObservations",
    ARCHIVE_TABLE_SUMMARIES: "summaries",
    ARCHIVE_TABLE_ALERTS: "alerts",
    ARCHIVE_TABLE_SCAN_RUNS: "scans",
}
# 归档子表里没有代理主键的行（评估覆盖、命中观测）：用业务唯一键的 md5 作归档行号。
# PG 侧用 concat_ws(分隔符, ...) + md5(text) 计算同一个值，两个后端的归档行号一致。
ROW_ID_SEPARATOR = "\x1f"


def evidence_row_id(*values: Any) -> str:
    """无代理主键的子表行的归档行号（与 PG 的 md5(concat_ws(...)) 结果一致）。"""
    joined = ROW_ID_SEPARATOR.join("" if value is None else str(value) for value in values)
    return hashlib.md5(joined.encode("utf-8")).hexdigest()

SCAN_BRIEF_KEYS = (
    "scanId", "trigger", "status", "partial", "ruleVersion", "scanTypes",
    "startedAt", "finishedAt", "warehouse", "dryRun", "scheduleSlot",
    "archived",  # 仅当扫描已归档（读回落）时出现
)


def scan_brief(run: dict[str, Any]) -> dict[str, Any]:
    """告警详情里内嵌的触发扫描：只保留抽屉判断状态需要的信息。

    完整扫描记录（配置快照、触发身份、执行者、租约、错误明细）按 `can_view_scan`
    只对本人/管理员可见；告警详情对能看该仓库告警的人开放，不能借它带出完整记录。
    """
    return {key: run[key] for key in SCAN_BRIEF_KEYS if key in run}


def _settled_at(alert: dict[str, Any]) -> datetime | None:
    """告警的「最后活动时间」：解决时间、忽略窗口结束时间、最后命中时间三者的最大值。

    任一时间缺失不影响其它项；三者都缺返回 None（视为无法判断，不归档）。
    """
    moments = [
        _parse_iso(alert.get("resolvedAt")),
        _parse_iso(alert.get("ignoredUntil")),
        _parse_iso(alert.get("lastSeenAt")) or _parse_iso(alert.get("firstSeenAt")),
    ]
    known = [moment for moment in moments if moment is not None]
    return max(known) if known else None


def summary_from_archive(data: dict[str, Any]) -> dict[str, Any]:
    """归档摘要行（``to_jsonb`` 快照，snake_case 列名）→ 与线上一致的接口形状。

    归档行统一带 ``archived=True``，调用方据此区分「线上」与「已归档」。
    """
    return {
        "summaryId": data.get("summary_id"),
        "scanId": data.get("scan_id"),
        "traceId": data.get("trace_id"),
        "ruleId": data.get("rule_id"),
        "ruleVersion": data.get("rule_version"),
        "warehouse": data.get("warehouse"),
        "customer": data.get("customer") or "",
        "severity": data.get("severity"),
        "objectCount": data.get("object_count"),
        "severityCounts": data.get("severity_counts") or {},
        "sampleObjects": data.get("sample_objects") or [],
        "summary": data.get("summary"),
        "summarySource": normalize_summary_source(data.get("summary_source")),
        "fallbackReason": data.get("fallback_reason"),
        "fallbackDetail": data.get("fallback_detail"),
        "suggestedActions": data.get("suggested_actions") or [],
        "model": data.get("model"),
        "promptTokens": data.get("prompt_tokens") or 0,
        "completionTokens": data.get("completion_tokens") or 0,
        "llmDurationMs": data.get("llm_duration_ms"),
        "createdAt": data.get("created_at"),
        "archived": True,
    }


_ZONE_SUFFIX_RE = re.compile(r"\[[^\]]+\]\s*$")


def _parse_observed_at(value: Any) -> datetime | None:
    """观测时间 → aware datetime；兼容 Java ``ZonedDateTime`` 的 ``[Asia/Shanghai]`` 后缀。

    与 ``_parse_iso`` 的差别：只接受带时区偏移的输入（观测时间必须可比较、可落 TIMESTAMPTZ），
    不会把 naive 时间当 UTC 补上——缺偏移宁可报错也不猜测。
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else None
    if not isinstance(value, str):
        return None
    text = _ZONE_SUFFIX_RE.sub("", value.strip()).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def _ignore_active(until: Any, *, now: datetime | None = None) -> bool:
    """ignored_until 是否仍在有效期（含时区比较）。"""
    end = _parse_iso(until)
    if end is None:
        return False
    return end > (now or datetime.now(timezone.utc))


def _is_ignoring(until: Any, state: str | None) -> bool:
    return state == "ignored" and _ignore_active(until)


# agent_scan_runs 列顺序：前 17 列是旧表基线，V001/V005/V007/V010 增量补列。
# INSERT/SELECT/row 映射三处严格按此顺序，避免列错位。
# 末尾 4 列（V010）是重试归属：只在入队时写入，执行阶段的 UPDATE 不触碰。
RUN_COLUMNS: tuple[str, ...] = (
    "scan_id", "trigger", "actor_type", "actor_id", "status", "partial",
    "source_status", "config_hash", "rule_version", "scan_types", "request_id",
    "schedule_slot", "scan_key", "queued_at", "started_at", "finished_at",
    "counts", "error_summary", "warehouse", "dry_run", "notification_mode",
    "payload_hash", "trace_id", "attempt", "lease_owner", "leased_at",
    "executor_type", "executor_id", "actor_user_id", "config_snapshot",
    "config_version",
    "retry_of_scan_id", "origin_actor_type", "origin_actor_id", "origin_trigger",
)
RUN_SELECT = ", ".join(RUN_COLUMNS)
# 执行阶段可写字段：不含 queued_at/attempt/lease_* 等队列簿记列，
# 这些列只能由 insert_run（入队）/claim_next_queued（领取）/recover_stale（恢复）改写。
RUN_MUTABLE_FIELDS: tuple[str, ...] = (
    "status", "partial", "sourceStatus", "ruleVersion", "startedAt", "finishedAt",
    "counts", "errorSummary", "warehouse", "dryRun", "notificationMode",
    "payloadHash", "traceId", "executorType", "executorId",
)
# queued_at / started_at 两列允许调用方不传，落库时由 DB 补 now()。
_RUN_INSERT_SQL = (
    f"INSERT INTO {SCHEMA}.agent_scan_runs ({RUN_SELECT}) VALUES ("
    + ",".join(
        "COALESCE(%s, now())" if col in ("queued_at", "started_at") else "%s"
        for col in RUN_COLUMNS
    )
    + ")"
)
_RUN_MUTABLE_SET_SQL = (
    "status = EXCLUDED.status, partial = EXCLUDED.partial, "
    "source_status = EXCLUDED.source_status, rule_version = EXCLUDED.rule_version, "
    # started_at NOT NULL：调用方没给就保留原值（领取时写入的时间）
    f"started_at = COALESCE(EXCLUDED.started_at, {SCHEMA}.agent_scan_runs.started_at), "
    "finished_at = EXCLUDED.finished_at, "
    "counts = EXCLUDED.counts, error_summary = EXCLUDED.error_summary, "
    "warehouse = EXCLUDED.warehouse, dry_run = EXCLUDED.dry_run, "
    "notification_mode = EXCLUDED.notification_mode, "
    "payload_hash = EXCLUDED.payload_hash, trace_id = EXCLUDED.trace_id, "
    "executor_type = EXCLUDED.executor_type, executor_id = EXCLUDED.executor_id"
)
# 非 fencing 写入（入队后补字段/测试直调）：只更新可写字段，绝不覆盖队列簿记列。
_RUN_UPSERT_SQL = (
    f"{_RUN_INSERT_SQL} ON CONFLICT (scan_id) DO UPDATE SET {_RUN_MUTABLE_SET_SQL}"
)
# fencing 写入（worker 执行路径）：必须仍持有租约且处于 running，否则 0 行 → ScanLeaseLostError。
_RUN_FENCED_UPDATE_SQL = (
    f"UPDATE {SCHEMA}.agent_scan_runs SET "
    "status = %(status)s, partial = %(partial)s, source_status = %(sourceStatus)s, "
    "rule_version = %(ruleVersion)s, started_at = %(startedAt)s, finished_at = %(finishedAt)s, "
    "counts = %(counts)s, error_summary = %(errorSummary)s, warehouse = %(warehouse)s, "
    "dry_run = %(dryRun)s, notification_mode = %(notificationMode)s, "
    "payload_hash = %(payloadHash)s, trace_id = %(traceId)s, "
    "executor_type = %(executorType)s, executor_id = %(executorId)s, "
    "lease_owner = CASE WHEN %(status)s IN ('succeeded','failed','cancelled') "
    "THEN NULL ELSE lease_owner END, "
    "leased_at = CASE WHEN %(status)s IN ('succeeded','failed','cancelled') "
    "THEN NULL ELSE leased_at END "
    "WHERE scan_id = %(scanId)s AND lease_owner = %(leaseOwner)s AND status = 'running'"
)


class ScanStoreUnavailableError(RuntimeError):
    """PG 故障或配置错误：拒绝 accepting/执行巡检，不静默降级。"""


class ScanStoreConflictError(RuntimeError):
    """幂等键/活动唯一索引冲突：已存在同 key 的 queued/running 扫描。"""


class ScanLeaseLostError(RuntimeError):
    """租约失效（fencing 拒绝）：执行者已不再持有该扫描的租约，本次写入被丢弃。"""


SCAN_DDL: tuple[str, ...] = (
    f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA}.agent_scan_runs (
        scan_id        TEXT PRIMARY KEY,
        trigger        TEXT,
        actor_type     TEXT,
        actor_id       TEXT,
        status         TEXT,
        partial        BOOLEAN NOT NULL DEFAULT false,
        source_status  TEXT,
        config_hash    TEXT,
        rule_version   TEXT,
        scan_types     TEXT,
        request_id     TEXT,
        schedule_slot  TEXT,
        scan_key       TEXT,
        started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
        finished_at    TIMESTAMPTZ,
        counts         TEXT,
        error_summary  TEXT
    )
    """,
    # 幂等唯一索引（NULL 不参与唯一约束）
    f"CREATE UNIQUE INDEX IF NOT EXISTS uq_scan_runs_request "
    f"ON {SCHEMA}.agent_scan_runs(request_id, actor_id) "
    f"WHERE request_id IS NOT NULL AND actor_id IS NOT NULL",
    f"CREATE UNIQUE INDEX IF NOT EXISTS uq_scan_runs_schedule "
    f"ON {SCHEMA}.agent_scan_runs(schedule_slot, config_hash, scan_types) "
    f"WHERE schedule_slot IS NOT NULL AND config_hash IS NOT NULL",
    # 同一 scan_key 只允许一个 queued/running
    f"CREATE UNIQUE INDEX IF NOT EXISTS uq_scan_runs_active_key "
    f"ON {SCHEMA}.agent_scan_runs(scan_key) "
    f"WHERE status IN ('queued','running')",
    f"CREATE INDEX IF NOT EXISTS idx_scan_runs_queue "
    f"ON {SCHEMA}.agent_scan_runs(status, started_at)",
    f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA}.agent_alerts (
        alert_id          BIGSERIAL PRIMARY KEY,
        fingerprint       TEXT NOT NULL,
        rule_id           TEXT NOT NULL,
        rule_version      TEXT,
        rule_params       TEXT,
        severity          TEXT,
        object_type       TEXT,
        object_id         TEXT,
        dimension         TEXT,
        title             TEXT,
        evidence          TEXT,
        suggested_actions TEXT,
        state             TEXT NOT NULL DEFAULT 'open',
        assignee          TEXT,
        warehouse_id      TEXT,
        occurrence_count  INTEGER NOT NULL DEFAULT 1,
        first_seen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_seen_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
        resolved_at       TIMESTAMPTZ,
        resolved_reason   TEXT,
        ignored_until     TIMESTAMPTZ,
        scan_id           TEXT,
        trace_id          TEXT,
        rule_degraded     BOOLEAN NOT NULL DEFAULT false,
        first_severity    TEXT
    )
    """,
    # 兼容早期已建表：first_severity 为第一轮新增列
    f"ALTER TABLE {SCHEMA}.agent_alerts ADD COLUMN IF NOT EXISTS first_severity TEXT",
    f"CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_alerts_active_fp "
    f"ON {SCHEMA}.agent_alerts(fingerprint) WHERE state IN ('open','acknowledged')",
    f"CREATE INDEX IF NOT EXISTS idx_agent_alerts_list "
    f"ON {SCHEMA}.agent_alerts(state, severity, warehouse_id, last_seen_at)",
    f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA}.agent_alert_events (
        event_id    BIGSERIAL PRIMARY KEY,
        alert_id    BIGINT NOT NULL REFERENCES {SCHEMA}.agent_alerts(alert_id) ON DELETE CASCADE,
        actor_type  TEXT,
        actor_id    TEXT,
        from_state  TEXT,
        to_state    TEXT,
        reason      TEXT,
        trace_id    TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA}.agent_notifications (
        notification_id    BIGSERIAL PRIMARY KEY,
        alert_id           BIGINT REFERENCES {SCHEMA}.agent_alerts(alert_id) ON DELETE CASCADE,
        channel            TEXT,
        recipient          TEXT,
        status             TEXT,
        payload_digest     TEXT,
        provider_message_id TEXT,
        created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
        sent_at            TIMESTAMPTZ,
        read_at            TIMESTAMPTZ
    )
    """,
)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _scan_types_key(scan_types: list[str]) -> str:
    """scan_types 唯一索引用规范化字符串：保序去重。"""
    return ",".join(dict.fromkeys(scan_types))


def _mutable_run_fields(run: dict[str, Any]) -> dict[str, Any]:
    """执行阶段允许写入的字段子集（保持 None 值，便于把 finished_at/error_summary 清空）。"""
    return {key: run[key] for key in RUN_MUTABLE_FIELDS if key in run}


def _queue_order(run: dict[str, Any]) -> tuple[str, str]:
    """队列顺序：queued_at 优先，回退 started_at；scan_id 作为稳定的第二排序键。"""
    return (str(run.get("queuedAt") or run.get("startedAt") or ""), str(run.get("scanId") or ""))


def _notification_dedupe_key(
    alert_id: int, event: str, severity: str | None, scope: str | None, recipient: str | None
) -> str:
    """去重键 = 告警 + 事件类型 + 级别 + 事件范围（trace）+ 接收人。

    fingerprint 不含级别，不能用指纹当去重键：created 与 escalated 会撞键，
    升级通知会被唯一索引吞掉。带上事件范围后，同一次扫描重试只落一条，
    下一次扫描的再升级仍能通知。
    """
    return f"{alert_id}:{event}:{severity or '-'}:{scope or '-'}:{recipient or '-'}"


@runtime_checkable
class ScanStore(Protocol):
    async def ensure_schema(self) -> bool: ...
    async def save_run(
        self, run: dict[str, Any], *, lease_owner: str | None = None
    ) -> bool: ...
    async def get_run(self, scan_id: str) -> dict[str, Any] | None: ...
    async def find_healthy_source_scan(
        self, *, warehouse: str, source: str, after_iso: str,
    ) -> dict[str, Any] | None: ...
    async def get_run_by_scan_key(self, scan_key: str) -> dict[str, Any] | None: ...
    async def claim_next_queued(self, worker_id: str | None = None) -> dict[str, Any] | None: ...
    async def renew_lease(self, scan_id: str, lease_owner: str) -> bool: ...
    async def recover_stale(self, stale_cutoff_iso: str, max_scan: int = 100) -> int: ...
    async def insert_run(self, run: dict[str, Any]) -> bool: ...
    async def upsert_alert(
        self, alert: dict[str, Any], *, notification: dict[str, Any] | None = None,
        no_downgrade: bool = False,
    ) -> AlertUpsertResult: ...
    async def get_alert(self, alert_id: int) -> dict[str, Any] | None: ...
    async def list_alerts(
        self, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...
    async def transition_alert(
        self, alert_id: int, to_state: str, *, reason: str | None = None,
        ignored_until: str | None = None, actor_type: str | None = None,
        actor_id: str | None = None, actor_user_id: str | None = None,
        assignee_user_id: str | None = None,
    ) -> dict[str, Any] | None: ...
    async def claim_alert(
        self, alert_id: int, *, assignee: str, assignee_user_id: str | None = None,
    ) -> dict[str, Any] | None: ...
    async def list_alerts_page(
        self, filters: dict[str, Any] | None = None, *,
        last_seen_at: str | None = None, last_alert_id: int | None = None,
        page_size: int = 50,
    ) -> list[dict[str, Any]]: ...
    async def get_alert_detail(self, alert_id: int) -> dict[str, Any] | None: ...
    async def save_notification(self, note: dict[str, Any]) -> bool: ...
    async def list_notifications(
        self, *, recipient_user_id: str | None = None, recipient: str | None = None,
        unread_only: bool = False, limit: int = 100,
    ) -> list[dict[str, Any]]: ...
    async def mark_notification_read(
        self, notification_id: int, *, recipient_user_id: str | None = None,
        recipient: str | None = None,
    ) -> dict[str, Any] | None: ...
    async def save_backlog_observations(
        self, observations: list[dict[str, Any]]
    ) -> int: ...
    async def list_backlog_observations(
        self, warehouse: str, queue_type: str, *, rule_version: str, limit: int = 50,
    ) -> list[dict[str, Any]]: ...
    async def save_evaluated_objects(self, objects: list[dict[str, Any]]) -> int: ...
    async def list_evaluated_objects(
        self, scan_id: str, *, rule_id: str | None = None,
    ) -> list[dict[str, Any]]: ...
    async def list_auto_resolve_candidates(
        self, *, warehouse: str, rule_ids: list[str], before_iso: str, limit: int = 200,
    ) -> list[dict[str, Any]]: ...
    async def auto_resolve_alert(
        self, alert_id: int, *, reason: str, scan_id: str, trace_id: str,
        before_iso: str, rule_id: str, rule_version: str, warehouse: str,
    ) -> bool: ...
    # 阶段6：LLM 聚合摘要（只摘要，不判定；与告警表无外键、不回写告警）
    async def save_scan_summaries(self, summaries: list[dict[str, Any]]) -> int: ...
    async def list_scan_summaries(self, scan_id: str) -> list[dict[str, Any]]: ...
    # 阶段7：只读指标聚合（不改任何业务状态）。时间窗左闭右开 ``[from, to)``；
    # warehouses 为 None 表示不过滤仓库（调用方必须已按令牌范围收敛）。
    # 口径见 app/scan/metrics.py：扫描与摘要按扫描 started_at 入窗；事件按事件时间入窗；
    # 告警返回「当前活跃」∪「窗口内有认领 / 关闭动作」两类；通知按创建 / 已读时间入窗。
    async def list_runs_for_metrics(
        self, *, started_from: str, started_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]: ...
    async def count_alert_events(
        self, *, created_from: str, created_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]: ...
    async def list_alert_handling(
        self, *, touched_from: str, touched_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]: ...
    async def count_notifications(
        self, *, created_from: str, created_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]: ...
    async def aggregate_scan_summaries(
        self, *, started_from: str, started_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]: ...
    # 阶段7：保留与归档（ADR-020）。每批最多 ``limit`` 行、同事务提交、可重入
    # （进程中断后重跑不会重复归档，也不会漏删）。cutoff_iso 为带时区的 ISO 时间；
    # 「早于 cutoff」才处理。trace 直接删除；通知、告警、事件、摘要、扫描证据先转归档表再删线上行。
    async def archive_notifications_before(self, cutoff_iso: str, *, limit: int) -> int: ...
    async def purge_traces_before(self, cutoff_iso: str, *, limit: int) -> int: ...
    async def archive_settled_alerts(
        self, cutoff_iso: str, *, limit: int,
    ) -> dict[str, int]: ...
    async def archive_scan_summaries(self, cutoff_iso: str, *, limit: int) -> int: ...
    async def archive_scan_evidence(self, cutoff_iso: str, *, limit: int) -> dict[str, int]: ...
    async def purge_archive_before(
        self, cutoff_iso: str, *, limit: int,
    ) -> dict[str, int]: ...
    async def get_archived_run(self, scan_id: str) -> dict[str, Any] | None: ...
    # 阶段7.7：指标日聚合（ADR-020）。metric_date 为 ``YYYY-MM-DD``（业务时区的自然日），
    # list 按 ``date_from <= metric_date < date_to`` 过滤；purge 按 ``metric_date < cutoff_date``。
    async def save_metric_daily(self, rows: list[dict[str, Any]]) -> int: ...
    async def list_metric_daily(
        self, *, date_from: str, date_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]: ...
    async def purge_metric_daily_before(self, cutoff_date: str, *, limit: int) -> int: ...


SUMMARY_SOURCES = ("llm", "template")


def normalize_summary_source(value: Any) -> str:
    """摘要来源只有两个取值；无法识别的值一律按模板处理，绝不冒充 LLM 摘要。

    Memory 与 Postgres 两个后端共用这一条规则（PG 另有 CHECK 约束兜底），
    避免单测走 Memory 时放过了会被真实库拒绝的取值。
    """
    source = str(value or "").strip().lower()
    return source if source in SUMMARY_SOURCES else "template"


def _summary_sort_key(row: dict[str, Any]) -> tuple[int, int, str, str, str]:
    """摘要排序：级别高在前 → 对象多在前 → 规则/仓库/客户，保证分页展示稳定。"""
    return (
        -_severity_rank(str(row.get("severity"))),
        -int(row.get("objectCount") or 0),
        str(row.get("ruleId") or ""),
        str(row.get("warehouse") or ""),
        str(row.get("customer") or ""),
    )


def _notification_rows(
    alert_id: int, event: str, severity: str | None, notification: dict[str, Any]
) -> list[dict[str, Any]]:
    """把通知请求展开为每个接收人一条记录；去重键由存储统一生成，调用方不能自定。"""
    recipients = notification.get("recipients")
    if not recipients:
        recipients = [notification.get("recipient")]
    rows: list[dict[str, Any]] = []
    # 稳定 user_id：手动扫描能拿到发起人的稳定 id（异步执行时随扫描记录落库）；
    # 定时扫描的接收人来自配置（只有用户名），此时为 None，按用户名回退匹配。
    recipient_user_id = notification.get("recipientUserId")
    for recipient in recipients:
        if not recipient:
            continue
        rows.append({
            "alertId": alert_id,
            "channel": notification.get("channel") or "in_app",
            "recipient": recipient,
            "recipientUserId": recipient_user_id,
            "status": notification.get("status") or "dry_run",
            "payloadDigest": notification.get("payloadDigest"),
            "dedupeKey": _notification_dedupe_key(
                alert_id, event, severity, notification.get("scope"), str(recipient)
            ),
        })
    return rows


def _notification_owned(
    row: dict[str, Any], recipient_user_id: str | None, recipient: str | None
) -> bool:
    """通知归属判定：优先按稳定 user_id，其次按用户名回退（定时接收人无稳定 id）。"""
    row_user_id = row.get("recipientUserId")
    if recipient_user_id and row_user_id:
        return str(row_user_id) == str(recipient_user_id)
    if recipient:
        return str(row.get("recipient") or "") == str(recipient)
    return recipient_user_id is None and not row_user_id


class MemoryScanStore:
    """单测/离线回放的内存实现（仅显式 `store_backend=memory` 时使用）。

    与 PostgresScanStore 共用契约测试：租约、fencing、attempt 上限、告警事务
    的语义必须一致，见 tests/test_scan_store_contract.py。
    """

    def __init__(self) -> None:
        self.runs: dict[str, dict[str, Any]] = {}
        self.alerts: dict[int, dict[str, Any]] = {}
        self._alert_seq = 0
        # fingerprint → 最新一条告警（对应 PG 的 ORDER BY alert_id DESC LIMIT 1）
        self._fp_index: dict[str, int] = {}
        self.notifications: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self._notification_seq = 0
        self._event_seq = 0
        # (scanId, traceId, fingerprint) → 已处理过的 alert_id。
        # 租约失效后同一扫描重放时命中，避免重复 occurrence/事件/通知。
        # 仅在 scanId 存在时启用（测试里手工构造的无 scanId 告警不走重放判定）。
        self._observations: dict[tuple[str, str, str], int] = {}
        # 待办积压观测样本：(scanId, queueType) 唯一，对应 PG 的 uq_backlog_observations_scan_queue
        self.backlog_observations: list[dict[str, Any]] = []
        self._backlog_obs_seq = 0
        # 评估覆盖记录（阶段5）：(scanId, ruleId, objectId, dimensionHash) 唯一
        self.evaluated_objects: list[dict[str, Any]] = []
        self._evaluated_index: set[tuple[Any, Any, Any, Any]] = set()
        # 聚合摘要（阶段6）：(scanId, ruleId, warehouse, customer) 唯一，
        # 对应 PG 的 uq_scan_summaries；同一扫描重放时整行替换、不产生重复行。
        self.scan_summaries: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        self._summary_seq = 0
        # 归档行（阶段7，对应 PG 的 agent_archive_rows）：(table_name, row_id) 唯一。
        # 这里保存接口形状的行（PG 保存 to_jsonb 快照），只用于计数与摘要回落。
        self.archive_rows: dict[tuple[str, str], dict[str, Any]] = {}
        # 问数 trace 与工具调用的保留清理（阶段7）：内存实现只为保留任务提供同口径行为，
        # 不承担问数链路；键为 trace_id。
        self.traces: dict[str, dict[str, Any]] = {}
        self.tool_calls: list[dict[str, Any]] = []
        # 指标日聚合：(metric_date "YYYY-MM-DD", warehouse) → 行
        self.metric_daily: dict[tuple[str, str], dict[str, Any]] = {}

    async def ensure_schema(self) -> bool:
        return True

    # ---------- runs：队列 ----------

    async def save_run(self, run: dict[str, Any], *, lease_owner: str | None = None) -> bool:
        scan_id = run["scanId"]
        existing = self.runs.get(scan_id)
        fields = _mutable_run_fields(run)
        if lease_owner is not None:
            # fencing：必须仍持有租约且处于 running，否则视为租约失效
            if (
                existing is None
                or existing.get("status") != "running"
                or existing.get("leaseOwner") != lease_owner
            ):
                raise ScanLeaseLostError(f"scan {scan_id} lease lost")
            merged = dict(existing)
            merged.update(fields)
            if merged.get("status") in TERMINAL_RUN_STATES:
                merged["leaseOwner"] = None
                merged["leasedAt"] = None
            self.runs[scan_id] = merged
            return True
        if existing is None:
            row = dict(run)
            row.setdefault("attempt", 0)
            if not row.get("queuedAt"):
                row["queuedAt"] = row.get("startedAt")
            self.runs[scan_id] = row
            return True
        merged = dict(existing)
        merged.update(fields)
        self.runs[scan_id] = merged
        return True

    async def get_run(self, scan_id: str) -> dict[str, Any] | None:
        found = self.runs.get(scan_id)
        return dict(found) if found else None

    async def find_healthy_source_scan(
        self, *, warehouse: str, source: str, after_iso: str,
    ) -> dict[str, Any] | None:
        cutoff = _parse_iso(after_iso)
        if cutoff is None:
            return None
        matches: list[dict[str, Any]] = []
        for run in self.runs.values():
            if run.get("status") != "succeeded" or run.get("warehouse") != warehouse:
                continue
            finished = _parse_iso(run.get("finishedAt"))
            if finished is None or finished <= cutoff:
                continue
            if any(
                item.get("source") == source
                and item.get("status") == "ok"
                and not bool(item.get("truncated", False))
                for item in (run.get("sourceStatus") or [])
                if isinstance(item, dict)
            ):
                matches.append({
                    "scanId": run.get("scanId"),
                    "finishedAt": run.get("finishedAt"),
                })
        if not matches:
            return None
        return max(
            matches,
            key=lambda item: (
                _parse_iso(item.get("finishedAt")) or _EPOCH,
                str(item.get("scanId") or ""),
            ),
        )

    async def get_run_by_scan_key(self, scan_key: str) -> dict[str, Any] | None:
        matches = [r for r in self.runs.values() if r.get("scanKey") == scan_key]
        if not matches:
            return None
        # 活动态优先（幂等冲突时唯一索引挡住的就是它），其次最近开始的
        matches.sort(
            key=lambda r: (
                r.get("status") in ACTIVE_RUN_STATES,
                str(r.get("startedAt") or ""),
            ),
            reverse=True,
        )
        return dict(matches[0])

    async def insert_run(self, run: dict[str, Any]) -> bool:
        # 幂等冲突检测（对应 PG 的部分唯一索引）
        for existing in self.runs.values():
            if run.get("requestId") and run.get("actorId"):
                if (
                    existing.get("requestId") == run["requestId"]
                    and existing.get("actorId") == run["actorId"]
                ):
                    raise ScanStoreConflictError("uq_scan_runs_request")
            if run.get("scheduleSlot") and run.get("configHash"):
                if (
                    existing.get("scheduleSlot") == run["scheduleSlot"]
                    and existing.get("configHash") == run["configHash"]
                    and _scan_types_key(existing.get("scanTypes") or [])
                    == _scan_types_key(run.get("scanTypes") or [])
                ):
                    raise ScanStoreConflictError("uq_scan_runs_schedule")
            if run.get("scanKey") and existing.get("scanKey") == run["scanKey"]:
                if existing.get("status") in ACTIVE_RUN_STATES:
                    raise ScanStoreConflictError("uq_scan_runs_active_key")
        row = dict(run)
        row.setdefault("attempt", 0)
        # V010 归属字段：与 PG 读回一致，非重试记录显式为 None 而不是缺键
        for key in ("retryOfScanId", "originActorType", "originActorId", "originTrigger"):
            row.setdefault(key, None)
        if not row.get("queuedAt"):
            row["queuedAt"] = row.get("startedAt")
        self.runs[run["scanId"]] = row
        return True

    async def claim_next_queued(self, worker_id: str | None = None) -> dict[str, Any] | None:
        wid = worker_id or uuid.uuid4().hex[:12]
        candidates = [r for r in self.runs.values() if r.get("status") == "queued"]
        if not candidates:
            return None
        candidates.sort(key=_queue_order)
        claimed = dict(candidates[0])
        now = datetime.now(timezone.utc).isoformat()
        claimed["status"] = "running"
        claimed["startedAt"] = now
        claimed["leaseOwner"] = wid
        claimed["leasedAt"] = now
        claimed["attempt"] = int(claimed.get("attempt") or 0) + 1
        self.runs[claimed["scanId"]] = claimed
        return dict(claimed)

    async def renew_lease(self, scan_id: str, lease_owner: str) -> bool:
        run = self.runs.get(scan_id)
        if run is None or run.get("status") != "running" or run.get("leaseOwner") != lease_owner:
            return False
        run["leasedAt"] = datetime.now(timezone.utc).isoformat()
        return True

    async def recover_stale(self, stale_cutoff_iso: str, max_scan: int = 100) -> int:
        """租约过期的 running → queued（attempt 未耗尽）或 failed(stale)。"""
        cutoff = _parse_iso(stale_cutoff_iso) or datetime.now(timezone.utc)
        recovered = 0
        ordered = sorted(
            self.runs.values(),
            key=lambda r: _parse_iso(r.get("leasedAt") or r.get("startedAt")) or datetime.min.replace(tzinfo=timezone.utc),
        )
        for run in ordered:
            if recovered >= max_scan:
                break
            if run.get("status") != "running":
                continue
            leased = _parse_iso(run.get("leasedAt") or run.get("startedAt"))
            if leased is None or leased >= cutoff:
                continue
            updated = dict(run)
            updated["leaseOwner"] = None
            updated["leasedAt"] = None
            if int(updated.get("attempt") or 0) < MAX_ATTEMPTS:
                updated["status"] = "queued"
                updated["errorSummary"] = "stale_requeued"
            else:
                updated["status"] = "failed"
                updated["errorSummary"] = "stale"
                updated["finishedAt"] = stale_cutoff_iso
            self.runs[run["scanId"]] = updated
            recovered += 1
        return recovered

    # ---------- alerts ----------

    @staticmethod
    def _ignore_active(alert: dict[str, Any]) -> bool:
        return _ignore_active(alert.get("ignoredUntil"))

    def _append_event(self, **fields: Any) -> dict[str, Any]:
        self._event_seq += 1
        # 与 PG 的 created_at DEFAULT now() 对齐：调用方未显式给时间时补当前时间，
        # 否则按事件时间入窗的指标聚合（阶段7）在 Memory 后端上会漏计。
        event = {"eventId": self._event_seq, **fields}
        event.setdefault("createdAt", datetime.now(timezone.utc).isoformat())
        self.events.append(event)
        return event

    def _append_notification(self, row: dict[str, Any]) -> bool:
        key = row.get("dedupeKey")
        if key and any(n.get("dedupeKey") == key for n in self.notifications):
            return False  # 与 PG 部分唯一索引一致：重复推送被忽略
        self._notification_seq += 1
        now = datetime.now(timezone.utc).isoformat()
        saved = {"notificationId": self._notification_seq, **row}
        # 与 PG 默认值对齐：created_at 默认 now；in_app（status=sent）同时写 sent_at；
        # read_at 默认未读（PG 侧为 NULL，这里统一用 None）。
        saved.setdefault("createdAt", now)
        saved.setdefault("readAt", None)
        if saved.get("status") == "sent":
            saved.setdefault("sentAt", now)
        self.notifications.append(saved)
        return True

    def _append_notifications(self, rows: list[dict[str, Any]]) -> bool:
        """逐接收人各落一条通知；任一条写入即视为已通知（不能短路，否则只写第一个接收人）。"""
        saved = [self._append_notification(row) for row in rows]
        return any(saved)

    async def upsert_alert(
        self, alert: dict[str, Any], *, notification: dict[str, Any] | None = None,
        no_downgrade: bool = False,
    ) -> AlertUpsertResult:
        severity = alert.get("severity")
        trace_id = alert.get("traceId")
        scan_id = alert.get("scanId")
        obs_key = (scan_id, trace_id, alert["fingerprint"]) if scan_id else None
        # 租约失效后同一扫描会从头重放：同一 (scanId, traceId, fingerprint) 已处理过
        # 就直接返回 replayed，绝不重复 occurrence/事件/通知。
        if obs_key is not None and obs_key in self._observations:
            return AlertUpsertResult(
                self._observations[obs_key], UPSERT_REPLAYED, severity, None, False
            )
        existing_id = self._fp_index.get(alert["fingerprint"])
        if existing_id is not None:
            old = self.alerts[existing_id]
            # ignored 抑制复发：忽略窗口未过期时不新建、不通知、不计 updated。
            if self._ignore_active(old):
                if obs_key is not None:
                    self._observations[obs_key] = existing_id
                return AlertUpsertResult(
                    existing_id, UPSERT_SUPPRESSED, old.get("severity"), old.get("severity")
                )
            if old.get("state") in ACTIVE_STATES:
                previous = old.get("severity")
                # no_downgrade：本轮该规则有数据质量跳过，禁止低级别 finding 覆盖高级别旧告警。
                # 保持旧 severity 及其配套 evidence/title，只累计 occurrence 与新鲜度。
                if no_downgrade and _severity_rank(severity) <= _severity_rank(previous):
                    old["occurrenceCount"] = int(old.get("occurrenceCount") or 1) + 1
                    old["lastSeenAt"] = alert.get("lastSeenAt") or old["lastSeenAt"]
                    old["scanId"] = alert.get("scanId") or old.get("scanId")
                    old["traceId"] = trace_id or old.get("traceId")
                    if obs_key is not None:
                        self._observations[obs_key] = existing_id
                    return AlertUpsertResult(
                        existing_id, UPSERT_UPDATED, previous, previous, False
                    )
                old["occurrenceCount"] = int(old.get("occurrenceCount") or 1) + 1
                old["lastSeenAt"] = alert.get("lastSeenAt") or old["lastSeenAt"]
                old["scanId"] = alert.get("scanId") or old.get("scanId")
                old["traceId"] = trace_id or old.get("traceId")
                # 同步 severity/evidence 等字段，保证告警与最新扫描一致
                for k in ("severity", "evidence", "dimension", "title", "suggestedActions", "ruleDegraded", "routedTo"):
                    if k in alert:
                        old[k] = alert[k]
                outcome = (
                    UPSERT_ESCALATED if _severity_rank(severity) > _severity_rank(previous)
                    else UPSERT_UPDATED
                )
                saved = False
                if outcome == UPSERT_ESCALATED:
                    self._append_event(
                        alertId=existing_id, eventType=UPSERT_ESCALATED,
                        fromState=old.get("state"), toState=old.get("state"),
                        fromSeverity=previous, toSeverity=severity, traceId=trace_id,
                        actorType="system", actorId=alert.get("scanId"),
                        reason=f"severity {previous}->{severity}",
                    )
                    if notification is not None:
                        saved = self._append_notifications(
                            _notification_rows(existing_id, UPSERT_ESCALATED, severity, notification)
                        )
                if obs_key is not None:
                    self._observations[obs_key] = existing_id
                return AlertUpsertResult(existing_id, outcome, severity, previous, saved)

        self._alert_seq += 1
        new_alert = dict(alert)
        new_alert["alertId"] = self._alert_seq
        new_alert.setdefault("state", "open")
        new_alert.setdefault("occurrenceCount", 1)
        new_alert.setdefault("firstSeverity", severity)
        new_alert.setdefault("firstSeenAt", alert.get("lastSeenAt"))
        # 与 PG _ALERT_LIST_COLUMNS 对齐：关闭原因/时限字段在创建时即存在，便于双后端返回形状一致。
        new_alert.setdefault("resolvedAt", None)
        new_alert.setdefault("resolvedReason", None)
        new_alert.setdefault("ignoredUntil", None)
        self.alerts[self._alert_seq] = new_alert
        self._fp_index[alert["fingerprint"]] = self._alert_seq
        if obs_key is not None:
            self._observations[obs_key] = self._alert_seq
        self._append_event(
            alertId=self._alert_seq, eventType=UPSERT_CREATED,
            fromState=None, toState="open", fromSeverity=None, toSeverity=severity,
            traceId=trace_id, actorType="system", actorId=alert.get("scanId"), reason=None,
        )
        saved = False
        if notification is not None:
            saved = self._append_notifications(
                _notification_rows(self._alert_seq, UPSERT_CREATED, severity, notification)
            )
        return AlertUpsertResult(self._alert_seq, UPSERT_CREATED, severity, None, saved)

    async def get_alert(self, alert_id: int) -> dict[str, Any] | None:
        found = self.alerts.get(alert_id)
        return dict(found) if found else None

    async def list_alerts(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        items = [dict(a) for a in self.alerts.values()]
        return _filter_and_sort_alerts(items, filters)

    async def transition_alert(
        self, alert_id: int, to_state: str, *, reason: str | None = None,
        ignored_until: str | None = None, actor_type: str | None = None,
        actor_id: str | None = None, actor_user_id: str | None = None,
        assignee_user_id: str | None = None,
    ) -> dict[str, Any] | None:
        alert = self.alerts.get(alert_id)
        if alert is None or alert.get("state") not in ACTIVE_STATES:
            return None
        if not _valid_transition(alert["state"], to_state):
            return None
        from_state = alert["state"]
        alert.update(state=to_state, reason=reason, ignoredUntil=ignored_until)
        # ack 只记录确认者/确认时间，不改 assignee（认领是独立动作）。
        if to_state == "acknowledged":
            alert["acknowledgedBy"] = actor_id
            alert["acknowledgedAt"] = datetime.now(timezone.utc).isoformat()
        if to_state in ("resolved", "ignored"):
            alert["resolvedAt"] = datetime.now(timezone.utc).isoformat()
            alert["resolvedReason"] = reason
        self._append_event(
            alertId=alert_id, eventType="transition",
            fromState=from_state, toState=to_state, reason=reason,
            actorType=actor_type, actorId=actor_id, actorUserId=actor_user_id,
            traceId=alert.get("traceId"),
        )
        return dict(alert)

    async def claim_alert(
        self, alert_id: int, *, assignee: str, assignee_user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """认领告警：仅活动态可认领；已被他人认领（不同 stable id）返回 None→409。"""
        alert = self.alerts.get(alert_id)
        if alert is None or alert.get("state") not in ACTIVE_STATES:
            return None
        current = alert.get("assigneeUserId")
        if current and current != assignee_user_id:
            return None
        alert["assignee"] = assignee
        alert["assigneeUserId"] = assignee_user_id
        alert["claimedAt"] = datetime.now(timezone.utc).isoformat()
        self._append_event(
            alertId=alert_id, eventType="claimed",
            fromState=alert.get("state"), toState=alert.get("state"),
            actorType="user", actorId=assignee, actorUserId=assignee_user_id,
            traceId=alert.get("traceId"),
        )
        return dict(alert)

    async def list_alerts_page(
        self, filters: dict[str, Any] | None = None, *,
        last_seen_at: str | None = None, last_alert_id: int | None = None,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        items = _filter_and_sort_alerts([dict(a) for a in self.alerts.values()], filters)
        if last_seen_at is not None and last_alert_id is not None:
            # 游标：(lastSeenAt, alertId) 之后（更旧），两者严格字典序
            items = [
                a for a in items
                if (str(a.get("lastSeenAt") or ""), a.get("alertId") or 0)
                < (last_seen_at, last_alert_id)
            ]
        elif last_seen_at is not None:
            items = [a for a in items if str(a.get("lastSeenAt") or "") < last_seen_at]
        return items[:max(1, min(page_size, 200))]

    async def get_alert_detail(self, alert_id: int) -> dict[str, Any] | None:
        alert = self.alerts.get(alert_id)
        if alert is None:
            return None
        detail = dict(alert)
        detail.setdefault("ruleParams", {})
        detail["events"] = [dict(e) for e in self.events if e.get("alertId") == alert_id]
        run = self.runs.get(alert.get("scanId") or "")
        if run is None:  # 扫描记录已随保留期归档：读回落，仍给出状态 / 完成时间
            run = await self.get_archived_run(alert.get("scanId") or "")
        detail["scan"] = scan_brief(run) if run is not None else None
        return detail

    async def save_notification(self, note: dict[str, Any]) -> bool:
        return self._append_notification(dict(note))

    async def list_notifications(
        self, *, recipient_user_id: str | None = None, recipient: str | None = None,
        unread_only: bool = False, limit: int = 100,
    ) -> list[dict[str, Any]]:
        items = [dict(n) for n in self.notifications]
        if recipient_user_id is not None or recipient is not None:
            items = [
                n for n in items
                if _notification_owned(n, recipient_user_id, recipient)
            ]
        if unread_only:
            items = [n for n in items if not n.get("readAt")]
        items.sort(key=lambda n: n.get("notificationId") or 0, reverse=True)
        return items[:max(1, min(limit, 500))]

    async def mark_notification_read(
        self, notification_id: int, *, recipient_user_id: str | None = None,
        recipient: str | None = None,
    ) -> dict[str, Any] | None:
        for note in self.notifications:
            if note.get("notificationId") != notification_id:
                continue
            # 稳定 user_id 隔离：他人通知不允许标记已读（无稳定 id 时按用户名回退）。
            if not _notification_owned(note, recipient_user_id, recipient):
                return None
            note["readAt"] = datetime.now(timezone.utc).isoformat()
            return dict(note)
        return None

    # ---------- backlog：待办积压观测样本 ----------

    async def save_backlog_observations(
        self, observations: list[dict[str, Any]]
    ) -> int:
        """落本次完整快照的样本；(scanId, queueType) 重复的行跳过（幂等）。返回新增行数。"""
        saved = 0
        existing = {
            (o.get("scanId"), o.get("queueType")) for o in self.backlog_observations
        }
        for obs in observations:
            key = (obs.get("scanId"), obs.get("queueType"))
            if key in existing:
                continue
            observed_at = _parse_observed_at(obs.get("observedAt"))
            if observed_at is None:
                raise ValueError("observedAt must be an ISO-8601 string with timezone offset")
            self._backlog_obs_seq += 1
            self.backlog_observations.append({
                "observationId": self._backlog_obs_seq,
                # 与 PG 对齐：observedAt 落成规范 ISO（去掉 Java 区域后缀），排序按真实时间
                **{k: v for k, v in obs.items() if k != "observationId"},
                "observedAt": observed_at.isoformat(),
            })
            existing.add(key)
            saved += 1
        return saved

    async def list_backlog_observations(
        self, warehouse: str, queue_type: str, *, rule_version: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """按 (observedAt, observationId) 稳定升序返回某仓库某队列的基线样本。"""
        rows = [
            dict(o) for o in self.backlog_observations
            if o.get("warehouse") == warehouse and o.get("queueType") == queue_type
            and o.get("ruleVersion") == rule_version
        ]
        # observedAt 可能带不同偏移（+08:00 / +00:00），按解析后的时刻排序而不是字符串序
        rows.sort(key=lambda o: (_parse_observed_at(o.get("observedAt")) or datetime.min.replace(tzinfo=timezone.utc),
                                 o.get("observationId") or 0))
        return rows[-limit:] if limit > 0 else rows

    # ---------- evaluated objects（阶段5：评估覆盖证据） ----------

    async def save_evaluated_objects(self, objects: list[dict[str, Any]]) -> int:
        """幂等落库：同一 (scanId, ruleId, objectId, dimensionHash) 只写一次。"""
        saved = 0
        for obj in objects:
            key = (
                obj.get("scanId"), obj.get("ruleId"), obj.get("objectId"),
                obj.get("dimensionHash"),
            )
            if key in self._evaluated_index:
                continue
            self._evaluated_index.add(key)
            self.evaluated_objects.append(dict(obj))
            saved += 1
        return saved

    async def list_evaluated_objects(
        self, scan_id: str, *, rule_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            dict(o) for o in self.evaluated_objects
            if o.get("scanId") == scan_id and (rule_id is None or o.get("ruleId") == rule_id)
        ]

    # ---------- scan summaries（阶段6：LLM 聚合摘要） ----------

    async def save_scan_summaries(self, summaries: list[dict[str, Any]]) -> int:
        """按 (scanId, ruleId, warehouse, customer) 幂等写入，返回写入（新增或替换）的行数。"""
        saved = 0
        for row in summaries:
            key = (
                str(row.get("scanId") or ""), str(row.get("ruleId") or ""),
                str(row.get("warehouse") or ""), str(row.get("customer") or ""),
            )
            stored = dict(row)
            stored["customer"] = key[3]
            stored["summarySource"] = normalize_summary_source(row.get("summarySource"))
            existing = self.scan_summaries.get(key)
            if existing is None:
                self._summary_seq += 1
                stored["summaryId"] = self._summary_seq
                stored["createdAt"] = datetime.now(timezone.utc).isoformat()
            else:
                stored["summaryId"] = existing["summaryId"]
                stored["createdAt"] = datetime.now(timezone.utc).isoformat()
            self.scan_summaries[key] = stored
            saved += 1
        return saved

    async def list_scan_summaries(self, scan_id: str) -> list[dict[str, Any]]:
        rows = [dict(r) for r in self.scan_summaries.values() if r.get("scanId") == scan_id]
        if not rows:
            # 线上已归档的扫描：回落归档行（带 archived=True），与 PG 行为一致
            rows = [
                {**dict(entry["row"]), "archived": True}
                for (table, _row_id), entry in self.archive_rows.items()
                if table == ARCHIVE_TABLE_SUMMARIES and entry["row"].get("scanId") == scan_id
            ]
        return sorted(rows, key=_summary_sort_key)

    # ---------- 阶段7：只读指标聚合（与 PostgresScanStore 同口径，供契约测试比对） ----------

    async def list_runs_for_metrics(
        self, *, started_from: str, started_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        lo, hi = _parse_iso(started_from), _parse_iso(started_to)
        rows: list[dict[str, Any]] = []
        for run in self.runs.values():
            # 尚未开始的排队记录：与 PG 的 started_at = COALESCE(%s, now()) 对齐，按入队时间入窗
            started_at = run.get("startedAt") or run.get("queuedAt")
            if not _in_window(_parse_iso(started_at), lo, hi):
                continue
            if warehouses is not None and run.get("warehouse") not in warehouses:
                continue
            rows.append({
                "scanId": run.get("scanId"),
                "trigger": run.get("trigger"),
                "status": run.get("status"),
                "partial": bool(run.get("partial")),
                "startedAt": started_at,
                "finishedAt": run.get("finishedAt"),
                "sourceStatus": [
                    dict(item) for item in (run.get("sourceStatus") or []) if isinstance(item, dict)
                ],
                "counts": dict(run.get("counts") or {}),
                "errorSummary": run.get("errorSummary"),
            })
        rows.sort(key=lambda row: (_parse_iso(row["startedAt"]) or _EPOCH, str(row["scanId"])))
        return rows

    async def count_alert_events(
        self, *, created_from: str, created_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        lo, hi = _parse_iso(created_from), _parse_iso(created_to)
        grouped: dict[tuple[str | None, str | None, str | None], int] = {}
        for event in self.events:
            alert = self.alerts.get(event.get("alertId"))
            if warehouses is not None and (
                alert is None or alert.get("warehouseId") not in warehouses
            ):
                continue
            if not _in_window(_parse_iso(event.get("createdAt")), lo, hi):
                continue
            key = (event.get("eventType"), event.get("fromState"), event.get("toState"))
            grouped[key] = grouped.get(key, 0) + 1
        return [
            {"eventType": key[0], "fromState": key[1], "toState": key[2], "count": count}
            for key, count in _sorted_grouped(grouped)
        ]

    async def list_alert_handling(
        self, *, touched_from: str, touched_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        lo, hi = _parse_iso(touched_from), _parse_iso(touched_to)
        rows: list[dict[str, Any]] = []
        for alert in self.alerts.values():
            if warehouses is not None and alert.get("warehouseId") not in warehouses:
                continue
            touched = _in_window(_parse_iso(alert.get("claimedAt")), lo, hi) or _in_window(
                _parse_iso(alert.get("resolvedAt")), lo, hi
            )
            if alert.get("state") not in ACTIVE_STATES and not touched:
                continue
            rows.append({
                "alertId": alert.get("alertId"),
                "ruleId": alert.get("ruleId"),
                "severity": alert.get("severity"),
                "state": alert.get("state"),
                "firstSeenAt": alert.get("firstSeenAt"),
                "lastSeenAt": alert.get("lastSeenAt"),
                "claimedAt": alert.get("claimedAt"),
                "resolvedAt": alert.get("resolvedAt"),
                "resolvedReason": alert.get("resolvedReason"),
            })
        rows.sort(key=lambda row: int(row["alertId"] or 0))
        return rows

    async def count_notifications(
        self, *, created_from: str, created_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        lo, hi = _parse_iso(created_from), _parse_iso(created_to)
        grouped: dict[tuple[str | None, str | None, bool, bool, bool], int] = {}
        for note in self.notifications:
            if warehouses is not None:
                alert = self.alerts.get(note.get("alertId"))
                if alert is None or alert.get("warehouseId") not in warehouses:
                    continue
            read_at = _parse_iso(note.get("readAt"))
            key = (
                note.get("status"), note.get("channel"),
                _in_window(_parse_iso(note.get("createdAt")), lo, hi),
                _in_window(read_at, lo, hi),
                read_at is None,
            )
            grouped[key] = grouped.get(key, 0) + 1
        return [
            {
                "status": key[0], "channel": key[1], "createdInWindow": key[2],
                "readInWindow": key[3], "unreadNow": key[4], "count": count,
            }
            for key, count in _sorted_grouped(grouped)
        ]

    async def aggregate_scan_summaries(
        self, *, started_from: str, started_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        lo, hi = _parse_iso(started_from), _parse_iso(started_to)
        grouped: dict[tuple[str | None, str | None, str | None], list[int]] = {}
        for row in self.scan_summaries.values():
            run = self.runs.get(row.get("scanId")) or {}
            if not _in_window(_parse_iso(run.get("startedAt") or run.get("queuedAt")), lo, hi):
                continue
            if warehouses is not None and run.get("warehouse") not in warehouses:
                continue
            key = (row.get("summarySource"), row.get("fallbackReason"), row.get("model"))
            bucket = grouped.setdefault(key, [0, 0, 0])
            bucket[0] += 1
            bucket[1] += int(row.get("promptTokens") or 0)
            bucket[2] += int(row.get("completionTokens") or 0)
        return [
            {
                "summarySource": key[0], "fallbackReason": key[1], "model": key[2],
                "summaries": totals[0], "promptTokens": totals[1],
                "completionTokens": totals[2],
            }
            for key, totals in _sorted_grouped(grouped)
        ]

    # ---------- 阶段7：保留与归档（与 PostgresScanStore 同口径；每批 limit 行，可重入） ----------

    def _archive_row(self, table: str, row_id: Any, row: dict[str, Any]) -> None:
        """写入归档行；同一 (table, row_id) 已存在时保留原归档时间（对应 PG 的 ON CONFLICT DO NOTHING）。"""
        key = (table, str(row_id))
        if key not in self.archive_rows:
            self.archive_rows[key] = {
                "row": dict(row),
                "archivedAt": datetime.now(timezone.utc).isoformat(),
            }

    async def archive_notifications_before(self, cutoff_iso: str, *, limit: int) -> int:
        """超期通知：先写归档再删线上行（通知是「谁收到、是否已读」的审计证据，不直接删除）。"""
        cutoff = _parse_iso(cutoff_iso)
        doomed = sorted(
            (
                note for note in self.notifications
                if _in_window(_parse_iso(note.get("createdAt")), _EPOCH, cutoff)
            ),
            key=lambda note: note.get("notificationId") or 0,
        )[: max(1, limit)]
        for note in doomed:
            self._archive_row(ARCHIVE_TABLE_NOTIFICATIONS, note.get("notificationId"), note)
        doomed_ids = {id(note) for note in doomed}
        self.notifications[:] = [n for n in self.notifications if id(n) not in doomed_ids]
        return len(doomed)

    async def purge_traces_before(self, cutoff_iso: str, *, limit: int) -> int:
        cutoff = _parse_iso(cutoff_iso)
        doomed = sorted(
            (
                trace for trace in self.traces.values()
                if _in_window(_parse_iso(trace.get("createdAt")), _EPOCH, cutoff)
            ),
            key=lambda trace: (_parse_iso(trace.get("createdAt")) or _EPOCH, str(trace.get("traceId"))),
        )[: max(1, limit)]
        trace_ids = {trace.get("traceId") for trace in doomed}
        # 先子（工具调用）后父（trace）：显式删除，不依赖外键级联
        self.tool_calls[:] = [c for c in self.tool_calls if c.get("traceId") not in trace_ids]
        for trace_id in trace_ids:
            self.traces.pop(trace_id, None)
        return len(doomed)

    async def archive_settled_alerts(self, cutoff_iso: str, *, limit: int) -> dict[str, int]:
        cutoff = _parse_iso(cutoff_iso)
        eligible = sorted(
            alert_id for alert_id, alert in self.alerts.items()
            if alert.get("state") not in ACTIVE_STATES
            and _in_window(_settled_at(alert), _EPOCH, cutoff)
        )[: max(1, limit)]
        events = 0
        cascaded = 0
        for alert_id in eligible:
            # 先归档子行（事件），再归档父行（告警）；顺序与 PG 一致
            for event in [e for e in self.events if e.get("alertId") == alert_id]:
                self._archive_row(ARCHIVE_TABLE_EVENTS, event.get("eventId"), event)
                self.events.remove(event)
                events += 1
            # 与 PG 外键 ON DELETE CASCADE 一致：告警删除时其通知一并离线；先归档再删（审计证据）
            for note in [n for n in self.notifications if n.get("alertId") == alert_id]:
                self._archive_row(ARCHIVE_TABLE_NOTIFICATIONS, note.get("notificationId"), note)
                self.notifications.remove(note)
                cascaded += 1
            self._archive_row(ARCHIVE_TABLE_ALERTS, alert_id, self.alerts[alert_id])
            del self.alerts[alert_id]
        if eligible:
            # fingerprint 索引指向已归档告警时必须清掉，否则复发时 upsert 会命中不存在的行
            self._fp_index = {
                fp: alert_id for fp, alert_id in self._fp_index.items()
                if alert_id in self.alerts
            }
        return {"alerts": len(eligible), "events": events, "notifications": cascaded}

    async def archive_scan_summaries(self, cutoff_iso: str, *, limit: int) -> int:
        cutoff = _parse_iso(cutoff_iso)
        cap = max(1, limit)
        doomed = []
        for key, row in self.scan_summaries.items():
            run = self.runs.get(row.get("scanId")) or {}
            finished = _parse_iso(
                run.get("finishedAt") or run.get("startedAt") or run.get("queuedAt")
            )
            if _in_window(finished, _EPOCH, cutoff):
                doomed.append(key)
        doomed.sort(key=lambda key: self.scan_summaries[key].get("summaryId") or 0)
        for key in doomed[:cap]:
            row = self.scan_summaries.pop(key)
            self._archive_row(ARCHIVE_TABLE_SUMMARIES, row.get("summaryId"), row)
        return min(len(doomed), cap)

    async def archive_scan_evidence(self, cutoff_iso: str, *, limit: int) -> dict[str, int]:
        """终态且超期的扫描：子表先归档删除，再归档删除扫描记录本身（先子后父）。

        只处理 succeeded / failed / cancelled；queued / running 永不归档。
        """
        cutoff = _parse_iso(cutoff_iso)

        def _finished(run: dict[str, Any]) -> datetime | None:
            return _parse_iso(run.get("finishedAt") or run.get("startedAt") or run.get("queuedAt"))

        eligible = sorted(
            (
                scan_id for scan_id, run in self.runs.items()
                if run.get("status") in TERMINAL_RUN_STATES
                and _in_window(_finished(run), _EPOCH, cutoff)
            ),
            key=lambda scan_id: (_finished(self.runs[scan_id]) or _EPOCH, scan_id),
        )[: max(1, limit)]
        counts = {
            "scans": 0, "summaries": 0, "evaluatedObjects": 0,
            "observations": 0, "backlogObservations": 0,
        }
        if not eligible:
            return counts
        selected = set(eligible)
        for key, row in list(self.scan_summaries.items()):
            if row.get("scanId") in selected:
                del self.scan_summaries[key]
                self._archive_row(ARCHIVE_TABLE_SUMMARIES, row.get("summaryId"), row)
                counts["summaries"] += 1
        kept_objects: list[dict[str, Any]] = []
        for obj in self.evaluated_objects:
            if obj.get("scanId") in selected:
                self._archive_row(
                    ARCHIVE_TABLE_EVALUATED,
                    evidence_row_id(
                        obj.get("scanId"), obj.get("ruleId"), obj.get("objectId"), obj.get("dimensionHash"),
                    ),
                    obj,
                )
                self._evaluated_index.discard(
                    (obj.get("scanId"), obj.get("ruleId"), obj.get("objectId"), obj.get("dimensionHash"))
                )
                counts["evaluatedObjects"] += 1
            else:
                kept_objects.append(obj)
        self.evaluated_objects[:] = kept_objects
        for key in [k for k in self._observations if k[0] in selected]:
            self._observations.pop(key, None)
            self._archive_row(
                ARCHIVE_TABLE_OBSERVATIONS, evidence_row_id(*key),
                {"scanId": key[0], "traceId": key[1], "fingerprint": key[2]},
            )
            counts["observations"] += 1
        kept_samples: list[dict[str, Any]] = []
        for sample in self.backlog_observations:
            if sample.get("scanId") in selected:
                self._archive_row(ARCHIVE_TABLE_BACKLOG, sample.get("observationId"), sample)
                counts["backlogObservations"] += 1
            else:
                kept_samples.append(sample)
        self.backlog_observations[:] = kept_samples
        for scan_id in eligible:  # 父行最后
            self._archive_row(ARCHIVE_TABLE_SCAN_RUNS, scan_id, self.runs[scan_id])
            del self.runs[scan_id]
        counts["scans"] = len(eligible)
        return counts

    async def get_archived_run(self, scan_id: str) -> dict[str, Any] | None:
        entry = self.archive_rows.get((ARCHIVE_TABLE_SCAN_RUNS, str(scan_id)))
        if entry is None:
            return None
        return {**deepcopy(entry.get("row") or {}), "archived": True}

    async def save_metric_daily(self, rows: list[dict[str, Any]]) -> int:
        """按 (metric_date, warehouse) 覆盖写；返回写入行数（与 PG 的 UPSERT 行数一致）。"""
        written = 0
        now = datetime.now(timezone.utc).isoformat()
        for row in rows:
            key = (str(row.get("metricDate")), str(row.get("warehouse")))
            existing = self.metric_daily.get(key)
            self.metric_daily[key] = {
                "metricDate": key[0],
                "warehouse": key[1],
                "timezone": str(row.get("timezone") or "Asia/Shanghai"),
                "metrics": deepcopy(row.get("metrics") or {}),
                "createdAt": (existing or {}).get("createdAt") or now,
                "updatedAt": now,
            }
            written += 1
        return written

    async def list_metric_daily(
        self, *, date_from: str, date_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        wanted = None if warehouses is None else set(warehouses)
        items = [
            deepcopy(row) for row in self.metric_daily.values()
            if date_from <= row["metricDate"] < date_to
            and (wanted is None or row["warehouse"] in wanted)
        ]
        items.sort(key=lambda row: (row["metricDate"], row["warehouse"]))
        return items

    async def purge_metric_daily_before(self, cutoff_date: str, *, limit: int) -> int:
        doomed = sorted(key for key in self.metric_daily if key[0] < cutoff_date)[: max(1, limit)]
        for key in doomed:
            self.metric_daily.pop(key, None)
        return len(doomed)

    async def purge_archive_before(self, cutoff_iso: str, *, limit: int) -> dict[str, int]:
        cutoff = _parse_iso(cutoff_iso)
        cap = max(1, limit)
        counts = {key: 0 for key in ARCHIVE_TABLE_KEYS.values()}
        for table in ARCHIVE_TABLES:  # 先子后父
            doomed = sorted(
                (
                    key for key, entry in self.archive_rows.items()
                    if key[0] == table
                    and _in_window(_parse_iso(entry.get("archivedAt")), _EPOCH, cutoff)
                ),
                key=lambda key: key[1],
            )[:cap]
            for key in doomed:
                del self.archive_rows[key]
            counts[ARCHIVE_TABLE_KEYS[table]] = len(doomed)
        return counts

    async def list_auto_resolve_candidates(
        self, *, warehouse: str, rule_ids: list[str], before_iso: str, limit: int = 200,
    ) -> list[dict[str, Any]]:
        """返回可能需要自动关闭的告警（仍为 open/acknowledged 且本次扫描未刷新过）。"""
        cutoff = _parse_iso(before_iso)
        wanted = set(rule_ids or [])
        candidates: list[dict[str, Any]] = []
        for alert in self.alerts.values():
            if alert.get("state") not in ACTIVE_STATES:
                continue
            if alert.get("warehouseId") != warehouse:
                continue
            if wanted and alert.get("ruleId") not in wanted:
                continue
            last_seen = _parse_iso(alert.get("lastSeenAt"))
            if cutoff is None or last_seen is None or last_seen >= cutoff:
                continue
            if alert.get("ruleId") == "SCAN-PARTIAL":
                source_run = self.runs.get(str(alert.get("scanId") or ""))
                finished = _parse_iso((source_run or {}).get("finishedAt"))
                if (
                    source_run is None
                    or source_run.get("status") not in TERMINAL_RUN_STATES
                    or finished is None
                    or finished >= cutoff
                ):
                    continue
            candidates.append({
                "alertId": alert.get("alertId"),
                "fingerprint": alert.get("fingerprint"),
                "ruleId": alert.get("ruleId"),
                "ruleVersion": alert.get("ruleVersion"),
                "objectId": alert.get("objectId"),
                "state": alert.get("state"),
                "lastSeenAt": alert.get("lastSeenAt"),
                "warehouseId": alert.get("warehouseId"),
            })
        candidates.sort(key=lambda c: c.get("alertId") or 0)
        return candidates[:limit] if limit > 0 else candidates

    async def auto_resolve_alert(
        self, alert_id: int, *, reason: str, scan_id: str, trace_id: str,
        before_iso: str, rule_id: str, rule_version: str, warehouse: str,
    ) -> bool:
        """条件 UPDATE：状态/规则/仓库/新鲜度任一不符即跳过（与用户操作并发时以状态为准）。"""
        alert = self.alerts.get(alert_id)
        if alert is None:
            return False
        if alert.get("state") not in ACTIVE_STATES:
            return False
        if alert.get("ruleId") != rule_id or alert.get("ruleVersion") != rule_version:
            return False
        if alert.get("warehouseId") != warehouse:
            return False
        cutoff = _parse_iso(before_iso)
        last_seen = _parse_iso(alert.get("lastSeenAt"))
        if cutoff is None or last_seen is None or last_seen >= cutoff:
            return False
        if rule_id == "SCAN-PARTIAL":
            source_run = self.runs.get(str(alert.get("scanId") or ""))
            finished = _parse_iso((source_run or {}).get("finishedAt"))
            if (
                source_run is None
                or source_run.get("status") not in TERMINAL_RUN_STATES
                or finished is None
                or finished >= cutoff
            ):
                return False
        from_state = alert.get("state")
        alert["state"] = "resolved"
        alert["resolvedAt"] = datetime.now(timezone.utc).isoformat()
        alert["resolvedReason"] = reason
        self._append_event(
            alertId=alert_id, eventType=AUTO_RESOLVE_EVENT,
            fromState=from_state, toState="resolved",
            fromSeverity=alert.get("severity"), toSeverity=alert.get("severity"),
            reason=reason, traceId=trace_id, actorType="system", actorId=scan_id,
        )
        return True


def _filter_and_sort_alerts(
    items: list[dict[str, Any]], filters: dict[str, Any] | None
) -> list[dict[str, Any]]:
    filters = filters or {}
    for key in ("state", "severity", "warehouseId", "ruleId", "assignee"):
        value = filters.get(key)
        if value:
            items = [a for a in items if a.get(key) == value]
    warehouse_ids = filters.get("warehouseIds")
    if warehouse_ids:
        allowed = set(warehouse_ids)
        items = [a for a in items if a.get("warehouseId") in allowed]
    # 排序口径与 PG 一致：(lastSeenAt, alertId) 倒序，游标翻页才不会出现重复/漏行。
    return sorted(
        items,
        key=lambda a: (str(a.get("lastSeenAt") or ""), a.get("alertId") or 0),
        reverse=True,
    )

class PostgresScanStore:
    """基于 PG 的巡检存储。故障时抛 ScanStoreUnavailableError，不降级。"""

    def __init__(self, dsn: str, *, connect_timeout: int = 3, statement_timeout_ms: int = 3000) -> None:
        from app.storage.postgres import normalize_dsn

        self._dsn = normalize_dsn(dsn)
        self._connect_timeout = connect_timeout
        self._statement_timeout_ms = statement_timeout_ms

    def _connect(self):
        import psycopg

        return psycopg.connect(
            self._dsn,
            connect_timeout=self._connect_timeout,
            options=f"-c statement_timeout={self._statement_timeout_ms}",
        )

    def _ensure_schema_sync(self) -> None:
        from app.scan.migrations.runner import apply_migrations_sync

        with self._connect() as conn:
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
            for statement in SCAN_DDL:
                conn.execute(statement)
            conn.commit()
        # 基础表建好后再跑版本化迁移，兼容既有 17 列旧表（列/索引幂等）。
        apply_migrations_sync(self._dsn)

    async def ensure_schema(self) -> bool:
        try:
            await asyncio.to_thread(self._ensure_schema_sync)
            return True
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"ensure scan schema failed: {type(exc).__name__}") from exc

    # ---------- runs：队列 ----------

    def _insert_run_sync(self, run: dict[str, Any]) -> bool:
        with self._connect() as conn:
            conn.execute(_RUN_INSERT_SQL, _run_params(run))
            conn.commit()
        return True

    async def insert_run(self, run: dict[str, Any]) -> bool:
        try:
            return await asyncio.to_thread(self._insert_run_sync, run)
        except Exception as exc:  # noqa: BLE001
            # psycopg.errors.UniqueViolation → 幂等冲突，不是 PG 故障。
            # 用类名判定避免在没有 psycopg 的环境里顶层 import 失败。
            if type(exc).__name__ == "UniqueViolation":
                raise ScanStoreConflictError("uq_scan_runs") from exc
            raise ScanStoreUnavailableError(f"insert scan run failed: {type(exc).__name__}") from exc

    def _save_run_sync(self, run: dict[str, Any], lease_owner: str | None) -> bool:
        with self._connect() as conn:
            if lease_owner is None:
                # 非 fencing：只更新可写字段，不覆盖 queued_at/attempt/lease_* 等簿记列
                conn.execute(_RUN_UPSERT_SQL, _run_params(run))
                conn.commit()
                return True
            cur = conn.execute(_RUN_FENCED_UPDATE_SQL, _fenced_params(run, lease_owner))
            if cur.rowcount != 1:
                # 租约已被别人拿走（或已被恢复入队/完成）：本次结果丢弃
                conn.rollback()
                raise ScanLeaseLostError(f"scan {run['scanId']} lease lost")
            conn.commit()
        return True

    async def save_run(self, run: dict[str, Any], *, lease_owner: str | None = None) -> bool:
        try:
            return await asyncio.to_thread(self._save_run_sync, run, lease_owner)
        except ScanLeaseLostError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"save scan run failed: {type(exc).__name__}") from exc

    def _get_run_sync(self, scan_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {RUN_SELECT} FROM {SCHEMA}.agent_scan_runs WHERE scan_id = %s",
                (scan_id,),
            ).fetchone()
            conn.commit()
        return _row_to_run(row)

    async def get_run(self, scan_id: str) -> dict[str, Any] | None:
        try:
            return await asyncio.to_thread(self._get_run_sync, scan_id)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"get scan run failed: {type(exc).__name__}") from exc

    def _find_healthy_source_scan_sync(
        self, *, warehouse: str, source: str, after_iso: str,
    ) -> dict[str, Any] | None:
        pattern = json.dumps([{"source": source, "status": "ok", "truncated": False}])
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT scan_id, finished_at FROM {SCHEMA}.agent_scan_runs "
                f"WHERE warehouse = %s AND status = 'succeeded' AND finished_at > %s "
                f"AND source_status::jsonb @> %s::jsonb "
                f"ORDER BY finished_at DESC, scan_id DESC LIMIT 1",
                (warehouse, after_iso, pattern),
            ).fetchone()
            conn.commit()
        return {
            "scanId": row[0],
            "finishedAt": row[1].isoformat() if row[1] is not None else None,
        } if row is not None else None

    async def find_healthy_source_scan(
        self, *, warehouse: str, source: str, after_iso: str,
    ) -> dict[str, Any] | None:
        try:
            return await asyncio.to_thread(
                self._find_healthy_source_scan_sync,
                warehouse=warehouse, source=source, after_iso=after_iso,
            )
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(
                f"find healthy source scan failed: {type(exc).__name__}"
            ) from exc

    def _get_run_by_scan_key_sync(self, scan_key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            # 活动态优先（幂等冲突时唯一索引挡住的就是它），其次最近开始的
            row = conn.execute(
                f"SELECT scan_id FROM {SCHEMA}.agent_scan_runs "
                f"WHERE scan_key = %s "
                f"ORDER BY (status IN ('queued','running')) DESC, started_at DESC "
                f"LIMIT 1",
                (scan_key,),
            ).fetchone()
            conn.commit()
        return self._get_run_sync(row[0]) if row else None

    async def get_run_by_scan_key(self, scan_key: str) -> dict[str, Any] | None:
        try:
            return await asyncio.to_thread(self._get_run_by_scan_key_sync, scan_key)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"get run by scan key failed: {type(exc).__name__}") from exc

    def _claim_next_queued_sync(self, worker_id: str) -> dict[str, Any] | None:
        """FOR UPDATE SKIP LOCKED 领取一条 queued，写入租约并 attempt+1。"""
        with self._connect() as conn:
            with conn.transaction():
                row = conn.execute(
                    f"SELECT scan_id FROM {SCHEMA}.agent_scan_runs "
                    f"WHERE status = 'queued' "
                    f"ORDER BY COALESCE(queued_at, started_at) ASC, scan_id ASC "
                    f"FOR UPDATE SKIP LOCKED LIMIT 1"
                ).fetchone()
                if row is None:
                    return None
                conn.execute(
                    f"UPDATE {SCHEMA}.agent_scan_runs SET status = 'running', "
                    f"started_at = now(), lease_owner = %s, leased_at = now(), "
                    f"attempt = COALESCE(attempt, 0) + 1 "
                    f"WHERE scan_id = %s",
                    (worker_id, row[0]),
                )
                scan_id = row[0]
            return self._get_run_sync(scan_id)

    async def claim_next_queued(self, worker_id: str | None = None) -> dict[str, Any] | None:
        try:
            wid = worker_id or uuid.uuid4().hex[:12]
            return await asyncio.to_thread(self._claim_next_queued_sync, wid)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"claim queued scan failed: {type(exc).__name__}") from exc

    def _renew_lease_sync(self, scan_id: str, lease_owner: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE {SCHEMA}.agent_scan_runs SET leased_at = now() "
                f"WHERE scan_id = %s AND lease_owner = %s AND status = 'running'",
                (scan_id, lease_owner),
            )
            renewed = cur.rowcount == 1
            conn.commit()
        return renewed

    async def renew_lease(self, scan_id: str, lease_owner: str) -> bool:
        try:
            return await asyncio.to_thread(self._renew_lease_sync, scan_id, lease_owner)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"renew lease failed: {type(exc).__name__}") from exc

    def _recover_stale_sync(self, stale_cutoff_iso: str, max_scan: int) -> int:
        """租约过期的 running → queued（attempt 未耗尽）或 failed(stale)。

        attempt 读 `attempt` 列（领取时 +1，从不归零），不读 counts，
        所以不会被每次执行重建的 counts 清零，也不会无限重排。
        """
        with self._connect() as conn:
            with conn.transaction():
                rows = conn.execute(
                    f"SELECT scan_id, attempt FROM {SCHEMA}.agent_scan_runs "
                    f"WHERE status = 'running' AND COALESCE(leased_at, started_at) < %s "
                    f"ORDER BY COALESCE(leased_at, started_at) ASC "
                    f"LIMIT %s FOR UPDATE SKIP LOCKED",
                    (stale_cutoff_iso, max_scan),
                ).fetchall()
                for row in rows:
                    attempt = int(row[1] or 0)
                    if attempt < MAX_ATTEMPTS:
                        conn.execute(
                            f"UPDATE {SCHEMA}.agent_scan_runs "
                            f"SET status = 'queued', lease_owner = NULL, leased_at = NULL, "
                            f"error_summary = 'stale_requeued' "
                            f"WHERE scan_id = %s",
                            (row[0],),
                        )
                    else:
                        conn.execute(
                            f"UPDATE {SCHEMA}.agent_scan_runs "
                            f"SET status = 'failed', error_summary = 'stale', "
                            f"finished_at = now(), lease_owner = NULL, leased_at = NULL "
                            f"WHERE scan_id = %s",
                            (row[0],),
                        )
                return len(rows)

    async def recover_stale(self, stale_cutoff_iso: str, max_scan: int = 100) -> int:
        try:
            return await asyncio.to_thread(self._recover_stale_sync, stale_cutoff_iso, max_scan)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"recover stale scans failed: {type(exc).__name__}") from exc
    # ---------- alerts ----------

    _ALERT_INSERT_SQL = f"""
        INSERT INTO {SCHEMA}.agent_alerts
            (fingerprint, rule_id, rule_version, rule_params, severity, object_type,
             object_id, dimension, title, evidence, suggested_actions, state,
             assignee, warehouse_id, occurrence_count, scan_id, trace_id,
             rule_degraded, first_severity, routed_to,
             first_seen_at, last_seen_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'open',%s,%s,1,%s,%s,%s,%s,%s,
                COALESCE(%s::timestamptz, now()), COALESCE(%s::timestamptz, now()))
        ON CONFLICT (fingerprint) WHERE state IN ('open','acknowledged') DO NOTHING
        RETURNING alert_id
    """

    def _upsert_alert_sync(
        self, alert: dict[str, Any], notification: dict[str, Any] | None,
        no_downgrade: bool = False,
    ) -> AlertUpsertResult:
        """告警 + 事件 + 通知在同一事务内提交；按 fingerprint 锁最新一行后再决策。

        - 最新行是未到期的 ignored → suppressed（不写任何行、不通知）；
        - 最新行活动 → 原地更新；级别高于更新前即 escalated；
        - 否则（resolved / ignored 到期 / 不存在）→ 新建 open。

        与 transition_alert 的 FOR UPDATE 串行化：不会出现“刚 ignored 又插入新 open”。
        """
        fingerprint = alert["fingerprint"]
        severity = alert.get("severity")
        trace_id = alert.get("traceId")
        scan_id = alert.get("scanId")
        with self._connect() as conn:
            with conn.transaction():
                # 观察记录原子认领：同一 (scan_id, trace_id, fingerprint) 已处理即 replay。
                # 仅在有 scanId 时启用；手工构造的无 scanId 告警（旧测试）不走重放判定。
                if scan_id:
                    claimed = conn.execute(
                        f"INSERT INTO {SCHEMA}.agent_scan_observations "
                        f"(scan_id, trace_id, fingerprint) VALUES (%s,%s,%s) "
                        f"ON CONFLICT DO NOTHING RETURNING alert_id",
                        (scan_id, trace_id or "", fingerprint),
                    ).fetchone()
                    if claimed is None:
                        prior = conn.execute(
                            f"SELECT alert_id FROM {SCHEMA}.agent_scan_observations "
                            f"WHERE scan_id = %s AND trace_id = %s AND fingerprint = %s",
                            (scan_id, trace_id or "", fingerprint),
                        ).fetchone()
                        return AlertUpsertResult(
                            int(prior[0]) if prior and prior[0] is not None else -1,
                            UPSERT_REPLAYED, severity, None, False,
                        )

                def _remember(alert_id_: int) -> None:
                    if scan_id:
                        conn.execute(
                            f"UPDATE {SCHEMA}.agent_scan_observations SET alert_id = %s "
                            f"WHERE scan_id = %s AND trace_id = %s AND fingerprint = %s",
                            (alert_id_, scan_id, trace_id or "", fingerprint),
                        )

                for _round in range(2):
                    latest = conn.execute(
                        f"SELECT alert_id, state, severity, "
                        f"(state = 'ignored' AND ignored_until > now()) AS ignoring "
                        f"FROM {SCHEMA}.agent_alerts WHERE fingerprint = %s "
                        f"ORDER BY alert_id DESC LIMIT 1 FOR UPDATE",
                        (fingerprint,),
                    ).fetchone()
                    if latest is not None and latest[3]:
                        _remember(int(latest[0]))
                        return AlertUpsertResult(
                            int(latest[0]), UPSERT_SUPPRESSED, latest[2], latest[2]
                        )
                    if latest is not None and latest[1] in ACTIVE_STATES:
                        alert_id = int(latest[0])
                        previous = latest[2]
                        # no_downgrade：本轮该规则有数据质量跳过，禁止低级别 finding
                        # 覆盖高级别旧告警；只累计 occurrence 与新鲜度，保留旧 severity。
                        if no_downgrade and _severity_rank(severity) <= _severity_rank(previous):
                            conn.execute(
                                f"UPDATE {SCHEMA}.agent_alerts SET "
                                f"occurrence_count = occurrence_count + 1, "
                                f"last_seen_at = COALESCE(%s::timestamptz, now()), "
                                f"scan_id = %s, trace_id = %s WHERE alert_id = %s",
                                (alert.get("lastSeenAt"), scan_id, trace_id, alert_id),
                            )
                            _remember(alert_id)
                            return AlertUpsertResult(alert_id, UPSERT_UPDATED, previous, previous)
                        conn.execute(
                            f"UPDATE {SCHEMA}.agent_alerts SET "
                            f"occurrence_count = occurrence_count + 1, "
                            f"last_seen_at = COALESCE(%s::timestamptz, now()), "
                            f"scan_id = %s, trace_id = %s, severity = %s, evidence = %s, "
                            f"dimension = %s, title = %s, suggested_actions = %s, "
                            f"rule_degraded = %s, routed_to = %s WHERE alert_id = %s",
                            (
                                alert.get("lastSeenAt"),
                                scan_id, trace_id, severity,
                                _json(alert.get("evidence") or {}),
                                _json(alert.get("dimension") or {}),
                                alert.get("title"),
                                _json(alert.get("suggestedActions") or []),
                                bool(alert.get("ruleDegraded", False)),
                                alert.get("routedTo"),
                                alert_id,
                            ),
                        )
                        if _severity_rank(severity) <= _severity_rank(previous):
                            _remember(alert_id)
                            return AlertUpsertResult(alert_id, UPSERT_UPDATED, severity, previous)
                        self._insert_event_sync(
                            conn, alert_id, "escalated", latest[1], latest[1],
                            previous, severity, f"severity {previous}->{severity}",
                            trace_id, scan_id,
                        )
                        saved = self._insert_notifications_sync(
                            conn, alert_id, UPSERT_ESCALATED, severity, notification
                        )
                        _remember(alert_id)
                        return AlertUpsertResult(
                            alert_id, UPSERT_ESCALATED, severity, previous, saved
                        )
                    cur = conn.execute(
                        self._ALERT_INSERT_SQL,
                        (
                            fingerprint, alert.get("ruleId"), alert.get("ruleVersion"),
                            _json(alert.get("ruleParams") or {}), severity,
                            alert.get("objectType"), alert.get("objectId"),
                            _json(alert.get("dimension") or {}), alert.get("title"),
                            _json(alert.get("evidence") or {}),
                            _json(alert.get("suggestedActions") or []), alert.get("assignee"),
                            alert.get("warehouseId"), scan_id, trace_id,
                            bool(alert.get("ruleDegraded", False)), severity,
                            alert.get("routedTo"),
                            # 与 Memory 后端对齐：调用方给了观测时间就用它，
                            # 否则回落库默认 now()（自动关闭的新鲜度判定依赖这个口径）。
                            alert.get("firstSeenAt") or alert.get("lastSeenAt"),
                            alert.get("lastSeenAt"),
                        ),
                    )
                    inserted = cur.fetchone()
                    if inserted is not None:
                        alert_id = int(inserted[0])
                        self._insert_event_sync(
                            conn, alert_id, UPSERT_CREATED, None, "open",
                            None, severity, None, trace_id, scan_id,
                        )
                        saved = self._insert_notifications_sync(
                            conn, alert_id, UPSERT_CREATED, severity, notification
                        )
                        _remember(alert_id)
                        return AlertUpsertResult(alert_id, UPSERT_CREATED, severity, None, saved)
                    # 被并发插入挡住（活动态部分唯一索引）：对方已提交，回到循环头加锁后走更新分支
        raise ScanStoreUnavailableError("upsert alert: concurrent insert race unresolved")

    @staticmethod
    def _insert_event_sync(
        conn: Any, alert_id: int, event_type: str, from_state: str | None,
        to_state: str | None, from_severity: str | None, to_severity: str | None,
        reason: str | None, trace_id: str | None, actor_id: str | None,
        actor_type: str = "system",
    ) -> None:
        conn.execute(
            f"INSERT INTO {SCHEMA}.agent_alert_events "
            f"(alert_id, actor_type, actor_id, from_state, to_state, reason, trace_id, "
            f"event_type, from_severity, to_severity) "
            f"VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                alert_id, actor_type, actor_id, from_state, to_state, reason, trace_id,
                event_type, from_severity, to_severity,
            ),
        )

    @classmethod
    def _insert_notifications_sync(
        cls, conn: Any, alert_id: int, event: str, severity: str | None,
        notification: dict[str, Any] | None,
    ) -> bool:
        """按接收人逐条写入（同一事务）；任一条写入即视为已通知（不能短路）。"""
        if notification is None:
            return False
        saved = [
            cls._insert_notification_sync(conn, row)
            for row in _notification_rows(alert_id, event, severity, notification)
        ]
        return any(saved)

    @staticmethod
    def _insert_notification_sync(conn: Any, note: dict[str, Any]) -> bool:
        # dedupe_key 唯一（部分索引）：同一告警同一事件点重复推送被忽略，返回 False。
        # in_app 通知在告警事务内直接写成 sent（sent_at=now）：站内信没有外部投递环节。
        status = note.get("status")
        sent_at = "now()" if status == "sent" else None
        cur = conn.execute(
            f"""
            INSERT INTO {SCHEMA}.agent_notifications
                (alert_id, channel, recipient, recipient_user_id, status,
                 payload_digest, dedupe_key, sent_at, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,{'now()' if sent_at else 'NULL'},COALESCE(%s::timestamptz, now()))
            ON CONFLICT (dedupe_key) WHERE dedupe_key IS NOT NULL DO NOTHING
            RETURNING notification_id
            """,
            (
                note.get("alertId"), note.get("channel"), note.get("recipient"),
                note.get("recipientUserId"), status, note.get("payloadDigest"),
                note.get("dedupeKey"),
                # 调用方显式给的 createdAt 与 Memory 后端保持一致；未给时回落 now()
                note.get("createdAt"),
            ),
        )
        return cur.fetchone() is not None

    async def upsert_alert(
        self, alert: dict[str, Any], *, notification: dict[str, Any] | None = None,
        no_downgrade: bool = False,
    ) -> AlertUpsertResult:
        try:
            return await asyncio.to_thread(
                self._upsert_alert_sync, alert, notification, no_downgrade
            )
        except ScanStoreUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"upsert alert failed: {type(exc).__name__}") from exc

    _ALERT_LIST_COLUMNS = (
        "alert_id, fingerprint, rule_id, severity, object_type, object_id, "
        "dimension, title, state, assignee, warehouse_id, occurrence_count, "
        "first_seen_at, last_seen_at, scan_id, trace_id, rule_degraded, first_severity, "
        "acknowledged_by, acknowledged_at, assignee_user_id, claimed_at, routed_to, "
        "resolved_at, resolved_reason, ignored_until, rule_version"
    )

    _NOTIFICATION_COLUMNS = (
        "notification_id, alert_id, channel, recipient, recipient_user_id, status, "
        "payload_digest, provider_message_id, created_at, sent_at, read_at"
    )

    def _alert_filter_sql(self, filters: dict[str, Any]) -> tuple[str, list[Any]]:
        """告警过滤条件（列表与游标分页共用，保证两边口径一致）。"""
        sql = ""
        args: list[Any] = []
        for key, col in (("state", "state"), ("severity", "severity"),
                         ("warehouseId", "warehouse_id"), ("ruleId", "rule_id"),
                         ("assignee", "assignee")):
            if filters.get(key):
                sql += f" AND {col} = %s"
                args.append(filters[key])
        warehouse_ids = [w for w in (filters.get("warehouseIds") or []) if w]
        if warehouse_ids:
            # 令牌仓库范围：NULL 仓库的历史行也不可见（不默认放行）
            sql += " AND warehouse_id = ANY(%s)"
            args.append(warehouse_ids)
        return sql, args

    def _list_alerts_sync(self, filters: dict[str, Any] | None) -> list[dict[str, Any]]:
        filters = filters or {}
        where, args = self._alert_filter_sql(filters)
        sql = (
            f"SELECT {self._ALERT_LIST_COLUMNS} FROM {SCHEMA}.agent_alerts WHERE 1=1"
            f"{where} ORDER BY last_seen_at DESC, alert_id DESC LIMIT 200"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
            conn.commit()
        return [_row_to_alert(r) for r in rows]

    async def list_alerts(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(self._list_alerts_sync, filters)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"list alerts failed: {type(exc).__name__}") from exc

    def _list_alerts_page_sync(
        self, filters: dict[str, Any] | None, *, last_seen_at: str | None,
        last_alert_id: int | None, page_size: int,
    ) -> list[dict[str, Any]]:
        """游标分页：(last_seen_at, alert_id) 严格小于游标即取下一页。

        排序键固定 last_seen_at DESC, alert_id DESC；游标用严格小于的复合比较，
        保证同时间戳的多条告警既不漏也不重。
        """
        filters = filters or {}
        where, args = self._alert_filter_sql(filters)
        if last_seen_at is not None and last_alert_id is not None:
            where += " AND (last_seen_at, alert_id) < (%s, %s)"
            args.extend([last_seen_at, last_alert_id])
        elif last_seen_at is not None:
            where += " AND last_seen_at < %s"
            args.append(last_seen_at)
        limit = max(1, min(page_size, 200))
        sql = (
            f"SELECT {self._ALERT_LIST_COLUMNS} FROM {SCHEMA}.agent_alerts WHERE 1=1"
            f"{where} ORDER BY last_seen_at DESC, alert_id DESC LIMIT %s"
        )
        args.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
            conn.commit()
        return [_row_to_alert(r) for r in rows]

    async def list_alerts_page(
        self, filters: dict[str, Any] | None = None, *,
        last_seen_at: str | None = None, last_alert_id: int | None = None,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._list_alerts_page_sync, filters,
                last_seen_at=last_seen_at, last_alert_id=last_alert_id,
                page_size=page_size,
            )
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"list alerts page failed: {type(exc).__name__}") from exc

    def _get_alert_sync(self, alert_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {self._ALERT_LIST_COLUMNS} FROM {SCHEMA}.agent_alerts "
                f"WHERE alert_id = %s",
                (alert_id,),
            ).fetchone()
            conn.commit()
        return _row_to_alert(row) if row else None

    async def get_alert(self, alert_id: int) -> dict[str, Any] | None:
        try:
            return await asyncio.to_thread(self._get_alert_sync, alert_id)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"get alert failed: {type(exc).__name__}") from exc

    def _get_alert_detail_sync(self, alert_id: int) -> dict[str, Any] | None:
        """告警详情：告警主体 + 事件流 + 触发扫描（供前端抽屉展示证据链）。"""
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {self._ALERT_LIST_COLUMNS} FROM {SCHEMA}.agent_alerts "
                f"WHERE alert_id = %s",
                (alert_id,),
            ).fetchone()
            if row is None:
                return None
            detail = _row_to_alert(row)
            # evidence / rule_params 不在列表列里，单独取（列表第 6 列是 dimension）。
            extra = conn.execute(
                f"SELECT evidence, rule_params FROM {SCHEMA}.agent_alerts WHERE alert_id = %s",
                (alert_id,),
            ).fetchone()
            if extra is not None:
                detail["evidence"] = _safe_json(extra[0])
                detail["ruleParams"] = _safe_json(extra[1])
            events = conn.execute(
                f"SELECT event_id, alert_id, actor_type, actor_id, from_state, to_state, "
                f"reason, trace_id, created_at, event_type, from_severity, to_severity "
                f"FROM {SCHEMA}.agent_alert_events WHERE alert_id = %s ORDER BY event_id",
                (alert_id,),
            ).fetchall()
            detail["events"] = [_row_to_event(e) for e in events]
            scan_id = detail.get("scanId")
            detail["scan"] = None
            if scan_id:
                scan_row = conn.execute(
                    f"SELECT {RUN_SELECT} FROM {SCHEMA}.agent_scan_runs WHERE scan_id = %s",
                    (scan_id,),
                ).fetchone()
                if scan_row is not None:
                    detail["scan"] = scan_brief(_row_to_run(scan_row))
                else:
                    # 扫描记录已随保留期归档：读回落，仍给出状态 / 完成时间
                    archived = conn.execute(
                        f"SELECT row FROM {SCHEMA}.agent_archive_rows "
                        f"WHERE table_name = %s AND row_id = %s",
                        (ARCHIVE_TABLE_SCAN_RUNS, scan_id),
                    ).fetchone()
                    if archived is not None and isinstance(archived[0], dict):
                        detail["scan"] = scan_brief(run_from_archive(archived[0]))
            conn.commit()
        return detail

    async def get_alert_detail(self, alert_id: int) -> dict[str, Any] | None:
        try:
            return await asyncio.to_thread(self._get_alert_detail_sync, alert_id)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"get alert detail failed: {type(exc).__name__}") from exc

    def _claim_alert_sync(
        self, alert_id: int, *, assignee: str, assignee_user_id: str | None,
    ) -> dict[str, Any] | None:
        """认领：仅活动态；已被他人（不同 stable id）认领则返回 None → 409。"""
        with self._connect() as conn:
            with conn.transaction():
                row = conn.execute(
                    f"SELECT state, trace_id, assignee_user_id FROM {SCHEMA}.agent_alerts "
                    f"WHERE alert_id = %s FOR UPDATE",
                    (alert_id,),
                ).fetchone()
                if row is None or row[0] not in ACTIVE_STATES:
                    return None
                current = row[2]
                if current and current != assignee_user_id:
                    return None
                conn.execute(
                    f"UPDATE {SCHEMA}.agent_alerts SET assignee = %s, "
                    f"assignee_user_id = %s, claimed_at = now() WHERE alert_id = %s",
                    (assignee, assignee_user_id, alert_id),
                )
                self._insert_event_sync(
                    conn, alert_id, "claimed", row[0], row[0], None, None,
                    None, row[1], assignee, "user",
                )
                detail = conn.execute(
                    f"SELECT {self._ALERT_LIST_COLUMNS} FROM {SCHEMA}.agent_alerts "
                    f"WHERE alert_id = %s",
                    (alert_id,),
                ).fetchone()
        return _row_to_alert(detail) if detail else None

    async def claim_alert(
        self, alert_id: int, *, assignee: str, assignee_user_id: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            return await asyncio.to_thread(
                self._claim_alert_sync, alert_id,
                assignee=assignee, assignee_user_id=assignee_user_id,
            )
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"claim alert failed: {type(exc).__name__}") from exc

    def _transition_alert_sync(
        self, alert_id: int, to_state: str, *, reason: str | None,
        ignored_until: str | None, actor_type: str | None, actor_id: str | None,
        actor_user_id: str | None = None,
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.transaction():
                row = conn.execute(
                    f"SELECT state, trace_id FROM {SCHEMA}.agent_alerts "
                    f"WHERE alert_id = %s FOR UPDATE",
                    (alert_id,),
                ).fetchone()
                if row is None or row[0] not in ACTIVE_STATES:
                    return None
                if not _valid_transition(row[0], to_state):
                    return None
                from_state = row[0]
                # ack 只记录确认者/确认时间，不改 assignee（认领是独立动作）。
                conn.execute(
                    f"UPDATE {SCHEMA}.agent_alerts SET state = %s, resolved_reason = %s, "
                    f"ignored_until = %s, "
                    f"resolved_at = CASE WHEN %s IN ('resolved','ignored') THEN now() ELSE NULL END, "
                    f"acknowledged_by = CASE WHEN %s = 'acknowledged' THEN %s ELSE acknowledged_by END, "
                    f"acknowledged_at = CASE WHEN %s = 'acknowledged' THEN now() ELSE acknowledged_at END "
                    f"WHERE alert_id = %s AND state IN ('open','acknowledged')",
                    (
                        to_state, reason, ignored_until, to_state,
                        to_state, actor_id, to_state, alert_id,
                    ),
                )
                self._insert_event_sync(
                    conn, alert_id, "transition", from_state, to_state, None, None,
                    reason, row[1], actor_id, actor_type or "user",
                )
                return {
                    "alertId": alert_id, "fromState": from_state, "toState": to_state,
                    "acknowledgedBy": actor_id if to_state == "acknowledged" else None,
                }

    async def transition_alert(
        self, alert_id: int, to_state: str, *, reason: str | None = None,
        ignored_until: str | None = None, actor_type: str | None = None,
        actor_id: str | None = None, actor_user_id: str | None = None,
        assignee_user_id: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            return await asyncio.to_thread(
                self._transition_alert_sync, alert_id, to_state, reason=reason,
                ignored_until=ignored_until, actor_type=actor_type, actor_id=actor_id,
                actor_user_id=actor_user_id,
            )
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"transition alert failed: {type(exc).__name__}") from exc

    def _list_notifications_sync(
        self, *, recipient_user_id: str | None, recipient: str | None,
        unread_only: bool, limit: int,
    ) -> list[dict[str, Any]]:
        sql = (
            f"SELECT {self._NOTIFICATION_COLUMNS} FROM {SCHEMA}.agent_notifications WHERE 1=1"
        )
        args: list[Any] = []
        if recipient_user_id is not None or recipient is not None:
            # 稳定 user_id 优先；无稳定 id 的定时接收人按用户名回退。
            if recipient_user_id is not None:
                sql += " AND (recipient_user_id = %s OR (recipient_user_id IS NULL AND recipient = %s))"
                args.extend([recipient_user_id, recipient])
            else:
                sql += " AND recipient = %s"
                args.append(recipient)
        if unread_only:
            sql += " AND read_at IS NULL"
        sql += " ORDER BY notification_id DESC LIMIT %s"
        args.append(max(1, min(limit, 500)))
        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
            conn.commit()
        return [_row_to_notification(r) for r in rows]

    async def list_notifications(
        self, *, recipient_user_id: str | None = None, recipient: str | None = None,
        unread_only: bool = False, limit: int = 100,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._list_notifications_sync, recipient_user_id=recipient_user_id,
                recipient=recipient, unread_only=unread_only, limit=limit,
            )
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"list notifications failed: {type(exc).__name__}") from exc

    def _mark_notification_read_sync(
        self, notification_id: int, *, recipient_user_id: str | None,
        recipient: str | None,
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.transaction():
                # 稳定 user_id 隔离：他人通知不允许标记已读（无稳定 id 时按用户名回退）。
                sql = (
                    f"UPDATE {SCHEMA}.agent_notifications SET read_at = now() "
                    f"WHERE notification_id = %s"
                )
                args: list[Any] = [notification_id]
                if recipient_user_id is not None:
                    sql += " AND (recipient_user_id = %s OR (recipient_user_id IS NULL AND recipient = %s))"
                    args.extend([recipient_user_id, recipient])
                elif recipient is not None:
                    sql += " AND recipient = %s"
                    args.append(recipient)
                sql += " RETURNING " + self._NOTIFICATION_COLUMNS
                row = conn.execute(sql, args).fetchone()
        return _row_to_notification(row) if row else None

    async def mark_notification_read(
        self, notification_id: int, *, recipient_user_id: str | None = None,
        recipient: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            return await asyncio.to_thread(
                self._mark_notification_read_sync, notification_id,
                recipient_user_id=recipient_user_id, recipient=recipient,
            )
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"mark notification read failed: {type(exc).__name__}") from exc

    # ---------- backlog：待办积压观测样本（V006 agent_backlog_observations） ----------

    _BACKLOG_OBS_COLUMNS = (
        "observation_id", "scan_id", "warehouse", "queue_type", "value",
        "observed_at", "rule_version", "source_status", "created_at",
    )

    def _save_backlog_observations_sync(self, observations: list[dict[str, Any]]) -> int:
        """单事务 INSERT … ON CONFLICT (scan_id, queue_type) DO NOTHING；返回实际新增行数。

        ``observedAt`` 统一解析成 aware datetime 再绑定：数据源层已去掉 Java
        ``ZonedDateTime`` 的 ``[Asia/Shanghai]`` 区域后缀，这里再兜底一次，避免任何
        带 ISO 偏移的字符串形态触发 psycopg ``InvalidDatetimeFormat``。
        """
        if not observations:
            return 0
        saved = 0
        with self._connect() as conn:
            for obs in observations:
                observed_at = _parse_observed_at(obs.get("observedAt"))
                if observed_at is None:
                    raise ValueError("observedAt must be an ISO-8601 string with timezone offset")
                cur = conn.execute(
                    f"INSERT INTO {SCHEMA}.agent_backlog_observations "
                    "(scan_id, warehouse, queue_type, value, observed_at, rule_version, source_status) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (scan_id, queue_type) DO NOTHING RETURNING observation_id",
                    (
                        obs.get("scanId"), obs.get("warehouse"), obs.get("queueType"),
                        str(obs.get("value")), observed_at,
                        obs.get("ruleVersion"), obs.get("sourceStatus"),
                    ),
                )
                if cur.fetchone() is not None:
                    saved += 1
            conn.commit()
        return saved

    async def save_backlog_observations(self, observations: list[dict[str, Any]]) -> int:
        try:
            return await asyncio.to_thread(self._save_backlog_observations_sync, observations)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(
                f"save backlog observations failed: {type(exc).__name__}"
            ) from exc

    def _list_backlog_observations_sync(
        self, warehouse: str, queue_type: str, *, rule_version: str, limit: int,
    ) -> list[dict[str, Any]]:
        cols = ", ".join(self._BACKLOG_OBS_COLUMNS)
        body = (
            f"SELECT {cols} FROM {SCHEMA}.agent_backlog_observations "
            "WHERE warehouse = %s AND queue_type = %s AND rule_version = %s"
        )
        params: tuple[Any, ...] = (warehouse, queue_type, rule_version)
        if limit > 0:
            # 取最近 N 条：内层按降序截取，外层再恢复稳定升序（不能把 ORDER BY 拼两次）
            sql = (
                f"SELECT {cols} FROM (" + body
                + " ORDER BY observed_at DESC, observation_id DESC LIMIT %s) recent "
                "ORDER BY observed_at ASC, observation_id ASC"
            )
            params = (*params, limit)
        else:
            sql = body + " ORDER BY observed_at ASC, observation_id ASC"
        with self._connect() as conn:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            data = dict(zip(self._BACKLOG_OBS_COLUMNS, r))
            observed = data["observed_at"]
            out.append({
                "observationId": data["observation_id"],
                "scanId": data["scan_id"],
                "warehouse": data["warehouse"],
                "queueType": data["queue_type"],
                "value": str(data["value"]),
                "observedAt": observed.isoformat() if hasattr(observed, "isoformat") else str(observed),
                "ruleVersion": data["rule_version"],
                "sourceStatus": data["source_status"],
            })
        return out

    async def list_backlog_observations(
        self, warehouse: str, queue_type: str, *, rule_version: str, limit: int = 50,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._list_backlog_observations_sync, warehouse, queue_type,
                rule_version=rule_version, limit=limit,
            )
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(
                f"list backlog observations failed: {type(exc).__name__}"
            ) from exc

    def _save_notification_sync(self, note: dict[str, Any]) -> bool:
        with self._connect() as conn:
            saved = self._insert_notification_sync(conn, note)
            conn.commit()
        return saved

    async def save_notification(self, note: dict[str, Any]) -> bool:
        try:
            return await asyncio.to_thread(self._save_notification_sync, note)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(f"save notification failed: {type(exc).__name__}") from exc

    # ---------- evaluated objects（阶段5：评估覆盖证据） ----------

    def _save_evaluated_objects_sync(self, objects: list[dict[str, Any]]) -> int:
        if not objects:
            return 0
        with self._connect() as conn:
            saved = 0
            for obj in objects:
                cur = conn.execute(
                    f"""
                    INSERT INTO {SCHEMA}.agent_scan_evaluated_objects
                        (scan_id, rule_id, object_type, object_id, dimension_hash,
                         warehouse, evaluated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,COALESCE(%s::timestamptz, now()))
                    ON CONFLICT (scan_id, rule_id, object_id, dimension_hash) DO NOTHING
                    RETURNING 1
                    """,
                    (
                        obj.get("scanId"), obj.get("ruleId"), obj.get("objectType"),
                        obj.get("objectId"), obj.get("dimensionHash"), obj.get("warehouse"),
                        obj.get("evaluatedAt"),
                    ),
                )
                if cur.fetchone() is not None:
                    saved += 1
            conn.commit()
        return saved

    async def save_evaluated_objects(self, objects: list[dict[str, Any]]) -> int:
        try:
            return await asyncio.to_thread(self._save_evaluated_objects_sync, objects)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(
                f"save evaluated objects failed: {type(exc).__name__}"
            ) from exc

    def _list_evaluated_objects_sync(
        self, scan_id: str, *, rule_id: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = (
            f"SELECT scan_id, rule_id, object_type, object_id, dimension_hash, "
            f"warehouse, evaluated_at FROM {SCHEMA}.agent_scan_evaluated_objects "
            f"WHERE scan_id = %s"
        )
        params: list[Any] = [scan_id]
        if rule_id is not None:
            sql += " AND rule_id = %s"
            params.append(rule_id)
        sql += " ORDER BY rule_id, object_id, dimension_hash"
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [
            {
                "scanId": r[0], "ruleId": r[1], "objectType": r[2], "objectId": r[3],
                "dimensionHash": r[4], "warehouse": r[5],
                "evaluatedAt": r[6].isoformat() if r[6] is not None else None,
            }
            for r in rows
        ]

    async def list_evaluated_objects(
        self, scan_id: str, *, rule_id: str | None = None,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._list_evaluated_objects_sync, scan_id, rule_id=rule_id
            )
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(
                f"list evaluated objects failed: {type(exc).__name__}"
            ) from exc

    # ---------- scan summaries（阶段6：LLM 聚合摘要，只摘要不判定） ----------

    _SUMMARY_UPSERT_SQL = f"""
        INSERT INTO {SCHEMA}.agent_scan_summaries
            (scan_id, trace_id, rule_id, rule_version, warehouse, customer, severity,
             object_count, severity_counts, sample_objects, summary, summary_source,
             fallback_reason, fallback_detail, suggested_actions, model,
             prompt_tokens, completion_tokens, llm_duration_ms, created_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,now())
        ON CONFLICT (scan_id, rule_id, warehouse, customer) DO UPDATE SET
            trace_id = EXCLUDED.trace_id,
            rule_version = EXCLUDED.rule_version,
            severity = EXCLUDED.severity,
            object_count = EXCLUDED.object_count,
            severity_counts = EXCLUDED.severity_counts,
            sample_objects = EXCLUDED.sample_objects,
            summary = EXCLUDED.summary,
            summary_source = EXCLUDED.summary_source,
            fallback_reason = EXCLUDED.fallback_reason,
            fallback_detail = EXCLUDED.fallback_detail,
            suggested_actions = EXCLUDED.suggested_actions,
            model = EXCLUDED.model,
            prompt_tokens = EXCLUDED.prompt_tokens,
            completion_tokens = EXCLUDED.completion_tokens,
            llm_duration_ms = EXCLUDED.llm_duration_ms,
            created_at = now()
    """

    @staticmethod
    def _summary_json(value: Any) -> str:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, default=str)

    def _save_scan_summaries_sync(self, summaries: list[dict[str, Any]]) -> int:
        if not summaries:
            return 0
        saved = 0
        with self._connect() as conn:
            for row in summaries:
                # 防御：summary_source 只允许两个取值，异常值按模板落库而不是违反 CHECK 约束
                source = normalize_summary_source(row.get("summarySource"))
                duration = row.get("llmDurationMs")
                cur = conn.execute(
                    self._SUMMARY_UPSERT_SQL,
                    (
                        row.get("scanId"), row.get("traceId"), row.get("ruleId"), row.get("ruleVersion"),
                        row.get("warehouse"), row.get("customer") or "", row.get("severity"),
                        int(row.get("objectCount") or 0),
                        self._summary_json(row.get("severityCounts") or {}),
                        self._summary_json(row.get("sampleObjects") or []),
                        row.get("summary"), source,
                        row.get("fallbackReason"), row.get("fallbackDetail"),
                        self._summary_json(row.get("suggestedActions") or []),
                        row.get("model"),
                        int(row.get("promptTokens") or 0), int(row.get("completionTokens") or 0),
                        int(duration) if duration is not None else None,
                    ),
                )
                saved += max(0, cur.rowcount)
            conn.commit()
        return saved

    async def save_scan_summaries(self, summaries: list[dict[str, Any]]) -> int:
        try:
            return await asyncio.to_thread(self._save_scan_summaries_sync, summaries)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(
                f"save scan summaries failed: {type(exc).__name__}"
            ) from exc

    def _list_scan_summaries_sync(self, scan_id: str) -> list[dict[str, Any]]:
        sql = (
            f"SELECT summary_id, scan_id, trace_id, rule_id, rule_version, warehouse, "
            f"customer, severity, object_count, severity_counts::text, "
            f"sample_objects::text, summary, summary_source, fallback_reason, "
            f"fallback_detail, suggested_actions::text, model, prompt_tokens, "
            f"completion_tokens, llm_duration_ms, created_at "
            f"FROM {SCHEMA}.agent_scan_summaries WHERE scan_id = %s"
        )
        archive_sql = (
            f"SELECT row FROM {SCHEMA}.agent_archive_rows "
            f"WHERE table_name = %s AND row->>'scan_id' = %s"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, (scan_id,)).fetchall()
            # 线上已归档的扫描：回落归档行（带 archived=True）
            archived = (
                [] if rows
                else conn.execute(archive_sql, (ARCHIVE_TABLE_SUMMARIES, scan_id)).fetchall()
            )
        items = [
            {
                "summaryId": r[0], "scanId": r[1], "traceId": r[2], "ruleId": r[3],
                "ruleVersion": r[4], "warehouse": r[5], "customer": r[6], "severity": r[7],
                "objectCount": r[8], "severityCounts": _safe_json(r[9]) or {},
                "sampleObjects": _safe_json(r[10]) or [],
                "summary": r[11], "summarySource": r[12], "fallbackReason": r[13],
                "fallbackDetail": r[14], "suggestedActions": _safe_json(r[15]) or [],
                "model": r[16], "promptTokens": r[17], "completionTokens": r[18],
                "llmDurationMs": r[19],
                "createdAt": r[20].isoformat() if r[20] is not None else None,
            }
            for r in rows
        ]
        if not items:
            items = [
                summary_from_archive(r[0]) for r in archived
                if isinstance(r[0], dict)
            ]
        return sorted(items, key=_summary_sort_key)

    async def list_scan_summaries(self, scan_id: str) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(self._list_scan_summaries_sync, scan_id)
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(
                f"list scan summaries failed: {type(exc).__name__}"
            ) from exc

    # ---------- 阶段7：只读指标聚合（SQL 聚合；口径与 MemoryScanStore 一致） ----------

    @staticmethod
    def _metrics_filters(warehouses: list[str] | None, column: str) -> tuple[str, list[Any]]:
        """仓库过滤片段；warehouses 为空表示不过滤（调用方已按令牌范围收敛）。"""
        if not warehouses:
            return "", []
        return f" AND {column} = ANY(%s)", [list(warehouses)]

    def _list_runs_for_metrics_sync(
        self, *, started_from: str, started_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        clause, extra = self._metrics_filters(warehouses, "warehouse")
        sql = (
            f"SELECT scan_id, trigger, status, partial, started_at, finished_at, "
            f"source_status, counts, error_summary FROM {SCHEMA}.agent_scan_runs "
            f"WHERE started_at >= %s::timestamptz AND started_at < %s::timestamptz{clause} "
            f"ORDER BY started_at, scan_id"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, (started_from, started_to, *extra)).fetchall()
        return [
            {
                "scanId": r[0],
                "trigger": r[1],
                "status": r[2],
                "partial": bool(r[3]),
                "startedAt": r[4].isoformat() if r[4] is not None else None,
                "finishedAt": r[5].isoformat() if r[5] is not None else None,
                "sourceStatus": _json_list(r[6]),
                "counts": _safe_json(r[7]),
                "errorSummary": r[8],
            }
            for r in rows
        ]

    def _count_alert_events_sync(
        self, *, created_from: str, created_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        clause, extra = self._metrics_filters(warehouses, "a.warehouse_id")
        sql = (
            f"SELECT e.event_type, e.from_state, e.to_state, COUNT(*) "
            f"FROM {SCHEMA}.agent_alert_events e "
            f"JOIN {SCHEMA}.agent_alerts a ON a.alert_id = e.alert_id "
            f"WHERE e.created_at >= %s::timestamptz AND e.created_at < %s::timestamptz{clause} "
            f"GROUP BY e.event_type, e.from_state, e.to_state "
            f"ORDER BY e.event_type, e.from_state, e.to_state"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, (created_from, created_to, *extra)).fetchall()
        return [
            {"eventType": r[0], "fromState": r[1], "toState": r[2], "count": int(r[3])}
            for r in rows
        ]

    def _list_alert_handling_sync(
        self, *, touched_from: str, touched_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        clause, extra = self._metrics_filters(warehouses, "warehouse_id")
        sql = (
            f"SELECT alert_id, rule_id, severity, state, first_seen_at, last_seen_at, "
            f"claimed_at, resolved_at, resolved_reason FROM {SCHEMA}.agent_alerts "
            f"WHERE (state IN ('open','acknowledged') "
            f"OR (claimed_at >= %s::timestamptz AND claimed_at < %s::timestamptz) "
            f"OR (resolved_at >= %s::timestamptz AND resolved_at < %s::timestamptz))"
            f"{clause} ORDER BY alert_id"
        )
        with self._connect() as conn:
            rows = conn.execute(
                sql, (touched_from, touched_to, touched_from, touched_to, *extra)
            ).fetchall()

        def iso(value: Any) -> str | None:
            return value.isoformat() if value is not None else None

        return [
            {
                "alertId": r[0], "ruleId": r[1], "severity": r[2], "state": r[3],
                "firstSeenAt": iso(r[4]), "lastSeenAt": iso(r[5]),
                "claimedAt": iso(r[6]), "resolvedAt": iso(r[7]), "resolvedReason": r[8],
            }
            for r in rows
        ]

    def _count_notifications_sync(
        self, *, created_from: str, created_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        clause, extra = self._metrics_filters(warehouses, "a.warehouse_id")
        sql = (
            f"SELECT n.status, n.channel, "
            f"COALESCE(n.created_at >= %s::timestamptz AND n.created_at < %s::timestamptz, false), "
            f"COALESCE(n.read_at >= %s::timestamptz AND n.read_at < %s::timestamptz, false), "
            f"(n.read_at IS NULL), COUNT(*) "
            f"FROM {SCHEMA}.agent_notifications n "
            f"LEFT JOIN {SCHEMA}.agent_alerts a ON a.alert_id = n.alert_id "
            f"WHERE TRUE{clause} "
            f"GROUP BY n.status, n.channel, 3, 4, 5 "
            f"ORDER BY n.status NULLS LAST, n.channel NULLS LAST, 3, 4, 5"
        )
        with self._connect() as conn:
            rows = conn.execute(
                sql, (created_from, created_to, created_from, created_to, *extra)
            ).fetchall()
        return [
            {
                "status": r[0], "channel": r[1], "createdInWindow": bool(r[2]),
                "readInWindow": bool(r[3]), "unreadNow": bool(r[4]), "count": int(r[5]),
            }
            for r in rows
        ]

    def _aggregate_scan_summaries_sync(
        self, *, started_from: str, started_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        clause, extra = self._metrics_filters(warehouses, "r.warehouse")
        sql = (
            f"SELECT s.summary_source, s.fallback_reason, s.model, COUNT(*), "
            f"COALESCE(SUM(s.prompt_tokens), 0), COALESCE(SUM(s.completion_tokens), 0) "
            f"FROM {SCHEMA}.agent_scan_summaries s "
            f"JOIN {SCHEMA}.agent_scan_runs r ON r.scan_id = s.scan_id "
            f"WHERE r.started_at >= %s::timestamptz AND r.started_at < %s::timestamptz{clause} "
            f"GROUP BY s.summary_source, s.fallback_reason, s.model "
            f"ORDER BY s.summary_source NULLS LAST, s.fallback_reason NULLS LAST, "
            f"s.model NULLS LAST"
        )
        with self._connect() as conn:
            rows = conn.execute(sql, (started_from, started_to, *extra)).fetchall()
        return [
            {
                "summarySource": r[0], "fallbackReason": r[1], "model": r[2],
                "summaries": int(r[3]), "promptTokens": int(r[4]),
                "completionTokens": int(r[5]),
            }
            for r in rows
        ]

    @staticmethod
    def _metrics_unavailable(action: str, exc: Exception) -> ScanStoreUnavailableError:
        return ScanStoreUnavailableError(f"{action} for metrics failed: {type(exc).__name__}")

    async def list_runs_for_metrics(
        self, *, started_from: str, started_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._list_runs_for_metrics_sync,
                started_from=started_from, started_to=started_to, warehouses=warehouses,
            )
        except Exception as exc:  # noqa: BLE001
            raise self._metrics_unavailable("list runs", exc) from exc

    async def count_alert_events(
        self, *, created_from: str, created_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._count_alert_events_sync,
                created_from=created_from, created_to=created_to, warehouses=warehouses,
            )
        except Exception as exc:  # noqa: BLE001
            raise self._metrics_unavailable("count alert events", exc) from exc

    async def list_alert_handling(
        self, *, touched_from: str, touched_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._list_alert_handling_sync,
                touched_from=touched_from, touched_to=touched_to, warehouses=warehouses,
            )
        except Exception as exc:  # noqa: BLE001
            raise self._metrics_unavailable("list alert handling", exc) from exc

    async def count_notifications(
        self, *, created_from: str, created_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._count_notifications_sync,
                created_from=created_from, created_to=created_to, warehouses=warehouses,
            )
        except Exception as exc:  # noqa: BLE001
            raise self._metrics_unavailable("count notifications", exc) from exc

    async def aggregate_scan_summaries(
        self, *, started_from: str, started_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._aggregate_scan_summaries_sync,
                started_from=started_from, started_to=started_to, warehouses=warehouses,
            )
        except Exception as exc:  # noqa: BLE001
            raise self._metrics_unavailable("aggregate scan summaries", exc) from exc

    # ---------- 阶段7：保留与归档（每批 limit 行；FOR UPDATE SKIP LOCKED + 同事务提交，可重入） ----------

    @staticmethod
    def _retention_unavailable(action: str, exc: Exception) -> ScanStoreUnavailableError:
        return ScanStoreUnavailableError(f"{action} for retention failed: {type(exc).__name__}")

    def _archive_notifications_before_sync(self, cutoff_iso: str, *, limit: int) -> int:
        with self._connect() as conn:
            doomed = conn.execute(
                f"SELECT notification_id FROM {SCHEMA}.agent_notifications "
                f"WHERE created_at < %s::timestamptz ORDER BY notification_id "
                f"LIMIT %s FOR UPDATE SKIP LOCKED",
                (cutoff_iso, limit),
            ).fetchall()
            ids = [row[0] for row in doomed]
            if not ids:
                return 0
            # 通知是「谁收到、是否已读」的审计证据：先归档再删，不直接丢弃
            conn.execute(
                f"INSERT INTO {SCHEMA}.agent_archive_rows (table_name, row_id, row) "
                f"SELECT %s, n.notification_id::text, to_jsonb(n) "
                f"FROM {SCHEMA}.agent_notifications n WHERE n.notification_id = ANY(%s) "
                f"ON CONFLICT (table_name, row_id) DO NOTHING",
                (ARCHIVE_TABLE_NOTIFICATIONS, ids),
            )
            conn.execute(
                f"DELETE FROM {SCHEMA}.agent_notifications WHERE notification_id = ANY(%s)",
                (ids,),
            )
            return len(ids)

    def _purge_traces_before_sync(self, cutoff_iso: str, *, limit: int) -> int:
        with self._connect() as conn:
            # 问数链路未建 trace 表时没有可清理的数据：按 0 行处理，不让保留任务整体失败
            exists = conn.execute(
                "SELECT to_regclass(%s)", (f"{SCHEMA}.agent_traces",)
            ).fetchone()
            if not exists or exists[0] is None:
                return 0
            # 先子（工具调用）后父（trace）：显式删除，不依赖外键级联定义
            sql = (
                f"WITH doomed AS (SELECT trace_id FROM {SCHEMA}.agent_traces "
                f"WHERE created_at < %s::timestamptz ORDER BY created_at, trace_id "
                f"LIMIT %s FOR UPDATE SKIP LOCKED), "
                f"gone_calls AS (DELETE FROM {SCHEMA}.agent_tool_calls c USING doomed d "
                f"WHERE c.trace_id = d.trace_id RETURNING 1) "
                f"DELETE FROM {SCHEMA}.agent_traces t USING doomed d "
                f"WHERE t.trace_id = d.trace_id"
            )
            cur = conn.execute(sql, (cutoff_iso, limit))
            return max(0, int(cur.rowcount or 0))

    def _archive_settled_alerts_sync(self, cutoff_iso: str, *, limit: int) -> dict[str, int]:
        empty = {"alerts": 0, "events": 0, "notifications": 0}
        with self._connect() as conn:
            # 可归档 = 非活跃，且「最后活动时间」（解决 / 忽略窗口结束 / 最后命中的最大值）早于 cutoff。
            # 选出的行在本事务内持有行锁，直到归档与删除一起提交。
            rows = conn.execute(
                f"SELECT alert_id FROM {SCHEMA}.agent_alerts "
                f"WHERE state NOT IN ('open','acknowledged') AND GREATEST("
                f"COALESCE(resolved_at, '-infinity'::timestamptz), "
                f"COALESCE(ignored_until, '-infinity'::timestamptz), "
                f"COALESCE(last_seen_at, first_seen_at, '-infinity'::timestamptz)) "
                f"< %s::timestamptz ORDER BY alert_id LIMIT %s FOR UPDATE SKIP LOCKED",
                (cutoff_iso, limit),
            ).fetchall()
            ids = [r[0] for r in rows]
            if not ids:
                return empty
            events = conn.execute(
                f"SELECT COUNT(*) FROM {SCHEMA}.agent_alert_events WHERE alert_id = ANY(%s)",
                (ids,),
            ).fetchone()
            cascaded = conn.execute(
                f"SELECT COUNT(*) FROM {SCHEMA}.agent_notifications WHERE alert_id = ANY(%s)",
                (ids,),
            ).fetchone()
            # 先子（事件）后父（告警）；主键冲突说明上一轮已归档、只差删除，直接跳过插入
            conn.execute(
                f"INSERT INTO {SCHEMA}.agent_archive_rows (table_name, row_id, row) "
                f"SELECT %s, e.event_id::text, to_jsonb(e) FROM {SCHEMA}.agent_alert_events e "
                f"WHERE e.alert_id = ANY(%s) ON CONFLICT (table_name, row_id) DO NOTHING",
                (ARCHIVE_TABLE_EVENTS, ids),
            )
            conn.execute(
                f"INSERT INTO {SCHEMA}.agent_archive_rows (table_name, row_id, row) "
                f"SELECT %s, a.alert_id::text, to_jsonb(a) FROM {SCHEMA}.agent_alerts a "
                f"WHERE a.alert_id = ANY(%s) ON CONFLICT (table_name, row_id) DO NOTHING",
                (ARCHIVE_TABLE_ALERTS, ids),
            )
            # 通知随告警离线：同样是审计证据，先归档（主键冲突 = 上一轮已归档，跳过）
            conn.execute(
                f"INSERT INTO {SCHEMA}.agent_archive_rows (table_name, row_id, row) "
                f"SELECT %s, n.notification_id::text, to_jsonb(n) "
                f"FROM {SCHEMA}.agent_notifications n WHERE n.alert_id = ANY(%s) "
                f"ON CONFLICT (table_name, row_id) DO NOTHING",
                (ARCHIVE_TABLE_NOTIFICATIONS, ids),
            )
            conn.execute(
                f"DELETE FROM {SCHEMA}.agent_alert_events WHERE alert_id = ANY(%s)", (ids,)
            )
            # 告警删除时其通知由外键 ON DELETE CASCADE 一并删除（已先归档），计数写进报告
            conn.execute(
                f"DELETE FROM {SCHEMA}.agent_alerts WHERE alert_id = ANY(%s)", (ids,)
            )
            return {
                "alerts": len(ids),
                "events": int(events[0] if events else 0),
                "notifications": int(cascaded[0] if cascaded else 0),
            }

    def _archive_scan_summaries_sync(self, cutoff_iso: str, *, limit: int) -> int:
        with self._connect() as conn:
            # 按所属扫描的完成时间判定（未完成的扫描用开始 / 入队时间兜底）
            rows = conn.execute(
                f"SELECT s.summary_id FROM {SCHEMA}.agent_scan_summaries s "
                f"JOIN {SCHEMA}.agent_scan_runs r ON r.scan_id = s.scan_id "
                f"WHERE COALESCE(r.finished_at, r.started_at, r.queued_at) < %s::timestamptz "
                f"ORDER BY s.summary_id LIMIT %s FOR UPDATE OF s SKIP LOCKED",
                (cutoff_iso, limit),
            ).fetchall()
            ids = [r[0] for r in rows]
            if not ids:
                return 0
            conn.execute(
                f"INSERT INTO {SCHEMA}.agent_archive_rows (table_name, row_id, row) "
                f"SELECT %s, s.summary_id::text, to_jsonb(s) "
                f"FROM {SCHEMA}.agent_scan_summaries s "
                f"WHERE s.summary_id = ANY(%s) ON CONFLICT (table_name, row_id) DO NOTHING",
                (ARCHIVE_TABLE_SUMMARIES, ids),
            )
            conn.execute(
                f"DELETE FROM {SCHEMA}.agent_scan_summaries WHERE summary_id = ANY(%s)", (ids,)
            )
            return len(ids)

    def _get_archived_run_sync(self, scan_id: str) -> dict[str, Any] | None:
        """已归档扫描记录的读回落：只读端点用，形状与线上 ``get_run`` 一致并带 ``archived``。"""
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT row FROM {SCHEMA}.agent_archive_rows "
                f"WHERE table_name = %s AND row_id = %s",
                (ARCHIVE_TABLE_SCAN_RUNS, scan_id),
            ).fetchone()
        if row is None or not isinstance(row[0], dict) or not row[0].get("scan_id"):
            return None
        return run_from_archive(row[0])

    def _archive_scan_evidence_sync(self, cutoff_iso: str, *, limit: int) -> dict[str, int]:
        counts = {
            "scans": 0, "summaries": 0, "evaluatedObjects": 0,
            "observations": 0, "backlogObservations": 0,
        }
        finished = "COALESCE(r.finished_at, r.started_at, r.queued_at)"
        with self._connect() as conn:
            # 只处理终态扫描；选中的行在本事务内持锁，直到子表与父行一起归档、删除并提交
            rows = conn.execute(
                f"SELECT r.scan_id FROM {SCHEMA}.agent_scan_runs r "
                f"WHERE r.status IN ('succeeded','failed','cancelled') AND {finished} < %s::timestamptz "
                f"ORDER BY {finished}, r.scan_id LIMIT %s FOR UPDATE SKIP LOCKED",
                (cutoff_iso, limit),
            ).fetchall()
            ids = [row[0] for row in rows]
            if not ids:
                return counts
            # (表, 归档行号表达式, 行号表达式的参数, 统计键)；行号与 Memory 的 evidence_row_id 一致
            children = (
                (ARCHIVE_TABLE_SUMMARIES, "t.summary_id::text", (), "summaries"),
                (
                    ARCHIVE_TABLE_EVALUATED,
                    "md5(concat_ws(%s, COALESCE(t.scan_id, ''), COALESCE(t.rule_id, ''), "
                    "COALESCE(t.object_id, ''), COALESCE(t.dimension_hash, '')))",
                    (ROW_ID_SEPARATOR,), "evaluatedObjects",
                ),
                (
                    ARCHIVE_TABLE_OBSERVATIONS,
                    "md5(concat_ws(%s, COALESCE(t.scan_id, ''), COALESCE(t.trace_id, ''), "
                    "COALESCE(t.fingerprint, '')))",
                    (ROW_ID_SEPARATOR,), "observations",
                ),
                (ARCHIVE_TABLE_BACKLOG, "t.observation_id::text", (), "backlogObservations"),
            )
            for table, row_id_sql, row_id_params, key in children:
                where = f"t.scan_id = ANY(%s)"
                counts[key] = int(conn.execute(
                    f"SELECT COUNT(*) FROM {SCHEMA}.{table} t WHERE {where}", (ids,),
                ).fetchone()[0])
                conn.execute(
                    f"INSERT INTO {SCHEMA}.agent_archive_rows (table_name, row_id, row) "
                    f"SELECT %s, {row_id_sql}, to_jsonb(t) FROM {SCHEMA}.{table} t "
                    f"WHERE {where} ON CONFLICT (table_name, row_id) DO NOTHING",
                    (table, *row_id_params, ids),
                )
                conn.execute(f"DELETE FROM {SCHEMA}.{table} t WHERE {where}", (ids,))
            # 父行最后：先归档再删；状态条件再写一次，避免把刚被改回在途的记录删掉
            terminal = "('succeeded','failed','cancelled')"
            conn.execute(
                f"INSERT INTO {SCHEMA}.agent_archive_rows (table_name, row_id, row) "
                f"SELECT %s, r.scan_id, to_jsonb(r) FROM {SCHEMA}.agent_scan_runs r "
                f"WHERE r.scan_id = ANY(%s) AND r.status IN {terminal} "
                f"ON CONFLICT (table_name, row_id) DO NOTHING",
                (ARCHIVE_TABLE_SCAN_RUNS, ids),
            )
            conn.execute(
                f"DELETE FROM {SCHEMA}.agent_scan_runs r WHERE r.scan_id = ANY(%s) "
                f"AND r.status IN {terminal}",
                (ids,),
            )
            counts["scans"] = len(ids)
            return counts

    def _purge_archive_before_sync(self, cutoff_iso: str, *, limit: int) -> dict[str, int]:
        counts = {key: 0 for key in ARCHIVE_TABLE_KEYS.values()}
        with self._connect() as conn:
            for table in ARCHIVE_TABLES:  # 先子后父
                cur = conn.execute(
                    f"WITH doomed AS (SELECT ctid FROM {SCHEMA}.agent_archive_rows "
                    f"WHERE table_name = %s AND archived_at < %s::timestamptz "
                    f"ORDER BY archived_at LIMIT %s FOR UPDATE SKIP LOCKED) "
                    f"DELETE FROM {SCHEMA}.agent_archive_rows a USING doomed d "
                    f"WHERE a.ctid = d.ctid",
                    (table, cutoff_iso, limit),
                )
                counts[ARCHIVE_TABLE_KEYS[table]] = max(0, int(cur.rowcount or 0))
        return counts

    async def archive_notifications_before(self, cutoff_iso: str, *, limit: int) -> int:
        try:
            return await asyncio.to_thread(
                self._archive_notifications_before_sync, cutoff_iso, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            raise self._retention_unavailable("archive notifications", exc) from exc

    async def purge_traces_before(self, cutoff_iso: str, *, limit: int) -> int:
        try:
            return await asyncio.to_thread(
                self._purge_traces_before_sync, cutoff_iso, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            raise self._retention_unavailable("purge traces", exc) from exc

    async def archive_settled_alerts(
        self, cutoff_iso: str, *, limit: int,
    ) -> dict[str, int]:
        try:
            return await asyncio.to_thread(
                self._archive_settled_alerts_sync, cutoff_iso, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            raise self._retention_unavailable("archive settled alerts", exc) from exc

    async def archive_scan_summaries(self, cutoff_iso: str, *, limit: int) -> int:
        try:
            return await asyncio.to_thread(
                self._archive_scan_summaries_sync, cutoff_iso, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            raise self._retention_unavailable("archive scan summaries", exc) from exc

    async def purge_archive_before(
        self, cutoff_iso: str, *, limit: int,
    ) -> dict[str, int]:
        try:
            return await asyncio.to_thread(
                self._purge_archive_before_sync, cutoff_iso, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            raise self._retention_unavailable("purge archive", exc) from exc

    async def archive_scan_evidence(
        self, cutoff_iso: str, *, limit: int,
    ) -> dict[str, int]:
        try:
            return await asyncio.to_thread(
                self._archive_scan_evidence_sync, cutoff_iso, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            raise self._retention_unavailable("archive scan evidence", exc) from exc

    async def get_archived_run(self, scan_id: str) -> dict[str, Any] | None:
        try:
            return await asyncio.to_thread(self._get_archived_run_sync, scan_id)
        except Exception as exc:  # noqa: BLE001
            raise self._metrics_unavailable("get archived run", exc) from exc

    def _save_metric_daily_sync(self, rows: list[dict[str, Any]]) -> int:
        written = 0
        with self._connect() as conn:
            for row in rows:
                cur = conn.execute(
                    f"INSERT INTO {SCHEMA}.agent_metric_daily "
                    f"(metric_date, warehouse, timezone, metrics) "
                    f"VALUES (%s::date, %s, %s, %s::jsonb) "
                    f"ON CONFLICT (metric_date, warehouse) DO UPDATE SET "
                    f"timezone = EXCLUDED.timezone, metrics = EXCLUDED.metrics, updated_at = now()",
                    (
                        str(row.get("metricDate")), row.get("warehouse"),
                        row.get("timezone") or "Asia/Shanghai",
                        json.dumps(row.get("metrics") or {}, ensure_ascii=False),
                    ),
                )
                written += max(0, int(cur.rowcount or 0))
        return written

    def _list_metric_daily_sync(
        self, *, date_from: str, date_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        clause, params = self._metrics_filters(warehouses, "warehouse")
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT metric_date, warehouse, timezone, metrics::text, updated_at "
                f"FROM {SCHEMA}.agent_metric_daily "
                f"WHERE metric_date >= %s::date AND metric_date < %s::date{clause} "
                f"ORDER BY metric_date, warehouse",
                (date_from, date_to, *params),
            ).fetchall()
        return [
            {
                "metricDate": row[0].isoformat(), "warehouse": row[1],
                "timezone": row[2], "metrics": _safe_json(row[3]),
                "updatedAt": row[4].isoformat() if row[4] is not None else None,
            }
            for row in rows
        ]

    def _purge_metric_daily_before_sync(self, cutoff_date: str, *, limit: int) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                f"WITH doomed AS (SELECT metric_date, warehouse FROM {SCHEMA}.agent_metric_daily "
                f"WHERE metric_date < %s::date ORDER BY metric_date LIMIT %s FOR UPDATE SKIP LOCKED) "
                f"DELETE FROM {SCHEMA}.agent_metric_daily d USING doomed x "
                f"WHERE d.metric_date = x.metric_date AND d.warehouse = x.warehouse",
                (cutoff_date, limit),
            )
            return max(0, int(cur.rowcount or 0))

    async def save_metric_daily(self, rows: list[dict[str, Any]]) -> int:
        try:
            return await asyncio.to_thread(self._save_metric_daily_sync, rows)
        except Exception as exc:  # noqa: BLE001
            raise self._metrics_unavailable("save metric daily", exc) from exc

    async def list_metric_daily(
        self, *, date_from: str, date_to: str, warehouses: list[str] | None,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._list_metric_daily_sync,
                date_from=date_from, date_to=date_to, warehouses=warehouses,
            )
        except Exception as exc:  # noqa: BLE001
            raise self._metrics_unavailable("list metric daily", exc) from exc

    async def purge_metric_daily_before(self, cutoff_date: str, *, limit: int) -> int:
        try:
            return await asyncio.to_thread(
                self._purge_metric_daily_before_sync, cutoff_date, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            raise self._retention_unavailable("purge metric daily", exc) from exc

    def _list_auto_resolve_candidates_sync(
        self, *, warehouse: str, rule_ids: list[str], before_iso: str, limit: int = 200,
    ) -> list[dict[str, Any]]:
        sql = (
            f"SELECT a.alert_id, a.fingerprint, a.rule_id, a.rule_version, a.object_id, "
            f"a.state, a.last_seen_at, a.warehouse_id FROM {SCHEMA}.agent_alerts a "
            f"WHERE a.state IN ('open','acknowledged') AND a.warehouse_id = %s "
            f"AND a.last_seen_at < %s"
        )
        params: list[Any] = [warehouse, before_iso]
        if rule_ids:
            sql += f" AND a.rule_id IN ({','.join(['%s'] * len(rule_ids))})"
            params.extend(rule_ids)
        sql += (
            " AND (a.rule_id <> 'SCAN-PARTIAL' OR EXISTS ("
            f"SELECT 1 FROM {SCHEMA}.agent_scan_runs r "
            "WHERE r.scan_id = a.scan_id "
            "AND r.status IN ('succeeded','failed','cancelled') "
            "AND r.finished_at < %s))"
        )
        params.append(before_iso)
        sql += " ORDER BY a.alert_id LIMIT %s"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [
            {
                "alertId": r[0], "fingerprint": r[1], "ruleId": r[2],
                "ruleVersion": r[3], "objectId": r[4],
                "state": r[5],
                "lastSeenAt": r[6].isoformat() if r[6] is not None else None,
                "warehouseId": r[7],
            }
            for r in rows
        ]

    async def list_auto_resolve_candidates(
        self, *, warehouse: str, rule_ids: list[str], before_iso: str, limit: int = 200,
    ) -> list[dict[str, Any]]:
        try:
            return await asyncio.to_thread(
                self._list_auto_resolve_candidates_sync, warehouse=warehouse,
                rule_ids=rule_ids, before_iso=before_iso, limit=limit,
            )
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(
                f"list auto resolve candidates failed: {type(exc).__name__}"
            ) from exc

    def _auto_resolve_alert_sync(
        self, alert_id: int, *, reason: str, scan_id: str, trace_id: str,
        before_iso: str, rule_id: str, rule_version: str, warehouse: str,
    ) -> bool:
        """条件 UPDATE + 同事务写事件；任一条件不符返回 False（不写任何行）。

        事件的 from_state 必须是关闭前的真实状态（open / acknowledged）。``UPDATE … RETURNING``
        只看得到新值（真实 e2e 捕获：事件被写成 resolved→resolved），因此先用带 ``FOR UPDATE``
        的 CTE 在同一快照内锁定并读出旧行，再于同一语句内更新：锁保证并发下读-改-判原子，
        CTE 与主语句共用同一快照，读到的仍是更新前的行。
        """
        with self._connect() as conn:
            cur = conn.execute(
                f"""
                WITH prev AS (
                    SELECT a.alert_id, a.state, a.severity
                    FROM {SCHEMA}.agent_alerts a
                    WHERE a.alert_id = %s
                      AND a.state IN ('open','acknowledged')
                      AND a.rule_id = %s AND a.rule_version = %s
                      AND a.warehouse_id = %s
                      AND a.last_seen_at < %s
                      AND (
                        %s <> 'SCAN-PARTIAL'
                        OR EXISTS (
                            SELECT 1 FROM {SCHEMA}.agent_scan_runs r
                            WHERE r.scan_id = a.scan_id
                              AND r.status IN ('succeeded','failed','cancelled')
                              AND r.finished_at < %s
                        )
                      )
                    FOR UPDATE OF a
                )
                UPDATE {SCHEMA}.agent_alerts a
                SET state = 'resolved', resolved_at = now(), resolved_reason = %s
                FROM prev
                WHERE a.alert_id = prev.alert_id
                RETURNING prev.state, prev.severity, a.severity
                """,
                (
                    alert_id, rule_id, rule_version, warehouse, before_iso,
                    rule_id, before_iso, reason,
                ),
            )
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                return False
            self._insert_event_sync(
                conn, alert_id, AUTO_RESOLVE_EVENT, row[0], "resolved",
                row[1], row[2], reason, trace_id, scan_id, actor_type="system",
            )
            conn.commit()
            return True

    async def auto_resolve_alert(
        self, alert_id: int, *, reason: str, scan_id: str, trace_id: str,
        before_iso: str, rule_id: str, rule_version: str, warehouse: str,
    ) -> bool:
        try:
            return await asyncio.to_thread(
                self._auto_resolve_alert_sync, alert_id, reason=reason, scan_id=scan_id,
                trace_id=trace_id, before_iso=before_iso, rule_id=rule_id,
                rule_version=rule_version, warehouse=warehouse,
            )
        except Exception as exc:  # noqa: BLE001
            raise ScanStoreUnavailableError(
                f"auto resolve alert failed: {type(exc).__name__}"
            ) from exc


def _run_params(run: dict[str, Any]) -> tuple[Any, ...]:
    """按 RUN_COLUMNS 顺序生成参数；列顺序与 RUN_INSERT_SQL 严格对应。"""
    return (
        run.get("scanId"), run.get("trigger"), run.get("actorType"), run.get("actorId"),
        run.get("status"), bool(run.get("partial", False)),
        _json(run.get("sourceStatus") or []), run.get("configHash"), run.get("ruleVersion"),
        _scan_types_key(run.get("scanTypes") or []), run.get("requestId"),
        run.get("scheduleSlot"), run.get("scanKey"), run.get("queuedAt"),
        run.get("startedAt"), run.get("finishedAt"), _json(run.get("counts") or {}),
        run.get("errorSummary"), run.get("warehouse"), bool(run.get("dryRun", False)),
        run.get("notificationMode"), run.get("payloadHash"), run.get("traceId"),
        int(run.get("attempt") or 0), run.get("leaseOwner"), run.get("leasedAt"),
        run.get("executorType"), run.get("executorId"), run.get("actorUserId"),
        run.get("configSnapshot"), run.get("configVersion"),
        run.get("retryOfScanId"), run.get("originActorType"),
        run.get("originActorId"), run.get("originTrigger"),
    )


def _fenced_params(run: dict[str, Any], lease_owner: str) -> dict[str, Any]:
    """fencing UPDATE 的命名参数：只含执行阶段可写字段 + 租约条件。"""
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "status": run.get("status"),
        "partial": bool(run.get("partial", False)),
        "sourceStatus": _json(run.get("sourceStatus") or []),
        "ruleVersion": run.get("ruleVersion"),
        "startedAt": run.get("startedAt") or now_iso,
        "finishedAt": run.get("finishedAt"),
        "counts": _json(run.get("counts") or {}),
        "errorSummary": run.get("errorSummary"),
        "warehouse": run.get("warehouse"),
        "dryRun": bool(run.get("dryRun", False)),
        "notificationMode": run.get("notificationMode"),
        "payloadHash": run.get("payloadHash"),
        "traceId": run.get("traceId"),
        "executorType": run.get("executorType"),
        "executorId": run.get("executorId"),
        "scanId": run.get("scanId"),
        "leaseOwner": lease_owner,
    }


def _row_to_run(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(zip(RUN_COLUMNS, row))
    return {
        "scanId": data["scan_id"], "trigger": data["trigger"],
        "actorType": data["actor_type"], "actorId": data["actor_id"],
        "status": data["status"], "partial": data["partial"],
        "sourceStatus": json.loads(data["source_status"] or "[]"),
        "configHash": data["config_hash"], "ruleVersion": data["rule_version"],
        "scanTypes": (data["scan_types"] or "").split(",") if data["scan_types"] else [],
        "requestId": data["request_id"], "scheduleSlot": data["schedule_slot"],
        "scanKey": data["scan_key"],
        "queuedAt": data["queued_at"].isoformat() if data["queued_at"] else None,
        "startedAt": data["started_at"].isoformat() if data["started_at"] else None,
        "finishedAt": data["finished_at"].isoformat() if data["finished_at"] else None,
        "counts": json.loads(data["counts"] or "{}"), "errorSummary": data["error_summary"],
        "warehouse": data["warehouse"], "dryRun": data["dry_run"],
        "notificationMode": data["notification_mode"],
        "payloadHash": data["payload_hash"], "traceId": data["trace_id"],
        "attempt": data["attempt"], "leaseOwner": data["lease_owner"],
        "leasedAt": data["leased_at"].isoformat() if data["leased_at"] else None,
        "executorType": data["executor_type"], "executorId": data["executor_id"],
        "actorUserId": data["actor_user_id"],
        "configSnapshot": data["config_snapshot"],
        "configVersion": data["config_version"],
        "retryOfScanId": data["retry_of_scan_id"],
        "originActorType": data["origin_actor_type"],
        "originActorId": data["origin_actor_id"],
        "originTrigger": data["origin_trigger"],
    }


def run_from_archive(data: dict[str, Any]) -> dict[str, Any]:
    """归档扫描记录（``to_jsonb`` 快照，snake_case 列名）→ 与线上 ``get_run`` 同一形状。

    统一走 ``_row_to_run``：先把快照还原成与线上一致的行（JSON 列转回文本、时间转回
    datetime），保证归档读回与线上读回不会出现两套字段定义。归档行带 ``archived=True``。
    """
    if "scan_id" not in data:  # Memory 归档里存的就是接口形状
        return {**data, "archived": True}
    values: list[Any] = []
    for column in RUN_COLUMNS:
        value = data.get(column)
        if column in ("source_status", "counts") and isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        elif column in ("queued_at", "started_at", "finished_at", "leased_at"):
            value = _parse_iso(value) if isinstance(value, str) else value
        values.append(value)
    return {**_row_to_run(tuple(values)), "archived": True}


def _safe_json(value: Any) -> Any:
    """JSON 字段容错解析：坏数据不当场炸掉整个列表。"""
    if value is None or value == "":
        return {}
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return {}


def _row_to_alert(r: Any) -> dict[str, Any]:
    return {
        "alertId": r[0], "fingerprint": r[1], "ruleId": r[2], "severity": r[3],
        "objectType": r[4], "objectId": r[5], "dimension": json.loads(r[6] or "{}"),
        "title": r[7], "state": r[8], "assignee": r[9], "warehouseId": r[10],
        "occurrenceCount": r[11], "firstSeenAt": r[12].isoformat() if r[12] else None,
        "lastSeenAt": r[13].isoformat() if r[13] else None, "scanId": r[14],
        "traceId": r[15], "ruleDegraded": r[16], "firstSeverity": r[17],
        "acknowledgedBy": r[18],
        "acknowledgedAt": r[19].isoformat() if r[19] else None,
        "assigneeUserId": r[20],
        "claimedAt": r[21].isoformat() if r[21] else None,
        "routedTo": r[22],
        "resolvedAt": r[23].isoformat() if r[23] else None,
        "resolvedReason": r[24],
        "ignoredUntil": r[25].isoformat() if r[25] else None,
        "ruleVersion": r[26],
    }


def _row_to_event(r: Any) -> dict[str, Any]:
    """事件行 → dict（列顺序与 _EVENT_COLUMNS 一致）。"""
    return {
        "eventId": r[0], "alertId": r[1], "actorType": r[2], "actorId": r[3],
        "fromState": r[4], "toState": r[5], "reason": r[6], "traceId": r[7],
        "createdAt": r[8].isoformat() if r[8] else None,
        "eventType": r[9], "fromSeverity": r[10], "toSeverity": r[11],
    }


def _row_to_notification(r: Any) -> dict[str, Any]:
    """通知行 → dict（列顺序与 _NOTIFICATION_COLUMNS 一致）。"""
    return {
        "notificationId": r[0], "alertId": r[1], "channel": r[2], "recipient": r[3],
        "recipientUserId": r[4], "status": r[5], "payloadDigest": r[6],
        "providerMessageId": r[7],
        "createdAt": r[8].isoformat() if r[8] else None,
        "sentAt": r[9].isoformat() if r[9] else None,
        "readAt": r[10].isoformat() if r[10] else None,
    }


def build_scan_store(backend: str, db_url: str) -> ScanStore:
    """显式选择后端：postgres 故障不降级；未知后端一律拒绝启动。"""
    if backend == "postgres":
        if not db_url:
            raise ScanStoreUnavailableError("postgres backend requires WMS_AGENT_DB_URL")
        return PostgresScanStore(db_url)
    if backend == "memory":
        return MemoryScanStore()
    raise ScanStoreUnavailableError(f"unknown scan store backend: {backend}")
