# 流程、状态与 Git 守卫

> 本文件定义每轮会话的固定动作、状态写入、验证证据和 Git 防漂移规则。hook 是加速器，固定流程是底座。

## 1. 强制等级与边界

- 仓库层：单仓可配 `core.hooksPath` + `pre-commit` / `post-checkout`；当前仓库尚未落地 `.githooks/`，以固定流程为准。
- 会话层：WorkBuddy 支持 `PreToolUse` / `SessionStart`；项目级 hook 的桌面端生效性见 `../enforcement-capability.md`。在正式复验前按 B 档（Git 层 + 固定流程）执行，不宣称 A 档。
- 威胁模型：防无意识漏跑、半自动外部进程切分支/改 HEAD/恢复 gitlink、会话间漂移；不防本地有意篡改，审计链不是安全签名。
- hook 挡不住 `--no-verify`、plumbing；所以开工、暂存前、提交前、疑似干扰后四个时机必须人工复核。

## 2. 任务类型与 WIP=1

开工先判断任务类型：

- 执行类：读代码、改代码、跑验证。
- 分析/评审类：只读，不擅自改文件。
- 方案类：给路径、取舍、风险，不直接实现，除非用户明确要求。

同一时间只允许一个 `in_progress` 功能；功能从 `feature_list.json` 选，优先级数字越小越优先。

## 3. 开工流程

1. `pwd`，确认父仓库根目录。
2. 读 `AGENTS.md`（父/子）、`PROGRESS.md`、`feature_list.json`。
3. 记录基线快照（见第 4 节），写入 `<STATE_DIR>`。
4. 在 Git Bash 执行 `cd zero-one-10wms && ./init.sh --quick --snapshot`。
5. 复核：单仓分支与 HEAD、`zero-one-10wms` 普通目录树、脏改动分类、关键文件存在性。
6. 若基础状态损坏（构建/启动路径坏了），先修基础状态，不叠新功能。
7. 选一个最高优先级功能，置为 `in_progress`，写清验证步骤；开始前把本轮目标写入 `PROGRESS.md`。

## 4. 基线快照（5 类字段）

`<STATE_DIR>` 为 append-only 状态目录；优先读环境变量 `WMS_STATE_DIR`。当前受桌面工作区权限限制，默认 `$PARENT_ROOT/.wms-harness-state`（已 ignore）；生产/CI 可指向仓库外路径。

字段：

1. 仓库身份：父仓库路径、关键 remote（只记名称 + URL 指纹，去掉 userinfo/query/token）。
2. 单仓状态：分支、HEAD。
3. 目录结构：`zero-one-10wms` 在父仓库 HEAD 中必须是 `040000 tree`，不得出现 `160000` gitlink。
4. 脏改动清单：完整 porcelain 列表，分类 baseline / expected / unexpected。
5. 关键文件守卫：存在性 + 内容哈希（授权修改例外）。

记录示例（JSONL，一行一条）：

```json
{"ts":"2026-11-23T12:00:00+08:00","event":"session_start","repository":{"branch":"main","head":"2def349","layout":"single-repo"},"dirty":{"baseline":3,"expected":1,"unexpected":0},"files":{"AGENTS.md":"<sha256>","process.md":"<sha256>"},"prev_hash":"<sha256>","hash":"<sha256>"}
```

## 5. 四个守卫时机

- 开工时：写快照。
- 暂存前：确认暂存路径属于 expected。
- 提交前：复核基线，结构性漂移即停。
- 执行过分支切换、疑似外部干扰后：立即复核。

**结构性漂移即停**：分支/HEAD 变化、`zero-one-10wms` 变成 gitlink、关键文件丢失、预期外批量修改。

**允许变化**：本轮目标文件的增删改，只要能精确暂存。

## 6. 审计链（append-only）

每条记录含：时间、事件类型（`session_start` / `before_stage` / `before_commit` / `post_checkout` / `suspected_drift`）、单仓分支与 HEAD、目录模式、脏改动分类、关键文件哈希、本条哈希、上一条哈希。

- 只追加，不修改历史记录。
- 链路断裂（上一条哈希对不上）时报告并停止，不静默重建。
- 审计链用于发现意外漂移，不是防抵赖签名。

