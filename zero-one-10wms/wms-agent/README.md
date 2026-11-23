# wms-agent

WMS 问数 Agent 微服务（Python 3.14.7 + uv + FastAPI）。

依据 `documents/07、AI-Agent化/技术选型ADR.md`（ADR-001/003/013/015）与
`wms-agent/docs/implement/问数Agent实施方案.md`。

## 边界

- 只做编排、推理、生成 + 自己的 trace 状态；不做业务规则校验，不直读 MySQL。
- 业务数据一律经 Gateway 调 Java 只读端点，并透传用户 JWT。
- 首版同步接口，不做 SSE；只注册 6 个 R 级只读工具。

## 环境准备

```bash
export UV_CACHE_DIR=$(pwd)/.uv/cache
uv sync --python /d/DownloadPackage/environment/python.exe
```

`uv.lock` 已提交入库，`uv sync` 后 `pyproject.toml` 与 lock 必须保持同步。

## 启动

```bash
cd zero-one-10wms/wms-agent
uv run uvicorn app.main:app --host 127.0.0.1 --port 11200
```

## 验证

```bash
uv run pytest                                   # 单元/契约测试
curl http://127.0.0.1:11200/agent/health       # => {"status":"ok"}
```

harness 一键校验（Git Bash，仓库根 `zero-one-10wms`）：

```bash
./init.sh --agent        # 检查关键文件 + 网关路由 + uv + uv sync + uv run pytest
```

`WMS_AGENT_PYTHON` 可覆盖解释器（路径或版本，如 `3.14`）；缺省由 uv 自行选择。

## trace 持久化（F-012）

默认后端为内存（`persisted=false`）。接 PostgreSQL 时：

```bash
export WMS_AGENT_STORE_BACKEND=postgres
export WMS_AGENT_DB_URL=postgresql://postgres:postgres@192.168.89.128:5432/ragent
```

服务启动时自动创建 schema `wms_agent` 与 `agent_sessions` / `agent_traces` /
`agent_tool_calls` 三张表（只用标准 PG 类型，不依赖 pgvector 扩展）；
建表失败只告警不阻塞启动，PG 不可达时问数照常返回并标 `persisted=false`。
只落审计摘要与 `resultDigest`，不落 JWT 原文与完整工具结果。

真实 PG 集成测试需显式给出连接串：

```bash
WMS_AGENT_TEST_DB_URL=postgresql://postgres:123456@127.0.0.1:5432/ragent uv run pytest
```

未设置该变量时，3 个集成用例自动跳过。

## 配置

复制 `.env.example` 为 `.env` 后按需修改；`.env` 已被仓库根 `.gitignore` 排除，
密钥（`WMS_AGENT_LLM_API_KEY` 等）只允许进 `.env` 或运行环境，禁止入库、进日志、进快照。

## 端点

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/agent/health` | 匿名 | 固定返回 `{"status":"ok"}`（F-006） |
| GET | `/agent/tools` | JWT | 6 个工具 Schema（F-009） |
| POST | `/agent/query` | JWT | 同步问数（F-010） |
| GET | `/agent/trace/{traceId}` | JWT | 调用审计摘要（F-010 起可用；F-012 起可落 PG） |

### 问数请求/响应

```jsonc
// POST /agent/query  {"query": "查一下库存", "sessionId": "可选"}
{
  "code": 10000,
  "message": "ok",
  "data": {
    "answer": "……",
    "sessionId": "s-…",
    "traceId": "t-…",
    "persisted": false,          // PG 不可用时为 false
    "toolCalls": [               // 必填：失败也保留已完成的调用
      {
        "tool": "STOCK-QUERY",
        "params": { "page_index": 1, "page_size": 20 },
        "status": "success|empty|error",
        "rowCount": 2,
        "durationMs": 12,
        "endpoint": "/stock/inventory-query/query-all",
        "errorCode": null,
        "retryable": false,
        "attempt": 1,
        "resultDigest": "sha256:…"
      }
    ],
    "createdAt": "2026-01-01T00:00:00+08:00"
  }
}
```

鉴权失败返回 HTTP 401 + `{"code":401,"message":"…","data":null}`；
请求体非法（缺 `query`、多传 `context`）返回 `{"code":9995,…}`。

### 离线回放

模型侧用 mock provider 回放本地 scenario，网关侧可用真实 Gateway：

```bash
WMS_AGENT_LLM_PROVIDER=mock \
WMS_AGENT_LLM_SCENARIO_PATH=tests/fixtures/llm/query_single_tool.json \
uv run uvicorn app.main:app --host 127.0.0.1 --port 11200
```

scenario 是有序响应列表（`tool_call` / `text`），按序消费，耗尽即报错；
只断言工具调用序列与参数，不断言模型逐字文案。

