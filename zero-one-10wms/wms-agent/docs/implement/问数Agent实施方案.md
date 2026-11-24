# 问数 Agent 实施方案（F-006 ~ F-013）

> 编制日期：2026-11-23  
> 状态：**设计已对齐，待实施**（技术选型 ADR v1.0 + Round 1~3 grilling 结论）  
> 范围：Python 问数 Agent、网关接入、6 个只读工具、同步 `/agent/query`、前端悬浮窗、trace 持久化与 harness  
> 事实源：`documents/07、AI-Agent化/技术选型ADR.md`、`documents/07、AI-Agent化/工具清单.md`、`feature_list.json`

---

## 1. 目标与非目标

### 1.1 目标

1. 新增独立 Python 微服务 `zero-one-10wms/wms-agent/`，端口 `11200`，默认绑定 `127.0.0.1`。
2. 前端通过 Gateway 调用同步 `POST /agent/query`，用自然语言查询库存、效期、未上架、待办、趋势、延时。
3. Agent 只调用 6 个 L0 只读 Java 端点，并透传用户 JWT，不直读 MySQL。
4. 每次回答返回 `traceId`、`sessionId`、`toolCalls`，可审计、可回放、可验证。
5. mock LLM 场景回放可作为 harness 的确定性判据。
6. `init.sh --agent` 可一键校验 Python 3.14.7、uv lock、pytest 和 mock 回放。

### 1.2 非目标

- 不做多轮上下文记忆：`sessionId` 只做 trace 分组。
- 不做 SSE / 流式输出：v1 只做同步请求。
- 不接 RocketMQ、Nacos 服务注册、Mneme-rag、pgvector。
- 不做 NL2SQL，不直连 MySQL。
- 不暴露 W/X 级写工具；6 个工具全部为 R 级只读。
- 不修改 Java 业务 Controller 的参数命名和返回结构，差异全部由 Python 适配层消化。

---

## 2. 已确认的关键设计决策

| 主题 | 决策 |
|---|---|
| 代码位置 | `zero-one-10wms/wms-agent/` |
| Python | **3.14.7**，解释器 `D:/DownloadPackage/environment/python.exe`，`requires-python = ">=3.14,<3.15"` |
| 包管理 | uv + `pyproject.toml` + `uv.lock`；cache 放项目内 `.uv/cache` |
| 服务端口 | `11200`，默认 `127.0.0.1:11200` |
| 网关 | `agent-route` 静态路由；Python 不注册 Nacos |
| 健康检查 | `/agent/health` 匿名，仅返回 `{"status":"ok"}` |
| 业务鉴权 | Python 自验 RS256 JWT 与 `exp`；`user` header 仅交叉校验，不作为身份权威 |
| 工具鉴权 | Python 调 Gateway 时透传原始用户 JWT |
| 响应外壳 | 业务接口 `{code, message, data}`；`code=10000` 表示成功 |
| 请求字段 | `query` 必填，`sessionId` 可选；不预留 `context` |
| ReAct | 单 Agent，工具调用轮数硬上限 **2 轮** |
| 前端超时 | 独立 axios 实例 `timeout=60000`，不复用全局 `http.js` |
| trace | 不存完整工具结果；存参数摘要、状态、行数、耗时、错误码和 digest |
| PG | 独立 schema `wms_agent`；PG 不可用时问数降级为 `persisted=false` |

---

## 3. 服务结构与依赖

### 3.1 目录规划

```
zero-one-10wms/wms-agent/
  pyproject.toml
  uv.lock
  .env.example
  app/
    __init__.py
    main.py                 # FastAPI 入口
    config.py               # Settings 与 env 加载
    contracts.py            # API request/response Pydantic 模型
    security.py             # JWT RS256 验证与身份解析
    agent/
      __init__.py
      service.py            # 同步问数编排
      react.py              # 2 轮工具调用控制
      trace.py              # 请求内 trace collector
    llm/
      __init__.py
      provider.py           # LLMProvider 协议
      openai_compatible.py  # OpenAI 兼容实现
      mock.py               # 场景回放实现
    tools/
      __init__.py
      registry.py           # 6 工具注册与 Schema
      gateway_client.py     # Gateway HTTP client
      adapter.py            # 参数/返回/错误码归一化
      sanitizer.py          # 截断与个人信息脱敏
    storage/
      __init__.py
      store.py              # TraceStore 协议
      memory.py             # F-010 前的内存实现
      postgres.py           # F-012 实现
  tests/
    test_health.py
    test_security.py
    test_tools.py
    test_query_replay.py
    fixtures/
      llm/
        stock_query_happy.json
        stock_query_empty.json
        expiry_then_stock.json
        dash_pend_partial_fail.json
      gateway/
        *.json
  docs/
    implement/
      问数Agent实施方案.md
```

