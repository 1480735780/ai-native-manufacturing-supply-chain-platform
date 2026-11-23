# zero-one-10wms 项目规则

> 本文件是代码主战场的入口；父仓库 `../AGENTS.md` 管仓库关系与提交红线；全局行为契约在用户级 `SOUL.md`。深层细节按需加载，不在此重复。

## 项目概览

- 产品：仓储管理系统（WMS），覆盖基础资料、入库、库内、出库、盘点、计费、报表等仓库履约流程。
- 技术栈：Java（Spring Cloud Alibaba / Spring Boot 2.3 / MyBatis-Plus）、C++（oatpp / CMake）、Vue3（Vite / Element Plus / Pinia）、MySQL、Redis、Nacos、RocketMQ、FastDFS、Jenkins。
- 当前阶段：功能补齐与运行时验证并行；配置类功能多为静态完成，C++/端到端运行证据仍不足。
- 核心用户路径：登录 → 基础资料 → 入库/上架 → 库存查询/库内作业 → 出库 → 盘点/计费/报表。

## 目录结构

| 路径 | 职责 |
|---|---|
| `wms-java/` | Java 微服务：`wms-common`、`wms-domain`、`wms-apis`、`wms-gateway`、`wms-oauth2`、`wms-login` 及 `wms-j1..j8-*` 业务模块 |
| `wms-cpp/` | C++ oatpp 微服务：`lib-*` 基础库、`wms-c1..c8-*` 业务模块、`arch-tests` |
| `wms-frontend/` | Vue3 前端：`src/apis/` 接口层、`src/views/` 页面、文件路由与 `definePage` 菜单 |
| `documents/` | 需求、数据库、编码规范、环境搭建、版本计划 |
| `nacos-config/` | Nacos 配置样例 |
| `.dsh-scratch/` | 编码探测、静态校验等辅助脚本（不提交业务代码） |

## 标准命令

### 初始化与基线

```bash
# 在 Git Bash 中执行（Windows）
cd zero-one-10wms
./init.sh --quick          # 环境、状态文件、Git 基线、关键文件检查
./init.sh --cpp            # C++ 模块注册与词条重复键静态检查
./init.sh --verify         # Java 编译 + 前端构建 + C++ 静态检查（较慢）
```

> 本机若无 `bash`，用 Git Bash 打开本目录执行；PowerShell 不能直接运行 `.sh`。

### Java

```bash
cd wms-java
mvn -o -pl <module> -am compile -DskipTests
# 示例：mvn -o -pl wms-j8-othermana -am compile -DskipTests
```

- 全量：`mvn -o -DskipTests compile`
- 模块清单以 `wms-java/pom.xml` 的 `<modules>` 为准。

### 前端

```bash
cd wms-frontend
corepack pnpm install --frozen-lockfile   # 首次或依赖变更
corepack pnpm build                       # vite build --mode production
corepack pnpm lint                        # 定向 lint；存量告警先记录，不顺手全仓重构
```

- 包管理器固定 `pnpm@9.5.0`（`packageManager` 字段）；本机 `pnpm` 不在 PATH 时用 `corepack pnpm`。
- 页面路由/菜单由文件路由 + `definePage` 自动生成，新增页面不需要手写路由 SQL。

### C++

```bash
cd wms-cpp
./build.sh          # Linux/CI 环境；本机无 cmake/MSVC 时不执行
./run-back.sh       # 运行脚本，按模块 README 使用
```

- 本机无 C++ 编译环境：固定记 `static_pass + runtime_unverified`，不得写成“通过”。
- `init.sh --cpp` 当前覆盖模块注册与 `zh-dict.yaml` 重复顶层键；改动 C++ 代码时，再按范围运行 `.dsh-scratch/` 的类声明/定义、SQL、include、端点检查。

## 硬约束

完整清单见 `architecture.md`，以下为不可违反项：

1. C++ c7/c8 源码 UTF-8 与 GB18030 混存、行尾多为 CRLF；改文件前逐文件探测并原样保持。
2. oatpp `executeInsert` 返回 `LAST_INSERT_ID()`，varchar UUID 主键表判断插入成功用 `executeUpdate`（受影响行数）。
3. 路由 PATH 必须以 `/` 开头；端点唯一性按「HTTP 方法 + 路径」校验。
4. 批量删除一律 `SQLPARAMS_PUSH` 参数化，禁止字符串拼接。
5. `zh-dict.yaml` 同名顶层键会被 yaml-cpp 后者覆盖；新增词条前先查重复键。
6. 前端字典页统一走 `views/ware-config/composables/use-dict-page.ts` + `views/ware-config/components/DictPage.vue` 工厂；接口集中在 `apis/ware-config/index.js`；导出兼容 201。
7. 不覆盖、不 stash、不 checkout 用户既有改动；提交只暂存本轮明确路径。

## 验证矩阵

| 栈 | 静态层 | 行为层 | 系统层 | 允许的完成标签 |
|---|---|---|---|---|
| Java | `mvn ... compile` | 单测/接口测试（按需） | 启动服务 + 网关路由 + 真实接口 | `static_pass` / `e2e_pass` |
| 前端 | `corepack pnpm build` | 页面交互冒烟 | 浏览器端到端关键路径 | `static_pass` / `e2e_pass` |
| C++ | 静态校验脚本 | 无本机运行时 | CI/Linux 编译 + 服务启动 | `static_pass + runtime_unverified` |

- 配置类 CRUD 可以止步静态层，但必须在 `feature_list.json` 的 `evidence` 中写明 `static_pass` 和未验证项。
- 涉及资金、库存过账、PLC 指令、权限边界的改动，必须有运行时或端到端证据；没有证据只能记 `runtime_unverified` 或 `blocked`。

## 完成定义

功能从 `in_progress` 改为 `passing` 前，必须同时满足：

1. 用户可见行为已实现，范围只限该功能。
2. `feature_list.json` 中的 `verification` 步骤已实际执行。
3. 验证结果写入 `evidence`（命令、输出摘要、commit、截图/日志路径）。
4. 项目仍能按 `init.sh` 的标准路径启动或构建。
5. `PROGRESS.md` 已更新，下一步和剩余风险明确。

没有证据时不得写 `passing`；不能通过删除测试、削弱断言、跳过检查制造通过。

## 状态文件与 WIP

- `feature_list.json`：机器可读功能状态；同一时间只能有一个 `in_progress`。
- `PROGRESS.md`：当前已验证状态、本轮记录、阻塞项、下一步、交接摘要。
- `.workbuddy-ai/memory/MEMORY.md`：稳定事实、已验证命令、明确决策；不写进度和临时日志。
- `.workbuddy-ai/memory/YYYY-MM-DD.md`：会话日志，只写结论与指针。

开工顺序：读本文件 → 读 `PROGRESS.md` → 读 `feature_list.json` → 看 `git log --oneline -5` → 跑 `./init.sh --quick` → 只选一个最高优先级功能。

## 收尾

- 跑适用的最终验证；不能跑时写明原因和剩余风险。
- 更新 `PROGRESS.md` 和 `feature_list.json`。
- 清理本轮临时产物；不删除用户既有改动。
- 报告：已改 / 已验证 / 未验证 / 剩余风险 / 下一步。

## 深链接

- 架构、模块地图、工程硬约定：`architecture.md`
- 开工/收尾、Git 守卫、审计链、异常处理：`process.md`
- 强制能力探针：`../enforcement-capability.md`
- 数据库脚本与需求：`documents/02、项目需求/`
- 编码规范：`documents/03、编码规范/`
