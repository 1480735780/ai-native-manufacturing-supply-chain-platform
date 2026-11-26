"""温度超限规则（v0.2.1）：TEMP-EXCURSION。

数据源是人工录入/Excel 导入，不是传感器实时采集（方案 §8.3.2）：
- 用 wenduCjsj（采集时间）判断读数时间；create_date 仅审计，不参与超限判断；
- wenduCjsj 明显早于 create_date（倒填）、wenduCjsj 晚于 now（未来读数）、
  温度值非有限（NaN/Infinity）→ 数据质量标记，不判异常；
- wenduDd 必须映射到 YAML 地点词表；未匹配地点产生一条 P2 元告警，绝不自动映射；
- 阈值按 location -> {min_c, max_c}；录入间隔优先按地点 expected_interval_hours，
  缺省回退全局 expectedIntervalHours；max_silence_hours = 2 × interval。

分级（同一 location 内按 wenduCjsj 排序，只考察最近 max_silence_hours 窗口）：
- 连续 consecutive_points 个录入点超限（相邻间隔 ≤ interval），且段内
  （最大超限 ≥ p0_abs_c 或 超限跨度 ≥ p0_span_hours）→ P0；
- 窗口内单点超限 ≥ p0_single_point_abs_c → P0；其余单点超限 → P1；
- 窗口内无有效录入 → P2（为每个已配置地点显式生成，防止静默清空导致误自动关闭）。

超限（kind=excursion）与无录入（kind=no_entry）使用不同 dimension，指纹不会互相覆盖。
数据质量跳过按地点 + 当前评估窗统计：远古脏行只记一次质量跳过，不会永久抑制
当前无录入 P2；P0 证据永远取触发 P0 的最差超限，不用较小值代替。
质量跳过一律登记为对象级（quality_skipped_objects，键为 warehouse|location）：
单个地点的坏行/未知地点/地点阈值非法只冻结该地点对象，不拖累同规则其它地点（m01655）。
不做商品级温度属性 join，混合温区库房记为已知限制。
"""

from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Any

from app.scan.rules.base import (
    EvaluatedKey,
    Finding,
    RuleContext,
    RuleEvaluation,
    dimension_hash,
)

RULE_VERSION = "v0.2.1"
ENDPOINT = "/daycheck/temperature/query"
OBJECT_TYPE = "temperature_location"
ACTIONS = ("NOTIFY_QC", "CHECK_BATCH")
RULE_ID = "TEMP-EXCURSION"
KNOWN_LIMITATION = "不做商品级温度属性 join；混合温区库房按地点阈值判定"


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


def _parse_number(value: Any) -> float | None:
    """解析有限数值：NaN / Infinity / 空 / 布尔一律视为非法。"""
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _normalize_location(raw: Any, locations: list[dict[str, Any]]) -> dict[str, Any] | None:
    """把 wenduDd 按地点词表（name + aliases）归一化；未匹配返回 None。"""
    text = _as_text(raw).strip()
    if not text:
        return None
    for loc in locations:
        names = [loc.get("name")] + list(loc.get("aliases") or [])
        if any(_as_text(n).strip() == text for n in names if n is not None):
            return loc
    return None


def _interval_hours(loc: dict[str, Any], default: float) -> float:
    """优先使用地点自己的录入间隔；缺失/非法时回退全局值。"""
    value = _parse_number(loc.get("expected_interval_hours"))
    if value is None or value <= 0:
        return default
    return value


