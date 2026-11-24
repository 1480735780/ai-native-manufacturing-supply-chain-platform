"""`POST /agent/query` 的确定性回放测试。

用 mock scenario（模型侧）+ httpx.MockTransport（网关侧）跑完整链路：
请求 → ReAct → 工具 → 归一化 → 回喂模型 → 响应契约。

断言只针对「工具调用序列、参数、响应契约、错误码语义」，
不断言模型逐字文案（mock 文案是 fixture 内容，不是能力指标）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agent.react import MAX_TOOL_ROUNDS, ROUND_LIMIT_ANSWER
from app.llm.mock import MockProvider, load_scenario
from app.main import create_app
from app.routers import query as query_router
from app.security import Principal, require_principal
from app.storage.memory import MemoryTraceStore
from app.tools.gateway_client import GatewayClient

FIXTURES = Path(__file__).parent / "fixtures" / "llm"

STOCK_PATH = "/stock/inventory-query/query-all"
EXP_PATH = "/stock/expiry-warning/query-all"
NOUP_PATH = "/daycheck/no-up/get-no-up-goods"
TREND_UP_PATH = "/dashboard/query-goods-to-up"

TOKEN = "header.payload.signature"


def _stock_payload(rows: list[dict[str, Any]] | None = None, total: int = 0) -> dict:
    return {"code": 10000, "message": "ok", "data": {"rows": rows, "total": total}}


def _build_app(
    scenario_name: str,
    routes: dict[str, tuple[int, dict]],
    *,
    authorize: bool = True,
):
    """构造带 mock 模型与 mock 网关的应用。"""
    provider = MockProvider(load_scenario(FIXTURES / scenario_name))
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        entry = routes.get(request.url.path)
        if entry is None:
            return httpx.Response(
                404,
                json={"code": 9999, "message": "未匹配到路由", "data": None},
            )
        status, payload = entry
        return httpx.Response(status, json=payload)

    app = create_app()
    # 回放测试用内存存储，避免依赖本地 .env 的 PG 默认配置（不联网、不落库）。
    app.state.store = MemoryTraceStore()
    app.dependency_overrides[query_router.get_provider] = lambda: provider
    app.dependency_overrides[query_router.get_client] = lambda: GatewayClient(
        "http://gateway.test", transport=httpx.MockTransport(handler)
    )
    if authorize:
        app.dependency_overrides[require_principal] = lambda: Principal(
            user_id="u-1", user_name="tester", authorities=["R"], warnings=[]
        )
    return app, provider, captured


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_single_tool_query_returns_contract_shape() -> None:
    """单工具场景：响应外壳、data 字段、toolCalls 结构。"""
    rows = [
        {"goodsId": "G1", "goodsCode": "C1", "shpMingCheng": "商品1"},
        {"goodsId": "G2", "goodsCode": "C2", "shpMingCheng": "商品2"},
    ]
    app, provider, captured = _build_app(
        "query_single_tool.json", {STOCK_PATH: (200, _stock_payload(rows, 2))}
    )

    with TestClient(app) as client:
        response = client.post(
            "/agent/query", json={"query": "查一下库存"}, headers=_headers()
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 10000
    assert body["message"] == "ok"
    data = body["data"]
    assert set(data) == {
        "answer",
        "sessionId",
        "traceId",
        "persisted",
        "toolCalls",
        "createdAt",
    }
    assert data["persisted"] is False
    assert data["traceId"].startswith("t-")
    assert data["sessionId"].startswith("s-")

    calls = data["toolCalls"]
    assert len(calls) == 1
    call = calls[0]
    assert call["tool"] == "STOCK-QUERY"
    assert call["status"] == "success"
    assert call["rowCount"] == 2
    assert call["endpoint"] == STOCK_PATH
    assert call["errorCode"] is None
    assert call["retryable"] is False
    assert call["attempt"] == 1
    assert call["resultDigest"].startswith("sha256:")
    assert call["durationMs"] >= 0

    # 分页参数被映射成 Java 侧的驼峰命名
    assert captured[0].url.params.get("pageIndex") == "1"
    assert captured[0].url.params.get("pageSize") == "20"
    # 用户 JWT 原样透传给网关
    assert captured[0].headers.get("Authorization") == f"Bearer {TOKEN}"
    # 模型侧只应被问一轮半：一次工具调用 + 一次收尾
    assert len(provider.calls) == 2


def test_empty_result_is_reported_as_empty_not_failure() -> None:
    """Java 返回 rows=null 时归一化为空结果，不算失败。"""
    app, _provider, _captured = _build_app(
        "query_empty_result.json", {STOCK_PATH: (200, _stock_payload(None, 0))}
    )

    with TestClient(app) as client:
        response = client.post(
            "/agent/query", json={"query": "查一下库存"}, headers=_headers()
        )

    body = response.json()
    assert body["code"] == 10000
    call = body["data"]["toolCalls"][0]
    assert call["status"] == "empty"
    assert call["rowCount"] == 0
    assert call["errorCode"] is None


def test_two_step_query_keeps_tool_call_order() -> None:
    """两轮工具调用按顺序留痕，参数与端点正确。"""
    app, _provider, captured = _build_app(
        "query_two_steps.json",
        {
            STOCK_PATH: (200, _stock_payload([{"goodsId": "G1"}], 1)),
            TREND_UP_PATH: (
                200,
                {"code": 10000, "message": "ok", "data": [{"goodsName": "商品A"}]},
            ),
        },
    )

    with TestClient(app) as client:
        response = client.post(
            "/agent/query", json={"query": "库存和趋势"}, headers=_headers()
        )

    body = response.json()
    assert body["code"] == 10000
    calls = body["data"]["toolCalls"]
    assert [c["tool"] for c in calls] == ["STOCK-QUERY", "DASH-TREND"]
    assert calls[1]["endpoint"] == TREND_UP_PATH
    assert calls[1]["params"]["metric"] == "up_top"
    assert captured[1].url.params.get("count") == "7"


def test_tool_failure_is_recorded_with_error_code() -> None:
    """Java 返回 9995 时记为 error，不重试。"""
    app, _provider, _captured = _build_app(
        "query_tool_failed.json",
        {
            STOCK_PATH: (
                200,
                {"code": 9995, "message": "[pageIndex]参数值缺失", "data": None},
            )
        },
    )

    with TestClient(app) as client:
        response = client.post(
            "/agent/query", json={"query": "查一下库存"}, headers=_headers()
        )

    body = response.json()
    assert body["code"] == 10000
    call = body["data"]["toolCalls"][0]
    assert call["status"] == "error"
    assert call["errorCode"] == 9995
    assert call["retryable"] is False
    assert call["rowCount"] == 0


def test_gateway_5xx_is_error_and_retryable_but_not_retried() -> None:
    """网关 5xx 记 error 且 retryable=True，v1 不自动重试（只调用一次）。"""
    app, _provider, captured = _build_app(
        "query_tool_failed.json", {STOCK_PATH: (500, {"code": 9994, "message": "x"})}
    )

    with TestClient(app) as client:
        response = client.post(
            "/agent/query", json={"query": "查一下库存"}, headers=_headers()
        )

    body = response.json()
    call = body["data"]["toolCalls"][0]
    assert call["status"] == "error"
    assert call["errorCode"] == 500
    assert call["retryable"] is True
    assert call["attempt"] == 1
    assert len(captured) == 1


def test_tool_round_limit_is_enforced() -> None:
    """工具轮数硬上限 2 轮：第 3 个工具调用不再执行。"""
    app, _provider, captured = _build_app(
        "query_round_limit.json",
        {
            STOCK_PATH: (200, _stock_payload([{"goodsId": "G1"}], 1)),
            EXP_PATH: (200, _stock_payload([{"goodsId": "G2"}], 1)),
            NOUP_PATH: (200, {"code": 10000, "message": "ok", "data": []}),
        },
    )

    with TestClient(app) as client:
        response = client.post(
            "/agent/query", json={"query": "复杂问题"}, headers=_headers()
        )

    body = response.json()
    calls = body["data"]["toolCalls"]
    assert len(calls) == MAX_TOOL_ROUNDS
    assert [c["tool"] for c in calls] == ["STOCK-QUERY", "EXP-WARN-QUERY"]
    assert body["data"]["answer"] == ROUND_LIMIT_ANSWER
    # 第 3 个工具没有真正调用
    assert len(captured) == 2


def test_query_without_token_is_rejected() -> None:
    """无 token 直接 401（不 fallback 到 user 头）。"""
    app, _provider, _captured = _build_app(
        "query_single_tool.json", {STOCK_PATH: (200, _stock_payload([], 0))}
    )

    with TestClient(app) as client:
        response = client.post("/agent/query", json={"query": "查一下库存"})

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == 401
    assert body["data"] is None
    assert "token" in body["message"]


def test_request_rejects_unknown_field_and_empty_query() -> None:
    """不接收 context 字段；query 必填。"""
    app, _provider, _captured = _build_app(
        "query_single_tool.json", {STOCK_PATH: (200, _stock_payload([], 0))}
    )

    with TestClient(app) as client:
        extra = client.post(
            "/agent/query",
            json={"query": "查一下库存", "context": {"a": 1}},
            headers=_headers(),
        )
        empty = client.post("/agent/query", json={"query": ""}, headers=_headers())

    assert extra.json()["code"] == 9995
    assert empty.json()["code"] == 9995


def test_session_id_is_echoed() -> None:
    """传入 sessionId 时原样返回。"""
    app, _provider, _captured = _build_app(
        "query_single_tool.json", {STOCK_PATH: (200, _stock_payload([], 0))}
    )

    with TestClient(app) as client:
        response = client.post(
            "/agent/query",
            json={"query": "查一下库存", "sessionId": "s-fixed-1"},
            headers=_headers(),
        )

    assert response.json()["data"]["sessionId"] == "s-fixed-1"


def test_trace_endpoint_returns_summary_then_not_found() -> None:
    """trace 查询：命中返回 10000，未命中返回 9999。"""
    app, _provider, _captured = _build_app(
        "query_single_tool.json", {STOCK_PATH: (200, _stock_payload([], 0))}
    )

    with TestClient(app) as client:
        query_response = client.post(
            "/agent/query", json={"query": "查一下库存"}, headers=_headers()
        )
        trace_id = query_response.json()["data"]["traceId"]
        found = client.get(f"/agent/trace/{trace_id}", headers=_headers())
        missing = client.get("/agent/trace/t-not-exist", headers=_headers())

    assert found.status_code == 200
    found_body = found.json()
    assert found_body["code"] == 10000
    assert found_body["data"]["traceId"] == trace_id
    assert found_body["data"]["toolCalls"]

    assert missing.status_code == 200
    assert missing.json()["code"] == 9999


@pytest.mark.parametrize(
    "scenario",
    [
        "query_single_tool.json",
        "query_empty_result.json",
        "query_two_steps.json",
        "query_tool_failed.json",
        "query_all_failed.json",
        "query_round_limit.json",
    ],
)
def test_scenarios_are_deterministic(scenario: str) -> None:
    """同一 scenario 重复回放，工具调用序列一致（确定性）。"""
    routes = {
        STOCK_PATH: (200, _stock_payload([{"goodsId": "G1"}], 1)),
        EXP_PATH: (200, _stock_payload([{"goodsId": "G2"}], 1)),
        NOUP_PATH: (200, {"code": 10000, "message": "ok", "data": []}),
        TREND_UP_PATH: (
            200,
            {"code": 10000, "message": "ok", "data": [{"goodsName": "商品A"}]},
        ),
    }

    def run_once() -> list[dict[str, Any]]:
        app, _provider, _captured = _build_app(scenario, routes)
        with TestClient(app) as client:
            response = client.post(
                "/agent/query", json={"query": "回放"}, headers=_headers()
            )
        calls = response.json()["data"]["toolCalls"]
        # durationMs 是真实耗时，两次回放必然可能差 1ms；只比对确定性字段
        return [
            {k: v for k, v in call.items() if k != "durationMs"} for call in calls
        ]

    assert run_once() == run_once()
