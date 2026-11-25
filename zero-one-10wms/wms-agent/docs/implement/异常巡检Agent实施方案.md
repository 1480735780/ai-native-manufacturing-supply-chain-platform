# 异常巡检 Agent 实施方案（v0.2.0 / v0.2.1）

> 编制日期：2026-11-24  
> 状态：**设计已对齐，待实施**（Round 1~3 grilling 结论）  
> 适用版本：v0.2.0（效期、收货未上架、进货延时、待办积压）+ v0.2.1（出货异常、温度）  
> 事实源：`docs/业务分析/异常巡检agent业务背景.md`、`docs/07、AI-Agent化/技术选型ADR.md`、现有 `wms-agent` 代码  
> 边界：本文是实施方案，不代表功能已完成；所有 `passing` 仍需按 `feature_list.json` 的验证步骤补 evidence。

---

## 0. 结论摘要

1. **复用现有 `wms-agent` 进程**，新增 `app/scan/` 模块与 `/agent/scan` 路由，不新建微服务，不改问数 Agent 的 `/agent/query` 行为。
2. **v0.2.0 先做四类**：效期、收货未上架、进货延时、待办积压；**v0.2.1 再做出货异常、温度**，两批分开验收。
3. **异常判定完全由确定性规则完成**；LLM 只生成摘要和建议动作，不得改变“是否存在 / 级别”。
4. **手动巡检 + 内部定时巡检**，不接 RocketMQ；`POST /agent/scan` 异步返回 `202 + scanId`。
5. **无人值守使用 Java 侧 `service-token` + 只读服务账号**；不关闭验证码、不伪造 JWT、不使用管理员 token。
6. **告警生命周期四态**：`open → acknowledged → resolved | ignored`；复发新建，不做 `reopened`。
7. **通知走 Agent 自有 `in_app` 通道**：前端巡检页 + 30s 轮询；不写 Java 公告表。
8. **存储新增四张表**：`agent_scan_runs`、`agent_alerts`、`agent_alert_events`、`agent_notifications`，均在 `wms_agent` schema。
9. **规则配置走版本化 YAML**，入队冻结 `config_snapshot/config_hash/config_version`，worker 只按快照回放；这是对 ADR-014 的有意例外，已由 ADR-018 记录。
10. **Java 侧有前置项**：`service-token`、`sort=oldest`、`insp_read` 角色、菜单/资源种子、必要索引。Java 未完成时，对应能力必须标 `blocked`，不能靠绕过鉴权或伪造数据通过。

---

## 1. 背景、目标与非目标

### 1.1 业务背景

异常巡检 Agent 面向仓储运营中的“异常发现与前置处置”：系统按班次主动检查已经发生但尚未处理、以及即将发生但尚可干预的业务异常，形成带证据链、分级、责任人和建议动作的告警清单，推送到对应岗位并跟踪关闭。

现状问题：

- 预警管理只有“查”，没有主动巡检；
- 六类异常分散在预警管理、每日检查、系统首页；
- 依赖导出 Excel 和人工比对；
- 无分级、无去重、无生命周期；
- 夜班/周末无人主动查看；
- 告警缺少证据链、责任路由和闭环度量。

### 1.2 目标

1. 从“人找异常”转为“异常找人”。
2. 每条告警带证据链：来源单据、关键字段、命中规则、发现时间、traceId。
3. 建立告警生命周期：待处理、处理中、已关闭、已忽略。
4. 风险前置：按剩余天数/剩余时长排序，给出优先级。
5. 可配置、可降级：模型不可用时用模板，保证不漏报。
6. 只读安全边界：不修改业务数据，建议动作由人在原页面执行。

### 1.3 非目标

- 不做任何业务写操作（不改储位、不上架、不过账、不改温度主数据）。
- 不替代原有业务页面，只做发现、提醒、跟踪。
- 不做 NL2SQL，不直读 MySQL。
- 不接 RocketMQ 事件总线。
- 不做 SSE / WebSocket 推送；v0.2 用 30 秒轮询。
- 不做动态组织架构解析；责任人先用 YAML 映射。
- 不做商品级温度属性 join；v0.2.1 只做地点级阈值。
- 不把 v0.2.0 与 v0.2.1 混在一次通过结论里。

---

## 2. 版本范围与交付批次

| 批次 | 异常类型 | 数据源 | 新增工具 | 验收重点 |
|---|---|---|---|---|
| **v0.2.0** | 效期 | `/stock/expiry-warning/query-all` | 复用 v0.1 只读工具 | 已验证链路 + 新规则 |
| **v0.2.0** | 收货未上架 | `/daycheck/no-up/get-no-up-goods` | 复用 v0.1 只读工具 | 已验证链路 + 新规则 |
| **v0.2.0** | 进货延时 | `/daycheck/delay/im-delay` | 复用 v0.1 只读工具 | 已验证链路 + 新规则 |
| **v0.2.0** | 待办积压 | `/dashboard/query-pend-*`、`/query-cur-pick` | 复用 v0.1 只读工具 | 历史基线 + 新规则 |
| **v0.2.1** | 出货异常 | `/daycheck/yi-chang/get-yichang-down` | 新增 1 个工具 | 新端点 + 老化规则 |
| **v0.2.1** | 温度 | `/daycheck/temperature/query` | 新增 1 个工具 | 人工录入语义 + 地点阈值 |

**交付原则**：v0.2.0 只允许“已验证链路 + 新规则”；v0.2.1 单独验收，不把未验证风险带进 v0.2.0 的通过结论。

---

## 3. 总体架构

### 3.1 运行视图

```text
┌──────────────────────────────┐
│ Vue3 巡检页 / AI 助手角标     │
│ 30s 轮询 /agent/alerts       │
└──────────────┬───────────────┘
               │ JWT
               ▼
┌──────────────────────────────┐
│ wms-gateway                  │
│ /agent/** 静态路由            │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ wms-agent (FastAPI)          │
│ app/scan/                    │
│  router / service / scheduler│
│  rules / sources / repository│
│  notifications               │
└───┬──────────┬──────────┬────┘
    │          │          │
    ▼          ▼          ▼
 Java REST   PostgreSQL   LLMProvider
 (只读)      wms_agent    (仅摘要)
```

### 3.2 模块划分

