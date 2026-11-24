# Progress

> 当前状态与下一步。功能级验证步骤和证据在 `feature_list.json`；稳定事实与决策在 `.workbuddy-ai/memory/MEMORY.md`。

## 当前已验证状态

- 日期：2026-11-24
- 父仓库：`main`（F-006~F-013 已提交；本轮追加 F-011 浏览器 e2e 证据并单独提交，HEAD 见 `git log`）
- 嵌套历史仓库：`zero-one-10wms/.git` 仍存在，HEAD `7ef08d8`，但父仓库不维护其指针，不作为提交目标
- 跟踪结构：**单仓模式**。父仓库索引中 `zero-one-10wms/*` 全部为 mode `100644` 普通文件，无 `160000` gitlink 条目；`zero-one-10wms/` 下的 ADR、`init.sh`、`AGENTS.md`、`architecture.md`、`process.md`、`feature_list.json`、`PROGRESS.md` 均已直接被父仓库跟踪。
- 推送范围：父仓库根新增 `.gitignore`，排除 `node_modules/`、`node_modules.bak/`（**2.55 GB**，本轮明确不入库）、`target/`、`dist/`、`*.class`、`*.jar`、`*.pdb`、`*.log`、`__pycache__/`、`*.pyc`、`.venv/`、`.env`/`.env.*`、`.idea/`、`.vs/`、`.runtime_tmp/`（临时联调目录，含私钥/token/HAR）。其余文件全部入库（含 `.dsh-scratch/` 辅助脚本 6.4 MB / 210 文件）。
- 标准启动路径：`cd zero-one-10wms && ./init.sh --quick`（Git Bash）
- 标准验证路径：`./init.sh --quick` → `./init.sh --cpp` → 按功能跑 `--java <module>` / `--frontend` / `--verify` / `--agent`
- 当前工作项：**AI-Agent 轨道 F-006~F-013 全部完成**（`F-006`/`F-007`/`F-011`/`F-012`/`F-013` 为 `e2e_pass`，`F-008`/`F-009`/`F-010` 为 `unit_pass`）；F-008 追加真实 LLM（OpenRouter）手动 smoke 证据；下一个候选 `F-002`（储位管理前端页面）
- AI-Agent 轨道顺序（已全部走完）：`F-006` 骨架 → `F-007` 网关路由 → `F-008` LLMProvider → `F-009` 6 工具 → `F-010` ReAct 循环与 `/agent/query` → `F-011` 前端悬浮窗 → `F-012` 状态持久化 → `F-013` `init.sh --agent`
- 优先级决策（2026-11-23）：`priority` 改为唯一连续序号 1..13，features 数组按 id 升序、排序键为 priority；AI-Agent 轨道整体前置，传统功能队列后移（F-002=11、F-003=12、F-004=13；F-005=5 保持不变）。
- 排队项：`F-002` 储位管理前端页面、`F-003` 商品明细只读页面（均 `not_started`）；`F-004` 运行时基线仍 `blocked`
- 已通过项：`F-001` harness 入口、`F-005` 其他配置 25 项（均 `passing` + `static_pass`）、`F-006`（`e2e_pass`）、`F-007`（`e2e_pass`）、`F-008`/`F-009`/`F-010`（`unit_pass`）、`F-011`（`e2e_pass`，本轮真实浏览器实测）、`F-012`（`e2e_pass`）、`F-013`（`e2e_pass`）
- 运行时底座（本轮实测）：本机 `192.168.101.91`；虚拟机 `192.168.89.128` 提供 Nacos 8848、Redis 6379、MySQL 3306，**PG 5432 未起**；本机原生 PostgreSQL 16.15 在 5432（库 `ragent`，`postgres`/`123456`，本轮 F-012 落库用它）
- 工具链实测：Python 3.14.7 = `D:\DownloadPackage\environment\python.exe`；uv 0.13.1 = `C:\Users\a\.local\bin\uv.exe`（**不在 PATH**）；JDK17 = `D:\DownloadPackage\environment\jdk-17.0.20.1+1`（PATH 上的 java 是 JDK8，不能用于 Spring Boot 3）；mvn = `D:\DownloadPackage\Maven\apache-maven-3.6.3-bin\apache-maven-3.6.3\bin\mvn.cmd`；Git Bash = `D:\DownloadPackage\environment\Git\Git\bin\bash.exe`（**不在 PATH**，本轮已用它跑通 `init.sh --agent`）
- 当前 blocker：本机无 cmake/MSVC，C++ 只能 `static_pass + runtime_unverified`；运行时/端到端环境未就绪（`F-004`）；`init.sh` 需用 Git Bash 执行。前端浏览器链路已用本轮实测打通（私钥就在仓库 jwt.pfx/jwt.jks + 现启 Java 服务），原 blocker 已解除。

