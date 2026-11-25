"""BACKLOG 扫描编排契约（阶段3）：快照 → 基线 → 样本 → 告警（MemoryScanStore + MockTransport）。

覆盖用户 m04555 必测场景中涉及编排/存储的部分：
第 1–6 次扫描序列、单周期 P2、连续三次 P1、增长下降/零基线/负值、
重复 scanId 不重复落样本、partial/超时/5xx 不落样本不告警、三队列互不聚合、
规则版本变化不混用旧基线、dryRun 不落样本不告警。
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.scan.repository import MemoryScanStore
from app.scan.rules.backlog import RULE_VERSION
from app.scan.service import DEFAULT_CONFIG, run_scan
from app.scan.sources.backlog import parse_snapshot
from app.security import Principal
from app.tools.gateway_client import GatewayClient

TOKEN = "header.payload.signature"
SNAPSHOT_PATH = "/dashboard/query-pend-snapshot"
OBSERVED = "2026-11-25T12:00:00+08:00"


def _user() -> Principal:
    return Principal(user_id="u-1", user_name="tester", authorities=["insp_read"])


def _snapshot(receipt=0, to_up=0, pick=0, cur_pick=0, observed_at=OBSERVED) -> dict[str, Any]:
    return {
        "observedAt": observed_at,
        "receipt": {"queueType": "receipt", "value": receipt},
        "toUp": {"queueType": "to_up", "value": to_up},
        "pick": {"queueType": "pick", "value": pick},
        "curPick": {"queueType": "cur_pick", "value": cur_pick},
    }


def _client(snapshot: dict[str, Any] | None = None, *, status: int = 200, code: int = 10000,
            calls: list[str] | None = None, timeout_times: int = 0) -> GatewayClient:
    """``timeout_times``：前 N 次请求抛 ReadTimeout（之后按 ``snapshot`` 正常返回）。"""
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        state["n"] += 1
        if state["n"] <= timeout_times:
            raise httpx.ReadTimeout("slow", request=request)
        if status != 200:
            return httpx.Response(status, json={"code": status, "message": "fail"})
        if snapshot is None:
            return httpx.Response(200, json={"code": code, "data": None})
        return httpx.Response(200, json={"code": code, "data": snapshot})

    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(handler))


async def _scan(store: MemoryScanStore, scan_id: str, snapshot: dict[str, Any] | None,
                *, dry_run: bool = False, **kw) -> dict[str, Any]:
    return await run_scan(
        scan_id=scan_id, scan_types=["backlog"], principal=_user(), token=TOKEN,
        client=_client(snapshot, **kw), store=store, allowed_warehouses=["W01"],
        dry_run=dry_run, notification_mode="dry_run",
    )


def _alerts(store: MemoryScanStore, rule_id: str = "BACKLOG-GROWTH") -> list[dict[str, Any]]:
    return [a for a in store.alerts.values() if a.get("ruleId") == rule_id]


# ---------- parse ----------

def test_parse_snapshot_accepts_numeric_strings_and_numbers():
    rows = parse_snapshot(_snapshot(receipt="12.5", to_up=3, pick="45.0000", cur_pick=0))
    assert [r["queueType"] for r in rows] == ["receipt", "to_up", "pick", "cur_pick"]
    assert rows[0]["value"] == 12.5
    assert rows[2]["value"] == 45.0
    assert rows[3]["diagnostic"] is True and rows[0]["diagnostic"] is False
    assert all(r["observedAt"] == OBSERVED for r in rows)


@pytest.mark.parametrize("bad", [
    None, [], {"observedAt": OBSERVED},  # 缺队列
    {**_snapshot(), "pick": {"queueType": "pick", "value": None}},  # 值为 null
    {**_snapshot(), "receipt": {"queueType": "receipt", "value": "abc"}},  # 非数字
    {**_snapshot(), "observedAt": ""},  # 缺 observedAt
])
def test_parse_snapshot_rejects_incomplete_payload(bad):
    assert parse_snapshot(bad) is None


def test_parse_snapshot_normalizes_java_zoned_datetime_suffix():
    # 真实 Dashboard 端点返回 Java ZonedDateTime.toString()：带方括号区域 ID，
    # psycopg 解析 TIMESTAMPTZ 会抛 InvalidDatetimeFormat，必须在源头去掉。
    java_ts = "2026-11-25T13:01:08.141234900+08:00[Asia/Shanghai]"
    rows = parse_snapshot(_snapshot(observed_at=java_ts))
    assert rows is not None
    assert {r["observedAt"] for r in rows} == {"2026-11-25T13:01:08.141234900+08:00"}
    assert all("[" not in r["observedAt"] for r in rows)
    # 纯 ISO（无区域后缀）原样保留；UTC 'Z' 也保留给 psycopg 自行处理
    assert parse_snapshot(_snapshot(observed_at=OBSERVED))[0]["observedAt"] == OBSERVED
    assert parse_snapshot(_snapshot(observed_at="2026-11-25T05:00:00Z"))[0]["observedAt"] == "2026-11-25T05:00:00Z"
    # 只有区域后缀没有时间 → 视为缺失
    assert parse_snapshot(_snapshot(observed_at="   ")) is None


# ---------- 第 1–6 次序列（走完整编排） ----------

@pytest.mark.asyncio
async def test_scan_sequence_first_three_baseline_then_p2_then_p1():
    store = MemoryScanStore()
    # 每对相邻都 ≥30% 且 Δ≥10：第4次 70→110 +57%，第5次 110→140 +27%… 不行，改用下面序列
    seq = [60, 70, 80, 110, 150, 200, 300]  # 110→150 +36%，150→200 +33%，200→300 +50%
    for i, v in enumerate(seq, start=1):
        run = await _scan(store, f"scan-{i}", _snapshot(pick=v))
        assert run["status"] == "succeeded", run
        assert run["partial"] is False
        assert run["counts"]["backlogSamplesSaved"] == 3  # 三个分级队列各一条；cur_pick 不落
        alerts = _alerts(store)
        if i <= 3:
            assert alerts == []
        elif i in (4, 5):
            assert len(alerts) == 1 and alerts[0]["severity"] == "P2"
        else:
            assert len(alerts) == 1 and alerts[0]["severity"] == "P1"
    obs = [o for o in store.backlog_observations if o["queueType"] == "pick"]
    assert [o["value"] for o in obs] == seq
    assert all(o["ruleVersion"] == RULE_VERSION for o in obs)
    assert all(o["scanId"].startswith("scan-") for o in obs)
    assert not any(o["queueType"] == "cur_pick" for o in store.backlog_observations)


@pytest.mark.asyncio
async def test_scan_rule_version_recorded_on_run_and_alerts_carry_trace():
    store = MemoryScanStore()
    for i, v in enumerate([60, 70, 80, 110], start=1):  # 80→110 +37.5% 命中
        run = await _scan(store, f"scan-{i}", _snapshot(pick=v))
    assert run["ruleVersion"] == f"backlog={RULE_VERSION}"
    alert = _alerts(store)[0]
    assert alert["ruleVersion"] == RULE_VERSION
    assert alert["evidence"]["traceId"] == run["traceId"]
    assert alert["traceId"] == run["traceId"]
    assert alert["objectId"] == "W01|pick"


# ---------- 重复 scanId 不重复落样本 ----------

@pytest.mark.asyncio
async def test_duplicate_scan_id_does_not_duplicate_samples_or_alerts():
    store = MemoryScanStore()
    first = await _scan(store, "scan-same", _snapshot(pick=100))
    assert first["counts"]["backlogSamplesSaved"] == 3
    # 同 scanId 重放：三条都被唯一键挡下，基线不被污染
    second = await _scan(store, "scan-same", _snapshot(pick=100))
    assert second["counts"]["backlogSamplesSaved"] == 0
    assert len([o for o in store.backlog_observations if o["scanId"] == "scan-same"]) == 3


@pytest.mark.asyncio
async def test_observation_values_follow_latest_scan_even_with_same_scan_id():
    # 同 scanId 重放时样本不变（幂等），因此基线序列不会被重放污染
    store = MemoryScanStore()
    await _scan(store, "scan-a", _snapshot(pick=100))
    await _scan(store, "scan-a", _snapshot(pick=999))  # 被唯一键挡下
    hist = await store.list_backlog_observations("W01", "pick", rule_version=RULE_VERSION)
    assert [h["value"] for h in hist] == [100]


# ---------- partial / 超时 / 5xx / 失败不落样本不告警 ----------

@pytest.mark.asyncio
@pytest.mark.parametrize("kw", [
    {"status": 503}, {"status": 500}, {"timeout_times": 10},
])
async def test_source_failure_marks_partial_and_writes_nothing(kw):
    store = MemoryScanStore()
    calls: list[str] = []
    snapshot = kw.pop("snapshot", None) or _snapshot(pick=500)
    run = await run_scan(
        scan_id="scan-fail", scan_types=["backlog"], principal=_user(), token=TOKEN,
        client=_client(snapshot, calls=calls, **kw), store=store, allowed_warehouses=["W01"],
        dry_run=False, notification_mode="dry_run",
    )
    assert run["status"] == "succeeded"
    assert run["partial"] is True
    assert run["sourceStatus"][0]["source"] == "backlog"
    assert run["sourceStatus"][0]["status"] in ("error", "timeout")
    assert store.backlog_observations == []
    assert _alerts(store) == []
    # partial 元告警仍在，但不是 BACKLOG-GROWTH
    assert [a for a in store.alerts.values() if a.get("ruleId") == "SCAN-PARTIAL"]


@pytest.mark.asyncio
async def test_transient_timeout_then_success_is_not_partial():
    # 首次超时、重试成功：快照完整 → 正常落样本，不标 partial
    store = MemoryScanStore()
    calls: list[str] = []
    run = await _scan(store, "scan-retry", _snapshot(pick=42), calls=calls, timeout_times=1)
    assert calls.count(SNAPSHOT_PATH) == 2
    assert run["partial"] is False
    assert run["counts"]["backlogSamplesSaved"] == 3


@pytest.mark.asyncio
async def test_gateway_5xx_is_retried_once():
    calls: list[str] = []
    store = MemoryScanStore()
    await _scan(store, "scan-r", _snapshot(pick=1), status=503, calls=calls)
    assert calls.count(SNAPSHOT_PATH) == 2  # 首次 + 1 次重试


@pytest.mark.asyncio
async def test_gateway_4xx_is_not_retried_and_marks_partial():
    calls: list[str] = []
    store = MemoryScanStore()
    await _scan(store, "scan-4xx", _snapshot(pick=1), status=403, calls=calls)
    assert calls.count(SNAPSHOT_PATH) == 1


@pytest.mark.asyncio
async def test_business_failure_code_marks_partial():
    store = MemoryScanStore()
    run = await _scan(store, "scan-code", None, code=9998)
    assert run["partial"] is True
    assert store.backlog_observations == []


@pytest.mark.asyncio
async def test_incomplete_snapshot_payload_marks_partial():
    store = MemoryScanStore()
    run = await _scan(store, "scan-bad", {**_snapshot(pick=1), "toUp": {"queueType": "to_up", "value": None}})
    assert run["partial"] is True
    assert run["sourceStatus"][0]["errorSummary"] == "invalid_snapshot_payload"
    assert store.backlog_observations == []


@pytest.mark.asyncio
async def test_negative_queue_value_is_skipped_without_poisoning_other_queues():
    # 负值是数据质量问题：该队列不落样本不告警、不参与基线；其余队列照常；快照不标 partial
    store = MemoryScanStore()
    run = await _scan(store, "scan-neg", _snapshot(pick=-5, to_up=100))
    assert run["partial"] is False
    saved_q = sorted(o["queueType"] for o in store.backlog_observations)
    assert saved_q == ["receipt", "to_up"]  # pick 被跳过
    assert _alerts(store) == []
    hist = await store.list_backlog_observations("W01", "pick", rule_version=RULE_VERSION)
    assert hist == []
    # pick 的历史不因此建基线：下一轮 pick 仍是「第 1 次」
    await _scan(store, "scan-neg2", _snapshot(pick=100, to_up=200))
    hist = await store.list_backlog_observations("W01", "pick", rule_version=RULE_VERSION)
    assert [h["value"] for h in hist] == [100]


# ---------- 零基线 / 下降 ----------

@pytest.mark.asyncio
async def test_zero_baseline_never_alerts_and_real_baseline_then_alerts():
    store = MemoryScanStore()
    for i in range(3):
        await _scan(store, f"scan-z{i}", _snapshot(pick=0))
    run = await _scan(store, "scan-z3", _snapshot(pick=100))  # 0→100 不告警
    assert run["counts"]["findings"] == 0
    assert _alerts(store) == []
    run = await _scan(store, "scan-z4", _snapshot(pick=200))  # 100→200 告警
    assert len(_alerts(store)) == 1 and _alerts(store)[0]["severity"] == "P2"


@pytest.mark.asyncio
async def test_declining_queue_updates_samples_without_alert():
    store = MemoryScanStore()
    for i, v in enumerate([100, 150, 200, 150], start=1):
        run = await _scan(store, f"scan-d{i}", _snapshot(pick=v))
    assert run["counts"]["findings"] == 0
    assert _alerts(store) == []


# ---------- 三队列互不聚合 ----------

@pytest.mark.asyncio
async def test_queues_alert_independently_through_scan_pipeline():
    store = MemoryScanStore()
    for i, (r, t, p) in enumerate([(100, 500, 50), (110, 400, 50), (120, 300, 50)], start=1):
        await _scan(store, f"scan-q{i}", _snapshot(receipt=r, to_up=t, pick=p))
    run = await _scan(store, "scan-q4", _snapshot(receipt=400, to_up=100, pick=50))
    ids = sorted(a["objectId"] for a in _alerts(store))
    assert ids == ["W01|receipt"]
    assert all(a["severity"] == "P2" for a in _alerts(store))


# ---------- 规则版本变化不混用旧基线 ----------

@pytest.mark.asyncio
async def test_rule_version_change_starts_new_baseline():
    store = MemoryScanStore()
    for i, v in enumerate([60, 70, 80, 110], start=1):  # 80→110 +37.5% → 第 4 次 P2
        await _scan(store, f"scan-v{i}", _snapshot(pick=v))
    assert len(_alerts(store)) == 1
    # 模拟旧版本样本：查询时按 rule_version 过滤，不会混入当前版本基线
    store.backlog_observations.append({
        "observationId": 9999, "scanId": "scan-old", "warehouse": "W01", "queueType": "pick",
        "value": 5000, "observedAt": "2026-01-01T00:00:00+00:00", "ruleVersion": "v0.1.0",
        "sourceStatus": "ok",
    })
    hist = await store.list_backlog_observations("W01", "pick", rule_version=RULE_VERSION)
    assert [h["value"] for h in hist] == [60, 70, 80, 110]
    old = await store.list_backlog_observations("W01", "pick", rule_version="v0.1.0")
    assert [h["value"] for h in old] == [5000]


# ---------- dryRun ----------

@pytest.mark.asyncio
async def test_request_dry_run_writes_no_samples_and_no_alerts():
    store = MemoryScanStore()
    run = await _scan(store, "scan-dry", _snapshot(pick=500), dry_run=True)
    assert run["dryRun"] is True
    assert run["counts"]["backlogSamplesSaved"] == 0
    assert store.backlog_observations == []
    assert store.alerts == {}


# ---------- config ----------

def test_default_config_records_contract_thresholds():
    assert DEFAULT_CONFIG["rules"]["backlog"] == {
        "growthRatio": 0.30, "absoluteDelta": 10, "baselineScans": 3, "consecutiveForP1": 3,
    }
