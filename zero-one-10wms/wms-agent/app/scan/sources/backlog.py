"""待办积压数据源：经网关 GET /dashboard/query-pend-snapshot 取一致快照（阶段3）。

只调用一次快照端点（不分页）。Java 端点在 REPEATABLE READ 只读事务内一次 SQL 求出
四个队列，共用 observedAt，数值为 BigDecimal（JSON 数字或字符串都接受）。

返回的 ``SourceResult.rows`` 是按队列拆开的独立样本，每行：
``{"queueType": receipt|to_up|pick|cur_pick, "value": <数字>, "observedAt": ..., "diagnostic": bool}``。
``cur_pick`` 只做诊断，``diagnostic=True``，规则层不参与分级。

完整性策略：任何失败（超时 / 5xx 重试后仍失败 / 4xx / 响应缺队列 / 队列值为 null）
整体标 ``partial``——不会把部分队列的样本当成完整快照落库。
"""

from __future__ import annotations

import re
from typing import Any

from app.scan.sources.base import (
    RETRYABLE_STATUS, SUCCESS_CODES, SourceResult, classify_error, get_with_retry,
)
from app.tools.gateway_client import GatewayClient

SOURCE = "backlog"
ENDPOINT = "/dashboard/query-pend-snapshot"
GRADED_QUEUES: tuple[str, ...] = ("receipt", "to_up", "pick")
DIAGNOSTIC_QUEUES: tuple[str, ...] = ("cur_pick",)
ALL_QUEUES = GRADED_QUEUES + DIAGNOSTIC_QUEUES
_QUEUE_KEY = {"receipt": "receipt", "to_up": "toUp", "pick": "pick", "cur_pick": "curPick"}
# Java ``ZonedDateTime.toString()`` 形如 ``2026-11-25T13:01:08.141234900+08:00[Asia/Shanghai]``，
# 方括号区域 ID 不是 ISO 8601 的一部分，psycopg 解析 TIMESTAMPTZ 时会抛 InvalidDatetimeFormat。
_ZONE_SUFFIX = re.compile(r"\[[^\]]+\]\s*$")


def normalize_observed_at(value: Any) -> str | None:
    """规范化 observedAt：去掉 ``[Asia/Shanghai]`` 区域后缀，保留偏移与纳秒；非字符串 → None。

    只做字符串级清洗，不做时区换算——快照时间由 Java 端给出，Python 不重新解释。
    """
    if not isinstance(value, str):
        return None
    text = _ZONE_SUFFIX.sub("", value.strip()).strip()
    if not text:
        return None
    return text


def _to_number(value: Any) -> int | float | str | None:
    """接受 JSON 数字或数字字符串；布尔/非数字 → None（调用方按失败处理）。"""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return None


def parse_snapshot(data: Any) -> list[dict[str, Any]] | None:
    """把快照响应拆成四个队列样本；缺字段 / 值非法返回 None（整体失败）。"""
    if not isinstance(data, dict):
        return None
    observed_at = normalize_observed_at(data.get("observedAt"))
    if not observed_at:
        return None
    rows: list[dict[str, Any]] = []
    for queue in ALL_QUEUES:
        block = data.get(_QUEUE_KEY[queue])
        if not isinstance(block, dict):
            return None
        value = _to_number(block.get("value"))
        if value is None:
            return None
        rows.append({
            "queueType": queue,
            "value": value,
            "observedAt": observed_at,
            "diagnostic": queue in DIAGNOSTIC_QUEUES,
        })
    return rows


async def fetch_backlog(
    client: GatewayClient,
    token: str,
    *,
    page_size: int = 100,
    max_pages: int = 20,
    source_budget_seconds: float = 30.0,
) -> SourceResult:
    """取一次待办队列一致快照；不分页（page_size/max_pages 仅为 HANDLERS 签名兼容）。"""
    result = SourceResult(source=SOURCE, endpoint=ENDPOINT)
    response, error = await get_with_retry(client, ENDPOINT, {}, token)
    if response is None:
        status, summary = classify_error(None, error or "unknown")
        result.fail(status, summary)
        return result

    status_code = response.status_code
    payload = response.payload or {}
    code = payload.get("code")
    if status_code >= 400 or code not in SUCCESS_CODES:
        result.fail("error" if status_code < 500 else "error", f"http_{status_code}" if status_code >= 400 else f"code_{code}")
        return result

    rows = parse_snapshot(payload.get("data"))
    if rows is None:
        result.fail("partial", "invalid_snapshot_payload")
        return result

    result.rows = rows
    result.pages = 1
    return result