```text
wms-agent/app/scan/
  __init__.py
  router.py              # /agent/scan, /agent/scans, /agent/alerts
  service.py             # 编排：取数 → 规则 → 告警 → 通知
  scheduler.py           # 默认关闭的内部定时器
  schemas.py             # 请求/响应 Pydantic 模型
  repository.py          # 四张表的访问
  lock.py                # PG advisory lock + running 唯一约束
  rules/
    __init__.py
    base.py              # Rule / Finding / RuleContext
    expiry.py            # EXP-EXPIRED / EXP-NEAR
    no_up.py             # NOUP-OVERDUE
    delay.py             # DELAY-OVERDUE
    backlog.py           # BACKLOG-GROWTH
    temperature.py       # v0.2.1
    outbound.py          # v0.2.1
  sources/
    __init__.py
    base.py              # 分页、超时、partial、排序
    expiry.py
    no_up.py
    delay.py
    backlog.py
    temperature.py       # v0.2.1
    outbound.py          # v0.2.1
  notifications/
    __init__.py
    in_app.py            # Agent 自有通道
    dry_run.py           # 短信/邮件影子记录
    templates.py
  llm/
    __init__.py
    summarizer.py        # 只摘要，不判定
```

**复用现有能力**：

- `app/llm/provider.py`：`LLMProvider`、真实 OpenAI 兼容实现、mock 回放；
- `app/tools/gateway_client.py`：Gateway HTTP client；
- `app/agent/trace.py`：`TraceCollector` 的审计思想；
- `app/security.py`：JWT 验签；
- `app/storage/postgres.py`：PG 连接与 schema 管理；
- `app/config.py`：Settings 扩展。

**不修改**：

- `/agent/query` 的请求/响应契约；
- 问数 Agent 的 6 个工具行为；
- 前端 AI 助手现有交互。

---

## 4. Java 侧前置项（必须单列）

异常巡检不是纯 Python 工程。以下 Java 侧改动未完成时，对应能力必须标 `blocked`。

### 4.0 2026-11-24 前置项落地状态

- `POST /login/service-token`：已实现；经网关 200，`expiresIn=1800`，`roles=[insp_read]`，`warehouseScope=[W01]`。
- `insp_read` 角色：已创建；`agent-inspector` 已绑定；注意数据库 `rolecode` 只有 `varchar(10)`，不能使用 `INSPECTION_READ`。
- 菜单：`MENU-DAILY-CHECK-05` 已创建并挂到 `MENU-DAILY-CHECK`；已映射 `ckjl/cg/gly`。`ckjl` 当前 0 用户，实际可见主要来自 `cg/gly`。
- 索引：`idx_wm_in_qm_i_create_date`、`idx_wm_im_notice_h_im_data`、`idx_wm_to_down_goods_create_date` 已创建。
- `sort=oldest`：已实现并实测；无 sort 保持 delay 新→旧；`sort=oldest` 按 `im_data` 升序；非法 sort 返回 9995。
- 服务账号 JWT：已实测可调用 no-up、delay、expiry、dashboard 4 个计数端点。

### 4.1 `POST /login/service-token`

用途：无人值守巡检获取短时 JWT，不关闭验证码。

契约：

```http
POST /login/service-token
X-Agent-Api-Key: <from env>
X-Agent-Key-Id: <key id>
X-Agent-Warehouse: <optional, single-warehouse deploy may omit>
```

响应：

```json
{
  "code": 10000,
  "data": {
    "token": "<short-lived JWT>",
    "expiresIn": 1800,
    "userName": "agent-inspector",
    "roles": ["insp_read"],
    "warehouseScope": ["W01"]
  }
}
```

约束：

1. API Key 只来自环境变量；`X-Agent-Key-Id` 支持双 key 并存，便于轮换。
2. IP 白名单只允许网关地址；不信任 `X-Forwarded-For`。
3. `X-Agent-Warehouse` 只能取服务端白名单中的值；单仓部署直接去掉该头。
4. `warehouse_scope` 写入 JWT claim，后续业务调用按 claim 约束。
5. 服务账号固定，不接受请求体指定任意用户；禁止交互式登录、禁止改密。
6. 走现有 OAuth2 password grant；Redis 写入必须是 JSON 字符串（带引号），TTL 与 token 有效期一致。
7. `/login/service-token` 加入网关 `white-paths`：该请求没有用户 JWT，不能走 `inner-paths`；安全边界由 API Key + IP 白名单承担。
8. 端点限流；失败产生 P0 运维告警。

**必须先确认**：网关 Redis 校验是“存在性校验”还是“等值校验”。若是等值校验，服务账号并发扫描会互相踢下线，必须全局串行扫描，或按仓库拆服务账号。

### 4.2 `sort=oldest`

`NoUpMapper.xml` 与 `DelayServiceImpl` 当前没有 `ORDER BY`，无法保证“先截断最不紧急的”。

要求：

- `GET /daycheck/no-up/get-no-up-goods` 增加可选 `sort=oldest`；
- `GET /daycheck/delay/im-delay` 增加可选 `sort=oldest`；
- `sort` 只接受枚举 `oldest`，Mapper 硬编码 `orderByAsc("create_date")` / `orderByAsc("im_data")`；
- 禁止 `${sort}` 字符串拼接；
- 不传 `sort` 时保持改造前顺序，契约测试必须断言这一点；
- 确认 `create_date`、`im_data` 索引；没有索引时排序可能全表扫描，需要先评估数据量。

**若 Java 侧暂不改**：巡检只能放大分页上限 + 本地排序 + 标 `partial`，并在文档/页面明确写“截断不保证最老优先”，不能声称已按紧急度截断。

### 4.3 `insp_read` 角色

- 在资源/角色表注册只读角色；
- 授予 4 个只读端点（v0.2.0）或 6 个只读端点（v0.2.1）；
- 授予对应数据范围；
- 服务账号只绑定该角色；
- 客户、财务角色不可见巡检菜单。

### 4.4 菜单/资源种子

- **已核实父资源 ID：`MENU-DAILY-CHECK`**；
- 现有子资源：`MENU-DAILY-CHECK-01` ~ `MENU-DAILY-CHECK-04`，对应收货未上架、出货异常、温度维护、出货延时示警；
- 新巡检菜单建议使用 `MENU-DAILY-CHECK-05`，路由 `/inspection/alerts`；实施前再确认该 ID 未被占用；
- 权限码建议 `inspection:alert:view`；
- 当前 `t_s_role_function` 只有 `gly`（管理员）映射了“每日检查”及其子资源；仓库经理、仓库管理、值班主管尚未映射，必须补角色资源关系；
- 客户、财务不可见；
- 前端路由 `/inspection/alerts` 与菜单资源同步。

### 4.5 索引

至少确认：

- `wm_in_qm_i.create_date`；
- 进货延时表的 `im_data`；
- `mv_stock_yj` 的 `dqr` / `res_date`；
- 告警表的活动态 fingerprint 部分唯一索引；
- 告警列表索引 `(state, severity, warehouse_id, last_seen_at)`。

