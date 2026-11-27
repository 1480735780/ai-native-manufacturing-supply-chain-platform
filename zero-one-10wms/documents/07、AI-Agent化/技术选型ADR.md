# WMS AI Agent 微服务技术选型 ADR（v1.0）

> 编制日期：2026-11-23
> 状态：**Accepted**（经 5 轮 grilling 对齐后收敛，所有决策已过用户确认）
> 参与者：用户（架构决策）+ Codex（技术调研与评审）
> 决策范围：传统 WMS（Java/C++/Vue3 三栈）之上新增 AI Agent 微服务的技术选型与架构边界
> 相关文档：`工具清单.md`（490 端点分级清单）、`zero-one-10wms/architecture.md`（三栈骨架）

***

## 0. 背景与目标

传统 WMS 功能补齐已收尾（`feature_list.json` F-001 passing，静态通过）。现在需要在 Java（业务层）/ C++（性能层）/ Vue3（前端）三栈之上，新增**Python 智能层**，将传统业务场景做 AI Agent 智能化。

**核心约束：**

- Python Agent 服务是**独立微服务**，不侵入 Java/C++ 现有代码。
- 传统业务接口（约 490 个端点）已经存在且稳定，Agent 复用它们而不是重写。
- 本项目遵循 harnessengineering 约束：所有决策需有证据、可回放验证、状态可审计。
- Mneme-rag 项目（纯 Python FastAPI + agentscope）已在父仓库，后期作为 RAG 基座接入。

***

## 1. 决策索引（一览表）

| 编号      | 主题        | 决策                                                                                           |
| ------- | --------- | -------------------------------------------------------------------------------------------- |
| ADR-001 | 代码组织      | `zero-one-10wms/wms-agent/` 目录，独立 Python 微服务                                                 |
| ADR-002 | 主框架       | AgentScope（单 Agent + ReAct 循环），多 Agent 编排后期再做                                                |
| ADR-003 | 架构拓扑      | Gateway 做唯一枢纽，三栈星型互联，不两两直连                                                                   |
| ADR-004 | 通信协议      | HTTP REST（不引入 gRPC）                                                                          |
| ADR-005 | 数据访问      | Python 只走 Gateway REST，不直读 MySQL                                                             |
| ADR-006 | 服务发现      | 不注册 Nacos，Java Feign 静态 `url="${agent.url}"` 调 Python                                        |
| ADR-007 | 认证授权      | JWT 透传 + API Key 双层；高风险工具双签                                                                  |
| ADR-008 | 事件总线      | 首版不接 RocketMQ，代码留扩展点                                                                         |
| ADR-009 | 首版场景      | 问数 Agent（L0 感知层），6 个只读工具                                                                     |
| ADR-010 | LLM 选型    | agnes-3.0-flash（开发/测试），必须包一层 `LLMProvider`                                                   |
| ADR-011 | 状态存储      | PostgreSQL 独立 schema `wms_agent`（不用 pgvector）                                                |
| ADR-012 | 前端集成      | 全局悬浮 AI 对话框                                                                                  |
| ADR-013 | 依赖管理      | uv + `pyproject.toml` + `uv.lock`，Python 3.14.7                                              |
| ADR-014 | 配置管理      | 混合：非密走 Nacos 配置中心（只读），密钥走 env/`.env`                                                         |
| ADR-015 | API 契约    | `/agent/**` 路由 + `10000` 成功码 + `toolCalls` 必填字段                                              |
| ADR-016 | Mneme-rag | HTTP 服务间调用，后期接入，不改 Mneme-rag 一行代码                                                            |
| ADR-017 | 写操作策略     | W 级（增删改/状态变更）也走人工确认，X 级双签                                                                    |
| ADR-018 | 巡检规则配置    | 版本化 YAML + 入队 canonical 快照 + worker 快照回放                                                     |
| ADR-019 | 巡检 LLM 摘要 | 只摘要不判定；输入白名单；默认关闭、快照决定；失败降级模板                                                                |
| ADR-020 | 巡检数据保留与归档 | 告警/事件/通知/摘要/扫描记录及证据在线 180 天、归档 1 年；trace 90 天删除；指标按仓库·日聚合保留 2 年；限批、可重入、外键顺序安全、默认关闭、先聚合后归档    |
| ADR-021 | 网关认证与鉴权缺口 | 实测网关无 token 全放行、资源角色不生效；巡检端点由 agent 自验并加路由级回归；平台缺口阻塞生产上线                                     |
| ADR-022 | 接口权限声明规范  | 新增 @ResourcePermission + Java 端点 baseline 静态门禁；新增接口先声明，存量分组治理、未落库、deny-unregistered 保持 false |

