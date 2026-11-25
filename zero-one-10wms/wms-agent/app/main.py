"""FastAPI 应用入口。

已挂载：
- `GET /agent/health`（匿名，F-006）
- `GET /agent/tools`（需合法 JWT，F-009）
- `POST /agent/query`（需合法 JWT，F-010）
- `GET /agent/trace/{traceId}`（需合法 JWT，F-010）
- `POST /agent/scan`、`GET /agent/scans/{id}`、`POST /agent/scans/{id}/retry`、
  `GET /agent/alerts`、`POST /agent/alerts/{id}/{ack,resolve,ignore}`（F-015，需合法 JWT）
- 巡检配置强制单仓（多仓拒绝启动）；队列 worker 与最小内部调度随 lifespan 启停
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import ensure_single_scan_warehouse, get_settings
from app.routers import health, query, tools
from app.scan.config import load_scan_config
from app.scan.repository import ScanStoreUnavailableError, build_scan_store
from app.scan.retention import RetentionScheduler
from app.scan.router import router as scan_router
from app.scan.scheduler import ScanScheduler
from app.scan.worker import ScanWorker
from app.security import AuthError
from app.storage import build_store
from app.tools.gateway_client import GatewayClient

logger = logging.getLogger(__name__)

CODE_PARAMS_INVALID = 9995


def create_app() -> FastAPI:
    """构造并返回应用实例。"""
    settings = get_settings()
    overrides: dict[str, object] = {}
    if "scan_warehouses" in settings.model_fields_set:
        overrides["warehouses"] = settings.scan_warehouses
    notification_overrides: dict[str, object] = {}
    if "notification_mode" in settings.model_fields_set:
        notification_overrides["mode"] = settings.notification_mode
    if "alert_recipients" in settings.model_fields_set:
        notification_overrides["recipients"] = settings.alert_recipients
    if notification_overrides:
        overrides["notifications"] = notification_overrides
    scan_config = load_scan_config(settings.scan_config_path, overrides=overrides)
    # 首版强制单仓：多仓配置直接拒绝启动（数据源尚不支持按仓库过滤）
    ensure_single_scan_warehouse(list(scan_config.document.warehouses))
    settings.scan_warehouses = list(scan_config.document.warehouses)
    settings.notification_mode = scan_config.document.notifications.mode
    settings.alert_recipients = list(scan_config.document.notifications.recipients)
    store = build_store(settings)
    scan_store = build_scan_store(settings.store_backend, settings.db_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """启动时确保 PG schema 存在；巡检 store 故障则拒绝启动。"""
        for label, target in (("trace", app.state.store), ("scan", app.state.scan_store)):
            ensure_schema = getattr(target, "ensure_schema", None)
            if ensure_schema is not None:
                try:
                    logger.info("%s schema ready: %s", label, await ensure_schema())
                except ScanStoreUnavailableError:
                    if label == "scan":
                        # PG 故障拒绝：巡检依赖持久队列，不允许降级内存
                        raise
                    logger.warning("trace schema unavailable")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("ensure %s schema failed: %s", label, type(exc).__name__)

        worker = ScanWorker(
            store=app.state.scan_store,
            settings=settings,
            client=GatewayClient(
                settings.gateway_url, timeout_seconds=settings.tool_timeout_seconds
            ),
        )
        await worker.start()
        scheduler = ScanScheduler(
            store=app.state.scan_store, settings=settings,
            scan_config=app.state.scan_config,
        )
        await scheduler.start()
        # 保留与归档（ADR-020）：retention_enabled=false（默认）时 start() 只记一条日志
        retention = RetentionScheduler(store=app.state.scan_store, settings=settings)
        await retention.start()
        try:
            yield
        finally:
            await retention.stop()
            await scheduler.stop()
            await worker.stop()

    app = FastAPI(title="WMS Agent", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.scan_config = scan_config
    app.state.store = store
    app.state.scan_store = scan_store
    app.include_router(health.router, prefix="/agent")
    app.include_router(tools.router, prefix="/agent")
    app.include_router(query.router, prefix="/agent")
    app.include_router(scan_router, prefix="/agent")

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
