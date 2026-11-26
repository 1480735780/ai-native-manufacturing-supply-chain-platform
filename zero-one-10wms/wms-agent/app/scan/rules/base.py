"""规则基础类型：Finding / RuleContext / 指纹计算。

指纹把规则版本、业务键和维度纳入哈希，规则升版后历史告警仍可解释。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class RuleContext:
    """一次规则求值的上下文。"""

    warehouse: str
    now: datetime
    rule_params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    """规则命中的一条发现（尚未去重/落库）。"""

    rule_id: str
    rule_version: str
    severity: str
    object_type: str
    object_id: str
    dimension: dict[str, Any]
    evidence: dict[str, Any]
    suggested_actions: tuple[str, ...] = ()
    rule_params: dict[str, Any] = field(default_factory=dict)
    rule_degraded: bool = False

    @property
    def fingerprint(self) -> str:
        """sha256(ruleId + ruleVersion + objectType + objectId + dimension)。"""
        raw = "|".join(
            (
                self.rule_id,
                self.rule_version,
                self.object_type,
                self.object_id,
                json.dumps(self.dimension, ensure_ascii=False, sort_keys=True),
            )
        )
        return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_alert(self) -> dict[str, Any]:
        """转成可入库的告警摘要（不含原始行）。"""
        return {
            "fingerprint": self.fingerprint,
            "ruleId": self.rule_id,
            "ruleVersion": self.rule_version,
            "ruleParams": dict(self.rule_params),
            "severity": self.severity,
            "objectType": self.object_type,
            "objectId": self.object_id,
            "dimension": dict(self.dimension),
            "evidence": dict(self.evidence),
            "suggestedActions": list(self.suggested_actions),
            "ruleDegraded": self.rule_degraded,
        }


@dataclass(frozen=True)
class EvaluatedKey:
    """一次规则求值覆盖到的对象键。

    仅记录 findings 不足以判断“条件是否消失”：必须同时记录
    “评估过但未命中”的对象，才能证明某个告警对象的异常条件已经消失。
    """

    rule_id: str
    object_type: str
    object_id: str
    dimension_hash: str

    def as_row(self) -> dict[str, Any]:
        return {
            "ruleId": self.rule_id,
            "objectType": self.object_type,
            "objectId": self.object_id,
            "dimensionHash": self.dimension_hash,
        }


@dataclass
class RuleEvaluation:
    """规则求值的四件套：命中、覆盖、规则级质量跳过、对象级质量跳过。"""

    findings: list[Finding] = field(default_factory=list)
    evaluated_keys: list[EvaluatedKey] = field(default_factory=list)
    data_quality_skipped: list[str] = field(default_factory=list)
    # 对象级质量跳过（rule_id, object_id）：仅这些对象本次禁止自动关闭/降级。
    # 与 data_quality_skipped（整条规则级，v0.2.0 既有语义）并存：
    # 边缘坏行只应冻结同一对象的告警生命周期，不应拖累同规则其它正常对象（审计 m01655）。
    quality_skipped_objects: set[tuple[str, str]] = field(default_factory=set)

    def skip(self, rule_id: str) -> None:
        """整条规则级跳过：该规则本次整体禁止自动关闭（v0.2.0 既有语义）。"""
        if rule_id not in self.data_quality_skipped:
            self.data_quality_skipped.append(rule_id)

    def skip_object(self, rule_id: str, object_id: str) -> None:
        """对象级跳过：仅该对象本次禁止自动关闭与降级，同规则其它对象不受影响。"""
        self.quality_skipped_objects.add((rule_id, object_id))


def dimension_hash(dimension: dict[str, Any]) -> str:
    """维度哈希：与告警指纹使用同一套规范化方式，保证可比较。"""
    raw = json.dumps(dimension, ensure_ascii=False, sort_keys=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class Rule(Protocol):
    """规则接口。"""

    rule_id: str
    rule_version: str

    def evaluate(self, rows: list[dict[str, Any]], ctx: RuleContext) -> list[Finding]: ...