***

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

***

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

**理由**：Agent 服务是"被前端调用 + 调 Gateway"的边缘服务，不是被 Java 调用的核心服务，Nacos 的负载均衡和健康检查收益不大；Agent 首版是同步短请求，SSE 已后置；作为业务边缘服务，注册 Nacos 的负载均衡与健康检查收益不足。

**配置**：Java 侧 Feign 声明加 `url = "${agent.url}"`，`agent.url` 从 Nacos 配置中心 `system.yaml` 读取，固定 `agent.url: http://127.0.0.1:11200`；`sp.agent` 同步固定为 `11200`。

### ADR-007 认证授权

**决策**：两层叠加认证——**用户身份用现有 JWT，服务身份用 API Key**，两者不互相替代。

| 链路                         | 凭证                                   | 代表谁    |
| -------------------------- | ------------------------------------ | ------ |
| 前端 → 网关 → `/agent/**`      | **复用现有 JWT**（`/login/auth-login` 那套） | 用户本人   |
| Java → Python（内部调用）        | **API Key / service token**          | 调用方服务  |
| Python → 网关 → 工具（Java/C++） | **透传用户 JWT**                         | 仍是用户本人 |

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
- **Python 侧自己也验 JWT（2026-11-23 Round 3 修正）**：
  - 服务默认绑定 `127.0.0.1:11200`，不绑 `0.0.0.0`；
  - `/agent/query` 等业务端点用 `public.pem` 校验 RS256 签名与 `exp`，身份只取 JWT claims；
  - 网关下发的 `user` header 只作交叉校验，不作为身份权威，防止本机进程伪造；
  - Python 首版不查 Redis 注销黑名单；已登出 token 在过期前直连 Python 仍可能通过签名校验，需记为剩余风险。
- **网关放行目标（2026-11-23 Round 3 确定）**：
  1. `nacos-config/system.yaml` 先加 `sp.agent: 11200`，并同步真实 Nacos 的 `system.yaml`；
  2. `/agent/health` 加入 `white-paths`，响应只返回 `{"status":"ok"}`，不泄露版本、依赖或存储状态；
  3. `/agent/query`、`/agent/tools`、`/agent/trace/**` 加入 `inner-paths`；通配符行为必须在真实网关实测；
  4. 最后才新增 `agent-route`。实测被拦则 F-007 记 `blocked`，不改权限表、不改 `open-authorization`、不绕过网关。
- **`TokenExtendsValidateImpl.java:31` 的 `realToekn` 是死代码**，只登记为 known issue，待网关模块可编译时顺手清理；不作为 F-007 前置修复，不因纯重构阻塞功能。
- **Nacos 配置必须保持纯 ASCII（2026-11-23 实测新增）**：Windows 下 Nacos 客户端用平台默认字符集（GBK）解码配置内容，Spring Cloud Alibaba 的 YAML 解析器遇到非 ASCII 字节会抛 `MalformedInputException`，**整个 `system.yaml` 属性源被静默清空**——表现为 `${sp.agent}` 等占位符不解析、网关路由 URI 构造失败（HTTP 500，`Expected scheme-specific part at index 5: http:`）。因此 `nacos-config/system.yaml` 样例与真实 Nacos 的 `system.yaml` 一律只写 ASCII 注释；中文说明放仓库文档，不放 Nacos。
- **dry-run 与真实调用用同一套 JWT**：mock 回放时也要校验身份，否则验证不出越权问题。

### ADR-008 事件总线

**决策**：首版 Python **不接 RocketMQ**，代码留扩展点（`wms-agent/events/` 目录 + 空 consumer 基类），不装依赖不配置。

**理由**：问数场景本质是同步请求-响应，走 Gateway HTTP 足够；RocketMQ 的 Python 客户端生态比 Java/C++ 侧维护更差，引入后测试和部署都会增加负担；"RocketMQ 管事件"是架构分工原则，不是"每个栈现在都要接"的硬约束。

