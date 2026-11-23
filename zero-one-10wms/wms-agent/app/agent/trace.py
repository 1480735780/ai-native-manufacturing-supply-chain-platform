"""工具调用审计记录（实施方案 §5.2 的 toolCalls 字段）。

约定：
- 只记录审计摘要：工具名、脱敏后的统一参数、状态、行数、耗时、端点、错误码、digest；
- 不记录完整工具结果，不记录 JWT 原文；
- digest 形如 `sha256:<16 位十六进制>`。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.tools.adapter import ToolResult

# 本地错误码，与 Java 侧语义保持一致（ADR-009.1）
CODE_PARAMS_INVALID = 9995
CODE_RUNTIME_ERROR = 9994

DIGEST_PREFIX = "sha256:"


@dataclass
class ToolCallRecord:
    """一次工具调用的审计摘要。"""

    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    status: str = "error"
    row_count: int = 0
    duration_ms: int = 0
    endpoint: str = ""
    error_code: int | None = None
    retryable: bool = False
    attempt: int = 1
    result_digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转成响应里的 camelCase 结构。"""
        return {
            "tool": self.tool,
            "params": self.params,
            "status": self.status,
            "rowCount": self.row_count,
            "durationMs": self.duration_ms,
            "endpoint": self.endpoint,
            "errorCode": self.error_code,
            "retryable": self.retryable,
            "attempt": self.attempt,
            "resultDigest": self.result_digest,
        }


class TraceCollector:
    """收集一次问数过程中的工具调用记录。"""

    def __init__(self) -> None:
        self._records: list[ToolCallRecord] = []

    @property
    def records(self) -> list[ToolCallRecord]:
        """已记录的调用列表。"""
        return list(self._records)

    def add(self, record: ToolCallRecord) -> ToolCallRecord:
        """追加一条记录。"""
        self._records.append(record)
        return record

    def add_result(
        self, result: ToolResult, params: dict[str, Any] | None = None
    ) -> ToolCallRecord:
        """把一次工具执行结果转成审计记录。"""
        digest = result.result_digest or ""
        record = ToolCallRecord(
            tool=result.tool,
            params=dict(params or {}),
            status=result.status,
            row_count=len(result.rows),
            duration_ms=result.duration_ms,
            endpoint=result.endpoint,
            error_code=result.error_code,
            retryable=result.retryable,
            attempt=result.attempt,
            result_digest=f"{DIGEST_PREFIX}{digest}" if digest else "",
        )
        return self.add(record)

    def add_error(
        self,
        tool: str,
        message: str,
        *,
        error_code: int,
        params: dict[str, Any] | None = None,
        endpoint: str = "",
        retryable: bool = False,
    ) -> ToolCallRecord:
        """记录一次未到达 Java 端的本地错误。"""
        return self.add(
            ToolCallRecord(
                tool=tool,
                params=dict(params or {}),
                status="error",
                row_count=0,
                duration_ms=0,
                endpoint=endpoint,
                error_code=error_code,
                retryable=retryable,
                attempt=1,
                result_digest=f"{DIGEST_PREFIX}0",
            )
        )

    def to_list(self) -> list[dict[str, Any]]:
        """全部记录的响应结构。"""
        return [record.to_dict() for record in self._records]