def evaluate_temperature_detailed(
    rows: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    locations: list[dict[str, Any]] | None = None,
    expected_interval_hours: float = 8,
    consecutive_points: int = 2,
    p0_abs_c: float = 2.0,
    p0_span_hours: float = 4.0,
    p0_single_point_abs_c: float = 5.0,
) -> RuleEvaluation:
    """对温度行按地点分组判定超限/静默，返回命中、覆盖与数据质量跳过。

    坏行（无效读数/未来读数/倒填/地点阈值非法/未知地点）登记对象级
    quality_skipped_objects（warehouse|location，未知地点为 warehouse|未知地点:<raw>），
    只冻结该对象的自动关闭与降级；同规则其它正常地点不受影响（审计 m01655）。
    dimension.kind 的 excursion/no_entry/unknown_location 划分保持不变。
    """
    locations = locations or []
    params = {
        "expectedIntervalHours": expected_interval_hours,
        "consecutivePoints": consecutive_points,
        "p0AbsC": p0_abs_c,
        "p0SpanHours": p0_span_hours,
        "p0SinglePointAbsC": p0_single_point_abs_c,
        "knownLimitation": KNOWN_LIMITATION,
    }
    evaluation = RuleEvaluation()

    def object_id_for(location_name: str) -> str:
        return "|".join((ctx.warehouse, location_name))

    def dimension_for(location_name: str, kind: str) -> dict[str, Any]:
        # kind 进入 dimension：超限与无录入不再因相同 (warehouse, location) 指纹碰撞。
        return {"warehouse": ctx.warehouse, "location": location_name, "kind": kind}

    def add_key(dimension: dict[str, Any]) -> None:
        evaluation.evaluated_keys.append(
            EvaluatedKey(
                rule_id=RULE_ID,
                object_type=OBJECT_TYPE,
                object_id=object_id_for(_as_text(dimension.get("location"))),
                dimension_hash=dimension_hash(dimension),
            )
        )

    def quality_marker(row: dict[str, Any], reading_at: datetime | None) -> datetime:
        """给质量跳过行打时间标记：优先读数时间，其次录入时间，最后用本次 now。"""
        if reading_at is not None:
            return reading_at
        created = _parse_datetime(row.get("createDate") or row.get("create_date"))
        if created is not None:
            return created if created.tzinfo else created.replace(tzinfo=ctx.now.tzinfo)
        return ctx.now

    def mark_quality(info: dict[str, Any], marker: datetime, interval_hours: float) -> bool:
        """登记一次质量跳过；只有落在当前静默窗内才返回 True（需要冻结该对象）。

        远古脏行不应永久冻结同一地点的告警生命周期（审计 m01902）：一行 100 小时前的
        NaN 若一直登记对象级跳过，该地点旧 P0 永远无法关闭。因此这里按当前
        max_silence 窗（2 × 地点录入间隔）判定是否仍算“当前数据质量问题”。
        """
        info["quality_skipped_at"].append(marker)
        age_hours = (ctx.now - marker).total_seconds() / 3600
        return age_hours <= 2 * interval_hours

    unknown_locations: dict[str, int] = {}
    # 每个归一化地点都保留容器：即使本次没有任何有效行，也要显式判断“无录入”。
    grouped: dict[str, dict[str, Any]] = {}

    for row in rows:
        loc = _normalize_location(row.get("wenduDd"), locations)
        if loc is None:
            raw = _as_text(row.get("wenduDd")) or "<空>"
            unknown_locations[raw] = unknown_locations.get(raw, 0) + 1
            continue
        name = _as_text(loc.get("name"))
        interval = _interval_hours(loc, expected_interval_hours)
        info = grouped.setdefault(
            name, {"points": [], "quality_skipped_at": []}
        )
        reading_at = _parse_datetime(row.get("wenduCjsj"))
        if reading_at is not None and reading_at.tzinfo is None:
            reading_at = reading_at.replace(tzinfo=ctx.now.tzinfo)
        value = _parse_number(row.get("wenduZhi"))
        if reading_at is None or value is None:
            # 坏行只冻结自己所在地点：同批其它地点的告警生命周期不受影响（m01655）；
            # 且只有落在当前窗内才冻结，远古脏行不再永久冻结（m01902）。
            if mark_quality(info, quality_marker(row, reading_at), interval):
                evaluation.skip_object(RULE_ID, object_id_for(name))
            continue
        # 未来读数：单地点数据质量跳过，不判异常，也不参与连续性/无录入判断。
        if reading_at > ctx.now:
            if mark_quality(info, reading_at, interval):
                evaluation.skip_object(RULE_ID, object_id_for(name))
            continue
        created = _parse_datetime(row.get("createDate") or row.get("create_date"))
        if created is not None and created.tzinfo is None:
            created = created.replace(tzinfo=ctx.now.tzinfo)
        # 倒填：采集时间明显早于录入时间 → 数据质量标记，不判异常。
        if created is not None and (created - reading_at).total_seconds() / 3600 > interval:
            # 倒填行只冻结该地点，不拖累其它地点；同样只在当前窗内冻结。
            if mark_quality(info, reading_at, interval):
                evaluation.skip_object(RULE_ID, object_id_for(name))
            continue
        info["points"].append(
            {
                "loc": loc,
                "reading_at": reading_at,
                "value": value,
                "created": created,
                "row": row,
                "interval_hours": interval,
            }
        )

    # 未匹配地点：一条 P2 元告警，不自动映射，并禁止本次自动关闭。
    for raw, count in unknown_locations.items():
        name = "未知地点:" + raw
        dimension = dimension_for(name, "unknown_location")
        evaluation.findings.append(
            Finding(
                rule_id=RULE_ID,
                rule_version=RULE_VERSION,
                severity="P2",
                object_type=OBJECT_TYPE,
                object_id=object_id_for(name),
                dimension=dimension,
                evidence={
                    "reason": "温度地点不在词表中，未自动映射",
                    "rawLocation": raw,
                    "rowCount": count,
                    "sourceEndpoint": ENDPOINT,
                    "observedAt": ctx.now.isoformat(),
                },
                suggested_actions=("NOTIFY_QC",),
                rule_params=params,
            )
        )
        add_key(dimension)
        # 未知地点只冻结该 raw location 对应的对象，其它已知地点照常自动关闭。
        evaluation.skip_object(RULE_ID, object_id_for(name))

    # 遍历“已配置地点”而不是“实际出现的地点”：整批缺失也要生成无录入结果。
    for loc in locations:
        location_name = _as_text(loc.get("name")) or "<未命名地点>"
        interval = _interval_hours(loc, expected_interval_hours)
        max_silence_hours = 2 * interval
        info = grouped.get(location_name, {"points": [], "quality_skipped_at": []})
        dimension_excursion = dimension_for(location_name, "excursion")
        dimension_no_entry = dimension_for(location_name, "no_entry")
        min_c = _parse_number(loc.get("min_c"))
        max_c = _parse_number(loc.get("max_c"))

        if min_c is None or max_c is None or min_c > max_c:
            # 地点阈值配置不合法：该地点数据质量跳过，不判异常、也不误报无录入。
            # 阈值只作用于本地点，因此登记对象级跳过而非整条规则（m01655）。
            evaluation.skip_object(RULE_ID, object_id_for(location_name))
            add_key(dimension_excursion)
            add_key(dimension_no_entry)
            continue

        def exceed_of(value: float) -> float:
            return max(min_c - value, value - max_c, 0.0)

        # 只考察时间窗内的读数：历史超限不会永久复发。
        points = sorted(
            (
                p for p in info["points"]
                if (ctx.now - p["reading_at"]).total_seconds() / 3600 <= max_silence_hours
            ),
            key=lambda p: p["reading_at"],
        )
        # 质量跳过也按当前窗统计：远古脏行不再永久抑制无录入 P2。
        recent_quality_skip = any(
            (ctx.now - marker).total_seconds() / 3600 <= max_silence_hours
            for marker in info["quality_skipped_at"]
        )

        if not points:
            if not recent_quality_skip:
                # 完全无有效录入（含整批缺失或全部过期）→ P2。
                stale = [p["reading_at"] for p in info["points"]]
                last_reading = max(stale) if stale else None
                silence_hours = (
                    (ctx.now - last_reading).total_seconds() / 3600 if last_reading else None
                )
                evaluation.findings.append(
                    Finding(
                        rule_id=RULE_ID,
                        rule_version=RULE_VERSION,
                        severity="P2",
                        object_type=OBJECT_TYPE,
                        object_id=object_id_for(location_name),
                        dimension=dimension_no_entry,
                        evidence={
                            "reason": "超过预期录入间隔无新温度录入",
                            "location": location_name,
                            "lastReadingAt": last_reading.isoformat() if last_reading else None,
                            "silenceHours": round(silence_hours, 2) if silence_hours is not None else None,
                            "maxSilenceHours": max_silence_hours,
                            "effectiveIntervalHours": interval,
                            "sourceEndpoint": ENDPOINT,
                            "observedAt": ctx.now.isoformat(),
                            "knownLimitation": KNOWN_LIMITATION,
                        },
                        suggested_actions=("NOTIFY_QC",),
                        rule_params=params,
                    )
                )
            else:
                # 当前窗内该地点有数据质量问题：不把问题伪装成静默，只冻结该地点对象的自动关闭。
                evaluation.skip_object(RULE_ID, object_id_for(location_name))
            add_key(dimension_no_entry)
            add_key(dimension_excursion)
            continue

        evaluated = [(p, exceed_of(p["value"])) for p in points]
        worst = max(evaluated, key=lambda pair: pair[1])
        single_point_worst = max(
            ((p, exceed) for p, exceed in evaluated if exceed >= p0_single_point_abs_c),
            key=lambda pair: pair[1],
            default=None,
        )

        # 连续段按相邻采集间隔判定；段内 worst/跨度独立计算，不用全局历史最差值。
        segments: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for point, exceed in evaluated:
            if exceed <= 0:
                if current is not None:
                    segments.append(current)
                    current = None
                continue
            if current is not None:
                gap_hours = (point["reading_at"] - current["end"]).total_seconds() / 3600
                if gap_hours > interval:
                    segments.append(current)
                    current = None
            if current is None:
                current = {
                    "start": point["reading_at"],
                    "end": point["reading_at"],
                    "count": 1,
                    "worst": (point, exceed),
                }
            else:
                current["end"] = point["reading_at"]
                current["count"] += 1
                if exceed > current["worst"][1]:
                    current["worst"] = (point, exceed)
        if current is not None:
            segments.append(current)

        qualifying = [
            seg for seg in segments
            if seg["count"] >= consecutive_points
            and (
                seg["worst"][1] >= p0_abs_c
                or (seg["end"] - seg["start"]).total_seconds() / 3600 >= p0_span_hours
            )
        ]
        if single_point_worst is not None or qualifying:
            severity: str | None = "P0"
        elif any(exceed > 0 for _, exceed in evaluated):
            severity = "P1"
        else:
            severity = None

        if severity is not None:
            # P0 证据取触发 P0 的最差超限：单点最差与合格连续段最差之间取最大，
            # 避免较小值（如 2℃）掩盖真实 8℃ 单点超限。
            candidates = list(qualifying)
            if single_point_worst is not None:
                candidates.append({"worst": single_point_worst, "start": None, "end": None})
            representative = max(candidates, key=lambda seg: seg["worst"][1]) if candidates else None
            worst_point, worst_exceed = representative["worst"] if representative else worst
            span_hours = (
                (representative["end"] - representative["start"]).total_seconds() / 3600
                if representative and representative.get("start") is not None
                else 0.0
            )
            max_consecutive = max((seg["count"] for seg in segments), default=0)
            evidence = {
                "reason": "温度超出地点阈值",
                "location": location_name,
                "temperatureC": worst_point["value"],
                "minC": min_c,
                "maxC": max_c,
                "maxExceedC": round(worst_exceed, 2),
                "readingAt": worst_point["reading_at"].isoformat(),
                "enteredAt": (
                    worst_point["created"].isoformat() if worst_point["created"] is not None else None
                ),
                "consecutiveExceedPoints": max_consecutive,
                "thresholdSpanHours": round(span_hours, 2),
                "effectiveIntervalHours": interval,
                "sourceEndpoint": ENDPOINT,
                "observedAt": ctx.now.isoformat(),
                "knownLimitation": KNOWN_LIMITATION,
            }
            evaluation.findings.append(
                Finding(
                    rule_id=RULE_ID,
                    rule_version=RULE_VERSION,
                    severity=severity,
                    object_type=OBJECT_TYPE,
                    object_id=object_id_for(location_name),
                    dimension=dimension_excursion,
                    evidence=evidence,
                    suggested_actions=ACTIONS,
                    rule_params=params,
                )
            )
        add_key(dimension_excursion)
        add_key(dimension_no_entry)

    return evaluation


def evaluate_temperature(
    rows: list[dict[str, Any]],
    ctx: RuleContext,
    *,
    locations: list[dict[str, Any]] | None = None,
    expected_interval_hours: float = 8,
    consecutive_points: int = 2,
    p0_abs_c: float = 2.0,
    p0_span_hours: float = 4.0,
    p0_single_point_abs_c: float = 5.0,
) -> list[Finding]:
    """兼容入口：只返回命中列表（覆盖信息见 evaluate_temperature_detailed）。"""
    return evaluate_temperature_detailed(
        rows,
        ctx,
        locations=locations,
        expected_interval_hours=expected_interval_hours,
        consecutive_points=consecutive_points,
        p0_abs_c=p0_abs_c,
        p0_span_hours=p0_span_hours,
        p0_single_point_abs_c=p0_single_point_abs_c,
    ).findings
