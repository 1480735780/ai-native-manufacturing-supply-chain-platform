"""巡检持久队列 worker：启动恢复 + 周期恢复 + 轮询消费 + 租约心跳 + PG 故障拒绝。

- 定时器默认关闭；worker 随服务启动，只消费已落库的 queued 记录；
- 领取即写租约（lease_owner/leased_at）并把 attempt+1；执行期间按租约周期的 1/3 心跳续租；
- 租约过期（进程崩溃/长时间无心跳）的 running 由周期恢复重新入队，attempt 用尽则 failed(stale)；
- 回写一律 fencing：租约被别的 worker 接手后，旧执行者的结果被丢弃（ScanLeaseLostError）；
- 服务账号扫描在消费时现取短时令牌，不持久化用户 JWT；执行身份取自令牌 claims，
  不再用角色名硬编码；
- PG 故障时抛 ScanStoreUnavailableError，由 lifespan 决定拒绝启动。
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import ScanConfigError, Settings
from app.llm.provider import LLMProvider, ProviderError, build_provider
from app.scan.config import load_config_snapshot
from app.scan.repository import (
    MAX_ATTEMPTS, ScanStore, ScanLeaseLostError, ScanStoreUnavailableError,
)
from app.scan.service import run_scan
from app.security import AuthError, Principal, decode_principal, load_public_key
from app.tools.gateway_client import GatewayClient

logger = logging.getLogger(__name__)

__all__ = [
    "MAX_ATTEMPTS", "ScanLeaseLostError", "ScanWorker", "ServiceTokenError",
    "acquire_service_token", "decode_service_principal", "validate_service_principal",
    "execute_queued_scan", "recover_stale_runs", "worker_identity",
]

# 服务短时令牌的硬性 claim 约定（与 Java AgentServiceProperties / AgentTokenSigner 对齐）。
SERVICE_TOKEN_USE = "agent_service"
SERVICE_READ_AUTHORITY = "insp_read"


class ServiceTokenError(RuntimeError):
    """服务令牌获取失败（auth_failed）。"""


def worker_identity() -> str:
    """租约持有者标识：主机 + 进程 + 随机后缀，区分同机多实例。"""
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


SERVICE_TOKEN_ATTEMPTS = 3
SERVICE_TOKEN_RETRY_BASE_SECONDS = 0.5


async def acquire_service_token(settings: Settings, warehouse: str | None) -> str:
    """从 /login/service-token 取短时令牌；失败抛 ServiceTokenError。

    网关经 Nacos 解析 wms-login 实例，Nacos gRPC 存在间歇性 3s 超时（网关日志
    ``get services from nacos server fail`` → 502）。单次抖动不应让整次扫描直接
    ``failed(auth_failed)``，故对传输层错误与 502/503/504 做有限次退避重试；
    401/403 等确定性拒绝不重试，避免掩盖配置错误。
    """
    if not settings.service_api_key or not settings.service_key_id:
        raise ServiceTokenError("api_key_or_key_id_missing")
    headers = {
        "X-Agent-Api-Key": settings.service_api_key,
        "X-Agent-Key-Id": settings.service_key_id,
    }
    if warehouse:
        headers["X-Agent-Warehouse"] = warehouse

    last_error: ServiceTokenError | None = None
    for attempt in range(1, SERVICE_TOKEN_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.post(
                    settings.service_token_url, headers=headers, json={}
                )
        except httpx.HTTPError as exc:
            last_error = ServiceTokenError(f"transport: {type(exc).__name__}")
        else:
            if response.status_code < 400:
                break
            if response.status_code in (502, 503, 504):
                last_error = ServiceTokenError(f"http_{response.status_code}")
            else:
                # 确定性拒绝（401/403/404/422…）：不重试，直接暴露配置问题
                raise ServiceTokenError(f"http_{response.status_code}")
        if attempt < SERVICE_TOKEN_ATTEMPTS:
            await asyncio.sleep(SERVICE_TOKEN_RETRY_BASE_SECONDS * attempt)
    else:
        raise last_error  # type: ignore[misc]

    try:
        body = response.json()
    except ValueError as exc:
        raise ServiceTokenError("invalid_payload") from exc
    token = (body.get("data") or {}).get("token")
    if not token:
        raise ServiceTokenError("token_missing")
    return token


def decode_service_principal(token: str, public_key: str) -> Principal:
    """验签服务令牌并取出真实服务账号身份（executorId = 令牌里的账号名）。

    这里只负责验签 + 身份提取；claim 的合法性（token_use/角色/账号/仓库）由
    :func:`validate_service_principal` 统一校验，二者分开便于独立测试与 mock。
    """
    try:
        principal = decode_principal(token, public_key)
    except AuthError as exc:
        raise ServiceTokenError(f"invalid_token: {exc.message}") from exc
    if not principal.user_name:
        raise ServiceTokenError("token_missing_subject")
    return principal


def validate_service_principal(
    principal: Principal, settings: Settings, warehouse: str | None
) -> str | None:
    """校验服务短时令牌的全部 claim；返回失败摘要（auth_failed:*），通过返回 None。

    对齐 Java ``AgentTokenSigner`` 写出的 claim：``token_use=agent_service``、
    ``authorities=[insp_read]``、``user_name`` 为固定只读账号、``warehouse_scope``
    非空且包含本次扫描仓库。任一项不满足都 fail-closed，绝不拿用户 JWT 或
    其他账号签发的令牌冒充执行身份。
    """
    if principal.token_use != SERVICE_TOKEN_USE:
        return "auth_failed:token_use"
    if SERVICE_READ_AUTHORITY not in principal.authorities:
        return "auth_failed:authority"
    if principal.user_name != settings.service_account_name:
        return "auth_failed:account"
    if not warehouse or not principal.warehouse_scope or warehouse not in principal.warehouse_scope:
        return "auth_failed:warehouse_scope"
    return None


async def recover_stale_runs(store: ScanStore, settings: Settings) -> int:
    """把租约过期（超过 scan_lease_seconds 无心跳）的 running 重新入队或标 failed(stale)。"""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(seconds=settings.scan_lease_seconds)
    ).isoformat()
    try:
        return await store.recover_stale(cutoff, max_scan=100)
    except ScanStoreUnavailableError:
        raise


async def execute_queued_scan(
    run: dict[str, Any], *, store: ScanStore, settings: Settings,
    client: GatewayClient, token: str | None = None,
) -> dict[str, Any]:
    """消费一条队列记录：取短时服务令牌，以租约 fencing 执行 run_scan。

    ``token`` 仅供同步执行路径注入本次请求 JWT（不落库）。worker 异步消费时不传，
    **统一用服务账号**的短时令牌取数（用户 JWT 从不入队）；执行身份从令牌 claims 解出，
    扫描记录保留发起用户（actorId/actorType）与执行身份（executorId/executorType）。
    所有回写都带 ``run["leaseOwner"]`` 做 fencing，租约失效抛 ScanLeaseLostError。
    """
    lease_owner = run.get("leaseOwner") or worker_identity()
    warehouse = run.get("warehouse")

    async def _fail(summary: str) -> dict[str, Any]:
        failed = dict(run)
        failed["status"] = "failed"
        failed["errorSummary"] = summary
        failed["finishedAt"] = datetime.now(timezone.utc).isoformat()
        await store.save_run(failed, lease_owner=lease_owner)
        return failed

    if token is None:
        # 异步路径：定时与手动扫描都用服务账号取数，统一只读身份
        try:
            token = await acquire_service_token(settings, warehouse)
            principal = decode_service_principal(
                token, load_public_key(settings.jwt_public_key_path)
            )
        except (ServiceTokenError, AuthError) as exc:
            # 取 token 失败 → failed(auth_failed)，不回退管理员 token
            return await _fail(f"auth_failed:{exc}")
        invalid = validate_service_principal(principal, settings, warehouse)
        if invalid is not None:
            return await _fail(invalid)
    else:
        # 同步路径：调用方持有本次请求 JWT，直接复用（不落库）
        principal = Principal(
            user_id=run.get("actorId"), user_name=run.get("actorId") or "",
            authorities=("insp_read",),
            warehouse_scope=(warehouse,) if warehouse else (),
            token_use="agent_service",
        )

    # 快照检查放在鉴权之后：鉴权失败是更早的失败语义，缺快照属于配置完整性失败。
    # 入队时冻结的 canonical JSON 是唯一执行依据，绝不回退读当前 scan.yaml。
    snapshot = run.get("configSnapshot")
    if not snapshot:
        return await _fail("config_snapshot_missing")
    try:
        loaded = load_config_snapshot(
            snapshot,
            expected_hash=run.get("configHash"),
            expected_version=run.get("configVersion"),
        )
    except ScanConfigError as exc:
        return await _fail(str(exc))
    config = loaded.config

    # 阶段6：只按入队快照里的 llm 配置决定是否构建 LLM provider；是否调用、上限、超时
    # 全部取自快照。provider 构建失败不等于扫描失败：退回模板摘要（不漏报）。
    llm_provider = _build_llm_provider(settings, config)

    # principal 用服务账号身份执行取数；发起用户身份仍保留在 run 的 actor 字段。
    return await run_scan(
        scan_id=run["scanId"],
        scan_types=run.get("scanTypes") or [],
        principal=principal,
        token=token,
        client=client,
        store=store,
        allowed_warehouses=list(config["warehouses"]),
        requested_warehouse=warehouse,
        dry_run=bool(run.get("dryRun")),
        notification_mode=run.get("notificationMode") or config["notifications"]["mode"],
        config=config,
        config_hash_value=run.get("configHash"),
        request_id=run.get("requestId"),
        schedule_slot=run.get("scheduleSlot"),
        scan_key=run.get("scanKey"),
        executor_type="service",
        executor_id=principal.user_name,
        actor_type=run.get("actorType"),
        trigger=run.get("trigger"),
        actor_id=run.get("actorId"),
        claimed=run,
        lease_owner=lease_owner,
        recipients=list(config["notifications"].get("recipients") or []),
        llm_provider=llm_provider,
    )


def _build_llm_provider(settings: Settings, config: dict[str, Any]) -> LLMProvider | None:
    """快照 ``llm.enabled`` 为真时按环境配置构建 provider；关闭或构建失败返回 None。"""
    if not bool((config.get("llm") or {}).get("enabled")):
        return None
    try:
        return build_provider(settings)
    except ProviderError as exc:
        logger.warning("llm provider unavailable, summaries fall back to template: %s", exc)
        return None


class ScanWorker:
    """后台轮询 worker（定时器关闭时仍消费队列）。"""

    def __init__(
        self, *, store: ScanStore, settings: Settings, client: GatewayClient,
        worker_id: str | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.client = client
        self.worker_id = worker_id or worker_identity()
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._last_recovery = 0.0

    async def start(self) -> None:
        self._running = True
        await self._recover()
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _recover(self) -> None:
        self._last_recovery = time.monotonic()
        recovered = await recover_stale_runs(self.store, self.settings)
        if recovered:
            logger.info("scan worker recovered %s stale run(s)", recovered)

    def _recovery_interval(self) -> float:
        return max(
            float(self.settings.scan_worker_poll_seconds),
            self.settings.scan_lease_seconds / 3.0,
        )

    async def _maybe_recover(self) -> None:
        """周期恢复：不只靠启动那一次，运行中崩溃的 worker 也能被接手。"""
        if time.monotonic() - self._last_recovery >= self._recovery_interval():
            await self._recover()

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._maybe_recover()
                run = await self.store.claim_next_queued(self.worker_id)
            except ScanStoreUnavailableError as exc:
                logger.warning("scan worker store unavailable: %s", exc)
                await asyncio.sleep(self.settings.scan_worker_poll_seconds)
                continue
            if run is None:
                await asyncio.sleep(self.settings.scan_worker_poll_seconds)
                continue
            try:
                await self._execute_with_heartbeat(run)
            except ScanLeaseLostError as exc:
                logger.warning("scan %s result discarded: %s", run.get("scanId"), exc)
            except asyncio.CancelledError:
                if not self._running:
                    raise
                logger.warning("scan %s execution cancelled (lease lost)", run.get("scanId"))
            except Exception as exc:  # noqa: BLE001 - 单条失败不影响 worker
                logger.warning("scan worker task failed: %s", type(exc).__name__)

    async def _execute_with_heartbeat(self, run: dict[str, Any]) -> dict[str, Any]:
        lease = run.get("leaseOwner")
        execution = asyncio.create_task(
            execute_queued_scan(
                run, store=self.store, settings=self.settings, client=self.client
            )
        )
        heartbeat = asyncio.create_task(self._heartbeat(run["scanId"], lease, execution))
        try:
            return await execution
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)

    async def _heartbeat(
        self, scan_id: str, lease_owner: str | None, execution: asyncio.Task[Any]
    ) -> None:
        """按租约周期的 1/3 续租；续不上说明租约已被别人接手，取消本次执行。"""
        interval = max(1.0, self.settings.scan_lease_seconds / 3.0)
        while True:
            await asyncio.sleep(interval)
            if not lease_owner:
                return
            try:
                renewed = await self.store.renew_lease(scan_id, lease_owner)
            except ScanStoreUnavailableError as exc:
                logger.warning("scan worker heartbeat store unavailable: %s", exc)
                continue
            if not renewed:
                logger.warning("scan %s lease lost, cancelling execution", scan_id)
                execution.cancel()
                return