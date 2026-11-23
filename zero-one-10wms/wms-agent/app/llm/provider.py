"""LLMProvider 协议与工厂。

约定（ADR-010）：
- Provider 只负责"把消息发给模型并把回复翻译回来"，不做任何业务判断；
- API Key 只来自环境变量或本地 .env，不进代码、日志与异常消息；
- 统一的模型名、base URL、key 与超时由 Settings 提供。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.config import Settings
from app.contracts import Message, ModelReply, ToolSchema


class ProviderError(RuntimeError):
    """Provider 调用失败。

    约定：异常消息里不得出现 API Key、请求头原文等敏感内容。
    """


@runtime_checkable
class LLMProvider(Protocol):
    """统一模型调用协议。"""

    async def complete(
        self, messages: list[Message], tools: list[ToolSchema]
    ) -> ModelReply:
        """完成一轮对话，返回模型回复。"""
        ...


def build_provider(settings: Settings, *, scenario: dict | None = None) -> LLMProvider:
    """按配置构造 Provider。

    - `mock`：回放给定 scenario（离线确定性验证用）；
      未显式传 scenario 时，按 `WMS_AGENT_LLM_SCENARIO_PATH` 读取本地 JSON；
    - `openai` / `agnes` / `openai_compatible`：OpenAI 兼容的 Chat Completions。
    """
    name = (settings.llm_provider or "mock").strip().lower()
    if name == "mock":
        from app.llm.mock import MockProvider

        if scenario is None:
            scenario = _load_scenario_file(settings.llm_scenario_path)
        return MockProvider(scenario or {})
    if name in {"openai", "agnes", "openai_compatible"}:
        from app.llm.openai_compatible import OpenAICompatibleProvider

        return OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    raise ProviderError(f"unknown llm provider: {settings.llm_provider}")


def _load_scenario_file(path: str | None) -> dict | None:
    """按路径读取 mock scenario（未配置时返回 None）。"""
    if not path:
        return None
    from app.llm.mock import load_scenario

    return load_scenario(path)