**触发条件**：等 L1/L2 场景需要异步事件（如"入库单创建完成 → Agent 分析"）时再激活，届时评估 `rocketmq-client-python` 版本。

### ADR-009 首版场景与工具范围

**决策**：首场景是 **L0 感知层的问数 Agent**（自然语言查库存/效期/看板/未上架/延时），接入 6 个只读工具：

| 优先级 | 工具 ID            | 名称        | Java 端点                                | 说明                     |
| --- | ---------------- | --------- | -------------------------------------- | ---------------------- |
| 1   | `STOCK-QUERY`    | 库存查询      | `GET /stock/inventory-query/query-all` | 核心，最常问                 |
| 2   | `EXP-WARN-QUERY` | 效期预警      | `GET /stock/expiry-warning/query-all`  | Java 版，跳过 C++ 版（网关无路由） |
| 3   | `DAYCHECK-NOUP`  | 收货未上架     | `GET /daycheck/no-up/get-no-up-goods`  | 核心                     |
| 4   | `DASH-PEND`      | 待办统计      | `GET /dashboard/query-pend-*` 系列       | 核心                     |
| 5   | `DASH-TREND`     | 上下架 7 日趋势 | `GET /dashboard/query-goods-to-*`      | 重要                     |
| 6   | `DAYCHECK-DELAY` | 进货延时      | `GET /daycheck/delay/im-delay`         | 重要                     |

**跳过的 L0 工具**（4 个）：

- `STOCK-EXPORT`（Excel 下载，Agent 不适合做文件导出）
- `STOCK-CUS-QUERY`（客户库存报表，需要客户维度过滤，复杂）
- `DAYCHECK-YICHANG`（异常出货检查，场景复杂）
- `DASH-COST`（费用统计，涉及权限过滤，复杂）

**特别说明**：`EXP-WARN-CPP`（C++ 版效期预警）网关无路由（已在 `wms-gateway/application.yaml` 证实），跳过；Java 版 `EXP-WARN-QUERY` 底层视图（`mv_stock_yj`）相同，功能覆盖一致。

### ADR-009.1 工具适配层契约（2026-11-23 新增）

6 个 Java 端点的**参数命名与返回结构不一致**（2026-11-23 逐条核实），差异全部在 **Python 适配层消化**，**不修改 Java 业务端点**。

**① 参数命名两套并存**（LLM 只看适配层暴露的统一 schema）：

| 工具                         | 端点参数命名                                                                                           | 关键差异                     |
| -------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------ |
| `STOCK-QUERY`              | 驼峰：`pageIndex/pageSize/kuWeiBianMa/binId/cusCode/zhongWenQch/goodsCode/shpMingCheng`             | 商品编码叫 `goodsCode`        |
| `EXP-WARN-QUERY`           | 驼峰：`pageIndex/pageSize/cusCode/zhongWenQch/goodsId/shpMingCheng`                                 | 商品编码叫 `goodsId`（与上一条不同名） |
| `DAYCHECK-NOUP`            | **下划线**：`bin_id/tin_id/cus_code/zhong_wen_qch/goods_id/shp_ming_cheng` + 驼峰 `pageIndex/pageSize` | 一套里两种风格混用                |
| `DASH-PEND` / `DASH-TREND` | 无业务查询参数（仅 `count`，默认 6 / 7，范围 1..30）                                                             | 超出范围 → `9994 请求参数过大`     |
| `DAYCHECK-DELAY`           | 无查询类，仅必填 `pageIndex/pageSize`                                                                    | 缺参 → `9995 参数值缺失`        |

**② 返回结构三态**（适配层统一为 `{rows, total}`）：

| 工具               | 原始返回                              | 空数据表现                                                                                                      |
| ---------------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `STOCK-QUERY`    | `JsonVO<PageDTO<WvStockDTO>>`     | `data.rows == null`（`PageDTO.create(page,callback)` 仅非空时 setRows，`PageDTO.java:90-101`）                    |
| `EXP-WARN-QUERY` | `JsonVO<PageDTO<MvStockYj>>`      | `data.rows == []`（`PageDTO.create(page)` `:63-71`）                                                         |
| `DAYCHECK-NOUP`  | `JsonVO<List<NoUpGoodsDTO>>`      | `data == []`，**无 total**（裸 List）                                                                           |
| `DAYCHECK-DELAY` | `JsonVO<PageDTO<WaringAllDTO>>`   | `data.rows == null`                                                                                        |
| `DASH-PEND`      | `JsonVO<GoodsPendingVO>`（4 个端点各一） | 不报错，`goodsNumber="0"`                                                                                      |
| `DASH-TREND`     | `JsonVO<List<...>>`（4 个端点各一）      | **`code=9999`（FAIL，「查询数据不存在」）、`data=null`**（`DashboardController.java:104-106/:174-176/:192-194/:212-214`） |

