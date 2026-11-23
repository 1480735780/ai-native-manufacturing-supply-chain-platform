# Progress

> 当前状态与下一步。功能级验证步骤和证据在 `feature_list.json`；稳定事实与决策在 `.workbuddy-ai/memory/MEMORY.md`。

## 当前已验证状态

- 日期：2026-11-23
- 父仓库：`main` @ `2def3497`
- 子模块：`v1.0.0` @ `7ef08d88`
- gitlink：`7ef08d88`（与子模块 HEAD 一致）
- 标准启动路径：`cd zero-one-10wms && ./init.sh --quick`（Git Bash）
- 标准验证路径：`./init.sh --quick` → `./init.sh --cpp` → 按功能跑 `--java <module>` / `--frontend` / `--verify`
- 当前最高优先级功能：`F-001` 建立可执行的初始化、状态与验证入口（`passing`，`static_pass`）
- 下一个候选：`F-002` 储位管理前端页面（`not_started`）
- 当前 blocker：本机无 cmake/MSVC，C++ 只能 `static_pass + runtime_unverified`；运行时/端到端环境未就绪（`F-004`）

## 本轮记录

- 目标：按 harness 标准重写父/子 `AGENTS.md`、`architecture.md`、`process.md`，新增 `init.sh`、`feature_list.json`、`PROGRESS.md`，并把 `MEMORY.md` 收敛为稳定事实层。
- 已完成：
  - 父/子 `AGENTS.md` 补齐项目概览、标准命令、验证矩阵、完成定义、状态文件、开工/收尾流程。
  - `architecture.md` 补齐运行拓扑、模块地图、请求/数据契约、验证架构、可观测性和 ADR-lite。
  - `process.md` 合并固定流程与 Git 守卫，加入 WIP=1、完成证据、收尾交接、失败模式映射。
  - `init.sh` 提供 quick / cpp / java / frontend / verify / snapshot。
  - `feature_list.json` 建立种子功能面；`F-001` 已验证并置为 `passing`，`F-002`/`F-003` 待启动。
- 运行过的验证：
  - `./init.sh --quick`：PASS（工具链、关键文件、JSON、Git 基线）
  - `./init.sh --cpp`：PASS（C++ 模块注册、全部源码 `zh-dict.yaml` 无重复顶层键）
  - `./init.sh --frontend`：PASS（`vite build --mode production`，43.66s）
  - `./init.sh --java wms-j8-othermana`：PASS（Maven 离线编译）
  - `./init.sh --quick --snapshot`：PASS（JSONL 可解析，含 hash 链字段）
- 证据：已写入 `feature_list.json` 的 `F-001.evidence`。
- 下一步：评估 `F-002` 储位管理前端；需要运行时环境时先解 `F-004`。
- 已知风险：
  - 前端构建通过不代表页面运行通过；储位管理页面尚未做浏览器冒烟。
  - 本机 `pnpm` 不在 PATH，前端命令需 `corepack pnpm`。
  - 本机无 `bash` 在 PATH，`init.sh` 需用 Git Bash 执行。
  - 工作区存在用户既有未跟踪改动（`.dsh-scratch/`、`.workbuddy-ai/`、`wms-frontend/src/apis/chuweiguanli/`、`wms-frontend/src/views/chuweiguanli/`、`wms-frontend/src/views/base-data/Commodity-detail/`、`node_modules.bak/` 等），不要清理或覆盖。

## 最近会话（append-only）

### 2026-11-23 harness 文件重写

- 目标：把“约束与守卫”升级为“可运行 harness”。
- 决策：不新增根级 `MEMORY.md`；沿用 `zero-one-10wms/.workbuddy-ai/memory/MEMORY.md` 作为稳定事实层，新增 `PROGRESS.md` 管当前状态，避免记忆与进度混在一起。
- 结果：`F-001` 已验证并置为 `passing`；`init.sh` 的 quick/cpp/frontend/java/snapshot 路径均跑通。
- 待办：补 `F-002` 浏览器冒烟；运行时基线 `F-004` 仍阻塞。
