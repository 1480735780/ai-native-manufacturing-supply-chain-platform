"""Gateway 只读调用客户端。

只发 GET，透传原始用户 JWT（ADR-007 §工具调用）。
所有网络异常都转成明确异常类型，供上层判定 retryable。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping

import httpx


@dataclass(frozen=True)
class GatewayResponse:
    """一次网关调用的结果。"""

    status_code: int
    payload: dict[str, Any] | None
    duration_ms: int


class GatewayTimeoutError(RuntimeError):
    """网关调用超时。"""


class GatewayTransportError(RuntimeError):
    """网关调用网络异常。"""


class GatewayClient:
    """访问 wms-gateway 的最小客户端。"""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 3.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def with_timeout(self, timeout_seconds: float) -> GatewayClient:
        """为一次扫描创建独立超时配置，保留测试注入的 transport。"""
        return GatewayClient(
            self.base_url,
            timeout_seconds=timeout_seconds,
            transport=self._transport,
        )

    async def get(
        self,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        token: str | None = None,
    ) -> GatewayResponse:
        """发起一次 GET 调用。"""
        query = {k: v for k, v in (params or {}).items() if v is not None}
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, transport=self._transport
            ) as client:
                response = await client.get(
                    f"{self.base_url}{path}", params=query, headers=headers
                )
        except httpx.TimeoutException as exc:
            raise GatewayTimeoutError(f"gateway timeout: {path}") from exc
        except httpx.HTTPError as exc:
            raise GatewayTransportError(
                f"gateway transport error: {path} ({type(exc).__name__})"
            ) from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        payload: dict[str, Any] | None = None
        if response.status_code < 400:
            try:
                body = response.json()
            except ValueError:
                body = None
            if isinstance(body, dict):
                payload = body
        return GatewayResponse(
            status_code=response.status_code,
            payload=payload,
            duration_ms=duration_ms,
        )
