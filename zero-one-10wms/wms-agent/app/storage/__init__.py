"""trace 存储后端选择。

约定：
- `WMS_AGENT_STORE_BACKEND=memory`（默认）：内存存储，响应里 `persisted=false`；
- `WMS_AGENT_STORE_BACKEND=postgres`：F-012 起可用；PG 不可用时自动降级为内存，
  问数不失败，响应里 `persisted=false`。
"""

from __future__ import annotations

import logging

from app.config import Settings
from app.storage.memory import MemoryTraceStore
from app.storage.store import TraceStore

logger = logging.getLogger(__name__)


def build_store(settings: Settings) -> TraceStore:
    """按配置构造存储后端。"""
    backend = (settings.store_backend or "memory").strip().lower()
    if backend == "postgres":
        try:
            from app.storage.postgres import PostgresTraceStore

            return PostgresTraceStore(settings.db_url)
        except Exception as exc:  # noqa: BLE001 - 降级必须吞掉所有异常
            logger.warning("postgres store unavailable, fallback to memory: %s", type(exc).__name__)
            return MemoryTraceStore()
    return MemoryTraceStore()


__all__ = ["TraceStore", "MemoryTraceStore", "build_store"]
