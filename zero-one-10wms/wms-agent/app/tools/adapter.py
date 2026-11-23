"""工具适配层：统一参数 → Java 端点参数，返回归一化。

对应实施方案 §7.2 / §7.3：
- 参数命名两套（驼峰 / 下划线）在本层统一映射；
- 返回统一为 {rows, total, empty}；
- Java 的 code=9999（DASH-TREND「查询数据不存在」）转成空结果，不算失败；
- 9995 参数错误、9994 运行时错误不重试；超时与 5xx 标记 retryable，但 v1 只执行 1 次。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.tools.gateway_client import (
    GatewayClient,
    GatewayResponse,
    GatewayTimeoutError,
    GatewayTransportError,
)
from app.tools.registry import (
    TOOL_DASH_PEND,
    TOOL_DASH_TREND,
    TOOL_DAYCHECK_NOUP,
    TOOL_EXP_WARN_QUERY,
    TOOL_STOCK_QUERY,
    TREND_ENDPOINTS,
    ToolDefinition,
    get_tool,
)

CODE_SUCCESS = 10000
CODE_NOT_FOUND = 9999
CODE_PARAMS_INVALID = 9995
CODE_RUNTIME_ERROR = 9994

STATUS_SUCCESS = "success"
STATUS_EMPTY = "empty"
STATUS_ERROR = "error"

TREND_COUNT_MIN = 1
TREND_COUNT_MAX = 30

# 统一参数 → Java 参数
FIELD_MAPS: dict[str, dict[str, str]] = {
    TOOL_STOCK_QUERY: {
        "location_code": "kuWeiBianMa",
        "pallet_id": "binId",
        "customer_code": "cusCode",
        "customer_name": "zhongWenQch",
        "goods_code": "goodsCode",
        "goods_name": "shpMingCheng",
    },
    TOOL_EXP_WARN_QUERY: {
        "customer_code": "cusCode",
        "customer_name": "zhongWenQch",
        "goods_code": "goodsId",
        "goods_name": "shpMingCheng",
    },
    TOOL_DAYCHECK_NOUP: {
        "location_code": "bin_id",
        "pallet_id": "tin_id",
        "customer_code": "cus_code",
        "customer_name": "zhong_wen_qch",
        "goods_code": "goods_id",
        "goods_name": "shp_ming_cheng",
    },
}


class ToolParameterError(ValueError):
    """工具参数非法。"""


@dataclass
class ToolResult:
    """一次工具调用的归一化结果。"""

    tool: str
    endpoint: str
    status: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    total: int = 0
    error_code: int | None = None
    error_message: str | None = None
    retryable: bool = False
    duration_ms: int = 0
    attempt: int = 1
    result_digest: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """是否是一次成功（含空结果）的调用。"""
        return self.status in {STATUS_SUCCESS, STATUS_EMPTY}


def _digest(rows: list[dict[str, Any]]) -> str:
    """结果摘要（不落原文）。"""
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def prepare_call(tool_name: str, raw_params: dict[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    """校验统一参数并映射成 Java 端点参数。

    返回 (查询参数, 备注列表)。
    """
    tool = get_tool(tool_name)
    params = raw_params or {}
    try:
        validated = tool.params_model.model_validate(params)
    except ValidationError as exc:
        raise ToolParameterError(str(exc)) from exc

    data = validated.model_dump()
    notes: list[str] = []
    query: dict[str, Any] = {}

    if tool_name == TOOL_DASH_TREND:
        metric = data["metric"]
        count = int(data["count"])
        clamped = max(TREND_COUNT_MIN, min(TREND_COUNT_MAX, count))
        if clamped != count:
            notes.append(f"count 由 {count} 截断为 {clamped}")
        query["count"] = clamped
        return query, notes

    if tool_name == TOOL_DASH_PEND:
        return query, notes

    query["pageIndex"] = data["page_index"]
    query["pageSize"] = data["page_size"]

    for unified, java_name in FIELD_MAPS.get(tool_name, {}).items():
        value = data.get(unified)
        if value is not None:
            query[java_name] = value

    return query, notes


def _extract_rows(tool_name: str, data: Any) -> tuple[list[dict[str, Any]], int]:
    """从成功响应里抽取 rows 与 total。"""
    if tool_name == TOOL_DAYCHECK_NOUP:
        rows = [r for r in (data or []) if isinstance(r, dict)]
        return rows, len(rows)

    if tool_name == TOOL_DASH_PEND:
        if not isinstance(data, dict):
            return [], 0
        return (
            [
                {
                    "goodsStatus": data.get("goodsStatus"),
                    "goodsNumber": data.get("goodsNumber"),
                }
            ],
            1,
        )

    if isinstance(data, list):
        rows = [r for r in data if isinstance(r, dict)]
        return rows, len(rows)

    if isinstance(data, dict):
        raw_rows = data.get("rows")
        rows = [r for r in (raw_rows or []) if isinstance(r, dict)]
        total = data.get("total")
        if not isinstance(total, int):
            total = len(rows)
        return rows, total

    return [], 0


def normalize(
    tool_name: str,
    endpoint: str,
    response: GatewayResponse,
    *,
    attempt: int = 1,
    notes: list[str] | None = None,
) -> ToolResult:
    """把网关响应归一化成 ToolResult。"""
    result_notes = list(notes or [])

    if response.status_code >= 400:
        return ToolResult(
            tool=tool_name,
            endpoint=endpoint,
            status=STATUS_ERROR,
            error_code=response.status_code,
            error_message=f"gateway http {response.status_code}",
            retryable=response.status_code >= 500 or response.status_code == 429,
            duration_ms=response.duration_ms,
            attempt=attempt,
            result_digest=_digest([]),
            notes=result_notes,
        )

    payload = response.payload
    if payload is None:
        return ToolResult(
            tool=tool_name,
            endpoint=endpoint,
            status=STATUS_ERROR,
            error_message="gateway 返回空响应体",
            retryable=False,
            duration_ms=response.duration_ms,
            attempt=attempt,
            result_digest=_digest([]),
            notes=result_notes,
        )

    code = payload.get("code")
    message = payload.get("message")
    data = payload.get("data")

    if code == CODE_SUCCESS:
        rows, total = _extract_rows(tool_name, data)
        return ToolResult(
            tool=tool_name,
            endpoint=endpoint,
            status=STATUS_EMPTY if not rows else STATUS_SUCCESS,
            rows=rows,
            total=total,
            duration_ms=response.duration_ms,
            attempt=attempt,
            result_digest=_digest(rows),
            notes=result_notes,
        )

    if code == CODE_NOT_FOUND and tool_name == TOOL_DASH_TREND:
        result_notes.append("Java 返回 9999「查询数据不存在」，按空结果处理")
        return ToolResult(
            tool=tool_name,
            endpoint=endpoint,
            status=STATUS_EMPTY,
            rows=[],
            total=0,
            duration_ms=response.duration_ms,
            attempt=attempt,
            result_digest=_digest([]),
            notes=result_notes,
        )

    return ToolResult(
        tool=tool_name,
        endpoint=endpoint,
        status=STATUS_ERROR,
        error_code=code if isinstance(code, int) else None,
        error_message=str(message) if message else f"业务错误 code={code}",
        retryable=False,
        duration_ms=response.duration_ms,
        attempt=attempt,
        result_digest=_digest([]),
        notes=result_notes,
    )


def _error_result(
    tool_name: str, endpoint: str, exc: Exception, *, attempt: int, notes: list[str]
) -> ToolResult:
    """网络异常归一化。"""
    retryable = isinstance(exc, (GatewayTimeoutError, GatewayTransportError))
    message = (
        "网关调用超时" if isinstance(exc, GatewayTimeoutError) else "网关调用网络异常"
    )
    return ToolResult(
        tool=tool_name,
        endpoint=endpoint,
        status=STATUS_ERROR,
        error_message=message,
        retryable=retryable,
        attempt=attempt,
        result_digest=_digest([]),
        notes=notes,
    )


async def execute_tool(
    tool: ToolDefinition,
    raw_params: dict[str, Any] | None,
    client: GatewayClient,
    *,
    token: str | None = None,
    attempt: int = 1,
) -> ToolResult:
    """执行一次工具调用（v1 只尝试 1 次，不自动重试）。"""
    query, notes = prepare_call(tool.name, raw_params)

    if tool.name == TOOL_DASH_PEND:
        return await _execute_pend(tool, client, token=token, attempt=attempt, notes=notes)

    if tool.name == TOOL_DASH_TREND:
        metric = (raw_params or {}).get("metric")
        endpoint = TREND_ENDPOINTS.get(str(metric))
        if endpoint is None:
            raise ToolParameterError(f"unknown metric: {metric}")
    else:
        endpoint = tool.endpoints[0]

    try:
        response = await client.get(endpoint, query, token=token)
    except (GatewayTimeoutError, GatewayTransportError) as exc:
        return _error_result(tool.name, endpoint, exc, attempt=attempt, notes=notes)

    return normalize(tool.name, endpoint, response, attempt=attempt, notes=notes)


async def _execute_pend(
    tool: ToolDefinition,
    client: GatewayClient,
    *,
    token: str | None,
    attempt: int,
    notes: list[str],
) -> ToolResult:
    """DASH-PEND：并发调用 4 个计数端点并聚合。"""
    results = await asyncio.gather(
        *(
            client.get(endpoint, {}, token=token)
            for endpoint in tool.endpoints
        ),
        return_exceptions=True,
    )

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    duration_ms = 0
    for endpoint, outcome in zip(tool.endpoints, results):
        if isinstance(outcome, Exception):
            failures.append(f"{endpoint}: {type(outcome).__name__}")
            continue
        duration_ms = max(duration_ms, outcome.duration_ms)
        if outcome.status_code >= 400 or outcome.payload is None:
            failures.append(f"{endpoint}: http {outcome.status_code}")
            continue
        payload = outcome.payload
        if payload.get("code") != CODE_SUCCESS:
            failures.append(f"{endpoint}: code={payload.get('code')}")
            continue
        data = payload.get("data") or {}
        rows.append(
            {
                "endpoint": endpoint,
                "goodsStatus": data.get("goodsStatus"),
                "goodsNumber": data.get("goodsNumber"),
            }
        )

    all_notes = list(notes)
    if failures:
        all_notes.append("部分端点失败：" + "；".join(failures))

    if not rows:
        return ToolResult(
            tool=tool.name,
            endpoint=",".join(tool.endpoints),
            status=STATUS_ERROR,
            error_message="待办计数端点全部失败" if failures else "待办计数无数据",
            retryable=False,
            duration_ms=duration_ms,
            attempt=attempt,
            result_digest=_digest([]),
            notes=all_notes,
        )

    return ToolResult(
        tool=tool.name,
        endpoint=",".join(tool.endpoints),
        status=STATUS_EMPTY
        if all(str(r.get("goodsNumber")) == "0" for r in rows)
        else STATUS_SUCCESS,
        rows=rows,
        total=len(rows),
        duration_ms=duration_ms,
        attempt=attempt,
        result_digest=_digest(rows),
        notes=all_notes,
    )
