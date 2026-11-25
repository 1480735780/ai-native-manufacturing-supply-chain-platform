"""效期规则（v0.2.0）：EXP-EXPIRED / EXP-NEAR / EXP-WATCH。

判定完全确定性；LLM 不参与“是否存在/级别”。字段来自
`GET /stock/expiry-warning/query-all` 的 `data.rows`：
resDate、guoqibili、bzhiQi、cusCode、goodsId、goodsProData、dqr、
shpMingCheng、zhongWenQch、kuWeiBianMa、binId、id。

阶段5 起，规则除了返回 findings，还要返回“评估覆盖”（评估过但未命中的对象）
与“数据质量跳过”（该行数据不足以判定条件，本次禁止该规则自动关闭）。
"""

from __future__ import annotations

from typing import Any

from app.scan.rules.base import (
    EvaluatedKey,
    Finding,
    RuleContext,
    RuleEvaluation,
    dimension_hash,
)

RULE_VERSION = "v0.2.0"
ENDPOINT = "/stock/expiry-warning/query-all"

# 维度/对象类型
OBJECT_TYPE = "stock_batch"
ACTIONS_ALL = ("CHECK_BATCH", "FIFO_OUTBOUND", "NOTIFY_QC")

RULE_EXPIRED = "EXP-EXPIRED"
RULE_NEAR = "EXP-NEAR"
RULE_WATCH = "EXP-WATCH"


def _as_float(value: Any) -> float | None:
    """把可能是字符串/None 的数值字段转成 float，失败返回 None。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_text(value: Any) -> str:
    return "" if value is None else str(value)


def evaluate_expiry_detailed(
    rows: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    expired_days: int = 0,
    near_days: int = 7,
    near_ratio: float = 1 / 3,
    watch_days: int = 30,
) -> RuleEvaluation:
    """对效期行逐条判定，返回命中、覆盖与数据质量跳过。

    - res_date < expired_days（默认 0）→ EXP-EXPIRED / P0
    - 0 <= res_date <= near_days 或 临期比例 <= near_ratio → EXP-NEAR / P1
    - near_days < res_date <= watch_days → EXP-WATCH / P2
    - guoqibili 解析失败或 bzhiQi 为空/0 时回退 resDate，并置 rule_degraded=true
    - resDate 缺失/非法 → 数据质量跳过，不判异常

    覆盖语义：某规则对某对象的条件被“确定为假”时才记覆盖；条件不可判定
    （降级行缺少临期比例）时既不记覆盖，也不允许该规则本次自动关闭。
    """
    params = {
        "expired_days": expired_days,
        "near_days": near_days,
        "near_ratio": round(near_ratio, 4),
        "watch_days": watch_days,
    }
    evaluation = RuleEvaluation()

    for row in rows:
        res_date = _as_float(row.get("resDate"))
        if res_date is None:
            # 数据质量：剩余天数缺失，跳过，不判异常
            evaluation.skip(RULE_EXPIRED)
            evaluation.skip(RULE_NEAR)
            evaluation.skip(RULE_WATCH)
            continue

        warehouse = ctx.warehouse
        cus_code = _as_text(row.get("cusCode"))
        goods_id = _as_text(row.get("goodsId"))
        goods_date = _as_text(row.get("goodsProData"))
        object_id = "|".join((warehouse, cus_code, goods_id, goods_date))
        dimension = {"warehouse": warehouse, "customer": cus_code}
        key_hash = dimension_hash(dimension)

        evidence = {
            "goodsCode": goods_id,
            "goodsName": _as_text(row.get("shpMingCheng")),
            "customerName": _as_text(row.get("zhongWenQch")),
            "resDate": res_date,
            "guoqibili": _as_text(row.get("guoqibili")) or None,
            "shelfLifeDays": _as_text(row.get("bzhiQi")) or None,
            "expiryDate": _as_text(row.get("dqr")) or None,
            "batchDate": goods_date or None,
            "locationCode": _as_text(row.get("kuWeiBianMa")) or None,
            "sourceRowKey": "mv_stock_yj:id=" + _as_text(row.get("id")),
            "sourceEndpoint": ENDPOINT,
            "observedAt": ctx.now.isoformat(),
        }

        raw_ratio = _as_float(row.get("guoqibili"))
        shelf_life = _as_float(row.get("bzhiQi"))
        degraded = raw_ratio is None or shelf_life is None or shelf_life == 0
        ratio = raw_ratio if raw_ratio is not None else 1.0
        near_by_days = 0 <= res_date <= near_days

        # ---- 命中判定（与既有实现逐字一致） ----
        if res_date < expired_days:
            rule_id, severity = RULE_EXPIRED, "P0"
            actions = ("CHECK_BATCH", "FIFO_OUTBOUND")
            hit_degraded = False
        else:
            if near_by_days or (not degraded and ratio <= near_ratio):
                rule_id, severity = RULE_NEAR, "P1"
            elif res_date <= watch_days:
                rule_id, severity = RULE_WATCH, "P2"
            else:
                rule_id = None  # type: ignore[assignment]
            actions = ACTIONS_ALL
            hit_degraded = degraded

        if rule_id is not None:
            if rule_id != RULE_EXPIRED:
                evidence["ruleDegraded"] = hit_degraded
            evaluation.findings.append(
                Finding(
                    rule_id=rule_id,
                    rule_version=RULE_VERSION,
                    severity=severity,
                    object_type=OBJECT_TYPE,
                    object_id=object_id,
                    dimension=dimension,
                    evidence=evidence,
                    suggested_actions=actions,
                    rule_params=params,
                    rule_degraded=hit_degraded if rule_id != RULE_EXPIRED else False,
                )
            )

        # ---- 覆盖判定（保守：条件被确定为假才算“已评估且正常”） ----
        if res_date < expired_days:
            # 已过期：原始实现不再评估 near/watch，两者按“未命中”处理
            states = {RULE_EXPIRED: "hit", RULE_NEAR: "miss", RULE_WATCH: "miss"}
        else:
            if near_by_days:
                near_state = "hit"
                watch_state = "miss"
            elif degraded:
                # 临期比例不可用 → near/watch 条件不可判定
                near_state = "unknown"
                watch_state = "unknown"
            else:
                near_state = "hit" if ratio <= near_ratio else "miss"
                watch_state = (
                    "hit" if (near_state == "miss" and res_date <= watch_days) else "miss"
                )
            states = {RULE_EXPIRED: "miss", RULE_NEAR: near_state, RULE_WATCH: watch_state}

        for state_rule_id, state in states.items():
            if state == "unknown":
                evaluation.skip(state_rule_id)
                continue
            evaluation.evaluated_keys.append(
                EvaluatedKey(
                    rule_id=state_rule_id,
                    object_type=OBJECT_TYPE,
                    object_id=object_id,
                    dimension_hash=key_hash,
                )
            )

    return evaluation


def evaluate_expiry(
    rows: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    expired_days: int = 0,
    near_days: int = 7,
    near_ratio: float = 1 / 3,
    watch_days: int = 30,
) -> list[Finding]:
    """兼容入口：只返回命中列表（覆盖信息见 evaluate_expiry_detailed）。"""
    return evaluate_expiry_detailed(
        rows,
        ctx,
        expired_days=expired_days,
        near_days=near_days,
        near_ratio=near_ratio,
        watch_days=watch_days,
    ).findings
