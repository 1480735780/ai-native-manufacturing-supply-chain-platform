"""版本化巡检配置：启动校验、canonical 快照与确定性哈希。"""

from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import ScanConfigError

KNOWN_RULE_IDS = (
    "EXP-EXPIRED",
    "EXP-NEAR",
    "EXP-WATCH",
    "NOUP-OVERDUE",
    "DELAY-OVERDUE",
    "BACKLOG-GROWTH",
    "OUTBOUND-EXCEPTION",
    "TEMP-EXCURSION",
    "SCAN-PARTIAL",
)

# 巡检类型白名单（与 app/scan/schemas.py 的 Literal 一致，这里给的是可枚举的元组）。
SUPPORTED_SCAN_TYPE_LIST: tuple[str, ...] = (
    "expiry", "no_up", "delay", "backlog", "outbound", "temperature",
)


@dataclass(frozen=True)
class ScanCron:
    """``*/N H-M * * *`` 的解析结果：每 N 分钟一槽，窗口 [hour_start, hour_end]。"""

    minute_step: int
    hour_start: int
    hour_end: int


def parse_scan_cron(expression: str) -> ScanCron:
    """解析最小调度表达式；非法表达式直接抛 ValueError（启动即拒绝）。

    只接受 ``*/N H-M * * *``：
      - N ∈ [1, 60] 且必须整除 60（保证槽位落在整点上）；
      - 0 ≤ H ≤ M ≤ 23；
      - 其余字段必须是 ``*``。
    """
    text = (expression or "").strip()
    parts = text.split()
    if len(parts) != 5:
        raise ValueError(f"调度 cron 非法: {expression}（只支持 */N H-M * * *）")
    minute_part, hour_part, day_part, month_part, day_of_week = parts
    if not minute_part.startswith("*/"):
        raise ValueError(f"调度 cron 非法: {expression}（分钟必须是 */N）")
    try:
        minute_step = int(minute_part[2:])
    except ValueError as exc:
        raise ValueError(f"调度 cron 非法: {expression}（分钟步长不是整数）") from exc
    if minute_step < 1 or minute_step > 60 or 60 % minute_step != 0:
        raise ValueError(f"调度 cron 非法: {expression}（分钟步长必须整除 60 且在 1..60）")
    if "-" not in hour_part:
        raise ValueError(f"调度 cron 非法: {expression}（小时必须是 H-M）")
    hour_text, _, minute_text = hour_part.partition("-")
    try:
        hour_start = int(hour_text)
        hour_end = int(minute_text)
    except ValueError as exc:
        raise ValueError(f"调度 cron 非法: {expression}（小时范围不是整数）") from exc
    if not (0 <= hour_start <= hour_end <= 23):
        raise ValueError(f"调度 cron 非法: {expression}（小时范围必须满足 0<=H<=M<=23）")
    if day_part != "*" or month_part != "*" or day_of_week != "*":
        raise ValueError(f"调度 cron 非法: {expression}（只支持每日固定窗口）")
    return ScanCron(minute_step=minute_step, hour_start=hour_start, hour_end=hour_end)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScanRuntime(_Model):
    pageSize: int = Field(default=100, ge=1, le=1000)
    maxPages: int = Field(default=20, ge=1, le=1000)
    requestTimeoutSeconds: float = Field(default=3.0, gt=0, le=30)
    sourceBudgetSeconds: float = Field(default=30.0, gt=0, le=300)
    scanBudgetSeconds: float = Field(default=120.0, gt=0, le=600)
    concurrency: int = Field(default=1, ge=1, le=8)

    @model_validator(mode="after")
    def _budget_order(self) -> ScanRuntime:
        if self.scanBudgetSeconds < self.sourceBudgetSeconds:
            raise ValueError("scanBudgetSeconds 必须大于等于 sourceBudgetSeconds")
        return self


class ExpiryRules(_Model):
    expiredDays: int = Field(default=0, le=0)
    nearDays: int = Field(default=7, ge=0)
    nearRatio: float = Field(default=1 / 3, ge=0, le=1)
    watchDays: int = Field(default=30, ge=0)

    @model_validator(mode="after")
    def _day_order(self) -> ExpiryRules:
        if self.watchDays < self.nearDays:
            raise ValueError("watchDays 必须大于等于 nearDays")
        return self


