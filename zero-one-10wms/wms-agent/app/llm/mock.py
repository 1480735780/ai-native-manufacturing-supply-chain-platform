"""Mock Provider：按 scenario 有序回放模型响应。

用途：离线确定性验证（同一 scenario 重复运行产出相同的工具调用序列）。

约定：
- scenario 是有序响应列表，按序消费，一次调用消费一条；
- 列表耗尽后再次调用必须抛错，不允许静默返回空文本；
- 不做业务判断，只回放 fixture 里写好的内容。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.contracts import Message, ModelReply, ToolCall, ToolSchema
from app.llm.provider import ProviderError

TYPE_TOOL_CALL = "tool_call"
TYPE_TEXT = "text"


def load_scenario(path: str | Path) -> dict[str, Any]:
    """读取 scenario fixture 文件。"""
    file_path = Path(path)
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProviderError(f"mock scenario file not found: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderError(
            f"mock scenario file is not valid json: {file_path}"
        ) from exc


class MockProvider:
    """回放固定响应序列的 Provider。"""

    def __init__(self, scenario: dict[str, Any] | None = None) -> None:
        self.scenario = scenario or {}
        self.responses: list[dict[str, Any]] = list(self.scenario.get("responses") or [])
        self.calls: list[list[Message]] = []
        self._cursor = 0
        self._validate()

    @property
    def name(self) -> str:
        """scenario 名称，仅用于断言与日志定位。"""
        return str(self.scenario.get("name") or "unnamed")

    def _validate(self) -> None:
        for index, item in enumerate(self.responses):
            kind = item.get("type")
            if kind not in {TYPE_TOOL_CALL, TYPE_TEXT}:
                raise ProviderError(
                    f"mock scenario response #{index} has unsupported type: {kind!r}"
                )

    @property
    def remaining(self) -> int:
        """剩余未消费的响应条数。"""
        return len(self.responses) - self._cursor

    async def complete(
        self, messages: list[Message], tools: list[ToolSchema]
    ) -> ModelReply:
        """按序返回下一条预设响应。"""
        self.calls.append(list(messages))
        if self._cursor >= len(self.responses):
            raise ProviderError(
                f"mock scenario '{self.name}' exhausted after "
                f"{len(self.responses)} response(s)"
            )
        item = self.responses[self._cursor]
        self._cursor += 1

        if item["type"] == TYPE_TEXT:
            # 场景条目可选 "usage": {"prompt_tokens": .., "completion_tokens": ..}，
            # 形状与 OpenAI 兼容响应的 raw["usage"] 一致，供摘要记账测试回放。
            usage = item.get("usage")
            raw = {"usage": dict(usage)} if isinstance(usage, dict) else None
            return ModelReply(content=str(item.get("content") or ""), raw=raw)

        call = ToolCall(
            id=str(item.get("id") or f"mock_call_{self._cursor}"),
            name=str(item.get("tool") or ""),
            arguments=dict(item.get("arguments") or {}),
        )
        return ModelReply(content=None, tool_calls=(call,))
