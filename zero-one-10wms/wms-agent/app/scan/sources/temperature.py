"""温度数据数据源（F-016 v0.2.1）：经网关 GET /daycheck/temperature/query 分页取数。

Java 端点返回 JsonVO<PageDTO<TemperatureVO>>：
data = {pageIndex, pageSize, total, pages, rows:[...]}；每行含 wenduDd（地点）、
wenduCjsj（采集时间）、wenduZhi（摄氏度）、createDate（录入时间，仅审计）、id。
服务端 SQL 已按 wendu_cjsj + id 稳定排序；本数据源只做完整分页取数，不做判定。

require_page_dto=True：端点若返回裸 List 视为不可信，标 partial，不静默截断。
"""

from __future__ import annotations

from typing import Any

from app.scan.sources.base import SourceResult, fetch_paged
from app.tools.gateway_client import GatewayClient

SOURCE = "temperature"
ENDPOINT = "/daycheck/temperature/query"


def _row_key(row: dict[str, Any]) -> str:
    """稳定行键：优先 id，其次 createDate+地点+采集时间组合。"""
    row_id = row.get("id") or row.get("rowId") or row.get("row_id")
    if row_id:
        return "row:" + str(row_id)
    return "|".join(
        str(row.get(k) or "") for k in ("createDate", "create_date", "wenduDd", "wenduCjsj")
    )


async def fetch_temperature(
    client: GatewayClient,
    token: str,
    *,
    page_size: int = 100,
    max_pages: int = 20,
    source_budget_seconds: float = 30.0,
) -> SourceResult:
    """按 PageDTO 分页完整拉取温度行；逐页累加并校验一致性。"""
    return await fetch_paged(
        client, token,
        source=SOURCE, endpoint=ENDPOINT,
        page_size=page_size, max_pages=max_pages,
        source_budget_seconds=source_budget_seconds,
        row_key=_row_key, require_page_dto=True,
    )