## 本轮记录

### 追加：F-011 真实 LLM 浏览器 e2e 复跑（2026-11-23 晚）

- 目标：用户要求用**真实 LLM**（而非之前的 mock 场景）重跑 F-011 浏览器端到端。
- 前置确认：`wms-agent/.env` 为 `provider=openai` / OpenRouter `baidu/ernie-5.5-flash-preview:free`；env 写入 22:49:44、agent 22:50:07 启动，确认加载真实 LLM。直接 `POST /agent/query` 探针拿到 LLM 生成的 Markdown 答案（非 mock 固定文案），证明真实模型链路可用。
- 浏览器链路：vite 重启到 `127.0.0.1:3000`（原 5173 进程已退出）；Redis `admin:token` 真实 JWT 经 base64 注入 localStorage → `/home` 登录态生效（`current-user`/`get-menus` 200）→ 点『问数助手』→ 输入『查询 A01 库位的库存情况』→ 提问。
- 失败路径实测：首轮 OpenRouter 免费额度瞬时 429 → `POST /api/agent/query` 返回 `{code:9994,message:模型调用失败}`；页面未渲染答案区且保留输入，符合 F-011「失败显式提示且不清空输入」要求。
- 成功路径实测：重试后 HAR 捕获 `{code:10000,answer:**结论：A01 库位当前没有库存数据。**...,traceId:t-20261123232712-583fb2,persisted:false,toolCalls:[STOCK-QUERY/empty/0 行/36 ms]}`；截图与 DOM 均显示答案、工具调用溯源与 traceId。
- 未粉饰：`persisted=false`（本轮 memory backend）；首次 429 失败如实记录。
- 证据：`zero-one-10wms/.runtime_tmp/f011_real_llm_e2e/e2e_retry.har`（6KB）、`panel_real_llm.png`（109KB），gitignore 排除；已扫描确认无 LLM API key 明文泄漏（HAR 中仅含真实用户 JWT 于 Authorization 头，属预期）。

### 追加：F-011 浏览器端到端实测（解除 runtime_unverified，升级 e2e_pass）

- 目标：用户要求实测此前 4 项未验证内容中的「浏览器端到端链路断」。结论：**不需要 C++**（6 个工具全是 Java 端点），需要 Java 业务服务 + 网关 + Python Agent + 前端。
- 私钥结论纠正：私钥就在仓库 `wms-java/wms-oauth2/src/main/resources/jwt.jks` / `jwt.pfx`（密码 `123456`、alias `01star`），modulus 与 `wms-common/src/main/resources/public.pem` 一致；此前「无私钥」结论作废。
- Redis 登录态关键事实：`TokenExtendsValidateImpl.isLogout`（`wms-gateway/.../TokenExtendsValidateImpl.java:38`）用 JSON 反序列化读 `<user_name>:token`，值必须是 **JSON 字符串（带引号）**；裸 JWT → `SerializationException` 500，键不存在 → 401「用户凭证已注销」。真实 wms-login 登录写同格式。
- 启动实例（JDK17 + `--add-opens`）：wms-login 10200、wms-j3-daycheck 10320、wms-j6-stockln 10610、wms-oauth2 10400、wms-j1-dashboard 10010（Redisson 需 16 个 opens、oauth2 JAXB 需 6 个），网关 10001、wms-agent 11200（mock 场景）、vite 5173。
- 6 个 Java 工具端点经网关全部 200/code=10000 拿到真实数据（STOCK total=6、EXP total=6、DAYCHECK-DELAY total=3、DASH-TREND 真实列表等）；agent `/agent/query` STOCK-QUERY status=success rowCount=6。
- **浏览器 e2e 实测通过**：把 Redis `admin:token` 中的 wms-login 真实登录 token（700 字符、经 public.pem 验签通过、网关 `/login/current-user` 返回 code=10000）注入 localStorage → agent-browser 打开 `http://127.0.0.1:5173/home` → 点击「问数助手」→ 输入「查询 A01 库位的库存情况」→ 点击「提问」；HAR 捕获 `POST /api/agent/query` → HTTP 200 `{"code":10000,"message":"ok","data":{answer,sessionId,traceId,persisted:false,toolCalls:[STOCK-QUERY/success/rowCount=6/endpoint=/stock/inventory-query/query-all/resultDigest]}}`；页面实际渲染出「库存查询完成。」「工具调用（1）STOCK-QUERY 成功 6 行 62 ms」与 traceId。
- feature_list F-011 `runtime_unverified` → `e2e_pass`；未粉饰：`persisted=false`（本轮 agent 用 memory backend，PG 持久化已由 F-012 单独 e2e 证明）。
- 工具坑：PowerShell 5.1 向原生 exe 传参会吃内嵌双引号（写 Redis 值须用文件 `setfile`）；agent-browser console 会刷验证码 base64，改用 HAR 录制 + 定向过滤；harness 函数命名避开 `Get-History` 别名 `h`。

