"""服务令牌仓库范围校验（安全收口）。

覆盖：
- 令牌带 warehouse_scope 时，请求仓库必须在令牌范围内；
- 多仓部署必须显式指定仓库；
- 越权仓库一律拒绝。
"""

from __future__ import annotations

import pytest

from app.security import (
    AuthError,
    Principal,
    check_warehouse_scope,
    decode_principal,
    load_public_key,
)


def _principal(scope: tuple[str, ...] = ()) -> Principal:
    return Principal(
        user_id="USR-AGENT-INSPECTOR",
        user_name="agent-inspector",
        authorities=("insp_read",),
        warehouse_scope=scope,
        token_use="agent_service" if scope else None,
    )


def test_single_warehouse_may_omit_request():
    assert check_warehouse_scope(_principal(), None, ["W01"]) == "W01"


def test_multi_warehouse_requires_explicit_request():
    with pytest.raises(AuthError):
        check_warehouse_scope(_principal(), None, ["W01", "W02"])


def test_multi_warehouse_accepts_allowed_warehouse():
    assert check_warehouse_scope(_principal(), "W02", ["W01", "W02"]) == "W02"


def test_warehouse_outside_allowed_is_rejected():
    with pytest.raises(AuthError):
        check_warehouse_scope(_principal(), "W99", ["W01"])


def test_token_scope_narrower_than_request_is_rejected():
    with pytest.raises(AuthError):
        check_warehouse_scope(_principal(("W01",)), "W02", ["W01", "W02"])


def test_token_scope_allows_contained_warehouse():
    assert check_warehouse_scope(_principal(("W01",)), "W01", ["W01", "W02"]) == "W01"


def test_empty_allowed_list_is_rejected():
    with pytest.raises(AuthError):
        check_warehouse_scope(_principal(), "W01", [])


def test_decode_principal_reads_warehouse_scope_and_token_use(
    public_key_file, token_factory
):
    token = token_factory(warehouse_scope=["W01"], token_use="agent_service")
    principal = decode_principal(token, load_public_key(public_key_file))
    assert principal.warehouse_scope == ("W01",)
    assert principal.token_use == "agent_service"