没有索引时，先评估数据量；必要时补索引，不能等巡检超时再查。

---

## 5. 身份、鉴权与数据范围

### 5.1 两种身份

| 场景 | 身份 | 权限来源 | trace 标记 |
|---|---|---|---|
| 手动巡检 | 当前登录用户 JWT | 用户本人 RBAC | `actor_type=user` |
| 定时巡检 | 只读服务账号 JWT | 服务账号角色 + 仓库 claim | `actor_type=service` |
| 重试（管理员显式） | 发起重试的管理员 JWT | 管理员 RBAC（服务账号与业务角色不可重试） | `actor_type=user`、`trigger=retry`；`retry_of_scan_id` 指向被重试的扫描；`origin_actor_type/origin_actor_id/origin_trigger` 保留根来源（首次触发的人或服务与触发方式，链式重试不覆盖） |

重试记录回答的是「谁点了重试」，所以 `actor_*` 必须是重试管理员本人，不冒充原发起人，
也不丢失原发起人（由 `origin_*` 追溯）。执行者（`executor_type/executor_id`）仍由 worker 的服务令牌决定。
（2026-11-25 阶段7 修正：原表述「最近一次触发身份 / 原身份 / `actor_type=原值`」无法回答审计问题，已按上述规则实现，见 V010。）

### 5.2 手动巡检

- `POST /agent/scan` 必须带用户 JWT；
- `trigger` 由认证身份推导为 `manual`，请求体不决定 trigger；
- 用户只能扫描自己数据范围内的仓库；
- 服务账号扫描仅管理员可见。

### 5.3 定时巡检

- 每次扫描前调用 `/login/service-token` 重新取短时 token；
- 只在同一次扫描内复用 token；
- 取 token 失败 → `scan failed(auth_failed)`；
- 不回退管理员 token；
- 产生一条 P0 运维告警；
- 不把 token 写入日志、trace、数据库。

### 5.4 仓库范围

- 现有 RBAC 未必支持“按仓库”数据权限；
- Agent 侧必须显式传仓库条件，并在配置中声明；
- 服务账号配置允许仓库列表；
- `warehouse_scope` 写入 JWT claim；
- 单仓部署可不传 `X-Agent-Warehouse`；
- 多仓预留，不假设权限层已隔离。

---

## 6. 巡检 API 与调度

### 6.1 `POST /agent/scan`

请求：

```json
{
  "scanTypes": ["expiry", "no_up", "delay", "backlog"],
  "requestId": "optional-client-idempotency-key",
  "dryRun": false
}
```

响应 `202 Accepted`：

```json
{
  "code": 10000,
  "message": "ok",
  "data": {
    "scanId": "scan-20261124-001",
    "status": "queued"
  }
}
```

约束：

- `trigger` 不在请求体；由认证身份推导：用户 JWT → `manual`，服务令牌 → `schedule`；管理员显式重试接口固定写 `retry`（并带 `retry_of_scan_id`）；
- `scanTypes` 只允许白名单；
- `dryRun=true`：只计算 findings、写 `scan_runs`，不落告警、不发通知；
- 手动幂等键：有 `requestId` 才去重；没有则允许重复扫描；
- 定时幂等键：`scheduleSlot + configHash + scanTypes`；
- 幂等键落唯一索引：`(requestId, actorId)` 与 `(scheduleSlot, configHash, scanTypes)`。

### 6.2 `GET /agent/scans/{scanId}`

响应：

```json
{
  "code": 10000,
  "data": {
    "scanId": "scan-20261124-001",
    "trigger": "manual",
    "status": "running",
    "partial": false,
    "sourceStatus": [
      {"source": "expiry", "status": "ok", "rows": 120, "pages": 2},
      {"source": "no_up", "status": "ok", "rows": 8, "pages": 1}
    ],
    "configHash": "sha256:...",
    "ruleVersion": "v0.2.0",
    "startedAt": "2026-11-24T09:00:00+08:00",
    "finishedAt": null,
    "counts": {
      "findings": 12,
      "alertsCreated": 5,
      "alertsUpdated": 4,
      "alertsAutoResolved": 2,
      "staleCheckSkipped": 1,
      "notifications": 3,
      "llmCalls": 2,
      "promptTokens": 1200,
      "completionTokens": 300
    },
    "errorSummary": null
  }
}
```

状态固定：

`queued | running | succeeded | failed | cancelled`

- `partial` 是布尔字段，不是终态；
- `cancelled` 配套 `POST /agent/scans/{id}/cancel`；
- 协作式取消只在两个数据源之间检查；
- `errorSummary` 只给错误码，不给堆栈；
- 查询扫描只能查本人/数据范围；服务账号扫描仅管理员可见。

### 6.3 防重入与残留恢复

1. PG advisory lock 防止同 key 并发；
2. 同一 `scan_key` 只允许一个 `running` 的部分唯一索引；
3. 启动时把残留 `running` 标记为 `failed(stale)`，或重新入队；
4. 定时器默认关闭；测试环境只走手动；
5. 后续换 Java 侧调度，不改 `/agent/scan` 契约。

### 6.4 调度

- 默认 `enabled=false`；
- 配置 `scheduleSlot`、时区、窗口；
- 每次调度生成稳定 `scheduleSlot`，例如 `2026-11-24T09:00+08:00`；
- 错过调度不自动补跑，除非显式 `retry`；
- `retry` 沿用最近一次配置和 `scanTypes`。

---

## 7. 数据获取与分页

### 7.1 数据源

| 源 | 端点 | 默认排序 | 分页 |
|---|---|---|---|
| 效期 | `GET /stock/expiry-warning/query-all` | `dqr ASC`（已有） | `PageDTO` |
| 收货未上架 | `GET /daycheck/no-up/get-no-up-goods` | 当前无排序；建议加 `sort=oldest` | 裸 List |
| 进货延时 | `GET /daycheck/delay/im-delay` | 当前无排序；建议加 `sort=oldest` | `PageDTO` |
| 待办积压 | `/dashboard/query-pend-receipt`、`/query-pend-to-up`、`/query-pend-pick`、`/query-cur-pick` | 无 | 4 个计数 |
| 出货异常 | `/daycheck/yi-chang/get-yichang-down` | 当前无排序 | 裸 List |
| 温度 | `/daycheck/temperature/query` | 当前无排序 | `PageDTO` |

### 7.2 分页与预算

- `pageSize=100`；
- `maxPages` 默认 20，可配；
- 单请求超时 3s；
- 单源预算 30s；
- 整次扫描 120s；
- 并发 ≤ 3；
- 5xx/超时重试 1 次，4xx 不重试；
- 翻页期间数据变动按对象键去重；
- `PageQuery` 当前只有 `@Min(1)`，没有 `@Max`，所以 `pageSize=100` 在参数校验层可接受；但服务层/数据库可能另有上限，必须实测。