class HourRules(_Model):
    p0Hours: float = Field(gt=0)
    p1Hours: float = Field(ge=0)
    p2Hours: float = Field(ge=0)

    @field_validator("p0Hours", "p1Hours", "p2Hours")
    @classmethod
    def _hour_thresholds_finite(cls, value: float) -> float:
        # inf/NaN 会让分级恒真或恒假（例如 p0Hours=inf 时永远停在 P1），必须启动期拒绝。
        if not isfinite(float(value)):
            raise ValueError("小时阈值必须是有限数值")
        return value

    @model_validator(mode="after")
    def _severity_order(self) -> HourRules:
        if not (self.p0Hours > self.p1Hours > self.p2Hours):
            raise ValueError("必须满足 p0Hours > p1Hours > p2Hours")
        return self


class BacklogRules(_Model):
    growthRatio: float = Field(default=0.30, ge=0, le=1)
    absoluteDelta: int = Field(default=10, ge=0)
    baselineScans: int = Field(default=3, ge=1)
    consecutiveForP1: int = Field(default=3, ge=1)


def _finite_positive(value: float, label: str) -> float:
    """只允许有限正数；NaN / Infinity 会让 max_silence=inf 永不报无录入，必须拒绝。"""
    if not isfinite(float(value)) or float(value) <= 0:
        raise ValueError(f"{label} 必须是有限正数")
    return value


class OutboundRules(_Model):
    """出货异常（v0.2.1）：enabled 默认为 True，24h 自然时间老化。"""

    enabled: bool = True
    p0Hours: float = Field(default=24, gt=0)
    # 分页预算：出货异常源是全历史候选集，最新差异行在 oldest 正序下位于末尾。
    # 20 × 100 只覆盖 2000 行时会漏掉最新异常（审计 m01655/m01902），因此默认放宽到
    # 50 页并允许按仓库配置——溢出仍会标 partial + SCAN-PARTIAL，不会静默当作无异常。
    pageSize: int = Field(default=100, ge=1, le=500)
    maxPages: int = Field(default=50, ge=1, le=500)

    @field_validator("p0Hours")
    @classmethod
    def _p0_hours_finite(cls, value: float) -> float:
        # inf 会让所有行都落在 P1 侧（age > inf 永远为假），NaN 让分级结果不确定；
        # 两者都不是可配置的老化阈值，必须启动期拒绝（审计 m01655）。
        return _finite_positive(value, "p0Hours")


