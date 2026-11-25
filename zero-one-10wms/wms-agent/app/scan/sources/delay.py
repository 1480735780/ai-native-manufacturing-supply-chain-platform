"""进货延时数据源：经网关 GET /daycheck/delay/im-delay 分页取数。

Java 端点返回 `JsonVO<PageDTO<WaringAllDTO>>`，已支持 `sort=oldest`。
字段：noticeId、supName、imData（计划到货时间）、imCarDri/imCarMobile/
imCarNo（司机/车号，evidence 需脱敏）、createDate 等。

完整性策略与 expiry 一致（方案 §7.2/§7.4）：5xx/超时重试 1 次，4xx 不重试，
按 noticeId 去重，任一页失败/总数不一致/翻页漂移标 partial。
"""

from __future__ import annotations

from typing import Any

from app.scan.sources.base import SourceResult, fetch_paged
from app.tools.gateway_client import GatewayClient

SOURCE = "delay"
ENDPOINT = "/daycheck/delay/im-delay"


def _row_key(row: dict[str, Any]) -> str:
    notice = row.get("noticeId") or row.get("notice_id")
    if notice:
        return "notice:" + str(notice)
    return "|".join(str(row.get(k) or "") for k in ("supName", "imData", "imCarNo"))


async def fetch_delay(
    client: GatewayClient,
    token: str,
    *,
    page_size: int = 100,
    max_pages: int = 20,
    source_budget_seconds: float = 30.0,
) -> SourceResult:
    """分页拉取进货延时行，按通知单号去重；任一页失败标 partial。"""
    return await fetch_paged(
        client, token,
        source=SOURCE, endpoint=ENDPOINT,
        page_size=page_size, max_pages=max_pages,
        source_budget_seconds=source_budget_seconds,
        row_key=_row_key, sort="oldest",
    )