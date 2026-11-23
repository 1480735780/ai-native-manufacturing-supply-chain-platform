"""F-009：6 个只读工具的参数映射、返回归一化、脱敏与并发聚合。"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.tools.adapter import (
    STATUS_EMPTY,
    STATUS_ERROR,
    STATUS_SUCCESS,
    ToolParameterError,
    execute_tool,
    normalize,
    prepare_call,
)
from app.tools.gateway_client import GatewayClient, GatewayResponse
from app.tools.registry import TOOLS, get_tool, list_tools, tool_schemas
from app.tools.sanitizer import build_llm_payload, sanitize_rows


def _transport(handler_map: dict[str, Any], default: Any = None) -> httpx.MockTransport:
    """按路径返回预置响应的 MockTransport。"""

    def handler(request: httpx.Request) -> httpx.Response:
        spec = handler_map.get(request.url.path, default)
        if spec is None:
            return httpx.Response(
                404, json={"code": 404, "message": "not found", "data": None}
            )
        if isinstance(spec, Exception):
            raise spec
        if callable(spec):
            return spec(request)
        return httpx.Response(200, json=spec)

    return httpx.MockTransport(handler)


def _client(handler_map: dict[str, Any], default: Any = None) -> GatewayClient:
    return GatewayClient(
        "http://gateway.invalid", transport=_transport(handler_map, default)
    )


# ------------------------------------------------------------- 参数映射


def test_prepare_call_maps_camel_case_for_stock():
    query, notes = prepare_call(
        "STOCK-QUERY",
        {
            "page_index": 1,
            "page_size": 20,
            "location_code": "A-01",
            "pallet_id": "P1",
            "customer_code": "C1",
            "customer_name": "客户甲",
            "goods_code": "G1",
            "goods_name": "商品甲",
        },
    )
    assert query == {
        "pageIndex": 1,
        "pageSize": 20,
        "kuWeiBianMa": "A-01",
        "binId": "P1",
        "cusCode": "C1",
        "zhongWenQch": "客户甲",
        "goodsCode": "G1",
        "shpMingCheng": "商品甲",
    }
    assert notes == []


def test_prepare_call_maps_underscore_for_no_up():
    query, _ = prepare_call(
        "DAYCHECK-NOUP",
        {
            "page_index": 2,
            "page_size": 10,
            "location_code": "A-01",
            "pallet_id": "T9",
            "customer_code": "C1",
            "customer_name": "客户甲",
            "goods_code": "G1",
            "goods_name": "商品甲",
        },
    )
    assert query == {
        "pageIndex": 2,
        "pageSize": 10,
        "bin_id": "A-01",
        "tin_id": "T9",
        "cus_code": "C1",
        "zhong_wen_qch": "客户甲",
        "goods_id": "G1",
        "shp_ming_cheng": "商品甲",
    }


def test_prepare_call_maps_expiry_warning_goods_id():
    query, _ = prepare_call("EXP-WARN-QUERY", {"goods_code": "G1"})
    assert query == {"pageIndex": 1, "pageSize": 20, "goodsId": "G1"}


def test_prepare_call_delay_only_takes_paging():
    query, _ = prepare_call("DAYCHECK-DELAY", {"page_index": 3})
    assert query == {"pageIndex": 3, "pageSize": 20}


def test_prepare_call_pend_takes_no_params():
    query, _ = prepare_call("DASH-PEND", {})
    assert query == {}


def test_prepare_call_trend_clamps_count_and_records_note():
    query, notes = prepare_call("DASH-TREND", {"metric": "up_top", "count": 40})
    assert query == {"count": 30}
    assert notes and "40" in notes[0] and "30" in notes[0]

    query, notes = prepare_call("DASH-TREND", {"metric": "up_recent_days", "count": 0})
    assert query == {"count": 1}
    assert notes


def test_prepare_call_rejects_unknown_parameter():
    with pytest.raises(ToolParameterError):
        prepare_call("STOCK-QUERY", {"unknown_param": "x"})


def test_prepare_call_rejects_invalid_metric():
    with pytest.raises(ToolParameterError):
        prepare_call("DASH-TREND", {"metric": "sideways"})


# ----------------------------------------------------------- 返回归一化


def test_normalize_stock_null_rows_becomes_empty():
    response = GatewayResponse(
        status_code=200, payload={"code": 10000, "message": "ok", "data": {"rows": None}}, duration_ms=3
    )
    result = normalize("STOCK-QUERY", "/stock/inventory-query/query-all", response)
    assert result.status == STATUS_EMPTY
    assert result.rows == []
    assert result.total == 0
    assert result.ok


def test_normalize_no_up_bare_list_total_is_length():
    response = GatewayResponse(
        status_code=200,
        payload={"code": 10000, "message": "ok", "data": [{"goods_id": "1"}, {"goods_id": "2"}]},
        duration_ms=2,
    )
    result = normalize("DAYCHECK-NOUP", "/daycheck/no-up/get-no-up-goods", response)
    assert result.status == STATUS_SUCCESS
    assert result.total == 2
    assert len(result.rows) == 2


def test_normalize_trend_9999_is_empty_not_failure():
    response = GatewayResponse(
        status_code=200,
        payload={"code": 9999, "message": "查询数据不存在", "data": None},
        duration_ms=1,
    )
    result = normalize("DASH-TREND", "/dashboard/query-goods-to-up", response)
    assert result.status == STATUS_EMPTY
    assert result.ok
    assert result.error_code is None
    assert any("9999" in note for note in result.notes)


def test_normalize_params_invalid_is_not_retryable():
    response = GatewayResponse(
        status_code=200,
        payload={"code": 9995, "message": "[pageIndex]页码最小值为1", "data": None},
        duration_ms=1,
    )
    result = normalize("DAYCHECK-NOUP", "/daycheck/no-up/get-no-up-goods", response)
    assert result.status == STATUS_ERROR
    assert result.error_code == 9995
    assert result.retryable is False


def test_normalize_runtime_error_is_not_retryable():
    response = GatewayResponse(
        status_code=200,
        payload={"code": 9994, "message": "运行异常", "data": None},
        duration_ms=1,
    )
    result = normalize("STOCK-QUERY", "/stock/inventory-query/query-all", response)
    assert result.status == STATUS_ERROR
    assert result.error_code == 9994
    assert result.retryable is False


def test_normalize_http_500_is_retryable():
    result = normalize(
        "STOCK-QUERY",
        "/stock/inventory-query/query-all",
        GatewayResponse(status_code=500, payload=None, duration_ms=5),
    )
    assert result.status == STATUS_ERROR
    assert result.retryable is True


# ------------------------------------------------------------ 工具执行


async def test_execute_tool_stock_passes_token_and_query():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["query"] = dict(request.url.params)
        captured["auth"] = request.headers.get("Authorization")
        return httpx.Response(
            200,
            json={
                "code": 10000,
                "message": "ok",
                "data": {"rows": [{"goodsCode": "G1", "goodsQua": "3"}], "total": 1},
            },
        )

    client = GatewayClient("http://gateway.invalid", transport=httpx.MockTransport(handler))
    result = await execute_tool(
        get_tool("STOCK-QUERY"),
        {"page_index": 1, "page_size": 20, "goods_code": "G1"},
        client,
        token="user-jwt",
    )

    assert captured["path"] == "/stock/inventory-query/query-all"
    assert captured["query"]["goodsCode"] == "G1"
    assert captured["query"]["pageIndex"] == "1"
    assert captured["auth"] == "Bearer user-jwt"
    assert result.status == STATUS_SUCCESS
    assert result.total == 1
    assert result.result_digest
    assert result.duration_ms >= 0


async def test_execute_tool_timeout_is_retryable_but_single_attempt():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client = GatewayClient("http://gateway.invalid", transport=httpx.MockTransport(handler))
    result = await execute_tool(
        get_tool("STOCK-QUERY"), {}, client, token="user-jwt"
    )
    assert result.status == STATUS_ERROR
    assert result.retryable is True
    assert result.attempt == 1


async def test_execute_dash_pend_aggregates_four_endpoints():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        number = "0" if request.url.path.endswith("query-pend-receipt") else "5"
        return httpx.Response(
            200,
            json={
                "code": 10000,
                "message": "ok",
                "data": {"goodsStatus": "待处理", "goodsNumber": number},
            },
        )

    client = GatewayClient("http://gateway.invalid", transport=httpx.MockTransport(handler))
    result = await execute_tool(get_tool("DASH-PEND"), {}, client, token="user-jwt")

    assert sorted(seen) == sorted(
        [
            "/dashboard/query-pend-receipt",
            "/dashboard/query-pend-to-up",
            "/dashboard/query-pend-pick",
            "/dashboard/query-cur-pick",
        ]
    )
    assert len(result.rows) == 4
    assert result.total == 4
    assert result.status == STATUS_SUCCESS


async def test_execute_dash_pend_all_zero_is_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 10000,
                "message": "ok",
                "data": {"goodsStatus": "无", "goodsNumber": "0"},
            },
        )

    client = GatewayClient("http://gateway.invalid", transport=httpx.MockTransport(handler))
    result = await execute_tool(get_tool("DASH-PEND"), {}, client, token="user-jwt")
    assert result.status == STATUS_EMPTY
    assert result.total == 4


async def test_execute_dash_trend_uses_metric_endpoint():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["count"] = request.url.params.get("count")
        return httpx.Response(
            200, json={"code": 9999, "message": "查询数据不存在", "data": None}
        )

    client = GatewayClient("http://gateway.invalid", transport=httpx.MockTransport(handler))
    result = await execute_tool(
        get_tool("DASH-TREND"),
        {"metric": "down_recent_days", "count": 7},
        client,
        token="user-jwt",
    )
    assert captured["path"] == "/dashboard/query-goods-to-down-in-recent-days"
    assert captured["count"] == "7"
    assert result.status == STATUS_EMPTY


# ------------------------------------------------------------- 脱敏裁剪


def test_sanitize_rows_masks_delay_fields_and_drops_audit_fields():
    rows = [
        {
            "imCarMobile": "13812345678",
            "imCarDri": "王小明",
            "createName": "张三",
            "createDate": "2026-01-01",
            "noticeId": "n-1",
            "supName": "供应商甲",
        }
    ]
    sanitized = sanitize_rows("DAYCHECK-DELAY", rows)
    assert sanitized[0]["imCarMobile"] == "138****5678"
    assert sanitized[0]["imCarDri"] == "王*"
    assert "createName" not in sanitized[0]
    assert "noticeId" not in sanitized[0]
    assert sanitized[0]["supName"] == "供应商甲"


def test_sanitize_rows_drops_volume_fields_for_stock():
    rows = [{"goodsCode": "G1", "tiJiCm": "1.2", "quHuoCiXu": "3", "goodsQua": "5"}]
    sanitized = sanitize_rows("STOCK-QUERY", rows)
    assert sanitized == [{"goodsCode": "G1", "goodsQua": "5"}]


def test_build_llm_payload_limits_rows_and_chars():
    rows = [{"goodsCode": f"G{i}", "goodsName": "x" * 500} for i in range(30)]
    payload = build_llm_payload("STOCK-QUERY", rows, total=30)
    assert len(payload["rows"]) == 20
    assert payload["total"] == 30
    assert payload["truncated"] is True
    assert len(payload["text"]) <= 4100


# --------------------------------------------------------------- 工具清单


def test_six_tools_are_registered_and_read_only():
    assert len(list_tools()) == 6
    assert all(tool.read_only for tool in list_tools())
    assert {tool.name for tool in list_tools()} == set(TOOLS)


def test_tool_schemas_expose_unified_snake_case_parameters():
    schemas = {schema.name: schema for schema in tool_schemas()}
    stock = schemas["STOCK-QUERY"].parameters
    assert "location_code" in stock["properties"]
    assert "page_index" in stock["properties"]
    trend = schemas["DASH-TREND"].parameters
    assert "metric" in trend["properties"]
    assert "count" in trend["properties"]
