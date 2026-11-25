"""BACKLOG-GROWTH 规则契约（阶段3，方案 §8.2.5 / 用户 m04555 固化）。

纯函数测试：不依赖 PG / 网关。序列按 (observed_at, observation_id) 稳定升序。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.scan.rules.backlog import (
    GRADED_QUEUES, RULE_ID, RULE_VERSION, evaluate_backlog, to_decimal,
)
from app.scan.rules.base import RuleContext

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)
CTX = RuleContext(warehouse="W01", now=NOW)


def _hist(queue: str, values: list, start: int = 0) -> list[dict]:
    """构造某队列的历史样本（已稳定排序）。"""
    return [
        {"queueType": queue, "value": v, "observedAt": f"2026-11-25T{start + i:02d}:00:00+00:00",
         "observationId": start + i + 1}
        for i, v in enumerate(values)
    ]


def _cur(queue: str, value) -> dict:
    return {"queueType": queue, "value": value}


def _sample(values: dict) -> list[dict]:
    out = []
    for q in ("receipt", "to_up", "pick", "cur_pick"):
        if q in values:
            out.append(_cur(q, values[q]))
    return out


# ---------- 第 1–6 次扫描序列 ----------

@pytest.mark.parametrize("scan_no", [1, 2, 3])
def test_first_three_scans_only_build_baseline(scan_no):
    # 每次 +100%（远超门槛）但前 3 次只建基线
    history = _hist("pick", [10 * (2 ** i) for i in range(scan_no - 1)])
    assert evaluate_backlog([_cur("pick", 10 * (2 ** scan_no))], history, CTX) == []


def test_fourth_scan_single_cycle_growth_is_p2():
    history = _hist("pick", [100, 110, 120])  # 第 1~3 次，增幅不足
    [f] = evaluate_backlog([_cur("pick", 200)], history, CTX)
    assert (f.rule_id, f.severity, f.rule_version) == (RULE_ID, "P2", RULE_VERSION)
    assert f.object_id == "W01|pick"
    assert f.object_type == "backlog_queue"
    assert f.evidence["sampleIndex"] == 4
    assert f.evidence["consecutiveHits"] == 1
    assert f.evidence["absoluteDelta"] == "80"
    assert f.evidence["growthRatio"] == "0.6666666666666666666666666667"


def test_sixth_scan_three_consecutive_growth_is_p1():
    # 第 1~3 次基线不命中；第 4、5、6 次每一对都 ≥30% 且 Δ≥10：100→140(+40%)→200(+42.9%)→300(+50%)
    history = _hist("pick", [60, 70, 80, 100, 140, 200])
    [f] = evaluate_backlog([_cur("pick", 300)], history, CTX)
    assert f.severity == "P1"
    assert f.evidence["consecutiveHits"] == 3
    assert f.evidence["sampleIndex"] == 7


def test_sixth_scan_p1_with_exact_three_history_hits():
    # 精确到"最早第 6 次"：第 4、5 次命中（100→140、140→200），第 6 次 200→300 命中 → P1
    history = _hist("pick", [60, 70, 80, 100, 140, 200][:5])  # 60,70,80,100,140
    # 当前是第 6 次 = 200：100→140(+40%,Δ40) 命中，140→200(+42.9%,Δ60) 命中 → 只有 2 对连续 → P2
    [f] = evaluate_backlog([_cur("pick", 200)], history, CTX)
    assert f.severity == "P2"
    assert f.evidence["sampleIndex"] == 6
    # 再往后一次（第 7 次 = 300）三对连续 → P1
    history7 = _hist("pick", [60, 70, 80, 100, 140, 200])
    [g] = evaluate_backlog([_cur("pick", 300)], history7, CTX)
    assert g.severity == "P1"


def test_growth_below_30_percent_breaks_consecutive_chain():
    # 120→150 只有 +25%：即使 Δ=30 ≥ 10，也不算命中，连续链被打断 → P2 而非 P1
    history = _hist("pick", [80, 90, 100, 120, 150])
    [f] = evaluate_backlog([_cur("pick", 200)], history, CTX)
    assert f.severity == "P2"
    assert f.evidence["consecutiveHits"] == 1  # 只有 150→200 (+33.3%) 命中


def test_p1_needs_three_consecutive_not_cumulative():
    # 第 4 次命中、第 5 次未命中、第 6 次命中 → 只算连续 1 次 → P2
    history = _hist("pick", [100, 110, 120, 200, 210])  # 120→200 命中，200→210 未命中
    [f] = evaluate_backlog([_cur("pick", 300)], history, CTX)
    assert f.severity == "P2"
    assert f.evidence["consecutiveHits"] == 1


def test_p1_earliest_is_sixth_scan_not_fifth():
    # 第 4、5 次连续命中，第 6 次（本例第 5 次）只连续 2 次 → P2
    history = _hist("pick", [100, 110, 120, 200])
    [f] = evaluate_backlog([_cur("pick", 300)], history, CTX)
    assert f.evidence["sampleIndex"] == 5
    assert f.severity == "P2"


# ---------- 门槛边界 ----------

@pytest.mark.parametrize("prev,cur,expected", [
    (100, 130, True),   # 恰好 30% 且 30 ≥ 10
    (100, 129, False),  # 29% 不足
    (1000, 1009, False),  # 比例 0.9% 不足（即使 delta 9 < 10 也不行）
    (10000, 10009, False),  # delta 9 < 10 即使比例够也不行
    (10000, 10010, False),  # 恰好 10 但比例 0.1% 不足
    (100, 109, False),  # 9% 不足
    (0, 500, False),    # 基线 0：不做百分比判断，不误报
    (0, 0, False),
])
def test_growth_threshold_edges(prev, cur, expected):
    history = _hist("pick", [1, 1, prev])  # 第 3 次作为前值
    out = evaluate_backlog([_cur("pick", cur)], history, CTX)
    assert bool(out) is expected


def test_declining_or_flat_queue_never_alerts():
    history = _hist("pick", [100, 150, 200])
    assert evaluate_backlog([_cur("pick", 150)], history, CTX) == []
    assert evaluate_backlog([_cur("pick", 200)], history, CTX) == []


# ---------- 零基线 / 负值 / 非法值 ----------

def test_zero_baseline_then_real_baseline_next_scan_can_alert():
    # 第 1~3 次基线为 0（不误报），第 4 次 0→100 不告警，但样本保留；第 5 次 100→200 告警
    history = _hist("pick", [0, 0, 0])
    assert evaluate_backlog([_cur("pick", 100)], history, CTX) == []
    history = _hist("pick", [0, 0, 0, 100])
    [f] = evaluate_backlog([_cur("pick", 200)], history, CTX)
    assert f.severity == "P2"
    assert f.evidence["previous"] == "100"


@pytest.mark.parametrize("bad", [-5, "abc", None, "", True, "NaN"])
def test_negative_or_invalid_values_skip_queue_without_alert(bad):
    history = _hist("pick", [100, 110, 120])
    assert evaluate_backlog([_cur("pick", bad)], history, CTX) == []
    assert to_decimal(bad) is None


def test_invalid_history_values_are_ignored_in_series():
    # 历史中夹一条非法值：不参与序列，但其余样本仍按顺序
    history = _hist("pick", [100, "x", 120, 150])[:2] + [{"queueType": "pick", "value": "x"}] + _hist("pick", [120, 150], start=10)
    [f] = evaluate_backlog([_cur("pick", 200)], history, CTX)
    assert f.evidence["sampleIndex"] == 4  # 100,120,150 三个有效历史 + 当前
    assert f.evidence["previous"] == "150"


# ---------- 三队列互不聚合 ----------

def test_queues_are_judged_independently_and_never_summed():
    # receipt 突增、to_up 下降、pick 平稳；只有 receipt 告警
    history = _hist("receipt", [100, 110, 120]) + _hist("to_up", [500, 400, 300]) + _hist("pick", [50, 50, 50])
    samples = _sample({"receipt": 300, "to_up": 100, "pick": 50})
    out = evaluate_backlog(samples, history, CTX)
    assert [f.object_id for f in out] == ["W01|receipt"]
    assert out[0].severity == "P2"


def test_cur_pick_is_diagnostic_only_even_if_it_grows():
    history = _hist("cur_pick", [10, 20, 40]) + _hist("pick", [100, 110, 120])
    samples = _sample({"cur_pick": 1000, "pick": 121})
    assert evaluate_backlog(samples, history, CTX) == []


def test_multiple_queues_can_alert_in_same_scan():
    history = _hist("receipt", [100, 110, 120]) + _hist("pick", [200, 220, 240])
    out = evaluate_backlog(_sample({"receipt": 400, "pick": 500}), history, CTX)
    assert sorted(f.object_id for f in out) == ["W01|pick", "W01|receipt"]


# ---------- 规则参数透传 ----------

def test_rule_params_are_recorded_on_finding():
    history = _hist("pick", [100, 110, 120])
    [f] = evaluate_backlog([_cur("pick", 200)], history, CTX, growth_ratio=0.5, absolute_delta=20)
    assert f.rule_params == {"growthRatio": 0.5, "absoluteDelta": 20, "baselineScans": 3, "consecutiveForP1": 3}
    assert f.suggested_actions == ("NOTIFY_QC", "CHECK_BATCH")


def test_configurable_baseline_and_consecutive():
    history = _hist("pick", [100, 110, 120, 200])
    # baseline_scans=2 → 第 3 次就能出 P2；consecutive_for_p1=2 → 两次连续就是 P1
    out = evaluate_backlog([_cur("pick", 300)], history, CTX, baseline_scans=2, consecutive_for_p1=2)
    assert out[0].severity == "P1"


def test_graded_queues_constant_matches_contract():
    assert GRADED_QUEUES == ("receipt", "to_up", "pick")