### 7.3 `source_status`

每个数据源记录：

```json
{
  "source": "no_up",
  "status": "ok | partial | timeout | error",
  "rows": 8,
  "pages": 1,
  "truncated": false,
  "errorSummary": null
}
```

任一源 `partial`：

- `scan.partial=true`；
- 额外产生一条 P2 元告警 `SCAN-PARTIAL`；
- 页面显示“本次巡检未覆盖全量”；
- 不能静默。

### 7.4 排序策略

- 效期：`dqr ASC` 已有；
- 未上架/延时：Java 侧加 `sort=oldest` 后按最老优先；
- 若 Java 未改：本地排序 + 放大上限 + `partial`，并明确“截断不保证最老优先”；
- 不做 `${sort}` 拼接；
- 契约测试断言不传 `sort` 时顺序不变。

### 7.5 数据质量

以下情况跳过并记 `source_quality`，不判为异常：

- `create_date` / `im_data` 为空；
- 时间为未来；
- `guoqibili` 解析失败；
- `bzhi_qi` 为空或 0；
- 温度地点不在词表；
- 出货异常 `goods_qua` / `goods_quaok` 无法解析。

---

## 8. 规则引擎

### 8.1 规则接口

```python
class Rule(Protocol):
    rule_id: str
    rule_version: str

    def evaluate(self, ctx: RuleContext) -> list[Finding]: ...
```

`Finding`：

```json
{
  "ruleId": "EXP-NEAR",
  "ruleVersion": "v0.2.0",
  "ruleParams": {"days": 7, "ratio": 0.3333},
  "severity": "P1",
  "objectType": "stock_batch",
  "objectId": "W01|C01|G001|2026-01-01",
  "fingerprint": "sha256(...)",
  "dimension": {"warehouse": "W01", "customer": "C01"},
  "evidence": {
    "goodsCode": "G001",
    "goodsName": "示例商品",
    "resDate": 3,
    "guoqibili": 0.21,
    "sourceRowKey": "mv_stock_yj:id=...",
    "sourceEndpoint": "/stock/expiry-warning/query-all",
    "observedAt": "2026-11-24T09:00:00+08:00"
  },
  "ruleDegraded": false
}
```

**`objectId` 与 `fingerprint` 必须分离**：

- `objectId`：业务键，可回溯到源行；
- `fingerprint = sha256(ruleId + ruleVersion + objectType + objectId + dimension)`；
- 规则改版本后，历史告警仍可解释；
- `ruleParams` 保存本次生效阈值快照。

### 8.2 v0.2.0 规则

#### 8.2.1 `EXP-EXPIRED`

- 条件：`res_date < 0`；
- 级别：P0；
- objectId：`warehouse + cus_code + goods_id + goods_pro_data`；
- 不含储位：移库不应产生新告警；
- evidence：商品、客户、到期日、剩余天数、批次、来源端点；
- 建议：`CHECK_BATCH`、`FIFO_OUTBOUND`。

#### 8.2.2 `EXP-NEAR`

- 条件：`0 ≤ res_date ≤ 7` 或 `guoqibili ≤ 1/3`；
- 级别：P1；
- objectId：同上；
- evidence：`res_date`、`guoqibili`、`bzhi_qi`、到期日；
- `guoqibili` 解析失败或 `bzhi_qi` 为空/0 时回退 `res_date`，并打 `rule_degraded=true`；
- 建议：`CHECK_BATCH`、`FIFO_OUTBOUND`、`NOTIFY_QC`。

#### 8.2.3 `NOUP-OVERDUE`

- 条件：`now - create_date > 8h` → P0；`4–8h` → P1；`2–4h` → P2；
- objectId：`notice + goods + pallet`；
- evidence：通知单、商品、托盘、储位、收货日期、滞留时长；
- 建议：`MOVE_TO_BIN`、`CONTACT_CUSTOMER`。

#### 8.2.4 `DELAY-OVERDUE`

- 条件：`im_data < now` 仍为“是否延时”的定义；
- 分级：`now - im_data > 24h` → P0；`2–24h` → P1；`0–2h` → P2；
- objectId：`notice_id`；
- evidence：通知单号、货主、约定到货时间、延时时长、司机/车号（脱敏）；
- 建议：`CONTACT_CUSTOMER`、`NOTIFY_QC`。

#### 8.2.5 `BACKLOG-GROWTH`

- 按队列分别判定：待收货、待上架、待拣货；
- 不使用聚合总数，避免单队列突增被掩盖；
- 绝对增量下限：`growth ≥ 30% && absolute_delta ≥ 10`；
- 时间线：
  - 第 1–3 次只建基线；
  - 第 4 次起可出 P2（单周期增长）；
  - 连续 3 次增长出 P1（最早第 6 次）；
- objectId：`warehouse + queue_type`；
- partial 扫描、基线缺失时不产生待办告警；
- 建议：`NOTIFY_QC`、`CHECK_BATCH`。

### 8.3 v0.2.1 规则

#### 8.3.1 `OUTBOUND-EXCEPTION`

- 数据源已按 `goods_qua != goods_quaok` 过滤，命中即视为“下架数量与复核数量不一致”；
- `create_date` 是下架单创建时间，不是异常发生时间；文案写“下架后超过 24 小时仍未处理”，不写“异常持续 24 小时”；
- 分级：
  - `now - create_date > 24h` → P0；
  - 当日新增 → P1；
  - 不设 P2；
- objectId：`bin_id_to + goods_id + cus_code`；
- evidence：下架单号、商品、客户、储位、下架数量、复核数量、下架时间；
- 不声称“未闭环”，因为现有接口没有闭环状态；
- 建议：`CHECK_BATCH`、`NOTIFY_QC`。

#### 8.3.2 `TEMP-EXCURSION`

数据源是人工录入/Excel 导入，不是传感器实时采集：

- 规则用 `wenduCjsj` 判断读数时间；
- `create_date` 只做审计，不参与“是否超限”判断；
- 检测倒填：`wenduCjsj` 明显早于 `create_date` 时记数据质量标记，不判异常；
- 地点词表归一化：`wenduDd` 必须映射到 YAML 中的 `location`；未匹配地点产生一条 P2 元告警；
- 阈值按地点配置：`location -> {min,max}`；
- `expectedIntervalHours` 按实际录入节奏配置，默认 8 小时；
- `max_silence_hours = 2 × expectedIntervalHours`；
- 分级：
  - 连续 `N=2` 个录入点超限，且（最大超限 ≥2℃ 或 超限跨度 ≥4h）→ P0；
  - 单点超限 ≥5℃ → 直接 P0；
  - 其余单点超限 → P1；
  - 超过 `max_silence_hours` 无新录入 → P2；
