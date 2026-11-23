# Progress

> 当前状态与下一步。功能级验证步骤和证据在 `feature_list.json`；稳定事实与决策在 `.workbuddy-ai/memory/MEMORY.md`。

## 当前已验证状态

- 日期：2026-11-23
- 父仓库：`main` @ `799b9b0`（本轮：登记 F-006~F-013、重排 priority、加根 `.gitignore` 并全量提交）；其后仅追加一次基线同步提交
- 子模块：`v1.0.0` @ `7ef08d88`（独立仓库仍在 `zero-one-10wms/.git`，但父仓库不再维护其指针）
- 跟踪结构：**单仓模式**。父仓库索引中 `zero-one-10wms/*` 全部为 mode `100644` 普通文件，无 `160000` gitlink 条目；`zero-one-10wms/` 下的 ADR、`init.sh`、`AGENTS.md`、`architecture.md`、`process.md`、`feature_list.json`、`PROGRESS.md` 均已直接被父仓库跟踪。
- 推送范围：父仓库根新增 `.gitignore`，排除 `node_modules/`、`node_modules.bak/`（**2.55 GB**，本轮明确不入库）、`target/`、`dist/`、`*.class`、`*.jar`、`*.pdb`、`*.log`、`__pycache__/`、`*.pyc`、`.venv/`、`.env`/`.env.*`、`.idea/`、`.vs/`。其余文件全部入库（含 `.dsh-scratch/` 辅助脚本 6.4 MB / 210 文件）。
- 标准启动路径：`cd zero-one-10wms && ./init.sh --quick`（Git Bash）
- 标准验证路径：`./init.sh --quick` → `./init.sh --cpp` → 按功能跑 `--java <module>` / `--frontend` / `--verify`；Agent 轨道后续加 `--agent`（见 `F-013`）
- 当前工作项：`F-006` wms-agent Python 服务骨架与 `/agent/health` 健康检查（`in_progress`，`not_started`）
- AI-Agent 轨道顺序：`F-006` 骨架 → `F-007` 网关路由 → `F-008` LLMProvider → `F-009` 6 工具 → `F-010` ReAct 循环与 `/agent/query` → `F-011` 前端悬浮窗 → `F-012` 状态持久化 → `F-013` `init.sh --agent`
- 优先级决策（2026-11-23）：`priority` 改为唯一连续序号 1..13，features 数组按 id 升序、排序键为 priority；AI-Agent 轨道整体前置，传统功能队列后移（F-002=11、F-003=12、F-004=13；F-005=5 保持不变）。
- 排队项：`F-002` 储位管理前端页面、`F-003` 商品明细只读页面（均 `not_started`）；`F-004` 运行时基线仍 `blocked`
- 已通过项：`F-001` harness 入口、`F-005` 其他配置 25 项（均 `passing` + `static_pass`）
- 当前 blocker：本机无 cmake/MSVC，C++ 只能 `static_pass + runtime_unverified`；运行时/端到端环境未就绪（`F-004`）；本机无 `bash` 在 PATH，`init.sh` 需用 Git Bash 执行；`uv` 是否可用尚未核实（`F-006`/`F-013` 前提）

## 本轮记录

- 目标：以当前仓库为准真正登记 F-006 起的 Agent 功能；按规则解决 F-002 优先级冲突；取消 gitlink 思路，把整个 AIWMSproject 的文件正常提交并推送远端。
- 已完成：
  - `feature_list.json` 扩到 13 条：新增 `F-010` ReAct 循环 + `/agent/query`、`F-011` 前端悬浮 AI 对话框、`F-012` PostgreSQL `wms_agent` 状态持久化、`F-013` `init.sh --agent` harness 集成（对应 ADR 第 5 节第 5~8 步）。
  - `F-006`~`F-009` 全部改成**仓库实证**写法：F-009 新增 `tool_endpoints` 字段，逐条记录 6 个工具的真实方法、路径与 Controller 文件行号（`StockQueryController.java:30,39`、`ExpiryWarningController.java:24,30`、`NoUpController.java:35,46`、`DashboardController.java:30,38,52,66,79,110,123,136,148`、`DelayController.java:24,51`）；F-007 记录网关 `application.yaml` 既有路由行号（`/dashboard/**` 37-40、`/stockln/**,/stock/**` 85-88、`/daycheck/**` 89-92、C++ 静态路由样式 103-106）与 agent-route 的新增位置。
  - Agent 轨道条目新增 `adr_refs` 字段；`rules` 增加 `priority_rule` 与 `agent_track_order`。
  - 优先级重排：`F-002` 2→11、`F-003` 3→12、`F-004` 4→13、`F-006` 6→2、`F-007` 7→3、`F-008` 8→4、`F-009` 9→6，新增 `F-010`=7、`F-011`=8、`F-012`=9、`F-013`=10；`F-001`=1、`F-005`=5 不变。
  - 父仓库根新增 `.gitignore`（依赖/构建产物/密钥排除规则）。
  - 全量 `git add -A` 后提交并推送（单仓模式，无 gitlink 操作）。
- 运行过的验证：
  - `python -m json.tool feature_list.json`：PASS（可解析）
  - 自检脚本 `.dsh-scratch/check_feature_list.py`：PASS（13 条功能、ID 无重复且升序、priority 唯一且连续 1..13、status/verification_level 取值合法、passing 均有 evidence、`in_progress` 唯一为 `F-006`、F-009 含 6 条 tool_endpoints）
  - `git ls-files -s zero-one-10wms`：PASS，条目均为 `100644`，无 `160000` gitlink
  - `git add -An` 干跑：PASS，共 205 项待加入，其中落在 `node_modules` 下的为 0 项
- 未验证：本轮无代码改动，未执行 `init.sh --quick`、未跑 Java/前端构建；`F-006`~`F-013` 均无运行时证据，ADR 全部为设计时决策 `static_pass + runtime_unverified`。
- 下一步：实现 `F-006`（`wms-agent/` 目录 + `pyproject.toml`/`uv.lock` + 最小 FastAPI + `/agent/health`），并按 `F-006.verification` 执行 `uv sync` / `pytest` 并写 evidence；随后 `F-007` 网关路由。
- 已知风险：
  - 推送范围为“除依赖与构建产物外的全部文件”；`wms-frontend/node_modules.bak/`（2.55 GB）仍在磁盘但未入库，如需归档请自行处理。
  - `.dsh-scratch/` 内含文档抽取中间产物（emmx media PNG、txt/XML），本轮按“全部文件”原则入库，后续如需清理需重新提交删除。
  - 前端构建通过不代表页面运行通过；储位管理页面尚未做浏览器冒烟。
  - 本机 `pnpm` 不在 PATH，前端命令需 `corepack pnpm`；本机 `python` 不在 PATH（DSH 内置 Python 可用于 JSON 校验）。
  - ADR 决策全部为设计时结论；Python 侧任何 `passing` 都必须有运行时/回放证据，不允许静态通过即判完成。

## 最近会话（append-only）

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