- 目标：按 `wms-agent/docs/implement/问数Agent实施方案.md` 推进问数 Agent，本轮完成 `F-011`（前端全局悬浮对话框）、`F-012`（PostgreSQL `wms_agent` 持久化）、`F-013`（`init.sh --agent` harness 集成），收尾 AI-Agent 轨道（F-006~F-013）。
- 已完成：
  - F-011：`wms-frontend/src/apis/agent.ts`（独立 axios 实例 `timeout=60000`，不复用 `src/plugins/http.js` 的 10s 超时；`unwrapAgentEnvelope` 按 `code=10000` 解包；`normalizeAgentError` 归一超时/无响应/401/403）、`wms-frontend/src/components/ai-assistant/index.vue`（右下悬浮按钮 + el-card 面板、Ctrl+Enter 提交、答案区 + el-collapse 工具调用溯源、traceId/persisted 提示、失败仅 `ElMessage.error` 并保留输入）、`src/layouts/default.vue` 末尾挂载 `<AiAssistant />`、`vitest.config.ts` 补 `@vitejs/plugin-vue` 插件。
  - F-012：`wms-agent/app/storage/postgres.py`（`SCHEMA="wms_agent"`、3 张表 DDL、`normalize_dsn`、`PostgresTraceStore.ensure_schema/save/get`，重复保存先删同 trace 旧 tool_calls 保证幂等）、`tests/test_storage_postgres.py`（单元 + 真实 PG 集成）、`app/main.py` 改用 lifespan 钩子调用 `ensure_schema`（失败只告警）、pyproject 增 `psycopg[binary]>=3.2`。
  - F-013：`init.sh` 新增 `--agent` 分支与 `check_agent()`（关键文件、网关 `agent-route`、`nacos-config/system.yaml` agent 配置、uv、`uv sync` + `uv run pytest`；`UV_CACHE_DIR` 固定项目内 `.uv/cache`；解释器可用 `WMS_AGENT_PYTHON` 覆盖）。
  - 身份映射修正：`app/security.py` 按 Java 侧 JWT 实际载荷取身份——用户名 `user_name`→`username`→`sub`→`realname`，用户 id `id`→`user_id`→`sub`（依据 `wms-oauth2` `JwtTokenEnhancerDataServiceImpl.java:38-41`）。
  - harness 修复：`init.sh` 的 `check_json` 原先只在 PATH 无 `python` 时才回退 node，而 Windows 的 `python` 是 Microsoft Store 存根（必然失败）导致误报 JSON 非法；改为 `python` → `py -3` → `node` 依次回退。
- 运行过的验证：
  - `uv run pytest`（wms-agent）→ **72 passed, 1 warning**（含 3 个真实 PG 集成用例，`WMS_AGENT_TEST_DB_URL=postgresql://postgres:123456@127.0.0.1:5432/ragent`）。
  - 前端：`vitest run src/apis/agent.test.ts src/components/ai-assistant/index.test.ts` → **13 passed**；`node node_modules/vite/bin/vite.js build --mode production` → **✓ built in 39.46s, EXIT=0**。
  - F-012 运行时（后台 job `pwsh-4e91124cde604e58`，127.0.0.1:11200，`WMS_AGENT_STORE_BACKEND=postgres`）：`POST /agent/query` → 200 `code=10000`、**`persisted=true`**、`traceId=t-20261123214401-fbcf90`；`GET /agent/trace/{traceId}` → 200 摘要（answer/sessionId/userName/toolRounds/toolCalls[0].resultDigest）。
  - 数据库侧核对（`psql -d ragent`）：`wms_agent` 下 3 张表齐全；`agent_traces` 1 行（status=ok、tool_rounds=1）、`agent_tool_calls` 1 行（STOCK-QUERY/error）、`agent_sessions` 1 行（user_name=tester）。
  - F-013：Git Bash（`D:\DownloadPackage\environment\Git\Git\bin\bash.exe`）执行 `./init.sh --agent` → `uv sync` Resolved 39 packages、`uv run pytest` 69 passed 3 skipped、**结果 PASS**；`./init.sh --quick --snapshot --agent` → **结果 PASS** 且快照 JSONL 正常追加。
  - `feature_list.json` JSON 校验：PASS（13 条 feature）。
