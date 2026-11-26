"""出货异常数据源（F-016 v0.2.1）：经网关 GET /daycheck/yi-chang/get-yichang-down-page 分页取数。

Java 巡检端点返回 JsonVO<PageDTO<YichangDownDTO>>：
data = {pageIndex, pageSize, total, pages, rows:[...]}；每行带稳定行键 rowId
（wm_to_down_goods.id）。服务端 SQL 已按 create_date + id 稳定排序，并带“候选谓词”：
只排除「双方均为合法数字且数值相等」的行，NULL / 非法串 / 数值不等的行全部保留，
交给规则侧用 Decimal 判定并记录数据质量。本数据源不重复做数量过滤。

旧端点 /daycheck/yi-chang/get-yichang-down 仍返回裸 List，契约不变，本数据源不用它。
显式 sort=oldest 固定顺序；require_page_dto=True 防止旧裸 List 被误当作完整快照。

截断语义（审计 m01655）：候选谓词把全历史压到只剩真实候选，但候选仍可能超过
page_size × max_pages。此时 fetch_paged 返回 status=partial + max_pages_exceeded，
编排层据此置 run.partial、禁止自动关闭并产出 SCAN-PARTIAL 告警——即“数据没取全”
会显式暴露，不会静默当成“没有异常”。
"""

from __future__ import annotations

from typing import Any

from app.scan.sources.base import SourceResult, fetch_paged
from app.tools.gateway_client import GatewayClient

SOURCE = "outbound"
ENDPOINT = "/daycheck/yi-chang/get-yichang-down-page"


def _row_key(row: dict[str, Any]) -> str:
    """稳定行键：优先 rowId，缺失时回退业务组合键。"""
    row_id = row.get("rowId") or row.get("row_id")
    if row_id:
        return "row:" + str(row_id)
    return "|".join(
        str(row.get(k) or "") for k in ("bin_id_to", "goods_id", "cus_code", "create_date")
    )


async def fetch_outbound(
    client: GatewayClient,
    token: str,
    *,
    page_size: int = 100,
    max_pages: int = 50,
    source_budget_seconds: float = 30.0,
) -> SourceResult:
    """按 PageDTO 分页完整拉取出货异常行；逐页累加并校验一致性。"""
    return await fetch_paged(
        client, token,
        source=SOURCE, endpoint=ENDPOINT,
        page_size=page_size, max_pages=max_pages,
        source_budget_seconds=source_budget_seconds,
        row_key=_row_key, sort="oldest", require_page_dto=True,
    )
