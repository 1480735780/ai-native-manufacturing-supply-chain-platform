"""巡检 API：`POST /agent/scan`、`GET /agent/scans/{id}`、`GET /agent/alerts` 与告警状态操作。

所有端点都需要合法 JWT（与问数 Agent 同口径）；trigger 由身份推导，请求体不能指定。
扫描持久化到队列，由 worker 异步执行，POST 立即返回 202。

权限三种独立（security.py）：trigger（发起）/ view（查看）/ handle（操作）；
告警列表与状态操作都按令牌仓库范围过滤，越权仓库一律 403。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.scan.metrics import build_metrics
from app.scan.metrics_rollup import (
    METRICS_MAX_HOURS,
    METRICS_REALTIME_HOURS,
    RollupError,
    long_window_metrics,
    run_metric_rollup,
)
from app.scan.retention import RetentionError, RetentionPolicy, run_retention
from app.scan.repository import (
    ScanStore, ScanStoreConflictError, ScanStoreUnavailableError,
)
from app.scan.schemas import AlertActionRequest, ScanRequest
from app.scan.service import (
    combined_rule_version, compute_payload_hash, compute_scan_key, compute_retry_scan_key,
    enqueue_scan, new_trace_id,
)
from app.security import (
    AuthError, Principal, can_operate_alert, can_retry_scan, can_trigger_scan,
    can_view_alerts, can_view_notifications, can_view_scan, can_view_scan_summaries, check_warehouse_scope,
    effective_warehouse_scope, is_scan_admin, is_service_account, notification_identity,
    require_principal,
)
from app.tools.gateway_client import GatewayClient

router = APIRouter()

CODE_SUCCESS = 10000
CODE_NOT_FOUND = 9999
CODE_CONFLICT = 9996
CODE_FORBIDDEN = 9997
CODE_UNAVAILABLE = 9998
CODE_PARAMS_INVALID = 9995
STATUS_QUEUED = 202


def get_scan_store(request: Request) -> ScanStore:
    return request.app.state.scan_store


def get_client(request: Request) -> GatewayClient:
    settings = request.app.state.settings
    return GatewayClient(settings.gateway_url, timeout_seconds=settings.tool_timeout_seconds)


def _get_settings(request: Request) -> Any:
    return request.app.state.settings


def _new_scan_id() -> str:
    return "scan-" + uuid.uuid4().hex[:16]


def _forbidden(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"code": CODE_FORBIDDEN, "message": message, "data": None},
    )


def _unprocessable(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"code": CODE_PARAMS_INVALID, "message": message, "data": None},
    )


def _unavailable(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"code": CODE_UNAVAILABLE, "message": "巡检存储不可用：" + str(exc), "data": None},
    )


def _warehouse_scope(principal: Principal, settings: Any) -> tuple[list[str], bool]:
    """(可见仓库列表, 是否受令牌限制)。范围为空直接拒绝，不静默放行。"""
    scope = effective_warehouse_scope(principal, settings.scan_warehouses)
    token_restricted = bool(principal.warehouse_scope)
    if not scope:
        raise AuthError("令牌仓库范围不含任何可用仓库")
    return scope, token_restricted


def _in_scope(warehouse: str | None, scope: list[str], token_restricted: bool) -> bool:
    """仓库是否可见：有令牌范围时严格要求命中；无 claim 的用户接受历史 NULL 仓库。"""
    if warehouse:
        return warehouse in scope
    return not token_restricted


METRICS_MIN_HOURS = 1
# 窗口上限 2 年（METRICS_MAX_HOURS）：90 天内（METRICS_REALTIME_HOURS）读实时数据，
# 90 天至 2 年读日聚合（ADR-020），避免无界聚合。


# response_model=None：正常返回信封字典，参数 / 存储错误返回 JSONResponse（与其它端点同形）
@router.get("/scan/metrics", response_model=None)
async def scan_metrics(
    hours: float = 24,
    warehouse: str | None = None,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
    settings: Any = Depends(_get_settings),
) -> dict[str, Any] | JSONResponse:
    """巡检指标（管理员只读）。时间窗左闭右开，口径见 app/scan/metrics.py。

    服务账号与业务角色（ckjl/cg 等）一律拒绝；仓库范围按令牌收敛，
    指定仓库必须在令牌范围内，否则不区分「不存在」与「无权」。
    """
    if is_service_account(principal) or not is_scan_admin(principal):
        return {"code": CODE_FORBIDDEN, "message": "仅管理员可查看巡检指标", "data": None}
    if not (METRICS_MIN_HOURS <= hours <= METRICS_MAX_HOURS):
        return _unprocessable(
            f"hours 必须在 {METRICS_MIN_HOURS} 到 {METRICS_MAX_HOURS} 之间"
        )
    try:
        scope, _token_restricted = _warehouse_scope(principal, settings)
    except AuthError as exc:
        return {"code": CODE_FORBIDDEN, "message": exc.message, "data": None}
    if warehouse is not None and warehouse not in scope:
        return {
            "code": CODE_FORBIDDEN,
            "message": f"无权查看仓库 {warehouse} 的巡检指标",
            "data": None,
        }
    # 即使未指定仓库也按令牌范围过滤：范围只会被收窄，不会放大。
    warehouses = [warehouse] if warehouse is not None else list(scope)
    window_to = datetime.now(timezone.utc)
    window_from = window_to - timedelta(hours=hours)
    if hours > METRICS_REALTIME_HOURS:
        # 超过实时口径上限：日聚合 + 实时尾段（先聚合再归档，归档告警不致历史指标消失）
        try:
            data = await long_window_metrics(
                store,
                window_from=window_from,
                window_to=window_to,
                warehouses=warehouses,
                timezone=str(settings.retention_timezone),
                generated_at=window_to,
            )
        except ScanStoreUnavailableError as exc:
            return _unavailable(exc)
        except RollupError as exc:
            return {"code": CODE_UNAVAILABLE, "message": str(exc), "data": None}
        return {"code": CODE_SUCCESS, "message": "ok", "data": data}
    started_from, started_to = window_from.isoformat(), window_to.isoformat()
    try:
        runs = await store.list_runs_for_metrics(
            started_from=started_from, started_to=started_to, warehouses=warehouses,
        )
        event_counts = await store.count_alert_events(
            created_from=started_from, created_to=started_to, warehouses=warehouses,
        )
        alerts = await store.list_alert_handling(
            touched_from=started_from, touched_to=started_to, warehouses=warehouses,
        )
        notification_counts = await store.count_notifications(
            created_from=started_from, created_to=started_to, warehouses=warehouses,
        )
        summary_counts = await store.aggregate_scan_summaries(
            started_from=started_from, started_to=started_to, warehouses=warehouses,
        )
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)
    data = build_metrics(
        runs=runs,
        event_counts=event_counts,
        alerts=alerts,
        notification_counts=notification_counts,
        summary_counts=summary_counts,
        window_from=window_from,
        window_to=window_to,
        generated_at=window_to,
    )
    return {"code": CODE_SUCCESS, "message": "ok", "data": data}


# response_model=None：正常返回信封字典，参数 / 存储错误返回 JSONResponse（与其它端点同形）
@router.post("/scan/metrics/rollup/run", response_model=None)
async def run_scan_metrics_rollup(
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
    settings: Any = Depends(_get_settings),
) -> dict[str, Any] | JSONResponse:
    """手动补齐指标日聚合（仅管理员；ADR-020）。

    只算最近 ``history_days`` 天里缺失的「仓库 · 日」，已有的不重算；最旧优先、每轮限批，
    报告里 ``remaining > 0`` 时需要再跑一轮。超过 90 天的指标窗口依赖这些日聚合。
    """
    if is_service_account(principal) or not is_scan_admin(principal):
        return _forbidden("仅管理员可执行指标日聚合")
    try:
        scope, _token_restricted = _warehouse_scope(principal, settings)
    except AuthError as exc:
        return _forbidden(exc.message)
    try:
        report = await run_metric_rollup(
            store,
            warehouses=list(scope),
            timezone=str(settings.retention_timezone),
        )
    except (RollupError, RetentionError) as exc:
        return _unprocessable(str(exc))
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)
    return {"code": CODE_SUCCESS, "message": "ok", "data": report}


# response_model=None：正常返回 JSONResponse 信封，存储错误返回 503 信封（与其它端点同形）
@router.post("/scan/retention/run", response_model=None)
async def run_scan_retention(
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
    settings: Any = Depends(_get_settings),
) -> JSONResponse:
    """手动执行一轮保留与归档（仅管理员；ADR-020）。

    删除类操作，同步执行并返回逐类报告（行数 / 批数 / 是否还有剩余）。策略非法时拒绝执行；
    存储故障返回 503，不把「没跑成」伪装成「删了 0 行」。每轮受 batch_size × max_batches 限制，
    报告里 moreRemaining=true 时需要再跑一轮。
    """
    if is_service_account(principal) or not is_scan_admin(principal):
        return _forbidden("仅管理员可执行保留与归档")
    policy = RetentionPolicy.from_settings(settings)
    try:
        policy.validate()
    except RetentionError as exc:
        return _unprocessable(str(exc))
    try:
        report = await run_retention(
            store,
            policy=policy,
            batch_size=int(settings.retention_batch_size),
            max_batches=int(settings.retention_max_batches),
        )
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)
    return JSONResponse(
        status_code=200,
        content={"code": CODE_SUCCESS, "message": "ok", "data": report},
    )


@router.post("/scan")
async def scan(
    request: Request,
    payload: ScanRequest,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
) -> JSONResponse:
    """发起一次巡检：写入持久队列，返回 202 queued。"""
    if not can_trigger_scan(principal):
        return _forbidden("无巡检权限")

    settings = request.app.state.settings
    # 提前校验仓库范围，越权在入队前拒绝
    try:
        warehouse = check_warehouse_scope(
            principal, payload.warehouse, settings.scan_warehouses
        )
    except AuthError as exc:
        return _forbidden(exc.message)

    # 用户 JWT 绝不入队/落库：worker 统一用服务账号短时令牌取数。
    # 非密生效配置在入队时冻结，worker 之后不读取当前 YAML。
    scan_config = request.app.state.scan_config
    chash = scan_config.config_hash
    # 请求级 dryRun 独立于服务端通知模式：不指定即 false，正常落告警。
    # notification_mode=dry_run 只影响通知投递（写 dry_run 记录不发送），
    # 不跳过告警落库，两者不再互相短路。
    dry_run = bool(payload.dryRun)

    # 持久化队列；幂等冲突返回既有扫描，PG 故障映射 503（不降级内存）
    try:
        run, outcome = await enqueue_scan(
            store,
            principal=principal,
            scan_types=list(payload.scanTypes),
            warehouse=warehouse,
            config_snapshot=scan_config.snapshot,
            config_hash_value=chash,
            config_version=scan_config.version,
            notification_mode=scan_config.document.notifications.mode,
            dry_run=dry_run,
            request_id=payload.requestId,
            schedule_slot=payload.scheduleSlot,
            actor_user_id=principal.user_id,
        )
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)

    if outcome == "idempotent":
        return JSONResponse(
            status_code=STATUS_QUEUED,
            content={
                "code": CODE_SUCCESS, "message": "idempotent hit",
                "data": {"scanId": run["scanId"], "status": run["status"]},
            },
        )
    if outcome == "conflict":
        return JSONResponse(
            status_code=409,
            content={
                "code": CODE_CONFLICT, "message": "存在冲突的扫描请求", "data": None,
            },
        )

    # POST 只负责入队，立即返回；执行完全交给后台 ScanWorker（lifespan 启动）。
    # 用户 JWT 从不入队 —— worker 统一用服务账号取短时令牌。
    return JSONResponse(
        status_code=STATUS_QUEUED,
        content={
            "code": CODE_SUCCESS,
            "message": "ok",
            "data": {"scanId": run["scanId"], "status": "queued"},
        },
    )


async def _load_visible_scan(
    scan_id: str, principal: Principal, store: ScanStore, settings: Any,
    *, can_view: Callable[[Principal, dict[str, Any]], bool] = can_view_scan,
    denied_message: str = "无权查看该扫描",
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """取扫描记录并做可见性判定：返回 ``(run, None)`` 或 ``(None, 错误外壳)``。

    GET /scans/{id} 与 GET /scans/{id}/summaries 共用取数与仓库范围判定，避免两处漂移；
    最后一步的记录级可见性由调用方传入（扫描记录本人可见；摘要 additionally 对能看
    该仓库告警的人可见，见 `can_view_scan_summaries`）。
    """
    try:
        run = await store.get_run(scan_id)
        if run is None:
            # 扫描记录已随保留期归档：只读端点读回落（带 archived=True）；可见性判定不变
            run = await store.get_archived_run(scan_id)
    except ScanStoreUnavailableError as exc:
        return None, {"code": CODE_UNAVAILABLE, "message": "巡检存储不可用：" + str(exc), "data": None}
    if run is None:
        return None, {"code": CODE_NOT_FOUND, "message": "查询数据不存在", "data": {"scanId": scan_id}}
    try:
        scope, token_restricted = _warehouse_scope(principal, settings)
    except AuthError as exc:
        return None, {"code": CODE_FORBIDDEN, "message": exc.message, "data": None}
    if not _in_scope(run.get("warehouse"), scope, token_restricted):
        return None, {"code": CODE_FORBIDDEN, "message": "无权查看该仓库的扫描", "data": None}
    if not can_view(principal, run):
        return None, {"code": CODE_FORBIDDEN, "message": denied_message, "data": None}
    return run, None


_SUMMARY_COUNT_KEYS = (
    "llmCalls", "llmFailures", "promptTokens", "completionTokens", "summariesLlm", "summariesTemplate",
)


@router.get("/scans/{scan_id}")
async def get_scan(
    scan_id: str,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
    settings: Any = Depends(_get_settings),
) -> dict[str, Any]:
    """查询一次扫描的状态与统计（只本人/数据范围；服务扫描仅管理员）。"""
    run, error = await _load_visible_scan(scan_id, principal, store, settings)
    if error is not None:
        return error
    return {"code": CODE_SUCCESS, "message": "ok", "data": run}


@router.get("/scans/{scan_id}/summaries")
async def get_scan_summaries(
    scan_id: str,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
    settings: Any = Depends(_get_settings),
) -> dict[str, Any]:
    """查询一次扫描的聚合摘要（阶段6）。

    摘要是表达层：``items`` 每组（rule_id + warehouse + customer）一条，
    ``summarySource`` 为 ``llm`` 或 ``template``；告警的级别与证据不在此处，也不会被它改变。
    可见性 = 扫描记录可见，或能查看该仓库的告警（`can_view_scan_summaries`）：仓库范围判定
    与 GET /scans/{id} 相同，但定时巡检由服务账号发起，巡检业务角色看不到扫描记录本身，
    仍要能在告警详情里读到摘要；响应里只有摘要与状态，不含配置快照与计数明细。
    """
    run, error = await _load_visible_scan(
        scan_id, principal, store, settings,
        can_view=can_view_scan_summaries, denied_message="无权查看该扫描的摘要",
    )
    if error is not None:
        return error
    try:
        items = await store.list_scan_summaries(scan_id)
    except ScanStoreUnavailableError as exc:
        return {"code": CODE_UNAVAILABLE, "message": "巡检存储不可用：" + str(exc), "data": None}
    counts = run.get("counts") if isinstance(run.get("counts"), dict) else {}
    return {
        "code": CODE_SUCCESS,
        "message": "ok",
        "data": {
            "scanId": scan_id,
            "status": run.get("status"),
            "partial": bool(run.get("partial")),
            "llmCounts": {key: counts.get(key, 0) for key in _SUMMARY_COUNT_KEYS},
            "items": items,
        },
    }


@router.post("/scans/{scan_id}/retry")
async def retry_scan(
    scan_id: str,
    request: Request,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
) -> JSONResponse:
    """管理员显式重试一次扫描：复用原扫描的配置快照，不读当前 YAML。

    权限：仅管理员（服务账号、巡检业务角色、`inspection:scan:trigger` 权限码均不可重试），
    且原扫描必须归本人或由服务账号发起（他人发起的手动扫描 → 403）。
    复用项：configSnapshot / configHash / configVersion / scanTypes / warehouse /
    dryRun / notificationMode。生成新的 scanId、traceId 与幂等键。
    原记录没有配置快照（历史终态记录）→ 409，不静默用当前配置重跑。
    审计归属：actor_* 记录发起重试的管理员、trigger=retry、retryOfScanId 指向
    被重试的扫描；origin_* 保留根来源（首次触发的人或服务与触发方式），
    既不冒充原发起人，也不丢失原发起人。
    """
    # 权限判定先于取原记录：非管理员一律 403，不借 retry 探测 scanId 是否存在。
    if is_service_account(principal) or not is_scan_admin(principal):
        return _forbidden("仅管理员可重试扫描")
    try:
        original = await store.get_run(scan_id)
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)
    if original is None:
        return JSONResponse(
            status_code=404,
            content={"code": CODE_NOT_FOUND, "message": "扫描不存在", "data": None},
        )

    settings = request.app.state.settings
    try:
        warehouse = check_warehouse_scope(
            principal, original.get("warehouse"), settings.scan_warehouses
        )
    except AuthError as exc:
        return _forbidden(exc.message)
    if not can_retry_scan(principal, original):
        return _forbidden("无权重试该扫描：原扫描不属于当前用户")

    snapshot = original.get("configSnapshot")
    if not snapshot:
        return JSONResponse(
            status_code=409,
            content={
                "code": CODE_CONFLICT,
                "message": "原扫描没有配置快照，无法按原配置重试",
                "data": {"scanId": scan_id},
            },
        )

    # 根来源：被重试的扫描若本身是重试记录，沿用它的 origin_*；否则取它自己的发起人与触发方式。
    origin_type = original.get("originActorType") or original.get("actorType")
    origin_id = original.get("originActorId") or original.get("actorId")
    origin_trigger = original.get("originTrigger") or original.get("trigger")

    new_scan_id = _new_scan_id()
    # 重试不复用 requestId / scheduleSlot：它们都参与唯一索引，复用会撞幂等键。
    try:
        run, outcome = await enqueue_scan(
            store,
            principal=principal,
            scan_types=list(original.get("scanTypes") or []),
            warehouse=warehouse,
            config_snapshot=snapshot,
            config_hash_value=str(original.get("configHash") or ""),
            config_version=str(original.get("configVersion") or ""),
            notification_mode=str(
                original.get("notificationMode")
                or "dry_run"
            ),
            dry_run=bool(original.get("dryRun")),
            scan_id=new_scan_id,
            actor_user_id=principal.user_id,
            trigger="retry",
            retry_of=scan_id,
            origin_actor_type=origin_type,
            origin_actor_id=origin_id,
            origin_trigger=origin_trigger,
            scan_key=compute_retry_scan_key(scan_id, new_scan_id),
        )
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)

    if outcome == "conflict":
        return JSONResponse(
            status_code=409,
            content={
                "code": CODE_CONFLICT, "message": "存在冲突的重试请求", "data": None,
            },
        )
    return JSONResponse(
        status_code=STATUS_QUEUED,
        content={
            "code": CODE_SUCCESS,
            "message": "ok",
            "data": {
                "scanId": run["scanId"],
                "status": "queued",
                "trigger": "retry",
                "retryOf": scan_id,
                "originActorType": run.get("originActorType"),
                "originActorId": run.get("originActorId"),
                "originTrigger": run.get("originTrigger"),
                "configHash": run.get("configHash"),
            },
        },
    )


@router.get("/alerts")
async def alerts(
    state: str | None = None,
    severity: str | None = None,
    warehouseId: str | None = None,
    ruleId: str | None = None,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
    settings: Any = Depends(_get_settings),
) -> dict[str, Any]:
    """查询告警列表（只返回令牌/服务端仓库范围内的告警）。"""
    if not can_view_alerts(principal):
        return {"code": CODE_FORBIDDEN, "message": "无权查看告警", "data": None}
    try:
        scope, _ = _warehouse_scope(principal, settings)
    except AuthError as exc:
        return {"code": CODE_FORBIDDEN, "message": exc.message, "data": None}
    if warehouseId and warehouseId not in scope:
        return {"code": CODE_FORBIDDEN, "message": f"无权查看仓库 {warehouseId} 的告警", "data": None}
    filters = {
        "state": state, "severity": severity, "warehouseId": warehouseId, "ruleId": ruleId,
        "warehouseIds": scope,
    }
    try:
        items = await store.list_alerts(filters)
    except ScanStoreUnavailableError as exc:
        return {"code": CODE_UNAVAILABLE, "message": "巡检存储不可用：" + str(exc), "data": None}
    return {"code": CODE_SUCCESS, "message": "ok", "data": items}


@router.get("/alerts/page")
async def alerts_page(
    state: str | None = None,
    severity: str | None = None,
    warehouseId: str | None = None,
    ruleId: str | None = None,
    lastSeenAt: str | None = None,
    lastAlertId: int | None = None,
    pageSize: int = 50,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
    settings: Any = Depends(_get_settings),
) -> dict[str, Any]:
    """告警游标分页：按 (lastSeenAt, alertId) 倒序严格小于翻页，不漏不重。

    游标要成对使用：lastSeenAt 与 lastAlertId 同时给出才生效，否则只按时间过滤。
    """
    if not can_view_alerts(principal):
        return {"code": CODE_FORBIDDEN, "message": "无权查看告警", "data": None}
    try:
        scope, _ = _warehouse_scope(principal, settings)
    except AuthError as exc:
        return {"code": CODE_FORBIDDEN, "message": exc.message, "data": None}
    if warehouseId and warehouseId not in scope:
        return {"code": CODE_FORBIDDEN, "message": f"无权查看仓库 {warehouseId} 的告警", "data": None}
    filters = {
        "state": state, "severity": severity, "warehouseId": warehouseId, "ruleId": ruleId,
        "warehouseIds": scope,
    }
    size = max(1, min(int(pageSize), 200))
    try:
        items = await store.list_alerts_page(
            filters, last_seen_at=lastSeenAt, last_alert_id=lastAlertId, page_size=size,
        )
    except ScanStoreUnavailableError as exc:
        return {"code": CODE_UNAVAILABLE, "message": "巡检存储不可用：" + str(exc), "data": None}
    next_cursor = None
    if items:
        tail = items[-1]
        next_cursor = {
            "lastSeenAt": tail.get("lastSeenAt"),
            "lastAlertId": tail.get("alertId"),
        }
    return {
        "code": CODE_SUCCESS, "message": "ok",
        "data": {"items": items, "nextCursor": next_cursor, "pageSize": size},
    }


@router.get("/alerts/{alert_id}")
async def alert_detail(
    alert_id: int,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
    settings: Any = Depends(_get_settings),
) -> dict[str, Any]:
    """告警详情：含证据、规则参数、事件流水与触发扫描。"""
    if not can_view_alerts(principal):
        return {"code": CODE_FORBIDDEN, "message": "无权查看告警", "data": None}
    try:
        scope, token_restricted = _warehouse_scope(principal, settings)
    except AuthError as exc:
        return {"code": CODE_FORBIDDEN, "message": exc.message, "data": None}
    try:
        detail = await store.get_alert_detail(alert_id)
    except ScanStoreUnavailableError as exc:
        return {"code": CODE_UNAVAILABLE, "message": "巡检存储不可用：" + str(exc), "data": None}
    if detail is None:
        return {"code": CODE_NOT_FOUND, "message": "告警不存在", "data": None}
    if not _in_scope(detail.get("warehouseId"), scope, token_restricted):
        return {"code": CODE_FORBIDDEN, "message": "无权查看该仓库的告警", "data": None}
    return {"code": CODE_SUCCESS, "message": "ok", "data": detail}


@router.post("/alerts/{alert_id}/claim")
async def claim_alert(
    alert_id: int,
    request: Request,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
) -> JSONResponse:
    """认领告警：他人已认领返回 409；ack 不等同于认领。"""
    if not can_operate_alert(principal):
        return _forbidden("无权认领告警")
    settings = request.app.state.settings
    try:
        scope, token_restricted = _warehouse_scope(principal, settings)
    except AuthError as exc:
        return _forbidden(exc.message)
    try:
        alert = await store.get_alert(alert_id)
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)
    if alert is None:
        return JSONResponse(
            status_code=404,
            content={"code": CODE_NOT_FOUND, "message": "告警不存在", "data": None},
        )
    if not _in_scope(alert.get("warehouseId"), scope, token_restricted):
        return _forbidden("无权认领该仓库的告警")
    try:
        result = await store.claim_alert(
            alert_id, assignee=principal.user_name,
            assignee_user_id=principal.user_id or None,
        )
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)
    if result is None:
        return JSONResponse(
            status_code=409,
            content={
                "code": CODE_CONFLICT,
                "message": "告警已被他人认领或已关闭",
                "data": None,
            },
        )
    return JSONResponse(
        status_code=200,
        content={"code": CODE_SUCCESS, "message": "ok", "data": result},
    )


@router.get("/notifications")
async def list_notifications(
    unreadOnly: bool = False,
    limit: int = 100,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
) -> dict[str, Any]:
    """本站通知列表：按接收人隔离（稳定 user_id，缺失回退用户名）。"""
    if not can_view_notifications(principal):
        return _forbidden("无权查看通知")
    recipient_user_id, recipient = notification_identity(principal)
    try:
        items = await store.list_notifications(
            recipient_user_id=recipient_user_id, recipient=recipient,
            unread_only=bool(unreadOnly), limit=max(1, min(int(limit), 500)),
        )
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)
    return {"code": CODE_SUCCESS, "message": "ok", "data": {"items": items}}


@router.post("/notifications/{notification_id}/read")
async def read_notification(
    notification_id: int,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
) -> JSONResponse:
    """标记本人通知为已读；他人通知一律 404，不泄露存在性。"""
    if not can_view_notifications(principal):
        return _forbidden("无权操作通知")
    recipient_user_id, recipient = notification_identity(principal)
    try:
        result = await store.mark_notification_read(
            notification_id, recipient_user_id=recipient_user_id, recipient=recipient,
        )
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"code": CODE_NOT_FOUND, "message": "通知不存在", "data": None},
        )
    return JSONResponse(
        status_code=200,
        content={"code": CODE_SUCCESS, "message": "ok", "data": result},
    )


@router.post("/alerts/{alert_id}/ack")
async def ack_alert(
    alert_id: int,
    request: Request,
    body: AlertActionRequest | None = None,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
) -> JSONResponse:
    """确认告警。"""
    return await _transition(
        alert_id, "acknowledged", body, principal, store, request
    )


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    request: Request,
    body: AlertActionRequest | None = None,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
) -> JSONResponse:
    """解决告警。"""
    return await _transition(
        alert_id, "resolved", body, principal, store, request
    )


@router.post("/alerts/{alert_id}/ignore")
async def ignore_alert(
    alert_id: int,
    request: Request,
    body: AlertActionRequest | None = None,
    principal: Principal = Depends(require_principal),
    store: ScanStore = Depends(get_scan_store),
) -> JSONResponse:
    """忽略告警（默认 7 天；显式 ignoredUntil 须为带时区、晚于当前时间的 ISO 8601）。"""
    ignored_until = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    if body and body.ignoredUntil:
        try:
            parsed = _parse_ignored_until(body.ignoredUntil)
        except ValueError as exc:
            return _unprocessable(str(exc))
        ignored_until = parsed.isoformat()
    return await _transition(
        alert_id, "ignored", body, principal, store, request,
        ignored_until=ignored_until,
    )


def _parse_ignored_until(raw: str) -> datetime:
    """ignoredUntil 统一在入口校验：非法/无时区/过去时间一律 422，内存与 PG 行为一致。"""
    try:
        parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("ignoredUntil 须为 ISO 8601 时间") from exc
    if parsed.tzinfo is None:
        raise ValueError("ignoredUntil 须带时区，例如 2026-12-01T00:00:00+08:00")
    if parsed <= datetime.now(timezone.utc):
        raise ValueError("ignoredUntil 须晚于当前时间")
    return parsed


async def _transition(
    alert_id: int, to_state: str, body: AlertActionRequest | None,
    principal: Principal, store: ScanStore, request: Request,
    *, ignored_until: str | None = None,
) -> JSONResponse:
    if not can_operate_alert(principal):
        return _forbidden("无权操作告警")
    # resolve/ignore 须给出理由，便于审计；ack 可选。
    if to_state in ("resolved", "ignored") and not (body and body.reason and body.reason.strip()):
        return _unprocessable("resolve/ignore 须提供 reason")
    settings = request.app.state.settings
    try:
        scope, token_restricted = _warehouse_scope(principal, settings)
    except AuthError as exc:
        return _forbidden(exc.message)
    try:
        alert = await store.get_alert(alert_id)
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)
    # 先按仓库范围拒绝，再判断是否存在：不向越权者泄露告警是否存在
    if alert is None or not _in_scope(alert.get("warehouseId"), scope, token_restricted):
        if alert is not None:
            return _forbidden("无权操作该仓库的告警")
        return JSONResponse(
            status_code=404,
            content={"code": CODE_NOT_FOUND, "message": "告警不存在", "data": None},
        )
    try:
        result = await store.transition_alert(
            alert_id, to_state,
            reason=body.reason if body else None,
            ignored_until=ignored_until,
            actor_type="service" if principal.token_use == "agent_service" else "user",
            actor_id=principal.user_name,
            actor_user_id=principal.user_id or None,
        )
    except ScanStoreUnavailableError as exc:
        return _unavailable(exc)
    if result is None:
        return JSONResponse(
            status_code=409,
            content={
                "code": CODE_CONFLICT,
                "message": "状态已被他人变更，请刷新",
                "data": None,
            },
        )
    return JSONResponse(
        status_code=200,
        content={"code": CODE_SUCCESS, "message": "ok", "data": result},
    )