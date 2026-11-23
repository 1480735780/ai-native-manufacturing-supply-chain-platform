"""测试公共夹具。

JWT 相关测试在本地现生成 RSA 密钥对，不依赖仓库内任何私钥材料。
"""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


@pytest.fixture(scope="session")
def rsa_keypair() -> tuple[str, str]:
    """生成一次性测试密钥对（私钥 PEM、公钥 PEM）。"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return private_pem, public_pem


@pytest.fixture(scope="session")
def public_key_file(tmp_path_factory, rsa_keypair) -> str:
    """把公钥写到临时文件，供 Settings 读取。"""
    path = tmp_path_factory.mktemp("jwt") / "public.pem"
    path.write_text(rsa_keypair[1], encoding="utf-8")
    return str(path)


@pytest.fixture(scope="session")
def token_factory(rsa_keypair):
    """签发测试 JWT 的工厂。"""
    private_pem = rsa_keypair[0]

    def make(**claims) -> str:
        payload: dict[str, object] = {
            "exp": int(time.time()) + 3600,
            "user_name": "tester",
        }
        payload.update(claims)
        return jwt.encode(payload, private_pem, algorithm="RS256")

    return make