## 7. 基线更新授权

关键文件哈希变化不自动接受。必须记录：授权范围、授权原因、旧哈希、新哈希、对应任务或 commit；验证通过后才写入新基线，并留审计记录。未授权变化视为漂移。

## 8. 验证与完成证据

三层验证：

1. 静态层：构建、lint、类型检查、架构边界检查。
2. 行为层：单元测试、接口测试、核心 smoke test。
3. 系统层：端到端用户路径、真实启动、数据库副作用、资源清理、重启后持久化。

错误反馈必须可修复，至少写清：请求/命令、实际结果、期望结果、最可能的原因、下一步检查点。

状态标签：`static_pass` / `runtime_unverified` / `e2e_pass` / `blocked` / `not_started`。C++ 固定 `static_pass + runtime_unverified`，不得简写为“通过”。

完成定义：

- 用户可见行为已实现。
- `feature_list.json` 的验证步骤已执行。
- `evidence` 已记录命令、输出摘要、commit/截图/日志路径。
- 项目仍能按 `init.sh` 启动/构建。
- `PROGRESS.md` 已更新。

## 9. 收尾与交接

收尾检查：

- 标准启动路径仍可用。
- 基础验证仍通过，或未验证项已写明原因。
- `PROGRESS.md` 已更新。
- `feature_list.json` 反映真实状态。
- 没有“看起来 passing 但没证据”的功能。
- 临时产物、调试日志、未跟踪垃圾已清理或说明。
- 下一步最佳动作明确。
- 仓库处于可继续工作的安全状态。

交接摘要写五件事：

1. 当前已验证内容。
2. 本轮改动。
3. 仍损坏或未验证内容。
4. 下一步最佳动作和不要动的区域。
5. 启动、验证、调试命令。

## 10. 提交规则

- 单仓模式只在父仓库提交；禁止恢复 `zero-one-10wms` gitlink 或提交嵌套仓库指针。
- 禁止 `git add .` / `git add -A` / 未审查整目录暂存。
- 用户既有改动不覆盖、不 stash、不 checkout。
- 提交前跑 `git diff --cached --stat` 和 `git diff --cached`，确认只含本轮目标。
- 不强制推送，不绕过 hooks；`--no-verify` 只在用户明确授权且记录原因时使用。

## 11. 异常处理

- **分支漂移**：以 reflog 与提交图裁定权威侧；只读摆证据，由用户拍板，不自动 checkout / reset。
- **文档丢失**：从 git 历史找回，不凭记忆重建。
- **备份被破坏**：`<STATE_DIR>` 链路断裂时报告并停止；当前默认在仓库内且 ignore，执行 clean/reset 前必须先迁移或备份。
- **构建/启动坏了**：先修基础状态，不继续叠功能；记录最小复现。

## 12. 双实验（档位确认）

当前档位未正式复验，按 B 档固定流程执行。复验方法：

1. `SessionStart` 标记实验：最小项目级 hook 向 `<STATE_DIR>` 写标记。
2. `PreToolUse` deny 实验：matcher 用 `*` 或对应工具名；脚本读 stdin 的 `tool_input.command`，含 `HARNESS_EXP_DENY_PROBE` 返回 deny；执行探针命令应被阻断。
3. 双过 → A 档；只过第一个或都不过 → B 档，会话层以固定流程为准。

复验后更新 `../enforcement-capability.md` 和本节，不凭记忆宣称档位。

## 13. 失败模式 → 修复动作

| 失败模式 | 表现 | 修复 |
|---|---|---|
| 新会话摸黑 | 反复探索项目 | 更新 `PROGRESS.md` / `MEMORY.md` |
| 范围蔓延 | 同时开多个功能 | `feature_list.json` + WIP=1 |
| 提前宣布完成 | 只说“写完了” | `evidence` + 完成定义 |
| 启动脆弱 | 每轮重新学启动 | `init.sh` + 标准命令 |
| 交接薄弱 | 新会话不知道哪里坏 | 五段式交接摘要 |
| 指令膨胀 | AGENTS 越写越长 | 短入口 + 深链接 + 定期审计 |
| 文档过时 | 文档与代码漂移 | 知识靠近代码，改代码时同步文档 |
