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
from typing import Any
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
    return Principal(
        user_id=user_id,
        user_name=str(user_name),
        authorities=tuple(str(item) for item in raw_authorities),
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
        warnings=warnings,
    )
