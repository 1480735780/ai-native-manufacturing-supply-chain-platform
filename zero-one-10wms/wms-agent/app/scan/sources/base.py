"""数据源通用返回结构与取数公共逻辑（分页 + 完整性校验）。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.tools.gateway_client import (
    GatewayClient,
    GatewayResponse,
    GatewayTimeoutError,
    GatewayTransportError,
)

RETRYABLE_STATUS = {500, 502, 503, 504}
SUCCESS_CODES = (0, 10000, None)


@dataclass
class SourceResult:
    """一次取数的结果（含状态摘要）。"""

    source: str
    endpoint: str
    status: str = "ok"  # ok | partial | timeout | error
    rows: list[dict[str, Any]] = field(default_factory=list)
    pages: int = 0
    truncated: bool = False
    error_summary: str | None = None
    # 取数耗时（毫秒）。由 service 层在调用处统一计时回填；历史扫描没有该值（None）。
    duration_ms: int | None = None

    def to_status(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "endpoint": self.endpoint,
            "status": self.status,
            "rows": len(self.rows),
            "pages": self.pages,
            "truncated": self.truncated,
            "errorSummary": self.error_summary,
            "durationMs": self.duration_ms,
        }

    def fail(self, status: str, error_summary: str) -> None:
        """标记取数失败（截断，不静默丢数据）。"""
        self.status = status
        self.error_summary = error_summary
        self.truncated = True


async def get_with_retry(
    client: GatewayClient,
    path: str,
    params: dict[str, Any],
    token: str,
) -> tuple[GatewayResponse | None, str | None]:
    """单次取页：5xx / 超时重试 1 次，4xx 不重试。

    返回 (response, error_summary)；response 为 None 表示重试后仍失败。
    """
    last_error: str | None = None
    for _ in range(2):  # 首次 + 1 次重试
        try:
            response = await client.get(path, params, token=token)
        except GatewayTimeoutError:
            last_error = "gateway timeout"
            continue
        except GatewayTransportError as exc:
            last_error = type(exc).__name__
            continue

        if response.status_code in RETRYABLE_STATUS:
            last_error = f"http_{response.status_code}"
            continue
        if response.status_code >= 400:
            # 4xx 明确拒绝，不重试
            return response, f"http_{response.status_code}"
        return response, None
    return None, last_error


def classify_error(response: GatewayResponse | None, error: str) -> tuple[str, str]:
    """把取页错误归到 source_status 的 (status, errorSummary)。"""
    if response is not None and response.status_code < 500:
        return "error", error
    if "timeout" in error:
        return "timeout", error
    return "error", error


def _as_int(value: Any) -> int | None:
    """PageDTO 的 total/pages：缺失或非法返回 None（不能把缺失当成 0）。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


async def fetch_paged(
    client: GatewayClient,
    token: str,
    *,
    source: str,
    endpoint: str,
    page_size: int,
    max_pages: int,
    source_budget_seconds: float,
    row_key: Callable[[dict[str, Any]], str],
    sort: str | None = None,
    require_page_dto: bool = False,
    list_payload_status: tuple[str, str] = ("error", "unexpected payload"),
) -> SourceResult:
    """按 PageDTO 逐页拉取并做完整性校验（方案 §7.2/§7.4）。

    - 5xx/超时重试 1 次，4xx 不重试；任一页失败即 partial/error，不静默截断；
    - 按稳定行键去重；终止条件：声明的 pages 走完，或累计原始行数达到 total；
    - 完成后校验一致性，任一不满足即 partial：
      * `total_missing`：拿到了行但 total/pages 都没给，无法证明取全；
      * `row_count_mismatch`：原始行数（含重复）≠ total，翻页期间数据漂移或缺页；
      * `page_drift`：任意跨页重复稳定键（服务端未按排序翻页），即使每页仍有新键；
        同一页内的重复行视为上游联表重复，允许去重后标 ok；
      * `pagination_metadata_changed`：翻页期间 total/pages 发生变化（结果集漂移）。
    """
    result = SourceResult(source=source, endpoint=endpoint)
    seen: set[str] = set()          # 已处理页的稳定键
    page_seen: set[str] = set()     # 当前页的稳定键（区分页内重复与跨页重复）
    deadline = time.monotonic() + source_budget_seconds
    raw_count = 0
    total: int | None = None
    pages_declared: int | None = None
    first_total: int | None = None
    first_pages: int | None = None
    completed = False
    exhausted = False
    drift = False
    metadata_drift = False

    for page in range(1, max_pages + 1):
        if time.monotonic() >= deadline:
            result.fail("partial", "source_budget_exceeded")
            break

        params: dict[str, Any] = {"pageIndex": page, "pageSize": page_size}
        if sort:
            params["sort"] = sort
        response, error = await get_with_retry(client, endpoint, params, token)
        if error is not None:
            status, summary = classify_error(response, error)
            result.fail(status, summary)
            break

        assert response is not None
        payload = response.payload or {}
        if payload.get("code") not in SUCCESS_CODES:
            result.fail("error", "code=" + str(payload.get("code")))
            break

        data = payload.get("data")
        if not isinstance(data, dict):
            if require_page_dto:
                # 端点异常返回裸 List：当作不可信，标 partial 不能静默当完整页。
                result.fail("partial", "unexpected_list_payload")
            else:
                result.fail(*list_payload_status)
            break

        rows = [r for r in (data.get("rows") or []) if isinstance(r, dict)]
        result.pages = page
        page_seen = set()
        for row in rows:
            key = row_key(row)
            if key:
                if key in page_seen:
                    # 同一页内重复（上游联表 COUNT 含重复行），允许去重，不算翻页漂移。
                    continue
                if key in seen:
                    # 跨页重复稳定键：服务端未按排序稳定翻页，后续行可能已被跳过，
                    # 必须标 partial，不能用原始行数匹配 total 掩盖唯一行缺失。
                    drift = True
                    continue
                page_seen.add(key)
                seen.add(key)
            result.rows.append(row)
        raw_count += len(rows)

        total = _as_int(data.get("total"))
        pages_declared = _as_int(data.get("pages"))
        if page == 1:
            first_total, first_pages = total, pages_declared
        elif total != first_total or pages_declared != first_pages:
            # 翻页期间总数/页数变化：结果集在漂移，不能当作完整快照。
            metadata_drift = True
        last_page = pages_declared is not None and page >= pages_declared

        if pages_declared is not None and pages_declared > 0 and page >= pages_declared:
            completed = True
            break
        if total is not None and raw_count >= total:
            completed = True
            break
        if not rows:
            # 空页：当前排序下已无数据；是否有 total 交给下面的一致性校验
            completed = True
            break
    else:
        exhausted = True

    if result.status == "ok" and result.error_summary is None:
        if drift:
            result.fail("partial", "page_drift")
        elif metadata_drift:
            result.fail("partial", "pagination_metadata_changed")
        elif exhausted or not completed:
            result.fail("partial", "max_pages_exceeded" if exhausted else "incomplete_pages")
        elif total is not None and raw_count != total:
            result.fail("partial", f"row_count_mismatch:raw={raw_count},total={total}")
        elif total is None and pages_declared is None and raw_count > 0:
            result.fail("partial", "total_missing")
    return result