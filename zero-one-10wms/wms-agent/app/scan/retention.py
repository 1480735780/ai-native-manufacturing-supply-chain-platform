"""保留与归档（ADR-020）：按固定顺序、限批、可重入地清理巡检数据。

只做下面几件事，且顺序固定（先子后父，外键安全）：

1. 通知：创建时间早于 cutoff 的写入归档表后删除线上行。通知是「谁收到、是否已读」的审计
   证据，不直接删除；它引用告警，所以最先处理。
2. 问数 trace 与 tool_calls：trace 创建时间早于 cutoff 的直接删除（不归档，技术日志）；
   存储层先删工具调用再删 trace，不依赖外键级联定义。
3. 已结案告警：非活跃、且「最后活动时间」早于在线期 cutoff → 事件、通知、告警写入归档表后
   删除线上行（同一事务）。
4. 扫描摘要：所属扫描的完成时间早于在线期 cutoff → 写入归档表后删除线上行。
5. 扫描证据：终态且完成时间早于在线期 cutoff 的扫描，连同它的摘要、评估覆盖、命中观测、
   积压样本一起归档后删除（``queued`` / ``running`` 永不归档）。
6. 指标日聚合：``metric_date`` 早于 ``now - metrics_days`` 的行删除。
7. 归档保留期：``archived_at`` 早于归档期 cutoff 的归档行删除（先子后父）。

每一类每轮最多 ``max_batches`` 批、每批 ``batch_size`` 行。存储层每批独立提交，所以中途
失败时已完成的批次保持有效，下一轮从剩余行继续；归档表主键保证重跑不产生重复行。

指标日聚合由 ``RetentionScheduler`` 在保留任务**之前**补算（先聚合再归档，历史指标不随线上行
消失）；手动触发本模块的保留轮次不强制先聚合，由管理员自行决定。
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import datetime, time as dtime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.scan.metrics_rollup import RollupError, run_metric_rollup

if TYPE_CHECKING:  # 仅类型标注，运行时不产生循环导入
    from app.scan.repository import ScanStore

logger = logging.getLogger(__name__)

DEFAULT_ALERTS_ONLINE_DAYS = 180
DEFAULT_ALERTS_ARCHIVE_DAYS = 365
DEFAULT_NOTIFICATIONS_DAYS = 90
DEFAULT_TRACE_DAYS = 90
DEFAULT_METRICS_DAYS = 730
DEFAULT_BATCH_SIZE = 500
DEFAULT_MAX_BATCHES = 20
# 调度器补齐日聚合的最多轮数：每轮限批，轮询到 remaining == 0 为止；仍补不齐则本轮不归档
DEFAULT_ROLLUP_ROUNDS = 10

_STEP_NOTIFICATIONS = "notifications"
_STEP_TRACES = "traces"
_STEP_ALERTS = "alerts"
_STEP_SUMMARIES = "summaries"
_STEP_SCAN_EVIDENCE = "scanEvidence"
_STEP_METRIC_DAILY = "metricDaily"
_STEP_ARCHIVE = "archive"

# 子表计数键 → 报告里的归档总数键
_EVIDENCE_TOTAL_KEYS = {
    "summaries": "summariesArchived",
    "evaluatedObjects": "evaluatedObjectsArchived",
    "observations": "observationsArchived",
    "backlogObservations": "backlogObservationsArchived",
    "scans": "scansArchived",
}


class RetentionError(ValueError):
    """保留策略非法：拒绝执行，不带着会误删数据的参数运行。"""


@dataclass(frozen=True)
class RetentionPolicy:
    """保留期（天）。在线期与归档期都从各自的时间基准起算，最小 1 天，防止误配成 0 清空全表。

    ``alerts_online_days`` 同时是扫描证据的在线期：告警与产生它的扫描证据口径一致。
    """

    alerts_online_days: int = DEFAULT_ALERTS_ONLINE_DAYS
    alerts_archive_days: int = DEFAULT_ALERTS_ARCHIVE_DAYS
    notifications_days: int = DEFAULT_NOTIFICATIONS_DAYS
    trace_days: int = DEFAULT_TRACE_DAYS
    metrics_days: int = DEFAULT_METRICS_DAYS

    @classmethod
    def from_settings(cls, settings: Any) -> RetentionPolicy:
        return cls(
            alerts_online_days=int(settings.retention_alerts_online_days),
            alerts_archive_days=int(settings.retention_alerts_archive_days),
            notifications_days=int(settings.retention_notifications_days),
            trace_days=int(settings.retention_trace_days),
            metrics_days=int(getattr(settings, "retention_metrics_days", DEFAULT_METRICS_DAYS)),
        )

    def validate(self) -> None:
        problems: list[str] = []
        for name in (
            "alerts_online_days", "alerts_archive_days",
            "notifications_days", "trace_days", "metrics_days",
        ):
            value = int(getattr(self, name))
            if value < 1:
                problems.append(f"{name} 必须 ≥ 1，当前 {value}")
        if problems:
            raise RetentionError("保留策略非法：" + "；".join(problems))

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


def parse_daily_at(value: str) -> dtime:
    """每日执行时刻 ``HH:MM``（本地时区）。"""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", str(value or "").strip())
    if match is None:
        raise RetentionError(f"retention_daily_at 必须是 HH:MM，当前: {value!r}")
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        raise RetentionError(f"retention_daily_at 超出范围，当前: {value}")
    return dtime(hour, minute)


def _cutoff(moment: datetime, days: int) -> str:
    return (moment - timedelta(days=int(days))).isoformat()


def _batches(value: Any) -> tuple[int, int, bool]:
    return int(value.get("batches") or 0), int(value.get("rows") or 0), bool(value.get("moreRemaining"))


async def _drain(
    action: Callable[[], Awaitable[int]], *, limit: int, max_batches: int,
) -> tuple[int, int, bool]:
    """反复执行单批动作直到某一批不满（说明已清空）或达到批数上限。

    返回 ``(累计行数, 批数, 是否可能还有剩余)``。最后一批是满的就认为可能还有剩余：
    宁可多报一轮空跑，也不漏报。
    """
    total = 0
    batches = 0
    for _ in range(max_batches):
        rows = int(await action())
        total += rows
        batches += 1
        if rows < limit:
            return total, batches, False
    return total, batches, True


async def run_retention(
    store: ScanStore,
    *,
    policy: RetentionPolicy,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_batches: int = DEFAULT_MAX_BATCHES,
    now: datetime | None = None,
) -> dict[str, Any]:
    """执行一轮保留与归档，返回可核对的报告；任一批失败立即抛出（已提交的批次不回滚）。"""
    policy.validate()
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise RetentionError("now 必须带时区")
    limit = max(1, int(batch_size))
    allowed = max(1, int(max_batches))
    cutoffs = {
        "notifications": _cutoff(moment, policy.notifications_days),
        "traces": _cutoff(moment, policy.trace_days),
        "alertsOnline": _cutoff(moment, policy.alerts_online_days),
        "metricDaily": (moment - timedelta(days=policy.metrics_days)).date().isoformat(),
        "archive": _cutoff(moment, policy.alerts_archive_days),
    }
    steps: list[dict[str, Any]] = []

    # 1. 通知（引用告警；先归档再删，审计证据不直接丢弃）
    rows, batches, more = await _drain(
        lambda: store.archive_notifications_before(cutoffs["notifications"], limit=limit),
        limit=limit, max_batches=allowed,
    )
    steps.append({
        "step": _STEP_NOTIFICATIONS, "action": "archive", "rows": rows,
        "batches": batches, "moreRemaining": more,
    })

    # 2. 问数 trace 与 tool_calls（存储层先子后父）
    rows, batches, more = await _drain(
        lambda: store.purge_traces_before(cutoffs["traces"], limit=limit),
        limit=limit, max_batches=allowed,
    )
    traces_deleted = rows
    steps.append({
        "step": _STEP_TRACES, "action": "purge", "rows": rows,
        "batches": batches, "moreRemaining": more,
    })

    # 3. 已结案告警（先事件与通知、后告警；同一事务内归档 + 删除）
    alerts = events = cascaded = batches = 0
    more = False
    for _ in range(allowed):
        result = await store.archive_settled_alerts(cutoffs["alertsOnline"], limit=limit)
        taken = int(result.get("alerts") or 0)
        alerts += taken
        events += int(result.get("events") or 0)
        cascaded += int(result.get("notifications") or 0)
        batches += 1
        if taken < limit:
            break
    else:
        more = True
    steps.append({
        "step": _STEP_ALERTS, "action": "archive", "rows": alerts, "events": events,
        "notificationsArchivedWithAlerts": cascaded,
        "batches": batches, "moreRemaining": more,
    })

    # 4. 扫描摘要（按所属扫描的完成时间；与第 5 步口径一致，先单独成步便于核对）
    rows, batches, more = await _drain(
        lambda: store.archive_scan_summaries(cutoffs["alertsOnline"], limit=limit),
        limit=limit, max_batches=allowed,
    )
    summaries = rows
    steps.append({
        "step": _STEP_SUMMARIES, "action": "archive", "rows": rows,
        "batches": batches, "moreRemaining": more,
    })

    # 5. 扫描证据（终态扫描连同子表整批归档；queued / running 永不处理）
    evidence = {"scans": 0, "summaries": 0, "evaluatedObjects": 0, "observations": 0, "backlogObservations": 0}
    batches = 0
    more = False
    for _ in range(allowed):
        counts = await store.archive_scan_evidence(cutoffs["alertsOnline"], limit=limit)
        for key in evidence:
            evidence[key] += int(counts.get(key) or 0)
        batches += 1
        if int(counts.get("scans") or 0) < limit:
            break
    else:
        more = True
    steps.append({
        "step": _STEP_SCAN_EVIDENCE, "action": "archive", "rows": evidence["scans"],
        **{key: value for key, value in evidence.items() if key != "scans"},
        "batches": batches, "moreRemaining": more,
    })

    # 6. 指标日聚合（超过 2 年在线期的行删除）
    rows, batches, more = await _drain(
        lambda: store.purge_metric_daily_before(cutoffs["metricDaily"], limit=limit),
        limit=limit, max_batches=allowed,
    )
    metric_rows = rows
    steps.append({
        "step": _STEP_METRIC_DAILY, "action": "purge", "rows": rows,
        "batches": batches, "moreRemaining": more,
    })

    # 7. 超过归档期的归档行（存储层按先子后父的顺序逐表清理）
    purged = {"events": 0, "alerts": 0, "summaries": 0}
    batches = 0
    more = False
    for _ in range(allowed):
        counts = await store.purge_archive_before(cutoffs["archive"], limit=limit)
        batches += 1
        saturated = False
        for key, taken in counts.items():
            taken = int(taken or 0)
            purged[key] = purged.get(key, 0) + taken
            saturated = saturated or taken >= limit
        if not saturated:
            break
    else:
        more = True
    archive_purged = sum(purged.values())
    steps.append({
        "step": _STEP_ARCHIVE, "action": "purge", "rows": archive_purged,
        **purged, "batches": batches, "moreRemaining": more,
    })

    report: dict[str, Any] = {
        "startedAt": moment.isoformat(),
        "finishedAt": datetime.now(timezone.utc).isoformat(),
        "policy": policy.as_dict(),
        "cutoffs": cutoffs,
        "batchSize": limit,
        "maxBatches": allowed,
        "steps": steps,
        "totals": {
            "notificationsArchived": steps[0]["rows"],
            "tracesDeleted": traces_deleted,
            "alertsArchived": alerts,
            "eventsArchived": events,
            "notificationsArchivedWithAlerts": cascaded,
            "summariesArchived": summaries + evidence["summaries"],
            "scansArchived": evidence["scans"],
            "evaluatedObjectsArchived": evidence["evaluatedObjects"],
            "observationsArchived": evidence["observations"],
            "backlogObservationsArchived": evidence["backlogObservations"],
            "metricRowsPurged": metric_rows,
            "archiveRowsPurged": archive_purged,
        },
        "moreRemaining": any(bool(step["moreRemaining"]) for step in steps),
    }
    logger.info(
        "retention run finished: alerts=%s events=%s summaries=%s scans=%s notifications=%s traces=%s "
        "archivePurged=%s moreRemaining=%s",
        alerts, events, report["totals"]["summariesArchived"], evidence["scans"], steps[0]["rows"],
        traces_deleted, archive_purged, report["moreRemaining"],
    )
    return report


class RetentionScheduler:
    """随应用 lifespan 启停的每日保留任务。

    到了 ``retention_daily_at``（``retention_timezone``）之后跑一次，同一天不重复。
    每次先补齐指标日聚合（先聚合再归档，历史指标不随线上行消失），补不齐则本轮不归档。
    当天失败也等到第二天再试：这是删除类任务，不做分钟级重试；管理员可随时手动触发。
    ``retention_enabled=false``（默认）时不启动。
    """

    TICK_SECONDS = 60.0

    def __init__(
        self,
        store: ScanStore,
        settings: Any,
        *,
        tick_seconds: float = TICK_SECONDS,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._settings = settings
        self._tick_seconds = tick_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._last_run_day: str | None = None
        self._last_report: dict[str, Any] | None = None
        self._last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(getattr(self._settings, "retention_enabled", False))

    @property
    def last_run_day(self) -> str | None:
        return self._last_run_day

    @property
    def last_report(self) -> dict[str, Any] | None:
        return self._last_report

    @property
    def last_error(self) -> str | None:
        return self._last_error

    async def start(self) -> None:
        if not self.enabled:
            logger.info("保留与归档任务未启用（retention_enabled=false）")
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._loop(), name="scan-retention")
        logger.info(
            "保留与归档任务已启动：daily_at=%s timezone=%s",
            getattr(self._settings, "retention_daily_at", ""),
            getattr(self._settings, "retention_timezone", ""),
        )

    async def stop(self) -> None:
        self._stopping.set()
        task = self._task
        self._task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001 - 关闭期吞掉异常
                pass

    async def _loop(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.tick()
            except Exception as exc:  # noqa: BLE001 - 失败只记日志，第二天再试
                self._last_error = f"{type(exc).__name__}: {exc}"
                logger.warning("retention run failed: %s", self._last_error)
            await asyncio.sleep(self._tick_seconds)

    async def _rollup(self, moment: datetime) -> dict[str, Any] | None:
        """补齐日聚合；没有配置仓库时无事可做。补不齐则抛错，由调用方决定是否归档。"""
        warehouses = [str(item) for item in (getattr(self._settings, "scan_warehouses", None) or []) if item]
        if not warehouses:
            return None
        for _ in range(DEFAULT_ROLLUP_ROUNDS):
            rollup = await run_metric_rollup(
                self._store, warehouses=warehouses, now=moment,
                timezone=str(getattr(self._settings, "retention_timezone", "")),
            )
            if int(rollup.get("remaining") or 0) == 0:
                return rollup
        raise RetentionError(
            f"指标日聚合尚未补齐（remaining={rollup.get('remaining')}），本轮不执行保留与归档"
        )

    async def tick(self, now: datetime | None = None) -> dict[str, Any] | None:
        """到点则执行一轮并返回报告；未启用、未到点或今天已跑过都返回 None。"""
        if not self.enabled:
            return None
        moment = now or self._clock()
        try:
            zone = ZoneInfo(str(getattr(self._settings, "retention_timezone", "")))
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise RetentionError(f"retention_timezone 非法: {exc}") from exc
        local = moment.astimezone(zone)
        due = parse_daily_at(str(getattr(self._settings, "retention_daily_at", "")))
        day_key = local.strftime("%Y%m%d")
        target = local.replace(hour=due.hour, minute=due.minute, second=0, microsecond=0)
        if local < target or self._last_run_day == day_key:
            return None
        # 先占位再执行：失败也等到明天，避免每个 tick 重试删除类任务
        self._last_run_day = day_key
        try:
            rollup = await self._rollup(moment)
        except RollupError as exc:
            raise RetentionError(str(exc)) from exc
        report = await run_retention(
            self._store,
            policy=RetentionPolicy.from_settings(self._settings),
            batch_size=int(getattr(self._settings, "retention_batch_size", DEFAULT_BATCH_SIZE)),
            max_batches=int(getattr(self._settings, "retention_max_batches", DEFAULT_MAX_BATCHES)),
            now=moment,
        )
        report["rollup"] = rollup
        self._last_report = report
        self._last_error = None
        return report
