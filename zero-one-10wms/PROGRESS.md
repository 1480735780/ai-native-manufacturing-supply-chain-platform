# Progress

> 当前状态与下一步。功能级验证步骤和证据在 `feature_list.json`；稳定事实与决策在 `.workbuddy-ai/memory/MEMORY.md`。

## 当前已验证状态

- 日期：2026-11-23
- 父仓库：`main` @ `9a5260c`（本轮开工基线；尚未提交本轮设计文档改动）
- 嵌套历史仓库：`zero-one-10wms/.git` 仍存在，HEAD `7ef08d8`，但父仓库不维护其指针，不作为提交目标
- 跟踪结构：**单仓模式**。父仓库索引中 `zero-one-10wms/*` 全部为 mode `100644` 普通文件，无 `160000` gitlink 条目；`zero-one-10wms/` 下的 ADR、`init.sh`、`AGENTS.md`、`architecture.md`、`process.md`、`feature_list.json`、`PROGRESS.md` 均已直接被父仓库跟踪。
- 推送范围：父仓库根新增 `.gitignore`，排除 `node_modules/`、`node_modules.bak/`（**2.55 GB**，本轮明确不入库）、`target/`、`dist/`、`*.class`、`*.jar`、`*.pdb`、`*.log`、`__pycache__/`、`*.pyc`、`.venv/`、`.env`/`.env.*`、`.idea/`、`.vs/`。其余文件全部入库（含 `.dsh-scratch/` 辅助脚本 6.4 MB / 210 文件）。
- 标准启动路径：`cd zero-one-10wms && ./init.sh --quick`（Git Bash）
- 标准验证路径：`./init.sh --quick` → `./init.sh --cpp` → 按功能跑 `--java <module>` / `--frontend` / `--verify`；Agent 轨道后续加 `--agent`（见 `F-013`）
- 当前工作项：`F-011` 前端全局悬浮 AI 对话框（`in_progress`）；`F-006`（服务骨架+health）、`F-007`（网关 `/agent/**` 路由）已 `e2e_pass`，`F-008`（LLMProvider+mock 回放）、`F-009`（6 工具接入）、`F-010`（ReAct + `/agent/query`）已 `passing`（`unit_pass`）
- AI-Agent 轨道顺序：`F-006` 骨架 → `F-007` 网关路由 → `F-008` LLMProvider → `F-009` 6 工具 → `F-010` ReAct 循环与 `/agent/query` → `F-011` 前端悬浮窗 → `F-012` 状态持久化 → `F-013` `init.sh --agent`
- 优先级决策（2026-11-23）：`priority` 改为唯一连续序号 1..13，features 数组按 id 升序、排序键为 priority；AI-Agent 轨道整体前置，传统功能队列后移（F-002=11、F-003=12、F-004=13；F-005=5 保持不变）。
- 排队项：`F-002` 储位管理前端页面、`F-003` 商品明细只读页面（均 `not_started`）；`F-004` 运行时基线仍 `blocked`
- 已通过项：`F-001` harness 入口、`F-005` 其他配置 25 项（均 `passing` + `static_pass`）、`F-006`（`e2e_pass`）、`F-007`（`e2e_pass`）、`F-008`/`F-009`/`F-010`（`unit_pass`）
- 运行时底座（本轮实测）：本机 `192.168.101.91`；虚拟机 `192.168.89.128` 提供 Nacos 8848、Redis 6379、MySQL 3306，**PG 5432 未起**（F-012 需要）；本机有原生 PostgreSQL 16（5432）但密码与 compose 凭证不同
- 工具链实测：Python 3.14.7 = `D:\DownloadPackage\environment\python.exe`；uv 0.13.1 = `C:\Users\a\.local\bin\uv.exe`（**不在 PATH**）；JDK17 = `D:\DownloadPackage\environment\jdk-17.0.20.1+1`（PATH 上的 java 是 JDK8，不能用于 Spring Boot 3）；mvn = `D:\DownloadPackage\Maven\apache-maven-3.6.3-bin\apache-maven-3.6.3\bin\mvn.cmd`
- 当前 blocker：本机无 cmake/MSVC，C++ 只能 `static_pass + runtime_unverified`；运行时/端到端环境未就绪（`F-004`）；`init.sh` 需用 Git Bash 执行；uv 用户级 cache 异常，F-006 起改用项目内 `.uv/cache`

## 本轮记录

