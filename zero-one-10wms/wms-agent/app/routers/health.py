"""健康检查：匿名、返回固定最小响应。

ADR-015 要求 `/agent/health` 不套 JsonVO 外壳，只返回 `{"status":"ok"}`，
不泄露 Python 版本、依赖版本、PG 状态、网关状态或内部路径。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """返回固定最小健康响应。"""
    return {"status": "ok"}
