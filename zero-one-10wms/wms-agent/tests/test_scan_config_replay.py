"""阶段4：入队冻结配置、worker 快照回放、路由与扫描预算。"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.scan import router as scan_router
from app.scan.config import canonical_json, hash_config, load_scan_config
from app.scan.repository import MemoryScanStore
from app.scan.service import DEFAULT_CONFIG, run_scan
from app.scan.worker import execute_queued_scan
from app.security import Principal, require_principal
from app.tools.gateway_client import GatewayClient

TOKEN = "header.payload.signature"
NOUP_PATH = "/daycheck/no-up/get-no-up-goods-page"


def _config(*, p2_hours: float = 2.0, mode: str = "dry_run") -> dict[str, Any]:
    data = json.loads(canonical_json(DEFAULT_CONFIG))
    data["rules"]["noUp"]["p2Hours"] = p2_hours
    data["notifications"] = {"mode": mode, "recipients": ["admin"]}
    data["routing"] = [
        {
            "rule_id": "NOUP-OVERDUE",
            "warehouse": "W01",
            "assignee_role": "putaway_lead",
            "recipients": ["route-user"],
        }
    ]
    return data


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        WMS_AGENT_SCAN_WAREHOUSES="W01",
        WMS_AGENT_NOTIFICATION_MODE="dry_run",
        WMS_AGENT_ALERT_RECIPIENTS="admin",
    )


def _principal() -> Principal:
    return Principal(user_id="u-1", user_name="tester", authorities=("ckjl",))


def _row(age_hours: float = 3.0) -> dict[str, Any]:
    return {
        "rowId": "R1",
        "noticeId": "N1",
        "goods_id": "G1",
        "tin_id": "T1",
        "cus_code": "C1",
        "create_date": (datetime.now(timezone.utc) - timedelta(hours=age_hours)).isoformat(),
    }


def _gateway(rows: list[dict[str, Any]] | None = None) -> GatewayClient:
    rows = rows or []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 10000,
                "data": {"rows": rows, "total": len(rows), "pages": 1 if rows else 0},
            },
        )

    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))


def _queued(config: dict[str, Any], scan_id: str = "scan-replay") -> dict[str, Any]:
    snapshot = canonical_json(config)
    return {
        "scanId": scan_id,
        "trigger": "manual",
        "actorType": "user",
        "actorId": "tester",
        "actorUserId": "u-1",
        "status": "queued",
        "partial": False,
        "sourceStatus": [],
        "configHash": hash_config(config),
        "configSnapshot": snapshot,
        "configVersion": config["version"],
        "ruleVersion": "no_up=v0.2.0",
        "scanTypes": ["no_up"],
        "requestId": None,
        "scheduleSlot": None,
        "scanKey": scan_id,
        "queuedAt": datetime.now(timezone.utc).isoformat(),
        "startedAt": None,
        "finishedAt": None,
        "attempt": 0,
        "counts": {},
        "errorSummary": None,
        "warehouse": "W01",
        "dryRun": False,
        "notificationMode": config["notifications"]["mode"],
        "payloadHash": "sha256:p",
        "traceId": "trace-replay",
    }


async def test_worker_uses_queue_snapshot_after_yaml_changes(tmp_path: Path) -> None:
    config_a = _config(p2_hours=2.0)
    path = tmp_path / "scan.yaml"
    path.write_text(yaml.safe_dump(config_a, sort_keys=False), encoding="utf-8")
    assert load_scan_config(path).config["rules"]["noUp"]["p2Hours"] == 2.0

    config_b = _config(p2_hours=4.0)
    config_b["rules"]["noUp"]["p1Hours"] = 5.0
    path.write_text(yaml.safe_dump(config_b, sort_keys=False), encoding="utf-8")
    assert load_scan_config(path).config["rules"]["noUp"]["p2Hours"] == 4.0

    store = MemoryScanStore()
    await store.insert_run(_queued(config_a))
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None
    run = await execute_queued_scan(
        claimed,
        store=store,
        settings=_settings(),
        client=_gateway([_row(age_hours=3.0)]),
        token=TOKEN,
    )

    assert run["status"] == "succeeded"
    assert run["configHash"] == hash_config(config_a)
    assert json.loads(run["configSnapshot"])["rules"]["noUp"]["p2Hours"] == 2.0
    alerts = list(store.alerts.values())
    assert len(alerts) == 1 and alerts[0]["severity"] == "P2"
    assert alerts[0]["routedTo"] == "putaway_lead"
    assert {n["recipient"] for n in store.notifications} == {"tester"}


async def test_worker_rejects_missing_or_tampered_snapshot() -> None:
    store = MemoryScanStore()
    config = _config()
    await store.insert_run(_queued(config))
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None

    missing = dict(claimed)
    missing.pop("configSnapshot", None)
    failed = await execute_queued_scan(
        missing, store=store, settings=_settings(), client=_gateway(), token=TOKEN
    )
    assert failed["status"] == "failed"
    assert failed["errorSummary"] == "config_snapshot_missing"

    tampered_store = MemoryScanStore()
    await tampered_store.insert_run(_queued(config))
    tampered_claimed = await tampered_store.claim_next_queued("worker-a")
    assert tampered_claimed is not None
    tampered = dict(tampered_claimed)
    tampered["configHash"] = "sha256:tampered"
    failed = await execute_queued_scan(
        tampered, store=tampered_store, settings=_settings(), client=_gateway(), token=TOKEN
    )
    assert failed["status"] == "failed"
    assert failed["errorSummary"] == "config_snapshot_hash_mismatch"


def test_post_freezes_effective_config_snapshot(tmp_path: Path) -> None:
    config = _config(mode="in_app")
    path = tmp_path / "scan.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    loaded = load_scan_config(path)

    app = create_app()
    store = MemoryScanStore()
    app.state.scan_store = store
    app.state.scan_config = loaded
    app.state.settings.scan_warehouses = ["W01"]
    app.state.settings.notification_mode = "in_app"
    app.state.settings.alert_recipients = ["admin"]
    app.dependency_overrides[require_principal] = lambda: _principal()
    app.dependency_overrides[scan_router.get_scan_store] = lambda: store

    client = TestClient(app)
    response = client.post(
        "/agent/scan",
        json={"scanTypes": ["no_up"], "requestId": "req-config"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert response.status_code == 202
    scan_id = response.json()["data"]["scanId"]
    queued = store.runs[scan_id]
    assert queued["status"] == "queued"
    assert queued["configSnapshot"] == loaded.snapshot
    assert queued["configHash"] == loaded.config_hash
    assert queued["configVersion"] == loaded.version
    assert queued["notificationMode"] == "in_app"


async def test_scheduled_route_merges_global_and_rule_recipients() -> None:
    config = _config(mode="in_app")
    config["routing"][0]["recipients"] = ["route-user"]
    store = MemoryScanStore()
    run = await run_scan(
        scan_id="scan-route",
        scan_types=["no_up"],
        principal=Principal(
            user_id="svc",
            user_name="agent-inspector",
            authorities=("insp_read",),
            warehouse_scope=("W01",),
            token_use="agent_service",
        ),
        token=TOKEN,
        client=_gateway([_row(age_hours=9.0)]),
        store=store,
        allowed_warehouses=["W01"],
        config=config,
        notification_mode="in_app",
        actor_type="service",
        trigger="schedule",
        actor_id="agent-inspector",
    )
    assert run["status"] == "succeeded"
    assert {n["recipient"] for n in store.notifications} == {"admin", "route-user"}
    assert all(n["status"] == "sent" for n in store.notifications)
    assert list(store.alerts.values())[0]["routedTo"] == "putaway_lead"


async def test_scan_concurrency_is_bounded_by_config() -> None:
    config = json.loads(canonical_json(DEFAULT_CONFIG))
    config["scan"]["concurrency"] = 2
    config["scan"]["scanBudgetSeconds"] = 5
    active = 0
    max_active = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.03)
        active -= 1
        return httpx.Response(200, json={"code": 10000, "data": {"rows": [], "total": 0, "pages": 0}})

    transport = httpx.MockTransport(handler)
    client = GatewayClient("http://gateway.test", transport=transport)
    store = MemoryScanStore()
    run = await run_scan(
        scan_id="scan-concurrency",
        scan_types=["expiry", "no_up", "delay"],
        principal=_principal(),
        token=TOKEN,
        client=client,
        store=store,
        allowed_warehouses=["W01"],
        dry_run=True,
        config=config,
    )
    assert run["status"] == "succeeded"
    assert max_active == 2


async def test_scan_budget_marks_unfinished_source_partial() -> None:
    config = json.loads(canonical_json(DEFAULT_CONFIG))
    config["scan"]["scanBudgetSeconds"] = 0.02
    config["scan"]["sourceBudgetSeconds"] = 1

    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.1)
        return httpx.Response(200, json={"code": 10000, "data": {"rows": [], "total": 0}})

    client = GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))
    run = await run_scan(
        scan_id="scan-budget",
        scan_types=["expiry"],
        principal=_principal(),
        token=TOKEN,
        client=client,
        store=MemoryScanStore(),
        allowed_warehouses=["W01"],
        dry_run=True,
        config=config,
    )
    assert run["status"] == "succeeded"
    assert run["partial"] is True
    assert run["sourceStatus"][0]["status"] == "timeout"
    assert run["sourceStatus"][0]["errorSummary"] == "scan_budget_exceeded"
