"""运行配置：非密项可用环境变量覆盖，密钥只来自运行环境或本地 .env。

配置项与 `.env.example` 一一对应；本模块不打印、不记录任何密钥值。
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # trace 存储：F-012 起可用 postgres；不可用时降级为 memory
    store_backend: str = Field(default="memory", validation_alias="WMS_AGENT_STORE_BACKEND")
    db_url: str = Field(default="", validation_alias="WMS_AGENT_DB_URL")

    @property
    def bind(self) -> str:
        """监听地址，默认只绑 loopback（ADR-007 落地要点）。"""
        return f"{self.host}:{self.port}"


def get_settings() -> Settings:
    """读取当前配置（每次调用重新读，便于测试覆盖环境变量）。"""
    return Settings()
