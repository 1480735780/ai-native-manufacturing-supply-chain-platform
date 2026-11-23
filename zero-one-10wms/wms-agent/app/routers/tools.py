"""工具清单端点。

`GET /agent/tools`：需要合法 JWT，返回 6 个只读工具的 Schema。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.security import Principal, require_principal
from app.tools.registry import list_tools

router = APIRouter()


@router.get("/tools")
async def get_tools(principal: Principal = Depends(require_principal)) -> dict:
    """返回全部工具的 Schema。"""
    tools = [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.to_schema().parameters,
            "readOnly": tool.read_only,
        }
        for tool in list_tools()
    ]
    return {"code": 10000, "message": "ok", "data": {"tools": tools}}
