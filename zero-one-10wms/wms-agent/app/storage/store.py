"""trace 存储协议。

F-010 先用内存实现，F-012 换成 PostgreSQL（schema `wms_agent`）。
只存审计摘要：用户标识、query、answer、状态、耗时、工具名、脱敏参数、行数、错误码、digest；
不存 JWT 原文，不存完整工具结果。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TraceStore(Protocol):
    """trace 摘要存储。"""

    async def save(self, summary: dict[str, Any]) -> bool:
        """保存一条 trace 摘要，返回是否真正落库。"""
        ...

    async def get(self, trace_id: str) -> dict[str, Any] | None:
        """按 traceId 查询摘要。"""
        ...
