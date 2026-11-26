"""阶段4：版本化 scan.yaml、启动校验、配置快照冻结与回放。

覆盖：
- 仓库内 scan.yaml 可加载、哈希稳定、canonical JSON 与键顺序无关；
- 启动校验拒绝重复键 / 非法阈值顺序 / 非法通知模式 / 未知路由规则 / 跨仓路由；
- 阈值、路由、通知模式任一变化都改变哈希；
- 快照往返哈希一致（回归：不得用模型 dump 归一化后的结果重算哈希）；
- 快照不含密钥；
- worker 只执行入队快照，改文件不影响在途任务；
- 缺快照 fail-closed（config_snapshot_missing）；
- 责任路由写入 routedTo、接收人来自配置、解析不到记 notificationsUnrouted；
- PG 写入/读回放一致（需 WMS_AGENT_TEST_DB_URL）。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

from app.config import ScanConfigError, Settings, ensure_single_scan_warehouse
from app.scan.config import (
    canonical_json,
    hash_config,
    load_config_snapshot,
    load_scan_config,
)
from app.scan.repository import MemoryScanStore
from app.scan.service import DEFAULT_CONFIG, config_hash, run_scan
from app.scan.worker import execute_queued_scan
from app.security import Principal
from app.tools.gateway_client import GatewayClient

TOKEN = "header.payload.signature"
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
REPO_CONFIG = Path(__file__).resolve().parents[1] / "config" / "scan.yaml"


# ---------- helpers ----------

def _yaml_document(**overrides: Any) -> dict[str, Any]:
    """一份合法配置文档（与仓库内 scan.yaml 同构），可按需覆盖。"""
    document: dict[str, Any] = {
        "version": "v0.2.0",
        "warehouses": ["W01"],
        "scan": {
            "pageSize": 100,
            "maxPages": 20,
            "requestTimeoutSeconds": 3,
            "sourceBudgetSeconds": 30,
            "scanBudgetSeconds": 120,
            "concurrency": 1,
        },
        "rules": {
            "expiry": {"expiredDays": 0, "nearDays": 7, "nearRatio": 0.3333, "watchDays": 30},
            "noUp": {"p0Hours": 8, "p1Hours": 4, "p2Hours": 2},
            "delay": {"p0Hours": 24, "p1Hours": 2, "p2Hours": 0},
            "backlog": {
                "growthRatio": 0.30,
                "absoluteDelta": 10,
                "baselineScans": 3,
                "consecutiveForP1": 3,
            },
        },
        "routing": [
            {
                "rule_id": "NOUP-OVERDUE",
                "warehouse": "W01",
                "assignee_role": "putaway_lead",
                "recipients": ["zhangsan"],
            }
        ],
        "notifications": {"mode": "dry_run", "recipients": []},
        "schedule": {"enabled": False, "cron": "*/15 7-23 * * *", "timezone": "Asia/Shanghai"},
    }
    document.update(overrides)
    return document


def _write_config(tmp_path: Path, document: dict[str, Any], name: str = "scan.yaml") -> Path:
    path = tmp_path / name
    path.write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _user(name: str = "tester", **overrides: Any) -> Principal:
    return Principal(user_id="u-1", user_name=name, authorities=("ckjl",), **overrides)


def _service(scope: tuple[str, ...] = ("W01",)) -> Principal:
    return Principal(
        user_id="svc",
        user_name="agent-inspector",
        authorities=("insp_read",),
        warehouse_scope=scope,
        token_use="agent_service",
    )


def _gateway(handler: Any) -> GatewayClient:
    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))


def _ok(data: Any) -> Any:
    return lambda request: httpx.Response(200, json={"code": 10000, "data": data})


def _no_up_row(row_id: str, age_hours: float) -> dict[str, Any]:
    created = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    return {
        "rowId": row_id,
        "noticeId": "N1",
        "goods_id": "G1",
        "tin_id": "T1",
        "bin_id": "B1",
        "cus_code": "C1",
        "create_date": created.isoformat(),
    }


def _queued(snapshot: str, config_hash_value: str, version: str, **overrides: Any) -> dict[str, Any]:
    run: dict[str, Any] = {
        "scanId": "scan-1",
        "trigger": "manual",
        "actorType": "user",
        "actorId": "tester",
        "status": "queued",
        "configHash": config_hash_value,
        "configSnapshot": snapshot,
        "configVersion": version,
        "ruleVersion": "no_up=v0.2.0",
        "scanTypes": ["no_up"],
        "requestId": None,
        "scheduleSlot": None,
        "scanKey": "scan-1",
        "queuedAt": datetime.now(timezone.utc).isoformat(),
        "startedAt": None,
        "finishedAt": None,
        "attempt": 0,
        "counts": {},
        "errorSummary": None,
        "warehouse": "W01",
        "dryRun": False,
        "notificationMode": "dry_run",
        "payloadHash": "sha256:payload",
        "traceId": "trace-abc",
    }
    run.update(overrides)
    return run


def _settings() -> Settings:
    return Settings(_env_file=None, **{"WMS_AGENT_SCAN_LEASE_SECONDS": 60})


# ---------- 加载与哈希 ----------

def test_repo_scan_yaml_loads_and_hash_is_stable() -> None:
    first = load_scan_config(REPO_CONFIG)
    second = load_scan_config(REPO_CONFIG)

    # v0.2.1：新增 OUTBOUND-EXCEPTION / TEMP-EXCURSION 两类规则，配置版本同步升级。
    assert first.version == "v0.2.1"
    assert first.document.warehouses == ["W01"]
    assert first.config_hash == second.config_hash
    assert first.snapshot == second.snapshot
    # 快照必须是合法 JSON，且哈希对快照内容自洽（回放侧才算得出同一个值）
    assert first.config_hash == hash_config(json.loads(first.snapshot))
    assert first.document.notifications.mode in ("dry_run", "in_app", "full")
    assert first.document.schedule.enabled is False  # 阶段5 之前调度默认关闭
    assert first.document.routing, "仓库内配置应带责任路由"


def test_canonical_json_ignores_key_order() -> None:
    left = {"b": 1, "a": {"y": 2, "x": 3}}
    right = {"a": {"x": 3, "y": 2}, "b": 1}
    assert canonical_json(left) == canonical_json(right)
    assert hash_config(left) == hash_config(right)
    assert canonical_json(left).startswith('{"a":')


def test_same_document_written_differently_has_same_hash(tmp_path: Path) -> None:
    document = _yaml_document()
    reordered = {key: document[key] for key in reversed(list(document))}
    first = load_scan_config(_write_config(tmp_path, document, "a.yaml"))
    second = load_scan_config(_write_config(tmp_path, reordered, "b.yaml"))
    assert first.config_hash == second.config_hash


# ---------- 启动校验：拒绝非法配置 ----------

def test_duplicate_yaml_key_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "dup.yaml"
    path.write_text(
        "version: v0.2.0\nversion: v0.2.1\nwarehouses: [W01]\n", encoding="utf-8"
    )
    with pytest.raises(ScanConfigError) as excinfo:
        load_scan_config(path)
    assert "YAML 重复键" in str(excinfo.value)


def test_invalid_severity_order_is_rejected(tmp_path: Path) -> None:
    document = _yaml_document()
    document["rules"]["noUp"] = {"p0Hours": 4, "p1Hours": 8, "p2Hours": 2}
    with pytest.raises(ScanConfigError) as excinfo:
        load_scan_config(_write_config(tmp_path, document))
    assert "p0Hours > p1Hours > p2Hours" in str(excinfo.value)


def test_invalid_notification_mode_is_rejected(tmp_path: Path) -> None:
    document = _yaml_document()
    document["notifications"] = {"mode": "sms", "recipients": []}
    with pytest.raises(ScanConfigError) as excinfo:
        load_scan_config(_write_config(tmp_path, document))
    assert "巡检配置非法" in str(excinfo.value)


def test_unknown_routing_rule_is_rejected(tmp_path: Path) -> None:
    document = _yaml_document()
    document["routing"] = [
        {"rule_id": "NOPE-1", "warehouse": "W01", "assignee_role": "x", "recipients": []}
    ]
    with pytest.raises(ScanConfigError) as excinfo:
        load_scan_config(_write_config(tmp_path, document))
    assert "路由规则未匹配任何已知规则" in str(excinfo.value)


def test_routing_warehouse_must_be_in_scope(tmp_path: Path) -> None:
    document = _yaml_document()
    document["routing"] = [
        {"rule_id": "NOUP-OVERDUE", "warehouse": "W02", "assignee_role": "x", "recipients": []}
    ]
    with pytest.raises(ScanConfigError) as excinfo:
        load_scan_config(_write_config(tmp_path, document))
    assert "路由仓库不在 warehouses 中" in str(excinfo.value)


def test_unknown_override_key_is_rejected() -> None:
    with pytest.raises(ScanConfigError) as excinfo:
        load_scan_config(REPO_CONFIG, overrides={"rules": {}})
    assert "未知巡检配置覆盖项" in str(excinfo.value)


def test_multiple_warehouses_still_rejected_in_first_release(tmp_path: Path) -> None:
    document = _yaml_document(warehouses=["W01", "W02"])
    loaded = load_scan_config(_write_config(tmp_path, document))
    assert loaded.document.warehouses == ["W01", "W02"]
    with pytest.raises(ScanConfigError):
        ensure_single_scan_warehouse(list(loaded.document.warehouses))


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ScanConfigError) as excinfo:
        load_scan_config(tmp_path / "absent.yaml")
    assert "不可读" in str(excinfo.value)


# ---------- 哈希对变化敏感 ----------

def test_threshold_routing_and_mode_changes_alter_hash(tmp_path: Path) -> None:
    base = load_scan_config(_write_config(tmp_path, _yaml_document(), "base.yaml")).config_hash

    changed_rules = _yaml_document()
    changed_rules["rules"]["noUp"] = {"p0Hours": 9, "p1Hours": 5, "p2Hours": 3}
    rules_hash = load_scan_config(_write_config(tmp_path, changed_rules, "rules.yaml")).config_hash

    changed_routing = _yaml_document()
    changed_routing["routing"] = [
        {"rule_id": "NOUP-OVERDUE", "warehouse": "W01", "assignee_role": "other", "recipients": []}
    ]
    routing_hash = load_scan_config(_write_config(tmp_path, changed_routing, "routing.yaml")).config_hash

    changed_mode = _yaml_document()
    changed_mode["notifications"] = {"mode": "in_app", "recipients": []}
    mode_hash = load_scan_config(_write_config(tmp_path, changed_mode, "mode.yaml")).config_hash

    assert len({base, rules_hash, routing_hash, mode_hash}) == 4


def test_env_override_is_reflected_in_effective_snapshot_and_hash() -> None:
    base = load_scan_config(REPO_CONFIG)
    overridden = load_scan_config(REPO_CONFIG, overrides={"notifications": {"mode": "in_app"}})

    assert overridden.document.notifications.mode == "in_app"
    assert overridden.config_hash != base.config_hash
    assert json.loads(overridden.snapshot)["notifications"]["mode"] == "in_app"


# ---------- 快照回放 ----------

def test_snapshot_roundtrip_keeps_hash(tmp_path: Path) -> None:
    """回归：入队侧对原始 dict 算哈希，回放侧也必须算出同一个值。

    早期实现用模型 dump 再算哈希，float 字段把 24 归一化成 24.0，
    导致合法快照被判成篡改（config_snapshot_hash_mismatch）。
    """
    loaded = load_scan_config(_write_config(tmp_path, _yaml_document()))
    replayed = load_config_snapshot(
        loaded.snapshot,
        expected_hash=loaded.config_hash,
        expected_version=loaded.version,
    )
    assert replayed.config_hash == loaded.config_hash
    assert replayed.version == loaded.version
    assert replayed.config == json.loads(loaded.snapshot)
    # 整数阈值不得被浮点化，否则下游规则参数会漂移
    assert replayed.config["rules"]["delay"]["p0Hours"] == 24


def test_snapshot_tampering_is_detected(tmp_path: Path) -> None:
    loaded = load_scan_config(_write_config(tmp_path, _yaml_document()))
    # 篡改必须仍然是合法配置，否则会先被结构校验拦下，测不到哈希比对
    tampered = json.loads(loaded.snapshot)
    tampered["rules"]["noUp"]["p0Hours"] = 12
    with pytest.raises(ScanConfigError) as excinfo:
        load_config_snapshot(
            canonical_json(tampered),
            expected_hash=loaded.config_hash,
            expected_version=loaded.version,
        )
    assert str(excinfo.value) == "config_snapshot_hash_mismatch"


def test_snapshot_version_mismatch_is_detected(tmp_path: Path) -> None:
    loaded = load_scan_config(_write_config(tmp_path, _yaml_document()))
    with pytest.raises(ScanConfigError) as excinfo:
        load_config_snapshot(
            loaded.snapshot, expected_hash=loaded.config_hash, expected_version="v9.9.9"
        )
    assert str(excinfo.value) == "config_snapshot_version_mismatch"


def test_invalid_snapshot_json_is_rejected() -> None:
    with pytest.raises(ScanConfigError) as excinfo:
        load_config_snapshot("{not json")
    assert "不是合法 JSON" in str(excinfo.value)


def test_snapshot_contains_no_secrets() -> None:
    loaded = load_scan_config(REPO_CONFIG)
    lowered = loaded.snapshot.lower()
    for needle in ("api_key", "apikey", "password", "secret", "token", "db_url", "jwt"):
        assert needle not in lowered, f"配置快照不得包含密钥类字段: {needle}"


# ---------- worker 只执行入队快照 ----------

async def test_worker_uses_queue_snapshot_not_current_yaml(tmp_path: Path) -> None:
    """入队配置 A → 文件改成 B → worker 仍按 A 的阈值执行。"""
    config_a = load_scan_config(
        _write_config(tmp_path, _yaml_document(), "a.yaml")
    )  # noUp: 8/4/2

    document_b = _yaml_document()
    document_b["rules"]["noUp"] = {"p0Hours": 2, "p1Hours": 1, "p2Hours": 0.5}
    config_b = load_scan_config(_write_config(tmp_path, document_b, "b.yaml"))  # noUp: 2/1/0.5
    assert config_b.config_hash != config_a.config_hash

    store = MemoryScanStore()
    await store.insert_run(
        _queued(config_a.snapshot, config_a.config_hash, config_a.version)
    )
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None

    gateway = _gateway(_ok({
        "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
        "rows": [_no_up_row("R1", age_hours=3)],
    }))
    run = await execute_queued_scan(
        claimed, store=store, settings=_settings(), client=gateway, token=TOKEN
    )

    assert run["status"] == "succeeded"
    assert run["configHash"] == config_a.config_hash  # 执行的是入队快照的哈希
    assert run["configVersion"] == "v0.2.0"
    # A 下 3h 命中 P2（>2h）；若误用 B（p0=2h）会变成 P0
    alerts = list(store.alerts.values())
    assert [alert["severity"] for alert in alerts] == ["P2"]
    assert alerts[0]["ruleParams"]["p0Hours"] == 8


async def test_worker_fails_closed_without_snapshot() -> None:
    store = MemoryScanStore()
    queued = _queued("{}", "sha256:whatever", "v0.2.0")
    queued["configSnapshot"] = None
    await store.insert_run(queued)
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None

    gateway = _gateway(_ok({"rows": [], "total": 0}))
    run = await execute_queued_scan(
        claimed, store=store, settings=_settings(), client=gateway, token=TOKEN
    )

    assert run["status"] == "failed"
    assert run["errorSummary"] == "config_snapshot_missing"
    assert store.alerts == {}


async def test_worker_fails_closed_on_corrupted_snapshot(tmp_path: Path) -> None:
    """快照本身合法但哈希对不上（被篡改/版本错配）时必须失败退出。"""
    loaded = load_scan_config(_write_config(tmp_path, _yaml_document()))
    store = MemoryScanStore()
    await store.insert_run(
        _queued(loaded.snapshot, "sha256:deadbeef", loaded.version)
    )
    claimed = await store.claim_next_queued("worker-a")
    assert claimed is not None

    gateway = _gateway(_ok({"rows": [], "total": 0}))
    run = await execute_queued_scan(
        claimed, store=store, settings=_settings(), client=gateway, token=TOKEN
    )

    assert run["status"] == "failed"
    assert run["errorSummary"] == "config_snapshot_hash_mismatch"


# ---------- run_scan 记录快照 / 责任路由 ----------

async def test_run_scan_freezes_snapshot_and_version(tmp_path: Path) -> None:
    loaded = load_scan_config(_write_config(tmp_path, _yaml_document()))
    store = MemoryScanStore()
    gateway = _gateway(_ok({"pageIndex": 1, "pageSize": 100, "total": 0, "pages": 0, "rows": []}))

    run = await run_scan(
        scan_id="scan-cfg",
        scan_types=["no_up"],
        principal=_user(),
        token=TOKEN,
        client=gateway,
        store=store,
        allowed_warehouses=list(loaded.document.warehouses),
        config=loaded.config,
        config_hash_value=loaded.config_hash,
    )

    assert run["status"] == "succeeded"
    assert run["configHash"] == loaded.config_hash
    assert run["configVersion"] == "v0.2.0"
    assert json.loads(run["configSnapshot"]) == loaded.config


async def test_inline_config_still_records_snapshot_and_version() -> None:
    """不传 config 时用 DEFAULT_CONFIG，也必须落快照与版本（历史路径不得留空）。"""
    store = MemoryScanStore()
    gateway = _gateway(_ok({"pageIndex": 1, "pageSize": 100, "total": 0, "pages": 0, "rows": []}))

    run = await run_scan(
        scan_id="scan-inline",
        scan_types=["no_up"],
        principal=_user(),
        token=TOKEN,
        client=gateway,
        store=store,
        allowed_warehouses=["W01"],
    )

    assert run["configHash"] == config_hash(DEFAULT_CONFIG)
    assert run["configVersion"] == DEFAULT_CONFIG["version"]
    assert json.loads(run["configSnapshot"]) == DEFAULT_CONFIG


async def test_routed_to_holds_role_while_notification_goes_to_actor(tmp_path: Path) -> None:
    loaded = load_scan_config(_write_config(tmp_path, _yaml_document()))
    store = MemoryScanStore()
    gateway = _gateway(_ok({
        "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
        "rows": [_no_up_row("R1", age_hours=9)],
    }))

    await run_scan(
        scan_id="scan-route",
        scan_types=["no_up"],
        principal=_user(),
        token=TOKEN,
        client=gateway,
        store=store,
        allowed_warehouses=list(loaded.document.warehouses),
        config=loaded.config,
        config_hash_value=loaded.config_hash,
    )

    assert len(store.alerts) == 1
    alert = next(iter(store.alerts.values()))
    assert alert["routedTo"] == "putaway_lead"  # 责任岗位
    assert alert["assignee"] is None  # 认领人不能被路由抢占
    # 手动扫描默认通知发起人，而不是路由接收人
    assert [n["recipient"] for n in store.notifications] == ["tester"]


async def test_service_scan_merges_configured_and_routed_recipients(tmp_path: Path) -> None:
    document = _yaml_document()
    document["notifications"] = {"mode": "dry_run", "recipients": ["lisi"]}
    loaded = load_scan_config(_write_config(tmp_path, document))
    store = MemoryScanStore()
    gateway = _gateway(_ok({
        "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
        "rows": [_no_up_row("R1", age_hours=9)],
    }))

    await run_scan(
        scan_id="scan-svc",
        scan_types=["no_up"],
        principal=_service(),
        token=TOKEN,
        client=gateway,
        store=store,
        allowed_warehouses=list(loaded.document.warehouses),
        config=loaded.config,
        config_hash_value=loaded.config_hash,
    )

    assert sorted(n["recipient"] for n in store.notifications) == ["lisi", "zhangsan"]


async def test_unrouted_notification_is_counted_not_guessed(tmp_path: Path) -> None:
    document = _yaml_document()
    document["routing"] = []
    document["notifications"] = {"mode": "dry_run", "recipients": []}
    loaded = load_scan_config(_write_config(tmp_path, document))
    store = MemoryScanStore()
    gateway = _gateway(_ok({
        "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
        "rows": [_no_up_row("R1", age_hours=9)],
    }))

    run = await run_scan(
        scan_id="scan-unrouted",
        scan_types=["no_up"],
        principal=_service(),
        token=TOKEN,
        client=gateway,
        store=store,
        allowed_warehouses=list(loaded.document.warehouses),
        config=loaded.config,
        config_hash_value=loaded.config_hash,
    )

    assert run["counts"]["notificationsUnrouted"] == 1
    assert store.notifications == []  # 不写占位账号


# ---------- PG 写读回放一致 ----------

def _test_db_url() -> str:
    return os.environ.get("WMS_AGENT_TEST_DB_URL", "")


async def test_postgres_roundtrip_keeps_config_snapshot() -> None:
    db_url = _test_db_url()
    if not db_url or "test" not in db_url.rsplit("/", 1)[-1]:
        pytest.skip("需要 WMS_AGENT_TEST_DB_URL 指向测试库")

    from app.scan.repository import PostgresScanStore

    loaded = load_scan_config(REPO_CONFIG)
    store = PostgresScanStore(db_url)
    await store.ensure_schema()
    try:
        await store.insert_run(_queued(loaded.snapshot, loaded.config_hash, loaded.version, scanId="scan-pg-cfg"))
        restored = await store.get_run("scan-pg-cfg")
        assert restored is not None
        assert restored["configSnapshot"] == loaded.snapshot
        assert restored["configVersion"] == loaded.version
        assert restored["configHash"] == loaded.config_hash
        # 从库里取回的快照必须能通过哈希校验并还原同一份生效配置
        replayed = load_config_snapshot(
            restored["configSnapshot"],
            expected_hash=restored["configHash"],
            expected_version=restored["configVersion"],
        )
        assert replayed.config == loaded.config
    finally:
        import psycopg

        from app.storage.postgres import normalize_dsn

        with psycopg.connect(normalize_dsn(db_url)) as conn:
            conn.execute("DELETE FROM wms_agent.agent_scan_runs WHERE scan_id = %s", ("scan-pg-cfg",))
            conn.commit()
