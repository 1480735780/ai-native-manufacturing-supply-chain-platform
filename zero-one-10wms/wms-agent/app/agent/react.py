"""单 Agent 的 ReAct 循环（实施方案 §F-010）。

约束：
- 工具调用轮数硬上限 2 轮，第 2 轮之后强制模型给最终答案；
- 每次工具调用都记入 TraceCollector；
- 工具失败不抛异常，把失败信息回喂给模型，由模型决定如何作答；
- 模型永远拿不到完整工具结果，只拿到裁剪脱敏后的副本。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.agent.trace import CODE_PARAMS_INVALID, CODE_RUNTIME_ERROR, TraceCollector
from app.contracts import Message, ToolCall, ToolSchema
from app.llm.provider import LLMProvider
from app.tools.adapter import ToolParameterError, execute_tool, prepare_call
from app.tools.gateway_client import GatewayClient
from app.tools.registry import get_tool
from app.tools.sanitizer import build_llm_payload

MAX_TOOL_ROUNDS = 2

ROUND_LIMIT_ANSWER = "已达到工具调用轮数上限（2 轮），无法继续取数，请缩小问题范围后重试。"


@dataclass
class ReactResult:
    """一次 ReAct 执行的结果。"""

    answer: str
    tool_rounds: int = 0
    status: str = "ok"
    error_message: str | None = None
    messages: list[Message] = field(default_factory=list)


def _tool_result_content(tool: str, result: Any) -> str:
    """把工具结果转成喂给模型的文本（裁剪 + 脱敏）。"""
    payload = build_llm_payload(tool, result.rows, result.total)
    body = {
        "status": result.status,
        "rowCount": len(payload["rows"]),
        "total": payload["total"],
        "truncated": payload["truncated"],
        "rows": payload["rows"],
    }
    return json.dumps(body, ensure_ascii=False, default=str)


def _tool_error_content(message: str, error_code: int | None) -> str:
    """工具失败时喂给模型的文本，不含堆栈与敏感信息。"""
    return json.dumps(
        {"status": "error", "errorCode": error_code, "message": message},
        ensure_ascii=False,
    )


async def _run_one_tool(
    call: ToolCall,
    *,
    client: GatewayClient,
    token: str | None,
    collector: TraceCollector,
) -> tuple[str, str]:
    """执行一次工具调用，返回 (喂回模型的内容, 工具名)。"""
    params = dict(call.arguments or {})
    try:
        tool = get_tool(call.name)
    except KeyError:
        collector.add_error(
            call.name,
            f"未知工具：{call.name}",
            error_code=CODE_RUNTIME_ERROR,
            params=params,
        )
        return _tool_error_content(f"未知工具：{call.name}", CODE_RUNTIME_ERROR), call.name

    try:
        prepare_call(tool.name, params)
    except ToolParameterError as exc:
        collector.add_error(
            tool.name,
            "工具参数非法",
            error_code=CODE_PARAMS_INVALID,
            params=params,
        )
        return (
            _tool_error_content("工具参数非法，请检查参数取值", CODE_PARAMS_INVALID),
            tool.name,
        )

    result = await execute_tool(tool, params, client, token=token)
    collector.add_result(result, params)

    if result.status == "error":
        return (
            _tool_error_content(
                result.error_message or "工具调用失败", result.error_code
            ),
            tool.name,
        )
    return _tool_result_content(tool.name, result), tool.name


async def run_react(
    *,
    provider: LLMProvider,
    messages: list[Message],
    schemas: list[ToolSchema],
    client: GatewayClient,
    token: str | None,
    collector: TraceCollector,
) -> ReactResult:
    """跑一轮 ReAct：模型 → 工具 → 模型，直到拿到最终答案。"""
    conversation = list(messages)
    tool_rounds = 0
    available = list(schemas)

    while True:
        reply = await provider.complete(conversation, available)

        if not reply.tool_calls:
            answer = (reply.content or "").strip()
            if not answer:
                answer = "未获得有效回答，请换一种问法重试。"
            return ReactResult(
                answer=answer,
                tool_rounds=tool_rounds,
                status="ok",
                messages=conversation,
            )

        if tool_rounds >= MAX_TOOL_ROUNDS:
            # 达到硬上限：不再执行工具，直接给出最终答案
            return ReactResult(
                answer=ROUND_LIMIT_ANSWER,
                tool_rounds=tool_rounds,
                status="ok",
                messages=conversation,
            )

        conversation.append(
            Message(
                role="assistant",
                content=reply.content or "",
                tool_calls=tuple(reply.tool_calls),
            )
        )

        for call in reply.tool_calls:
            content, _ = await _run_one_tool(
                call, client=client, token=token, collector=collector
            )
            conversation.append(
                Message(role="tool", content=content, tool_call_id=call.id)
            )

        tool_rounds += 1
        if tool_rounds >= MAX_TOOL_ROUNDS:
            # 第 2 轮之后强制最终答案：不再向模型暴露工具
            available = []
