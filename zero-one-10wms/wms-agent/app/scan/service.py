"""巡检编排：取数 → 规则 → 告警 → 通知 → 落扫描记录。

v0.2.0 已实现四类：`expiry` / `no_up` / `delay` / `backlog`（阶段3）。规则判定确定性，LLM 不参与级别。
`backlog` 需要历史基线：快照完整时读基线 + 落样本（agent_backlog_observations），
partial / 快照失败不落样本不告警。

队列语义：worker 领取后以租约（lease_owner）执行，回写一律走 fencing；
`attempt` / `queued_at` / `lease_*` 等簿记列由存储维护，编排层只保留领取时
拿到的值并累加本次执行的 counts，不会把重试次数归零。
"""

from __future__ import annotations

import asyncio
import fnmatch
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from app.scan.config import canonical_json, hash_config
from app.scan.llm.summarizer import summarize_scan
from app.scan.repository import (
    SEVERITY_RANK, UPSERT_CREATED, UPSERT_ESCALATED, UPSERT_REPLAYED, UPSERT_SUPPRESSED,
    ScanStore, ScanStoreConflictError,
)
from app.scan.rules.backlog import (
    RULE_ID as BACKLOG_RULE_ID,
    RULE_VERSION as BACKLOG_RULE_VERSION,
    evaluate_backlog_detailed,
)
from app.scan.rules.base import Finding, RuleContext, RuleEvaluation
from app.scan.rules.delay import (
    RULE_ID as DELAY_RULE_ID,
    RULE_VERSION as DELAY_RULE_VERSION,
    evaluate_delay_detailed,
)
from app.scan.rules.expiry import (
    RULE_EXPIRED, RULE_NEAR, RULE_VERSION, RULE_WATCH, evaluate_expiry_detailed,
)
from app.scan.rules.no_up import (
    RULE_ID as NOUP_RULE_ID,
    RULE_VERSION as NOUP_RULE_VERSION,
    evaluate_no_up_detailed,
)
from app.scan.sources.backlog import GRADED_QUEUES, fetch_backlog
from app.scan.sources.base import SourceResult
from app.scan.sources.delay import fetch_delay
from app.scan.sources.expiry import fetch_expiry
from app.scan.sources.no_up import fetch_no_up
from app.security import Principal, check_warehouse_scope
from app.tools.gateway_client import GatewayClient

if TYPE_CHECKING:  # 仅类型标注，避免编排层在导入期依赖 LLM 实现
    from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = ("expiry", "no_up", "delay", "backlog")
CODE_SUCCESS = 10000
# 与 config/scan.yaml 同构的默认生效配置：测试与“无配置文件”的库内调用都走这里，
# 保证 cfg["scan"] / cfg["rules"] / cfg["notifications"] 的嵌套读取路径唯一。
DEFAULT_CONFIG: dict[str, Any] = {
    "version": "v0.2.0",
    "warehouses": ["W01"],
    "scan": {
        "pageSize": 100,
        "maxPages": 20,
        "requestTimeoutSeconds": 3.0,
        "sourceBudgetSeconds": 30.0,
        "scanBudgetSeconds": 120.0,
        "concurrency": 1,
    },
    "rules": {
        "expiry": {"expiredDays": 0, "nearDays": 7, "nearRatio": 1 / 3, "watchDays": 30},
        "noUp": {"p0Hours": 8, "p1Hours": 4, "p2Hours": 2},
        "delay": {"p0Hours": 24, "p1Hours": 2, "p2Hours": 0},
        # 方案 §13.1 / 用户 m04555 固化：三队列分别判定，前 3 次只建基线
        "backlog": {
            "growthRatio": 0.30, "absoluteDelta": 10, "baselineScans": 3, "consecutiveForP1": 3,
        },
    },
    "routing": [],
    "notifications": {"mode": "dry_run", "recipients": []},
    "schedule": {
        "enabled": False,
        "scanTypes": ["expiry", "no_up", "delay", "backlog"],
        "cron": "*/15 7-23 * * *",
        "timezone": "Asia/Shanghai",
    },
    # 阶段6：LLM 聚合摘要默认关闭（全部走确定性模板）；边界与 LlmConfig 一致
    "llm": {
        "enabled": False,
        "maxCallsPerScan": 20,
        "timeoutSeconds": 8.0,
        "concurrency": 4,
        "maxSummaryChars": 300,
        "maxActions": 3,
        "maxActionChars": 100,
    },
}
# 各类型规则版本；多类型扫描的 run.ruleVersion 记组合串，便于回放定位。
RULE_VERSIONS: dict[str, str] = {
    "expiry": RULE_VERSION,
    "no_up": NOUP_RULE_VERSION,
    "delay": DELAY_RULE_VERSION,
    "backlog": BACKLOG_RULE_VERSION,
}
# 每次执行从零累计的统计；attempt 不在这里（它是 agent_scan_runs 的独立列）。
DEFAULT_COUNTS: dict[str, Any] = {
    "findings": 0, "alertsCreated": 0, "alertsUpdated": 0, "alertsEscalated": 0,
    "alertsSuppressed": 0, "alertsReplayed": 0, "alertsAutoResolved": 0, "staleCheckSkipped": 0,
    "notifications": 0, "notificationsUnrouted": 0,
    # 阶段6：LLM 只做聚合摘要。llmCalls 含失败调用；llmFailures 含超时/提供方故障/输出不合规
    "llmCalls": 0, "llmFailures": 0, "promptTokens": 0, "completionTokens": 0,
    "summariesLlm": 0, "summariesTemplate": 0,
}

