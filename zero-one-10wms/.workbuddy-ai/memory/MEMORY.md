# 项目长期记忆（稳定事实与决策）

> 只放稳定事实、已验证命令、明确决策和反复出现的问题。
> 当前进度放 `PROGRESS.md`；功能状态与证据放 `feature_list.json`；会话日志放 `memory/YYYY-MM-DD.md`。
> 与仓库事实冲突时，以重新验证后的代码/配置为准。

## 项目身份

- 项目：`zero-one-10wms`，仓储管理系统（WMS），覆盖基础资料、入库、库内、出库、盘点、计费、报表。
- 仓库关系（2026-11-23 起为单仓模式）：父仓库 `AIWMSproject` 直接跟踪 `zero-one-10wms/` 下的全部文件（普通文件，无 gitlink），并另含 `Mneme-rag/`、`AGENTS.md`、`.workbuddy-ai/`；`zero-one-10wms/.git` 这个独立仓库仍留在磁盘上，但父仓库不再维护它的指针。
- 技术栈：Java（Spring Cloud Alibaba / Spring Boot 2.3 / MyBatis-Plus）、C++（oatpp / CMake）、Vue3（Vite / Element Plus / Pinia）、MySQL、Redis、Nacos、RocketMQ、FastDFS、Jenkins。
- 当前基线（2026-11-23）：父仓库 `main` @ `799b9b0`（单仓模式，索引内 `zero-one-10wms/*` 全为 100644 普通文件，无 160000 gitlink；该提交一次性入库 207 个文件，含 F-006~F-013 登记与根 `.gitignore`）；独立子模块仓库 `v1.0.0` @ `7ef08d88` 仍在磁盘，但父仓库不再同步其指针。

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
- 旧“收货未上架”页面（`wms-frontend/src/views/daily-check/received-unsold/index.vue`）的 `statusText` 按 N=未上架 / I=上架中 / Y=已上架 三态展示库存状态：旧端点 `/daycheck/no-up/get-no-up-goods` 不得加 `bin_sta` 过滤；巡检口径（`bin_sta='N'` 或 NULL、稳定排序、显式列）走独立端点 `/daycheck/no-up/get-no-up-goods-page`（`NoUpMapper.getNoUpGoodsForInspection`）。
- Agent `Settings`（pydantic-settings）字段都带 `validation_alias`：`Settings(scan_lease_seconds=3)` 会被静默忽略，必须按环境变量名传（`Settings(WMS_AGENT_SCAN_LEASE_SECONDS=3)`）；list 类型环境变量用 `Annotated[list[str], NoDecode]` + 逗号分隔。
- Codex 沙箱内 `wms-agent` 的 `cryptography` DLL 与 Maven 本地仓库不可用：pytest / psycopg / mvn 必须提权执行；Windows 下打包前先停掉占用 jar 的服务，否则 `spring-boot:repackage` 因文件锁失败、产出无主清单的 jar。
- MyBatis resultMap 映射了实体没有的 property 时，解析不报错，但逐行映射到非空列会抛 `There is no setter for property named ...`；空表会让缺陷“看起来正常”。守护测试：`NoUpMapperXmlTest`（真实解析 + `MetaClass.hasSetter` + 逐行赋值）。
- 网关 `wms-gateway/src/main/resources/application.yaml` 路由现状：`/dashboard/**` 行 37-40、`/stockln/**,/stock/**` 行 85-88、`/daycheck/**` 行 89-92 走 `lb://${sn.*}`；C++ 走静态端口样式（行 103-106 `c3-chuweiguanli-route uri: http://127.0.0.1:8103`，`Path=/chuweiguanli/**`）；`/warningmanagement/**` 无路由，故 ADR 跳过 `EXP-WARN-CPP` 成立。
- S1 源码核查确认的库表与鉴权底座事实（2026-11-27）：
  - `t_s_role.rolecode` 列宽为 `varchar(10)`，新增角色码须 ≤10 字符；
  - 零壹多表「库位 vs 托盘」列名互异：`wm_to_up_goods` 中 `ku_wei_bian_ma`=库位、`bin_id`=托盘码；`wm_to_down_goods` 中 `ku_wei_bian_ma`=源库位、`bin_id_from`=源托盘；`wm_om_qm_i`/`wm_in_qm_i` 中 `bin_id`=库位、`tin_id`=托盘码；未入 `wm_notice_conf` 的下架记录在 j8 视图（`InTransitStockMapper.xml:8`）中归属“在途”；
  - `TaskConfirmServiceImpl.batchConfirmTask`（j7）无 `@Transactional` 且仅置 `bin_sta='Y'`，非库存分配时点；回单写入归 `wms-j8-exportmana`（`ReceiptServiceImpl`→`wm_notice_conf`，`ManyReceiptsServiceImpl`→`wm_om_notice_h`）；仓库不存在 Java `/cost` 服务（计费在 C++ `wms-c5-costmanagement`）；
  - C++ `wms-c4-icmanagement` `AdjustlistDAO.cpp:148` 直接 `UPDATE wm_to_up_goods SET goods_qua=...` 而未同步 `base_goodscount`，而 `wv_stock` 汇总 `base_goodscount`；
  - `wms-common` `JwtComponent.java:84` 对 HMAC 密钥做 MD5 且 `exp` 按毫秒计算，不可复用于标准 JWT 验签；`ResourcePermission` 仅为静态声明注解，运行时拦截须独立 AOP 且外包 `@Transactional`；`GatewayAccessFilter` 当前仅识别 `token_use=agent_service`；`wms-agent/pyproject.toml` 当前未安装 `psycopg-pool`。

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
- `./init.sh --java-test`（Git Bash + JDK17）：PASS；login 12 + daycheck 19 = 31 tests，7 个门禁测试类逐一确认执行（2026-11-24）。
- `wms-agent`：`.venv\Scripts\python.exe -m pytest`，设置 `WMS_AGENT_TEST_DB_URL=postgresql://postgres:<口令>@127.0.0.1:5432/wms_agent_scan_test`（独立测试库，库名必须含 test）→ 184 passed / 3 skipped；不设 → 166 passed / 21 skipped（2026-11-24）。需在沙箱外执行。
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
- S1 每日巡检与异常自愈 Agent 架构决策（2026-11-27 锁定，详见 `wms-agent/docs/implement/S1_每日巡检与异常自愈Agent_代码实施设计文档_v2.3-rc1.md`）：
  - 在现有 `wms-agent` 平滑演进（新增 `app/s1/`、`/agent/s1/**`、PG `V013~V019`），保持 `app/scan/` 与 588 passed 零退化；纯 Python 轻量自研，**先逐个完成单领域 Agent，全领域完成后再做顶层 Supervisor-Worker 编排**；
  - 严守 ADR-005（Python 不直读 MySQL），通过网关调 Java 端点；前端复用 `wms-frontend`，**既有问数悬浮球（`components/ai-assistant/index.vue`）保持原样不动**，S1 新增独立形态 B 右侧抽屉与动作级权限组合式函数（不扩大全站 `WRITABLE_ROLES`）；
  - 角色范围落 PG（不动 `wms-oauth2` 登录 JWT）；写动作按动作级独立控 `disabled | dry_run | live`（默认 `dry_run`），受 `CHECK(live ⇒ ready)` 与逐动作安全评审约束；不侵入任何 `wms-cpp` 服务。

## 不要写入本文件

- 临时命令、工具日志、一次性推理过程。
- 当前进度、阻塞项、下一步（写 `PROGRESS.md`）。
- 未经验证的猜测、密钥、令牌、个人信息。
