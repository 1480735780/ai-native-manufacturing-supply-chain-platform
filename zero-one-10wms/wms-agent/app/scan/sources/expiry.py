"""效期数据源：经网关 GET /stock/expiry-warning/query-all 分页取数。

完整性策略（方案 §7.2）：
- 单请求超时由 GatewayClient 控制（默认 3s）；单源总预算 30s。
- 5xx / 超时重试 1 次；4xx 不重试（视为明确拒绝，直接 partial）。
- 翻页按对象键 `id` 去重；任一页失败/总数不一致/翻页漂移即标 partial，不静默丢数据。
"""

from __future__ import annotations

from typing import Any

from app.scan.sources.base import SourceResult, fetch_paged
from app.tools.gateway_client import GatewayClient

SOURCE = "expiry"
ENDPOINT = "/stock/expiry-warning/query-all"


def _row_key(row: dict[str, Any]) -> str:
    return str(row.get("id") or "")


async def fetch_expiry(
    client: GatewayClient,
    token: str,
    *,
    page_size: int = 100,
    max_pages: int = 20,
    source_budget_seconds: float = 30.0,
) -> SourceResult:
    """分页拉取效期行，按 `id` 去重；任一页失败即标 partial。"""
    return await fetch_paged(
        client, token,
        source=SOURCE, endpoint=ENDPOINT,
        page_size=page_size, max_pages=max_pages,
        source_budget_seconds=source_budget_seconds,
        row_key=_row_key,
    )