### 3.2 依赖分档

**F-006 一次加入 Tier 1：**

- `fastapi`
- `uvicorn[standard]`
- `httpx`
- `pydantic`
- `pydantic-settings`
- `pyjwt`
- `cryptography`
- `pytest`
- `pytest-asyncio`

**后续按 feature 加入 Tier 2：**

- F-010：`agentscope`（先跑 Python 3.14 兼容性探针）
- F-012：`psycopg[binary]`

不引入 `respx`；工具 HTTP mock 使用 `httpx.MockTransport`。不引入 LangChain Chain / AgentExecutor。

---

## 4. 配置与环境

### 4.1 `.env.example`

```dotenv
# 服务
WMS_AGENT_HOST=127.0.0.1
WMS_AGENT_PORT=11200

# Gateway
WMS_GATEWAY_URL=http://127.0.0.1:10001

# JWT
WMS_JWT_PUBLIC_KEY_PATH=../wms-java/wms-common/src/main/resources/public.pem

# LLM
WMS_AGENT_LLM_PROVIDER=mock
WMS_AGENT_LLM_BASE_URL=https://api.agnes-ai.cn/v1
WMS_AGENT_LLM_MODEL=agnes-3.0-flash
WMS_AGENT_LLM_API_KEY=

# Nacos（可选，只读）
WMS_AGENT_NACOS_ENABLED=false

# PG（F-012）：默认 postgres 持久化；无 PG 环境可改 memory 降级（persisted=false）
WMS_AGENT_STORE_BACKEND=postgres
WMS_AGENT_DB_URL=postgresql://postgres:postgres@127.0.0.1:5432/ragent
```

密钥只允许来自运行环境或 gitignored `.env`，不进代码、测试 fixture、Nacos 明文、日志、快照和 `MEMORY.md`。

### 4.2 Nacos / 网关配置顺序

F-007 必须严格按以下顺序执行：

1. 修改仓库样例 `zero-one-10wms/nacos-config/system.yaml`：
   - `sp.agent: 11200`，放在 `sp.othermana` 后面；
   - 增加 `agent.url: http://127.0.0.1:11200`（如配置结构需要，放到独立合适层级，不混入 `sp`）。
2. 同步真实 Nacos 的 `system.yaml`；样例文件修改不等于配置生效。
3. 修改 `wms-gateway/application.yaml`：
   - `white-paths` 增加 `/agent/health`；
   - `inner-paths` 增加 `/agent/query`、`/agent/tools`、`/agent/trace/**`；
   - 最后增加 `agent-route`。
4. 重启 Gateway 后实测。若仍被拦截，F-007 记 `blocked`，不改权限表、不改 `open-authorization`、不绕过网关。

目标路由：

```yaml
- id: agent-route
  uri: http://127.0.0.1:${sp.agent}
  predicates:
    - Path=/agent/**
```

---

## 5. API 契约

### 5.1 `GET /agent/health`

匿名端点，不套 `JsonVO` 外壳，响应固定为：

```json
{"status":"ok"}
```

不返回 Python 版本、依赖版本、PG 状态、网关状态或内部路径。

### 5.2 `POST /agent/query`

请求：

```json
{
  "query": "当前待上架多少件？",
  "sessionId": null
}
```

- `query`：必填，非空字符串，建议最大长度 500；
- `sessionId`：可选；缺省由服务端生成；
- 不接收、不预留 `context` 字段。

成功响应：

```json
{
  "code": 10000,
  "message": "ok",
  "data": {
    "answer": "当前待上架 128 件。",
    "sessionId": "s-20261123-001",
    "traceId": "t-20261123-001",
    "persisted": false,
    "toolCalls": [
      {
        "tool": "DASH-PEND",
        "params": {},
        "status": "ok",
        "rowCount": 4,
        "durationMs": 120,
        "endpoint": "/dashboard/query-pend-*",
        "errorCode": null,
        "retryable": false,
        "attempt": 1,
        "resultDigest": "sha256:..."
      }
    ],
    "createdAt": "2026-11-23T20:17:53+08:00"
  }
}
```

失败仍使用 `{code, message, data}` 外壳；`toolCalls` 在已完成工具调用时保留，方便定位失败前行为。

### 5.3 `GET /agent/tools`

返回 6 个工具 Schema。该端点需要合法 JWT（经 Gateway 后仍由 Python 自验）。