**适配规则**：

- `code=9999` 对 `DASH-TREND` 属于**业务"无数据"**，不是失败 → 适配层转成空结果，禁止向 LLM 报"查询失败"。
- `9999` 结果有约 2 分钟 Redis 缓存（`WmToUpGoodsServiceImpl.java:52-64/:79-88`，空列表也缓存）→ 修复后重查仍可能 9999，属预期。
- `rows == null` 与 `rows == []` 在适配层统一成 `[]`；`DAYCHECK-NOUP` 的裸 List 无 total，适配层置 `total = len(rows)`。
- `DAYCHECK-NOUP` 的 `pageIndex/pageSize` **实际必填**（类级 `@Validated` + `@Min(1)`，缺省 → `9995 "[pageIndex]页码最小值为1"`；`NoUpServiceImpl.java:32` 直接 `new Page<>(...)`）；其 Mapper 用 `=` 精确匹配（`NoUpMapper.xml:26-43`），而 stock/expiry 侧用 `like` → 参数语义必须写进 Tool Schema 描述，避免 LLM 误以为模糊匹配。

**③ 错误码语义**（供适配层判定"重试/报错/空结果"）：`10000` 成功；`9995` 参数非法（文案 `[字段]说明`）；`9994` 运行时异常（文案在 `data`）；`9999` 业务无数据。来源：各模块 `GlobalExceptionHandler.java:37-42/:74-95`、`ResultStatus.java:21-22`。

### ADR-010 LLM 选型与封装

**决策**：开发测试阶段用 **agnes-3.0-flash**（用户自有 API Key，Agnes OpenAI 兼容接口），但**必须包一层 `LLMProvider`**，不让 AgentScope 直接管模型。AgentScope 的模型类放在封装后面。

**理由**：

1. **可回放验证**：harness 要求 mock LLM 回放 + 工具断言才能判 passing。直连 agnes-3.0-flash 无法确定性验证。
2. **可替换**：模型厂商/型号切换只改配置，不动 Agent 代码。
3. **统一治理**：key、超时、重试、限流、成本、审计全在一处。
4. **数据边界**：库存/客户数据别裸发给外部模型——工具结果先在本地摘要/脱敏再进 prompt，或改内网模型。

**参考实现**：直接采用 Mneme-rag 的模型路由设计（多供应商档位、健康过滤、熔断降级、首包探测），在 `wms-agent/llm/` 目录下独立实现（不 import Mneme-rag 代码，因为 Mneme-rag 未接入）。

**边界**：直连 agnes-3.0-flash 只适合个人 demo，不适合要进审计链的项目。

**Agnes 配置（2026-11-23 更新）**：

- OpenAI 兼容 Base URL：`https://api.agnes-ai.cn/v1`；
- 模型名：`agnes-3.0-flash`；
- API Key 只放运行环境或本地 gitignored `.env`，禁止写入代码、文档、fixture、Nacos、日志、快照或 `MEMORY.md`；
- 已在聊天中暴露过的 API Key 不允许直接进入仓库，应先在 Agnes 控制台轮换后再配置本地 `.env`。

**执行预算（2026-11-23 Round 3 确定）**：前端独立 axios 实例 `timeout=60000`；服务端端到端软目标 ≤15 秒；LLM 单轮 8 秒；单工具 3 秒；工具调用轮数硬上限 **2 轮**。第 2 轮工具结果返回后强制进入最终答案生成，禁止无限 ReAct。

### ADR-011 状态存储

**决策**：PostgreSQL 独立 schema（`wms_agent`），跑在 Mneme-rag docker-compose 起的 PG 实例上（镜像 `pgvector/pgvector:pg16`，库 `ragent`），暂不用 pgvector。

