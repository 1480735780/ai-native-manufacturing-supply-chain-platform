"""最小内部调度器（阶段5）。

职责只有一个：在配置的每日窗口内，按固定步长为“当前槽位”入队一次巡检。

刻意不做的事：
- 不引入通用 cron 框架（只支持 ``*/N H-M * * *``，避免长期维护表达式子语言）；
- 不补跑错过的槽位（服务在 14:37 启动，就不会补 14:30 的槽）；
- 不做扫描逻辑判断（取数、判定、落库仍由 worker 按队列快照执行）；
- 不在调度里存任何密钥或令牌。

去重靠两层：进程内记住最近一次槽位；跨进程/重启靠
``agent_scan_runs`` 的 ``uq_scan_runs_schedule(schedule_slot, config_hash, scan_types)``
唯一索引——同一槽位重复触发只会保留一条扫描。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

from app.scan.config import LoadedScanConfig, parse_scan_cron
from app.scan.repository import ScanStore
from app.scan.service import enqueue_scan
from app.security import Principal

logger = logging.getLogger(__name__)

# 轮询间隔：15 秒，足以在槽位分钟内命中一次边界。
TICK_SECONDS = 15


@dataclass(frozen=True)
class ScheduleSlot:
    """一个调度槽位（按调度时区命名，例：20261125T1430）。"""

    slot_id: str
    moment: datetime


def current_slot(
    now: datetime, timezone_name: str, cron_expression: str,
) -> ScheduleSlot | None:
    """返回 now 所在的槽位；不在窗口内或不在槽位分钟上返回 None。

    槽位分钟必须整除步长（``*/15`` → 00/15/30/45），窗口是闭区间 ``[H, M]``。
    """
    cron = parse_scan_cron(cron_expression)
    local = now.astimezone(ZoneInfo(timezone_name))
    if not (cron.hour_start <= local.hour <= cron.hour_end):
        return None
    if local.minute % cron.minute_step != 0:
        return None
    return ScheduleSlot(slot_id=local.strftime("%Y%m%dT%H%M"), moment=local)


class ScanScheduler:
    """随应用 lifespan 启停的最小调度器。"""

    def __init__(
        self,
        store: ScanStore,
        settings: Any,
        scan_config: LoadedScanConfig,
        *,
        tick_seconds: float = TICK_SECONDS,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._settings = settings
        self._config = scan_config
        self._tick_seconds = tick_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._task: asyncio.Task[None] | None = None
        self._last_slot_id: str | None = None
        self._stopping = asyncio.Event()

    @property
    def enabled(self) -> bool:
        return bool(self._config.document.schedule.enabled)

    @property
    def last_slot_id(self) -> str | None:
        return self._last_slot_id

    async def start(self) -> None:
        if not self.enabled:
            logger.info("内部调度未启用（schedule.enabled=false）")
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._loop(), name="scan-scheduler")
        logger.info(
            "内部调度已启动：cron=%s timezone=%s scanTypes=%s",
            self._config.document.schedule.cron,
            self._config.document.schedule.timezone,
            self._config.document.schedule.scanTypes,
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
            except Exception as exc:  # noqa: BLE001 - 调度失败不能拖垮服务
                logger.warning(
                    "scheduler tick failed: %s: %s", type(exc).__name__, exc, exc_info=True
                )
            await asyncio.sleep(self._tick_seconds)

    async def tick(self, now: datetime | None = None) -> str | None:
        """处理当前槽位。返回本次入队的槽位 id；未入队返回 None。

        只处理“现在正在进行的”槽位：服务在槽位之后启动不会补跑。
        """
        schedule = self._config.document.schedule
        if not schedule.enabled:
            return None
        moment = now or self._clock()
        slot = current_slot(moment, schedule.timezone, schedule.cron)
        if slot is None:
            return None
        if self._last_slot_id == slot.slot_id:
            # 同一分钟内重复 tick：本地已处理过。
            return None
        self._last_slot_id = slot.slot_id
        outcome = await self._enqueue(slot, schedule)
        logger.info(
            "scheduled scan slot=%s outcome=%s", slot.slot_id, outcome,
        )
        return slot.slot_id

    async def _enqueue(self, slot: ScheduleSlot, schedule: Any) -> str:
        warehouses = list(self._config.document.warehouses)
        warehouse = warehouses[0]
        # 调度用服务账号身份入队：worker 取数时现取服务令牌，用户 JWT 不参与。
        principal = Principal(
            user_id=self._settings.service_account_name,
            user_name=self._settings.service_account_name,
            authorities=("insp_read",),
            warehouse_scope=tuple(warehouses),
            token_use="agent_service",
        )
        run, outcome = await enqueue_scan(
            self._store,
            principal=principal,
            scan_types=list(schedule.scanTypes),
            warehouse=warehouse,
            config_snapshot=self._config.snapshot,
            config_hash_value=self._config.config_hash,
            config_version=self._config.version,
            notification_mode=self._config.document.notifications.mode,
            schedule_slot=slot.slot_id,
            trigger="schedule",
        )
        logger.info(
            "scheduled scan queued slot=%s scanId=%s outcome=%s",
            slot.slot_id, run.get("scanId"), outcome,
        )
        return outcome
