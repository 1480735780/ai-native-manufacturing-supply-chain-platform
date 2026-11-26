"""出货异常规则（v0.2.1）：OUTBOUND-EXCEPTION。

数据源是 Java 巡检端点（wm_to_down_goods）；巡检 SQL 返回全部下架候选行，
本规则用 Decimal 对 goods_qua/goods_quaok 做精确比较：
- 数值确实不相等 → 命中；数值相等（如 10/10.0）→ 正常未命中，不当质量跳过；
- 无法解析 / 非有限（NaN/Infinity）→ 数据质量跳过，不误报、也不静默当正常；
  且为对象级跳过：只冻结坏行自己的对象，其它正常对象照常自动关闭/降级。

create_date 是下架单创建时间，不是异常发生时间；禁写"异常持续 24 小时"，
也不声称"未闭环"（接口无闭环状态）。分级基于可配置 p0_hours（默认 24h）：
- now - create_date > p0_hours 小时 → P0，文案用 p0_hours 表述；
- 未超过 p0_hours → P1，文案只陈述"下架数量与复核数量不一致，待复核"；
- 不设 P2。文案不得写死"24 小时/当日"，以免与配置值或跨日边界矛盾。

同一对象（bin_id_to + goods_id + cus_code）的多行先聚合，只保留最高级别的
一条，避免同指纹后行覆盖前行把 P0 降成 P1。建议动作：CHECK_BATCH、NOTIFY_QC。
时间缺失/解析失败/未来时间 → 数据质量跳过，不误报、不自动关闭。
质量跳过均为对象级（quality_skipped_objects）：坏行按 bin_id_to|goods_id|cus_code
只冻结自己；规则级 data_quality_skipped 仅留给整批不可信的情形（审计 m01655）。
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.scan.rules.base import (
    EvaluatedKey,
    Finding,
    RuleContext,
    RuleEvaluation,
    dimension_hash,
)

RULE_VERSION = "v0.2.1"
ENDPOINT = "/daycheck/yi-chang/get-yichang-down-page"
OBJECT_TYPE = "outbound_exception"
ACTIONS = ("CHECK_BATCH", "NOTIFY_QC")
RULE_ID = "OUTBOUND-EXCEPTION"


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


def _parse_decimal(value: Any) -> Decimal | None:
    """精确解析数量：必须是有限十进制数，NaN/Infinity/空/布尔一律视为非法。"""
    if value is None or value == "" or isinstance(value, bool):
        return None
    if isinstance(value, float):
        # float 先转字符串再进 Decimal，避免二进制浮点尾数污染；非有限值直接拒绝。
        if value != value or value in (float("inf"), float("-inf")):
            return None
        value = repr(value)
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _p0_description(p0_hours: float) -> str:
    hours = int(p0_hours) if float(p0_hours).is_integer() else p0_hours
    return f"下架后超过 {hours} 小时仍未处理"


P1_DESCRIPTION = "下架数量与复核数量不一致，待复核"


def evaluate_outbound_detailed(
    rows: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    p0_hours: float = 24,
) -> RuleEvaluation:
    """对出货异常行按对象聚合判定老化分级，返回命中与数据质量跳过。

    坏行（日期缺失/未来/数量非法）登记对象级 quality_skipped_objects：仅冻结该对象
    的自动关闭与降级；其它对象正常参与判定，避免单行脏数据冻结整条规则（m01655）。
    """
    params = {"p0Hours": p0_hours}
    evaluation = RuleEvaluation()
    # object_id → (severity_rank, created, evidence, dimension)
    aggregated: dict[str, tuple[int, datetime, dict[str, Any], dict[str, Any]]] = {}
    p0_description = _p0_description(p0_hours)

    for row in rows:
        # 先算 object_id（与 findings 同一个 bin_id_to|goods_id|cus_code 键）：
        # 坏行也要能登记对象级质量跳过，不能因为日期/数量非法就丢掉对象身份。
        bin_to = _as_text(row.get("bin_id_to"))
        goods = _as_text(row.get("goods_id"))
        cus = _as_text(row.get("cus_code"))
        object_id = "|".join((bin_to, goods, cus)) or "unknown"

        created = _parse_datetime(row.get("create_date") or row.get("createDate"))
        if created is None:
            # 单行的日期缺失/不可解析只冻结该对象的告警生命周期，不拖累同规则其它对象。
            evaluation.skip_object(RULE_ID, object_id)
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=ctx.now.tzinfo)
        age_hours = (ctx.now - created).total_seconds() / 3600
        if age_hours < 0:
            # 未来时间：单对象数据质量跳过，不判异常。
            evaluation.skip_object(RULE_ID, object_id)
            continue

        down_quantity = _parse_decimal(row.get("goods_qua"))
        review_quantity = _parse_decimal(row.get("goods_quaok"))
        if down_quantity is None or review_quantity is None:
            # 无法解析或非有限：单对象数据质量跳过（上游 SQL 保留此类行，不静默判异常），
            # 不用整条规则级 skip 冻结其它正常对象的自动关闭/降级（审计 m01655）。
            evaluation.skip_object(RULE_ID, object_id)
            continue
        if down_quantity == review_quantity:
            # 数值相等（10 与 10.0、高精度相等）是正常未命中，不是数据质量问题；
            # 不写 skip，避免无谓禁用整条规则的自动关闭。
            continue

        dimension = {"warehouse": ctx.warehouse, "customer": cus}
        severity = "P0" if age_hours > p0_hours else "P1"
        evidence = {
            "description": p0_description if severity == "P0" else P1_DESCRIPTION,
            "downOrderId": _as_text(row.get("id") or row.get("rowId")) or None,
            "goodsId": goods or None,
            "goodsName": _as_text(row.get("shp_ming_cheng")) or None,
            "customerName": _as_text(row.get("zhong_wen_qch")) or None,
            "locationCode": bin_to or None,
            "downQuantity": _as_text(row.get("goods_qua")) or None,
            "reviewQuantity": _as_text(row.get("goods_quaok")) or None,
            "downCreatedAt": created.isoformat(),
            "ageHours": round(age_hours, 2),
            "sourceRowKey": "wm_to_down_goods:rowId="
            + _as_text(row.get("rowId") or row.get("row_id")),
            "sourceEndpoint": ENDPOINT,
            "observedAt": ctx.now.isoformat(),
        }
        # 同对象保留最高级别；同级别保留最早的下架单（更值得先处理）。
        candidate = (3 if severity == "P0" else 2, created, evidence, dimension)
        previous = aggregated.get(object_id)
        if previous is None or candidate[0] > previous[0] or (
            candidate[0] == previous[0] and candidate[1] < previous[1]
        ):
            aggregated[object_id] = candidate

    for object_id, (_rank, _created, evidence, dimension) in aggregated.items():
        severity = "P0" if evidence["description"] == p0_description else "P1"
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


def evaluate_outbound(
    rows: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    p0_hours: float = 24,
) -> list[Finding]:
    """兼容入口：只返回命中列表（覆盖信息见 evaluate_outbound_detailed）。"""
    return evaluate_outbound_detailed(rows, ctx, p0_hours=p0_hours).findings
