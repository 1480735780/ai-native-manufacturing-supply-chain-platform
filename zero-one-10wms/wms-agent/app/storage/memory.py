"""内存 trace 存储：进程内字典，重启即丢。

用途：
- F-010 阶段的默认后端（PG 未就绪时的降级路径）；
- 单元测试里不依赖数据库即可断言 `persisted` 与 trace 内容。
"""

from __future__ import annotations

from typing import Any

from app.storage.store import TraceStore


class MemoryTraceStore:
    """把 trace 摘要放在进程内存里。"""

    def __init__(self) -> None:
        self._traces: dict[str, dict[str, Any]] = {}

    async def save(self, summary: dict[str, Any]) -> bool:
        """保存摘要；内存后端不算真正持久化。"""
        trace_id = str(summary.get("traceId") or "")
        if trace_id:
            self._traces[trace_id] = dict(summary)
        return False

    async def get(self, trace_id: str) -> dict[str, Any] | None:
        """按 traceId 取摘要。"""
        return self._traces.get(trace_id)