- 未验证（本轮已消除前 3 项，保留后 2 项）：
  - ~~前端浏览器端到端链路~~ **本轮已实测打通**（见上「追加：F-011 浏览器端到端实测」），原「无私钥/无 wms-login 实例」结论作废。
  - ~~真实用户 JWT 经网关 → Java 业务端点的完整链路~~ **本轮已实测**：wms-login 真实登录 token 经网关验签 + Redis 登出校验 → 6 个 Java 工具端点返回真实数据 → agent 拿到真实库存 rowCount=6。
  - 网关 `inner-paths` 与 `RESOURCE_ROLES_MAP` 的实际判定（判定在 starter jar 内，本环境 `open-authorization=false`，无法区分 white/inner 差异；Python 侧 401 已兜底）。
  - F-012 落库用的是本机原生 PostgreSQL 16.15，**未在虚拟机 pgvector 镜像上复验**。
  - ~~本轮浏览器 e2e 使用 `persisted=false`（memory backend），未与 PG 持久化同时打开；两条链路各自单独通过。~~ **2026-11-24 已消除**：补做三合一合并 e2e（真实 LLM + 浏览器 + PG 持久化同时打开），`persisted=true`，详见下方「追加：三合一合并 e2e」。
- 下一步：`F-002` 储位管理前端页面（`next_candidate`）；`F-004` 运行时基线仍 `blocked`。2026-11-24 已补齐问数 Agent 三合一合并 e2e 缺口（见下），AI-Agent 轨道剩余风险仅剩 VM pgvector 复验等非阻塞项。
- 用户待办（可选）：若要把 trace 落到虚拟机，`192.168.89.128` 用 `pgvector/pgvector:pg16` 起库（库名 `ragent`），连接串 `postgresql+psycopg://postgres:postgres@192.168.89.128:5432/ragent`；不拉也不阻塞，F-006~F-013 均已通过，缺失时按 `persisted=false` 降级。
- 已知风险：
  - **AgentScope 探针已通过**（`uv pip install --dry-run agentscope` → 97 包可解析、agentscope 2.0.12 兼容 Python 3.14.7，故 F-010 不记 blocked）；但 ReAct 循环按方案自研 `LLMProvider` + ToolSchema 契约实现，**未引入 AgentScope 依赖**（避免引入未被使用的 73 个传递依赖）——与 `feature_list.json` F-010 标题/notes 一致记录。
  - Gateway `inner-paths` 通配符行为在 starter jar 内，本环境因鉴权开关关闭未能区分 white/inner 差异；F-010 用 Python 侧 401 实测兜底。
  - JWT 签发私钥明文存在于仓库历史，是独立安全问题；后续需轮换密钥并清理历史。
  - Python 不查 Redis 注销黑名单；已登出 token 在 JWT 过期前直连 Python 仍是理论风险。
  - 本机 `postgres/123456` 是明文口令且本轮在库中建了 `ragent` 库，属测试环境痕迹，交付前宜改口令或清理该库。

## 最近会话（append-only）

### 2026-11-24 问数 Agent 三合一合并 e2e（真实 LLM + 浏览器 + PG 持久化同时打开）