**部署形态（2026-11-23 确定）**：PG 跑在**虚拟机**的 docker 里，`docker compose up -d`（整套 `Mneme-rag/docker/docker-compose.yml`：postgres/redis/minio/neo4j/lightrag）。Agent 只依赖 `postgres` 服务，其余服务与问数场景无关，但整套起可保证与 Mneme-rag 后续集成（ADR-016）时环境一致；`lightrag` 需要在该 compose 同目录的 `.env` 里配 `DASHSCOPE_API_KEY`（`docker-compose.yml:119-120`），否则该服务起不来（不影响 Agent）。

**连接地址不再硬编码 `localhost`**：Agent 跑在 Windows 宿主机、PG 跑在虚拟机 → 必须用 `<VM-IP>:5432`。连接串走环境变量：

```
WMS_AGENT_DB_URL=postgresql+psycopg://postgres:postgres@<VM-IP>:5432/ragent
```

（`.env` 本地保存、不入库；生产由部署注入。）

**表设计起点**：

- `agent_sessions` - 会话主键 / 用户 ID / 创建时间 / 最近活跃
- `agent_traces` - 每次 Agent 运行的完整 trace（输入/中间步骤/输出/耗时）
- `agent_tool_calls` - 工具调用记录（关联 trace\_id）

**降级边界（Simplicity First）**：**PG 不可用时不阻塞服务启动**——`/agent/health`、`/agent/tools` 正常可用，`/agent/query` 降级为"无持久化只读问数"（trace 只进内存/日志，不落库），并在响应中标注 `persisted=false`。落库失败只记日志，不让问数失败。

**理由**：Mneme-rag 已有 pgvector:pg16 环境（`ragent` 库），Agent 的会话/trace/状态用同一个 PG 实例但独立 schema 隔离，运维成本最低；后续如果做"历史会话语义搜索"，pgvector 现成可用；MySQL 是 Java 的主战场，Python 往 MySQL 写数据会踩 Java 的地盘；Redis 适合缓存不适合持久化；SQLite 无法多实例部署。

### ADR-012 前端集成

**决策**：全局悬浮 AI 对话框。任意页面右下角"AI 助手"按钮，点击弹出对话窗。

**首版同步优先，流式（SSE）后置（2026-11-23 修正）**：首版只做**同步** `/agent/query`——前端"提问 → loading → 最终答案 + 工具溯源"。理由：浏览器原生 `EventSource` **不能带 `Authorization` 头**，改用 query 参数传 token 会让 token 落到 URL 与网关审计日志；改用 `fetch` + `ReadableStream` 读 SSE 可以带 header，但属于额外机制，首版不值得为它承担联调风险（且与 F-004 的运行时基线未就绪叠加）。

**超时约定**：前端 `src/plugins/http.js:8` 的全局 `timeout = 10000` 对 LLM 多步 ReAct 必超时 → `/agent/query` 用**独立 axios 实例**（`timeout: 60000`），**不改全局默认值**，避免影响既有 100+ 个业务请求；该实例必须显式展示 Agent 错误，不复用 `http.js` 的静默 default 分支。

**理由**：问数场景的价值是"在任何业务页面都能随时问"；悬浮窗组件（类似客服聊天窗）是 Vue3 常见模式；后续扩展到 L1/L2 场景（"在这批货的页面上问怎么上架"）时，悬浮窗可以带上下文（当前页面 URL / 当前选中的单据 ID）做"上下文感知问答"。

**前端改动范围**：`wms-frontend/src` 新增 `components/ai-assistant/` 组件 + `apis/agent.ts` + 在主布局组件挂载。成功码约定沿用前端现有 `{code:10000, message, data}`（`src/plugins/http.js:43/:91/:121/:125`，**不是** ADR 早期稿里的 `request.js`——全仓无此文件）。

### ADR-013 依赖管理

**决策**：uv + `pyproject.toml` + `uv.lock`，Python 版本固定 **3.14.7**（2026-11-23 Round 3 按本机系统环境修订；`requires-python = ">=3.14,<3.15"`），`uv.lock` 提交进仓库。

**本机解释器与缓存**：

- 解释器固定 `D:/DownloadPackage/environment/python.exe`（当前实测 3.14.7）；
- uv cache 固定项目内 `.uv/cache`，避免用户级 cache 权限/损坏问题；
- AgentScope 在 F-010 才引入；引入前必须先跑 Python 3.14 兼容性探针，不兼容则 F-010 记 `blocked`，不悄悄降级解释器。

**理由**：

