# Progress

> 当前状态与下一步。功能级验证步骤和证据在 `feature_list.json`；稳定事实与决策在 `.workbuddy-ai/memory/MEMORY.md`。

## 当前已验证状态

- 日期：2026-11-23
- 父仓库：`main` @ `fcbc02b`（Merge gitee/main: 展平源码快照 + ADR）
- 子模块：`v1.0.0` @ `7ef08d88`
- 跟踪结构：父仓库**无 gitlink 条目**，已展平跟踪 `zero-one-10wms/` 下 6456 个文件（含 `feature_list.json`、`PROGRESS.md`、`documents/07、AI-Agent化/*`）；子模块仓库内这三个路径仍为未跟踪，暂不重复提交。
- 标准启动路径：`cd zero-one-10wms && ./init.sh --quick`（Git Bash）
- 标准验证路径：`./init.sh --quick` → `./init.sh --cpp` → 按功能跑 `--java <module>` / `--frontend` / `--verify`
- 当前工作项：`F-006` wms-agent Python 服务骨架与 `/agent/health` 健康检查（`in_progress`，`not_started`）
- AI-Agent 轨道顺序：`F-006` 骨架 → `F-007` 网关路由 → `F-008` LLMProvider → `F-009` 6 工具
- 排队项：`F-002` 储位管理前端页面、`F-003` 商品明细只读页面（均 `not_started`）；`F-004` 运行时基线仍 `blocked`
- 已通过项：`F-001` harness 入口、`F-005` 其他配置 25 项（均 `passing` + `static_pass`）
- 当前 blocker：本机无 cmake/MSVC，C++ 只能 `static_pass + runtime_unverified`；运行时/端到端环境未就绪（`F-004`）；本机无 `bash` 在 PATH，`init.sh` 需用 Git Bash 执行

## 本轮记录

- 目标：按 `documents/07、AI-Agent化/技术选型ADR.md`（Accepted，17 条决策）登记 AI-Agent 轨道功能条目并启动第一条，不写代码。
- 已完成：
  - `feature_list.json` 登记 4 条：`F-006` 骨架+health、`F-007` 网关 `/agent/**` 路由、`F-008` LLMProvider 抽象、`F-009` 6 个 L0 只读工具。
  - `F-006` 置 `in_progress`（唯一进行中项）；`F-007`/`F-008`/`F-009` 置 `not_started`，`verification_level` 均为 `not_started`，`evidence` 均为空。
  - `next_candidate` 由 `F-002` 改为 `F-006`；`source_of_truth` 增列 ADR 与工具清单两份文档。
  - `PROGRESS.md` 同步基线、工作项、轨道顺序与风险。
- 运行过的验证：
  - `python -m json.tool feature_list.json`：PASS（可解析）
  - 自检脚本：PASS（9 条功能、ID 无重复、status 与 verification_level 取值合法、`in_progress` 唯一且为 `F-006`）
  - `git status` / `git log`：父仓库 `main @ fcbc02b`、子模块 `v1.0.0 @ 7ef08d88`
- 未验证：本轮无代码改动，未执行 `init.sh --quick`、未跑 Java/前端构建；F-006~F-009 均无运行时证据，ADR 全部为设计时决策 `static_pass + runtime_unverified`。
- 下一步：实现 `F-006`（`wms-agent/` 目录 + `pyproject.toml`/`uv.lock` + 最小 FastAPI + `/agent/health`），并把 `init.sh` 扩展 `--agent` 模式；完成后按 `F-006.verification` 逐步执行并写 evidence。
- 已知风险：
  - 前端构建通过不代表页面运行通过；储位管理页面尚未做浏览器冒烟。
  - 本机 `pnpm` 不在 PATH，前端命令需 `corepack pnpm`；本机 `python` 不在 PATH（DSH 内置 Python 可用于 JSON 校验）。
  - 工作区存在用户既有未跟踪改动（`.dsh-scratch/`、`vc140.pdb`、`wms-frontend/node_modules.bak/`、`wms-frontend/src/apis/chuweiguanli/`、`wms-frontend/src/views/chuweiguanli/`、`wms-frontend/src/views/base-data/Commodity-detail/` 等），不要清理或覆盖。
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

