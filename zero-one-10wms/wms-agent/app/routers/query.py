"""`POST /agent/query` 与 `GET /agent/trace/{traceId}`。

契约见实施方案 §5.2 / §5.4：
- 请求体只接受 `query`（必填，≤500 字）与可选 `sessionId`，不接收 `context`；
- 响应统一 `{code, message, data}`，`data.toolCalls` 必填；
- 鉴权沿用 `require_principal`，工具调用原样透传用户 JWT。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from app.agent.service import answer_query
from app.config import get_settings
from app.llm.provider import LLMProvider, build_provider
from app.security import Principal, extract_bearer_token, require_principal
from app.storage.store import TraceStore
from app.tools.gateway_client import GatewayClient

router = APIRouter()

CODE_SUCCESS = 10000
CODE_NOT_FOUND = 9999


class QueryRequest(BaseModel):
    """问数请求体。"""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500, description="自然语言问题")
    sessionId: str | None = Field(default=None, description="会话 ID，缺省由服务端生成")


def get_provider() -> LLMProvider:
    """构造模型 Provider（测试可覆盖）。"""
    return build_provider(get_settings())


def get_client(request: Request) -> GatewayClient:
    """构造网关客户端（测试可覆盖）。"""
    settings = request.app.state.settings
    return GatewayClient(
        settings.gateway_url,
        timeout_seconds=settings.tool_timeout_seconds,
    )


def get_store(request: Request) -> TraceStore:
    """取 trace 存储（测试可覆盖）。"""
    return request.app.state.store


@router.post("/query")
async def query(
    request: Request,
    payload: QueryRequest,
    principal: Principal = Depends(require_principal),
    provider: LLMProvider = Depends(get_provider),
    client: GatewayClient = Depends(get_client),
    store: TraceStore = Depends(get_store),
) -> dict[str, Any]:
    """同步问数：模型自主选工具取数并作答。"""
    token = extract_bearer_token(request)
    code, message, data = await answer_query(
        query=payload.query,
        session_id=payload.sessionId,
        principal=principal,
        provider=provider,
        client=client,
        store=store,
        token=token,
    )
    return {"code": code, "message": message, "data": data}


@router.get("/trace/{trace_id}")
async def trace(
    trace_id: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    store: TraceStore = Depends(get_store),
) -> dict[str, Any]:
    """按 traceId 查询审计摘要。"""
    summary = await store.get(trace_id)
    if summary is None:
        return {
            "code": CODE_NOT_FOUND,
            "message": "查询数据不存在",
            "data": {"traceId": trace_id, "persisted": False},
        }
    return {"code": CODE_SUCCESS, "message": "ok", "data": summary}