- **可复现**：`uv.lock` 锁死版本，CI 和本机一致；`requirements.txt` 不锁依赖树，会漂移。
- **快、跨平台**：Windows/Git Bash 都能跑，比 poetry 轻。
- **适配 harness**：`init.sh --agent` 可以直接校验 `pyproject.toml` + lock 是否同步。

### ADR-014 配置管理

**决策**：混合——**非密配置进 Nacos（只读不注册），密钥走环境变量/`.env`**。

| 配置   | 放哪                           | 例子                      |
| ---- | ---------------------------- | ----------------------- |
| 共享非密 | Nacos 配置中心（像 C++ 那样只读拉取）     | 网关地址、模型名、超时、开关          |
| 密钥   | 环境变量 + 本地 `.env`（gitignored） | LLM API Key、服务间 API Key |

**要点**：

- `nacos-sdk-python` 只拉配置、**不注册服务**，和 C++ 行为一致。
- `.env` 不进 git、不进 `MEMORY.md`、不进快照哈希、不进日志。
- 本地开发 `.env` 兜底，生产由部署注入环境变量。
- 别把 LLM Key 写进 Nacos 明文配置——它会被快照/审计链覆盖。

### ADR-015 API 契约

**决策**：网关加静态路由（仿 C++），Python 暴露 5 个端点；除匿名健康检查外，业务响应契约沿用前端现有成功码 `10000`。

**网关路由**（`wms-gateway/application.yaml` 新增）：

```yaml
- id: agent-route
  uri: http://127.0.0.1:${sp.agent}   # 如 11200
  predicates:
    - Path=/agent/**
```

**端点（第一版）**：

| 方法   | 路径                       | 用途                           |
| ---- | ------------------------ | ---------------------------- |
| GET  | `/agent/health`          | 匿名健康检查，仅返回 `{"status":"ok"}` |
| GET  | `/agent/tools`           | 工具 Schema 列表（供验证/前端展示）       |
| POST | `/agent/query`           | 同步问数（主入口）                    |
| GET  | `/agent/trace/{traceId}` | 调用审计查询                       |
| POST | `/agent/scan`            | 预留异步巡检，第一版不实现                |

**响应契约**（沿用前端现有成功码 `10000`；字段名沿用 `JsonVO` 的 `code/message/data`）：