- objectId：`warehouse + location`；
- evidence：地点、温度值、阈值、采集时间、录入时间、连续超限次数、最大超限幅度；
- 不做商品级温度属性 join；混合温区库房作为已知限制记录。

### 8.4 规则版本

- `ruleVersion` 固定字符串，如 `v0.2.0`；
- 规则参数变化必须升 `ruleVersion` 或 `ruleParams`；
- `configHash` 记录整份 YAML 的哈希；
- 每次 `scan_runs` 保存 `ruleVersion`、`configHash`；
- 回放时按 `scanId` 取同一份配置。

---

## 9. 告警生命周期与存储

### 9.1 状态机

```text
open ──ack──▶ acknowledged ──resolve──▶ resolved
  │                │
  ├──resolve───────┤
  └──ignore────────┴──ignore──▶ ignored
```

终态：`resolved`、`ignored`。  
不做 `reopened`；复发用同一 fingerprint 新建一条。

### 9.2 转移矩阵

| 当前 | 动作 | 目标 | 前置条件 | 请求字段 |
|---|---|---|---|---|
| open | ack | acknowledged | 有权限 | 无 |
| open | resolve | resolved | 有权限 | `reason` |
| open | ignore | ignored | 有权限 | `reason`、`ignoredUntil` |
| acknowledged | resolve | resolved | 有权限 | `reason` |
| acknowledged | ignore | ignored | 有权限 | `reason`、`ignoredUntil` |
| resolved/ignored | - | - | 终态 | - |

并发控制：

```sql
UPDATE agent_alerts
SET state = :to_state, ...
WHERE alert_id = :id
  AND state IN ('open', 'acknowledged');
```

影响行数为 0 → 返回 HTTP 409，提示“状态已被他人变更，请刷新”。

### 9.3 自动 resolved

仅当：

1. 该源 `sourceStatus=ok`；
2. 该源 `partial=false`；
3. 对象落在本次扫描窗口内；
4. 本次未命中该规则；

才允许 `resolved(condition_cleared)`。

否则：

- 保持 `open`；
- 记 `stale_check_skipped`；
- 不批量误关。

### 9.4 `ignored`

- `ignoredUntil` 默认 7 天；
- 期间抑制同一 fingerprint 的新告警；
- 到期后条件仍存在 → 新建告警；
- 避免永久静默。

### 9.5 表设计

#### `agent_scan_runs`

| 字段 | 类型 | 说明 |
|---|---|---|
| `scan_id` | TEXT PK | 扫描 ID |
| `trigger` | TEXT | `schedule/manual/retry` |
| `actor_type` | TEXT | `user/service` |
| `actor_id` | TEXT | 用户或服务账号 |
| `status` | TEXT | `queued/running/succeeded/failed/cancelled` |
| `partial` | BOOLEAN | 是否覆盖不全 |
| `source_status` | JSONB | 每源状态 |
| `config_hash` | TEXT | 生效配置 canonical JSON 哈希 |
| `config_snapshot` | TEXT | 入队冻结的 canonical JSON 配置快照 |
| `config_version` | TEXT | 配置文件版本 |
| `rule_version` | TEXT | 规则实现版本 |
| `scan_types` | TEXT[] | 扫描类型 |
| `request_id` | TEXT NULL | 手动幂等键 |
| `schedule_slot` | TEXT NULL | 定时槽 |
| `scan_key` | TEXT | 幂等键 |
| `started_at` | TIMESTAMPTZ | 开始 |
| `finished_at` | TIMESTAMPTZ | 结束 |
| `counts` | JSONB | 统计 |
| `error_summary` | TEXT | 错误码，不含堆栈 |

索引：

- `(request_id, actor_id)` 唯一（允许 NULL）；
- `(schedule_slot, config_hash, scan_types)` 唯一；
- `scan_key` 上活动态部分唯一索引，防止重复 running。

#### `agent_alerts`

| 字段 | 类型 | 说明 |
|---|---|---|
| `alert_id` | BIGSERIAL PK | 告警 ID |
| `fingerprint` | TEXT | 去重指纹 |
| `rule_id` | TEXT | 规则 ID |
| `rule_version` | TEXT | 规则版本 |
| `rule_params` | JSONB | 本次阈值快照 |
| `severity` | TEXT | `P0/P1/P2` |
| `object_type` | TEXT | 对象类型 |
| `object_id` | TEXT | 业务键 |
| `dimension` | JSONB | 仓库/客户/队列等 |
| `title` | TEXT | 标题 |
| `evidence` | JSONB | 证据摘要，不含原始行 |
| `suggested_actions` | JSONB | 建议动作 |
| `state` | TEXT | `open/acknowledged/resolved/ignored` |
| `assignee` | TEXT NULL | 责任人 |
| `warehouse_id` | TEXT | 仓库 |
| `occurrence_count` | INTEGER | 出现次数 |
| `first_seen_at` | TIMESTAMPTZ | 首次发现 |
| `last_seen_at` | TIMESTAMPTZ | 最近发现 |
| `resolved_at` | TIMESTAMPTZ NULL | 关闭时间 |
| `resolved_reason` | TEXT NULL | 关闭原因 |
| `ignored_until` | TIMESTAMPTZ NULL | 忽略截止 |
| `scan_id` | TEXT | 最近扫描 |
| `trace_id` | TEXT | 最近 trace |
| `created_at` | TIMESTAMPTZ | 创建 |

索引：

- `fingerprint` 活动态部分唯一索引；
- `(state, severity, warehouse_id, last_seen_at)`；
- `(rule_id, last_seen_at)`。

#### `agent_alert_events`

append-only：

| 字段 | 类型 |
|---|---|
| `event_id` | BIGSERIAL PK |
| `alert_id` | BIGINT FK |
| `actor_type` | TEXT |
| `actor_id` | TEXT |
| `from_state` | TEXT |
| `to_state` | TEXT |
| `reason` | TEXT |
| `trace_id` | TEXT |
| `created_at` | TIMESTAMPTZ |

#### `agent_notifications`

| 字段 | 类型 | 说明 |
|---|---|---|
| `notification_id` | BIGSERIAL PK | 通知 ID |
| `alert_id` | BIGINT FK | 告警 |
| `channel` | TEXT | `in_app/sms/email` |
| `recipient` | TEXT | 接收人 |
| `status` | TEXT | `pending/sent/failed/dry_run` |
| `payload_digest` | TEXT | 内容摘要 |
| `provider_message_id` | TEXT NULL | 外部通道 ID |
| `created_at` | TIMESTAMPTZ | 创建 |
| `sent_at` | TIMESTAMPTZ NULL | 实际发送 |
| `read_at` | TIMESTAMPTZ NULL | 用户打开列表/详情 |

