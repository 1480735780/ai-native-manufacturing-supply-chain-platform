"""`/agent/health` 契约测试：响应体必须精确等于 `{"status":"ok"}`。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_exact_minimal_payload() -> None:
    response = client.get("/agent/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_leaks_no_extra_fields() -> None:
    """不得泄露版本、依赖或存储状态。"""
    body = client.get("/agent/health").json()

    assert set(body.keys()) == {"status"}
