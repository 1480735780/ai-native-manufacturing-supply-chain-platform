"""进入 LLM 前的裁剪与脱敏。

规则（实施方案 §7.4）：
- 每个工具最多保留前 20 行；
- 序列化后不超过 4000 字符；
- 去掉体积、面积等与回答无关的字段；
- DAYCHECK-DELAY 的手机号与司机姓名脱敏；
- 完整结果不落库、不写日志，因此这里只产出可交给模型的裁剪副本。
"""

from __future__ import annotations

import json
from typing import Any

from app.tools.registry import TOOL_DAYCHECK_DELAY

MAX_ROWS_FOR_LLM = 20
MAX_CHARS_FOR_LLM = 4000

# 与回答无关的字段（审计字段、体积面积、作业次序等）
DROP_FIELDS: dict[str, frozenset[str]] = {
    "STOCK-QUERY": frozenset(
        {
            "createDate",
            "createName",
            "createBy",
            "quHuoCiXu",
            "shangJiaCiXu",
            "tiJiCm",
            "tiJiDanWei",
            "zhongLiangDanWei",
            "mianJiDanWei",
            "zuiDaTiJi",
            "zuiDaMianJi",
        }
    ),
    "EXP-WARN-QUERY": frozenset({"id", "quHuoCiXu", "shangJiaCiXu", "guoqibili"}),
    "DAYCHECK-NOUP": frozenset({"create_date"}),
    "DAYCHECK-DELAY": frozenset({"createName", "createDate", "noticeId"}),
}

MOBILE_FIELDS = frozenset({"imCarMobile"})
DRIVER_FIELDS = frozenset({"imCarDri"})


def mask_mobile(value: Any) -> Any:
    """手机号脱敏：保留前 3 后 4，例如 138****5678。"""
    if not isinstance(value, str) or not value:
        return value
    if len(value) <= 7:
        return "****"
    return f"{value[:3]}****{value[-4:]}"


def mask_driver(value: Any) -> Any:
    """司机姓名脱敏：保留姓氏，例如 王*。"""
    if not isinstance(value, str) or not value:
        return value
    return f"{value[0]}*"


def sanitize_rows(tool: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """去掉无关字段并对敏感字段脱敏。"""
    drop = DROP_FIELDS.get(tool, frozenset())
    sanitized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        new_row: dict[str, Any] = {}
        for key, value in row.items():
            if key in drop:
                continue
            if tool == TOOL_DAYCHECK_DELAY and key in MOBILE_FIELDS:
                new_row[key] = mask_mobile(value)
            elif tool == TOOL_DAYCHECK_DELAY and key in DRIVER_FIELDS:
                new_row[key] = mask_driver(value)
            else:
                new_row[key] = value
        sanitized.append(new_row)
    return sanitized


def build_llm_payload(
    tool: str, rows: list[dict[str, Any]], total: int
) -> dict[str, Any]:
    """生成交给 LLM 的裁剪结果。

    返回 rows（已脱敏、最多 20 行）、total、truncated 标记与序列化文本（≤4000 字符）。
    """
    sanitized = sanitize_rows(tool, rows)
    kept = sanitized[:MAX_ROWS_FOR_LLM]
    text = json.dumps(kept, ensure_ascii=False, default=str)
    truncated = len(sanitized) > len(kept)
    if len(text) > MAX_CHARS_FOR_LLM:
        text = text[:MAX_CHARS_FOR_LLM] + "…(truncated)"
        truncated = True
    return {
        "rows": kept,
        "total": total,
        "truncated": truncated,
        "text": text,
    }
