# 项目长期记忆（稳定事实与决策）

> 只放稳定事实、已验证命令、明确决策和反复出现的问题。
> 当前进度放 `PROGRESS.md`；功能状态与证据放 `feature_list.json`；会话日志放 `memory/YYYY-MM-DD.md`。
> 与仓库事实冲突时，以重新验证后的代码/配置为准。

## 项目身份

- 项目：`zero-one-10wms`，仓储管理系统（WMS），覆盖基础资料、入库、库内、出库、盘点、计费、报表。
- 仓库关系（2026-11-23 起为单仓模式）：父仓库 `AIWMSproject` 直接跟踪 `zero-one-10wms/` 下的全部文件（普通文件，无 gitlink），并另含 `Mneme-rag/`、`AGENTS.md`、`.workbuddy-ai/`；`zero-one-10wms/.git` 这个独立仓库仍留在磁盘上，但父仓库不再维护它的指针。
- 技术栈：Java（Spring Cloud Alibaba / Spring Boot 2.3 / MyBatis-Plus）、C++（oatpp / CMake）、Vue3（Vite / Element Plus / Pinia）、MySQL、Redis、Nacos、RocketMQ、FastDFS、Jenkins。
- 当前基线（2026-11-23）：父仓库 `main` @ `fcbc02b`（单仓模式，索引内 `zero-one-10wms/*` 全为 100644 普通文件，无 160000 gitlink）；独立子模块仓库 `v1.0.0` @ `7ef08d88` 仍在磁盘，但父仓库不再同步其指针。

## 已验证的工程事实

- c7/c8 模块源码 UTF-8 与 GB18030 混存且行尾多为 CRLF：改文件前必须逐文件探测编码与行尾并原样保持（辅助脚本 `.dsh-scratch/enc.py`、`patchlib.py`）。
- oatpp 项目 `executeInsert` 返回 `LAST_INSERT_ID()`，对 varchar UUID 主键表无意义，插入后判断成功应使用 `executeUpdate`（返回受影响行数）。
- 路由 PATH 必须以 `/` 开头（oatpp `info->path = PATH` 原样使用）；同一路径不同 HTTP 方法合法，端点唯一性按「方法+路径」校验。
- 批量删除一律 `SQLPARAMS_PUSH` 参数化（IN 占位符逐个 push），禁止字符串拼接。
- `zh-dict.yaml` 同名顶层键会被 yaml-cpp 后者覆盖——新增词条前先检查重复键。
- 前端字典页统一走 `views/ware-config/composables/use-dict-page.ts` + `views/ware-config/components/DictPage.vue` 工厂，接口集中在 `apis/ware-config/index.js`；导出兼容 201 状态码（`requestBlob`）。
- 动态更新 DTO 用 `API_DTO_FIELD_DEFAULT`；`API_DTO_FIELD` 第 5 参数是真默认值，未传字段会被填默认值。
- Java 成功码 `10000`；C++ `JsonVO` 成功码 `0`；文件导出兼容 `201`。
- Agent 首版 6 个工具端点在当前仓库均已核实存在（2026-11-23）：`/stock/inventory-query/query-all`（`StockQueryController.java:30,39`）、`/stock/expiry-warning/query-all`（`ExpiryWarningController.java:24,30`）、`/daycheck/no-up/get-no-up-goods`（`NoUpController.java:35,46`）、`/daycheck/delay/im-delay`（`DelayController.java:24,51`，类级 `@RequestMapping("daycheck")` 无前导 `/`）、`/dashboard/query-pend-*` 与 `/dashboard/query-cur-pick`（`DashboardController.java:30,38,52,66,79`）、`/dashboard/query-goods-to-*`（`DashboardController.java:110,123,136,148`）。
- 网关 `wms-gateway/src/main/resources/application.yaml` 路由现状：`/dashboard/**` 行 37-40、`/stockln/**,/stock/**` 行 85-88、`/daycheck/**` 行 89-92 走 `lb://${sn.*}`；C++ 走静态端口样式（行 103-106 `c3-chuweiguanli-route uri: http://127.0.0.1:8103`，`Path=/chuweiguanli/**`）；`/warningmanagement/**` 无路由，故 ADR 跳过 `EXP-WARN-CPP` 成立。

## 环境限制

- Windows + PowerShell 5；`bash` 不在 PATH，`init.sh` 需用 Git Bash 执行。
- Java 8 + Maven 3.6.3；本机无 cmake/MSVC，C++ 只能做静态校验，结果固定 `static_pass + runtime_unverified`。
- 本机 `pnpm` 不在 PATH；前端命令用 `corepack pnpm`。
- 前端包管理器固定 `pnpm@9.5.0`，Node 要求 `>=20.15.0`。

## 已验证命令（2026-11-23）

- `./init.sh --quick`：PASS；检查工具链、关键文件、JSON、父/子 Git 基线与 gitlink。
- `./init.sh --cpp`：PASS；C++ 模块注册完整，源码 `zh-dict.yaml` 无重复顶层键；本机无 cmake，仅静态层。
- `./init.sh --frontend`：PASS；`vite build --mode production` 完成（约 44s）。
- `./init.sh --java wms-j8-othermana`：PASS；Maven 离线编译通过。
- `./init.sh --quick --snapshot`：PASS；`$WMS_STATE_DIR/history.jsonl` 追加 JSONL，含 `prev_hash` / `hash`。
- `python -m json.tool feature_list.json`：PASS。

## 稳定决策

- 父仓库与子模块分开提交；先提交子模块，再在父仓库精确 `git add -- zero-one-10wms` 更新 gitlink。（**2026-11-23 起作废**：改为单仓模式，父仓库直接跟踪 `zero-one-10wms/` 全部文件，不再有 gitlink。）
- 提交只暂存明确路径；禁止 `git add .` / `git add -A`；用户既有改动不覆盖、不 stash、不 checkout。（**2026-11-23 起修订**：单仓全量推送场景允许 `git add -A`，前提是父仓库根 `.gitignore` 已排除 `node_modules.bak/`（2.55 GB）、`target/`、`*.class`、`*.pdb`、`*.log`、`.env*` 等依赖/产物/密钥；每次推送前用 `git add -An` 干跑核对待加入文件数与路径。）
- 优先级（2026-11-23 决策）：`feature_list.json` 的 `priority` 为唯一连续序号，features 数组按 id 升序、排序键是 priority；AI-Agent 轨道 `F-006`~`F-013` 整体排在传统功能队列 `F-002`/`F-003`/`F-004` 之前。
- 状态文件分工：`feature_list.json` 管功能状态与证据；`PROGRESS.md` 管当前状态与下一步；`MEMORY.md` 只放稳定事实与决策；`memory/YYYY-MM-DD.md` 放会话日志。
- 不引入根级 `MEMORY.md`，避免与 `.workbuddy-ai/memory/MEMORY.md` 形成两套记忆。
- 配置类 CRUD 可止步静态验证；资金、库存过账、PLC、权限边界必须有运行时或端到端证据。
- 没有证据不得写 `passing`；不能通过删除测试、削弱断言、跳过检查制造通过。

## 不要写入本文件

- 临时命令、工具日志、一次性推理过程。
- 当前进度、阻塞项、下一步（写 `PROGRESS.md`）。
- 未经验证的猜测、密钥、令牌、个人信息。
