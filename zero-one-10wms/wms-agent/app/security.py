"""JWT 自验与身份提取（ADR-007 §鉴权）。

约定：
- 只认 `Authorization: Bearer <JWT>`，用 public.pem 验 RS256 签名并校验 exp；
- 身份优先取 JWT 里的 `user_name`（兼容 `username`、`sub`、`realname`），
  用户 id 取 `id`（Java 侧 JwtTokenEnhancerDataServiceImpl.java:38 写入），其次 `user_id`、`sub`；
- 网关下发的 `user` 请求头只作交叉校验，不作权威；不一致只记 warning，不拒绝；
- 缺 token / 签名无效 / 过期一律拒绝，不 fallback 到 user 头。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote

import jwt
from fastapi import Request

from app.config import get_settings

BEARER_PREFIX = "bearer "


class AuthError(Exception):
    """鉴权失败，调用方应返回 401。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class Principal:
    """已通过验签的身份。"""

    user_id: str | None
    user_name: str
    authorities: tuple[str, ...] = ()
    warehouse_scope: tuple[str, ...] = ()
    token_use: str | None = None
    warnings: tuple[str, ...] = ()


def resolve_public_key_path(path: str) -> Path:
    """定位公钥文件：依次尝试原路径、CWD 相对路径、包根相对路径。"""
    candidates = [
        Path(path),
        Path.cwd() / path,
        Path(__file__).resolve().parents[1] / path,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise AuthError("JWT 公钥文件不可用")


def load_public_key(path: str) -> str:
    """读取公钥内容。"""
    try:
        return resolve_public_key_path(path).read_text(encoding="utf-8")
    except AuthError:
        raise
    except OSError as exc:
        raise AuthError("JWT 公钥文件不可读") from exc


def decode_principal(token: str, public_key: str) -> Principal:
    """验签并提取身份。"""
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"require": ["exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("token 已过期") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("token 无效") from exc

    user_name = (
        claims.get("user_name")
        or claims.get("username")
        or claims.get("sub")
        or claims.get("realname")
        or ""
    )
    # Java 侧把用户 id 放进 `id`（JwtTokenEnhancerDataServiceImpl.java:38），
    # `sub` 在 Spring Security 中通常是用户名，仅作兜底候选。
    raw_user_id = claims.get("id")
    if raw_user_id is None:
        raw_user_id = claims.get("user_id")
    if raw_user_id is None:
        raw_user_id = claims.get("sub")
    user_id = str(raw_user_id) if raw_user_id is not None else None
    raw_authorities = claims.get("authorities") or []
    if isinstance(raw_authorities, str):
        raw_authorities = [raw_authorities]
    raw_scope = claims.get("warehouse_scope") or []
    if isinstance(raw_scope, str):
        raw_scope = [raw_scope]
    token_use = claims.get("token_use")
    return Principal(
        user_id=user_id,
        user_name=str(user_name),
        authorities=tuple(str(item) for item in raw_authorities),
        warehouse_scope=tuple(str(item) for item in raw_scope),
        token_use=str(token_use) if token_use is not None else None,
    )


def cross_check_user_header(request: Request, principal: Principal) -> tuple[str, ...]:
    """把网关下发的 `user` 头与 JWT 身份交叉校验。

    只产出 warning，不拒绝请求。
    """
    raw = request.headers.get("user")
    if not raw:
        return ()
    try:
        data = json.loads(unquote(raw))
    except (json.JSONDecodeError, ValueError):
        return ("网关 user 头无法解析，已忽略",)
    if not isinstance(data, dict):
        return ("网关 user 头格式异常，已忽略",)

    header_name = data.get("user_name") or data.get("username")
    if header_name and principal.user_name and str(header_name) != principal.user_name:
        return (f"网关 user 头与 JWT 身份不一致：user={header_name}",)
    return ()


def extract_bearer_token(request: Request) -> str:
    """从 Authorization 头取出裸 JWT。

    工具调用要把用户 JWT 原样透传给 Gateway，因此这里返回原始 token 字符串。
    """
    header = request.headers.get("Authorization") or ""
    if not header.lower().startswith(BEARER_PREFIX):
        raise AuthError("缺少 Bearer token")
    token = header[len(BEARER_PREFIX) :].strip()
    if not token:
        raise AuthError("缺少 Bearer token")
    return token


async def require_principal(request: Request) -> Principal:
    """FastAPI 依赖：缺 token / 验签失败 / 过期都抛 AuthError。"""
    token = extract_bearer_token(request)

    settings = get_settings()
    public_key = load_public_key(settings.jwt_public_key_path)
    principal = decode_principal(token, public_key)
    warnings = cross_check_user_header(request, principal)
    return Principal(
        user_id=principal.user_id,
        user_name=principal.user_name,
        authorities=principal.authorities,
        warehouse_scope=principal.warehouse_scope,
        token_use=principal.token_use,
        warnings=warnings,
    )


def check_warehouse_scope(
    principal: Principal,
    requested: str | None,
    allowed: list[str],
) -> str:
    """校验巡检请求的仓库范围，返回生效仓库。

    规则（实施方案 §5.3 / 安全收口）：
    - 服务端只允许 `allowed`（配置 `WMS_AGENT_SCAN_WAREHOUSES`）内的仓库；
    - 多仓配置必须显式指定仓库，单仓配置允许省略；
    - 令牌带 `warehouse_scope` 时，请求仓库必须在令牌范围内；
    - 越权一律拒绝，不做静默降级。
    """
    if not allowed:
        raise AuthError("未配置巡检仓库范围")

    target = (requested or "").strip()
    if not target:
        if len(allowed) != 1:
            raise AuthError("多仓部署必须显式指定仓库")
        target = allowed[0]
    if target not in allowed:
        raise AuthError(f"仓库 {target} 不在允许范围内")

    if principal.warehouse_scope and target not in principal.warehouse_scope:
        raise AuthError(f"令牌仓库范围不包含 {target}")
    return target


# 巡检权限码（与 Java 侧菜单/角色种子一致）
ADMIN_AUTHORITIES = frozenset({"gly", "ROLE_ADMIN", "admin"})
# 三种权限各自独立：只读权限码不能发起扫描，也不能操作告警。
PERM_ALERT_VIEW = "inspection:alert:view"
PERM_SCAN_TRIGGER = "inspection:scan:trigger"
PERM_ALERT_HANDLE = "inspection:alert:handle"
# 菜单 MENU-DAILY-CHECK-05 可见的业务角色（实施方案 §12.1：仓库经理 ckjl / 仓库管理 cg）。
# 菜单可见则 API 必须可用，否则页面一打开就是 403。
INSPECTION_ROLES = frozenset({"ckjl", "cg"})
# 只读巡检角色：服务账号绑定 insp_read；人类用户持有它只能查看。
SCAN_READ_AUTHORITIES = frozenset({"insp_read", PERM_ALERT_VIEW})


def has_authority(principal: Principal, authority: str) -> bool:
    """权限码比较忽略大小写。"""
    lower = authority.lower()
    return any(item.lower() == lower for item in principal.authorities)


def has_any_authority(principal: Principal, authorities: Iterable[str]) -> bool:
    lowered = {str(item).lower() for item in authorities}
    return any(str(item).lower() in lowered for item in principal.authorities)


def is_scan_admin(principal: Principal) -> bool:
    return has_any_authority(principal, ADMIN_AUTHORITIES)


def is_service_account(principal: Principal) -> bool:
    return principal.token_use == "agent_service"


def can_trigger_scan(principal: Principal) -> bool:
    """发起巡检（手动 / 定时）。

    - 服务账号只允许 trigger（定时触发须持只读巡检角色），不能看告警、不能操作；
    - 人类用户须管理员、`inspection:scan:trigger` 或巡检业务角色；
    - 只读权限码 `inspection:alert:view` 不能发起扫描。
    """
    if is_service_account(principal):
        return has_any_authority(principal, SCAN_READ_AUTHORITIES)
    return is_scan_admin(principal) or has_any_authority(
        principal, {PERM_SCAN_TRIGGER, *INSPECTION_ROLES}
    )


def can_view_scan(principal: Principal, run: dict[str, Any]) -> bool:
    """查询扫描：只能查本人且仓库在令牌范围内；服务账号扫描仅管理员可见。"""
    if run.get("actorType") == "service":
        return is_scan_admin(principal)
    if principal.token_use == "agent_service":
        return False
    if principal.warehouse_scope and run.get("warehouse") not in principal.warehouse_scope:
        return False
    actor_id = run.get("actorId")
    return bool(actor_id) and actor_id == principal.user_name


def can_retry_scan(principal: Principal, run: dict[str, Any]) -> bool:
    """重试扫描：仅管理员，且原扫描必须归本人或由服务账号发起。

    - retry 是管理员接口：巡检业务角色（ckjl/cg）、`inspection:scan:trigger` 权限码、
      服务账号都不能重试（它们能发起扫描，不等于能按别人的原配置重跑）；
    - 原扫描归属沿用查询规则（`can_view_scan`）：本人发起的手动扫描，或服务账号
      发起的定时扫描；他人发起的手动扫描不可重试，避免借 retry 绕过扫描可见性。
    """
    if is_service_account(principal):
        return False
    if not is_scan_admin(principal):
        return False
    return can_view_scan(principal, run)


def can_view_scan_summaries(principal: Principal, run: dict[str, Any]) -> bool:
    """查询扫描摘要：能看扫描记录的人，或能看该仓库告警的人。

    摘要只是告警聚合后的表达层（规则、仓库、客户、级别分布、样本标签、建议动作），
    不含配置快照、触发身份与计数明细。告警详情抽屉按 scanId 取摘要，而定时巡检由
    服务账号发起，`can_view_scan` 对巡检业务角色不可见；照搬会让仓库经理看不到自己
    告警的摘要。能看某仓库告警的人已经能看到这些告警本身，摘要不扩大可见范围。
    仓库范围由调用方按令牌范围判定。
    """
    if can_view_scan(principal, run):
        return True
    return can_view_alerts(principal)


def can_view_alerts(principal: Principal) -> bool:
    """查看告警列表：只读权限（权限码 / 只读角色 / 巡检业务角色 / 管理员）。

    服务账号只负责 trigger，不开放告警读取。
    """
    if is_service_account(principal):
        return False
    return is_scan_admin(principal) or has_any_authority(
        principal, {*SCAN_READ_AUTHORITIES, *INSPECTION_ROLES}
    )


def can_operate_alert(principal: Principal) -> bool:
    """告警状态操作（ack/resolve/ignore）：须 handle 权限码、巡检业务角色或管理员。

    服务账号（agent_service）只读，禁止 ack/resolve/ignore；
    只读权限码 `inspection:alert:view` 不足以操作告警。
    """
    if is_service_account(principal):
        return False
    return is_scan_admin(principal) or has_any_authority(
        principal, {PERM_ALERT_HANDLE, *INSPECTION_ROLES}
    )


def can_view_notifications(principal: Principal) -> bool:
    """查看/标记本人站内通知。

    通知按接收人隔离（稳定 user_id，缺失时回退用户名），因此任何登录用户
    只能读到自己的通知；服务账号只读巡检，不开放通知入口。
    """
    return not is_service_account(principal)


def notification_identity(principal: Principal) -> tuple[str | None, str | None]:
    """(稳定 user_id, 用户名)：通知归属判定用，缺一可退化为按用户名匹配。"""
    return (principal.user_id or None, principal.user_name or None)


def effective_warehouse_scope(principal: Principal, allowed: list[str]) -> list[str]:
    """本次请求可见的仓库：令牌 `warehouse_scope` ∩ 服务端允许范围（保序去重）。

    普通 wms-login 用户 JWT 没有 `warehouse_scope` claim，按服务端配置范围处理；
    服务令牌带 claim，超出允许范围的部分直接丢弃，空范围由调用方拒绝（不静默放行）。
    """
    if principal.warehouse_scope:
        candidates = [w for w in principal.warehouse_scope if w in allowed]
    else:
        candidates = list(allowed)
    return list(dict.fromkeys(candidates))