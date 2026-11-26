"""F-016 v0.2.1：出货异常（OUTBOUND-EXCEPTION）与温度巡检（TEMP-EXCURSION）
规则、数据源、独立开关与编排集成测试。

不依赖 PG/Nacos/真实网络；规则分级确定性，mock gateway + 固定输入回放。
覆盖：24h 老化分级（无闭环字段、文案不含“未闭环”）、温度地点词表/连续超限/
单点超限/无录入/未匹配地点/倒填数据质量、两类独立开关、partial 不自动关闭。
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from app.scan.config import (
    SUPPORTED_SCAN_TYPE_LIST,
    OutboundRules,
    TemperatureRules,
    load_scan_config,
)
from app.scan.repository import MemoryScanStore
from app.scan.rules.base import RuleContext
from app.scan.rules.outbound import (
    P1_DESCRIPTION,
    _p0_description,
    evaluate_outbound,
    evaluate_outbound_detailed,
)
from app.scan.rules.temperature import evaluate_temperature, evaluate_temperature_detailed
from app.scan.service import DEFAULT_CONFIG, run_scan
from app.scan.sources.outbound import fetch_outbound
from app.scan.sources.temperature import fetch_temperature
from app.security import Principal
from app.tools.gateway_client import GatewayClient

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
TOKEN = "header.payload.signature"
OUTBOUND_PATH = "/daycheck/yi-chang/get-yichang-down-page"
TEMPERATURE_PATH = "/daycheck/temperature/query"


def _ctx() -> RuleContext:
    return RuleContext(warehouse="W01", now=NOW)


def _hours_ago(hours: float) -> str:
    return (NOW - timedelta(hours=hours)).isoformat()


def _user() -> Principal:
    return Principal(user_id="u-1", user_name="tester", authorities=["insp_read"])


# ---------- outbound rule ----------


def _outbound_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "rowId": "W1",
        "bin_id_to": "K01",
        "goods_id": "G1",
        "cus_code": "C1",
        "shp_ming_cheng": "小蓝管",
        "zhong_wen_qch": "客户甲",
        "goods_qua": "10",
        "goods_quaok": "9",
        "create_date": _hours_ago(2),
    }
    row.update(overrides)
    return row


def test_outbound_p0_over_24h() -> None:
    out = evaluate_outbound([_outbound_row(create_date=_hours_ago(25))], _ctx())
    assert len(out) == 1
    assert out[0].rule_id == "OUTBOUND-EXCEPTION" and out[0].severity == "P0"
    assert out[0].object_type == "outbound_exception"
    assert out[0].object_id == "K01|G1|C1"
    assert out[0].suggested_actions == ("CHECK_BATCH", "NOTIFY_QC")


def test_outbound_p1_same_day_and_boundary() -> None:
    # 恰好 24h 不触发 P0（严格 >24h）；当日新增 → P1；不设 P2。
    assert evaluate_outbound([_outbound_row(create_date=_hours_ago(24))], _ctx())[0].severity == "P1"
    assert evaluate_outbound([_outbound_row(create_date=_hours_ago(2))], _ctx())[0].severity == "P1"


def test_outbound_wording_no_unclosed_claim() -> None:
    p0 = evaluate_outbound([_outbound_row(create_date=_hours_ago(25))], _ctx())[0]
    blob = str(p0.evidence) + _p0_description(24)
    assert "下架后超过 24 小时仍未处理" in blob
    assert "未闭环" not in blob
    assert "异常持续 24 小时" not in blob
    assert p0.evidence["description"] == _p0_description(24)
    # 审计修复：文案随 p0_hours 配置生成，不写死 24；P1 不再误写“超过24小时”
    assert _p0_description(12) == "下架后超过 12 小时仍未处理"
    assert _p0_description(24.5) == "下架后超过 24.5 小时仍未处理"
    p1 = evaluate_outbound([_outbound_row(create_date=_hours_ago(2))], _ctx())[0]
    assert p1.evidence["description"] == P1_DESCRIPTION
    assert "未闭环" not in str(p1.evidence)
    assert "24" not in p1.evidence["description"]


def test_outbound_same_object_keeps_highest_severity() -> None:
    """审计④：同对象 25h P0 与 2h P1 同行聚合后只保留 P0，不被 P1 覆盖。"""
    rows = [
        _outbound_row(rowId="W-p1", create_date=_hours_ago(2)),
        _outbound_row(rowId="W-p0", create_date=_hours_ago(25)),
    ]
    findings = evaluate_outbound(rows, _ctx())
    assert len(findings) == 1
    assert findings[0].severity == "P0"
    assert findings[0].object_id == "K01|G1|C1"


def test_outbound_skips_null_or_equal_quantity() -> None:
    """审计①（数据质量）：NULL / 无法解析 / 实际相等的数量不静默判异常。"""
    rows = [
        _outbound_row(rowId="W-null", goods_qua=None),
        _outbound_row(rowId="W-oknull", goods_quaok=None),
        _outbound_row(rowId="W-bad", goods_qua="abc"),
        _outbound_row(rowId="W-eq", goods_qua="10", goods_quaok="10"),
    ]
    detailed = evaluate_outbound_detailed(rows, _ctx())
    assert detailed.findings == []
    # 坏数量行按对象登记质量跳过；不再冻结整条规则（m01655）。
    assert detailed.data_quality_skipped == []
    for row in rows[:3]:
        assert ("OUTBOUND-EXCEPTION", "K01|G1|C1") in detailed.quality_skipped_objects


def test_outbound_skips_missing_future_and_bad_date() -> None:
    rows = [
        _outbound_row(rowId="W1", create_date=None),
        _outbound_row(rowId="W2", create_date=(NOW + timedelta(hours=1)).isoformat()),
        _outbound_row(rowId="W3", create_date="not-a-date"),
    ]
    detailed = evaluate_outbound_detailed(rows, _ctx())
    assert detailed.findings == []
    # 日期坏行也是对象级跳过，规则级 data_quality_skipped 不再被单行污染。
    assert detailed.data_quality_skipped == []
    assert ("OUTBOUND-EXCEPTION", "K01|G1|C1") in detailed.quality_skipped_objects


def test_outbound_partial_marks_no_auto_close() -> None:
    """单对象质量跳过只冻结该对象，不整体禁用规则自动关闭（m01655）。"""
    detailed = evaluate_outbound_detailed([_outbound_row(create_date=None)], _ctx())
    assert detailed.data_quality_skipped == []
    assert ("OUTBOUND-EXCEPTION", "K01|G1|C1") in detailed.quality_skipped_objects


def test_outbound_bad_row_skips_only_its_object() -> None:
    """(a) 单行坏数据与同规则正常行共存：只冻结坏对象，整条规则不被跳过。"""
    bad = _outbound_row(rowId="bad", goods_qua="NaN", cus_code="C-bad")
    good = _outbound_row(rowId="good", create_date=_hours_ago(25), cus_code="C-good")
    detailed = evaluate_outbound_detailed([bad, good], _ctx())
    assert len(detailed.findings) == 1
    assert detailed.findings[0].object_id == "K01|G1|C-good"
    assert detailed.findings[0].severity == "P0"
    # 规则级未跳过：正常对象的自动关闭/降级不受影响。
    assert detailed.data_quality_skipped == []
    # 仅坏对象被标记；正常对象不在集合中。
    assert ("OUTBOUND-EXCEPTION", "K01|G1|C-bad") in detailed.quality_skipped_objects
    assert ("OUTBOUND-EXCEPTION", "K01|G1|C-good") not in detailed.quality_skipped_objects


# ---------- temperature rule ----------


LOCATIONS = [
    {"name": "一号冷库", "aliases": ["1号冷库", "冷库1"], "min_c": 2.0, "max_c": 8.0},
    {"name": "常温库A", "aliases": ["常温A"], "min_c": 10.0, "max_c": 30.0},
]
# 单点规则用单地点词表：rewrite 后规则会为“每个已配置地点”生成无录入 P2，
# 多地点词表会给无关地点额外告警，干扰聚焦断言。
COLD_ONLY = [copy.deepcopy(LOCATIONS[0])]


def _temp_row(
    value: float,
    reading_at: datetime,
    *,
    location: str = "一号冷库",
    entered_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "id": f"T-{reading_at.timestamp()}",
        "wenduDd": location,
        "wenduCjsj": reading_at.isoformat(),
        "wenduZhi": value,
        "createDate": (entered_at or reading_at).isoformat(),
    }


def test_temperature_single_point_p1_and_p0() -> None:
    # 单点超限 4℃（2℃阈值差）→ P1；单点超限 8℃（≥5℃）→ P0。
    p1 = evaluate_temperature(
        [_temp_row(10.0, NOW - timedelta(hours=1))], _ctx(), locations=COLD_ONLY
    )
    assert len(p1) == 1 and p1[0].severity == "P1"
    assert p1[0].rule_id == "TEMP-EXCURSION"
    assert p1[0].object_id == "W01|一号冷库"

    p0 = evaluate_temperature(
        [_temp_row(16.0, NOW - timedelta(hours=1))], _ctx(), locations=COLD_ONLY
    )
    assert len(p0) == 1 and p0[0].severity == "P0"


def test_temperature_consecutive_points_p0() -> None:
    rows = [
        _temp_row(9.0, NOW - timedelta(hours=6)),
        _temp_row(9.0, NOW - timedelta(hours=3)),
    ]
    out = evaluate_temperature(rows, _ctx(), locations=COLD_ONLY)
    # 连续 2 点超限，最大超限 1℃ <2℃，但跨度 3h <4h → 仅 P1（不满足 P0 附加条件）。
    assert len(out) == 1 and out[0].severity == "P1"
    assert out[0].evidence["consecutiveExceedPoints"] == 2

    rows2 = [
        _temp_row(9.0, NOW - timedelta(hours=8)),
        _temp_row(9.0, NOW - timedelta(hours=2)),
    ]
    out2 = evaluate_temperature(rows2, _ctx(), locations=COLD_ONLY)
    # 跨度 6h ≥4h → P0。
    assert len(out2) == 1 and out2[0].severity == "P0"


def test_temperature_no_entry_p2() -> None:
    # 最近一次采集在 20h 前，>2×8h=16h → P2 无录入告警。
    out = evaluate_temperature(
        [_temp_row(5.0, NOW - timedelta(hours=20))], _ctx(), locations=COLD_ONLY
    )
    assert len(out) == 1 and out[0].severity == "P2"
    assert "无新温度录入" in out[0].evidence["reason"]


def test_temperature_unknown_location_p2_meta_alert() -> None:
    out = evaluate_temperature(
        [
            _temp_row(5.0, NOW - timedelta(hours=1), location="未知冷库"),
            # 配置地点给一条正常读数，避免额外触发该地点的“无录入”P2。
            _temp_row(5.0, NOW - timedelta(hours=1), location="一号冷库"),
        ],
        _ctx(),
        locations=COLD_ONLY,
    )
    assert len(out) == 1 and out[0].severity == "P2"
    assert "未知地点" in out[0].object_id
    assert out[0].evidence["rawLocation"] == "未知冷库"


def test_temperature_backfill_skipped() -> None:
    # wenduCjsj 明显早于 createDate（倒填 10h > expected 8h）→ 数据质量跳过，不判异常。
    reading = NOW - timedelta(hours=10)
    entered = NOW - timedelta(hours=1)
    detailed = evaluate_temperature_detailed(
        [_temp_row(16.0, reading, entered_at=entered)], _ctx(), locations=COLD_ONLY
    )
    assert detailed.findings == []
    # 倒填是单地点坏行，只标记对象级跳过（m01655）。
    assert detailed.data_quality_skipped == []
    assert ("TEMP-EXCURSION", "W01|一号冷库") in detailed.quality_skipped_objects


def test_temperature_bad_threshold_skipped() -> None:
    bad_locations = [{"name": "坏配置", "aliases": [], "min_c": 10.0, "max_c": 2.0}]
    detailed = evaluate_temperature_detailed(
        [_temp_row(5.0, NOW - timedelta(hours=1), location="坏配置")],
        _ctx(),
        locations=bad_locations,
    )
    assert detailed.data_quality_skipped == []
    assert ("TEMP-EXCURSION", "W01|坏配置") in detailed.quality_skipped_objects


def test_temperature_future_reading_not_alerted() -> None:
    """审计①：未来 wenduCjsj 记对象级数据质量，不判 P0/P1，也不打断其它判定。"""
    future = NOW + timedelta(hours=1)
    detailed = evaluate_temperature_detailed(
        [_temp_row(16.0, future)], _ctx(), locations=COLD_ONLY
    )
    # 未来超限行被跳过，不产生超限告警；只冻结该地点对象。
    assert detailed.findings == []
    assert detailed.data_quality_skipped == []
    assert ("TEMP-EXCURSION", "W01|一号冷库") in detailed.quality_skipped_objects


def test_temperature_bad_row_skips_only_its_object() -> None:
    """(b) 单条当前窗内 NaN / 未知地点坏行：只标记对象级跳过，不拖累正常地点。"""
    recent_nan = _temp_row(float("nan"), NOW - timedelta(hours=1), location="一号冷库")
    unknown = _temp_row(5.0, NOW - timedelta(hours=1), location="未知冷库")
    good = _temp_row(5.0, NOW - timedelta(hours=1), location="常温库A")
    detailed = evaluate_temperature_detailed(
        [recent_nan, unknown, good], _ctx(), locations=copy.deepcopy(LOCATIONS)
    )
    # 正常地点仍产生正常评估（无告警），规则整体未被跳过。
    assert detailed.data_quality_skipped == []
    assert ("TEMP-EXCURSION", "W01|一号冷库") in detailed.quality_skipped_objects
    assert ("TEMP-EXCURSION", "W01|未知地点:未知冷库") in detailed.quality_skipped_objects
    assert ("TEMP-EXCURSION", "W01|常温库A") not in detailed.quality_skipped_objects
    # dimension.kind 拆分保持不变：未知地点元告警仍在 findings 中。
    assert any(f.dimension.get("kind") == "unknown_location" for f in detailed.findings)


def test_temperature_ancient_bad_row_does_not_freeze_current_object() -> None:
    """审计 m01902：远古坏行不得永久冻结同一地点的告警生命周期。

    100 小时前的 NaN 落在当前 max_silence 窗（2 × 8h = 16h）之外：
    - 不得登记对象级跳过（否则该地点旧 P0 永远无法自动关闭）；
    - 当前窗内没有有效读数时，仍应生成「无新录入」P2。
    """
    ancient_nan = _temp_row(float("nan"), NOW - timedelta(hours=100), location="一号冷库")
    detailed = evaluate_temperature_detailed(
        [ancient_nan], _ctx(), locations=COLD_ONLY
    )
    assert ("TEMP-EXCURSION", "W01|一号冷库") not in detailed.quality_skipped_objects
    assert detailed.data_quality_skipped == []
    # 窗口内无有效点 → 仍然生成无录入 P2（不是被远古脏行抑制）
    assert len(detailed.findings) == 1
    assert detailed.findings[0].dimension.get("kind") == "no_entry"


def test_temperature_configured_location_missing_generates_no_entry() -> None:
    """审计②：配置了地点但整批无读数时，也必须显式生成无录入 P2。"""
    out = evaluate_temperature([], _ctx(), locations=COLD_ONLY)
    assert len(out) == 1 and out[0].severity == "P2"
    assert "无新温度录入" in out[0].evidence["reason"]
    assert out[0].object_id == "W01|一号冷库"


def test_temperature_excursion_and_no_entry_do_not_collide() -> None:
    """审计③：同地点超限与无录入使用不同 dimension，互不覆盖。"""
    # 多地点词表：一号冷库有超限读数，常温库A 完全无读数。
    out = evaluate_temperature(
        [_temp_row(16.0, NOW - timedelta(hours=1), location="一号冷库")],
        _ctx(),
        locations=copy.deepcopy(LOCATIONS),
    )
    assert len(out) == 2
    severities = sorted(f.severity for f in out)
    assert severities == ["P0", "P2"]  # 超限 P0 + 常温库A 无录入 P2
    # 两条 object_id 不同（不同地点），指纹不碰撞
    assert len({f.fingerprint for f in out}) == 2
    assert all(f.evidence.get("reason") is not None for f in out)


def test_temperature_historical_excursion_not_permanent() -> None:
    """审计④：超出 max_silence 窗口的历史超限点不再永久复发。"""
    # 20h 前的超限值在 16h 窗口之外：该点过期 → 只剩无录入 P2，不再判超限。
    out = evaluate_temperature(
        [_temp_row(16.0, NOW - timedelta(hours=20))], _ctx(), locations=COLD_ONLY
    )
    assert len(out) == 1 and out[0].severity == "P2"
    assert "无新温度录入" in out[0].evidence["reason"]


def test_temperature_consecutive_segments_respect_gap() -> None:
    """审计④：相邻间隔 > interval 的两个超限点不算连续段，不合成 P0。"""
    # interval=2 → max_silence=4h；两点都在窗口内，但间隔 3h > 2h 应断段。
    rows = [
        _temp_row(9.0, NOW - timedelta(hours=3.5)),
        _temp_row(9.0, NOW - timedelta(hours=0.5)),
    ]
    out = evaluate_temperature(rows, _ctx(), locations=COLD_ONLY, expected_interval_hours=2.0)
    # 间隔 3h > 2h → 两段各单点(1℃<5℃)→ P1；不会因全局 worst/跨度合成 P0。
    assert len(out) == 1 and out[0].severity == "P1"
    assert out[0].evidence["consecutiveExceedPoints"] == 1


def test_temperature_location_specific_interval() -> None:
    """审计中②：地点级 expected_interval_hours 优先于全局值。"""
    # 全局 interval=8（max_silence=16），地点 interval=1（max_silence=2）：
    # 3h 前读数在地点窗口外 → 只报无录入 P2，证明用了地点级 interval。
    loc = {"name": "一号冷库", "aliases": [], "min_c": 2.0, "max_c": 8.0,
           "expected_interval_hours": 1.0}
    out = evaluate_temperature(
        [_temp_row(5.0, NOW - timedelta(hours=3))], _ctx(),
        locations=[loc], expected_interval_hours=8,
    )
    assert len(out) == 1 and out[0].severity == "P2"
    assert out[0].evidence["effectiveIntervalHours"] == 1.0


# ---------- sources ----------


def _gateway(path: str, handler) -> GatewayClient:
    def wrapped(request: httpx.Request) -> httpx.Response:
        assert request.url.path == path
        return handler(request)

    return GatewayClient("http://gateway.test", transport=httpx.MockTransport(wrapped))


@pytest.mark.asyncio
async def test_outbound_source_sorts_oldest_and_requires_page_dto() -> None:
    seen: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params)
        return httpx.Response(200, json={"code": 10000, "data": {
            "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
            "rows": [_outbound_row()],
        }})

    result = await fetch_outbound(_gateway(OUTBOUND_PATH, handler), TOKEN)
    assert result.status == "ok"
    assert len(result.rows) == 1
    assert seen[0].get("sort") == "oldest"


@pytest.mark.asyncio
async def test_outbound_source_marks_partial_on_list_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 10000, "data": [_outbound_row()]})

    result = await fetch_outbound(_gateway(OUTBOUND_PATH, handler), TOKEN)
    assert result.status == "partial"
    assert result.truncated is True


@pytest.mark.asyncio
async def test_temperature_source_uses_query_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 10000, "data": {
            "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
            "rows": [_temp_row(5.0, NOW - timedelta(hours=1))],
        }})

    result = await fetch_temperature(_gateway(TEMPERATURE_PATH, handler), TOKEN)
    assert result.status == "ok"
    assert len(result.rows) == 1


# ---------- config contract: versioned YAML + independent switches ----------


def test_repo_scan_yaml_declares_f016_contract() -> None:
    """版本化 YAML：温度使用用户授权的 dev 演示词表，prod 必须重新确认。"""
    from pathlib import Path

    config_path = Path(__file__).resolve().parents[1] / "config" / "scan.yaml"
    loaded = load_scan_config(config_path)
    assert {"outbound", "temperature"}.issubset(set(SUPPORTED_SCAN_TYPE_LIST))
    rules = loaded.document.rules
    assert rules.outbound.enabled is True and rules.outbound.p0Hours == 24
    assert rules.temperature.enabled is True
    locations = {location.name: location for location in rules.temperature.locations}
    assert set(locations) == {"一号冷库", "二号冷库", "常温库A", "三号冷库"}
    assert (locations["一号冷库"].min_c, locations["一号冷库"].max_c) == (2.0, 8.0)
    assert (locations["二号冷库"].min_c, locations["二号冷库"].max_c) == (-20.0, -15.0)
    assert (locations["常温库A"].min_c, locations["常温库A"].max_c) == (10.0, 25.0)
    # 默认调度不含两类新巡检：不影响 v0.2.0
    assert "temperature" not in loaded.document.schedule.scanTypes
    assert "outbound" not in loaded.document.schedule.scanTypes
    # 两类规则 id 进入配置快照与哈希
    snapshot = loaded.snapshot
    assert "OUTBOUND-EXCEPTION" in snapshot and "TEMP-EXCURSION" in snapshot


def test_temperature_enabled_without_locations_fails_closed() -> None:
    """审计中①：enabled=true + locations=[] 必须 fail-closed，禁止用示例阈值空跑。

    强化（复审高项）：地点缺 expected_interval_hours、非有限阈值、空白地点名、
    跨地点重复 alias 都必须被 pydantic 拒绝——真实业务值与词表缺一不可。
    """
    from pydantic import ValidationError

    from app.scan.config import TemperatureRules

    with pytest.raises(ValidationError):
        TemperatureRules(enabled=True, locations=[])
    # 地点缺必填 expected_interval_hours → 拒绝（真实录入间隔必须业务提供）
    with pytest.raises(ValidationError):
        TemperatureRules(
            enabled=True,
            locations=[{"name": "一号冷库", "aliases": [], "min_c": 2.0, "max_c": 8.0}],
        )
    # 非有限阈值 / 非有限 min_c → 拒绝
    with pytest.raises(ValidationError):
        TemperatureRules(enabled=True, expectedIntervalHours=float("inf"),
                         locations=[{"name": "一号冷库", "aliases": [], "min_c": 2.0,
                                     "max_c": 8.0, "expected_interval_hours": 8.0}])
    with pytest.raises(ValidationError):
        TemperatureRules(
            enabled=True,
            locations=[{"name": "一号冷库", "aliases": [], "min_c": float("nan"),
                        "max_c": 8.0, "expected_interval_hours": 8.0}],
        )
    # 空白地点名 / 跨地点重复 alias → 拒绝
    with pytest.raises(ValidationError):
        TemperatureRules(
            enabled=True,
            locations=[{"name": "   ", "aliases": [], "min_c": 2.0,
                        "max_c": 8.0, "expected_interval_hours": 8.0}],
        )
    with pytest.raises(ValidationError):
        TemperatureRules(
            enabled=True,
            locations=[
                {"name": "一号冷库", "aliases": ["冷库"], "min_c": 2.0,
                 "max_c": 8.0, "expected_interval_hours": 8.0},
                {"name": "二号冷库", "aliases": ["冷库"], "min_c": 2.0,
                 "max_c": 8.0, "expected_interval_hours": 8.0},
            ],
        )
    # 有真实地点词表（含必填间隔）时允许启用
    enabled = TemperatureRules(
        enabled=True,
        locations=[{"name": "一号冷库", "aliases": [], "min_c": 2.0, "max_c": 8.0,
                    "expected_interval_hours": 8.0}],
    )
    assert enabled.enabled is True


def test_outbound_p0_hours_must_be_finite_positive() -> None:
    """(c) OutboundRules.p0Hours 必须是有限正数；inf/NaN/0 一律拒绝。"""
    assert OutboundRules(p0Hours=24).p0Hours == 24
    for bad in (float("inf"), float("-inf"), float("nan"), 0, -1):
        with pytest.raises(ValidationError):
            OutboundRules(p0Hours=bad)


def test_temperature_single_point_abs_c_must_be_positive() -> None:
    """(d) p0SinglePointAbsC=0 会把 exceed=0 的正常读数判成 P0，必须拒绝。"""
    with pytest.raises(ValidationError):
        TemperatureRules(p0SinglePointAbsC=0)
    assert TemperatureRules(p0SinglePointAbsC=5.0).p0SinglePointAbsC == 5.0


# ---------- service integration: independent switches ----------


@pytest.mark.asyncio
async def test_temperature_disabled_by_default_is_skipped() -> None:
    """温度默认 enabled=false：即使请求该类型也不取数、不告警。"""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"code": 10000, "data": {
            "pageIndex": 1, "pageSize": 100, "total": 0, "pages": 0, "rows": [],
        }})

    store = MemoryScanStore()
    run = await run_scan(
        scan_id="scan-temp-off", scan_types=["temperature"], principal=_user(), token=TOKEN,
        client=_gateway(TEMPERATURE_PATH, handler), store=store,
        allowed_warehouses=["W01"], notification_mode="dry_run",
    )
    assert calls["n"] == 0
    assert run["sourceStatus"] == []
    assert "temperature" in run["counts"]["skippedTypes"]


@pytest.mark.asyncio
async def test_outbound_enabled_and_finding_persisted() -> None:
    """出货异常默认 enabled=true：命中行落告警，文案不含未闭环。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 10000, "data": {
            "pageIndex": 1, "pageSize": 100, "total": 1, "pages": 1,
            "rows": [_outbound_row(create_date=_hours_ago(25))],
        }})

    store = MemoryScanStore()
    run = await run_scan(
        scan_id="scan-outbound", scan_types=["outbound"], principal=_user(), token=TOKEN,
        client=_gateway(OUTBOUND_PATH, handler), store=store,
        allowed_warehouses=["W01"], notification_mode="dry_run",
    )
    assert run["status"] == "succeeded"
    assert run["counts"]["findings"] == 1
    alerts = await store.list_alerts({"warehouseId": "W01"})
    assert len(alerts) == 1
    assert alerts[0]["ruleId"] == "OUTBOUND-EXCEPTION"
    assert "未闭环" not in str(alerts[0].get("evidence") or "")