class TemperatureLocation(_Model):
    """地点词表：min_c/max_c 与录入间隔必须由用户提供真实业务值。"""

    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    min_c: float
    max_c: float
    # 地点级录入间隔为必填业务值：缺失会回退默认 8h，违背"真实间隔由业务提供"。
    expected_interval_hours: float

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("地点 name 不能为空白")
        return value.strip()

    @field_validator("aliases")
    @classmethod
    def _aliases_clean(cls, value: list[str]) -> list[str]:
        cleaned = [a.strip() for a in value if a and a.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("同一地点 aliases 不允许重复")
        return cleaned

    @field_validator("expected_interval_hours")
    @classmethod
    def _interval_finite(cls, value: float) -> float:
        return _finite_positive(value, "expected_interval_hours")

    @field_validator("min_c", "max_c")
    @classmethod
    def _temp_finite(cls, value: float) -> float:
        if not isfinite(float(value)):
            raise ValueError("min_c / max_c 必须是有限数值")
        return value

    @model_validator(mode="after")
    def _range_order(self) -> TemperatureLocation:
        if self.min_c > self.max_c:
            raise ValueError("min_c 必须小于等于 max_c")
        if self.name in self.aliases:
            raise ValueError("地点 aliases 不能与 name 重复")
        return self


class TemperatureRules(_Model):
    """温度巡检（v0.2.1）：enabled 默认 False，无真实阈值时不产生生产告警。"""

    enabled: bool = False
    expectedIntervalHours: float = Field(default=8, gt=0)
    consecutivePoints: int = Field(default=2, ge=1)
    p0AbsC: float = Field(default=2.0, ge=0)
    p0SpanHours: float = Field(default=4.0, ge=0)
    # 必须严格 >0：为 0 时任何 exceed=0 的正常读数都会被判成单点 P0（m01655）。
    p0SinglePointAbsC: float = Field(default=5.0, gt=0)
    locations: list[TemperatureLocation] = Field(default_factory=list)

    @field_validator(
        "expectedIntervalHours", "p0AbsC", "p0SpanHours", "p0SinglePointAbsC"
    )
    @classmethod
    def _thresholds_finite(cls, value: float) -> float:
        if not isfinite(float(value)):
            raise ValueError("温度阈值必须是有限数值")
        return value

    @model_validator(mode="after")
    def _require_locations_when_enabled(self) -> "TemperatureRules":
        # fail-closed：没有真实地点词表/阈值时绝不启用温度告警，
        # 避免用示例 2–8℃ / 8h 当生产值，也避免开启后把每次采集都报成未知地点 P2。
        if self.enabled and not self.locations:
            raise ValueError("temperature.enabled=true 时必须提供真实 locations 地点词表")
        # 地点名与别名在所有地点间唯一：重复 alias 会按首匹配套用错误阈值。
        seen: dict[str, str] = {}
        for loc in self.locations:
            for token in [loc.name] + list(loc.aliases):
                if token in seen:
                    raise ValueError(f"地点名/别名重复: {token}")
                seen[token] = loc.name
        return self


class RuleSet(_Model):
    expiry: ExpiryRules = Field(default_factory=ExpiryRules)
    noUp: HourRules = Field(
        default_factory=lambda: HourRules(p0Hours=8, p1Hours=4, p2Hours=2)
    )
    delay: HourRules = Field(
        default_factory=lambda: HourRules(p0Hours=24, p1Hours=2, p2Hours=0)
    )
    backlog: BacklogRules = Field(default_factory=BacklogRules)
    outbound: OutboundRules = Field(default_factory=OutboundRules)
    temperature: TemperatureRules = Field(default_factory=TemperatureRules)


class RoutingRule(_Model):
    rule_id: str = Field(min_length=1)
    warehouse: str = Field(min_length=1)
    assignee_role: str = Field(min_length=1)
    recipients: list[str] = Field(default_factory=list)

    @field_validator("recipients")
    @classmethod
    def _recipients(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("recipients 不允许重复")
        return cleaned


class NotificationConfig(_Model):
    mode: str = Field(default="dry_run", pattern="^(dry_run|in_app|full)$")
    recipients: list[str] = Field(default_factory=list)

    @field_validator("recipients")
    @classmethod
    def _recipients(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("recipients 不允许重复")
        return cleaned


class ScheduleConfig(_Model):
    """最小内部调度配置（阶段5）。

    只支持 ``*/N H-M * * *`` 一种形态：固定步长、固定每日窗口。
    不引入通用 cron 框架，避免把“巡检调度”变成一个需要长期维护的表达式子语言。
    """

    enabled: bool = False
    scanTypes: list[str] = Field(
        default_factory=lambda: ["expiry", "no_up", "delay", "backlog"],
    )
    cron: str = Field(default="*/15 7-23 * * *", min_length=1)
    timezone: str = Field(default="Asia/Shanghai", min_length=1)

    @field_validator("scanTypes")
    @classmethod
    def _scan_types(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("schedule.scanTypes 不能为空")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("schedule.scanTypes 不允许重复")
        unknown = [item for item in cleaned if item not in SUPPORTED_SCAN_TYPE_LIST]
        if unknown:
            raise ValueError(f"schedule.scanTypes 含未知巡检类型: {','.join(unknown)}")
        return cleaned

    @field_validator("cron")
    @classmethod
    def _cron(cls, value: str) -> str:
        parse_scan_cron(value)  # 非法表达式直接拒绝启动
        return value

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"未知时区: {value}") from exc
        return value


class LlmConfig(_Model):
    """LLM 聚合摘要配置（阶段6）：只表达，不判定。

    - 默认关闭；关闭时全部使用确定性模板摘要。
    - 上限写死为方案 §10.2 的硬边界（单次扫描 ≤20 次调用、单次 ≤8 秒），
      超过即视为非法配置拒绝启动，避免把成本/时延边界交给部署方放宽。
    - API Key 不在此处：只走环境变量 ``WMS_AGENT_LLM_API_KEY``。``extra="forbid"``
      使 ``apiKey`` 之类的键直接被拒绝，配置快照因此不可能携带密钥。
    """

    enabled: bool = False
    maxCallsPerScan: int = Field(default=20, ge=0, le=20)
    timeoutSeconds: float = Field(default=8.0, gt=0, le=8.0)
    concurrency: int = Field(default=4, ge=1, le=8)
    maxSummaryChars: int = Field(default=300, ge=1, le=300)
    maxActions: int = Field(default=3, ge=0, le=3)
    maxActionChars: int = Field(default=100, ge=1, le=100)


class ScanConfigDocument(_Model):
    version: str = Field(min_length=1)
    warehouses: list[str] = Field(min_length=1)
    scan: ScanRuntime = Field(default_factory=ScanRuntime)
    rules: RuleSet = Field(default_factory=RuleSet)
    routing: list[RoutingRule] = Field(default_factory=list)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    # 阶段6 新增且带默认值：阶段5 及之前入队的快照（无 llm 键）仍可校验通过，
    # 且哈希不变（哈希算在原始数据上），在途任务按“LLM 关闭”执行。
    llm: LlmConfig = Field(default_factory=LlmConfig)

    @field_validator("warehouses")
    @classmethod
    def _warehouses(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("warehouses 不允许重复")
        return cleaned

    @model_validator(mode="after")
    def _routing(self) -> ScanConfigDocument:
        warehouses = set(self.warehouses)
        for route in self.routing:
            if route.warehouse not in warehouses:
                raise ValueError(f"路由仓库不在 warehouses 中: {route.warehouse}")
            if route.rule_id != "*" and not any(
                fnmatch.fnmatchcase(rule_id, route.rule_id) for rule_id in KNOWN_RULE_IDS
            ):
                raise ValueError(f"路由规则未匹配任何已知规则: {route.rule_id}")
        return self


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ScanConfigError("YAML 键必须是字符串")
        if key in mapping:
            mark = getattr(key_node, "start_mark", None)
            location = f"（行 {mark.line + 1}）" if mark else ""
            raise ScanConfigError(f"YAML 重复键: {key}{location}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


@dataclass(frozen=True)
class LoadedScanConfig:
    path: Path
    document: ScanConfigDocument
    snapshot: str
    config_hash: str

    @property
    def version(self) -> str:
        return self.document.version

    @property
    def config(self) -> dict[str, Any]:
        return json.loads(self.snapshot)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def hash_config(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    roots = (Path.cwd(), Path(__file__).resolve().parents[2])
    for root in roots:
        resolved = root / candidate
        if resolved.is_file():
            return resolved
    return roots[0] / candidate


def _validate_data(data: Any) -> ScanConfigDocument:
    try:
        return ScanConfigDocument.model_validate(data)
    except (ValueError, TypeError) as exc:
        raise ScanConfigError(f"巡检配置非法: {exc}") from exc


def load_scan_config(
    path: str | Path, *, overrides: dict[str, Any] | None = None
) -> LoadedScanConfig:
    """加载 YAML，应用显式部署覆盖，返回不可变 canonical 快照。"""
    resolved = _resolve_path(path)
    try:
        raw = yaml.load(resolved.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except OSError as exc:
        raise ScanConfigError(f"巡检配置文件不可读: {resolved}") from exc
    except yaml.YAMLError as exc:
        raise ScanConfigError(f"巡检配置 YAML 解析失败: {exc}") from exc
    if not isinstance(raw, dict):
        raise ScanConfigError("巡检配置顶层必须是对象")

    data = dict(raw)
    for key, value in (overrides or {}).items():
        if key == "warehouses":
            data[key] = value
        elif key == "notifications":
            notifications = dict(data.get("notifications") or {})
            notifications.update(value)
            data[key] = notifications
        else:
            raise ScanConfigError(f"未知巡检配置覆盖项: {key}")
    document = _validate_data(data)
    snapshot = canonical_json(document.model_dump(mode="json"))
    return LoadedScanConfig(
        path=resolved,
        document=document,
        snapshot=snapshot,
        config_hash=hash_config(json.loads(snapshot)),
    )


def load_config_snapshot(
    snapshot: str, *, expected_hash: str | None = None, expected_version: str | None = None
) -> LoadedScanConfig:
    """校验队列中的 JSON 快照；worker 不读取当前 YAML。"""
    try:
        data = json.loads(snapshot)
    except (TypeError, ValueError) as exc:
        raise ScanConfigError("config_snapshot 不是合法 JSON") from exc
    document = _validate_data(data)
    # 哈希必须对「入队时写入的原始快照」计算：模型再序列化会做数值归一化
    # （例如 nearRatio 1/3 → 0.3333333333333333），若用归一化结果重算哈希，
    # 同一份配置在入队与消费两侧会得到不同哈希，导致合法快照被误判为篡改。
    canonical = canonical_json(data)
    actual_hash = hash_config(json.loads(canonical))
    if expected_hash is not None and actual_hash != expected_hash:
        raise ScanConfigError("config_snapshot_hash_mismatch")
    if expected_version is not None and document.version != expected_version:
        raise ScanConfigError("config_snapshot_version_mismatch")
    return LoadedScanConfig(
        path=Path("<queue-snapshot>"),
        document=document,
        snapshot=canonical,
        config_hash=actual_hash,
    )
