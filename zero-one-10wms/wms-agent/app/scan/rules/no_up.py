"""收货未上架规则（v0.2.0）：NOUP-OVERDUE。

条件（方案 §8.2.3）：now - create_date 滞留时长分级——
- > 8h → P0
- 4–8h → P1
- 2–4h → P2
- < 2h → 不判异常（正常处理中）

create_date 是收货日期（LocalDateTime），解析失败或未来时间为数据质量
问题：跳过并置 rule_degraded（不产生误报）。objectId = notice+goods+pallet，
不含储位（移库不产生新告警）。建议动作：MOVE_TO_BIN、CONTACT_CUSTOMER。

阶段5 起同时返回评估覆盖与数据质量跳过：时间缺失/未来时间的行不算
“已评估且正常”，NOUP-OVERDUE 本次禁止自动关闭。
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
ENDPOINT = "/daycheck/no-up/get-no-up-goods"
OBJECT_TYPE = "no_up_goods"
ACTIONS = ("MOVE_TO_BIN", "CONTACT_CUSTOMER")
RULE_ID = "NOUP-OVERDUE"


def _parse_datetime(value: Any) -> datetime | None:
    """解析 create_date（ISO 8601 / 'yyyy-MM-dd HH:mm:ss'），失败返回 None。"""
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


def evaluate_no_up_detailed(
    rows: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    p0_hours: float = 8,
    p1_hours: float = 4,
    p2_hours: float = 2,
) -> RuleEvaluation:
    """对未上架行逐条判定滞留分级，返回命中、覆盖与数据质量跳过。"""
    params = {"p0Hours": p0_hours, "p1Hours": p1_hours, "p2Hours": p2_hours}
    evaluation = RuleEvaluation()

    for row in rows:
        created = _parse_datetime(row.get("create_date") or row.get("createDate"))
        if created is None:
            # 数据质量：时间缺失 → 不算“已评估且正常”
            evaluation.skip(RULE_ID)
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=ctx.now.tzinfo)
        age_hours = (ctx.now - created).total_seconds() / 3600
        if age_hours < 0:
            # 未来时间：数据质量跳过，不判异常
            evaluation.skip(RULE_ID)
            continue

        notice = _as_text(row.get("noticeId") or row.get("notice_id"))
        goods = _as_text(row.get("goods_id"))
        pallet = _as_text(row.get("tin_id"))
        object_id = "|".join((notice, goods, pallet))
        warehouse = ctx.warehouse
        dimension = {"warehouse": warehouse, "customer": _as_text(row.get("cus_code"))}
        evidence = {
            "noticeId": notice or None,
            "goodsId": goods or None,
            "goodsName": _as_text(row.get("shp_ming_cheng")) or None,
            "palletId": pallet or None,
            "locationCode": _as_text(row.get("bin_id")) or None,
            "receivedAt": created.isoformat(),
            "ageHours": round(age_hours, 2),
            "customerName": _as_text(row.get("zhong_wen_qch")) or None,
            "sourceRowKey": "wm_in_qm_i:rowId=" + _as_text(row.get("rowId") or row.get("row_id")),
            "sourceEndpoint": ENDPOINT,
            "observedAt": ctx.now.isoformat(),
        }

        if age_hours > p0_hours:
            severity = "P0"
        elif age_hours > p1_hours:
            severity = "P1"
        elif age_hours > p2_hours:
            severity = "P2"
        else:
            severity = None

        if severity is not None:
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

        # 条件确定为假（未超期）→ 记覆盖，允许自动关闭历史告警
        evaluation.evaluated_keys.append(
            EvaluatedKey(
                rule_id=RULE_ID,
                object_type=OBJECT_TYPE,
                object_id=object_id,
                dimension_hash=dimension_hash(dimension),
            )
        )

    return evaluation


def evaluate_no_up(
    rows: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    p0_hours: float = 8,
    p1_hours: float = 4,
    p2_hours: float = 2,
) -> list[Finding]:
    """兼容入口：只返回命中列表（覆盖信息见 evaluate_no_up_detailed）。"""
    return evaluate_no_up_detailed(
        rows, ctx, p0_hours=p0_hours, p1_hours=p1_hours, p2_hours=p2_hours
    ).findings
