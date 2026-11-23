"""F-009/F-010：JWT 自验、401 外壳与 `/agent/tools` 输出。"""

from __future__ import annotations

import json
import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.main import create_app
from app.security import decode_principal


def _client(monkeypatch, public_key_file) -> TestClient:
    monkeypatch.setenv("WMS_JWT_PUBLIC_KEY_PATH", public_key_file)
    return TestClient(create_app())


def _other_key_token() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return jwt.encode(
        {"exp": int(time.time()) + 3600, "user_name": "intruder"},
        private_pem,
        algorithm="RS256",
    )


def test_health_stays_anonymous(monkeypatch, public_key_file):
    client = _client(monkeypatch, public_key_file)
    response = client.get("/agent/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tools_without_token_is_rejected(monkeypatch, public_key_file):
    client = _client(monkeypatch, public_key_file)
    response = client.get("/agent/tools")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == 401
    assert body["data"] is None
    assert body["message"]


def test_tools_with_non_bearer_scheme_is_rejected(monkeypatch, public_key_file):
    client = _client(monkeypatch, public_key_file)
    response = client.get("/agent/tools", headers={"Authorization": "Basic abc"})
    assert response.status_code == 401


def test_tools_with_invalid_signature_is_rejected(monkeypatch, public_key_file):
    client = _client(monkeypatch, public_key_file)
    response = client.get(
        "/agent/tools", headers={"Authorization": f"Bearer {_other_key_token()}"}
    )
    assert response.status_code == 401
    assert response.json()["message"] == "token 无效"


def test_tools_with_expired_token_is_rejected(monkeypatch, public_key_file, token_factory):
    client = _client(monkeypatch, public_key_file)
    token = token_factory(exp=int(time.time()) - 10)
    response = client.get("/agent/tools", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["message"] == "token 已过期"


def test_tools_with_valid_token_lists_six_tools(monkeypatch, public_key_file, token_factory):
    client = _client(monkeypatch, public_key_file)
    token = token_factory(user_name="alice")
    response = client.get("/agent/tools", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 10000
    tools = body["data"]["tools"]
    assert len(tools) == 6
    assert {tool["name"] for tool in tools} == {
        "STOCK-QUERY",
        "EXP-WARN-QUERY",
        "DAYCHECK-NOUP",
        "DASH-PEND",
        "DASH-TREND",
        "DAYCHECK-DELAY",
    }
    assert all(tool["readOnly"] is True for tool in tools)


def test_user_header_mismatch_does_not_reject(monkeypatch, public_key_file, token_factory):
    client = _client(monkeypatch, public_key_file)
    token = token_factory(user_name="alice")
    response = client.get(
        "/agent/tools",
        headers={
            "Authorization": f"Bearer {token}",
            "user": json.dumps({"user_name": "bob"}),
        },
    )
    assert response.status_code == 200


def test_user_header_alone_cannot_authorize(monkeypatch, public_key_file):
    client = _client(monkeypatch, public_key_file)
    response = client.get(
        "/agent/tools", headers={"user": json.dumps({"user_name": "alice"})}
    )
    assert response.status_code == 401


def test_principal_reads_java_token_claims(rsa_keypair, token_factory):
    """Java 侧 JWT 写 `id`/`orgCode`/`realname`，用户名在 `sub`（JwtTokenEnhancerDataServiceImpl.java:38-41）。"""
    _, public_pem = rsa_keypair
    token = token_factory(
        id="u-42",
        sub="zhangsan",
        realname="张三",
        orgCode="ORG01",
        user_name="",
    )
    principal = decode_principal(token, public_pem)
    assert principal.user_id == "u-42"
    assert principal.user_name == "zhangsan"


def test_principal_prefers_user_name_claim(rsa_keypair, token_factory):
    _, public_pem = rsa_keypair
    token = token_factory(user_name="alice", id="u-7")
    principal = decode_principal(token, public_pem)
    assert principal.user_name == "alice"
    assert principal.user_id == "u-7"
