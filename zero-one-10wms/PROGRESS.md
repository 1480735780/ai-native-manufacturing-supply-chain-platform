# Progress

> 当前状态与下一步。功能级验证步骤和证据在 `feature_list.json`；稳定事实与决策在 `.workbuddy-ai/memory/MEMORY.md`。

## 当前已验证状态

- 日期：2026-11-23
- 父仓库：`main` @ `c988cd5`（F-006~F-010 已提交；F-011~F-013 改动待提交）
- 嵌套历史仓库：`zero-one-10wms/.git` 仍存在，HEAD `7ef08d8`，但父仓库不维护其指针，不作为提交目标
- 跟踪结构：**单仓模式**。父仓库索引中 `zero-one-10wms/*` 全部为 mode `100644` 普通文件，无 `160000` gitlink 条目；`zero-one-10wms/` 下的 ADR、`init.sh`、`AGENTS.md`、`architecture.md`、`process.md`、`feature_list.json`、`PROGRESS.md` 均已直接被父仓库跟踪。
- 推送范围：父仓库根新增 `.gitignore`，排除 `node_modules/`、`node_modules.bak/`（**2.55 GB**，本轮明确不入库）、`target/`、`dist/`、`*.class`、`*.jar`、`*.pdb`、`*.log`、`__pycache__/`、`*.pyc`、`.venv/`、`.env`/`.env.*`、`.idea/`、`.vs/`。其余文件全部入库（含 `.dsh-scratch/` 辅助脚本 6.4 MB / 210 文件）。
- 标准启动路径：`cd zero-one-10wms && ./init.sh --quick`（Git Bash）
- 标准验证路径：`./init.sh --quick` → `./init.sh --cpp` → 按功能跑 `--java <module>` / `--frontend` / `--verify` / `--agent`
- 当前工作项：**AI-Agent 轨道 F-006~F-013 全部完成**（`F-006`/`F-007`/`F-012`/`F-013` 为 `e2e_pass`，`F-008`/`F-009`/`F-010` 为 `unit_pass`，`F-011` 为 `passing` + `runtime_unverified`）；下一个候选 `F-002`（储位管理前端页面）
- AI-Agent 轨道顺序（已全部走完）：`F-006` 骨架 → `F-007` 网关路由 → `F-008` LLMProvider → `F-009` 6 工具 → `F-010` ReAct 循环与 `/agent/query` → `F-011` 前端悬浮窗 → `F-012` 状态持久化 → `F-013` `init.sh --agent`
- 优先级决策（2026-11-23）：`priority` 改为唯一连续序号 1..13，features 数组按 id 升序、排序键为 priority；AI-Agent 轨道整体前置，传统功能队列后移（F-002=11、F-003=12、F-004=13；F-005=5 保持不变）。
- 排队项：`F-002` 储位管理前端页面、`F-003` 商品明细只读页面（均 `not_started`）；`F-004` 运行时基线仍 `blocked`
- 已通过项：`F-001` harness 入口、`F-005` 其他配置 25 项（均 `passing` + `static_pass`）、`F-006`（`e2e_pass`）、`F-007`（`e2e_pass`）、`F-008`/`F-009`/`F-010`（`unit_pass`）、`F-011`（`passing` + `runtime_unverified`）、`F-012`（`e2e_pass`）、`F-013`（`e2e_pass`）
- 运行时底座（本轮实测）：本机 `192.168.101.91`；虚拟机 `192.168.89.128` 提供 Nacos 8848、Redis 6379、MySQL 3306，**PG 5432 未起**；本机原生 PostgreSQL 16.15 在 5432（库 `ragent`，`postgres`/`123456`，本轮 F-012 落库用它）
- 工具链实测：Python 3.14.7 = `D:\DownloadPackage\environment\python.exe`；uv 0.13.1 = `C:\Users\a\.local\bin\uv.exe`（**不在 PATH**）；JDK17 = `D:\DownloadPackage\environment\jdk-17.0.20.1+1`（PATH 上的 java 是 JDK8，不能用于 Spring Boot 3）；mvn = `D:\DownloadPackage\Maven\apache-maven-3.6.3-bin\apache-maven-3.6.3\bin\mvn.cmd`；Git Bash = `D:\DownloadPackage\environment\Git\Git\bin\bash.exe`（**不在 PATH**，本轮已用它跑通 `init.sh --agent`）
- 当前 blocker：本机无 cmake/MSVC，C++ 只能 `static_pass + runtime_unverified`；运行时/端到端环境未就绪（`F-004`）；`init.sh` 需用 Git Bash 执行；仓库只有 `public.pem` 无签发私钥且无 `wms-login` 实例，前端浏览器链路无法端到端验证

## 本轮记录

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
- 未验证：
  - 前端浏览器端到端链路：仓库与 `.m2` 的 wms-common jar 均无 `private.pem`（只有 460B `public.pem`），无法签发合法 JWT；Nacos 无 `wms-login` 实例，路由守卫 `src/routers/index.ts:139` 会因 `loadUser` 抛错到不了 default layout → `F-011` 记 `runtime_unverified`，需用户提供私钥或启动 `wms-login` 后用 agent-browser 复测。
  - 真实用户 JWT 经网关 → Java 业务端点的完整链路（Java 业务服务 `wms-j6-stockln` 等本机未启动）。
  - 网关 `inner-paths` 与 `RESOURCE_ROLES_MAP` 的实际判定（判定在 starter jar 内，本环境 `open-authorization=false`）。
  - F-012 落库用的是本机原生 PostgreSQL 16.15，**未在虚拟机 pgvector 镜像上复验**。
- 下一步：`F-002` 储位管理前端页面（`next_candidate`）；`F-004` 运行时基线仍 `blocked`。
- 用户待办（可选）：若要把 trace 落到虚拟机，`192.168.89.128` 用 `pgvector/pgvector:pg16` 起库（库名 `ragent`），连接串 `postgresql+psycopg://postgres:postgres@192.168.89.128:5432/ragent`；不拉也不阻塞，F-006~F-013 均已通过，缺失时按 `persisted=false` 降级。
- 已知风险：
  - **AgentScope 探针已通过**（`uv pip install --dry-run agentscope` → 97 包可解析、agentscope 2.0.12 兼容 Python 3.14.7，故 F-010 不记 blocked）；但 ReAct 循环按方案自研 `LLMProvider` + ToolSchema 契约实现，**未引入 AgentScope 依赖**（避免引入未被使用的 73 个传递依赖）——与 `feature_list.json` F-010 标题/notes 一致记录。
  - Gateway `inner-paths` 通配符行为在 starter jar 内，本环境因鉴权开关关闭未能区分 white/inner 差异；F-010 用 Python 侧 401 实测兜底。
  - JWT 签发私钥明文存在于仓库历史，是独立安全问题；后续需轮换密钥并清理历史。
  - Python 不查 Redis 注销黑名单；已登出 token 在 JWT 过期前直连 Python 仍是理论风险。
  - 本机 `postgres/123456` 是明文口令且本轮在库中建了 `ragent` 库，属测试环境痕迹，交付前宜改口令或清理该库。

## 最近会话（append-only）

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
