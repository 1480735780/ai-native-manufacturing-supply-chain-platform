"""6 个 L0 只读工具的定义与参数模型。

约束：
- 工具全部只读（GET），不暴露写操作；
- 对 LLM 只暴露统一 snake_case 参数，Java 端差异由适配层处理；
- 参数模型 `extra="forbid"`，模型编造的参数直接报错，不做静默忽略。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts import ToolSchema

TOOL_STOCK_QUERY = "STOCK-QUERY"
TOOL_EXP_WARN_QUERY = "EXP-WARN-QUERY"
TOOL_DAYCHECK_NOUP = "DAYCHECK-NOUP"
TOOL_DASH_PEND = "DASH-PEND"
TOOL_DASH_TREND = "DASH-TREND"
TOOL_DAYCHECK_DELAY = "DAYCHECK-DELAY"

# DASH-TREND 的四个语义
METRIC_UP_TOP = "up_top"
METRIC_DOWN_TOP = "down_top"
METRIC_UP_RECENT_DAYS = "up_recent_days"
METRIC_DOWN_RECENT_DAYS = "down_recent_days"

TREND_ENDPOINTS: dict[str, str] = {
    METRIC_UP_TOP: "/dashboard/query-goods-to-up",
    METRIC_DOWN_TOP: "/dashboard/query-goods-to-down",
    METRIC_UP_RECENT_DAYS: "/dashboard/query-goods-to-up-in-recent-days",
    METRIC_DOWN_RECENT_DAYS: "/dashboard/query-goods-to-down-in-recent-days",
}

# DASH-PEND 的四个计数端点
PEND_ENDPOINTS: tuple[str, ...] = (
    "/dashboard/query-pend-receipt",
    "/dashboard/query-pend-to-up",
    "/dashboard/query-pend-pick",
    "/dashboard/query-cur-pick",
)


class _Params(BaseModel):
    """参数模型基类。"""

    model_config = ConfigDict(extra="forbid")


class PageParams(_Params):
    """分页参数。"""

    page_index: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页行数，1~100")


class StockQueryParams(PageParams):
    """库存查询参数。"""

    location_code: str | None = Field(default=None, description="储位编码")
    pallet_id: str | None = Field(default=None, description="托盘（箱）号")
    customer_code: str | None = Field(default=None, description="客户编码")
    customer_name: str | None = Field(default=None, description="客户名称")
    goods_code: str | None = Field(default=None, description="商品编码")
    goods_name: str | None = Field(default=None, description="商品名称")


class ExpWarnQueryParams(PageParams):
    """效期预警查询参数。"""

    customer_code: str | None = Field(default=None, description="客户编码")
    customer_name: str | None = Field(default=None, description="客户名称")
    goods_code: str | None = Field(default=None, description="商品编码")
    goods_name: str | None = Field(default=None, description="商品名称")


class NoUpGoodsParams(PageParams):
    """收货未上架查询参数。"""

    location_code: str | None = Field(default=None, description="储位编码")
    pallet_id: str | None = Field(default=None, description="托盘（箱）号")
    customer_code: str | None = Field(default=None, description="客户编码")
    customer_name: str | None = Field(default=None, description="客户名称")
    goods_code: str | None = Field(default=None, description="商品编码")
    goods_name: str | None = Field(default=None, description="商品名称")


class DelayQueryParams(PageParams):
    """进货延时查询参数（仅分页）。"""


class PendQueryParams(_Params):
    """待办计数参数（无需参数）。"""


class TrendQueryParams(_Params):
    """上/下架 Top 与趋势参数。"""

    metric: Literal[
        METRIC_UP_TOP, METRIC_DOWN_TOP, METRIC_UP_RECENT_DAYS, METRIC_DOWN_RECENT_DAYS
    ] = Field(description="统计维度：上架Top/下架Top/近N日上架/近N日下架")
    count: int = Field(default=7, description="统计条数，1~30，超界按边界截断")


@dataclass(frozen=True)
class ToolDefinition:
    """一个只读工具的定义。"""

    name: str
    description: str
    params_model: type[_Params]
    endpoints: tuple[str, ...]
    read_only: bool = True

    def to_schema(self) -> ToolSchema:
        """转成暴露给模型的工具描述。"""
        schema = self.params_model.model_json_schema()
        schema.pop("title", None)
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=schema,
        )


TOOLS: dict[str, ToolDefinition] = {
    TOOL_STOCK_QUERY: ToolDefinition(
        name=TOOL_STOCK_QUERY,
        description="按储位、托盘、客户、商品等条件分页查询实时库存。",
        params_model=StockQueryParams,
        endpoints=("/stock/inventory-query/query-all",),
    ),
    TOOL_EXP_WARN_QUERY: ToolDefinition(
        name=TOOL_EXP_WARN_QUERY,
        description="按客户、商品等条件分页查询效期预警库存。",
        params_model=ExpWarnQueryParams,
        endpoints=("/stock/expiry-warning/query-all",),
    ),
    TOOL_DAYCHECK_NOUP: ToolDefinition(
        name=TOOL_DAYCHECK_NOUP,
        description="分页查询收货后尚未上架的货物。",
        params_model=NoUpGoodsParams,
        endpoints=("/daycheck/no-up/get-no-up-goods",),
    ),
    TOOL_DASH_PEND: ToolDefinition(
        name=TOOL_DASH_PEND,
        description="查询待收货、待上架、待拣货与当前拣货四个待办计数。",
        params_model=PendQueryParams,
        endpoints=PEND_ENDPOINTS,
    ),
    TOOL_DASH_TREND: ToolDefinition(
        name=TOOL_DASH_TREND,
        description="查询上架/下架数量 Top 或近 N 日上架/下架趋势。",
        params_model=TrendQueryParams,
        endpoints=tuple(TREND_ENDPOINTS.values()),
    ),
    TOOL_DAYCHECK_DELAY: ToolDefinition(
        name=TOOL_DAYCHECK_DELAY,
        description="分页查询进货（入库）延时记录。",
        params_model=DelayQueryParams,
        endpoints=("/daycheck/delay/im-delay",),
    ),
}


def get_tool(name: str) -> ToolDefinition:
    """按名称取工具定义。"""
    try:
        return TOOLS[name]
    except KeyError as exc:
        raise KeyError(f"unknown tool: {name}") from exc


def list_tools() -> list[ToolDefinition]:
    """全部工具定义（按注册顺序）。"""
    return list(TOOLS.values())


def tool_schemas() -> list[ToolSchema]:
    """全部工具的模型可见 Schema。"""
    return [tool.to_schema() for tool in TOOLS.values()]