```json
{
  "code": 10000,
  "message": "ok",
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

**请求契约（2026-11-23 Round 3 确定）**：

```json
{
  "query": "当前待上架多少件？",
  "sessionId": null
}
```

`query` 必填；`sessionId` 可选，缺省由服务端生成。**`sessionId` 仅用于 trace 分组，v1 不加载历史上下文**；不预留 `context` 字段。

**字段名以 `JsonVO` 为准（2026-11-23 修正）**：`wms-domain/.../vo/JsonVO.java:22-39` 的字段是 `code`(`:27`)、`message`(`:33`)、`data`(`:39`)，工厂 `create(data, code, message)` 在 `:72-78`；前端 `src/plugins/http.js` 读 `code`(`:91`)、`message`(`:121/:125`)、成功码常量 `10000`(`:43`)。早期稿写的 `msg` **是错的**：只返 `msg` 会让前端拦截器拿不到文案。**Python 侧必须返回 `message`**；Java 端点与前端 `http.js` 都不改。

**`toolCalls` 是必填字段**——既给前端做溯源展示，也是验证证据。鉴权：前端走 JWT 透传；Java 直调走 service API Key。

### ADR-016 Mneme-rag 集成

**决策**：Mneme-rag 保持独立运行，Agent 微服务通过 **HTTP API** 调用它（服务间调用），不把 Mneme-rag 代码作为 Python 包引入。首版不集成，等问数 Agent 跑通后再接。

**理由**：Mneme-rag 顶层没有 `pyproject.toml` / 标准 `requirements.txt`，不是标准 Python 包，没法 `pip install`；HTTP 集成让两个服务保持独立发版节奏，不会因为 Mneme-rag 改个接口就把 Agent 服务弄坏；问数 Agent 场景根本不需要 RAG（用的是 WMS 结构化数据 + Gateway API，不是文档知识库）；Mneme-rag 的价值在"非结构化知识问答"，那是后续场景（SOP 查询、操作手册问答）。

### ADR-017 写操作策略

**决策**：工具清单里 **W 级（增删改/状态变更）也走人工确认**，Agent 默认不直接执行，生成"建议动作 + 参数"由人在前端确认后由 Java 执行。X 级（过账/PLC/批量计费）保持双签 human-in-the-loop 不变。

**理由**：现有清单允许 Agent 直接改数据（如 `IN-BIN-SET` 批量改储位、`IN-SHELF-BATCH` 批量上架），一旦 LLM 幻觉选错储位或数量，回滚成本比"人多点一下确认"高得多；制造业对"数据被 AI 擅自改动"的容忍度几乎为零；等 Agent 准确率有 trace 数据支撑后再逐步放开低风险 W 级。

**触发条件**：Agent 运行 trace 数据显示某类 W 级工具建议准确率 ≥ 95% 时，评估是否对该类工具放开"白名单自动执行 + 审计回放"模式。

***

### ADR-018 巡检规则配置

**决策**：异常巡检非密规则使用版本化 `wms-agent/config/scan.yaml`，作为 ADR-014 的有意例外。启动时校验并归一为 canonical JSON；入队冻结 `config_snapshot/config_hash/config_version`；worker 只按快照执行，不读取当前 YAML。阈值、路由、通知与调度进入哈希，密钥仍只走环境变量或本地 `.env`。完整说明见 `ADR-018-巡检规则配置.md`。

### ADR-019 巡检 LLM 摘要边界

**决策**：异常巡检的 LLM 只做人读摘要与建议动作文案，不参与存在性、级别、对象与证据的判定（这些由规则引擎决定）。输入只送按 `rule_id + warehouse + customer` 聚合后的白名单字段，不送原始行与个人敏感信息；输出做 schema 校验与清洗，建议动作只展示不执行（ADR-017）。`llm.enabled` 默认关闭并进入配置快照与哈希（ADR-018），worker 只按快照决定是否调用；超时、超限、输出不合规一律降级为确定性模板，LLM 任何失败都不改变告警落库与扫描结果。完整说明见 `ADR-019-巡检LLM摘要边界.md`。

### ADR-020 巡检数据保留与归档

**决策**：已结案告警、事件、通知、扫描摘要、扫描记录及其证据（评估覆盖、命中观测、积压样本）在线保留 180 天，之后转入单表 JSONB 归档表保留 1 年；扫描记录只处理终态、`queued/running` 永不归档，并连同证据按父扫描整批归档；问数 trace/工具调用 90 天后直接删除。指标按「仓库·日」滚动聚合并保留 2 年：90 天内读实时、90 天至 2 年读日聚合（响应带 `mode=dailyRollup` 与 `coverage`）、超过 2 年不返回，归档不再让历史指标消失。清理按外键顺序（先子后父）分七步执行，每批限行、`FOR UPDATE SKIP LOCKED`、逐批提交，可重入；保留参数是运维参数，走环境配置而不进入配置快照（与 ADR-018 的对照见单独文件）。自动任务默认关闭，每日先补齐日聚合再归档，补不齐则跳过归档；当天失败不重试。完整说明见 `ADR-020-巡检数据保留与归档.md`。

### ADR-021 网关认证与鉴权缺口（生产上线阻塞）

**决策**：实测运行中的网关对无 token 的请求（任意方法、任意路径）直接转发，资源角色（`AUTH:RESOURCE_ROLES`）对已登录的错误角色也不生效，唯一生效的是「带 token 时必须能解析为 JWT 且未登出」。巡检端点 `/agent/**` 不依赖网关：agent 自己验签、验过期并逐端点校验角色与仓库范围，并由路由级回归固化（巡检路由表逐条对五种不可信凭据返回 401）。平台级缺口登记为生产上线阻塞项，本任务不改网关，修复方案与回归要求见单独文件。

### ADR-022 接口权限声明规范

**决策**：在 `wms-common` 新增 `@ResourcePermission(roles=..., allowPublic=...)`，作为接口权限的显式声明与审查契约；注解不自动改库或刷缓存。新增 Java HTTP 端点必须在 baseline 之外带该注解或等价 Spring Security 声明，否则 `init.sh --quick` 失败。当前 baseline 收录 349 个存量端点，518 条前端未登记路径只形成分组草案，未落库；`deny-unregistered` 保持 false。完整规则、迁移与审计模式见 `ADR-022-接口权限声明规范.md`。

## 4. 剩余风险

| 风险                                     | 应对                                                                                      |
| -------------------------------------- | --------------------------------------------------------------------------------------- |
| 跨语言契约漂移                                | 建议建立 `contracts/` 目录（或 Java 侧统一暴露 OpenAPI 文档），Python 手写 Pydantic 模型对齐；变更需双方 code review |
| Python 微服务变成"第二个 Java"                 | 严格限制 Python 职责：只做编排、推理、生成 + 状态持久化，不做业务规则校验                                              |
| Agent 幻觉导致业务事故                         | W 级/X 级强制人工确认 + 双签；R 级可缓存但不做写操作                                                         |
| Mneme-rag 版本演进冲突                       | HTTP 集成（ADR-016），不 fork 魔改；需要改 Mneme-rag 时先提 PR 上游                                      |
| 调试困难（多模型 + 多工具 + 多步骤）                  | 从第一天就写 trace 到 PostgreSQL，每个 Agent 运行记录完整工具调用链和中间状态                                     |
| agnes-3.0-flash 外部模型数据边界风险             | 工具结果在本地摘要/脱敏后再进 prompt；或后续切换内网模型（ADR-010 预留的 `LLMProvider` 抽象）                          |
| 巡检 LLM 摘要质量未用真实模型评估                    | 模型只写摘要不判定，失败降级模板（ADR-019）；`llm.enabled` 默认关闭，模型可用后再开并补质量评估                              |
| 巡检指标日聚合只回看最近 180 天补算                   | 更早的日期不补算；超过 90 天的长窗口查询在 `coverage.missingDays` 中如实暴露缺算天数，不给出貌似完整的数字（ADR-020 第 3.1 节）    |
| 网关无 token 全放行、资源角色不生效（实测，影响全部 Java 服务） | **阻塞生产上线**（ADR-021）；巡检端点由 agent 自验并有路由级回归；平台侧按 ADR-021 第 5 节修复并补网关契约测试后才能上线             |
| `EXP-WARN-CPP` 网关无路由                   | 首版跳过，Java 版功能覆盖一致；后续补 C++ 网关路由时再评估                                                      |
| Python 不查 Redis 注销黑名单                  | 服务只绑 loopback，正常流量先过网关；已登出 token 在 JWT 过期前直连 Python 仍是理论风险                              |
| AgentScope 与 Python 3.14 兼容性未实测        | F-010 引入前先跑 import/最小构造探针；失败则 blocked，不降级解释器                                            |
| JWT 签发私钥明文存在于仓库历史                      | 独立安全问题，不在问数 Agent 范围内修；后续轮换密钥、清理历史并补充忽略规则                                               |

***

## 5. 下一步（建议实施顺序）

1. **搭骨架**：`zero-one-10wms/wms-agent/` 建立 `pyproject.toml` + `uv.lock` + `app/main.py` 最小 FastAPI 服务（`/agent/health` 通），`uv sync --python D:/DownloadPackage/environment/python.exe` 一键起环境（Python 3.14.7）。
2. **配网关**：`wms-gateway/application.yaml` 加 `agent-route`，验证前端能通过网关打到 Python 的 `/agent/health`。
3. **接 LLM**：`wms-agent/llm/` 实现 `LLMProvider` 抽象（先用 Agnes OpenAI 兼容接口接入 agnes-3.0-flash），跑通最小对话。
4. **实现 6 个工具**：按 ADR-009 优先级逐个接入，每个工具带 Pydantic 参数模型 + Gateway 调用 + JWT 透传 + 审计写入。
5. **ReAct 循环**：AgentScope 单 Agent + 6 工具 + `LLMProvider`，**首版只做同步 `/agent/query`**（SSE 流式后置，见 ADR-012 修正）。
6. **前端悬浮窗**：`wms-frontend/src/components/ai-assistant/` 全局组件 + `apis/agent.ts`。
7. **状态持久化**：PostgreSQL `wms_agent` schema + 3 张表（sessions/traces/tool\_calls），`agent_tool_calls` 写入。
8. **harness 集成**：`init.sh` 加 `--agent` 模式，校验 `uv sync` + `uv run pytest`。

***

## 6. 状态标签

- 本文档所有决策均为**设计时决策**：`static_pass`。
- 尚无运行时验证：`runtime_unverified`。
- 下一步按第 5 节顺序逐步落地，每一步都要跑 harness 验证并写入 `feature_list.json` evidence。
