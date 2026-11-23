"""问数服务：组装提示 → 跑 ReAct → 组装响应 → 落 trace。

响应契约见实施方案 §5.2：成功与失败都用 `{code, message, data}` 外壳，
`data.toolCalls` 必填，失败时已完成的工具调用也要保留。
"""

from __future__ import annotations

import logging
import secrets
import time
from datetime import datetime
from typing import Any

from app.agent.react import ReactResult, run_react
from app.agent.trace import TraceCollector
from app.contracts import Message, ToolSchema
from app.llm.provider import LLMProvider, ProviderError
from app.security import Principal
from app.storage.store import TraceStore
from app.tools.gateway_client import GatewayClient
from app.tools.registry import tool_schemas

logger = logging.getLogger(__name__)

CODE_SUCCESS = 10000
CODE_RUNTIME_ERROR = 9994

BASE_SYSTEM_PROMPT = """你是 WMS 仓储问数助手，只回答库存、效期、收货未上架、待办计数、上/下架趋势、进货延时这六类业务数据。

规则：
1. 必须通过工具取数，禁止凭记忆或猜测编造数字；
2. 工具返回空结果时，明确说明没有数据；
3. 工具调用失败时，如实说明失败原因与错误码，不要伪造数据；
4. 回答用简洁中文，先给结论，再给关键明细（最多列 20 行）。
"""

NO_RESULT_ANSWER = "未查询到相关数据。"


def _now_iso() -> str:
    """带时区的当前时间。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def new_trace_id() -> str:
    """生成 traceId。"""
    return f"t-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}"


def new_session_id() -> str:
    """生成 sessionId。"""
    return f"s-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}"


def build_system_prompt(schemas: list[ToolSchema]) -> str:
    """把工具清单拼进系统提示。"""
    lines = [BASE_SYSTEM_PROMPT, "可用工具："]
    for schema in schemas:
        params = schema.parameters.get("properties") or {}
        param_text = "、".join(sorted(params.keys())) if params else "无"
        lines.append(f"- {schema.name}：{schema.description}（参数：{param_text}）")
    return "\n".join(lines)


def _summary(
    *,
    trace_id: str,
    session_id: str,
    query: str,
    answer: str,
    principal: Principal,
    result: ReactResult,
    collector: TraceCollector,
    duration_ms: int,
) -> dict[str, Any]:
    """trace 审计摘要（不含 JWT、不含完整工具结果）。"""
    return {
        "traceId": trace_id,
        "sessionId": session_id,
        "userId": principal.user_id,
        "userName": principal.user_name,
        "query": query,
        "answer": answer,
        "status": result.status,
        "toolRounds": result.tool_rounds,
        "durationMs": duration_ms,
        "createdAt": _now_iso(),
        "toolCalls": [
            {
                "tool": record.tool,
                "params": record.params,
                "status": record.status,
                "rowCount": record.row_count,
                "durationMs": record.duration_ms,
                "endpoint": record.endpoint,
                "errorCode": record.error_code,
                "retryable": record.retryable,
                "attempt": record.attempt,
                "resultDigest": record.result_digest,
            }
            for record in collector.records
        ],
    }


async def answer_query(
    *,
    query: str,
    session_id: str | None,
    principal: Principal,
    provider: LLMProvider,
    client: GatewayClient,
    store: TraceStore,
    token: str | None = None,
) -> tuple[int, str, dict[str, Any]]:
    """执行一次问数。

    返回 (code, message, data)。
    """
    trace_id = new_trace_id()
    session = session_id or new_session_id()
    collector = TraceCollector()
    schemas = tool_schemas()

    messages = [
        Message(role="system", content=build_system_prompt(schemas)),
        Message(role="user", content=query),
    ]

    started = time.perf_counter()

    try:
        result = await run_react(
            provider=provider,
            messages=messages,
            schemas=schemas,
            client=client,
            token=token,
            collector=collector,
        )
        answer = result.answer or NO_RESULT_ANSWER
        code, message = CODE_SUCCESS, "ok"
    except ProviderError as exc:
        logger.warning("llm provider failed: %s", type(exc).__name__)
        result = ReactResult(answer="模型调用失败，请稍后重试。", status="error")
        answer = result.answer
        code, message = CODE_RUNTIME_ERROR, "模型调用失败"
    except Exception as exc:  # noqa: BLE001 - 兜底不让问数 500
        logger.warning("query failed: %s", type(exc).__name__)
        result = ReactResult(answer="问数处理失败，请稍后重试。", status="error")
        answer = result.answer
        code, message = CODE_RUNTIME_ERROR, "问数处理失败"

    duration_ms = int((time.perf_counter() - started) * 1000)

    data: dict[str, Any] = {
        "answer": answer,
        "sessionId": session,
        "traceId": trace_id,
        "persisted": False,
        "toolCalls": collector.to_list(),
        "createdAt": _now_iso(),
    }

    try:
        persisted = await store.save(
            _summary(
                trace_id=trace_id,
                session_id=session,
                query=query,
                answer=answer,
                principal=principal,
                result=result,
                collector=collector,
                duration_ms=duration_ms,
            )
        )
        data["persisted"] = bool(persisted)
    except Exception as exc:  # noqa: BLE001 - 持久化失败不影响问数
        logger.warning("trace persist failed: %s", type(exc).__name__)
        data["persisted"] = False

    return code, message, data
