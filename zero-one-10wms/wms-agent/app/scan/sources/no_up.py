"""收货未上架数据源：经网关 GET /daycheck/no-up/get-no-up-goods-page 全量分页取数。

Java 端点（巡检专用）：返回 JsonVO<PageDTO<NoUpGoodsDTO>>，
data = {pageIndex, pageSize, total, pages, rows:[...]}，每行带稳定行键 rowId
（wm_in_qm_i 主键）与 noticeId；只取未上架（巡检口径在 Java 语句里显式定义）。
旧端点 /daycheck/no-up/get-no-up-goods 仍返回裸 List，契约不变，本数据源不用它。

完整性策略（方案 §7.2/§7.4）：显式 sort=oldest 固定顺序；按 rowId 去重；
单源预算 30s、max_pages 上限；任一分页失败/总数不一致/翻页漂移即 partial，
不静默截断（见 sources/base.fetch_paged）。
"""

from __future__ import annotations

from typing import Any

from app.scan.sources.base import SourceResult, fetch_paged
from app.tools.gateway_client import GatewayClient

SOURCE = "no_up"
ENDPOINT = "/daycheck/no-up/get-no-up-goods-page"


def _row_key(row: dict[str, Any]) -> str:
    """稳定行键：优先 rowId，缺失时回退业务组合键。"""
    row_id = row.get("rowId") or row.get("row_id")
    if row_id:
        return "row:" + str(row_id)
    return "|".join(
        str(row.get(k) or "") for k in ("noticeId", "goods_id", "bin_id", "create_date")
    )


async def fetch_no_up(
    client: GatewayClient,
    token: str,
    *,
    page_size: int = 100,
    max_pages: int = 20,
    source_budget_seconds: float = 30.0,
) -> SourceResult:
    """按 PageDTO 分页完整拉取未上架行；逐页累加，按 pages/total 终止并校验一致性。"""
    return await fetch_paged(
        client, token,
        source=SOURCE, endpoint=ENDPOINT,
        page_size=page_size, max_pages=max_pages,
        source_budget_seconds=source_budget_seconds,
        row_key=_row_key, sort="oldest", require_page_dto=True,
    )