- 用户诉求（m00001/m00031）：此前浏览器 e2e 用 `persisted=false`（memory backend），PG 持久化由 F-012 单独 e2e 证明，两条链路仍未同时打开；用户确认「可以，你测试下端到端的验证」。目标是把真实 LLM、浏览器 e2e、PG 持久化放到同一次运行中验证，补齐唯一残留缺口后回填 `feature_list.json` 与 `PROGRESS.md`。
- 环境前置：wms-agent `.env` 为 `provider=openai` / OpenRouter `baidu/ernie-5.5-flash-preview:free`（真实 LLM）；通过 cmd 包装脚本 `zero-one-10wms/.runtime_tmp/start_agent_pg.cmd` 以 `WMS_AGENT_STORE_BACKEND=postgres` + `WMS_AGENT_DB_URL=postgresql://postgres:123456@127.0.0.1:5432/ragent` 重启 agent（pid 27272，日志 `agent_pg_combined.log`），即**同一进程同时开真实 LLM + PG 持久化**。JWT 取自 Redis `admin:token`（VM 192.168.89.128:6379，密码 `01star`），值须 `json.loads` 去外层引号得 700 字符裸 JWT（https:// 前缀无关），经网关 `/login/current-user` 验签通过。
- 直连探针：`POST http://127.0.0.1:11200/agent/query`（真实 JWT，body `{"query":"查询 A01 库位的库存情况"}`）→ HTTP 200 `code=10000`、**`persisted=true`**、`traceId=t-20261124092640-e16eb8`、真实 LLM Markdown 答案「结论：A01 库位当前没有库存数据」、`toolCalls=[STOCK-QUERY/empty/0 行/46 ms]`。
- 浏览器 e2e：Redis 真实 JWT 经 base64 注入 localStorage（`tokenLen=700`）→ `http://127.0.0.1:3000/home` 登录态生效（vite 代理 `/api`→网关 10001）→ 点『问数助手』→ 输入『查询 A01 库位的库存情况』→ 点『提问』。HAR（`zero-one-10wms/.runtime_tmp/f012_combined_e2e/combined.har`，gitignore 排除）捕获 `POST http://127.0.0.1:3000/api/agent/query`（Authorization: Bearer <真实 JWT>）→ HTTP 200 `{code:10000, data:{answer:**结论：A01 库位当前没有库存数据。** + 可能原因, sessionId:s-20261124092842-f68ae5, traceId:t-20261124092842-32b880, persisted:true, toolCalls:[STOCK-QUERY/status=empty/rowCount=0/durationMs=49/endpoint=/stock/inventory-query/query-all/resultDigest=sha256:4f53cda18c2baa0c]}}`；DOM 面板显示答案、『工具调用（1）STOCK-QUERY 无数据 0 行 49 ms』与『traceId t-20261124092842-32b880 · 已持久化』。
- 回读与落库：`GET http://127.0.0.1:10001/agent/trace/t-20261124092842-32b880`（经网关、真实 JWT）→ `code=10000`、status=ok、userName=admin、toolRounds=1、答案一致；`psql -d ragent` 核对三表均新增 1 行：`agent_traces`(`t-20261124092842-32b880`,admin,ok,1,3317ms)、`agent_tool_calls`(seq=0,STOCK-QUERY,empty,row_count=0,49ms,endpoint,sha256:4f53cda18c2baa0c)、`agent_sessions`(`s-20261124092842-f68ae5`,admin,user_id=2c9221a4717bb44c01717d01c6ff0540)。测试前基线各 1 行（tester），测试后 traces=3 行（含直连探针 1 行）。
- 结论：**两条链路已同时打开**，唯一残留缺口消除；`feature_list.json` F-011/F-012 evidence 已追加合并 e2e 条目，`updated_at` 改为 2026-11-24；F-011/F-012 仍为 `passing`+`e2e_pass`，F-006~F-013 状态不变。
- 未粉饰/剩余风险：PG 仍为本机原生 PostgreSQL 16.15（非 VM pgvector 镜像）；JWT 私钥明文、Redis 注销黑名单、网关 inner-paths 判定等既有风险不变；测试痕迹（库 `ragent` 与明文口令 `postgres/123456`）交付前宜清理。

### 2026-11-23 问数助手「库存查询完成。」答非所问修复（方案 A：真实 LLM）

