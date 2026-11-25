"""待办积压规则（v0.2.0）：BACKLOG-GROWTH。

契约（方案 §8.2.5，用户 m04555 固化）：
- 待收货 receipt / 待上架 to_up / 待拣货 pick **分别判定**，不做四队列总和；
- `query-cur-pick` 只做诊断，不参与分级；
- 前 ``baseline_scans``（默认 3）次完整扫描只建基线；
- 第 4 次起，单周期相邻增长同时满足 ``growth ≥ growth_ratio``（0.30）且
  ``absolute_delta ≥ absolute_delta``（10）→ P2；
- P1 = 最近 ``consecutive_for_p1``（3）次相邻增长**全部**满足门槛（最早第 6 次）；
- 基线为 0 时不做百分比判断（不除零、不误报）；
- 负值 / 非数值样本：该队列跳过并 ``rule_degraded``，不参与基线也不告警；
- 历史样本必须与本次 ``rule_version`` 一致（版本变化不混用旧基线，由调用方过滤）。

纯函数：输入本次样本 + 该 (warehouse, queue_type) 的历史样本，输出 Findings。
历史样本按 ``observed_at, observation_id`` 稳定升序。

阶段5 起同时返回评估覆盖与数据质量跳过：非法数值与“基线期尚未可判定”
都记入跳过集合——条件未被判定时不允许该规则本次自动关闭。
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.scan.rules.base import (
    EvaluatedKey,
    Finding,
    RuleContext,
    RuleEvaluation,
    dimension_hash,
)

RULE_ID = "BACKLOG-GROWTH"
RULE_VERSION = "v0.2.0"
OBJECT_TYPE = "backlog_queue"
ENDPOINT = "/dashboard/query-pend-snapshot"
ACTIONS = ("NOTIFY_QC", "CHECK_BATCH")

# 参与分级的队列；cur_pick 仅诊断
GRADED_QUEUES: tuple[str, ...] = ("receipt", "to_up", "pick")
DIAGNOSTIC_QUEUES: tuple[str, ...] = ("cur_pick",)


def to_decimal(value: Any) -> Decimal | None:
    """把快照值转成 Decimal；None / 布尔 / 空串 / 非数字 / 负数 → None。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        dec = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not dec.is_finite() or dec < 0:
        return None
    return dec


def _hit(previous: Decimal, current: Decimal, growth_ratio: Decimal, absolute_delta: Decimal) -> bool:
    """单周期相邻增长是否同时满足百分比与绝对增量门槛；基线 0 不做百分比判断。"""
    delta = current - previous
    if delta < absolute_delta:
        return False
    if previous == 0:
        # 基线 0：没有可比的分母，不做百分比判断（不误报）
        return False
    return (delta / previous) >= growth_ratio


def evaluate_backlog_detailed(
    samples: list[dict[str, Any]],
    history: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    growth_ratio: float = 0.30,
    absolute_delta: int = 10,
    baseline_scans: int = 3,
    consecutive_for_p1: int = 3,
) -> RuleEvaluation:
    """按 warehouse + queue_type 判定积压增长，返回命中、覆盖与数据质量跳过。

    ``samples``：本次快照的队列样本（queueType/value/diagnostic）。
    ``history``：同一 warehouse 下各队列的历史有效样本（已按 rule_version 过滤，
    按 observed_at, observation_id 稳定升序），元素含 queueType/value。
    """
    params = {
        "growthRatio": growth_ratio, "absoluteDelta": absolute_delta,
        "baselineScans": baseline_scans, "consecutiveForP1": consecutive_for_p1,
    }
    ratio = Decimal(str(growth_ratio))
    floor_delta = Decimal(str(absolute_delta))
    evaluation = RuleEvaluation()

    for sample in samples:
        queue = str(sample.get("queueType") or "").strip()
        value = to_decimal(sample.get("value"))
        if queue in DIAGNOSTIC_QUEUES or sample.get("diagnostic"):
            continue
        if queue not in GRADED_QUEUES:
            continue

        object_id = f"{ctx.warehouse}|{queue}"
        dimension = {"warehouse": ctx.warehouse, "queueType": queue}
        if value is None:
            # 负值 / 非法值：数据质量跳过，不参与基线、不告警
            evaluation.skip(RULE_ID)
            continue

        series: list[Decimal] = []
        for item in history:
            if item.get("queueType") != queue:
                continue
            past = to_decimal(item.get("value"))
            if past is None:
                continue
            series.append(past)
        # 第 n 次完整扫描 = 历史样本数 + 1
        sample_index = len(series) + 1
        if sample_index <= baseline_scans:
            # 基线期：增长条件尚未可判定 → 不记覆盖，也不允许本次自动关闭
            evaluation.skip(RULE_ID)
            continue

        # 相邻增长序列（含最后一对 history[-1] → current）
        points = series + [value]
        hits: list[bool] = [
            _hit(points[i - 1], points[i], ratio, floor_delta) for i in range(1, len(points))
        ]
        current_hit = hits[-1]
        if not current_hit:
            # 增长条件确定为假 → 记覆盖，允许自动关闭历史告警
            evaluation.evaluated_keys.append(
                EvaluatedKey(
                    rule_id=RULE_ID,
                    object_type=OBJECT_TYPE,
                    object_id=object_id,
                    dimension_hash=dimension_hash(dimension),
                )
            )
            continue
        consecutive = 0
        for hit in reversed(hits):
            if not hit:
                break
            consecutive += 1
        severity = "P1" if consecutive >= consecutive_for_p1 else "P2"

        previous = points[-2]
        delta = value - previous
        evidence = {
            "queueType": queue,
            "current": str(value),
            "previous": str(previous),
            "absoluteDelta": str(delta),
            "growthRatio": (str(delta / previous) if previous != 0 else None),
            "sampleIndex": sample_index,
            "baselineScans": baseline_scans,
            "consecutiveHits": consecutive,
            "thresholds": {"growthRatio": str(ratio), "absoluteDelta": str(floor_delta)},
            "sourceEndpoint": ENDPOINT,
            "observedAt": ctx.now.isoformat(),
        }
        evaluation.findings.append(
            Finding(
                rule_id=RULE_ID, rule_version=RULE_VERSION, severity=severity,
                object_type=OBJECT_TYPE, object_id=object_id,
                dimension=dimension, evidence=evidence,
                suggested_actions=ACTIONS, rule_params=params,
            )
        )
        evaluation.evaluated_keys.append(
            EvaluatedKey(
                rule_id=RULE_ID,
                object_type=OBJECT_TYPE,
                object_id=object_id,
                dimension_hash=dimension_hash(dimension),
            )
        )
    return evaluation


def evaluate_backlog(
    samples: list[dict[str, Any]],
    history: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    growth_ratio: float = 0.30,
    absolute_delta: int = 10,
    baseline_scans: int = 3,
    consecutive_for_p1: int = 3,
) -> list[Finding]:
    """兼容入口：只返回命中列表（覆盖信息见 evaluate_backlog_detailed）。"""
    return evaluate_backlog_detailed(
        samples,
        history,
        ctx,
        growth_ratio=growth_ratio,
        absolute_delta=absolute_delta,
        baseline_scans=baseline_scans,
        consecutive_for_p1=consecutive_for_p1,
    ).findings