# 类型 → (取数函数, 规则求值函数, 配置键, 端点)
TypeHandler = tuple[
    Callable[..., Awaitable[SourceResult]],
    Callable[..., RuleEvaluation],
    str,
    str,
]
HANDLERS: dict[str, TypeHandler] = {
    "expiry": (fetch_expiry, evaluate_expiry_detailed, "expiry", "/stock/expiry-warning/query-all"),
    "no_up": (fetch_no_up, evaluate_no_up_detailed, "noUp", "/daycheck/no-up/get-no-up-goods-page"),
    "delay": (fetch_delay, evaluate_delay_detailed, "delay", "/daycheck/delay/im-delay"),
    # backlog 的求值走 _evaluate_backlog（需要历史基线），evaluator 仅作标识
    "backlog": (
        fetch_backlog, evaluate_backlog_detailed, "backlog", "/dashboard/query-pend-snapshot",
    ),
}

# 规则 id → 扫描类型：自动关闭时用它取期望的 rule_version（版本不匹配的告警不自动关）。
RULE_ID_TYPES: dict[str, str] = {
    RULE_EXPIRED: "expiry",
    RULE_NEAR: "expiry",
    RULE_WATCH: "expiry",
    NOUP_RULE_ID: "no_up",
    DELAY_RULE_ID: "delay",
    BACKLOG_RULE_ID: "backlog",
}

# 扫描类型 → 规则 id 全集（RULE_ID_TYPES 的反向表）：
# 取数可信时该类型的每个规则都参与“已评估且未命中”的自动关闭判定，哪怕本次求值结果为空。
SCAN_TYPE_RULE_IDS: dict[str, tuple[str, ...]] = {
    scan_type: tuple(sorted(rid for rid, typ in RULE_ID_TYPES.items() if typ == scan_type))
    for scan_type in SUPPORTED_TYPES
}


def config_hash(config: dict[str, Any]) -> str:
    return hash_config(config)


def combined_rule_version(scan_types: list[str]) -> str:
    """按类型顺序拼 `type=version`，如 `expiry=v0.2.0;no_up=v0.2.0`。"""
    return ";".join(
        f"{t}={RULE_VERSIONS[t]}" for t in dict.fromkeys(scan_types) if t in RULE_VERSIONS
    )


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """请求体指纹（入队时计算并落库，便于幂等/审计比对）。"""
    normalized = {
        "scanTypes": list(dict.fromkeys(payload.get("scanTypes") or [])),
        "warehouse": payload.get("warehouse"),
        "dryRun": bool(payload.get("dryRun", False)),
        "requestId": payload.get("requestId"),
        "scheduleSlot": payload.get("scheduleSlot"),
        "configHash": payload.get("configHash"),
    }
    raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_trace_id() -> str:
    """扫描级 trace：入队时生成，告警/事件沿用同一 traceId。"""
    return "trace-" + uuid.uuid4().hex[:16]


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _rule_config(config: dict[str, Any], config_key: str) -> dict[str, Any]:
    """取某类规则的阈值块：嵌套 `rules.<key>`，兼容旧扁平结构（库内调用/历史快照）。"""
    rules = config.get("rules")
    if isinstance(rules, dict):
        return dict(rules.get(config_key) or {})
    legacy = config.get(config_key)
    return dict(legacy) if isinstance(legacy, dict) else {}


def resolve_route_targets(
    finding: Finding,
    *,
    warehouse: str,
    actor_type: str | None,
    actor_id: str | None,
    config: dict[str, Any],
    configured_recipients: list[str] | None,
) -> tuple[list[str], list[str]]:
    """返回 (责任岗位, 通知接收人)。

    手动扫描默认只通知发起人；定时扫描合并全局接收人与命中路由的接收人。
    路由只影响责任岗位和接收人，不改变告警级别、对象或证据。
    """
    routes = [
        route
        for route in config.get("routing", [])
        if route.get("warehouse") == warehouse
        and fnmatch.fnmatchcase(finding.rule_id, str(route.get("rule_id") or ""))
    ]
    roles = _unique([str(route.get("assignee_role") or "") for route in routes])
    routed_recipients = _unique(
        [str(recipient) for route in routes for recipient in route.get("recipients", [])]
    )
    if actor_type == "user":
        recipients = [actor_id] if actor_id else []
    else:
        recipients = _unique(list(configured_recipients or []) + routed_recipients)
    return roles, recipients


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def compute_retry_scan_key(original_scan_id: str, new_scan_id: str) -> str:
    """重试扫描的幂等键：与原扫描不同，且不会被 requestId / scheduleSlot 唯一索引拦下。"""
    basis = f"retry|{original_scan_id}|{new_scan_id}"
    return "sha256:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()


