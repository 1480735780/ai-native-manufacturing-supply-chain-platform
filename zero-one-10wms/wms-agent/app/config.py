"""运行配置：非密项可用环境变量覆盖，密钥只来自运行环境或本地 .env。

配置项与 `.env.example` 一一对应；本模块不打印、不记录任何密钥值。
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_csv(value: Any) -> Any:
    """环境变量里的列表：逗号分隔；也接受 JSON 数组。空串表示空列表。"""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return []
    if text.startswith("["):
        return json.loads(text)
    return [item.strip() for item in text.split(",") if item.strip()]


class Settings(BaseSettings):
    """服务配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 服务
    host: str = Field(default="127.0.0.1", validation_alias="WMS_AGENT_HOST")
    port: int = Field(default=11200, validation_alias="WMS_AGENT_PORT")

    # Gateway
    gateway_url: str = Field(
        default="http://127.0.0.1:10001", validation_alias="WMS_GATEWAY_URL"
    )
    tool_timeout_seconds: float = Field(
        default=3.0, validation_alias="WMS_AGENT_TOOL_TIMEOUT_SECONDS"
    )

    # JWT 验签公钥（RS256），仅做验签，不涉及签发
    jwt_public_key_path: str = Field(
        default="../wms-java/wms-common/src/main/resources/public.pem",
        validation_alias="WMS_JWT_PUBLIC_KEY_PATH",
    )

    # LLM
    llm_provider: str = Field(default="mock", validation_alias="WMS_AGENT_LLM_PROVIDER")
    llm_base_url: str = Field(
        default="https://api.agnes-ai.cn/v1", validation_alias="WMS_AGENT_LLM_BASE_URL"
    )
    llm_model: str = Field(default="agnes-3.0-flash", validation_alias="WMS_AGENT_LLM_MODEL")
    llm_api_key: str = Field(default="", validation_alias="WMS_AGENT_LLM_API_KEY")
    llm_timeout_seconds: float = Field(
        default=8.0, validation_alias="WMS_AGENT_LLM_TIMEOUT_SECONDS"
    )
    # mock provider 的回放场景文件（本地 JSON），仅离线回放用
    llm_scenario_path: str = Field(
        default="", validation_alias="WMS_AGENT_LLM_SCENARIO_PATH"
    )

    # Nacos（可选，只读拉配置，不注册服务）
    nacos_enabled: bool = Field(default=False, validation_alias="WMS_AGENT_NACOS_ENABLED")

    # 巡检非密配置：启动时加载一次；阈值、路由、通知与调度均进入队列快照。
    scan_config_path: str = Field(
        default="config/scan.yaml", validation_alias="WMS_AGENT_SCAN_CONFIG_PATH"
    )

    # 巡检允许访问的仓库范围。首版强制单仓：数据源不支持按仓库过滤，
    # 配置多个仓库时服务拒绝启动（见 main.ensure_single_scan_warehouse）。
    # 显式设置环境变量时覆盖 scan.yaml，并纳入最终生效快照。
    scan_warehouses: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["W01"],
        validation_alias="WMS_AGENT_SCAN_WAREHOUSES",
    )

    # trace 存储：F-012 起可用 postgres；不可用时降级为 memory
    store_backend: str = Field(default="memory", validation_alias="WMS_AGENT_STORE_BACKEND")
    db_url: str = Field(default="", validation_alias="WMS_AGENT_DB_URL")

    # 巡检：通知模式（dry_run 只落记录不发送；in_app 写自有通知；full 暂不启用）
    notification_mode: str = Field(
        default="dry_run", validation_alias="WMS_AGENT_NOTIFICATION_MODE"
    )
    # 巡检：持久队列与 worker（worker 始终随服务启动；调度开关在 scan.yaml 的 schedule.enabled）
    scan_worker_poll_seconds: float = Field(
        default=2.0, validation_alias="WMS_AGENT_SCAN_WORKER_POLL_SECONDS"
    )
    # 租约时长：worker 领取写 lease_owner/leased_at，执行期间按 1/3 周期心跳续租；
    # 超过该时长无心跳的 running 由周期恢复重新入队（attempt<3）或标 failed(stale)。
    scan_lease_seconds: int = Field(
        default=60, validation_alias="WMS_AGENT_SCAN_LEASE_SECONDS"
    )
    # in_app 通知接收人（定时扫描用，逗号分隔用户名）；手动扫描推给发起人。
    alert_recipients: Annotated[list[str], NoDecode] = Field(
        default_factory=list, validation_alias="WMS_AGENT_ALERT_RECIPIENTS"
    )
    # 定时巡检取短时令牌（不把用户 JWT 持久化到队列）
    service_token_url: str = Field(
        default="http://127.0.0.1:10001/login/service-token",
        validation_alias="WMS_AGENT_SERVICE_TOKEN_URL",
    )
    service_api_key: str = Field(default="", validation_alias="WMS_AGENT_SERVICE_API_KEY")
    service_key_id: str = Field(default="", validation_alias="WMS_AGENT_SERVICE_KEY_ID")
    service_warehouse: str | None = Field(
        default=None, validation_alias="WMS_AGENT_SERVICE_WAREHOUSE"
    )
    # 短时令牌必须来自这个固定的只读服务账号（与 Java agent.service.username 对应）。
    # worker 解码令牌后强制校验 token_use/authorities/账号名/仓库范围，防止拿用户 JWT 或
    # 任意账号签发的令牌冒充执行身份。
    service_account_name: str = Field(
        default="agent-inspector", validation_alias="WMS_AGENT_SERVICE_ACCOUNT_NAME"
    )

    # 保留与归档（ADR-020）：运维参数，不进巡检配置快照。
    # - 已结案告警、告警事件、扫描摘要、扫描记录及其证据：在线 N 天后转入归档表，归档再保留
    #   M 天后删除；通知同样在线 N 天后归档（审计证据）；
    # - 问数 trace/tool_calls、超过 2 年的指标日聚合：到期直接删除（不归档）。
    # 自动任务默认关闭；管理员可随时调 POST /agent/scan/retention/run 手动执行一轮。
    retention_enabled: bool = Field(
        default=False, validation_alias="WMS_AGENT_RETENTION_ENABLED"
    )
    retention_alerts_online_days: int = Field(
        default=180, validation_alias="WMS_AGENT_RETENTION_ALERTS_ONLINE_DAYS"
    )
    retention_alerts_archive_days: int = Field(
        default=365, validation_alias="WMS_AGENT_RETENTION_ARCHIVE_DAYS"
    )
    retention_notifications_days: int = Field(
        default=90, validation_alias="WMS_AGENT_RETENTION_NOTIFICATIONS_DAYS"
    )
    retention_trace_days: int = Field(
        default=90, validation_alias="WMS_AGENT_RETENTION_TRACE_DAYS"
    )
    # 指标日聚合的在线期（天）：metric_date 早于 now - N 天的聚合行删除；指标接口最长回看 2 年
    retention_metrics_days: int = Field(
        default=730, validation_alias="WMS_AGENT_RETENTION_METRICS_DAYS"
    )
    # 每批行数与每轮最多批数：限制单次任务对线上表的锁与 IO 影响（默认 20×500 行/类）
    retention_batch_size: int = Field(
        default=500, validation_alias="WMS_AGENT_RETENTION_BATCH_SIZE"
    )
    retention_max_batches: int = Field(
        default=20, validation_alias="WMS_AGENT_RETENTION_MAX_BATCHES"
    )
    # 自动任务的每日执行时刻（HH:MM）与时区；过了该时刻当天只跑一次
    retention_daily_at: str = Field(
        default="02:30", validation_alias="WMS_AGENT_RETENTION_DAILY_AT"
    )
    retention_timezone: str = Field(
        default="Asia/Shanghai", validation_alias="WMS_AGENT_RETENTION_TIMEZONE"
    )

    @field_validator("scan_warehouses", "alert_recipients", mode="before")
    @classmethod
    def _parse_list_env(cls, value: Any) -> Any:
        return _split_csv(value)

    @property
    def bind(self) -> str:
        """监听地址，默认只绑 loopback（ADR-007 落地要点）。"""
        return f"{self.host}:{self.port}"


class ScanConfigError(RuntimeError):
    """巡检配置非法：服务拒绝启动，不带着错误配置运行。"""


def ensure_single_scan_warehouse(warehouses: list[str]) -> str:
    """首版强制单仓：Java 数据源不支持按仓库过滤，多仓数据会被贴成请求仓库的标签。

    配置 0 个或多个仓库一律拒绝启动，直到 Java 侧支持仓库过滤；返回唯一仓库。
    """
    unique = list(dict.fromkeys(w for w in (warehouses or []) if w))
    if len(unique) != 1:
        raise ScanConfigError(
            "WMS_AGENT_SCAN_WAREHOUSES 首版只允许配置一个仓库，当前: "
            + (", ".join(unique) if unique else "空")
        )
    return unique[0]


def get_settings() -> Settings:
    """读取当前配置（每次调用重新读，便于测试覆盖环境变量）。"""
    return Settings()