- 用户反馈：问数助手不管问什么都只回「库存查询完成。」，是否符合实施文档？结论：**不完全符合**。该句是 mock 回放 fixture（`tests/fixtures/llm/query_single_tool.json:12`）的占位文案；实施方案虽在 §8.2 规定「只断言工具调用序列、不逐字断言文案」（测试层允许占位），但产品层要求具体回答（方案 :220 样例「当前待上架 128 件。」）。
- 根因：运行配置 `WMS_AGENT_LLM_PROVIDER=mock`，`MockProvider.complete()`（app/llm/mock.py:65-86）忽略 messages/tools 只按序吐 fixture 文本；真实作答链路（app/llm/openai_compatible.py + app/agent/react.py:40-50 工具结果回喂）代码早已存在但未启用。
- 处置（用户选方案 A）：把真实 LLM key 只写入本地 `wms-agent/.env`（根 .gitignore:32-34 排除，未提交），设 `WMS_AGENT_LLM_PROVIDER=openai` + base_url + model + timeout，重启 11200 的 wms-agent。
- 实测（合法 JWT 取自 Redis `admin:token`，经 public.pem RS256 验签有效至 2026-11-24）：三问三答全部 `code=10000`、答案各异且基于工具真实数据——①按仓库统计库存→共 540 件/成品库 6 行明细（STOCK-QUERY/success/6）；②临期批次→6 行效期表含已过期 -180/-27 天与 3 天临期（EXP-WARN-QUERY/success/6）；③A01 库位→0 件（STOCK-QUERY/empty/0）。彻底告别固定占位文案。
- 模型供应商：先用 Agnes（agnes-3.0-flash）验证真实调用成功，但该账号 chat/completions 有 429 RPM 限流（密集提问偶发 code=9994，provider 如实报错非缺陷）；按用户要求换 OpenRouter（`baidu/ernie-5.5-flash-preview:free`），重跑三问全部成功无 429。最终生效配置即 OpenRouter，key 仍未入库。
- 风险：Agnes key 与 OpenRouter key 均为用户直接提供的明文，已在本会话出现且曾落本地 .env；建议视为已泄露并择机轮换。feature_list F-008 证据已回填；F-006~F-013 状态不变。

### 2026-11-23 问数 Agent 实施方案设计

- 目标：基于技术选型 ADR 继续 grill 实施细节并形成可执行方案。
- 决策：Python 3.14.7、独立 axios 60 秒、2 轮工具调用上限、Python 自验 JWT、health 匿名最小响应、单仓模式；不预留 `context`，不做 SSE 和多轮记忆。
- 结果：ADR、实施方案、feature_list、init 单仓检查与进度文件已同步；`./init.sh --quick --snapshot` PASS。
- 待办：实现 F-006 服务骨架；Gateway 配置必须等 F-006 直连 health 通过后再动。

### 2026-11-23 harness 文件重写

- 目标：把“约束与守卫”升级为“可运行 harness”。
- 决策：不新增根级 `MEMORY.md`；沿用 `zero-one-10wms/.workbuddy-ai/memory/MEMORY.md` 作为稳定事实层，新增 `PROGRESS.md` 管当前状态，避免记忆与进度混在一起。
- 结果：`F-001` 已验证并置为 `passing`；`init.sh` 的 quick/cpp/frontend/java/snapshot 路径均跑通。
- 待办：补 `F-002` 浏览器冒烟；运行时基线 `F-004` 仍阻塞。

### 2026-11-23 AI-Agent 轨道 feature 登记

- 目标：按技术选型 ADR 登记 AI-Agent 功能条目并启动骨架项，不写代码。
- 决策：以 ADR 第 5 节实施顺序拆成 4 条功能：`F-006` 骨架+health → `F-007` 网关路由 → `F-008` LLMProvider → `F-009` 6 工具；`F-006` 置唯一 `in_progress`。
- 结果：`feature_list.json` 与 `PROGRESS.md` 已同步；JSON 校验通过；无代码改动，无运行时证据。
- 待办：实现 `F-006` 并补 `init.sh --agent`；`F-002`/`F-003` 保持排队。

### 2026-11-23 AI-Agent 轨道补全 + 优先级重排 + 单仓推送

- 目标：把 Agent 轨道登记完整（F-006~F-013）、解决 F-002 优先级冲突、取消 gitlink 并把整个项目推上远端。
- 决策：`priority` 唯一连续 1..13，AI-Agent 轨道整体前置；父仓库改为单仓模式直接跟踪 `zero-one-10wms/` 全部文件，子模块仓库保留但不再同步指针；根 `.gitignore` 排除依赖/构建产物/密钥后允许 `git add -A`。
- 结果：`feature_list.json` 13 条（`F-006` 唯一 `in_progress`）、`PROGRESS.md`、`.gitignore`、`MEMORY.md` 已同步并提交推送。
- 待办：实现 `F-006`（`wms-agent/` 从零创建），再按 `F-007`→`F-013` 顺序推进。