### 5.4 `GET /agent/trace/{traceId}`

F-012 实现按 trace 查询审计摘要；F-010 阶段可先返回未持久化提示，不伪造数据。

---

## 6. 鉴权与身份

### 6.1 Python 侧验证

1. 从 `Authorization: Bearer <token>` 提取裸 JWT。
2. 用 `wms-common/src/main/resources/public.pem` 验证 RS256 签名。
3. 验证 `exp`。
4. 从 claims 取身份：
   - 优先 `user_name`（Spring Security OAuth2 实际约定）；
   - 兼容 `username`（`PayloadDTO` 字段）；
   - `sub` 作为用户 ID 候选；
   - `authorities` 只做记录，不在 Python 重做业务 RBAC。
5. 若存在网关注入的 `user` header，仅做交叉校验；不一致记 warning，身份仍以 JWT claims 为准。
6. 缺 token、签名无效、过期均拒绝；不 fallback 到 `user` header。

### 6.2 工具调用

Python 调 Gateway 时原样透传用户 JWT。service API Key 不替代用户 JWT，首版前端链路不启用 API Key 双入口。

### 6.3 已知边界

- Python 不查 Redis 注销黑名单；已登出 token 在 JWT 过期前直连 Python 仍是理论风险。
- 服务只绑定 loopback，正常流量必须先过 Gateway。
- 仓库历史中存在可签发 JWT 的私钥，这是独立安全问题；问数 Agent 不在本轮清理，但必须记录风险并后续轮换密钥。

---

## 7. 工具适配层

### 7.1 6 个工具

| 工具 | Java 端点 | 说明 |
|---|---|---|
| `STOCK-QUERY` | `GET /stock/inventory-query/query-all` | 库存分页 |
| `EXP-WARN-QUERY` | `GET /stock/expiry-warning/query-all` | 效期预警 |
| `DAYCHECK-NOUP` | `GET /daycheck/no-up/get-no-up-goods` | 收货未上架 |
| `DASH-PEND` | 4 个 `GET /dashboard/query-pend-*` / `query-cur-pick` | 并发聚合计数 |
| `DASH-TREND` | 4 个 `GET /dashboard/query-goods-to-*` | 上架/下架 Top 与趋势 |
| `DAYCHECK-DELAY` | `GET /daycheck/delay/im-delay` | 进货延时 |

### 7.2 对 LLM 暴露的统一参数

列表工具统一使用 snake case：

- `page_index`，默认 1，最小 1；
- `page_size`，默认 20，范围 1~100；
- `location_code`：储位；
- `pallet_id`：托盘；
- `customer_code`：客户编码；
- `customer_name`：客户名称；
- `goods_code`：商品编码；
- `goods_name`：商品名称。

适配层负责映射 Java 差异：

| 统一字段 | STOCK | EXP | NOUP |
|---|---|---|---|
| `location_code` | `kuWeiBianMa` | - | `bin_id` |
| `pallet_id` | `binId` | - | `tin_id` |
| `customer_code` | `cusCode` | `cusCode` | `cus_code` |
| `customer_name` | `zhongWenQch` | `zhongWenQch` | `zhong_wen_qch` |
| `goods_code` | `goodsCode` | `goodsId` | `goods_id` |
| `goods_name` | `shpMingCheng` | `shpMingCheng` | `shp_ming_cheng` |

`DASH-TREND` 暴露：

- `metric`: `up_top | down_top | up_recent_days | down_recent_days`
- `count`: 默认 7，范围 1~30；超出范围 clamp 到边界并在 trace 中记录原始值与实际值。

`DASH-PEND` 不暴露必填参数，内部并发调用 4 个计数端点并聚合。

### 7.3 返回归一化

所有工具统一返回：

```json
{
  "rows": [],
  "total": 0,
  "empty": true
}
```

- `rows == null` 与 `rows == []` 都转成 `[]`；
- `DAYCHECK-NOUP` 裸 List 的 `total = len(rows)`；
- `DASH-TREND` 的 Java `code=9999 / 查询数据不存在` 转为空结果，不算失败；
- `DASH-PEND` 聚合为 4 个计数对象；
- `9995` 为参数错误，`9994` 为运行时错误，不重试；
- 网络超时 / 5xx 可标记 `retryable=true`，但 v1 最多执行 1 次尝试，避免放大延迟。

### 7.4 数据进入 LLM 前的裁剪与脱敏

- 每个工具最多保留前 20 行进入 prompt；
- 每个工具序列化后不超过 4000 字符；
- 只保留回答所需字段，不把体积、面积等无关字段全部塞给模型；
- `DAYCHECK-DELAY`：
  - `imCarMobile` → 保留前 3 后 4，例如 `138****5678`；
  - `imCarDri` → 保留姓氏，例如 `王*`；
- 商品、客户、货主等业务实体名可保留；
- 完整工具结果不落库、不写日志。

---

## 8. LLMProvider 与回放

### 8.1 Provider 协议

`LLMProvider` 至少支持：

```python
async def complete(
    self,
    messages: list[Message],
    tools: list[ToolSchema],
) -> ModelReply
```

职责：

- 统一模型名、base URL、API Key、超时；
- 解析 tool call 与最终文本；
- 不做业务判断；
- 不把 API Key 写入异常或日志。

真实实现使用 Agnes 的 OpenAI 兼容 Chat Completions API，可通过 `httpx` 直接调用，避免额外 SDK 依赖：

- `WMS_AGENT_LLM_BASE_URL=https://api.agnes-ai.cn/v1`
- `WMS_AGENT_LLM_MODEL=agnes-3.0-flash`
- `WMS_AGENT_LLM_API_KEY` 只放本地 gitignored `.env` 或运行环境

已在聊天中暴露过的 key 不写入仓库；应先轮换，再把新 key 配置到本地 `.env`。

### 8.2 Mock 场景回放

Fixture 位于 `tests/fixtures/llm/<scenario>.json`，内容为有序响应列表：

```json
[
  {
    "type": "tool_call",
    "tool": "EXP-WARN-QUERY",
    "args": {}
  },
  {
    "type": "tool_call",
    "tool": "STOCK-QUERY",
    "args": {"goods_code": "A001"}
  },
  {
    "type": "text",
    "content": "A001 有 3 个批次将在 7 天内到期。"
  }
]
```

约束：

- 按顺序消费；
- 响应耗尽后再次调用必须抛错，不允许返回空文本；
- 断言重点是工具调用序列和参数，不逐字断言最终文案；
- 最终文案只断言关键数字或关键结论；
- 同一 scenario 重复运行结果确定。

### 8.3 时间与轮次

- LLM 单轮预算 8 秒；
- 单工具预算 3 秒；
- `DASH-PEND` 4 个子请求并发，总预算 3 秒；
- 工具调用轮数硬上限 2；
- 第 2 轮工具结果返回后，强制要求模型生成最终答案；
- 前端独立 axios 超时 60 秒；
- 端到端软目标 ≤15 秒，超时不作为单独失败条件。

---

## 9. 分阶段实施与验收

## F-006 服务骨架与健康检查

**改动**

- 新建 `wms-agent/pyproject.toml`、`uv.lock`、`app/main.py`；
- Tier 1 依赖一次加入；
- `/agent/health` 返回 `{"status":"ok"}`；
- 至少 1 个 pytest 覆盖 health；
- `README.md` 记录启动命令。

**命令**

```bash
cd zero-one-10wms/wms-agent
export UV_CACHE_DIR=/d/Learning/code/AIWMSproject/.uv/cache
uv sync --python /d/DownloadPackage/environment/python.exe
uv run pytest
uv run uvicorn app.main:app --host 127.0.0.1 --port 11200
curl http://127.0.0.1:11200/agent/health
```

**完成标准**

- `uv.lock` 与 `pyproject.toml` 同步；
- Python 为 3.14.7；
- pytest 通过；
- 直连 health 响应体精确等于 `{"status":"ok"}`；
- 无密钥入库。

## F-007 网关路由与鉴权实测

**改动**

- 按第 4.2 节顺序修改样例 Nacos、真实 Nacos、Gateway；
- 增加静态 `agent-route`；
- 记录 `/agent/health` 匿名可达和业务端点带 JWT 行为。

**验证**

```bash
curl http://127.0.0.1:10001/agent/health
# 带 /login/auth-login 获取的真实 JWT 请求 /agent/tools
```

**完成标准**

- health 经 Gateway 可达；
- `/agent/tools` 未带 token 拒绝；
- 合法 token 行为符合 inner-paths 实测结果；
- 不修改权限表、不绕过 Gateway；
- 若被拦截，F-007 `blocked` 并保存请求/响应摘要。

## F-008 LLMProvider

**改动**

- 实现 Provider 协议、OpenAI 兼容实现、Mock 场景回放；
- 单元测试覆盖签名接口、超时配置、mock 耗尽抛错；
- agnes-3.0-flash 真实调用仅做手动 smoke，不作为唯一 passing 依据。

**完成标准**

- mock 模式完全离线可跑；
- API Key 不出现在日志和异常；
- 同一 scenario 重复运行一致。

## F-009 6 个只读工具

**改动**

- 实现 Gateway client、Pydantic 参数模型、6 工具 Schema、适配层、脱敏层；
- 使用 `httpx.MockTransport` 覆盖每个工具的成功、空数据、参数错误、运行时错误、超时；
- `DASH-PEND` 并发聚合测试；
- `DASH-TREND` `9999` 归一化测试。

**完成标准**

- 6 个工具 Schema 可从 `/agent/tools` 输出；
- 统一参数映射有测试；
- 所有工具均为只读；
- 工具调用记录包含 status / rowCount / durationMs / errorCode / digest。

## F-010 同步问数与 2 轮 ReAct

**改动**

- 引入 AgentScope 前先跑 Python 3.14 兼容性探针；
- 实现单 Agent + 6 工具 + LLMProvider；
- 实现 `POST /agent/query`、JWT 自验、trace collector、2 轮硬上限；
- mock 场景至少覆盖：
  - 单工具成功；
  - 空数据；
  - 两步工具调用；
  - 单工具失败但请求返回说明；
  - 所有工具失败时不编造数据。

**完成标准**

- 响应契约完全符合第 5.2 节；
- `toolCalls` 必填；
- 工具调用轮数不超过 2；
- mock 回放可作为 passing evidence；
- 真实 LLM /真实 Gateway 仅作为运行时补充证据，不替代确定性测试。

## F-011 前端悬浮窗

**改动**

- 新增 `wms-frontend/src/apis/agent.ts`；
- 新增 `wms-frontend/src/components/ai-assistant/`；
- 挂载到登录后的 default layout；
- 独立 axios 实例 `timeout=60000`；
- UI 包含提问、loading、答案、工具调用折叠面板、错误提示。

**完成标准**

- `corepack pnpm build` 通过；
- 任意业务路由可打开/关闭悬浮窗；
- 请求失败不清空用户输入；
- 不做历史会话、多轮上下文、SSE、页面上下文注入。

## F-012 PostgreSQL trace 持久化

**表**

- `agent_sessions`
- `agent_traces`
- `agent_tool_calls`

只存审计摘要：用户标识、query、answer、状态、时间、耗时、工具名、脱敏参数、行数、错误码、digest。不存 JWT 原文、不存完整工具结果。

**完成标准**

- PG 可用时自动建 `wms_agent` schema 和 3 张表；
- `GET /agent/trace/{traceId}` 可查询摘要；
- PG 不可用时服务可启动、问数可完成，响应 `persisted=false`；
- 持久化失败不让问数失败。

## F-013 `init.sh --agent`

**命令**

```bash
cd zero-one-10wms
./init.sh --agent
```

**检查项**

1. `uv --version`；
2. Python 解释器为 3.14.x；
3. `uv lock --check`；
4. `uv sync --python /d/DownloadPackage/environment/python.exe`；
5. `uv run pytest`；
6. 至少一个 mock 回放断言通过；
7. `./init.sh --quick --snapshot` 仍通过。

---

## 10. 验证证据规则

- F-006 / F-008 / F-009 / F-010 / F-013 可以用 `uv run pytest` + mock 回放作为主要证据。
- F-007 / F-011 需要真实运行时证据；不能只写配置后标 passing。
- 涉及真实 LLM 的测试必须单独标记，不能把网络可用当作默认前提。
- 所有 evidence 写入 `feature_list.json`，并注明命令、日期、结果和未验证项。
- 不删除测试、不改权限表、不绕过网关、不伪造 token 来制造通过。
- C++ 仍按 `static_pass + runtime_unverified` 表述。

---

## 11. 剩余风险与后续事项

| 风险 | 处理 |
|---|---|
| AgentScope 不兼容 Python 3.14 | F-010 前探针验证；失败则 blocked，不悄悄降级 |
| Python 不查 Redis 注销黑名单 | loopback 绑定 + Gateway 前置校验；后续可评估 Redis 只读检查 |
| Gateway inner-paths 通配符行为未知 | F-007 实测；失败则 blocked |
| JWT 私钥明文在仓库历史 | 独立安全议题：后续轮换密钥、清理历史、补 ignore |
| 外部 LLM 数据边界 | 工具结果先裁剪/脱敏再进 prompt |
| PG 在虚拟机，地址变化 | `WMS_AGENT_DB_URL` 注入；不可用时降级 |
| 真实 Java 数据为空 | mock Gateway 测试契约，运行时验证记录空数据行为 |
