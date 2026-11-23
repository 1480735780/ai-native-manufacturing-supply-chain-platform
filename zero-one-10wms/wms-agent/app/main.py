"""FastAPI 应用入口。

已挂载：
- `GET /agent/health`（匿名，F-006）
- `GET /agent/tools`（需合法 JWT，F-009）
- `POST /agent/query`（需合法 JWT，F-010）
- `GET /agent/trace/{traceId}`（需合法 JWT，F-010）
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import health, query, tools
from app.security import AuthError
from app.storage import build_store

logger = logging.getLogger(__name__)

CODE_PARAMS_INVALID = 9995


def create_app() -> FastAPI:
    """构造并返回应用实例。"""
    settings = get_settings()
    store = build_store(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """启动时确保 PG schema 存在；失败只告警，不阻塞服务。"""
        ensure_schema = getattr(app.state.store, "ensure_schema", None)
        if ensure_schema is not None:
            try:
                logger.info("storage schema ready: %s", await ensure_schema())
            except Exception as exc:  # noqa: BLE001 - 建表失败不影响服务
                logger.warning("ensure storage schema failed: %s", type(exc).__name__)
        yield

    app = FastAPI(title="WMS Agent", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store
    app.include_router(health.router, prefix="/agent")
    app.include_router(tools.router, prefix="/agent")
    app.include_router(query.router, prefix="/agent")

    @app.exception_handler(AuthError)
    async def _auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
        """鉴权失败统一返回 401 外壳。"""
        return JSONResponse(
            status_code=401,
            content={"code": 401, "message": exc.message, "data": None},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """参数非法统一返回 9995 外壳，与 Java 侧语义一致。"""
        details = exc.errors()
        message = "参数校验失败"
        if details:
            first = details[0]
            location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
            message = f"{location}: {first.get('msg', '参数校验失败')}" if location else str(
                first.get("msg", message)
            )
        return JSONResponse(
            status_code=200,
            content={"code": CODE_PARAMS_INVALID, "message": message, "data": None},
        )

    return app


app = create_app()
