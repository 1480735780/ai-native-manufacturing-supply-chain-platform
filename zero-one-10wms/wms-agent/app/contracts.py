"""跨模块共享的数据契约。

只放纯数据结构与常量，不依赖网络、存储或具体模型 SDK，
避免 LLM、工具、Agent 三层互相耦合。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 对话角色，取值与 OpenAI Chat Completions 兼容
ROLE_SYSTEM = "system"
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_TOOL = "tool"


@dataclass(frozen=True)
class ToolCall:
    """模型请求调用的一次工具。"""

    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Message:
    """一条对话消息。"""

    role: str
    content: str = ""
    tool_call_id: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True)
class ToolSchema:
    """暴露给模型的工具描述。"""

    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_openai(self) -> dict[str, Any]:
        """转成 OpenAI 兼容的 tools 条目。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {"type": "object", "properties": {}},
            },
        }


@dataclass(frozen=True)
class ModelReply:
    """模型一次回复：要么给文本，要么给工具调用，可同时出现。"""

    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    raw: dict[str, Any] | None = None