### 9.6 保留周期

原计划：`agent_alerts` 在线 180 天、归档 1 年；`agent_traces` / `agent_tool_calls` 90 天；聚合统计 2 年；通知记录 90 天。

2026-11-25 阶段 7 按下列口径实现（决策与取舍见 `documents/07、AI-Agent化/ADR-020-巡检数据保留与归档.md`）：

| 数据 | 在线期 | 之后 | 判定基准 |
|---|---|---|---|
| 已结案告警 | 180 天 | 归档 1 年（`agent_archive_rows`，单表 JSONB） | 状态非 `open/acknowledged`，且 `resolved_at`、`ignored_until`、`last_seen_at` 三者最大值早于 cutoff |
| 告警事件 | 随所属告警 | 随所属告警 | — |
| 扫描摘要 | 180 天 | 归档 1 年；`GET /agent/scans/{scanId}/summaries` 线上无行时回落归档并标 `archived=true` | 所属扫描完成时间；随扫描证据整批处理，单独落单的由摘要步兜底 |
| 通知记录 | 90 天 | 归档 1 年（审计证据）；挂在被归档告警上的通知随告警一起归档 | `created_at` |
| `agent_traces` / `agent_tool_calls` | 90 天 | 直接删除，不归档 | trace 的 `created_at` |
| 扫描记录（终态）及评估覆盖、命中观测、积压样本 | 180 天 | 随扫描整批归档 1 年；`queued/running` 永不归档；`GET /agent/scans/{scanId}` 与告警详情的扫描简报线上无行时回落归档并标 `archived=true` | 扫描完成时间（`finished_at`，缺失时依次取 `started_at`、`queued_at`） |
| 指标日聚合 `agent_metric_daily` | 730 天 | 直接删除，不归档 | `metric_date` |
| 活跃告警、忽略窗口未结束的告警、在途扫描 | 不受影响 | — | — |

- 执行方式：`POST /agent/scan/retention/run`（仅管理员）或每日 `retention_daily_at` 之后执行一次（`WMS_AGENT_RETENTION_ENABLED` 默认关闭）。七步顺序固定：通知（先归档再删）→ trace/tool_calls → 已结案告警（先事件、通知后告警）→ 扫描摘要 → 扫描记录及证据（先子后父）→ 过期指标日聚合 → 过期归档；每批 `retention_batch_size` 行、`FOR UPDATE SKIP LOCKED`、逐批提交，可重入；报告逐步给出动作、行数、批数与 `moreRemaining`。
- 保留参数是运维参数，走环境配置，不进入配置快照（理由见 ADR-020 第 6 节）。
- 聚合统计 2 年（2026-11-25 阶段 7.7 落地）：每日聚合表 `agent_metric_daily(metric_date, warehouse, metrics JSONB)`，`POST /agent/scan/metrics/rollup/run`（仅管理员）或定时任务每日补算最近 180 天内缺失的「仓库·日」（最旧优先、限批）；`GET /agent/scan/metrics` 的 `hours ≤ 2160` 读实时、`2160 < hours ≤ 17520` 读「90 天前的整日日聚合 + 其后的实时」并在响应里带 `mode=dailyRollup` 与 `coverage`，超过 2 年返回 422。定时任务先补齐日聚合再归档，补不齐则本轮不归档。

---

## 10. LLM 摘要与建议

### 10.1 分工

- 规则引擎决定：是否存在、级别、对象、证据；
- LLM 只决定：怎么用人话说清楚、建议动作怎么表达；
- LLM 不得修改 `ruleId`、`severity`、`evidence`；
- LLM 失败 → 模板摘要；
- 第 21 个 P0 仍落库、仍通知，只是摘要降级为模板。

### 10.2 聚合与上限

- 按 `rule_id + warehouse + customer` 聚合；
- 只对 P0/P1 调用 LLM；
- P2 用模板；
- 单次扫描 LLM 调用上限 ≤ 20；
- 单次调用 8s 超时；
- `scan_runs` 记录 `llm_calls`、`prompt_tokens`、`completion_tokens`。

### 10.3 输出 schema

```json
{
  "summary": "纯文本，最多 300 字",
  "suggestedActions": [
    {"code": "CHECK_BATCH", "text": "优先复核该批次并按 FIFO 出库"}
  ]
}
```

约束：

- `summary` 纯文本，无 Markdown 注入；
- `suggestedActions[].code` 只允许：
  - `CHECK_BATCH`
  - `FIFO_OUTBOUND`
  - `CONTACT_CUSTOMER`
  - `NOTIFY_QC`
  - `MOVE_TO_BIN`
- 未知 code 直接丢弃；
- 最多 3 条；
- 每条 ≤ 100 字；
- schema 校验失败 → 模板。

### 10.4 提示注入防护

- 业务字段按“数据”处理，不作为指令；
- 输入只给压缩摘要，不塞原始行；
- 输出做 schema 校验；
- 不执行模型返回的任何“动作”；
- 建议动作只展示，由人确认。

---

## 11. 通知

### 11.1 通道

v0.2 使用 Agent 自有 `in_app` 通道：

- `GET /agent/alerts?state=open&since=...`
- `GET /agent/alerts/{alertId}`
- 前端巡检页 + AI 助手角标 30s 轮询；
- `agent_notifications` 记录 `channel=in_app`；
- `read_at` 表示用户打开列表/详情；
- 不写 Java 公告表；
- Java 公告接口只保留为未来“全仓广播”的可选写通道。

### 11.2 通知时点

v0.2.0 只做：

- `created`：新告警；
- `escalated`：升级；
- `daily_digest` 暂不做，除非实现固定 08:00 调度器；不要留没有生产者的通知类型。

### 11.3 模式

`notification_mode = dry_run | in_app | full`

- `dry_run`：只落 `agent_notifications`，不发送；
- `in_app`：写 Agent 自有通知；
- `full`：短信/邮件真实发送，v0.2 不默认开启；
- P0 短信影子运行 ≥2 周、误报率可接受、业务签字后才开启；
- 现有短信 Controller 使用固定模板，若不支持变量，短信只能发“你有 P0 告警，请进系统查看”，不能带明细。

### 11.4 去重

- 只在 `created`、`escalated` 两个时点推送；
- 持久告警不按扫描次数重复推送；
- 同一聚合键只发一条；
- `read_at` 不等于 `created_at`。

---

## 12. 前端