async def enqueue_scan(
    store: ScanStore,
    *,
    principal: Principal,
    scan_types: list[str],
    warehouse: str,
    config_snapshot: str,
    config_hash_value: str,
    config_version: str,
    notification_mode: str,
    dry_run: bool = False,
    request_id: str | None = None,
    schedule_slot: str | None = None,
    scan_id: str | None = None,
    actor_user_id: str | None = None,
    trigger: str | None = None,
    scan_key: str | None = None,
    retry_of: str | None = None,
    origin_actor_type: str | None = None,
    origin_actor_id: str | None = None,
    origin_trigger: str | None = None,
) -> tuple[dict[str, Any], str]:
    """统一入队：API、内部调度与管理员重试共用。

    返回 (run, outcome)，outcome ∈ {"created", "idempotent", "conflict"}：
      - created：新建并入队；
      - idempotent：命中既有扫描（requestId / scheduleSlot 幂等）；
      - conflict：唯一索引冲突但找不到既有扫描（调用方回 409）。

    审计归属：actor_* 永远是「谁触发了这一次入队」，trigger 区分方式
    （manual / schedule / retry）。重试必须给 retry_of（被重试的 scanId），
    origin_* 记录根来源（首次触发的人或服务与触发方式），不冒充原发起人。

    用户 JWT 绝不入队/落库：这里只记录发起人的稳定 id（actorUserId）与用户名，
    worker 之后统一用服务账号短时令牌取数。
    """
    types = list(dict.fromkeys(scan_types))
    actor_type = "service" if principal.token_use == "agent_service" else "user"
    resolved_trigger = trigger or ("schedule" if actor_type == "service" else "manual")
    if resolved_trigger == "retry" and not retry_of:
        # 不允许出现「标成重试却追溯不到原扫描」的记录。
        raise ValueError("retry scan requires retry_of (the retried scanId)")
    resolved_key = scan_key if scan_key is not None else compute_scan_key(
        principal=principal, request_id=request_id, schedule_slot=schedule_slot,
        config_hash_value=config_hash_value, scan_types=types, warehouse=warehouse,
    )
    resolved_scan_id = scan_id or ("scan-" + uuid.uuid4().hex[:16])
    now = _now_iso()
    run: dict[str, Any] = {
        "scanId": resolved_scan_id,
        "trigger": resolved_trigger,
        "retryOfScanId": retry_of,
        "originActorType": origin_actor_type,
        "originActorId": origin_actor_id,
        "originTrigger": origin_trigger,
        "actorType": actor_type,
        "actorId": principal.user_name,
        "status": "queued",
        "partial": False,
        "sourceStatus": [],
        "configHash": config_hash_value,
        "ruleVersion": combined_rule_version(types),
        "scanTypes": types,
        "requestId": request_id,
        "scheduleSlot": schedule_slot,
        "scanKey": resolved_key or resolved_scan_id,
        "queuedAt": now,
        "startedAt": now,
        "finishedAt": None,
        "attempt": 0,
        "counts": {},
        "errorSummary": None,
        "dryRun": bool(dry_run),
        "warehouse": warehouse,
        "notificationMode": notification_mode,
        "configSnapshot": config_snapshot,
        "configVersion": config_version,
        "payloadHash": compute_payload_hash({
            "scanTypes": types, "warehouse": warehouse, "dryRun": bool(dry_run),
            "requestId": request_id, "scheduleSlot": schedule_slot,
            "configHash": config_hash_value,
        }),
        "traceId": new_trace_id(),
        "actorUserId": actor_user_id if actor_type == "user" else None,
    }
    try:
        await store.insert_run(run)
    except ScanStoreConflictError:
        existing = await store.get_run_by_scan_key(resolved_key) if resolved_key else None
        if existing is not None:
            return existing, "idempotent"
        return run, "conflict"
    return run, "created"


def compute_scan_key(
    *, principal: Principal, request_id: str | None, schedule_slot: str | None,
    config_hash_value: str, scan_types: list[str], warehouse: str | None = None,
) -> str:
    """幂等键：手动 requestId / 定时 scheduleSlot+warehouse+configHash+scanTypes。

    服务账号未带 scheduleSlot 时不去重（返回空），否则所有无槽位的定时扫描
    会撞成同一个 key；仓库纳入键中，不同仓库的同一槽位互不覆盖。
    """
    normalized = ",".join(dict.fromkeys(scan_types))
    if principal.token_use == "agent_service":
        if not schedule_slot:
            return ""
        basis = f"schedule|{schedule_slot}|{warehouse or ''}|{config_hash_value}|{normalized}"
    elif request_id:
        basis = f"manual|{request_id}|{principal.user_name}"
    else:
        # 无幂等键：每次独立，scanKey 用 scan_id（调用方注入）
        return ""
    return "sha256:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()


