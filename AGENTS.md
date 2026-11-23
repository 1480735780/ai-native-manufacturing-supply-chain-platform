# AIWMSproject 根指令

## 项目概览

- 目标：以 `zero-one-10wms` 为载体完成 WMS 功能补齐、验证与交付。
- 仓库结构：**单仓模式**。父仓库直接跟踪 `zero-one-10wms/**` 全部业务与文档文件，不维护 gitlink；`zero-one-10wms/.git` 仅是历史遗留嵌套仓库，不作为提交目标。
- 当前阶段：功能补齐与 harness 建设并行；配置类功能多为静态完成，运行时/端到端证据不足。
- 技术栈：Java / C++ / Vue3 三栈，详见子模块 `AGENTS.md` 与 `architecture.md`。

## 信息优先级

冲突时按以下顺序判断：

1. 当前运行环境的系统与开发者规则
2. 用户最新明确指令
3. 父/子仓库 `AGENTS.md` 与项目规则
4. 已验证的代码、测试、文档和运行结果
5. `feature_list.json` / `PROGRESS.md` 的当前状态
6. 稳定记忆（`MEMORY.md`、历史决策）
7. 模型推断

旧记忆与仓库事实冲突时，重新验证，不沿用过期结论。

## 标准流程（每轮会话）

### 开工

1. `pwd`，确认在父仓库根目录。
2. 读本文件、`zero-one-10wms/AGENTS.md`、`zero-one-10wms/PROGRESS.md`、`zero-one-10wms/feature_list.json`。
3. 记录单仓 Git 基线：分支、HEAD、`zero-one-10wms` 必须是普通目录树、脏改动分类、关键文件存在性（按 `zero-one-10wms/process.md`）。
4. 在 Git Bash 中执行 `cd zero-one-10wms && ./init.sh --quick --snapshot`。
5. 只选择一个最高优先级功能，置为 `in_progress`；同一时间只做一个。

### 收尾

1. 复核基线；结构性漂移即停。
2. 跑适用验证；不能跑时写明原因。
3. 更新 `PROGRESS.md` 和 `feature_list.json`，写入 evidence。
4. 清理临时产物；不覆盖用户既有改动。
5. 报告：已改 / 已验证 / 未验证 / 剩余风险 / 下一步。

## 硬约束

- 只在父仓库提交；`zero-one-10wms` 不作为子模块指针更新，禁止恢复 gitlink。
- 提交只允许 `git add -- <明确文件路径>`；禁止 `git add .` / `git add -A` / 未审查整目录暂存。
- 用户既有改动一律视为 baseline：不覆盖、不 stash、不 checkout 丢弃。
- C++ 本机无 MSVC，固定记 `static_pass + runtime_unverified`，不得简写为“通过”。
- 不删除或削弱测试来制造通过；不把日志、密钥、临时推断写入 `MEMORY.md`。
- 单仓内仍保持目录职责：业务代码在 `zero-one-10wms/`，父根只放项目级文档、harness 与工作日志。

## 完成定义

一个功能只有同时满足以下条件才算完成：

1. 用户可见行为已实现。
2. `feature_list.json` 的验证步骤已执行。
3. 验证结果已写入 `evidence`。
4. 项目仍能按 `init.sh` 的标准路径启动/构建。
5. `PROGRESS.md` 已更新，下一步明确。

## 状态文件

| 文件 | 职责 |
|---|---|
| `zero-one-10wms/feature_list.json` | 功能状态、验证步骤、证据 |
| `zero-one-10wms/PROGRESS.md` | 当前已验证状态、阻塞、下一步 |
| `zero-one-10wms/.workbuddy-ai/memory/MEMORY.md` | 稳定事实、已验证命令、明确决策 |
| `.workbuddy-ai/memory/YYYY-MM-DD.md` | 父仓库会话日志 |

## 深链接

- 业务仓库规则：`zero-one-10wms/AGENTS.md`
- 架构与工程约束：`zero-one-10wms/architecture.md`
- 流程与 Git 守卫：`zero-one-10wms/process.md`
- 强制能力探针：`enforcement-capability.md`
- 功能事实源：父仓库《差距分析与补齐规划》报告 + 子模块 `documents/01、项目计划/`
