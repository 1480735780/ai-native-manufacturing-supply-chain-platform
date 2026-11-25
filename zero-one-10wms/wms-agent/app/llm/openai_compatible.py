"""OpenAI 兼容 Chat Completions Provider（Agnes OpenAI 兼容接口）。

刻意用 httpx 直调而不引 SDK：少一个依赖、少一层版本风险，
也便于用 httpx.MockTransport 做离线验证。

安全约定：API Key 只从环境变量/.env 取；异常与日志都不带 key 值。
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.contracts import Message, ModelReply, ToolCall, ToolSchema
from app.llm.provider import ProviderError

CHAT_COMPLETIONS_PATH = "/chat/completions"
ERROR_DETAIL_MAX_CHARS = 200


def _error_detail(response: httpx.Response, *, secret: str = "") -> str:
    """从错误响应里取一句可读的原因，附在状态码后面。

    只取 ``error.message``（OpenAI 风格）或正文开头，压成单行并截断；完整正文与 API Key
    一律不进异常和日志——否则现场只看到 "http status 400"，分不清是 key、模型还是网络出口的问题。
    """
    try:
        body = response.json()
    except ValueError:
        body = None
    message: Any = None
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
        elif isinstance(error, str):
            message = error
    text = message if isinstance(message, str) else response.text
    text = " ".join(str(text).split())
    if secret:
        text = text.replace(secret, "<redacted>")
    if len(text) > ERROR_DETAIL_MAX_CHARS:
        text = text[: ERROR_DETAIL_MAX_CHARS - 1] + "…"
    return text


class OpenAICompatibleProvider:
    """调用 OpenAI 兼容的 /chat/completions 接口。"""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: float = 8.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key or ""
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    @property
    def endpoint(self) -> str:
        """完整请求地址。"""
        return f"{self.base_url}{CHAT_COMPLETIONS_PATH}"

    async def complete(
        self, messages: list[Message], tools: list[ToolSchema]
    ) -> ModelReply:
        """发起一轮对话并解析回复。"""
        if not self._api_key:
            raise ProviderError("llm api key is not configured")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [self._to_openai_message(m) for m in messages],
            "temperature": 0,
        }
        if tools:
            payload["tools"] = [t.to_openai() for t in tools]

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, transport=self._transport
            ) as client:
                response = await client.post(
                    self.endpoint, json=payload, headers=headers
                )
        except httpx.TimeoutException as exc:
            raise ProviderError("llm request timeout") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"llm request failed: {type(exc).__name__}"
            ) from exc

        if response.status_code >= 400:
            detail = _error_detail(response, secret=self._api_key)
            raise ProviderError(
                f"llm returned http status {response.status_code}"
                + (f": {detail}" if detail else "")
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError("llm response is not valid json") from exc

        return self._parse(data)

    @staticmethod
    def _to_openai_message(message: Message) -> dict[str, Any]:
        """把内部消息转成 OpenAI 格式。"""
        if message.tool_calls:
            return {
                "role": message.role,
                "content": message.content or None,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(call.arguments, ensure_ascii=False),
                        },
                    }
                    for call in message.tool_calls
                ],
            }
        if message.role == "tool":
            return {
                "role": "tool",
                "tool_call_id": message.tool_call_id or "",
                "content": message.content or "",
            }
        return {"role": message.role, "content": message.content}

    @staticmethod
    def _parse(data: dict[str, Any]) -> ModelReply:
        """解析 Chat Completions 响应。"""
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("llm response contains no choices")
        message = choices[0].get("message") or {}

        raw_calls = message.get("tool_calls") or []
        calls: list[ToolCall] = []
        for raw in raw_calls:
            function = raw.get("function") or {}
            arguments = function.get("arguments") or "{}"
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError as exc:
                    raise ProviderError(
                        "llm response tool call arguments is not valid json"
                    ) from exc
            calls.append(
                ToolCall(
                    id=str(raw.get("id") or ""),
                    name=str(function.get("name") or ""),
                    arguments=dict(arguments),
                )
            )

        return ModelReply(
            content=message.get("content"),
            tool_calls=tuple(calls),
            raw=data,
        )