### 12.1 路由与菜单

- 路由：`/inspection/alerts`；
- 菜单：挂在“每日检查”下；
- 父资源 ID 从数据库查询，不能猜；
- 权限码：`inspection:alert:view`；
- 角色：仓库经理、仓库管理、值班主管；
- 客户、财务不可见。

### 12.2 页面能力

- 列表：级别、状态、异常类型、仓库、责任人、时间；
- 筛选：state/severity/warehouse/ruleId/assignee/since；
- 游标分页 + `since` 增量；
- 详情：证据链、规则参数、来源端点、scanId、traceId；
- 操作：认领、关闭、忽略；
- 关闭必须填 `reason`；
- 忽略必须填 `reason + ignoredUntil`；
- 跳转源页面；
- 顶部显示 `partial` 提示；
- 30s 轮询，不引入 WebSocket；
- 详情抽屉展示巡检摘要（阶段7 实现，ADR-019）：按 scanId 调 `GET /agent/scans/{id}/summaries`，取与当前告警同规则、同仓库、同客户的那一组；标识「模型摘要 / 模板摘要」，降级时显示原因；摘要按纯文本渲染（不用 `v-html`）；建议动作只展示并标注「需人工确认，不会自动执行」；扫描未结束时提示稍后刷新（10s 轮询、最多 30 次）。

### 12.3 显示字段

每条告警至少显示：

- `severity`；
- `ruleId`；
- `title`；
- `objectType/objectId`；
- `warehouse`；
- `assignee`；
- `firstSeenAt/lastSeenAt`；
- `occurrenceCount`；
- `scanId`；
- `traceId`；
- `partial`（扫描级）；
- `ruleDegraded`（如有）。

---

## 13. 配置

### 13.1 YAML 示例

```yaml
scan:
  enabled: false
  schedule_slot: "*/15 07-23 * * *"
  timezone: "Asia/Shanghai"
  max_pages: 20
  page_size: 100
  request_timeout_seconds: 3
  source_budget_seconds: 30
  scan_budget_seconds: 120
  concurrency: 3
  dry_run: false

rules:
  expiry:
    expired_days: 0
    near_days: 7
    near_ratio: 0.3333
    watch_days: 30
  no_up:
    p0_hours: 8
    p1_hours: 4
    p2_hours: 2
  delay:
    p0_hours: 24
    p1_hours: 2
    p2_hours: 0
  backlog:
    growth_ratio: 0.30
    absolute_delta: 10
    baseline_scans: 3
    consecutive_for_p1: 3
  temperature:
    expected_interval_hours: 8
    consecutive_points: 2
    p0_abs_c: 2.0
    p0_span_hours: 4
    p0_single_point_abs_c: 5.0
    locations:
      - name: "冷藏区"
        aliases: ["冷藏", "cold"]
        min_c: 2.0
        max_c: 8.0
      - name: "常温区"
        aliases: ["常温", "ambient"]
        min_c: 10.0
        max_c: 30.0
  outbound:
    p0_hours: 24

routing:
  - rule_id: "EXP-*"
    warehouse: "W01"
    assignee: "qc_lead"
  - rule_id: "NOUP-OVERDUE"
    warehouse: "W01"
    assignee: "putaway_lead"
  - rule_id: "DELAY-OVERDUE"
    warehouse: "W01"
    assignee: "receiving_lead"
  - rule_id: "BACKLOG-GROWTH"
    warehouse: "W01"
    assignee: "duty_supervisor"

notifications:
  mode: "dry_run"   # dry_run | in_app | full
  channels:
    in_app:
      enabled: true
    sms:
      enabled: false
    email:
      enabled: false
```

### 13.2 配置原则

- 阈值、巡检窗口、责任路由、通知开关全部配置化；
- 启动加载 YAML；
- `config_hash` 写入 `agent_scan_runs`；
- 规则版本变化必须升 `ruleVersion` 或 `ruleParams`；
- 环境变量只覆盖密钥和部署差异；
- ADR-014 的 Nacos 非密配置是默认，但巡检规则是**有意例外**：必须版本化、可 review、可回放；已由 ADR-018 记录。worker 不读取当前 YAML，只执行入队快照。

---

## 14. 可回放与可观测

### 14.1 回放要素

每次扫描必须保存：

- `scanId`；
- `configHash`；
- `ruleVersion`；
- `sourceStatus[]`；
- `partial`；
- `counts`；
- `traceId`；
- `actorType/actorId`。

### 14.2 测试替身

- 时钟注入：固定 `now`；
- mock Gateway：`httpx.MockTransport` fixtures；
- mock LLM：scenario 有序回放；
- 固定 `scanId` 生成器；
- 按 `scanId` 重放同一份配置和 fixtures。

### 14.3 指标

- 扫描次数、成功/失败/partial；
- 每源耗时、行数、截断；
- 告警新增/更新/自动关闭；
- 认领/关闭/忽略时效；
- LLM 调用次数、token、失败率；
- 通知 dry-run/发送/阅读。

---

## 15. 回滚

三档回退：

1. **关闭调度器**：`scan.enabled=false`，只保留手动；
2. **通知降级**：`notification_mode=dry_run`，不发送；
3. **功能开关**：按 `scanTypes` 关闭单类巡检；
4. **紧急回滚**：下线 `/agent/scan` 路由或回退服务版本，保留已落库告警只读查询。

---

## 16. 验收与测试计划

### 16.1 v0.2.0 验收

1. 效期：已过期 → P0；7 天内或比例 ≤1/3 → P1；30 天内 → P2。
2. 收货未上架：8h/4h/2h 分级正确。
3. 进货延时：24h/2h/0h 分级正确，且仍按 `im_data < now` 判定。
4. 待办积压：前 3 次只建基线；第 4 次可出 P2；连续 3 次增长出 P1。
5. 同一 fingerprint 重复扫描不新增，只更新 `occurrence_count`。
6. 异常消失自动 `resolved(condition_cleared)`。
7. 单源 partial 产生 P2 元告警，且不自动关闭。
8. LLM 失败仍落告警，摘要用模板。
9. 通知 dry-run 只落库，不发送。
10. 服务 token 失败 → 定时巡检 `failed(auth_failed)`，手动巡检可用。
11. 提示注入样本不改变级别和输出结构。
12. 扫描进程崩溃后残留 `running` 能被标记/重跑。

### 16.2 v0.2.1 验收

1. 出货异常：`goods_qua != goods_quaok` 命中；`>24h` P0；当日 P1；文案不写“未闭环”。
2. 温度：地点阈值；连续 N=2 点超限；幅度覆盖；无录入 P2；未匹配地点 P2 元告警。
3. 温度倒填/未来时间记数据质量，不判异常。
4. 出货异常/温度各自独立开关，不影响 v0.2.0。
5. 两批验收证据分开，不混在一次通过结论。

