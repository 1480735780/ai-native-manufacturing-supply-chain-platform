"""F-008：LLMProvider 抽象与 mock 回放的验证。

覆盖：
- Mock Provider 按序消费、耗尽抛错、确定性；
- OpenAI 兼容 Provider 的请求构造与响应解析（httpx.MockTransport，不联网）；
- 密钥只来自环境变量：仓库内不得出现密钥样式字符串。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.contracts import Message, ToolSchema
from app.llm.mock import MockProvider, load_scenario
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.llm.provider import ProviderError, build_provider

FIXTURES = Path(__file__).parent / "fixtures" / "llm"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCHEMA = ToolSchema(
    name="STOCK-QUERY",
    description="查询实时库存",
    parameters={
        "type": "object",
        "properties": {"page_index": {"type": "integer"}},
    },
)


def _messages() -> list[Message]:
    return [Message(role="user", content="当前库存有多少？")]


# ---------------------------------------------------------------- Mock 回放


async def test_mock_provider_consumes_responses_in_order():
    provider = MockProvider(load_scenario(FIXTURES / "single_tool_stock.json"))

    first = await provider.complete(_messages(), [SCHEMA])
    assert [call.name for call in first.tool_calls] == ["STOCK-QUERY"]
    assert first.tool_calls[0].arguments == {"page_index": 1, "page_size": 20}
    assert first.content is None

    second = await provider.complete(_messages(), [SCHEMA])
    assert second.tool_calls == ()
    assert second.content == "库存查询完成。"


async def test_mock_provider_raises_when_scenario_exhausted():
    provider = MockProvider(load_scenario(FIXTURES / "single_tool_stock.json"))
    await provider.complete(_messages(), [SCHEMA])
    await provider.complete(_messages(), [SCHEMA])

    with pytest.raises(ProviderError) as excinfo:
        await provider.complete(_messages(), [SCHEMA])
    assert "exhausted" in str(excinfo.value)


async def test_mock_provider_rejects_unknown_response_type():
    with pytest.raises(ProviderError):
        MockProvider({"name": "bad", "responses": [{"type": "nope"}]})


async def test_same_scenario_yields_identical_tool_call_sequence():
    async def run() -> list[tuple[str, dict]]:
        provider = MockProvider(load_scenario(FIXTURES / "two_step.json"))
        sequence: list[tuple[str, dict]] = []
        while provider.remaining > 0:
            reply = await provider.complete(_messages(), [SCHEMA])
            sequence.extend((c.name, c.arguments) for c in reply.tool_calls)
        return sequence

    assert await run() == await run()
    assert [name for name, _ in await run()] == ["STOCK-QUERY", "DASH-TREND"]


# ------------------------------------------------------- OpenAI 兼容 Provider


async def test_openai_compatible_sends_expected_request_and_parses_tool_calls():
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "STOCK-QUERY",
                                        "arguments": '{"page_index": 1}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    provider = OpenAICompatibleProvider(
        base_url="https://example.invalid/v1",
        model="agnes-3.0-flash",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    reply = await provider.complete(_messages(), [SCHEMA])

    assert captured["url"] == "https://example.invalid/v1/chat/completions"
    assert captured["auth"] == "Bearer test-key"
    payload = captured["payload"]
    assert payload["model"] == "agnes-3.0-flash"
    assert payload["messages"] == [
        {"role": "user", "content": "当前库存有多少？"}
    ]
    assert payload["tools"][0]["function"]["name"] == "STOCK-QUERY"

    assert reply.tool_calls[0].name == "STOCK-QUERY"
    assert reply.tool_calls[0].arguments == {"page_index": 1}


async def test_openai_compatible_requires_api_key():
    provider = OpenAICompatibleProvider(
        base_url="https://example.invalid/v1",
        model="agnes-3.0-flash",
        api_key="",
    )
    with pytest.raises(ProviderError) as excinfo:
        await provider.complete(_messages(), [SCHEMA])
    assert "api key" in str(excinfo.value)


async def test_openai_compatible_timeout_becomes_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    provider = OpenAICompatibleProvider(
        base_url="https://example.invalid/v1",
        model="agnes-3.0-flash",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderError) as excinfo:
        await provider.complete(_messages(), [SCHEMA])
    assert "timeout" in str(excinfo.value)
    assert "test-key" not in str(excinfo.value)


async def test_openai_compatible_http_error_becomes_provider_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    provider = OpenAICompatibleProvider(
        base_url="https://example.invalid/v1",
        model="agnes-3.0-flash",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderError) as excinfo:
        await provider.complete(_messages(), [SCHEMA])
    assert "500" in str(excinfo.value)
    assert "test-key" not in str(excinfo.value)


# ------------------------------------------------------------------ 工厂与密钥


def test_build_provider_selects_mock_by_default():
    # 不读本地 .env：本地 .env 可能配了真实 LLM（openai），那属于运行环境而非默认值。
    provider = build_provider(Settings(_env_file=None))
    assert isinstance(provider, MockProvider)


def test_build_provider_rejects_unknown_provider():
    settings = Settings(WMS_AGENT_LLM_PROVIDER="unknown")
    with pytest.raises(ProviderError):
        build_provider(settings)


def test_no_api_key_material_in_repository():
    pattern = re.compile(r"sk-[A-Za-z0-9_\-]{12,}")
    skip_dirs = {".venv", ".uv", "__pycache__", ".git", ".pytest_cache"}
    # 本地 .env / .env.local 是 gitignore 排除的运行配置，密钥按设计只应出现在那里，
    # 不属于入库文件；.env.example 是入库模板，仍纳入扫描。
    local_env_files = {".env", ".env.local"}
    offenders: list[str] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.name in local_env_files:
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if pattern.search(content):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == []
