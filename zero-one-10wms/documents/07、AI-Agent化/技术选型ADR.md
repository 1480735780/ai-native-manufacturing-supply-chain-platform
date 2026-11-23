# WMS AI Agent 微服务技术选型 ADR（v1.0）

> 编制日期：2026-11-23
> 状态：**Accepted**（经 5 轮 grilling 对齐后收敛，所有决策已过用户确认）
> 参与者：用户（架构决策）+ Codex（技术调研与评审）
> 决策范围：传统 WMS（Java/C++/Vue3 三栈）之上新增 AI Agent 微服务的技术选型与架构边界
> 相关文档：`工具清单.md`（490 端点分级清单）、`zero-one-10wms/architecture.md`（三栈骨架）

---

## 0. 背景与目标

传统 WMS 功能补齐已收尾（`feature_list.json` F-001 passing，静态通过）。现在需要在 Java（业务层）/ C++（性能层）/ Vue3（前端）三栈之上，新增**Python 智能层**，将传统业务场景做 AI Agent 智能化。

**核心约束：**

- Python Agent 服务是**独立微服务**，不侵入 Java/C++ 现有代码。
- 传统业务接口（约 490 个端点）已经存在且稳定，Agent 复用它们而不是重写。
- 本项目遵循 harnessengineering 约束：所有决策需有证据、可回放验证、状态可审计。
- Mneme-rag 项目（纯 Python FastAPI + agentscope）已在父仓库，后期作为 RAG 基座接入。

---

## 1. 决策索引（一览表）

| 编号 | 主题 | 决策 |
|---|---|---|
| ADR-001 | 代码组织 | `zero-one-10wms/wms-agent/` 目录，独立 Python 微服务 |
| ADR-002 | 主框架 | AgentScope（单 Agent + ReAct 循环），多 Agent 编排后期再做 |
| ADR-003 | 架构拓扑 | Gateway 做唯一枢纽，三栈星型互联，不两两直连 |
| ADR-004 | 通信协议 | HTTP REST（不引入 gRPC） |
| ADR-005 | 数据访问 | Python 只走 Gateway REST，不直读 MySQL |
| ADR-006 | 服务发现 | 不注册 Nacos，Java Feign 静态 `url="${agent.url}"` 调 Python |
| ADR-007 | 认证授权 | JWT 透传 + API Key 双层；高风险工具双签 |
| ADR-008 | 事件总线 | 首版不接 RocketMQ，代码留扩展点 |
| ADR-009 | 首版场景 | 问数 Agent（L0 感知层），6 个只读工具 |
| ADR-010 | LLM 选型 | GPT-4o-mini（开发/测试），必须包一层 `LLMProvider` |
| ADR-011 | 状态存储 | PostgreSQL 独立 schema `wms_agent`（不用 pgvector） |
| ADR-012 | 前端集成 | 全局悬浮 AI 对话框 |
| ADR-013 | 依赖管理 | uv + `pyproject.toml` + `uv.lock`，Python 3.11 |
| ADR-014 | 配置管理 | 混合：非密走 Nacos 配置中心（只读），密钥走 env/`.env` |
| ADR-015 | API 契约 | `/agent/**` 路由 + `10000` 成功码 + `toolCalls` 必填字段 |
| ADR-016 | Mneme-rag | HTTP 服务间调用，后期接入，不改 Mneme-rag 一行代码 |
| ADR-017 | 写操作策略 | W 级（增删改/状态变更）也走人工确认，X 级双签 |

---

## 2. 架构图

```
                    前端（Vue3）
                        │  复用现有 JWT（/login/auth-login 那套）
                        ▼
              ┌──────────────────┐
              │   wms-gateway    │  ← 唯一枢纽，星型拓扑中心
              └──┬─────┬─────┬───┘
                 │     │     │
        ┌────────┘     │     └────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌──────────┐
   │  Java    │   │   C++    │   │  Python   │
   │ 业务层    │   │ 性能层    │   │ 智能层     │
   │ (22 模块) │   │ (16 服务) │   │ (wms-agent)│
   └────┬────┘   └────┬────┘   └──────┬───┘
        │             │               │
        └─────────────┼───────────────┘
                      ▼
        MySQL / Redis / RocketMQ / FastDFS / Nacos
                  （三栈共享的中间件）
```

**架构原则（四句口诀）：**

- **网关管调用**：所有同步请求-响应走 Gateway。
- **RocketMQ 管事件**：异步事件走消息总线（首版 Python 不接）。
- **MySQL 管业务事实**：业务数据的唯一真相源在 MySQL，Python 不写。
- **Python 只管智能和自己的状态**：编排、推理、生成 + 自己的 PostgreSQL schema。

---

## 3. 详细决策

### ADR-001 代码组织

**决策**：Python Agent 微服务代码放在 `zero-one-10wms/wms-agent/` 目录，不建独立仓库、不加到 Mneme-rag 里。

**理由**：WMS Agent 的工具定义、场景 prompt、权限策略会跟 RAG 平台的通用逻辑持续分叉；混在一起会导致两边发版节奏互相绑架。Mneme-rag 保持通用性（`父仓库/Mneme-rag/`），未来可复用其他制造业场景。

**边界**：`wms-agent/` 是 Python 主战场，不引入 Java/C++ 源码，不写业务规则校验（那是 Java 的事）。

### ADR-002 主框架

**决策**：AgentScope 作为主框架，首版单 Agent + ReAct 循环；多 Agent 编排（MsgHub/Pipeline/Sequential）留扩展点但首版不做；不引入完整 LangChain。

**理由**：Mneme-rag v2 已基于 agentscope 做 ReAct + MCP 工具桥 + trace + 状态持久化，复用基础设施；重新引入 LangGraph 意味着两套状态持久化、两套 trace 格式、两套运维心智；AgentScope 原生编排能力对多 Agent 场景够用。

**边界**：LangChain 只允许使用原子组件（`Tool` / `OutputParser`），禁止使用 `Chain` / `AgentExecutor` 编排。

### ADR-003 架构拓扑

**决策**：Gateway 做唯一枢纽，三栈星型互联，不两两直连。

**理由**：项目已有的约定——Java 服务走 `lb://`（Nacos 发现）、C++ 服务走 `http://127.0.0.1:8103`（静态地址，不注册 Nacos）、Vue3 前端从 Gateway 进。Python 加入这个星型，把 Gateway 当唯一入口，地位等同于 Vue3 前端。

**结果**：Python 不知道 C++ 存在，Java 单个微服务不知道 Python 存在，C++ 不知道 Python 存在。所有"谁调谁"的信息都收敛在 Gateway 路由表里。

### ADR-004 通信协议

**决策**：HTTP REST，不引入 gRPC。

**理由**：Java 侧已有 240+ REST 端点 + Feign 声明；调试用 curl/Postman 即可；JSON 序列化在 Agent 场景（工具调用参数本身是 JSON）更自然；gRPC 的性能优势在这个量级用不上。

### ADR-005 数据访问

**决策**：Python 不直读 WMS 的 MySQL，所有业务数据都通过调用 Java REST API 获取（Java 已暴露 240+ 端点 + 57 个 SQL 视图）。

**理由**：Java 已有事务边界和业务规则校验；Python 直读 MySQL 需要在 Python 里复制 Java 的数据模型理解（字段语义、状态机、联动逻辑），一旦 Java 改表结构 Python 会悄悄坏掉；57 个视图本来就是给"外部消费者"设计的，Agent 作为消费者完全够用。

**边界**：唯一例外：未来做"离线分析/训练数据导出"可单独开只读账号直连，但那是分析场景不是 Agent 场景。

### ADR-006 服务发现

**决策**：Python 微服务**不注册 Nacos**，Java Feign 用静态 `url="${agent.url}"` 调 Python，模式与项目里 C++ 一致。

**理由**：Agent 服务是"被前端调用 + 调 Gateway"的边缘服务，不是被 Java 调用的核心服务，Nacos 的负载均衡和健康检查收益不大；Agent 服务走 SSE 长连接，跟 Java 微服务的短请求模式不同，放进 Nacos 可能触发不适合的健康检查策略。

**配置**：Java 侧 Feign 声明加 `url = "${agent.url}"`，`${agent.url}` 从 Nacos 配置中心 `system.yaml` 读取（如 `agent.url: http://127.0.0.1:8021`）。

### ADR-007 认证授权

**决策**：两层叠加认证——**用户身份用现有 JWT，服务身份用 API Key**，两者不互相替代。

| 链路 | 凭证 | 代表谁 |
|---|---|---|
| 前端 → 网关 → `/agent/**` | **复用现有 JWT**（`/login/auth-login` 那套） | 用户本人 |
| Java → Python（内部调用） | **API Key / service token** | 调用方服务 |
| Python → 网关 → 工具（Java/C++） | **透传用户 JWT** | 仍是用户本人 |

**为什么工具调用必须透传用户 JWT**：

1. Java 和 C++ 工具都校验 JWT（C++ 端点带 `API_HANDLER_AUTH_PARAME`）。Python 用自己的 service token 调，要么被网关 OAuth2 资源服务器拒，要么权限角色不对被业务服务拒。
2. 权限必须跟随真实用户。用户 A 不能通过 Agent 查到用户 B 的库存——如果 Agent 用统一的 service 身份，这层越权就悄悄发生了。透传 JWT 让现有 RBAC 直接生效，不用在 Agent 里重做一套权限。
3. 审计要记"谁让 Agent 干的"，不只是"Agent 调了什么"。

**API Key 的作用**：不是替代 JWT，而是补 JWT 覆盖不到的地方：

- Java 服务主动触发 Agent（如审批回调、状态查询）时，证明"是内部服务在调，不是外部伪造"。
- 防止有人绕过前端直接打 `/agent/**`。
- 复用网关已有的 `inner-paths` 机制。

**🔴 高风险工具双签**：过账、PLC、批量计费这类操作，审计记录同时要有：
```
发起用户 JWT（谁要求的）+ 审批用户 JWT（谁批准的）+ service key（哪个服务执行的）
```
审批关卡不能只记"Agent 自己同意了"。

**落地要点**：
- **不另起 OAuth 服务**：沿用网关的 `public.pem` + 现有 token，Agent 只是校验方，不是签发方。
- **API Key 放配置**（`nacos-config/key-config.yaml` 或环境变量），不进代码、不进 `MEMORY.md`、不进快照哈希。
- **网关加 `/agent/**` 到 inner-paths 白名单**（如果 Java→Python 要走网关）或保持 open-authorization 但允许 service token。
- **dry-run 与真实调用用同一套 JWT**：mock 回放时也要校验身份，否则验证不出越权问题。

### ADR-008 事件总线

**决策**：首版 Python **不接 RocketMQ**，代码留扩展点（`wms-agent/events/` 目录 + 空 consumer 基类），不装依赖不配置。

**理由**：问数场景本质是同步请求-响应，走 Gateway HTTP 足够；RocketMQ 的 Python 客户端生态比 Java/C++ 侧维护更差，引入后测试和部署都会增加负担；"RocketMQ 管事件"是架构分工原则，不是"每个栈现在都要接"的硬约束。

**触发条件**：等 L1/L2 场景需要异步事件（如"入库单创建完成 → Agent 分析"）时再激活，届时评估 `rocketmq-client-python` 版本。

### ADR-009 首版场景与工具范围

**决策**：首场景是 **L0 感知层的问数 Agent**（自然语言查库存/效期/看板/未上架/延时），接入 6 个只读工具：

| 优先级 | 工具 ID | 名称 | Java 端点 | 说明 |
|---|---|---|---|---|
| 1 | `STOCK-QUERY` | 库存查询 | `GET /stock/inventory-query/query-all` | 核心，最常问 |
| 2 | `EXP-WARN-QUERY` | 效期预警 | `GET /stock/expiry-warning/query-all` | Java 版，跳过 C++ 版（网关无路由） |
| 3 | `DAYCHECK-NOUP` | 收货未上架 | `GET /daycheck/no-up/get-no-up-goods` | 核心 |
| 4 | `DASH-PEND` | 待办统计 | `GET /dashboard/query-pend-*` 系列 | 核心 |
| 5 | `DASH-TREND` | 上下架 7 日趋势 | `GET /dashboard/query-goods-to-*` | 重要 |
| 6 | `DAYCHECK-DELAY` | 进货延时 | `GET /daycheck/delay/im-delay` | 重要 |

**跳过的 L0 工具**（4 个）：
- `STOCK-EXPORT`（Excel 下载，Agent 不适合做文件导出）
- `STOCK-CUS-QUERY`（客户库存报表，需要客户维度过滤，复杂）
- `DAYCHECK-YICHANG`（异常出货检查，场景复杂）
- `DASH-COST`（费用统计，涉及权限过滤，复杂）

**特别说明**：`EXP-WARN-CPP`（C++ 版效期预警）网关无路由（已在 `wms-gateway/application.yaml` 证实），跳过；Java 版 `EXP-WARN-QUERY` 底层视图（`mv_stock_yj`）相同，功能覆盖一致。

### ADR-010 LLM 选型与封装

**决策**：开发测试阶段用 **GPT-4o-mini**（用户自有 API Key），但**必须包一层 `LLMProvider`**，不让 AgentScope 直接管模型。AgentScope 的模型类放在封装后面。

**理由**：
1. **可回放验证**：harness 要求 mock LLM 回放 + 工具断言才能判 passing。直连 GPT-4o-mini 无法确定性验证。
2. **可替换**：模型厂商/型号切换只改配置，不动 Agent 代码。
3. **统一治理**：key、超时、重试、限流、成本、审计全在一处。
4. **数据边界**：库存/客户数据别裸发给外部模型——工具结果先在本地摘要/脱敏再进 prompt，或改内网模型。

**参考实现**：直接采用 Mneme-rag 的模型路由设计（多供应商档位、健康过滤、熔断降级、首包探测），在 `wms-agent/llm/` 目录下独立实现（不 import Mneme-rag 代码，因为 Mneme-rag 未接入）。

**边界**：直连 GPT-4o-mini 只适合个人 demo，不适合要进审计链的项目。

### ADR-011 状态存储

**决策**：PostgreSQL 独立 schema（`wms_agent`），跑在 Mneme-rag docker-compose 起的 PG 实例（`localhost:5432`），暂不用 pgvector。

**表设计起点**：
- `agent_sessions` - 会话主键 / 用户 ID / 创建时间 / 最近活跃
- `agent_traces` - 每次 Agent 运行的完整 trace（输入/中间步骤/输出/耗时）
- `agent_tool_calls` - 工具调用记录（关联 trace_id）

**理由**：Mneme-rag 已有 pgvector:pg16 环境（`ragent` 库），Agent 的会话/trace/状态用同一个 PG 实例但独立 schema 隔离，运维成本最低；后续如果做"历史会话语义搜索"，pgvector 现成可用；MySQL 是 Java 的主战场，Python 往 MySQL 写数据会踩 Java 的地盘；Redis 适合缓存不适合持久化；SQLite 无法多实例部署。

### ADR-012 前端集成

**决策**：全局悬浮 AI 对话框。任意页面右下角"AI 助手"按钮，点击弹出对话窗，走 SSE 流式响应。

**理由**：问数场景的价值是"在任何业务页面都能随时问"；悬浮窗组件（类似客服聊天窗）是 Vue3 常见模式；后续扩展到 L1/L2 场景（"在这批货的页面上问怎么上架"）时，悬浮窗可以带上下文（当前页面 URL / 当前选中的单据 ID）做"上下文感知问答"。

**前端改动范围**：`wms-frontend/src` 新增 `components/ai-assistant/` 组件 + `apis/agent.ts` + 在主布局组件挂载。

### ADR-013 依赖管理

**决策**：uv + `pyproject.toml` + `uv.lock`，Python 版本固定 **3.11**（AgentScope/LangGraph 兼容区间），`uv.lock` 提交进子模块。

**理由**：
- **可复现**：`uv.lock` 锁死版本，CI 和本机一致；`requirements.txt` 不锁依赖树，会漂移。
- **快、跨平台**：Windows/Git Bash 都能跑，比 poetry 轻。
- **适配 harness**：`init.sh --agent` 可以直接校验 `pyproject.toml` + lock 是否同步。

### ADR-014 配置管理

**决策**：混合——**非密配置进 Nacos（只读不注册），密钥走环境变量/`.env`**。

| 配置 | 放哪 | 例子 |
|---|---|---|
| 共享非密 | Nacos 配置中心（像 C++ 那样只读拉取） | 网关地址、模型名、超时、开关 |
| 密钥 | 环境变量 + 本地 `.env`（gitignored） | LLM API Key、服务间 API Key |

**要点**：
- `nacos-sdk-python` 只拉配置、**不注册服务**，和 C++ 行为一致。
- `.env` 不进 git、不进 `MEMORY.md`、不进快照哈希、不进日志。
- 本地开发 `.env` 兜底，生产由部署注入环境变量。
- 别把 LLM Key 写进 Nacos 明文配置——它会被快照/审计链覆盖。

### ADR-015 API 契约

**决策**：网关加静态路由（仿 C++），Python 暴露 5 个端点，响应契约沿用前端现有成功码 `10000`。

**网关路由**（`wms-gateway/application.yaml` 新增）：
```yaml
- id: agent-route
  uri: http://127.0.0.1:${sp.agent}   # 如 11200
  predicates:
    - Path=/agent/**
```