### 16.3 证据要求

每条 evidence 写入 `feature_list.json`，包含：

- 命令；
- 日期；
- `scanId`；
- `configHash`；
- `ruleVersion`；
- 结果摘要；
- 未验证项。

---

## 17. 实施顺序

### 阶段 A：Java 前置

1. `service-token` 端点；
2. `insp_read` 角色；
3. `sort=oldest`；
4. 菜单/资源种子；
5. 索引确认；
6. 网关 `white-paths`（`/login/service-token` 无用户 JWT）；
7. Redis 覆盖语义确认。

### 阶段 B：Python 核心

1. `app/scan/` 骨架；
2. 四张表 DDL；
3. scan API；
4. 调度器与锁；
5. 四类规则；
6. 数据源适配；
7. 告警状态机；
8. LLM 摘要；
9. in_app 通知。

### 阶段 C：前端

1. `/inspection/alerts`；
2. 列表/详情/操作；
3. 30s 轮询；
4. AI 助手角标；
5. 菜单联调。

### 阶段 D：验证

1. 单元测试；
2. 契约测试；
3. mock 回放；
4. 真实手动扫描；
5. 服务 token 定时扫描；
6. dry-run 通知；
7. v0.2.1 独立验收。

---

## 18. 已知限制与风险

| 风险/限制 | 处理 |
|---|---|
| 未上架/延时无排序 | Java 加 `sort=oldest`；否则本地排序 + partial，并明确不保证最老优先 |
| `pageSize` 无 `@Max` | 参数层可传 100，但服务层/DB 可能另有限制，必须实测 |
| 出货异常无闭环状态 | v0.2.1 只按 `create_date` 老化，不写“未闭环” |
| 温度是人工录入/导入 | 规则按“无录入/连续点超限”，不称设备采集 |
| 服务账号 token 覆盖语义未知 | 先确认 Redis 是存在性还是等值校验；必要时全局串行或按仓库拆账号 |
| 单实例调度 | v0.2 先单实例；多实例需额外leader选举/锁 |
| LLM 成本 | 聚合 + 上限 20 次 + token 记账 |
| 提示注入 | 业务字段按数据、压缩摘要、schema 校验、建议动作只展示 |
| 多仓/多货主 | v0.2 单仓优先，配置预留 |
| 菜单父资源 ID | 必须查真实 DB，不能猜 |
| JWT 私钥历史风险 | 独立安全问题，后续轮换密钥、清理历史 |
| Python 不查 Redis 注销黑名单 | 既有风险，不在本方案扩大 |

---

## 19. 实施前验证门与 2026-11-24 实测结果

以下不是设计问题，而是编码前必须拿到的事实。带“已实测”的项目已经用本机 10320 服务或只读 SQL 验证；未实测项必须在实施前补。

| # | 验证项 | 2026-11-24 结果 | 结论 |
|---|---|---|---|
| 1 | `pageSize=100` 是否被 NoUp/Delay 服务层接受 | 直连 `10320` 与经网关 `10001` 均返回 200：delay 3 行、no-up 0 行、yichang 4 行、temperature 4 行、expiry 6 行；`PageQuery` 无 `@Max` | **参数层接受**；仍需做大数据量压测 |
| 2 | `create_date` / `im_data` 是否有索引 | `wm_in_qm_i` 无 `create_date` 索引；`wm_im_notice_h` 无 `im_data` 索引；`wm_to_down_goods` 的 `bgtp` 组合索引中 `create_date` 不是首列；`mv_stock_yj` 是视图无索引 | **风险确认**，排序可能全表扫描 |
| 3 | Redis 校验是存在性还是等值 | `TokenExtendsValidateImpl` 使用 `Objects.equals(redis value, token)`；`RedisConfig` value 用 Jackson JSON 序列化；实测 `admin:token` 值带引号，长度 702，去引号后 700；网关接受该 token；服务账号 token 也写入同一格式 | **等值校验 + JSON 字符串**；同用户新 token 会覆盖旧 token |
| 4 | `insp_read` 角色是否已注册 | 已创建 `insp_read`，`agent-inspector` 已绑定；菜单映射 `ckjl/cg/gly` | **已验证**；`ckjl` 当前 0 用户，实际可见主要来自 `cg/gly` |
| 5 | “每日检查”父资源 ID | 已查到 `MENU-DAILY-CHECK`，子资源 `01`~`04` | **已确认**；新菜单建议 `MENU-DAILY-CHECK-05` |
| 6 | `/login/service-token` 的 IP 白名单实际网关地址 | 网关已启动并注册 `GATEWAY 192.168.101.91:10001`；`/login/service-token` 经网关 200，说明白名单已允许实际来源；`/agent/health` 200，`/agent/tools` 无 token 401、带 token 200 | **已验证经网关可调用**；如需精确 remoteAddr，可在登录服务加访问日志 |
| 7 | 服务账号是否被允许调用 4/6 个只读端点 | 已创建 `agent-inspector` + `insp_read`；服务账号 JWT 调用 4 类端点均 200 | **已验证**；v0.2.1 两个端点待后续 |
| 8 | 现有短信模板是否支持变量 | `SendSmsController` 固定签名 `阿里云测试短信`、模板 `SMS_154950909`，参数只传 `message` | **代码只支持 `message` 变量**；是否可发需业务/短信平台确认，未做真实发送 |
| 9 | `sort=oldest` 是否会改变现有页面默认顺序 | 已实现：无 sort 时 delay 保持新→旧；`sort=oldest` 时按 `im_data` 升序；非法 sort 返回 9995 | **已验证** |
| 10 | 温度地点词表由谁维护 | 当前数据地点为“一号冷库/二号冷库/常温库A/三号冷库”等自由文本；`wenduDd` 无受控词表 | **未确认**；需业务提供词表并配置 aliases |
| 11 | 未实现端点状态 | `POST /agent/scan` 404；`POST /login/service-token` 已实现并实测 200 | `/agent/scan` 仍待 F-015 实现 |

---

## 20. 结论

本方案已经把异常巡检从“业务愿望”收敛为可实施设计：

- v0.2.0 四类先落地，复用已验证链路；
- v0.2.1 两类单独验收；
- 规则确定性、LLM 只表达；
- 服务账号不破坏验证码；
- 告警有状态、有证据、有回放；
- 通知不污染 Java 公告；
- Java 前置项单列，避免“纯 Python 幻觉”。

下一步：先完成第 19 节验证门，再按第 17 节阶段 A 开始 Java 前置改造。
