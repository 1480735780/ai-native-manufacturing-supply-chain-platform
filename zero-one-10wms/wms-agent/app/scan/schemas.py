"""巡检 API 的请求模型（响应走统一 {code,message,data} 外壳）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SUPPORTED_SCAN_TYPES = Literal["expiry", "no_up", "delay", "backlog"]


class ScanRequest(BaseModel):
    """POST /agent/scan 请求体。trigger 由认证身份推导，不在请求体中。"""

    model_config = ConfigDict(extra="forbid")

    scanTypes: list[SUPPORTED_SCAN_TYPES] = Field(
        default_factory=lambda: ["expiry"], description="巡检类型白名单"
    )
    requestId: str | None = Field(default=None, description="手动幂等键")
    dryRun: bool | None = Field(
        default=None, description="只算 findings 不落告警不通知；不指定即 false（与通知模式无关）"
    )
    warehouse: str | None = Field(default=None, description="仓库，多仓必填")
    scheduleSlot: str | None = Field(
        default=None, description="定时槽（仅服务令牌参与幂等键；无槽位的服务扫描不去重）"
    )


class AlertActionRequest(BaseModel):
    """告警状态转移请求体。"""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, description="操作原因")
    ignoredUntil: str | None = Field(
        default=None,
        description="忽略截止时间：带时区的 ISO 8601，且须晚于当前时间；入口统一校验（非法 → 422）",
    )