- 目标：按 `wms-agent/docs/implement/问数Agent实施方案.md` 推进问数 Agent，本轮完成 `F-008`（LLMProvider + mock 回放）、`F-009`（6 工具接入 + Python 侧鉴权）、`F-010`（ReAct 循环 + `POST /agent/query` + `GET /agent/trace/{traceId}`）。
- 已完成：
  - F-008：`app/contracts.py`（Message/ToolCall/ToolSchema/ModelReply）、`app/llm/provider.py`（`LLMProvider` Protocol + `build_provider`）、`app/llm/mock.py`（有序回放、耗尽即报错）、`app/llm/openai_compatible.py`（httpx 直调 Chat Completions，异常不含 Key）、fixture `single_tool_stock.json` / `two_step.json`。
  - F-009：`app/tools/registry.py`（6 工具 + Pydantic 参数模型，`extra="forbid"`）、`app/tools/gateway_client.py`（只 GET、透传 `Authorization: Bearer`、3s 超时）、`app/tools/adapter.py`（两套命名映射、分页转 `pageIndex/pageSize`、TREND count 截断、`{rows,total,empty}` 归一化、10000/9995/9994/9999 语义、9999→空结果、v1 只 1 次尝试）、`app/tools/sanitizer.py`（≤20 行/≤4000 字符、删除审计与体积面积字段、`imCarMobile`→`138****5678`、`imCarDri`→`王*`）、`app/security.py`（PyJWT RS256 + 强制 `exp`、`user` 头仅交叉校验记 warning）、`app/routers/tools.py`。
  - F-010：`app/agent/react.py`（自研 ReAct，`MAX_TOOL_ROUNDS=2`，第 2 轮后强制最终答案，工具失败回喂模型不抛异常）、`app/agent/trace.py`（`sha256:` digest、不落完整结果与 JWT）、`app/agent/service.py`（提示词、traceId/sessionId、`{code,message,data}` 外壳、失败保留已完成的 toolCalls）、`app/routers/query.py`、`app/storage/{store,memory}.py`（F-012 前默认内存后端，`persisted=false`）。
  - 配置补充：`WMS_AGENT_TOOL_TIMEOUT_SECONDS`（默认 3）、`WMS_AGENT_LLM_SCENARIO_PATH`（mock 回放场景文件，供运行时离线回放）。
- 运行过的验证：
  - `uv run pytest` → **61 passed**（F-008 11 例 + F-009 若干 + F-010 `tests/test_query_replay.py` 12 例）。
  - 运行时（后台 job `pwsh-2c8e4c1c20a94844`，127.0.0.1:11200）：`/agent/health` → 200 `{"status":"ok"}`；`POST /agent/query` 无 token → 401 `{"code":401,"message":"缺少 Bearer token","data":null}`；无效签名 token → 401 `{"code":401,"message":"token 无效","data":null}`；带临时自签 RSA 测试密钥的合法 token → 200 `code=10000`，`toolCalls` 记录 `STOCK-QUERY → /stock/inventory-query/query-all`、`status=error`、`errorCode=401`（未编造数据）。
  - 经网关 `POST http://127.0.0.1:10001/agent/query`（非仓库签名 token）→ 网关自身 401『暂未登录或TOKEN已经过期』：**网关会独立校验 `Authorization` 头**，即使 Nacos 把 `open-authorization` 设为 `false`。
  - `python -m json.tool feature_list.json`：PASS。
- 未验证：
  - 真实用户 JWT 经网关 → Java 业务端点的完整链路：仓库只有 `public.pem`、无私钥，且 Java 业务服务（`wms-j6-stockln` 等）本机未启动；工具调用已实测到"发出请求并如实记录错误码"为止。
  - 网关 `inner-paths` 与 `RESOURCE_ROLES_MAP` 的实际判定（判定在 starter jar 内，本环境鉴权开关关闭）。
- 下一步：`F-011` 前端全局悬浮对话框（独立 axios 实例 timeout=60000）→ `F-012` PG 持久化 → `F-013` `init.sh --agent`。
- 用户待办：F-012 需要 PostgreSQL，建议在虚拟机 `192.168.89.128` 用 `pgvector/pgvector:pg16` 起库（库名 `ragent`），连接串 `postgresql+psycopg://postgres:postgres@192.168.89.128:5432/ragent`；F-006~F-011/F-013 不依赖它，缺失时按 `persisted=false` 降级。
- 已知风险：
  - **AgentScope 探针已通过**（`uv pip install --dry-run agentscope` → 97 包可解析、agentscope 2.0.12 兼容 Python 3.14.7，故 F-010 不记 blocked）；但 ReAct 循环按方案自研 `LLMProvider` + ToolSchema 契约实现，**未引入 AgentScope 依赖**（避免引入未被使用的 73 个传递依赖）——与 `feature_list.json` F-010 标题/notes 一致记录。
  - Gateway `inner-paths` 通配符行为在 starter jar 内，本环境因鉴权开关关闭未能区分 white/inner 差异；F-010 用 Python 侧 401 实测兜底。
  - JWT 签发私钥明文存在于仓库历史，是独立安全问题；后续需轮换密钥并清理历史。
  - Python 不查 Redis 注销黑名单；已登出 token 在 JWT 过期前直连 Python 仍是理论风险。

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