@pytest.mark.asyncio
async def test_temperature_partial_source_skips_evaluation_and_auto_close() -> None:
    """审计高③：partial 源（裸 List）时温度跳过求值、不落告警、禁自动关闭。"""
    enabled_cfg = copy.deepcopy(DEFAULT_CONFIG)
    enabled_cfg["rules"] = copy.deepcopy(DEFAULT_CONFIG["rules"])
    enabled_cfg["rules"]["temperature"] = {
        "enabled": True,
        "locations": [{"name": "一号冷库", "aliases": [], "min_c": 2.0, "max_c": 8.0}],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        # 裸 List → require_page_dto=True 标 partial
        return httpx.Response(200, json={"code": 10000, "data": [
            _temp_row(16.0, NOW - timedelta(hours=1)),
        ]})

    store = MemoryScanStore()
    run = await run_scan(
        scan_id="scan-temp-partial", scan_types=["temperature"], principal=_user(), token=TOKEN,
        client=_gateway(TEMPERATURE_PATH, handler), store=store,
        allowed_warehouses=["W01"], notification_mode="dry_run", config=enabled_cfg,
    )
    # partial 源被标记；温度规则跳过求值，不产生任何告警（含未来/超限/无录入）。
    assert run["partial"] is True
    assert run["counts"]["findings"] == 0


# ---------- 复审专项：指纹贯穿自动关闭 + 质量跳过阻止降级 ----------


def test_list_auto_resolve_candidates_includes_fingerprint() -> None:
    """自动关闭候选必须返回 fingerprint，才能按维度指纹判定命中。"""
    import asyncio

    store = MemoryScanStore()
    alert = {
        "fingerprint": "fp-candidate",
        "severity": "P0", "ruleId": "TEMP-EXCURSION", "ruleVersion": "v0.2.1",
        "objectType": "temperature_location", "objectId": "W01|一号冷库",
        "dimension": {"warehouse": "W01", "kind": "excursion"},
        "title": "TEMP-EXCURSION P0", "evidence": {}, "suggestedActions": [],
        "warehouseId": "W01", "lastSeenAt": _hours_ago(100),
    }
    asyncio.run(store.upsert_alert(alert))
    candidates = asyncio.run(store.list_auto_resolve_candidates(
        warehouse="W01", rule_ids=["TEMP-EXCURSION"], before_iso=NOW.isoformat(),
    ))
    assert candidates and candidates[0]["fingerprint"] == "fp-candidate"


def test_auto_resolve_uses_fingerprint_not_object_id() -> None:
    """复审高项：旧 P0 excursion 消失、同地点仍有 P2 no_entry → 旧 P0 应被关闭。

    按 (rule_id, object_id) 判命中会把两条同对象告警视为同一条件，导致旧 P0 永不关。
    改为按 fingerprint（含 dimension.kind）判定后，旧维度消失即可关闭。
    """
    import asyncio

    from app.scan.rules.base import Finding
    from app.scan.service import _auto_resolve_cleared

    store = MemoryScanStore()
    # 旧 P0 超限告警（dimension.kind=excursion），指纹与本次 no_entry 不同
    asyncio.run(store.upsert_alert({
        "fingerprint": "fp-old-p0-excursion",
        "severity": "P0", "ruleId": "TEMP-EXCURSION", "ruleVersion": "v0.2.1",
        "objectType": "temperature_location", "objectId": "W01|一号冷库",
        "dimension": {"warehouse": "W01", "kind": "excursion"},
        "title": "TEMP-EXCURSION P0", "evidence": {}, "suggestedActions": [],
        "warehouseId": "W01", "lastSeenAt": _hours_ago(100),
    }))
    # 本次只命中同地点的 P2 无录入（fingerprint 必然不同于上面手工构造的旧指纹）
    current = Finding(
        rule_id="TEMP-EXCURSION", rule_version="v0.2.1", severity="P2",
        object_type="temperature_location", object_id="W01|一号冷库",
        dimension={"warehouse": "W01", "kind": "no_entry"},
        evidence={},
    )
    assert current.fingerprint != "fp-old-p0-excursion"
    counts: dict = {}
    asyncio.run(_auto_resolve_cleared(
        store, evaluations={}, rule_ok={"TEMP-EXCURSION": True},
        findings={current.fingerprint: current},
        scan_id="scan-fp", warehouse="W01", trace_id="trace-fp",
        started_at=NOW.isoformat(), dry_run=False, partial=False, counts=counts,
    ))
    assert counts.get("alertsAutoResolved") == 1
    closed = [a for a in store.alerts.values() if a["fingerprint"] == "fp-old-p0-excursion"]
    assert closed and closed[0]["state"] == "resolved"


def test_upsert_no_downgrade_keeps_higher_severity() -> None:
    """复审高项：质量跳过的规则，低级别 finding 不得把旧高级别告警降级。"""
    import asyncio

    store = MemoryScanStore()
    fp = "fp-outbound-quality"
    asyncio.run(store.upsert_alert({
        "fingerprint": fp, "severity": "P0", "ruleId": "OUTBOUND-EXCEPTION",
        "ruleVersion": "v0.2.1", "objectType": "outbound_exception",
        "objectId": "K01|G1|C1", "dimension": {"warehouse": "W01"},
        "title": "OUTBOUND-EXCEPTION P0", "evidence": {"v": "old"},
        "suggestedActions": [], "warehouseId": "W01", "lastSeenAt": _hours_ago(100),
    }))
    p1 = {
        "fingerprint": fp, "severity": "P1", "ruleId": "OUTBOUND-EXCEPTION",
        "ruleVersion": "v0.2.1", "objectType": "outbound_exception",
        "objectId": "K01|G1|C1", "dimension": {"warehouse": "W01"},
        "title": "OUTBOUND-EXCEPTION P1", "evidence": {"v": "new"},
        "suggestedActions": [], "warehouseId": "W01", "lastSeenAt": NOW.isoformat(),
    }
    # 不带标志：旧行为会降级为 P1（证明标志是必要的）
    asyncio.run(store.upsert_alert(dict(p1)))
    assert store.alerts[1]["severity"] == "P1"
    # 带 no_downgrade：重新 seed 一条 P0，再 upsert P1 不应降级
    store2 = MemoryScanStore()
    asyncio.run(store2.upsert_alert({
        **p1, "severity": "P0", "title": "OUTBOUND-EXCEPTION P0", "evidence": {"v": "old"},
    }))
    asyncio.run(store2.upsert_alert(dict(p1), no_downgrade=True))
    assert store2.alerts[1]["severity"] == "P0"
    # 升级仍允许
    asyncio.run(store2.upsert_alert(
        {**p1, "severity": "P0", "evidence": {"v": "escalate"}}, no_downgrade=True
    ))
    assert store2.alerts[1]["severity"] == "P0"


# ---------- 复议专项：候选超过 max_pages 时必须显式 partial ----------


@pytest.mark.asyncio
async def test_outbound_candidate_overflow_marks_partial_not_silent_empty() -> None:
    """审计 m01655：候选行超过 page_size × max_pages 时不能静默截断。

    真实复现是「2000 条旧候选 + 1 条最新差异行」，这里按同一语义缩放成
    pageSize=2 / maxPages=2 / total=5：第 3 页的最新异常永远取不到。
    正确行为不是"当作没有异常"，而是 status=partial + max_pages_exceeded、
    run.partial=True、产出 SCAN-PARTIAL 告警，并禁止自动关闭。
    """
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["rules"] = copy.deepcopy(DEFAULT_CONFIG["rules"])
    cfg["rules"]["outbound"] = {
        "enabled": True, "p0Hours": 24, "pageSize": 2, "maxPages": 2,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(dict(request.url.params).get("pageIndex", "1"))
        rows = [
            _outbound_row(rowId=f"row-p{page}-{i}", create_date=_hours_ago(30))
            for i in range(2)
        ] if page <= 2 else [_outbound_row(rowId="row-newest", create_date=_hours_ago(30))]
        return httpx.Response(200, json={"code": 10000, "data": {
            "pageIndex": page, "pageSize": 2, "total": 5, "pages": 3, "rows": rows,
        }})

    store = MemoryScanStore()
    run = await run_scan(
        scan_id="scan-outbound-overflow", scan_types=["outbound"],
        principal=_user(), token=TOKEN,
        client=_gateway(OUTBOUND_PATH, handler), store=store,
        allowed_warehouses=["W01"], notification_mode="dry_run", config=cfg,
    )

    # 数据没取全必须显式暴露，不能被当成"本次没有异常"
    assert run["partial"] is True
    source_status = run["sourceStatus"][0]
    assert source_status["status"] == "partial"
    assert "max_pages_exceeded" in str(source_status.get("errorSummary") or "")

    alerts = await store.list_alerts({"warehouseId": "W01"})
    rule_ids = {a["ruleId"] for a in alerts}
    # SCAN-PARTIAL 告警必须出现，提示运维数据不完整
    assert "SCAN-PARTIAL" in rule_ids
    # 第 3 页的最新异常行没有被取到，但这是"已知不完整"，不是静默遗漏
    assert "row-newest" not in {str(a.get("objectId")) for a in alerts}


@pytest.mark.asyncio
async def test_outbound_default_paging_budget_is_not_the_global_twenty() -> None:
    """审计 m01902：编排层必须真的按 outbound 预算翻页，而不是永远只用全局 20 页。

    配置里只写 enabled/p0Hours（不写 pageSize/maxPages），验证默认预算生效：
    21 页候选（每页 100 行）+ 第 22 页空，必须全部请求到，不能被 20 页截断成 partial。
    """
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["rules"] = copy.deepcopy(DEFAULT_CONFIG["rules"])
    cfg["rules"]["outbound"] = {"enabled": True, "p0Hours": 24}   # 故意不写分页键
    cfg["scan"] = {**copy.deepcopy(DEFAULT_CONFIG["scan"]), "maxPages": 20}

    seen_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(dict(request.url.params).get("pageIndex", "1"))
        seen_pages.append(page)
        rows = [
            _outbound_row(rowId=f"row-p{page}-{i}", create_date=_hours_ago(2))
            for i in range(100)
        ] if page <= 21 else []
        return httpx.Response(200, json={"code": 10000, "data": {
            "pageIndex": page, "pageSize": 100, "total": 2100, "pages": 21, "rows": rows,
        }})

    store = MemoryScanStore()
    run = await run_scan(
        scan_id="scan-outbound-paging-budget", scan_types=["outbound"],
        principal=_user(), token=TOKEN,
        client=_gateway(OUTBOUND_PATH, handler), store=store,
        allowed_warehouses=["W01"], notification_mode="dry_run", config=cfg,
    )

    # 21 页候选全部取到（第 21 页即 pages 声明的末页），没被全局 20 页截断
    assert max(seen_pages) == 21, seen_pages
    assert run["partial"] is False
    assert run["sourceStatus"][0]["status"] == "ok"


@pytest.mark.asyncio
async def test_outbound_partial_source_does_not_downgrade_existing_p0() -> None:
    """审计 m01902：出货异常取数不完整时不得把旧 P0 降成 P1，也不得自动关闭。

    复现：旧 P0 已在库；本次第 1 页返回同对象 P1、第 2 页 500 → 源 partial。
    正确行为：不评估（不产生 P1），旧 P0 保持 P0 且仍 open。
    """
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["rules"] = copy.deepcopy(DEFAULT_CONFIG["rules"])
    cfg["rules"]["outbound"] = {"enabled": True, "p0Hours": 24}

    store = MemoryScanStore()
    # 先造一条旧 P0（指纹由规则真实生成，避免"新建"分支导致误判）
    old_row = _outbound_row(rowId="row-old-p0", create_date=_hours_ago(30))
    old_eval = evaluate_outbound_detailed([old_row], _ctx(), p0_hours=24)
    assert old_eval.findings and old_eval.findings[0].severity == "P0"
    old_finding = old_eval.findings[0]
    await store.upsert_alert(
        {
            **old_finding.to_alert(),
            "warehouseId": "W01",
            "lastSeenAt": NOW.isoformat(),
            "scanId": "scan-previous",
        },
        notification=None,
    )
    before = await store.list_alerts({"warehouseId": "W01"})
    assert before[0]["severity"] == "P0"

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(dict(request.url.params).get("pageIndex", "1"))
        if page == 1:
            # 同对象一行"看起来更轻"的差异（2h）→ 若被评估会把 P0 降成 P1
            rows = [_outbound_row(rowId="row-old-p0", create_date=_hours_ago(2))]
            return httpx.Response(200, json={"code": 10000, "data": {
                "pageIndex": 1, "pageSize": 100, "total": 150, "pages": 2, "rows": rows,
            }})
        return httpx.Response(500, json={"code": 50000, "message": "boom"})

    run = await run_scan(
        scan_id="scan-outbound-partial", scan_types=["outbound"],
        principal=_user(), token=TOKEN,
        client=_gateway(OUTBOUND_PATH, handler), store=store,
        allowed_warehouses=["W01"], notification_mode="dry_run", config=cfg,
    )

    assert run["partial"] is True
    alerts = await store.list_alerts({"warehouseId": "W01"})
    p0_alerts = [a for a in alerts if a["ruleId"] == "OUTBOUND-EXCEPTION"]
    assert len(p0_alerts) == 1
    assert p0_alerts[0]["severity"] == "P0", p0_alerts[0]
    assert p0_alerts[0]["state"] == "open"
