"""进货延时规则（v0.2.0）：DELAY-OVERDUE。

条件（方案 §8.2.4）：im_data（计划到货时间）< now 视为延时，按超时时长分级——
- > 24h → P0
- 2–24h → P1
- 0–2h → P2
- im_data >= now → 尚未延时，不判异常

数据质量：im_data 为空/解析失败/未来时间 → 跳过（方案 §7.5），不误报。
objectId = notice_id。evidence 中司机姓名/电话/车号做脱敏。
建议动作：CONTACT_CUSTOMER、NOTIFY_QC。

阶段5 起同时返回评估覆盖与数据质量跳过：时间缺失/未来时间的行不算
“已评估且正常”，DELAY-OVERDUE 本次禁止自动关闭。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.scan.rules.base import (
    EvaluatedKey,
    Finding,
    RuleContext,
    RuleEvaluation,
    dimension_hash,
)

RULE_VERSION = "v0.2.0"
ENDPOINT = "/daycheck/delay/im-delay"
OBJECT_TYPE = "delivery_notice"
ACTIONS = ("CONTACT_CUSTOMER", "NOTIFY_QC")
RULE_ID = "DELAY-OVERDUE"


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip().replace(" ", "T")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _as_text(value: Any) -> str:
    return "" if value is None else str(value)


def _mask(value: Any, *, keep_head: int = 1, keep_tail: int = 1) -> str | None:
    """脱敏：保留头尾，中间用 *** 替代；空值返回 None。"""
    text = _as_text(value)
    if not text:
        return None
    if len(text) <= keep_head + keep_tail:
        return "***"
    return text[:keep_head] + "***" + text[-keep_tail:]


def evaluate_delay_detailed(
    rows: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    p0_hours: float = 24,
    p1_hours: float = 2,
    p2_hours: float = 0,
) -> RuleEvaluation:
    """对延时行逐条判定超时分级，返回命中、覆盖与数据质量跳过。"""
    params = {"p0Hours": p0_hours, "p1Hours": p1_hours, "p2Hours": p2_hours}
    evaluation = RuleEvaluation()

    for row in rows:
        planned = _parse_datetime(row.get("imData") or row.get("im_data"))
        if planned is None:
            # 数据质量：计划到货时间缺失 → 不算“已评估且正常”
            evaluation.skip(RULE_ID)
            continue
        if planned.tzinfo is None:
            planned = planned.replace(tzinfo=ctx.now.tzinfo)
        age_hours = (ctx.now - planned).total_seconds() / 3600
        if age_hours < 0:
            # 未来时间：数据质量跳过，不判异常
            evaluation.skip(RULE_ID)
            continue

        notice = _as_text(row.get("noticeId") or row.get("notice_id"))
        object_id = notice
        warehouse = ctx.warehouse
        dimension = {"warehouse": warehouse, "supplier": _as_text(row.get("supName"))}
        evidence = {
            "noticeId": notice or None,
            "supplierName": _as_text(row.get("supName")) or None,
            "plannedArrivalAt": planned.isoformat(),
            "delayHours": round(age_hours, 2),
            "driver": _mask(row.get("imCarDri")),
            "driverPhone": _mask(row.get("imCarMobile"), keep_head=3, keep_tail=4),
            "vehicleNo": _mask(row.get("imCarNo"), keep_head=2, keep_tail=2),
            "status": _as_text(row.get("imSta")) or None,
            "sourceEndpoint": ENDPOINT,
            "observedAt": ctx.now.isoformat(),
        }

        if age_hours > p0_hours:
            severity = "P0"
        elif age_hours > p1_hours:
            severity = "P1"
        else:
            severity = "P2"

        if age_hours <= p2_hours:
            # 尚未超过 P2 起点（默认 0）：不算延时 → 条件确定为假
            evaluation.evaluated_keys.append(
                EvaluatedKey(
                    rule_id=RULE_ID,
                    object_type=OBJECT_TYPE,
                    object_id=object_id,
                    dimension_hash=dimension_hash(dimension),
                )
            )
            continue

        evaluation.findings.append(
            Finding(
                rule_id=RULE_ID,
                rule_version=RULE_VERSION,
                severity=severity,
                object_type=OBJECT_TYPE,
                object_id=object_id,
                dimension=dimension,
                evidence=evidence,
                suggested_actions=ACTIONS,
                rule_params=params,
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


def evaluate_delay(
    rows: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    p0_hours: float = 24,
    p1_hours: float = 2,
    p2_hours: float = 0,
) -> list[Finding]:
    """兼容入口：只返回命中列表（覆盖信息见 evaluate_delay_detailed）。"""
    return evaluate_delay_detailed(
        rows, ctx, p0_hours=p0_hours, p1_hours=p1_hours, p2_hours=p2_hours
    ).findings