**端点（第一版）**：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/agent/health` | 健康检查 |
| GET | `/agent/tools` | 工具 Schema 列表（供验证/前端展示） |
| POST | `/agent/query` | 同步问数（主入口） |
| GET | `/agent/trace/{traceId}` | 调用审计查询 |
| POST | `/agent/scan` | 预留异步巡检，第一版不实现 |

**响应契约**（沿用前端现有成功码 `10000`，避免改 `request.js`）：

```json
{
  "code": 10000,
  "msg": "ok",
  "data": {
    "answer": "当前待上架 128 件，最多的是 A 客户…",
    "traceId": "t-20261123-001",
    "toolCalls": [
      { "tool": "DASH-PEND", "params": {}, "rowCount": 4, "durationMs": 120 }
    ],
    "createdAt": "2026-11-23T..."
  }
}
```

**`toolCalls` 是必填字段**——既给前端做溯源展示，也是验证证据。鉴权：前端走 JWT 透传；Java 直调走 service API Key。

### ADR-016 Mneme-rag 集成

**决策**：Mneme-rag 保持独立运行，Agent 微服务通过 **HTTP API** 调用它（服务间调用），不把 Mneme-rag 代码作为 Python 包引入。首版不集成，等问数 Agent 跑通后再接。

**理由**：Mneme-rag 顶层没有 `pyproject.toml` / 标准 `requirements.txt`，不是标准 Python 包，没法 `pip install`；HTTP 集成让两个服务保持独立发版节奏，不会因为 Mneme-rag 改个接口就把 Agent 服务弄坏；问数 Agent 场景根本不需要 RAG（用的是 WMS 结构化数据 + Gateway API，不是文档知识库）；Mneme-rag 的价值在"非结构化知识问答"，那是后续场景（SOP 查询、操作手册问答）。

### ADR-017 写操作策略

**决策**：工具清单里 **W 级（增删改/状态变更）也走人工确认**，Agent 默认不直接执行，生成"建议动作 + 参数"由人在前端确认后由 Java 执行。X 级（过账/PLC/批量计费）保持双签 human-in-the-loop 不变。

**理由**：现有清单允许 Agent 直接改数据（如 `IN-BIN-SET` 批量改储位、`IN-SHELF-BATCH` 批量上架），一旦 LLM 幻觉选错储位或数量，回滚成本比"人多点一下确认"高得多；制造业对"数据被 AI 擅自改动"的容忍度几乎为零；等 Agent 准确率有 trace 数据支撑后再逐步放开低风险 W 级。

**触发条件**：Agent 运行 trace 数据显示某类 W 级工具建议准确率 ≥ 95% 时，评估是否对该类工具放开"白名单自动执行 + 审计回放"模式。

---

## 4. 剩余风险

| 风险 | 应对 |
|---|---|
| 跨语言契约漂移 | 建议建立 `contracts/` 目录（或 Java 侧统一暴露 OpenAPI 文档），Python 手写 Pydantic 模型对齐；变更需双方 code review |
| Python 微服务变成"第二个 Java" | 严格限制 Python 职责：只做编排、推理、生成 + 状态持久化，不做业务规则校验 |
| Agent 幻觉导致业务事故 | W 级/X 级强制人工确认 + 双签；R 级可缓存但不做写操作 |
| Mneme-rag 版本演进冲突 | HTTP 集成（ADR-016），不 fork 魔改；需要改 Mneme-rag 时先提 PR 上游 |
| 调试困难（多模型 + 多工具 + 多步骤） | 从第一天就写 trace 到 PostgreSQL，每个 Agent 运行记录完整工具调用链和中间状态 |
| GPT-4o-mini 数据边界风险 | 工具结果在本地摘要/脱敏后再进 prompt；或后续切换内网模型（ADR-010 预留的 `LLMProvider` 抽象） |
| `EXP-WARN-CPP` 网关无路由 | 首版跳过，Java 版功能覆盖一致；后续补 C++ 网关路由时再评估 |

---

## 5. 下一步（建议实施顺序）

1. **搭骨架**：`zero-one-10wms/wms-agent/` 建立 `pyproject.toml` + `uv.lock` + `app/main.py` 最小 FastAPI 服务（`/agent/health` 通），`uv sync` 一键起环境。
2. **配网关**：`wms-gateway/application.yaml` 加 `agent-route`，验证前端能通过网关打到 Python 的 `/agent/health`。
3. **接 LLM**：`wms-agent/llm/` 实现 `LLMProvider` 抽象（先用 OpenAI 兼容客户端包 GPT-4o-mini），跑通最小对话。
4. **实现 6 个工具**：按 ADR-009 优先级逐个接入，每个工具带 Pydantic 参数模型 + Gateway 调用 + JWT 透传 + 审计写入。
5. **ReAct 循环**：AgentScope 单 Agent + 6 工具 + `LLMProvider`，SSE 流式输出（`/agent/query` 同步版先做，SSE 后加）。
6. **前端悬浮窗**：`wms-frontend/src/components/ai-assistant/` 全局组件 + `apis/agent.ts`。
7. **状态持久化**：PostgreSQL `wms_agent` schema + 3 张表（sessions/traces/tool_calls），`agent_tool_calls` 写入。
8. **harness 集成**：`init.sh` 加 `--agent` 模式，校验 `uv sync` + `uv run pytest`。

---

## 6. 状态标签

- 本文档所有决策均为**设计时决策**：`static_pass`。
- 尚无运行时验证：`runtime_unverified`。
- 下一步按第 5 节顺序逐步落地，每一步都要跑 harness 验证并写入 `feature_list.json` evidence。