async def run_scan(
    *,
    scan_id: str,
    scan_types: list[str],
    principal: Principal,
    token: str,
    client: GatewayClient,
    store: ScanStore,
    allowed_warehouses: list[str],
    requested_warehouse: str | None = None,
    dry_run: bool = False,
    notification_mode: str | None = None,
    config: dict[str, Any] | None = None,
    request_id: str | None = None,
    schedule_slot: str | None = None,
    config_hash_value: str | None = None,
    scan_key: str | None = None,
    executor_type: str | None = None,
    executor_id: str | None = None,
    actor_type: str | None = None,
    trigger: str | None = None,
    actor_id: str | None = None,
    claimed: dict[str, Any] | None = None,
    lease_owner: str | None = None,
    recipients: list[str] | None = None,
    llm_provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """执行一次扫描，返回扫描记录字典。失败也落 `failed` 记录，不抛给调用方。

    ``claimed`` 是 worker 领取到的队列记录：其中的 queuedAt/attempt/leaseOwner/
    leasedAt/payloadHash/traceId 等簿记字段原样保留，只覆盖本次执行结果。
    ``lease_owner`` 非空时所有回写都走 fencing，租约失效抛 ScanLeaseLostError。
    ``llm_provider`` 只用于聚合摘要（阶段6），不参与判定；为 None 时全部用模板摘要。
    """
    cfg = config or DEFAULT_CONFIG
    chash = config_hash_value or config_hash(cfg)
    notification_mode = notification_mode or str(
        (cfg.get("notifications") or {}).get("mode") or "dry_run"
    )
    configured_recipients = (
        list(recipients)
        if recipients is not None
        else list((cfg.get("notifications") or {}).get("recipients") or [])
    )
    runtime = cfg.get("scan") or {}
    client = client.with_timeout(float(runtime.get("requestTimeoutSeconds", 3.0)))
    base = dict(claimed) if claimed else {}
    # 领取记录里的请求级参数优先（入队时已定），未被显式覆盖时沿用
    if base:
        requested_warehouse = requested_warehouse or base.get("warehouse")
        notification_mode = base.get("notificationMode") or notification_mode
        request_id = base.get("requestId")
        schedule_slot = base.get("scheduleSlot")
        scan_key = base.get("scanKey")
        actor_type = actor_type or base.get("actorType")
        trigger = trigger or base.get("trigger")
        actor_id = actor_id or base.get("actorId")
        dry_run = bool(base.get("dryRun", dry_run))
    # worker 执行身份是服务账号，但扫描记录要保留发起用户与触发来源。
    actor_type = actor_type or ("service" if principal.token_use == "agent_service" else "user")
    trigger = trigger or ("schedule" if actor_type == "service" else "manual")
    started = _now_iso()
    trace_id = base.get("traceId") or new_trace_id()
    config_snapshot = base.get("configSnapshot") or canonical_json(cfg)
    config_version = base.get("configVersion") or str(cfg.get("version") or "inline")
    payload_hash = base.get("payloadHash") or compute_payload_hash({
        "scanTypes": scan_types, "warehouse": requested_warehouse, "dryRun": dry_run,
        "requestId": request_id, "scheduleSlot": schedule_slot, "configHash": chash,
    })
    # dryRun 与 notification_mode 语义统一（实施方案 §6.1 vs §11.3）：
    # - 请求级 dryRun=true：整次只算 findings 写 scan_runs，不落告警、不发通知；
    # - 服务端 notification_mode=dry_run：是“通知投递”策略，不影响告警落库，
    #   只在 created/escalated 写 agent_notifications(status=dry_run) 而不发送。
    no_persist_alerts = dry_run is True
    types = list(scan_types)
    counts: dict[str, Any] = {
        **DEFAULT_COUNTS,
        "skippedTypes": [t for t in types if t not in SUPPORTED_TYPES],
    }
    run: dict[str, Any] = {
        **base,
        "scanId": scan_id,
        "trigger": trigger,
        "actorType": actor_type,
        "actorId": actor_id or principal.user_name,
        "status": "running",
        "partial": False,
        "sourceStatus": [],
        "configHash": chash,
        "ruleVersion": combined_rule_version(types),
        "scanTypes": types,
        "requestId": request_id,
        "scheduleSlot": schedule_slot,
        "scanKey": scan_key or scan_id,
        "startedAt": base.get("startedAt") or started,
        "finishedAt": None,
        "counts": counts,
        "errorSummary": None,
        "dryRun": no_persist_alerts,
        "notificationMode": notification_mode,
        "warehouse": requested_warehouse,
        "payloadHash": payload_hash,
        "traceId": trace_id,
        "configSnapshot": config_snapshot,
        "configVersion": config_version,
        "executorType": executor_type or base.get("executorType")
        or (actor_type if actor_type == "service" else None),
        "executorId": executor_id or base.get("executorId")
        or (principal.user_name if actor_type == "service" else None),
        # 发起用户的稳定 id：入队时由入口写入，异步执行时用于 in_app 通知隔离
        "actorUserId": base.get("actorUserId")
        or (principal.user_id if actor_type == "user" else None),
    }
    if not run.get("queuedAt"):
        run["queuedAt"] = started
    run.setdefault("attempt", 0)
    await store.save_run(run, lease_owner=lease_owner)

    try:
        warehouse = check_warehouse_scope(principal, requested_warehouse, allowed_warehouses)
        run["warehouse"] = warehouse
        ctx = RuleContext(warehouse=warehouse, now=datetime.now(timezone.utc).astimezone())
        by_fingerprint: dict[str, Finding] = {}
        page_size = int(runtime.get("pageSize", 100))
        max_pages = int(runtime.get("maxPages", 20))
        budget = float(runtime.get("sourceBudgetSeconds", 30))
        concurrency = int(runtime.get("concurrency", 1))
        deadline = time.monotonic() + float(runtime.get("scanBudgetSeconds", 120))
        semaphore = asyncio.Semaphore(concurrency)
        supported = [(scan_type, HANDLERS[scan_type]) for scan_type in types if scan_type in HANDLERS]

        async def fetch_one(scan_type: str, handler: TypeHandler) -> SourceResult:
            fetcher, _evaluator, config_key, endpoint = handler
            type_cfg = _rule_config(cfg, config_key)
            async with semaphore:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return SourceResult(
                        source=scan_type,
                        endpoint=endpoint,
                        status="timeout",
                        truncated=True,
                        error_summary="scan_budget_exceeded",
                    )
                try:
                    return await asyncio.wait_for(
                        fetcher(
                            client, token,
                            page_size=int(type_cfg.get("pageSize", page_size)),
                            max_pages=int(type_cfg.get("maxPages", max_pages)),
                            source_budget_seconds=float(
                                type_cfg.get("sourceBudgetSeconds", budget)
                            ),
                        ),
                        timeout=remaining,
                    )
                except asyncio.TimeoutError:
                    return SourceResult(
                        source=scan_type,
                        endpoint=endpoint,
                        status="timeout",
                        truncated=True,
                        error_summary="scan_budget_exceeded",
                    )

        async def _timed_fetch(scan_type: str, handler: Any) -> SourceResult:
            # 统一在调用处计时（阶段7 指标）：覆盖全部取数 handler，
            # 包括不经过 fetch_paged 的 backlog 快照源；超时分支同样带上实际耗时。
            source_started = time.monotonic()
            result = await fetch_one(scan_type, handler)
            if result.duration_ms is None:
                result.duration_ms = int((time.monotonic() - source_started) * 1000)
            return result

        if concurrency == 1:
            sources = [
                await _timed_fetch(scan_type, handler) for scan_type, handler in supported
            ]
        else:
            sources = list(await asyncio.gather(
                *(_timed_fetch(scan_type, handler) for scan_type, handler in supported)
            ))

        # evaluations：扫描类型 → 规则求值三件套（命中 / 覆盖 / 数据质量跳过）
        evaluations: dict[str, RuleEvaluation] = {}
        # rule_ok：规则 id → 该规则本次的取数是否可信（源 status=ok 且未截断）
        rule_ok: dict[str, bool] = {}
        for (scan_type, handler), source in zip(supported, sources):
            fetcher, evaluator, config_key, _endpoint = handler
            type_cfg = _rule_config(cfg, config_key)
            run["sourceStatus"].append(source.to_status())
            if source.status in ("partial", "timeout", "error"):
                run["partial"] = True
            source_trusted = source.status == "ok" and not source.truncated

            if scan_type == "backlog":
                # 待办积压需要历史基线：只在快照完整时读基线 + 落样本；partial 不落样本不告警；
                # 请求级 dryRun 只算不落（样本与告警都不写）。
                evaluation, saved = await _evaluate_backlog(
                    store, source, type_cfg, ctx, scan_id, trace_id, chash,
                    persist=not no_persist_alerts,
                )
                counts["backlogSamplesSaved"] = (
                    counts.get("backlogSamplesSaved", 0) + saved
                )
            else:
                evaluation = _evaluate(fetcher, evaluator, type_cfg, source.rows, ctx)
            evaluations[scan_type] = evaluation
            findings = evaluation.findings
            # 该类型的全部规则都登记取数可信度，而不是只登记“本次求值出现过”的规则：
            # 源完整返回 0 行时求值结果为空，但规则同样已评估且未命中，必须允许自动关闭
            # （真实 e2e 捕获：第二次扫描 0 行 → eligible 为空 → alertsAutoResolved 恒为 0）。
            for rule_id in set(SCAN_TYPE_RULE_IDS.get(scan_type, ())) | {
                key.rule_id for key in evaluation.evaluated_keys
            } | {
                finding.rule_id for finding in findings
            } | set(evaluation.data_quality_skipped):
                rule_ok[rule_id] = source_trusted
            counts["findings"] += len(findings)
            for finding in findings:
                by_fingerprint[finding.fingerprint] = finding

        if run["partial"]:
            by_fingerprint[_partial_fingerprint(scan_id)] = _partial_finding(scan_id, ctx)

        if no_persist_alerts:
            # dryRun：只算 findings 写 scan_runs，不落告警、不发通知
            counts["notifications"] = 0
        else:
            # 稳定接收人 id：手动扫描取发起用户的 user_id（入队时已落库），
            # 定时扫描的接收人只有用户名，按用户名回退。
            recipient_user_id = (
                base.get("actorUserId") if actor_type == "user" else None
            ) or (principal.user_id if actor_type == "user" else None)
            await _persist_findings(
                by_fingerprint, store, scan_id, warehouse, ctx.now.isoformat(),
                notification_mode, counts, trace_id=trace_id, config=cfg,
                actor_type=actor_type, actor_id=run["actorId"],
                configured_recipients=configured_recipients,
                recipient_user_id=recipient_user_id,
            )
            # 阶段5：先幂等落覆盖记录（自动关闭的证据），再逐条条件关闭。
            await _auto_resolve_cleared(
                store, evaluations=evaluations, rule_ok=rule_ok, findings=by_fingerprint,
                scan_id=scan_id, warehouse=warehouse, trace_id=trace_id,
                started_at=started, dry_run=no_persist_alerts, partial=bool(run["partial"]),
                counts=counts,
            )
            # 阶段6：告警与通知已落库之后才做聚合摘要；摘要失败不影响扫描结果。
            await _summarize_scan_findings(
                store, by_fingerprint, scan_id=scan_id, trace_id=trace_id, config=cfg,
                llm_provider=llm_provider, partial=bool(run["partial"]), deadline=deadline,
                counts=counts,
            )

        run["status"] = "succeeded"
    except Exception as exc:  # noqa: BLE001 - 失败落 failed 记录，不抛出
        # 完整堆栈进日志（errorSummary 只给类型名，不泄露内部信息给调用方）
        logger.warning("scan %s failed: %s: %s", scan_id, type(exc).__name__, exc, exc_info=True)
        run["status"] = "failed"
        run["errorSummary"] = type(exc).__name__

    run["finishedAt"] = _now_iso()
    await store.save_run(run, lease_owner=lease_owner)
    return run


async def _summarize_scan_findings(
    store: ScanStore,
    by_fingerprint: dict[str, Finding],
    *,
    scan_id: str,
    trace_id: str,
    config: dict[str, Any],
    llm_provider: LLMProvider | None,
    partial: bool,
    deadline: float | None,
    counts: dict[str, Any],
) -> None:
    """阶段6：LLM 聚合摘要并落库（只摘要，不判定）。

    调用点在告警落库、通知、自动关闭全部完成之后，所以这里吞掉一切异常：
    摘要只是表达层，任何 LLM / 存储故障都不能把一次已经生效的扫描改成 failed。
    """
    try:
        rows, stats = await summarize_scan(
            list(by_fingerprint.values()), config=config, provider=llm_provider,
            scan_id=scan_id, trace_id=trace_id, partial=partial, deadline=deadline,
        )
        counts.update(stats)
        counts["summariesSaved"] = await store.save_scan_summaries(rows) if rows else 0
    except Exception as exc:  # noqa: BLE001 - 表达层故障不改变扫描结果
        logger.warning(
            "scan %s summaries failed: %s: %s", scan_id, type(exc).__name__, exc, exc_info=True,
        )
        counts["summariesError"] = type(exc).__name__


def _evaluate(
    fetcher: Callable[..., Awaitable[SourceResult]],
    evaluator: Callable[..., RuleEvaluation],
    type_cfg: dict[str, Any],
    rows: list[dict[str, Any]],
    ctx: RuleContext,
) -> RuleEvaluation:
    """把配置键映射为规则求值参数；未配置项走规则函数默认值。"""
    if fetcher is fetch_expiry:
        return evaluator(
            rows, ctx,
            expired_days=int(type_cfg.get("expiredDays", 0)),
            near_days=int(type_cfg.get("nearDays", 7)),
            near_ratio=float(type_cfg.get("nearRatio", 1 / 3)),
            watch_days=int(type_cfg.get("watchDays", 30)),
        )
    if fetcher is fetch_no_up:
        return evaluator(
            rows, ctx,
            p0_hours=float(type_cfg.get("p0Hours", 8)),
            p1_hours=float(type_cfg.get("p1Hours", 4)),
            p2_hours=float(type_cfg.get("p2Hours", 2)),
        )
    if fetcher is fetch_delay:
        return evaluator(
            rows, ctx,
            p0_hours=float(type_cfg.get("p0Hours", 24)),
            p1_hours=float(type_cfg.get("p1Hours", 2)),
            p2_hours=float(type_cfg.get("p2Hours", 0)),
        )
    return RuleEvaluation()


def _partial_fingerprint(scan_id: str) -> str:
    return "sha256:" + hashlib.sha256(f"SCAN-PARTIAL|v1|{scan_id}".encode()).hexdigest()


async def _evaluate_backlog(
    store: ScanStore, source: SourceResult, type_cfg: dict[str, Any], ctx: RuleContext,
    scan_id: str, trace_id: str, config_hash_value: str, *, persist: bool = True,
) -> tuple[RuleEvaluation, int]:
    """待办积压：快照完整 → 读基线 → 判定 → 落本次样本；快照不完整 → 不落样本不告警。

    基线严格按 rule_version 过滤（规则升版不混用旧基线）；样本按 (scanId, queueType)
    唯一，重复回放不重复落样本。手动扫描同样计入基线（受 requestId 幂等约束）。
    ``persist=False``（请求级 dryRun）时只判定不落样本。
    返回 (RuleEvaluation, 新增样本数)。
    """
    if source.status != "ok":
        return RuleEvaluation(), 0
    graded = [r for r in source.rows if not r.get("diagnostic")]
    if not graded or len(graded) != len(GRADED_QUEUES):
        # 快照形状不完整（队列缺行/多行）≠ “已评估且正常”：禁用本次自动关闭
        return RuleEvaluation(data_quality_skipped=[BACKLOG_RULE_ID]), 0
    observed_at = graded[0].get("observedAt") or ctx.now.isoformat()
    # 负值 / 非数值是数据质量问题：该队列不参与基线也不落样本（规则层同样跳过），
    # 其余队列照常；快照本身仍是完整的，不标 partial。
    valid = [r for r in graded if _is_non_negative_number(r.get("value"))]
    if not valid:
        # 全部队列数值非法：没有可判定的对象，禁用本次自动关闭
        return RuleEvaluation(data_quality_skipped=[BACKLOG_RULE_ID]), 0
    graded_for_rule = [r if r in valid else {**r, "value": None} for r in graded]

    history_all: list[dict[str, Any]] = []
    for queue in GRADED_QUEUES:
        history = await store.list_backlog_observations(
            ctx.warehouse, queue, rule_version=BACKLOG_RULE_VERSION, limit=50,
        )
        history_all.extend(history)
    evaluation = evaluate_backlog_detailed(
        graded_for_rule, history_all, ctx,
        growth_ratio=float(type_cfg.get("growthRatio", 0.30)),
        absolute_delta=int(type_cfg.get("absoluteDelta", 10)),
        baseline_scans=int(type_cfg.get("baselineScans", 3)),
        consecutive_for_p1=int(type_cfg.get("consecutiveForP1", 3)),
    )
    for finding in evaluation.findings:
        # 告警沿用扫描级 trace，便于把告警/样本/扫描记录串起来
        finding.evidence["traceId"] = trace_id

    if not persist:
        return evaluation, 0

    observations = [
        {
            "scanId": scan_id, "warehouse": ctx.warehouse, "queueType": row["queueType"],
            "value": row["value"], "observedAt": observed_at,
            "ruleVersion": BACKLOG_RULE_VERSION, "sourceStatus": "ok",
            "traceId": trace_id, "configHash": config_hash_value,
        }
        for row in valid
    ]
    saved = await store.save_backlog_observations(observations)
    return evaluation, saved


async def _auto_resolve_cleared(
    store: ScanStore,
    *,
    evaluations: dict[str, RuleEvaluation],
    rule_ok: dict[str, bool],
    findings: dict[str, Finding],
    scan_id: str,
    warehouse: str,
    trace_id: str,
    started_at: str,
    dry_run: bool,
    partial: bool,
    counts: dict[str, Any],
) -> None:
    """阶段5 安全自动 resolved。

    关闭条件（全部满足才关）：
      1. 非 dryRun；
      2. 该规则本次取数可信（源 status=ok 且未截断）；
      3. 整次扫描非 partial（无超时 / 分页漂移 / 截断）；
      4. 该规则本次没有数据质量跳过（时间缺失、未来、数值非法 → 不算“已评估且正常”）；
      5. 覆盖记录已落库；
      6. 告警仓库 / ruleId / ruleVersion 与本次规则一致；
      7. 告警 last_seen_at < 本次扫描 startedAt（乱序 / 并发扫描不关）；
      8. 告警对象本次未命中（命中集 = 本次 findings 的 (rule_id, object_id)）；
      9. 告警仍是 open / acknowledged（ignored 终态不复活）。

    “本次覆盖集中不存在该告警对象”按“该对象本次未违反条件”解读：
    覆盖集记录的是本次评估过的对象（命中与未命中都记），其中仍违反条件的对象构成命中集；
    命中集之外的告警对象说明异常条件已经消失（要么本次评估正常，要么源里已不存在），
    因此可以关闭。数据质量跳过的规则被整体禁用，宁可漏关不可误关。
    """
    if dry_run:
        # dryRun 不产生任何副作用：既不落覆盖记录，也不关闭告警。
        return

    evaluated_at = _now_iso()
    coverage_rows: list[dict[str, Any]] = []
    for evaluation in evaluations.values():
        for key in evaluation.evaluated_keys:
            coverage_rows.append({
                "scanId": scan_id,
                "warehouse": warehouse,
                "evaluatedAt": evaluated_at,
                **key.as_row(),
            })
    # 覆盖记录先幂等落库（后续关闭以它为证据）。
    if coverage_rows:
        await store.save_evaluated_objects(coverage_rows)

    if partial:
        # partial：本次评估不完整，任何关闭都可能误关。
        return

    skipped: set[str] = set()
    for evaluation in evaluations.values():
        skipped.update(evaluation.data_quality_skipped)
    eligible = sorted(
        rule_id for rule_id, ok in rule_ok.items() if ok and rule_id not in skipped
    )
    if not eligible:
        return

    hit_objects = {
        (finding.rule_id, finding.object_id) for finding in findings.values()
    }
    candidates = await store.list_auto_resolve_candidates(
        warehouse=warehouse, rule_ids=eligible, before_iso=started_at,
    )
    for candidate in candidates:
        rule_id = str(candidate.get("ruleId") or "")
        object_id = str(candidate.get("objectId") or "")
        if (rule_id, object_id) in hit_objects:
            # 本次仍命中：条件没有消失，不关。
            continue
        scan_type = RULE_ID_TYPES.get(rule_id)
        expected_version = RULE_VERSIONS.get(scan_type or "")
        if not expected_version or candidate.get("ruleVersion") != expected_version:
            # 规则版本不一致：不自动关（避免旧版本告警被新版本语义误关）。
            counts["staleCheckSkipped"] = counts.get("staleCheckSkipped", 0) + 1
            continue
        closed = await store.auto_resolve_alert(
            int(candidate["alertId"]),
            reason=(
                f"condition_cleared: {rule_id} 对象 {object_id} 在扫描 {scan_id} 中未再命中"
            ),
            scan_id=scan_id, trace_id=trace_id, before_iso=started_at,
            rule_id=rule_id, rule_version=expected_version, warehouse=warehouse,
        )
        if closed:
            counts["alertsAutoResolved"] = counts.get("alertsAutoResolved", 0) + 1
        else:
            # 与用户 resolve/ignore 并发：条件 UPDATE 未命中，交给状态机判定。
            counts["staleCheckSkipped"] = counts.get("staleCheckSkipped", 0) + 1


def _is_non_negative_number(value: Any) -> bool:
    """快照值合法性：非布尔、有限、非负（负值是数据质量问题，不参与基线）。"""
    if value is None or isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == number and number not in (float("inf"), float("-inf")) and number >= 0


def _partial_finding(scan_id: str, ctx: RuleContext) -> Finding:
    return Finding(
        rule_id="SCAN-PARTIAL", rule_version="v1", severity="P2",
        object_type="scan", object_id=scan_id,
        dimension={"warehouse": ctx.warehouse},
        evidence={"reason": "source partial", "observedAt": ctx.now.isoformat()},
        suggested_actions=("RETRY_SCAN",),
    )


async def _persist_findings(
    findings: dict[str, Finding], store: ScanStore, scan_id: str, warehouse: str,
    observed_at: str, notification_mode: str, counts: dict[str, Any], *,
    trace_id: str, config: dict[str, Any], actor_type: str | None,
    actor_id: str | None, configured_recipients: list[str],
    recipient_user_id: str | None = None,
) -> None:
    """落告警/事件/通知：三者由存储在同一事务内提交。

    - created：新建告警 + created 事件 + 通知；
    - escalated：级别高于更新前 → escalated 事件 + 通知；
    - updated：复发且级别不升 → 只累计 occurrence；
    - suppressed：被未到期的 ignored 抑制 → 不写任何行、不通知、单独计数；
    - replayed：租约失效后同一 (scanId, traceId, fingerprint) 重放 → 不增
      occurrence、不写事件/通知，仅计数（fencing 保护到告警副作用）。

    ``recipient_user_id`` 是接收人的稳定 id（手动扫描有，定时接收人只有用户名）。
    通知状态语义：dry_run 只落记录不发送；in_app 在告警事务内直接写成 sent。
    """
    status = (
        "dry_run" if notification_mode == "dry_run"
        else ("sent" if notification_mode == "in_app" else "pending")
    )
    for finding in findings.values():
        roles, recipients = resolve_route_targets(
            finding,
            warehouse=warehouse,
            actor_type=actor_type,
            actor_id=actor_id,
            config=config,
            configured_recipients=configured_recipients,
        )
        alert = finding.to_alert()
        alert["warehouseId"] = warehouse
        alert["assignee"] = None
        alert["scanId"] = scan_id
        alert["traceId"] = trace_id
        alert["title"] = f"{finding.rule_id} {finding.severity} {finding.object_id}"
        alert["lastSeenAt"] = observed_at
        # routed_to 表示责任岗位；assignee 仍由用户认领后写入，不能由路由自动抢占。
        alert["routedTo"] = ",".join(roles) if roles else None
        notification = None
        if recipients:
            notification = {
                "channel": "in_app",
                "recipients": list(recipients),
                "recipientUserId": recipient_user_id,
                "status": status,
                "payloadDigest": finding.fingerprint,
                "scope": trace_id,
            }
        result = await store.upsert_alert(alert, notification=notification)
        if result.outcome == UPSERT_CREATED:
            counts["alertsCreated"] += 1
            _count_notification(counts, result.notification_saved, recipients)
        elif result.outcome == UPSERT_ESCALATED:
            counts["alertsEscalated"] += 1
            counts["alertsUpdated"] += 1
            _count_notification(counts, result.notification_saved, recipients)
        elif result.outcome == UPSERT_SUPPRESSED:
            counts["alertsSuppressed"] += 1
        elif result.outcome == UPSERT_REPLAYED:
            counts["alertsReplayed"] += 1
        else:
            counts["alertsUpdated"] += 1


def _count_notification(
    counts: dict[str, Any], saved: bool, recipients: list[str]
) -> None:
    if saved:
        counts["notifications"] += 1
    elif not recipients:
        counts["notificationsUnrouted"] += 1