# Progress

> 当前状态与下一步。功能级验证步骤和证据在 `feature_list.json`；稳定事实与决策在 `.workbuddy-ai/memory/MEMORY.md`。

## 当前已验证状态

- 日期：2026-11-26
- F-015 阶段7.7（2026-11-25，扫描记录与证据归档 + 通知归档 + 指标日聚合 2 年，ADR-020 修订）：Python 全量 pytest 带独立 PG 测试库 **531 passed / 11 skipped / 1 warning**、不带 PG **474 passed / 68 skipped**；Java `./init.sh --java-test` PASS（41 tests）；真实环境 e2e **21/21**（日聚合 180 仓库·日、合成过期扫描整批归档、通知归档、读回落、长窗口指标）；新测试抓到并修复 3 个日聚合真实缺陷；F-015 按用户 m09157 决定置为 **passing / e2e_pass**；生产上线仍被 ADR-021 阻塞；改动未提交。
- F-015 真实模型摘要质量评估 + 端到端（2026-11-25，用户 m08991 指定本轮只做这两项；未改产品代码、未提交）：`.env` 配置的外部模型对本机不可用（OpenRouter 对全部免费模型与配置模型的 `POST /chat/completions` 返回 400 `Request path cannot be relayed`，属服务端问题，未改 `.env`）。质量评估：真实巡检输入 5 组 + 按真实形状构造的注入输入 3 组 → 真实模型 glm-5.4（cc-switch-zhipu-glm，经 DSH 子代理通道；**不是生产配置的模型，也不是直连端点**）的 8 条回复全部走产品真实的解析/清洗链路 **8/8 通过**（数量与级别一致、纯文本无 Markdown/链接、动作码 ⊆ allowedActions 且文案对题、incomplete 有说明；3 组注入未改变级别与输出结构并主动提示字段含可疑指令），人工阅读结论「可用，偏啰嗦」。端到端：回放链路 `scan-8a7e9ea19c8f494b`（经网关真实 JWT 触发，summariesLlm 5 / template 0，PG 文本即模型原文；浏览器详情抽屉显示「模型摘要 / 模型：glm-5.4(replay)」、纯文本、3 条建议动作）；直连真实端点 `scan-50bb337adc9c4489`（llmCalls 5 / llmFailures 5 / 全部降级模板，`fallback_detail` 含 `llm returned http status 400: Request path cannot be relayed`，整次扫描约 4.7 秒）。证据：`.runtime_tmp/stage8_real_model_summary_quality.json`、`stage8_real_model_replay_e2e.json`、`stage8_direct_endpoint_degradation.json`、`stage8_real_model_summary.png`。**限制**：生产配置模型的摘要质量仍未评估；回放链路的 token 用量是端点固定值；接入其它模型前须按同一组 8 条输入复评。agent 已以默认配置重启（`llm.enabled=false`）。
- F-015 阶段7（2026-11-25，retry 审计归属 + 指标 + 保留与归档 + 前端摘要展示 + 生产安全门 + v0.2.0 总验收，ADR-020/ADR-021）：Python 全量 pytest 带独立 PG 测试库 **512 passed / 10 skipped / 1 warning**、不带 PG **459 passed / 63 skipped / 1 warning**；Java `./init.sh --java-test` **PASS**（41 tests，阶段7 无 Java 改动）；前端 Vitest 15 passed、生产构建通过；真实环境总验收 e2e（真实 JWT 经网关）**STAGE7_E2E_OK 29/29**（retry 归属四列、调度槽位唯一入队、指标接口权限与取数耗时、保留任务删除/归档/摘要回落）。落地：V010 retry 审计归属（`trigger=retry` + `retry_of_scan_id` + `origin_*`）；`GET /agent/scan/metrics`（仅管理员）；V011 归档表 + `POST /agent/scan/retention/run` + 每日保留任务（默认关闭）；告警详情抽屉展示巡检摘要（模型/模板标识、降级原因、纯文本）。本轮修复：摘要可见性跟随告警可见性、`GET /agent/alerts/{id}` 内嵌完整扫描记录的越权缺口（改为摘要）、抽屉关闭动画期间重开竞态、PG 通知忽略 `createdAt`。**生产上线阻塞（ADR-021）**：实测网关无 token 任意方法均放行、资源角色不生效，范围是全部 Java 服务；巡检端点由 agent 自验并有路由级回归。待决：扫描记录与证据保留期、通知与 trace 是否归档、「聚合统计 2 年」未落地、生产配置模型的摘要质量未评估（glm-5.4 的评估见上一条）。改动未提交；F-015 状态待用户确认验收后更新（v0.2.1 在阶段8 登记）。
- F-015 阶段6（2026-11-25，LLM 聚合摘要，ADR-019）：Python 全量 pytest 带独立 PG 测试库 **452 passed / 7 skipped / 1 warning**、不带 PG **411 passed / 48 skipped**（阶段5 基线 368 → +84）；新增 `tests/test_scan_stage6.py` 73 例与 V009 双后端契约 6 例；Java `./init.sh --java-test`（harness JDK8）**HARNESS_EXIT=0，41 tests BUILD SUCCESS**（阶段6 无 Java 改动，仅回归）。落地内容：`config/scan.yaml` 的 `llm` 段（**默认关闭**，6 个上限为启动硬上限，进入配置快照与哈希，密钥仍只走 env）；`app/scan/llm/summarizer.py`（**只摘要不判定**：按 rule+仓库+客户聚合，仅 P0/P1 调模型，输入是白名单 digest、不含原始行与司机姓名/电话/车牌，输出做 schema 校验与清洗，任何失败降级确定性模板，调用数与 token 记入 counts）；V009 `agent_scan_summaries`；`GET /agent/scans/{scanId}/summaries`（可见性同扫描详情）。真实链路 e2e **STAGE6_E2E_OK（22 项）**：A. 按 `.env` 所配外部模型入队启用 LLM 的快照 → 该网关对话接口对本机返回 HTTP 400（13 个模型均如此，属环境问题），5 组全部降级模板、扫描 succeeded、8 条命中照常落库（「LLM 失败仍落告警、摘要用模板」被真实验证）；B. 同一 agent 的真实 worker 经真实 HTTP 调本地 OpenAI 兼容桩（**模型是桩**）→ 5 组中 3 组取得模型摘要（`llmCalls 5 / llmFailures 2 / promptTokens 462 / completionTokens 90`）、2 组超过 8 秒降级模板，桩侧请求体只含白名单键，经网关读取接口 code 10000；对照快照未启用的扫描期间模型端点零请求。evidence `.runtime_tmp/stage6_llm_summary_e2e_result.json`。本轮修复 3 个缺陷：PG 与 Memory 对未知 `summarySource` 归一不一致、成功路径未累加 token、迁移守卫测试写死版本号。**未做/未验证**：前端 `/inspection/alerts` 尚未展示摘要；真实模型的摘要质量未评估；`llm.enabled` 启用属部署决策。F-015 仍 `in_progress/runtime_unverified`（剩阶段7 指标与保留+v0.2.0 总验收）。
- F-015 阶段5（2026-11-25，自动 resolved + 内部调度）：Python 全量 pytest 带独立 PG 测试库 **368 passed / 6 skipped / 1 warning**、不带 PG **333 passed / 41 skipped**（阶段4 基线 313 → +55）；新增 `tests/test_scan_stage5.py` 44 例（必测 10 项全覆盖 + retry 权限 14 例）与 V008 双后端契约；Java `./init.sh --java-test`（harness JDK8）**HARNESS_EXIT=0，41 tests BUILD SUCCESS**（阶段5 无 Java 改动，仅回归）；真实 e2e **STAGE5_E2E_OK**（四项同一次连贯运行）——①`wm_in_qm_i` 插两行未上架（-10h/-5h）→ 真实 admin JWT 扫描建 2 条告警（P0/P1）→ 一行改已上架、一行删除 → 第二次扫描 `findings 0 / alertsAutoResolved 2 / staleCheckSkipped 0`，两条 `condition_cleared` 事件 `open→resolved`、`actorType=system`、traceId 与扫描一致；②调度槽位 `20261125T1730` tick `outcome=created` → 扫描 succeeded，`trigger=schedule`、`executor=[service,agent-inspector]`、`scheduleSlot`/`configSnapshot`/`configHash`/`configVersion=v0.2.0` 与入队一致且可回放；③同槽位：同实例再 tick 不入队，新实例 tick 与直接 enqueue 重放均 `idempotent`，PG 该槽位仅 1 行；同 requestId 三次真实 POST 同一 `scanId`；④错 key/缺 key 的扫描 `failed(auth_failed:…)` 且 executor 为空，不回退管理员令牌。本轮修复 3 个 **Memory 单测发现不了、PG 契约/真实 e2e 才暴露**的缺陷：PG 建告警丢 `lastSeenAt`、源合法返回 0 行时自动关闭被整体跳过、自动关闭事件 `from_state` 被写成 `resolved`。**retry 权限修正（用户 m07086 评审）**：首版 retry 误用 `can_trigger_scan`（cg/ckjl/服务账号可重试）且未校验原扫描归属，已改为仅管理员且原扫描须归本人或由服务账号发起（`security.can_retry_scan`）；真实令牌 e2e **RETRY_E2E_OK**（14 项：ckjl001 仍可发起扫描但重试 403、服务令牌 403、admin 重试他人扫描 403、被拒调用不入队、admin 重试本人扫描与定时扫描均按原快照成功；evidence `.runtime_tmp/retry_permission_e2e_result.json`）。**调度器默认仍关闭**（仓库 `scan.yaml` 的 `schedule.enabled=false`，启用属部署决策）。F-015 仍 `in_progress/runtime_unverified`（剩阶段6 LLM 聚合摘要、阶段7 指标与保留+v0.2.0 总验收）。
- F-015 阶段4（2026-11-25，版本化 YAML + ADR-018）：Python 全量 pytest 带独立 PG 测试库 **313 passed / 5 skipped / 1 warning**、不带 PG **284 passed / 34 skipped**（阶段3 基线 277 → +36）；新增 `tests/test_scan_config.py` 26 例覆盖配置契约（重复键/非字符串键/阈值反序/非法通知模式/未知路由/跨仓路由/未知 override/缺文件/哈希稳定与键序无关/三处变化各改哈希/env override 进快照/往返哈希一致/篡改/版本不符/非法 JSON/快照不含密钥/worker 用入队快照/缺快照与坏快照 fail-closed/routedTo=岗位且 assignee 为空/合并接收人/无路由计数/PG 回放）；Java `./init.sh --java-test`（harness JDK8）**HARNESS_EXIT=0**，10 个门禁类 **41 tests BUILD SUCCESS**；真实 e2e **STAGE4_E2E_OK**——入队冻结配置 A（`configHash=sha256:479605f8…`，noUp 8/4/2）后把 `scan.yaml` 改为 B（noUp 3/2/1，`sha256:451c2e31…`），worker 消费该任务仍按 A 执行（`status=succeeded`、库中 `config_hash/config_version` 回读为 A、执行快照 `p0Hours` 仍 8.0），脚本结束自动还原 YAML 并核对回 8/4/2。F-015 仍 `in_progress/runtime_unverified`（剩阶段5 自动 resolved+内部调度、阶段6 LLM 摘要、阶段7 指标与保留）。
- F-015 阶段3（2026-11-25，backlog+一致快照）：Python 全量 pytest 带独立 PG 测试库 **277 passed / 4 skipped**；Java `./init.sh --java-test`（harness JDK8）已把 `PendSnapshotContractTest`/`PendSnapshotResourceRoleSeedTest` 纳入门禁（10 个测试类）→ **wms-login 12 + dashboard 7 + daycheck 22 = 41 tests BUILD SUCCESS**；真实 e2e **STAGE3_E2E_OK**——dashboard(10010) 直读 MySQL 一致快照 `receipt 0 / to_up 0 / pick 45 / cur_pick 74`，admin 连发 7 次 backlog 扫描全部 succeeded、PG `agent_backlog_observations` 恰 21 行（7×3 队列，observed_at 为 Java 纳秒时间已去 `[Asia/Shanghai]` 后缀）与 scan trace 串联，真实 pick 恒 45 → 0 条 BACKLOG-GROWTH 误报。四类规则（效期/未上架/延时/积压）至此全部落地；F-015 仍 `in_progress/runtime_unverified`（后续阶段见上条）。
- F-015 阶段1（2026-11-25，告警详情/认领/已读/真实 in_app）：Python 全量 pytest 带独立 PG 测试库 **208 passed / 3 skipped**、不带 PG **185 passed / 26 skipped**；Java `./init.sh --java-test`（harness JDK8）**daycheck 22 + wms-login 12 tests BUILD SUCCESS**；V004/V005 迁移已在真实 PG 应用并核对列与索引。F-015 仍 `in_progress/runtime_unverified`（backlog/LLM/前端未做）。前一阶段第四轮返修基线：带 PG **184 passed / 3 skipped**、不带 PG **166 passed / 21 skipped**，Java 31 tests BUILD SUCCESS，真实 daycheck+网关+agent+PG 运行态 42 项检查全过。**运行态注意**：agent 进程当前带进程级环境变量 `WMS_AGENT_SERVICE_API_KEY` / `WMS_AGENT_SERVICE_KEY_ID` / `WMS_AGENT_ALERT_RECIPIENTS=admin` 启动（未写入 `.env`），不带这些变量重启后 worker 取不到服务令牌会 `failed(auth_failed)`。
- 问数 Agent 收尾（2026-11-24 晚）：默认持久化配置已固化到 `.env`（本地）与 `.env.example`/实施方案/README（入库模板），正常重启即从 `.env` 读 PG 配置，无需进程级临时覆盖；复验 `persisted=true`。相关测试隔离修复后 `uv run pytest` 72 passed、`init.sh --agent` 69 passed 3 skipped PASS。问数 Agent（F-006~F-013）就此结项。
- 父仓库：`main`（F-006~F-013 已提交；F-015 异常巡检 Agent 阶段 0–7.7 已分 5 批提交：`4a64e3e` → `ccf22ef` → `9d270c3` → `d1e467d` → `c0182cc`，未 push）
- 嵌套历史仓库：`zero-one-10wms/.git` 仍存在，HEAD `7ef08d8`，但父仓库不维护其指针，不作为提交目标
- 跟踪结构：**单仓模式**。父仓库索引中 `zero-one-10wms/*` 全部为 mode `100644` 普通文件，无 `160000` gitlink 条目；`zero-one-10wms/` 下的 ADR、`init.sh`、`AGENTS.md`、`architecture.md`、`process.md`、`feature_list.json`、`PROGRESS.md` 均已直接被父仓库跟踪。
- 推送范围：父仓库根新增 `.gitignore`，排除 `node_modules/`、`node_modules.bak/`（**2.55 GB**，本轮明确不入库）、`target/`、`dist/`、`*.class`、`*.jar`、`*.pdb`、`*.log`、`__pycache__/`、`*.pyc`、`.venv/`、`.env`/`.env.*`、`.idea/`、`.vs/`、`.runtime_tmp/`（临时联调目录，含私钥/token/HAR）。其余文件全部入库（含 `.dsh-scratch/` 辅助脚本 6.4 MB / 210 文件）。
- 标准启动路径：`cd zero-one-10wms && ./init.sh --quick`（Git Bash）
- 标准验证路径：`./init.sh --quick` → `./init.sh --cpp` → 按功能跑 `--java <module>` / `--frontend` / `--verify` / `--agent`
- 当前状态：**异常巡检 Agent dev 验收已结束**。F-014/F-015/F-016 均为 passing/e2e_pass；Java 18 类 116 tests、Python 588 passed/12 skipped、前端 15 例+生产构建、权限 baseline 349/349、init.sh --quick 均通过。温度使用用户授权的 dev 合成配置；生产温区确认、518 落库强拦截、prod 凭据与运维观察不在本次 dev 收口范围。
- AI-Agent 轨道：问数 Agent F-006~F-013 已走完；异常巡检 F-014/F-015/F-016 均为 passing/e2e_pass。F-016 的 dev 温度超限/恢复、两类告警浏览器详情、六源扫描、审计模式与新增接口权限门禁已有真实证据。
- 优先级决策（2026-11-26）：`priority` 唯一连续 1..16；异常巡检前置项 `F-014`=11、v0.2.0 `F-015`=12、v0.2.1 `F-016`=16；传统队列 `F-002`=13、`F-003`=14、`F-004`=15；`F-005`=5 保持不变。
- 当前工作项：无 in_progress；异常巡检 Agent dev 验收收口。排队项：F-002 储位管理、F-003 商品明细（not_started）；F-004 运行时基线 blocked。
- 已通过项：F-001、F-005（static_pass）；问数 Agent F-006/F-007/F-011/F-012/F-013（e2e_pass）、F-008/F-009/F-010（unit_pass）；异常巡检 F-014/F-015/F-016（passing/e2e_pass）。
- 运行时底座（本轮实测）：本机 `192.168.101.91`；虚拟机 `192.168.89.128` 提供 Nacos 8848、Redis 6379、MySQL 3306，**PG 5432 未起**；本机原生 PostgreSQL 16.15 在 5432（库 `ragent`，`postgres`/`123456`，本轮 F-012 落库用它）
- 工具链实测：Python 3.14.7 = `D:\DownloadPackage\environment\python.exe`；uv 0.13.1 = `C:\Users\a\.local\bin\uv.exe`（**不在 PATH**）；JDK17 = `D:\DownloadPackage\environment\jdk-17.0.20.1+1`（PATH 上的 java 是 JDK8，不能用于 Spring Boot 3）；mvn = `D:\DownloadPackage\Maven\apache-maven-3.6.3-bin\apache-maven-3.6.3\bin\mvn.cmd`；Git Bash = `D:\DownloadPackage\environment\Git\Git\bin\bash.exe`（**不在 PATH**，本轮已用它跑通 `init.sh --agent`）
- 当前 blocker：dev 验收无阻断；生产上线仍有独立待办——业务确认 prod 温度词表/阈值/间隔、518 接口角色矩阵落库后开 deny-unregistered、prod 独立凭据初始化与轮换、定时巡检/失败恢复/监控/保留观察。

## 本轮记录

### 追加：异常巡检 Agent dev 验收收口（2026-11-26）

- 用户调整边界：dev 不按生产上线完工标准强切换；温度可用逻辑一致的合成开发值；518 先分组草案+审计模式；生产凭据只做准备。
- 温度：`scan.yaml` 已启用四个 dev 地点；真实 MySQL→Agent→PG 产生 P0 超限告警并自动 resolved；生产构建浏览器验证 TEMP-EXCURSION 列表、详情、模板摘要与证据；六源混合扫描 `scan-cdd635abb7a449f4` 全 ok、`skippedTypes=[]`。证据 `temperature_dev_e2e.json`、`temperature_browser_result.json`、`six_source_scan_result.json`。
- 权限：`audit-authorization=true` 只记录 `AUTHZ_AUDIT` 并放行未登记/角色不匹配；匿名 401、服务令牌越界 403 保持硬边界。518 已形成分组草案；`@ResourcePermission` + baseline 门禁接入 `init.sh --quick`，349/349 通过，新增未声明端点会失败。
- 生产准备：环境变量模板、脱敏校验、Nacos 只读巡检与上线/回滚 SOP 已落盘；未发布 Nacos、未生成/轮换凭据、未改 DB/Redis/Mongo/JKS。
- 最终门禁：Java 18 类 116 tests；Python 588 passed/12 skipped；前端 15 例+生产构建；权限自测 14/14、baseline 349/349；`init.sh --quick --snapshot` PASS。
- 状态：F-014/F-015/F-016 均 `passing/e2e_pass`，无 `in_progress`。**异常巡检 Agent dev 研发验收结束；生产上线尚未完工。**

### 追加：接口权限声明与新增端点门禁（ADR-022，2026-11-26）

- 新增 `wms-common/.../security/ResourcePermission.java`：支持 `roles`、`allowPublic`，类级默认/方法级覆盖；注解不自动改库或刷缓存。
- 新增 `.dsh-scratch/check-resource-permissions.mjs` 与 `resource-permission-baseline.json`：扫描 Java HTTP 映射，按“方法 + 规范化路径”对比 349 个存量端点；baseline 之外未声明端点失败。已接入 `init.sh --quick`，不会自动更新 baseline。
- 自测 **14/14**；当前门禁 **349/349、newDeclared=0、newUndeclared=0、stale=0**；`wms-common` 编译、`node --check`、`bash -n init.sh` 均通过。
- 新增 `documents/07、AI-Agent化/接口权限分组草案.md` 与 `ADR-022-接口权限声明规范.md`，并更新技术选型 ADR 索引。518 条清单拆为 484 端点类条目、23 拼接片段、11 基址/动态模板；孤儿候选 25（高危交集 12）；四类高危并集 207，另 PLC 执行 1。
- 边界：未修改数据库、未刷新权限缓存、未改 deny-unregistered；审计模式与 dev 验收收口见上条。

### 追加：生产上线准备（仅文件，dev 不执行运维，2026-11-26）

- 用户边界：dev 不安排运维窗口、不生成/轮换凭据、不发布 Nacos、不修改 DB/Redis/Mongo/JKS 口令；本轮只做生产上线准备，未提交。
- 已改 `nacos-config/`：新增 `java-service.env.example`（27 个启用变量均为占位符）、`validate-java-env.py`（必填/空值/占位符/弱默认值/签名与双 key 配对校验，不输出值）、`inspect-nacos-config.py`（只读 GET，输出 dataId/SHA-256/明文可疑标记/env 占位符标记，不输出正文）；扩充 `README-credentials.md` 的 prod 独立初始化、切换顺序、灰度清单、回滚触发与步骤。
- 本地验证：环境校验最终回归 **12 项通过**（假值、缺失、空值、弱默认值、连续数字/重复模式、进程覆盖、双 key、JKS/PEM、坏文件）；巡检器 **11 项通过**（占位符/明文/URI/注释/私钥块/哈希、本地 CLI、HTTP 桩仅 GET、拒绝 302、假 token/正文不泄露）。仓库三份 Nacos 样本只读巡检均为 `plaintext_credential_suspected=false`、`env_placeholder_present=true`。
- 未执行：未调用远端 dev/prod Nacos，未发布配置，未重启服务，未生成/轮换凭据，未修改任何数据库/Redis/Mongo/JKS。prod 将使用独立环境和新凭据初始化。
- 状态：生产准备文件已完成；F-016 dev 验收已收口，prod 独立初始化、凭据轮换、灰度与回滚演练仍待未来 prod 变更窗口。

### 追加：F-016 顺序收尾、真实回归与生产边界确认（2026-11-26）

**执行顺序**：①SCAN-PARTIAL 并发/遗留维护 → ②前端路由授权 → ③状态证据 → ④温度真实验收 → ⑤生产门槛。

1. **SCAN-PARTIAL**：候选查询与最终 UPDATE 都增加“触发扫描已在本轮健康扫描开始前结束”的 fencing；真实 PG 预提交并发用例通过。维护脚本改游标翻页、同来源后续健康扫描证明、当前 partial 阻断，205 条分页回归通过；真实业务 PG dry-run scanned=0/legacyActive=0/0 写入。定向 20 passed/2 skipped。
2. **前端授权**：路径大小写归一；current-user=null、空菜单、加载失败均失败关闭；空菜单清旧授权，setToken/reset 清用户与菜单；修复 main.ts 先装 HTTP 拦截器再装路由。生产构建浏览器回归：ckjl/admin 正常与大小写变体放行，cw 两种路径均 403，mock 空用户/空菜单均 403；15 例单测通过。证据 `.runtime_tmp/r7_route_guard_result.json`。
3. **状态证据**：F-014 补齐真实数据/规模/浏览器证据并置 passing/e2e_pass；F-016 保持 in_progress/runtime_unverified，删除“只剩两项上线”等矛盾口径。
4. **温度**：当时仓库没有生产地点词表；后续用户明确授权 dev 合成值，已配置并完成真实超限/自动关闭/浏览器详情回归，见上条。prod 阈值仍须业务确认。
5. **生产门槛**：issuer/logout 已修复并实测；dev 网关已改审计模式，只记录未登记/越权并放行，匿名与服务令牌硬边界不变。518 已有分组草案但未落库，deny-unregistered 保持 false；prod 凭据与运维观察按用户边界暂缓。

**门禁**：Java 18 类 116 tests/0 failures/0 skipped；Python 588 passed/12 skipped（600 total），真实 PG 0 failures/0 errors；前端 15 例+生产构建；ADR-022 权限自测 14/14、baseline 349/349；init.sh --quick PASS。

**下一步**：异常巡检 Agent dev 研发结束；后续仅按新需求或 prod 变更单处理生产温区确认、518 权限落库、凭据初始化与运维观察，不在 dev 阶段继续扩范围。

### 追加：cs/KH 生产构建浏览器回归与 403 路由修复（2026-11-26，用户 m04010 收口范围）

**为什么做**：m04299 第 2 组要求的最后一项前端缺口——cs/KH 只有合成空菜单证据、且未在生产构建上验证「手动输入 URL 能否绕过菜单隐藏」。温度真实阈值需业务提供，无法代做，故本轮只补这一项。

**方法**：
1. 临时账号：`.runtime_tmp/TempUsers.java` 克隆 `ckjl001` 的密码哈希建 `e2e-cs-R6CSKH`/`e2e-kh-R6CSKH`，各绑定单一角色 `cs`/`KH`。
2. 令牌：密码模式取 JWT，并按登录流程把 `<用户名>:token` 写 Redis（大小写敏感，写小写键会 401「用户凭证已注销」）。
3. 生产构建：`VITE_API_URL=/api npx vite build --mode production --outDir dist-e2e`，由 `wms-frontend/preview-e2e.mjs` 在 4173 静态服务并把 `/api` 反代到网关 10001（不指向公网 8.140.208.103）。
4. 浏览器：无头 Chrome + 裸 CDP（`wms-frontend/scripts/e2e-route-guard.mjs`）逐角色独立 browserContext，注入 token 后访问 `/home` 取侧边栏、访问 `/inspection/alerts` 取最终路径与正文。

**结果**：cs/KH `/login/get-menus` 均 200 且 `data=[]`；侧边栏 `navItems=1`（仅「首页」）、无「异常巡检」；手动访问 `/inspection/alerts` **最终 path=/forbidden**、正文含「403 抱歉，你无权访问该页面」；`gly(admin)` `navItems=130` 且 `/inspection/alerts` 正常渲染告警表。数据面另有后端 `code 9997` 兜底。

**发现并修复的缺陷**：首轮回归 cs/KH 停留在 `/inspection/alerts`、页面空白。根因有两条——①`unplugin-vue-router` 只扫描 `src/views`（并排除 `**/components`），403/404/500 组件在 `src/components/status/` 下，`definePage({name,path})` **从未注册**，守卫 `next({name:'Forbidden'})` 解析失败后 vue-router 静默中止；②同处 `definePage()` 不被编译期转换，运行时 `ReferenceError: definePage is not defined`（console 实测）。修复：`src/routers/index.ts` 的 `originRoutes` 显式登记 NotFound/Forbidden/Error 并 `setupLayouts([...originRoutes, ...routes])`；三个状态页移除无效 `definePage()`；新增 `src/routers/__tests__/status-routes.spec.ts` 做源码级契约断言。

**门禁**：前端单测 `npx vitest run 'src/composables/__tests__' 'src/routers/__tests__'` → **3 文件 11 例通过**；`npm run build` 通过；Java 18 类 111 tests、Python 593 tests 本轮未改动（上一轮数字仍有效）。

**清理**：`TempUsers cleanup R6CSKH` → `ids=2 rowsDeleted=6`；Redis 4 个 `e2e-*:token` 已 DEL（`EXISTS=0`）；预览服务已停；`dist-e2e` 构建产物已删。

**证据**：`zero-one-10wms/.runtime_tmp/r6_cs_kh_browser_regression.json`（汇总）、`r6_route_guard_result.json`、`r6_forbidden_direct_probe.json`、截图 `r6_menu_*.png`/`r6_guard_*.png`。

**边界**：仍不升 `e2e_pass`——温度真实阈值缺失（生产 `temperature.enabled=false`）、生产环境部署后未回归、518 个未登记接口与 issuer/logout 属上线前治理。

**未闭环（上线前）**：①温度真实地点/aliases/min-max/录入间隔；②518 接口角色治理后开启 deny-unregistered；③Nacos 发布与 DB/Redis/Mongo/JKS 凭据轮换；④生产定时巡检、失败恢复、监控与保留观察。issuer/logout 已在后续轮次修复并实测。

### 追加：第六轮独立复核后的修复与研发收口（2026-11-26，用户 m04299 + m04010）

**用户结论**：m04299「有实质进展但仍不能签收；温度不是唯一阻塞」，列出 5 组阻断；m04010 收口为「五步 + PG 直接证据 + 最终验收做完，v0.2.1 研发结束；生产凭据轮换与启用观察做完才上线，不再加新范围」。

**本轮修复**
1. 运行态未部署 + backlog 取数 403：`wms-java/wms-gateway/src/main/resources/application.yaml` 的 `service-token-paths` 补齐 6 条巡检数据源端点（no-up / outbound / delay / expiry / temperature / **backlog `/dashboard/query-pend-snapshot`**）；`GatewayAccessFilterTest` 增 2 例（取数端点放行、未声明端点 403）共 27 例；网关重建 pid 44168（jar 103,979,190 B @18:51:18），daycheck 重建 pid 10408（jar 211,168,102 B @18:54:10）。
2. 六源真实 e2e：`six_source_access_result.json` 六源全部 200（no_up 0 / outbound 46 / delay 3 / expiry 6 / temperature 4 / backlog 四队列）；`six_source_scan.py` → `scan-5f76a606ca6a48be`：**status=succeeded、partial=false、errorSummary=null**，sourceStatus 全 ok，counts findings 12 / alertsUpdated 11 / suppressed 1 / summariesSaved 8 / skippedTypes `[temperature]`。
3. 分页缺省运行态闭环：不传 pageIndex/pageSize 的 outbound → `pageIndex=1 pageSize=10 total=46 pages=5 rows=10`（修复前 0/0/0）。
4. SCAN-PARTIAL 并发误关：`app/scan/service.py` 的 `_persist_findings` 改 `lastSeenAt = persist_seen_at`（落库时刻而非扫描开始时间）；`app/scan/repository.py` 的 PG 两次 UPDATE 改 `last_seen_at = COALESCE(%s::timestamptz, now())`，Memory/PG 统一 agent 时间戳。回归 `tests/test_scan_partial_concurrency.py` 4 例。
5. 旧格式 `objectId=scan-*` 收敛：新增 `app/scan/maintenance.py`（`is_legacy_partial_alert` + `resolve_legacy_scan_partial_alerts`，支持 dry-run/`--apply`、幂等、保留事件原因）与 `tests/test_scan_legacy_partial_maintenance.py` 3 例；真实 PG 命中 1 条（objectId `scan-64c13510649846de`）→ `--apply` 关闭 `alertId=8`，再 dry-run 为 0（证据 `.runtime_tmp/scan_partial_legacy_migration.json`）。
6. 前端权限：新增 `src/composables/menu-access.ts`（`normalizePath`/`collectMenuPaths`/`isSensitivePath`/`isPathPermitted`），`src/routers/index.ts` 守卫对 `/inspection` 要求菜单授权否则跳 `Forbidden`；`use-permission.ts` 改为可写角色白名单（`cg`/`ckjl`/`gly`/`admin`…），未知角色一律只读；新增 `menu-access.spec.ts` 5 例 + `use-permission.spec.ts` 4 例 = 9 passed。

**门禁**：`./init.sh --quick` PASS（脏改动 73 项）；`./init.sh --java-test` PASS（18 类 **111 tests**，0 失败 0 跳过）；`uv run pytest` **593 tests / 0 failures / 68 skipped**；前端 `npx vitest run` 9 passed + `npm run build` 26.05 s。

**验收证据**：`zero-one-10wms/.runtime_tmp/final_acceptance_20261126_v2.json`（五步逐项、六源实测、SCAN-PARTIAL 并发与遗留收敛、门禁数字、上线前清单）；浏览器证据在**父仓库** `.runtime_tmp/`。

**仍未闭环（上线前，不属研发范围）**：温度真实阈值（地点/aliases/min-max/实际录入间隔 → `temperature.enabled=false`，扫描里 `skippedTypes=[temperature]`）；生产凭据轮换（DB/Redis/Mongo/JKS、Nacos 发布）；518 个未登记接口治理后置 `deny-unregistered=true`；`issuer` 配置与 `/login/logout` 服务令牌 `code=9999`；cs/KH 真实账号与生产 preview 浏览器回归。

**v0.2.1 收口口径（已修正）**：F-016 保持 `in_progress / runtime_unverified`；代码与门禁已推进，但温度真实阈值、518 接口 RBAC、Nacos/凭据轮换与生产观察仍未闭环，不能宣告完工。

### 追加：浏览器级回归与 SCAN-PARTIAL 运行时验证（2026-11-26）

- 浏览器级（Vite dev + CDP，证据父仓库 `.runtime_tmp/browser_regression_20261126.json` 与 5 张截图）：gly(admin) 侧边栏 25 个一级/129 项，含「每日检查 → 异常巡检」；cw(cwtest001) 仅 9 项、无异常巡检、无静态菜单残留，数据面 `/agent/alerts/page` → HTTP 200 + `code=9997`；cs/KH 开发库无可登录用户，改用合成空菜单 + 路由守卫单测覆盖；`/inspection/alerts` 渲染 14 条告警，含 4 条 `OUTBOUND-EXCEPTION` P0（alertId 30/31/32/33），详情抽屉显示 `description=下架后超过 24 小时仍未处理`、`ageHours=125.66`、`downOrderId=YC-DOWN-002`、`locationCode=CK20261121-0002`。
- SCAN-PARTIAL 运行时（当时 memory 后端）：临时实例 11203 + 桩网关 11204，`page_drift` → SCAN-PARTIAL open（objectId=`no_up`、v1、P2）；恢复一致 → `alertsAutoResolved=1`、SCAN-PARTIAL resolved，三条 NOUP-OVERDUE 保持 open（证据 `.runtime_tmp/scan_partial_lifecycle_runtime.json`）。后续已用**真实 PG** 复做（`scan-ae5e4c80ec63428b` → `scan-8e2e3de2ed3c42c5`，alertId=38 关闭），见 `.runtime_tmp/scan_partial_lifecycle_pg.json`。

### 追加：第五轮独立复核后的加固（2026-11-26，用户 m03535）

用户复核判定「有实质进展但不能签收；ADR-021 只能记部分修复」，并列出 5 组阻断。本轮修复：
1. 网关 v1.1.0（`GatewayAccessFilter`/`GatewayAccessProperties`）：Actuator 白名单收窄到 `/actuator/health`（`wms-common` 暴露改为 `health,info`）；服务令牌边界按 `token_use=agent_service` + `service-token-paths`；未登记路径必须命中 `unregistered-allow-paths`（85 条，源自我方覆盖率快照）否则 403；路径归一（尾斜杠/`;x=1`/`//`/`..`）不可绕过；角色缓存异常 fail-closed 503；401/403 带 CORS。24 例单测入门禁。
2. 凭据：`third-services.yaml` FastDFS `http-secret-key` → `${FASTDFS_HTTP_SECRET_KEY:}`；`init.sh check_credentials` 覆盖 password/secret/api-key 类键且不回显值；旧 API Key 宽限关闭（k2 → code=10000，k1 → HTTP 200 + code=401）。
3. 分页与前端：`PageQuery` 默认 `pageIndex=1/pageSize=10`；`layouts/default.vue` 已登录用户空菜单不再回退静态路由；`use-permission.ts` 空角色只读并纳入 `cs`。
4. SCAN-PARTIAL 生命周期：`object_id` 改为来源、`rule_ok` 纳入、`_auto_resolve_cleared(..., scanned_sources=...)` 只在扫描过同一来源时关闭。
5. 证据纠偏：JWT 脱敏、服务令牌撤销时效修正、未知 API Key 标注为 HTTP 200 + body code=401；ADR-021 状态改「部分修复（第二轮加固后）＝生产仍阻塞」。
门禁：Java 18 类 107 tests、Python 586 tests / 68 skipped、前端 3 例、`./init.sh --quick` PASS。

### 追加：第二阶段门槛收尾与 F-016 真实 e2e（2026-11-26）

- ADR-021 网关鉴权：新增 `wms-java/wms-gateway/src/main/java/com/zeroone/star/gateway/security/GatewayAccessProperties.java` 与 `GatewayAccessFilter.java`（`WebFilter` + `Ordered.HIGHEST_PRECEDENCE`，因为 Spring Security 的 `WebFilterChainProxy` 在 `GlobalFilter` 之前）；实测匿名 401、坏令牌 401、Basic 401、白名单 200、错角色 403、注销后 401「用户凭证已注销」、未登记 200 + WARN；错误角色 403 通过临时改 Redis `AUTH:RESOURCE_ROLES` 实测后恢复。
- 凭据：`nacos-config/data-source.yaml`、`key-config.yaml` 全量 `${ENV}` 占位（保留中文注释、无 BOM）；`wms-login/application.yaml` 去掉 jks/key 口令默认值；新增 `nacos-config/README-credentials.md`；API Key 轮换实测（k2 生效、k1 宽限、未知 key 401），证据 `.runtime_tmp/cred_rotation_result.json`。
- F-014：菜单可见性 API 级 6/6（cg/ckjl/gly 可见、cw/cs/KH 不可见）；真实 `bin_sta='N'` 过滤 e2e（5 行夹具 → 巡检 3 行 / 旧端点 5 行，已清理）；201/2001 条分页与排序（`sort=oldest` 全局非降、并列按 id 升序）与性能（pageSize=100 首屏 avg 59.8 ms / p95 88.1 ms）。
- LLM：生产 `llm.enabled=false`，历史 `stage8_real_model_summary_quality.json` 的模型是 `glm-5.4` 经 DSH 通道（非生产模型），落 `llm_applicability_result.json` → `decision=not_applicable`。
- 定时巡检（`scheduled_scan_unattended.json`）：无人值守每次重新取服务令牌、cron 连续 5 槽 succeeded、取令牌失败只落 `failed/auth_failed:*` 不影响服务、metrics 与 retention 端点可用、partial 不自动关闭、保留策略归档+清理实测。
- F-016 真实 e2e：真实 MySQL 应用 F-016 种子两次（幂等）+ Redis `AUTH:RESOURCE_ROLES` 刷新 200 + 真实网关（匿名 401 / 服务令牌与 gly 200 / cw 403）+ agent 真实扫描：出货 46 行 → 4 条 P0，`evidence.description=下架后超过 24 小时仍未处理`、`ageHours` 125.66~167.33、无「未闭环」字样；温度按 `enabled=false` 跳过（`srcScan-fbff499dd36b4d1b`，skippedTypes `[temperature]`）。

### 追加：阶段8 Python 规则完成（2026-11-26）

- `wms-agent/app/scan/sources/outbound.py`、`sources/temperature.py` 走 `fetch_paged(..., require_page_dto=True)`（outbound 带 `sort=oldest`）。
- `app/scan/rules/outbound.py`：`OUTBOUND-EXCEPTION`（v0.2.1），`create_date` 缺失/未来 → 数据质量跳过；>24h → P0、其余 → P1（不设 P2）；`object_id=bin_id_to|goods_id|cus_code`；`evidence.description` 固定「下架后超过 24 小时仍未处理」。
- `app/scan/rules/temperature.py`：`TEMP-EXCURSION`（v0.2.1），地点 aliases 归一化、未匹配地点 P2 元告警、倒填/未来读数跳过、连续超限/单点超限/无录入分级，`knownLimitation` 记录不做商品级温区 join。
- 注册：`service.py`（`SUPPORTED_TYPES` 增 `outbound`/`temperature`、`HANDLERS`、`RULE_VERSIONS`、`_type_enabled` 独立开关、`_evaluate` 两个分支）、`config.py`（`OutboundRules`/`TemperatureRules`/`TemperatureLocation`，`enabled` 默认 false 且 `locations=[]` 时 fail-closed）、`schemas.py`、`config/scan.yaml`（占位不写示例阈值）、`llm/summarizer.py`（标题/指标/摘要片段）。
- 测试 `tests/test_scan_f016_outbound_temperature.py`；全量 pytest 曾达 491 passed。

### 追加：阶段8 Java 数据契约完成（2026-11-26）

- 出货异常新增独立分页端点 `GET /daycheck/yi-chang/get-yichang-down-page`（`PageDTO<YichangDownDTO>` + `rowId`，显式列清单、`ORDER BY create_date,id`、`CAST(goods_qua AS DECIMAL(18,4)) <> CAST(goods_quaok ...)`、数量 NULL 不静默丢弃、仅 `sort=oldest`）；旧端点保留（`SELECT *` 兼容）。
- 温度 `TemperatureVO`/`DTO` 补 `createDate`，`pageQueryAll` 改 `order by wendu_cjsj asc, id asc` 由分页插件注入。
- `documents/02、项目需求/数据库/seed_daycheck_f016_inspection_role.sql`（insp_read 资源与绑定，动态 rolecode、存在性预检、纯增量、`ID varchar(32)`）；5 个新测试类（Mapper XML、Controller 契约、Service、温度 XML、种子契约）加入 `init.sh` 门禁（15 类 → 当时 41 tests）。

### 追加：阶段8 决策门确认与开工（2026-11-26）

- m00024 决策：出货异常按 **24 小时自然时间**老化；**不新增闭环字段**，文案只描述「下架后超时未处理」，不得声称「未闭环」；数据契约按计划执行。
- 温度：真实业务值（标准地点名 / aliases / 最低最高温度 / 实际录入间隔）由用户提供，进入版本化 `scan.yaml` 并冻结进扫描快照；**缺值时 `temperature.enabled=false` 且不产生生产告警**，禁止把示例 2–8℃/8h 当生产阈值。
- F-016 置 `in_progress`，登记三条实施前决策与证据入口。

### 追加：阶段8 v0.2.1 登记（2026-11-26）

- 阶段 7.7 验收通过（F-015 保持 `passing/e2e_pass`）；新登记 `F-016：v0.2.1 出货异常与温度巡检`（priority 16，5 条验证项，`not_started`）。
- 实施顺序：业务口径 → Java 数据契约（独立分页数据源、稳定 `rowId/create_date`、Decimal 数量、`insp_read` 资源映射与 Redis 刷新、真实 MyBatis 映射测试）→ Python 规则（`OUTBOUND-EXCEPTION` / `TEMP-EXCURSION`，两类独立开关，partial 不自动关闭）→ 验收（Memory/PG 契约、Java+网关+agent 真实 e2e、前端巡检页展示、evidence 与 v0.2.0 分开）。

### 追加：剩余实施路线图阶段7.7（2026-11-25，用户 m09157 验收决定）

- **目标**：按用户验收决定补齐三项保留口径——扫描记录及其证据与告警证据一致（在线 180 天→归档 1 年）、通知 90 天在线后归档 1 年、聚合统计 2 年（90 天内实时、90 天至 2 年读日聚合）。
- **契约**：V012 `agent_metric_daily(metric_date, warehouse, timezone, metrics JSONB)`；`archive_notifications_before`、`archive_scan_evidence`、`get_archived_run`、`save_metric_daily`/`list_metric_daily`/`purge_metric_daily_before`；`POST /agent/scan/metrics/rollup/run`（仅管理员）；`GET /agent/scan/metrics` 的 `hours` 上限由 2160 提到 17520；保留执行由 5 步扩为 7 步；`WMS_AGENT_RETENTION_METRICS_DAYS`（默认 730）。决策见 ADR-020（2026-11-25 修订）。
- **已改**：`app/scan/migrations/V012__metric_daily.{up,down}.sql`、`app/scan/repository.py`、`app/scan/metrics_rollup.py`（新建）、`app/scan/retention.py`、`app/scan/router.py`、`app/config.py`、`.env.example`；`tests/test_scan_stage77.py`（新建 12 例）、`tests/test_scan_stage7.py`、`tests/test_scan_store_contract.py`；ADR-020、`技术选型ADR.md`、实施方案 §9.6。
- **本轮捕获并修复的真实缺陷**：`metrics_rollup.py` 三处——参数名 `timezone` 遮蔽 `datetime.timezone`（不传 `now` 时路由与调度器路径必崩）、降级原因计数对普通字典做 `+=`（有降级摘要的日期补算必失败）、合并最大值时与 `None` 比较（无样本日期合并必失败）。三处均由新测试发现，未进入真实环境。
- **已验证**：全量 pytest 带 PG 531 passed / 11 skipped、不带 PG 474 passed / 68 skipped；Java harness PASS；真实环境 e2e 21/21（日聚合 180 仓库·日且重跑幂等；合成过期扫描连同摘要、评估覆盖、命中观测、积压样本一次整批归档；100 天前通知归档；扫描记录/摘要/告警详情扫描简报读回落并标 archived；`hours=2160` 实时、`hours=2200` 走日聚合、`hours=17521` 422、越权仓库 9997；二次运行全 0）。
- **未验证与限制**：日聚合只回看 180 天补算，首次启用前更早的日期不补算（`coverage.missingDays` 如实暴露）；日聚合不提供分位数；真实库已由真实历史数据算出 180 行日聚合并保留；归档行无通用查询接口（读回落仅覆盖摘要与扫描简报）。
- **退出判定**：通过。F-015 按用户决定置为 passing / e2e_pass；生产上线阻塞项 ADR-021 不变。
- **提交记录（2026-11-25 23:59）**：待提交文件中新增的连接串口令已替换为 `<口令>` 占位；阶段 0–7.7 已分 5 批提交到父仓库 `main`（明确路径、未 push）：`4a64e3e` → `ccf22ef` → `9d270c3` → `d1e467d` → `c0182cc`（Java 前置端点/服务令牌/角色种子与门禁测试 → Python 巡检核心 → 存储契约与阶段 7/7.7 测试 → 前端异常巡检页面与摘要展示 → ADR-018~021/实施方案/状态文件）。未提交的基线文件：`.workbuddy-ai/memory/2026-11-23.md`、`.workbuddy-ai/memory/2026-11-24.md`、`wms-java/wms-oauth2/pom.xml`、`documents/07、AI-Agent化/业务场景分析/` 两份模板、`wms-agent/_e2e_recovery_result.json`、`wms-agent/docs/agent_architecture/问数agent-architecture.svg`、`wms-agent/docs/业务分析/异常巡检agent业务背景.md`。
- **下一步**：用户确认后登记阶段8 v0.2.1。

### 追加：剩余实施路线图阶段7（2026-11-25，用户 m07804 签收阶段6 并给定范围）

- **目标**：补齐 v0.2.0 收尾——retry 审计归属、前端摘要展示、管理员只读指标、保留与归档、v0.2.0 总验收、生产安全门。
- **契约（ADR-020 / ADR-021）**：
  - 重试记录回答「谁点了重试」：`actor_type=user`、`actor_id`=发起重试的管理员、`trigger=retry`、`retry_of_scan_id` 指向被重试的扫描；`origin_actor_type/origin_actor_id/origin_trigger` 保留根来源（链式重试不覆盖）；`executor_*` 仍由 worker 服务令牌决定。
  - 指标只读、实时聚合（窗口 1 小时–90 天，按请求时刻计算），不落统计表；扫描按 `started_at` 入窗，事件按事件时间入窗，活跃数为当前快照。
  - 保留：已结案告警及其事件在线 180 天 → 归档 1 年（单表 JSONB，`agent_archive_rows`）；通知、trace/tool_calls 90 天后删除；扫描摘要随扫描归档并在接口回落；每步限批（默认 500/批、最多 20 批/次）、可重入、先子后父；自动任务默认关闭，当天失败不重试。
  - 摘要可见性跟随告警可见性：能看扫描记录或能看该仓库告警即可读摘要；扫描记录本身可见性不变；告警详情只内嵌扫描摘要字段（`SCAN_BRIEF_KEYS`）。
  - 生产安全门：网关实测为「无 token 全放行、资源角色不生效」，范围是全部 Java 服务 → **阻塞生产上线**（ADR-021）；巡检端点以 agent 自验为准，15 条路由 × 5 类坏凭据全部 401 的回归已固化。
- **已改**：`wms-agent/app/scan/migrations/V010__scan_retry_attribution`、`V011__agent_archive_rows`；`app/scan/{service,router,repository,worker}.py`、新增 `app/scan/metrics.py`、`app/scan/retention.py`；`app/config.py`（保留策略 9 个 `WMS_AGENT_RETENTION_*`）与 `.env.example`；`app/security.py`（`can_view_scan_summaries`）；`app/main.py`（启停 `RetentionScheduler`）；前端 `src/apis/inspection/alerts.ts`（`fetchScanSummaries` 与纯函数）、`src/views/inspection/alerts/index.vue`（摘要卡片与抽屉竞态修复）；文档 `ADR-020-巡检数据保留与归档.md`、`ADR-021-网关认证与鉴权缺口（上线阻塞）.md`、`技术选型ADR.md`、实施方案 §5.1/§5.2/§9.6/§12.2。
- **本轮捕获并修复的缺陷**：①摘要可见性原先跟随扫描记录 → 仓库经理取不到定时巡检摘要；②`GET /agent/alerts/{id}` 内嵌完整扫描记录（配置快照、执行人、租约、错误摘要）越权；③详情抽屉关闭动画期间再点「详情」不重新打开；④PG 写通知忽略调用方 `createdAt`（e2e 捕获，Memory/PG 不一致）。
- **已验证**：
  - 自动化：`tests/test_scan_stage7.py` 36 例（指标口径、存储聚合、保留与归档、调度器、接口权限、路由级凭据回归）+ `tests/test_scan_store_contract.py` 新增 12 个契约用例（retry 归属、指标聚合、保留与归档、通知时间、告警内嵌摘要，Memory/PG 双后端）；全量 pytest 带 PG 512/10、不带 459/63；Java harness PASS（41 tests）。
  - 前端：Vitest 15 passed；`vite build --mode production` BUILD_EXIT=0；真实 Chrome（headless + dev server）验证「模型摘要」「模板摘要 + 降级原因」「入库延迟无客户维度」三种形态、ckjl001 可见，以及抽屉关闭后 0–450ms 内重开；evidence `.runtime_tmp/stage74_summary_llm.png`、`stage74_summary_template_fallback.png`（**模型是本地桩 stage7-stub**）。
  - 真实环境总验收（`.runtime_tmp/stage7_acceptance_e2e_result.json`，STAGE7_E2E_OK 29/29）：admin 发起 no_up 扫描 → ckjl001 重试 403 → admin 重试后 PG `trigger=retry`、`retry_of_scan_id`、`origin_*=user/admin/manual`、executor=service/agent-inspector；admin 重试阶段5 的定时扫描 → origin 为 service/agent-inspector/schedule；调度槽位 `20261125T2200` 只有一条扫描且按临时启用的快照执行；`GET /agent/scan/metrics?hours=24` 管理员 10000、ckjl001/cwtest001 9997、新扫描 `sourceStatus.durationMs` 有值；`POST /agent/scan/retention/run` 业务角色 403、管理员执行后合成过期行被删除/归档、步骤顺序正确、归档摘要回落 `archived=true`、二次运行全 0、真实告警 10→10 未动。
  - 网关实测（ADR-021 证据 `.runtime_tmp/_probe_gateway_75_out.json`、`_75b_out.json`）。
- **未验证与限制**：真实模型的摘要质量未评估；扫描记录与评估覆盖/命中观测/积压样本无保留期（只增不减）；通知与 trace 到期后直接删除不归档；归档数据无查询接口与预览（dry-run）接口；「聚合统计 2 年」未落地；生产上线被 ADR-021 阻塞。
- **退出判定**：阶段7 六项均已落地并有真实环境证据，v0.2.0 总验收通过；F-015 状态与 v0.2.1 登记待用户确认。
- **下一步**：用户确认后进入阶段8（登记 v0.2.1）；平台侧按 ADR-021 修复网关认证与资源鉴权后再做生产验收。

### 追加：剩余实施路线图阶段6 LLM 聚合摘要（2026-11-25，用户 m07086「直接阶段 6」）

- **目标**：给一次巡检的 P0/P1 告警生成「这组告警说的是什么事、先做什么」的人读摘要；LLM 只负责表达，不参与判定；任何模型侧失败都不影响告警落库与扫描结果。
- **契约（ADR-019）**：
  - 只摘要不判定：`ruleId/severity/objectCount/severityCounts` 取自规则结果；模型输出只取 `summary` 与 `suggestedActions[{code,text}]`，其余字段忽略；建议动作只展示不执行（ADR-017）。
  - 输入白名单：按 `rule_id + warehouse + customer` 聚合后的 digest（规则、级别分布、区间指标、≤5 个样本标签、允许的动作码），**不含原始行、`sourceRowKey`/`sourceEndpoint`、司机姓名/电话/车牌**。
  - 输出约束：摘要纯文本 ≤300 字（去 HTML 标签/Markdown 强调与链接/URL/零宽与双向控制字符）；建议动作 code 取「白名单 ∩ 规则已给出的动作」，≤3 条、每条 ≤100 字，未知 code 丢弃。
  - 默认关闭、快照决定：`llm.enabled` 默认 `false`，`llm` 段进入配置快照与哈希（ADR-018）；worker 只在入队快照启用时构造 provider；6 个上限（调用 20 / 超时 8s / 并发 4 / 摘要 300 字 / 动作 3 条 / 每条 100 字）是启动硬上限。
  - 失败降级模板：P2、partial 取数、模型不可用、调用上限、预算耗尽、超时、非法 JSON、违反 schema、空摘要 → 确定性模板 + `fallbackReason/fallbackDetail`；模型已应答但不合规时 `model` 与 token 用量照记。
  - 读取接口：`GET /agent/scans/{scanId}/summaries`，可见性与 `GET /agent/scans/{scanId}` 完全一致。
- **已改**：`wms-agent/config/scan.yaml`（`llm` 段）；`app/scan/config.py`（`LlmConfig`，带默认值 → 旧快照仍可回放）；新增 `app/scan/llm/summarizer.py`；`app/scan/migrations/V009__scan_llm_summaries.up.sql`（表 `agent_scan_summaries`，唯一键 `scan_id+rule_id+warehouse+customer`）；`app/scan/repository.py`（协议 `save_scan_summaries/list_scan_summaries` + Memory + PG，`normalize_summary_source`）；`app/scan/service.py`（`run_scan` 新增 `llm_provider` 参数，在告警落库与自动关闭之后编排摘要；`DEFAULT_CONFIG`/`DEFAULT_COUNTS` 同步）；`app/scan/worker.py`（`_build_llm_provider` 仅按快照启用）；`app/scan/router.py`（抽出 `_load_visible_scan`，新增 summaries 接口）；`app/llm/mock.py`（场景条目可带 `usage`）；`app/llm/openai_compatible.py`（HTTP 错误带脱敏、截断后的可读详情）；`tests/test_scan_stage6.py`、`tests/test_scan_store_contract.py`（V009 契约 6 例）、`tests/test_scan_round4.py`（迁移守卫测试改动态版本号）；`documents/07、AI-Agent化/ADR-019-巡检LLM摘要边界.md` 与 `技术选型ADR.md`（索引、条目、风险表）。
- **本轮捕获并修复的缺陷**：①契约测试发现 PG 把未知 `summarySource` 归一为 `template` 而 Memory 原样保留 → 统一 `normalize_summary_source`；②summarizer 成功路径未累加 token（只有失败路径记账）→ 成功与已应答降级行都记 `promptTokens/completionTokens`；③`test_migration_rollback_requires_applied_and_latest` 写死「未知版本 9」，V009 落地后 9 变成合法版本 → 按 `discover_migrations()` 动态计算。
- **已验证**：
  - 自动化：`tests/test_scan_stage6.py` 73 例（配置校验与旧快照兼容、聚合与输入白名单、清洗与 schema、仅 P0/P1 调用、调用上限、超时/预算/异常降级、并发上限、token 记账、提示注入不改级别与结构、dry-run 不摘要、摘要存储失败不拖垮扫描、worker 传 provider、API 可见性、`httpx.MockTransport` 走真实 `OpenAICompatibleProvider`）；全量 pytest 带 PG **452 passed / 7 skipped**、不带 PG **411 passed / 48 skipped**；Java harness **HARNESS_EXIT=0**（41 tests BUILD SUCCESS，2026-11-25T19:26:37）。
  - 真实链路 A（`.env` 所配外部模型，未改用户 `.env`）：入队 `llm.enabled=true` 的快照 → `scan-f9a6e79ace184137` succeeded、8 条命中照常落库，5 组全部 `provider_error`（该网关对话接口对本机返回 `HTTP 400 Request path cannot be relayed`，13 个模型均如此，属环境问题）并降级模板。
  - 真实链路 B（本地 OpenAI 兼容桩 `127.0.0.1:11800`，**模型是桩**；agent 以进程环境变量 `WMS_AGENT_LLM_*` 临时覆盖）：经网关以真实 admin JWT 入队 → `scan-ed05c09285484d62` succeeded、`llmCalls 5 / llmFailures 2 / summariesLlm 3 / summariesTemplate 2 / promptTokens 462 / completionTokens 90`；3 组取得模型摘要，2 组超过 8 秒降级模板；桩侧 5 个请求全部鉴权通过、请求体只含白名单键；经网关读取接口 code 10000，无 token 401，ckjl001 得 9997。对照 `scan-0a35bc93881e4eed`（快照未启用）期间模型端点零请求、5 行全模板。e2e 共 22 项全过（**STAGE6_E2E_OK**），evidence `.runtime_tmp/stage6_llm_summary_e2e_result.json`。
  - 收尾：桩已停止；agent 已以默认配置重启（`llm` 关闭，`configHash=sha256:339c13d0…`）；中途两轮被取代的 e2e 扫描及其摘要/覆盖记录/积压样本行已清理，保留三条证据扫描。
- **未验证与限制**：真实模型的摘要质量未评估（外部模型在本机不可用，桩只证明链路与边界）；前端 `/inspection/alerts` 尚未展示摘要；`llm.enabled` 启用属部署决策；digest 仍含货名/客户名/供应商名等业务标识（已是最小集合，零外发可保持关闭）；提示注入只能降低不能消除（级别与对象不受影响）；「网关 GET 无 token 仍被第三方 starter 放行」继续作为部署前安全未闭环项保留；阶段0–6 改动均未提交（用户 m07086 指示不提交）。
- **退出判定**：阶段6 用户清单项均已落地并有真实链路证据 → 退出条件满足；F-015 整体仍 `in_progress/runtime_unverified`（不升级）。
- **下一步**：阶段7 指标与保留 + v0.2.0 总验收（须等用户确认再进）；待用户决定：前端是否展示摘要、重试记录归属是否按实施方案改为「原身份 / trigger=retry」。

### 追加：剩余实施路线图阶段5 自动 resolved + 内部调度（2026-11-25，用户 m06123 清单）

- **目标**：条件消失后告警自动关闭（严格、可审计、不误关），并把定时触发从外部 cron 收回到 agent 内部（默认关闭）；不提前做 LLM 摘要（阶段6）。
- **契约（先定后写）**：
  - 关闭条件九条同时成立才关闭：源 `status=ok` 且未截断；本次扫描非 partial；该规则本次已登记为「已评估」；对象不在本次命中集；告警 `lastSeenAt` 早于本次扫描开始时间；`ruleVersion` 与当前规则版本一致；仓库一致；状态为 `open/acknowledged`；忽略窗口未生效。数据质量跳过（缺时间/未来时间/畸形快照）不参与关闭。
  - V008 `agent_scan_evaluated_objects`：每次扫描每个对象每个规则一行，`UNIQUE(scan_id,rule_id,object_id,dimension_hash)` 幂等；自动关闭用「已评估且未命中」判定，而不是「没出现」。
  - 幂等三重：`requestId+actorId` / `scheduleSlot+configHash+scanTypes`（`uq_scan_runs_schedule`）/ 活动态 `scanKey`；统一入口 `service.enqueue_scan`。
  - 调度：`schedule.enabled` 默认 `false`；`cron="*/15 7-23 * * *"`、`timezone=Asia/Shanghai`；错过不补跑；同一槽位进程内只入队一次，重启后由 PG 唯一索引兜底。
  - `POST /agent/scans/{scanId}/retry` 是**管理员接口**（用户 m07086 修正）：仅 `is_scan_admin`，服务账号一律拒绝；原扫描归属沿用查询规则 `can_view_scan`——本人发起的手动扫描或服务账号发起的定时扫描，他人手动扫描 403；权限判定先于取记录（非管理员探测存在/不存在的 scanId 得到同一 403）。复用原扫描的 configSnapshot/configHash/configVersion/scanTypes/warehouse/dryRun/notificationMode（无快照 409、不存在 404）。
- **已改**：
  - 规则层：`app/scan/rules/base.py` 增 `EvaluatedKey`、`RuleEvaluation.evaluated_keys/data_quality_skipped/skip()`；`rules/{expiry,no_up,delay,backlog}.py` 命中与未命中都登记已评估，缺时间/未来时间/非法值登记为质量跳过。
  - 存储：`app/scan/migrations/V008__scan_evaluated_objects.{up,down}.sql`；`repository.py` Protocol 与 Memory/PG 双后端新增 `save_evaluated_objects`、`list_evaluated_objects`、`list_auto_resolve_candidates`、`auto_resolve_alert`（PG 用 `CTE prev … FOR UPDATE` 取旧状态）。
  - 服务：`service.py` 新增 `enqueue_scan`、`_auto_resolve_cleared`、`SCAN_TYPE_RULE_IDS`、`compute_retry_scan_key`；`counts` 增 `alertsAutoResolved/staleCheckSkipped`。
  - 调度与入口：`app/scan/scheduler.py`（`parse_scan_cron`/`current_slot`/`ScanScheduler.tick`），`app/main.py` lifespan 随服务启停；`router.py` 新增 retry 接口，入队改走 `enqueue_scan`。
  - 配置：删除死配置 `WMS_AGENT_SCAN_QUEUE_ENABLED`（`app/config.py`、`.env.example`、`config/scan.yaml` 的 `schedule.enabled` 承担开关语义）。
- **本轮捕获并修复的真实缺陷（均为 Memory 单测全绿、PG 契约或真实 e2e 才暴露）**：
  1. PG 建告警不接受调用方 `lastSeenAt`（`first_seen_at/last_seen_at` 直接取 `DB now()`）→ 回填观测时间的告警永不满足自动关闭的新鲜度条件。修复：`_ALERT_INSERT_SQL` 改 `COALESCE(%s::timestamptz, now())`。
  2. 源合法返回 0 行时求值结果为空，`rule_ok` 没有任何规则登记 → 自动关闭被整体跳过（单测里第二次扫描总留一条不超期行，掩盖了该分支）。修复：`SCAN_TYPE_RULE_IDS` 按扫描类型登记全部规则；`_evaluate_backlog` 对畸形快照登记 `data_quality_skipped`。
  3. PG 自动关闭事件 `from_state` 取自 `UPDATE … RETURNING state`，拿到的永远是新值 → 事件被写成 `resolved→resolved`。修复：CTE 先 `FOR UPDATE` 取旧状态再 UPDATE；契约测试补断言 `fromState`。
  4. （用户 m07086 评审发现）retry 接口误用 `can_trigger_scan` 做门禁：ckjl/cg/仅 `inspection:scan:trigger` 权限码/服务账号都能重试，且未校验原扫描归属；原测试恰以 ckjl 身份重试并通过，等于把缺陷测成了功能。修复：新增 `security.can_retry_scan`（仅管理员 + 原扫描归本人或服务账号发起），`router.py` 先判管理员再取记录。
- **已验证**：`tests/test_scan_stage5.py` 44 例（必测 10 项全覆盖：条件消失才关闭 / partial·page_drift·5xx 不关 / 质量跳过不关 / 乱序不关 / ignored 不复活 / 复发新建 / 用户先解决则不自动关 / fake clock 窗口边界·重启·重复槽 / 调度关闭不入队 / retry 复用旧快照；另 retry 权限 14 例：管理员正例 2、403 负例矩阵）；`tests/test_scan_store_contract.py` 增 V008 段（覆盖幂等、auto_resolve 条件 UPDATE、候选查询、并发唯一赢家、事件 fromState）；全量 pytest 带 PG **368 passed / 6 skipped**、不带 PG **333 passed / 41 skipped**；`./init.sh --java-test` **HARNESS_EXIT=0（41 tests）**；真实 e2e **STAGE5_E2E_OK**（四项见顶部条目，evidence `.runtime_tmp/stage5_auto_resolve_e2e_result.json`）；retry 权限真实令牌 e2e **RETRY_E2E_OK**（14 项，evidence `.runtime_tmp/retry_permission_e2e_result.json`）。
- **未验证与限制**：调度器默认关闭，启用后长期运行的稳定性未压测；多实例同时 tick 只验证了「重启重放」，未做多进程并发实测（依赖 `uq_scan_runs_schedule` 兜底）；自动关闭只覆盖「未再命中」一种原因，人工认领中的告警同样会被关闭（条件消失即关闭是设计选择，事件流可审计）；网关 GET 无 token 仍被第三方 starter 放行，该安全未闭环项保留至生产验收。
- **退出判定**：阶段5 退出条件满足（自动 resolved 严格条件 + 内部调度 + retry + 必测 10 项 + 契约 + 真实 e2e 四项全部通过）；F-015 仍 `in_progress/runtime_unverified`，待阶段6/7。
- **下一步**：阶段6 LLM 聚合摘要（须用户确认后进入）；阶段7 指标与保留 + v0.2.0 总验收；阶段8 v0.2.1。

### 追加：剩余实施路线图阶段4 版本化 YAML + ADR-018（2026-11-25，用户 m05130 七项清单、m05303 指定先做配置契约）

- **目标**：把四类规则阈值、仓库范围、预算、责任路由、通知模式与调度开关从代码常量/env 迁到仓库内版本化 `scan.yaml`，实现「启动一次性校验 + 入队冻结 canonical 快照 + worker 只读快照回放」；密钥不进 YAML；不启用调度器、不做自动 resolved（阶段5）。
- **配置契约（先定后写）**：新建 `wms-agent/config/scan.yaml`（`version/warehouses/scan{pageSize,maxPages,requestTimeoutSeconds,sourceBudgetSeconds,scanBudgetSeconds,concurrency}/rules{expiry,noUp,delay,backlog}/routing/notifications/schedule`）；新建 `app/scan/config.py`：pydantic 模型全部 `extra="forbid"`，校验 `p0Hours>p1Hours>p2Hours`、`watchDays>=nearDays`、`scanBudgetSeconds>=sourceBudgetSeconds`、通知模式 `dry_run|in_app|full`、路由 `rule_id` 必须命中 `KNOWN_RULE_IDS`（或 `*`）、路由 `warehouse` 必须在 `warehouses` 内、`warehouses` 非空不重复；自定义 `_UniqueKeyLoader` 拒绝重复键与非字符串键；`canonical_json`（`sort_keys` + 紧凑分隔符）与 `hash_config`（`sha256:` 前缀）是唯一指纹来源。`ScanConfigError` 定义在 `app/config.py`，10 个精确错误串（`YAML 重复键: {key}（行 N）`、`巡检配置非法: {exc}`、`config_snapshot_hash_mismatch` 等）。
- **已改**：
  - Python 配置层：`app/scan/config.py`（新建，287 行）、`config/scan.yaml`（新建）、`app/config.py`（`scan_config_path` / `WMS_AGENT_SCAN_CONFIG_PATH`）、`app/main.py`（启动加载 + 按 `settings.model_fields_set` 只把真正由 env 提供的三项作为 override 合并，再算快照与哈希；非法配置拒绝启动；`ensure_single_scan_warehouse` 仍强制单仓；`app.state.scan_config`）、`pyproject.toml`（`pyyaml>=6.0`）。
  - 快照冻结：`migrations/V007__scan_config_snapshot.{up,down}.sql`（`agent_scan_runs` +`config_snapshot TEXT`/`config_version TEXT`，保留 `config_hash`；down 先备份到 `agent_scan_runs_v007_config_backup`）；`repository.py` 的 `RUN_COLUMNS`/`_run_params`/`_row_to_run` 三处同步 31 列；`router.py` POST /scan 写 `configSnapshot`/`configVersion`/`configHash`/`notificationMode`（均取自生效配置）。
  - 快照回放：`worker.py` `execute_queued_scan` 只从 `run["configSnapshot"]` 反序列化执行，不再读当前 `scan.yaml`；缺失 → `failed(config_snapshot_missing)`，哈希/版本不符 → `failed(config_snapshot_hash_mismatch)`/`failed(config_snapshot_version_mismatch)`；该检查**有意排在鉴权之后**（鉴权失败是更早的失败语义）。
  - 责任路由：`service.py` 新增 `resolve_route_targets`（按 `warehouse`+`rule_id` fnmatch 解析）与 `_rule_config` 兼容层；`DEFAULT_CONFIG` 改为与 `scan.yaml` 同构嵌套；`routed_to` 只写责任岗位，`assignee` 仍只由 claim 写；手动/用户身份只通知发起人，定时/服务身份合并 `notifications.recipients` 与路由 recipients 去重，解析不到记 `counts.notificationsUnrouted` 且不写占位账号。
  - 文档：新建 `documents/07、AI-Agent化/ADR-018-巡检规则配置.md`（7 章：背景/决策/与 ADR-014 的有意例外关系/规则版本 vs 配置版本/后果/验证证据表/未覆盖范围）；`技术选型ADR.md` 索引表与正文摘要本已存在，无需重写。
- **本轮捕获并修复的真实运行时缺陷（单测全绿、真实回放才暴露）**：`load_config_snapshot` 原对 `document.model_dump()` 重算哈希，pydantic 把 `p0Hours: 24` 归一化为 `24.0`，导致入队侧 `sha256:ed25ab23…` 与消费侧 `sha256:e15ff7b6…` 不一致、合法快照被判 `config_snapshot_hash_mismatch` → 改为对 `json.loads(snapshot)` 的**原始 dict** 算 `canonical_json`，并由 `test_snapshot_roundtrip_keeps_hash` 守住。另修 `service.py` 漏 `import hashlib`/`import json`（38 例失败主因）、配置扁平→嵌套未同步的读取点、worker 检查顺序。教训：**配置快照哈希必须对原始字节/dict 计算，绝不能对模型序列化结果计算**，只有「写快照→读快照回放」往返测试能捕获。
- **已验证**：`tests/test_scan_config.py` 26 passed / 1 skipped（PG 回放用例需 `WMS_AGENT_TEST_DB_URL`）；全量 pytest 带 PG 测试库 **313 passed / 5 skipped / 1 warning**（阶段3 基线 277 → +36）、不带 PG **284 passed / 34 skipped**；`./init.sh --java-test` HARNESS_EXIT=0，10 个门禁类 41 tests BUILD SUCCESS；真实 e2e **STAGE4_E2E_OK**（与 router 同构的入队路径写 A → 改文件为 B → `claim_next_queued` + `execute_queued_scan` 消费）：A `sha256:479605f8…`/noUp 8/4/2，B `sha256:451c2e31…`/noUp 3/2/1，执行结果 `status=succeeded`、`config_hash`/`config_version` 回读为 A、执行快照 `p0Hours=8.0`（未变成 B 的 3.0）；脚本结束自动还原 `scan.yaml` 并已核对回 8/4/2。
- **未验证 / 限制**：调度器仍未启用（`schedule.enabled` 默认 false，阶段5 实现）；多仓未开放（强制单仓）；不做热重载；e2e 走的是与 router 同构的入队路径而非真实 HTTP POST（运行中的 agent worker 会立即抢走 queued 任务，且进程级 `WMS_AGENT_NOTIFICATION_MODE=in_app` 会让生效哈希与纯文件哈希天然不同——这是「最终生效配置」语义）；网关 GET 无 token 仍被第三方 starter 放行，安全未闭环项保留至生产验收。
- **阶段4 退出判定**：满足——V007 迁移通过并已写入真实 PG；启动校验生效（非法配置拒绝启动）；所有新扫描都有 `config_snapshot/config_hash/config_version`；worker 不重读 YAML；路由与通知模式来自生效快照；ADR-018 落盘；Memory/PG 契约测试与真实 e2e 通过。F-015 保持 `in_progress/runtime_unverified`。
- **下一步**：阶段5 自动 resolved + 内部调度（用 `schedule.enabled`/cron/timezone 触发，按 YAML 路由解析接收人，自动关闭消失的告警但保留 partial 期间不自动关闭）。改动均未 git add/commit。

### 追加：剩余实施路线图阶段3 backlog+一致快照（2026-11-25，用户 m02548 指定、m04555 确认进入）

- **目标**：按用户路线图阶段3 落地第四类规则 BACKLOG-GROWTH——Java 新增一致快照端点、Python 数据源/规则/编排、V006 观测表、必测场景与真实 e2e；不接 LLM、不做自动 resolved、不加调度器、Python 不直读 MySQL、旧 Dashboard 缓存端点不改、不用四队列总和掩盖单队列突增。
- **规则契约（先定后写）**：receipt/to_up/pick 三队列分别判定，cur_pick 只诊断；前 3 次完整扫描只建基线；第 4 次起单周期 `growth≥30% 且 absolute_delta≥10` → P2；P1 = 最近 3 次相邻增长均满足门槛（最早第 6 次）；基线 0 不做百分比判断；负值/非法值该队列跳过不落样本不告警；partial/快照失败/业务码失败不落样本不告警（只有 SCAN-PARTIAL 元告警）；手动扫描计入基线但受 requestId 幂等约束；基线严格按 rule_version 过滤。
- **已改**：
  - Java：`wms-domain/.../vo/j1/dashboard/PendSnapshotVO.java`、`wms-j1-dashboard/.../service/IPendSnapshotService.java` + `impl/PendSnapshotServiceImpl.java`（`@Transactional(readOnly=true, isolation=REPEATABLE_READ)`）、`WmOmQmIMapper.java` 一条 `@Select` 四个标量子查询（`IFNULL(SUM(CAST(col AS DECIMAL(18,4))),0)`，绕过 Redis 缓存，BigDecimal）、`DashboardApis.java`/`DashboardController.java` 新增 `GET /dashboard/query-pend-snapshot`；测试 `PendSnapshotContractTest`（4）/`PendSnapshotResourceRoleSeedTest`（3）；资源种子 `documents/02、项目需求/数据库/seed_dashboard_pend_snapshot_role.sql`（纯增量，ID 用 `FN-DASH-PEND-SNAPSHOT`/`RF-DASH-PEND-SNAPSHOT-INSPECT`，已在真实 MySQL 幂等执行并刷 Redis）；`init.sh` 门禁纳入两个新测试类（10 类）。
  - Python：`app/scan/rules/backlog.py`、`sources/backlog.py`（`parse_snapshot`/`normalize_observed_at`）、`service.py`（HANDLERS/SUPPORTED_TYPES/DEFAULT_CONFIG.backlog/`_evaluate_backlog`/`_is_non_negative_number`）、`repository.py`（`save_backlog_observations`/`list_backlog_observations` 双后端、`_parse_observed_at`）、`migrations/V006__backlog_observations.{up,down}.sql`；测试 `tests/test_scan_backlog_rule.py`（32）、`tests/test_scan_backlog_scan.py`（27）、`test_scan_store_contract.py` 新增 3 例（双后端唯一/稳定排序、Java ZonedDateTime observedAt、PG 并发唯一约束）。
- **本轮捕获并修复的真实运行时缺陷（单测全绿、真实 e2e 才暴露）**：①MyBatis 无法把列映射到 interface（`ReflectionException: Error instantiating interface …PendSnapshotRow`），JDK8 契约测试只 mock service 覆盖不到 → `PendSnapshotRow` 改 static class；②Dashboard `observedAt` 为 Java `ZonedDateTime.toString()` 带 `[Asia/Shanghai]` 区域 ID，psycopg 解析 TIMESTAMPTZ 抛 `InvalidDatetimeFormat` → 整次扫描 failed（Memory 后端只存字符串故单测全绿；PG 探针手写无方括号时间未复现）→ 源头 `normalize_observed_at` 去后缀 + 存储层 `_parse_observed_at` 兜底转 aware datetime（只接受带偏移 ISO，不把 naive 当 UTC 猜），Memory 同样规范化并按真实时刻排序；`run_scan` 失败日志加 `exc_info`（errorSummary 仍只给类型名）。教训：**Memory/PG 契约测试必须喂真实上游形态（含时区后缀）**，手写简化样本会漏掉这类缺陷。
- **已验证**：全量 pytest 带 PG 测试库 **277 passed / 4 skipped / 1 warning**；`./init.sh --java-test` HARNESS_EXIT=0，10 个门禁测试类 41 tests BUILD SUCCESS；真实 e2e **STAGE3_E2E_OK**（evidence `.runtime_tmp/_e2e_stage3_out.txt`）：dashboard(10010，JDK17 重新打包启动) 经网关 `GET /dashboard/query-pend-snapshot` code 10000，`observedAt=2026-11-25T13:12:59.319353300+08:00[Asia/Shanghai]`、`receipt 0.0 / toUp 0.0 / pick 45.0 / curPick 74.0`（与 MySQL `wm_om_qm_i bin_sta='I'` 两行 45 一致）；admin JWT 连发 7 次 `POST /agent/scan{scanTypes:[backlog]}` 全部 succeeded partial=False backlogSamplesSaved=3；PG `agent_backlog_observations` 恰 21 行（7×3，`pick=45.0000`，observed_at 已去方括号带纳秒 +08:00，`rule_version=v0.2.0 source_status=ok`，与 `agent_scan_runs.trace_id` 串联）；真实 pick 恒 45 → 增长 0 → 0 条 BACKLOG-GROWTH（基线不误报）。告警路径（P2/三连 P1）由 32+27 单测覆盖。
- **未验证 / 限制**：真实数据只有一个恒定队列值，P2/P1 升级未在真实环境触发（单测与编排测试覆盖）；Dashboard 服务为本地 JDK17 启动（harness 门禁是 JDK8 单测）。
- **阶段3 退出判定**：满足——规则契约先定并有 32 例规则测试；Java 快照端点 REPEATABLE READ/绕过缓存/BigDecimal/整体失败 + insp_read 资源映射已刷 Redis；Python 数据源/规则/编排与 V006 双后端契约一致；必测 9 类场景全部覆盖（含 PG 并发唯一约束、规则版本隔离）；真实 e2e 核对样本/基线/告警/trace 全过。F-015 保持 `in_progress/runtime_unverified`（LLM 摘要未做，阶段6）。
- **下一步**：阶段4 版本化 YAML + ADR-018 已完成（见上条）；接着进入阶段5 自动 resolved + 内部调度。改动均未 git add/commit。

### 追加：剩余实施路线图阶段2 最小前端 /inspection/alerts（2026-11-25，用户 m02548 指定、m02550 授权）

- **范围**：用户路线图阶段2——新增巡检 API 与单页（筛选/游标/30s 轮询按 alertId 去重/partial 横幅/详情抽屉/ack/claim/resolve/ignore 关闭必填 reason），挂 MENU-DAILY-CHECK-05，Vitest+生产构建，真实浏览器权限与全链路 e2e；不引入 SSE、不改问数交互。
- **已改**：`wms-frontend/src/apis/inspection/alerts.ts`（API 层+纯函数）、`src/apis/inspection/alerts.test.ts`（3 例）、`src/views/inspection/alerts/index.vue`（页面）；`wms-agent/app/scan/repository.py`（`_ALERT_LIST_COLUMNS` 23→27 列：补 resolved_at/resolved_reason/ignored_until/rule_version 并在 `_row_to_alert` 映射，MemoryScanStore 新建告警对关闭字段 setdefault None）；`wms-agent/app/scan/worker.py`（`acquire_service_token` 有限重试：SERVICE_TOKEN_ATTEMPTS=3，502/503/504 与传输错误重试，其它 4xx 直接抛出）；`wms-agent/tests/test_scan_round4.py`（+4 例服务令牌重试）、`tests/test_scan_round5.py`（+1 例关闭信息与 ruleVersion 契约）；`documents/02、项目需求/数据库/seed_menu_daily_check_05_inspection.sql`（新增，纯增量菜单种子）。
- **本轮发现并修复的真实缺陷**：①关闭原因/忽略截止/rule_version 从未被查询与映射，列表与详情把关闭信息全部丢弃（抽屉「规则」显示（-）、看不到解决原因）——已补列与映射并在双后端契约测试中断言；②partial 横幅用「列表里是否有 SCAN-PARTIAL 元告警」判定，元告警关闭前一直在导致干净扫描后误显示——改为独立取最新扫描自身 partial；③运行时父菜单 MENU-DAILY-CHECK 只绑 gly，菜单树按父构建导致 ckjl/cg 看不到子菜单 05——种子补父绑定；④worker 取服务令牌无重试，远端 Nacos gRPC 间歇 3s 超时使整次扫描 failed——加有限重试并区分确定性 4xx。
- **已验证**：Vitest 纯函数 4 files 15 tests passed；`vite build --mode production` BUILD_EXIT=0；全量 pytest 不带 PG **190 passed/26 skipped/1 warning**，带 PG 测试库 **213 passed/3 skipped/1 warning**（契约套件真跑 27 列 SELECT）。浏览器 e2e（agent-browser 0.43.0 + Chrome，dev server 3000，登录经 oauth token 写入 Redis `{user}:token` JSON 字符串后注入 localStorage）：admin(gly) 菜单可见、5 条数据、认领→解决成功；ckjl001(ckjl，新建测试账号) 菜单可见、认领成功、他人已认领告警仅显示详情；cw(新建 cwtest001) 菜单无每日检查/异常巡检、深链 0 行并提示无权、直连与经网关 API 均 code 9997；无 token 直连 HTTP 401。「扫描→告警→认领→关闭」：API 触发 scan-f67059e0c3b145de（succeeded、partial=False、findings=5）→ 浏览器轮询承接新告警 9 → admin 认领→确认→忽略（空 reason 被拦、填 reason 后 claim/ack/ignore 均 200、状态 已忽略），抽屉显示 规则 EXP-NEAR（v0.2.0）/确认人/解决原因/忽略截止 2026/12/2。菜单种子在真实 MySQL 幂等执行两轮一致；ckjl001 经网关 get-menus 含异常巡检。
- **未验证 / 限制**：页面无触发扫描按钮（用户路线图页面范围不含触发扫描，e2e 以 API 触发）；全量 `vitest run` 另有 5 个既有失败（daycheck/temperature、sysmanager/catagory、use-request/path 向 localhost:3000 发真实 XHR，baseline 环境依赖，与本轮无关）；vite-plugin-autogeneration-import-file 的 FSWatcher 在 HMR 文件变更时会崩溃（Node v24.21.0），需重启 dev server；本机 stockln(10610) 原未运行，已按 daycheck 同样方式启动后 expiry 源恢复 200。测试账号 ckjl001/cwtest001 为本轮新建的运行时数据。改动均未 git add/commit。
- **F-014**：浏览器证据（cg/gly/ckjl 可见可操作、KH/cw/cs 不可见）已在本次 e2e 覆盖；压测证据仍待并行补。
- **阶段2 退出判定**：满足——Vitest/生产构建通过；cg/gly 真实浏览器可见可操作；ckjl 测试用户已补并验证；KH/cw/cs 菜单与 API 均不可访问；「扫描→告警→认领→关闭」浏览器 e2e 通过。F-015 保持 in_progress/runtime_unverified（backlog 规则与 LLM 摘要未实现）。
- **下一步**：阶段3 backlog+一致快照（Dashboard GET /dashboard/query-pend-snapshot REPEATABLE READ 直读、新增 backlog 观测表迁移（V006 起，V005 已用于 actor_user_id）、receipt/to_up/pick 参与、前 3 次基线/第 4 次 P2/连续 3 次 P1）。

### 追加：剩余实施路线图阶段1 告警详情/认领/已读/真实 in_app（2026-11-25）

- 目标：按用户 m02548 路线图阶段1 实施——告警详情、认领、已读、真实 in_app 通知，并落盘 V004/V005 迁移与网关通知路由。
- ① 迁移：新增 `V004__alert_claim_read`（agent_alerts 增 acknowledged_by/acknowledged_at/assignee_user_id/claimed_at/routed_to；agent_notifications 增 recipient_user_id；索引 idx_agent_alerts_cursor、idx_agent_notifications_user）与 `V005__scan_actor_user_id`（agent_scan_runs 增 actor_user_id——异步执行时 worker 只有服务账号身份，发起用户稳定 user_id 必须落库才能按稳定 id 隔离已读）。真实 PG apply_migrations_sync 返回已应用版本 1..5，列与索引全部核对存在。
- ② 数据层（repository.py）：ScanStore Protocol 与 Memory/PG 双后端实现 claim_alert（FOR UPDATE + 他人已认领返回 None→409 + claimed 事件）、list_alerts_page（复合游标 `(last_seen_at, alert_id)` 严格小于，排序与 PG 一致）、get_alert_detail（evidence/ruleParams/events/触发 scan）、list_notifications、mark_notification_read；`_notification_rows` 带 recipientUserId，新增 `_notification_owned`（优先稳定 id、回退用户名）；`_ALERT_INSERT_SQL` 与活动态 UPDATE 补 routed_to。
- ③ 服务层（service.py）：通知 status 规则 dry_run→dry_run / in_app→sent / 其余→pending（in_app 在告警事务内写 sent 并由 PG 填 sent_at）；通知带 recipientUserId，告警带 routedTo；run 落 actorUserId。
- ④ 路由与权限（router.py / security.py）：新增 GET `/agent/alerts/page`（游标翻页）、GET `/agent/alerts/{id}`、POST `/agent/alerts/{id}/claim`、GET `/agent/notifications`、POST `/agent/notifications/{id}/read`；入口落库发起用户稳定 id（服务账号不落）；`_transition` 传 actor_user_id；新增 `can_view_notifications`（服务账号不可读）与 `notification_identity`。
- ⑤ 网关落盘：`wms-gateway/src/main/resources/application.yaml` inner-paths 追加 `/agent/notifications` 与 `/agent/notifications/**`。
- ⑥ 验证：新增 `tests/test_scan_round5.py` 13 例 + `tests/test_scan_store_contract.py` 5 个双后端契约用例；全量 pytest 不带 PG **185 passed / 26 skipped / 1 warning**，带独立 PG 测试库 `wms_agent_scan_test` **208 passed / 3 skipped / 1 warning**（契约单跑 38 passed）；`./init.sh --java-test`（harness JDK8 1.8.0_512）**HARNESS_EXIT=0**，daycheck 22 tests + wms-login 12 tests，BUILD SUCCESS。
- ⑦ 修 PG 详情缺陷：`_get_alert_detail_sync` 曾把列表第 6 列 dimension 当 evidence 返回且 evidence 不在列表列内，改为单独查 `evidence/rule_params` 后用 `_safe_json` 解析。
- 阶段1 退出判定：功能代码与自动化验证完成，F-015 仍 `in_progress/runtime_unverified`（backlog/LLM/前端未做）。下一步：阶段2 最小前端 `/inspection/alerts` + 浏览器权限测试。改动均未 git add/commit。

### 追加：剩余实施路线图阶段0 安全与真实运行门（2026-11-25，用户 m02548 指定、m02550 授权）

- 目标：按用户「异常巡检 Agent 剩余实施路线图」阶段 0–8 严格串行推进（阶段 9 才登记 v0.2.1），基线不重做队列/租约/fencing/幂等/三类规则/V001~V003。阶段0 聚焦安全与真实运行门。
- ① 种子改纯增量：`documents/02、项目需求/数据库/seed_daycheck_no_up_goods_page_role.sql` 重写为 DELIMITER// 存储过程，按 rolecode 动态取唯一 insp_read 角色 ID（0/>1 行 SIGNAL 中止）、ID/URL 冲突 SIGNAL 中止、移除全部 DELETE、不触碰 MENU-DAILY-CHECK-05；`NoUpPageResourceRoleSeedTest.java` 加 stripComments() 配合，JDK8 下 3 tests/0 failures BUILD SUCCESS。
- ② 真实 MySQL zo_wms 执行种子成功（幂等、二次执行结果一致），两端点均绑 insp_read、MENU-05 未变；evidence `.runtime_tmp/stage0_seed_result.json`。
- ③ Redis 刷新：网关 10001 `/open/resources/cache/reload` 404（未路由），改直连 oauth2 10400 PUT 成功（HTTP 200 code=10000）；AUTH:RESOURCE_ROLES 两 no-up 端点均为 `["insp_read"]`；evidence `.runtime_tmp/stage0_redis_result.json`。
- ④ 真实运行门：旧裸 List 端点 N/I/Y 三态齐全且无 rowId/noticeId；巡检分页端点 2001 行跨 21 页 fetched=2001/unique=2001/stable_order=true/max_latency=88ms 全覆盖；服务 JWT claims 收敛（agent_service/insp_read/agent-inspector/W01）；用户 JWT 不落库（wms_agent 全表无敏感列）；evidence `.runtime_tmp/stage0_security_result.json`、`stage0_pagination_2001_result.json`。
- 环境限制（如实记录）：网关 GET 端点无 token 仍 200（第三方 starter 全局放行，非新端点回归；POST /agent/scan 无 token 由 agent 侧自验 401），网关层 401/403 在本 harness 无法实测，鉴权按 ADR-007 由 agent 侧自验承接；当前 PG 为 postgres 超级用户，「Agent PG 账号只写 wms_agent」属部署配置约束需部署时建专用账号。
- 阶段0 退出判定：运行态门已用真实 MySQL/Redis/daycheck 复现通过；F-015 仍 `in_progress/runtime_unverified`（阶段1–8 未做）。下一步：阶段1 告警详情/认领/已读/真实 in_app（V004 迁移、claim 端点、游标分页、详情、通知已读、网关通知路由）。改动均未 git add/commit。

### 追加：F-015 第四轮签收补强（2026-11-25，用户 m01292 复跑复核后）

- 目标：用户复跑认定「主体修复完成但不能签收全部闭环」，指定 4 项必修 + 2 处 evidence 修正 + 3 项 e2e，全部完成。
- 必修① JDK8 兼容：`NoUpPageContractTest.java:71` `List.of`→`Arrays.asList`，`./init.sh --java-test` 用 harness PATH 的 JDK8 1.8.0_512 真跑 19 tests/0 failures、HARNESS_EXIT=0（直接取 harness 退出码，勿用 PowerShell Tee 管道，管道本身会返 exit 1）。
- 必修② 资源角色映射：新建 `documents/02、项目需求/数据库/seed_daycheck_no_up_goods_page_role.sql`（旧/新端点资源均绑 insp_read；不复用 MENU-DAILY-CHECK-05 以免破坏 ckjl/cg/gly 菜单授权），新增 `NoUpPageResourceRoleSeedTest.java` 3 例，init.sh 门禁 7→8 类，JDK8 下 8 类 22 tests BUILD SUCCESS。种子未在真实 MySQL 执行、网关 401/403/200 负例未跑 → runtime_unverified。
- 必修③ 分页重叠与元数据漂移：`app/scan/sources/base.py` fetch_paged 区分页内去重（page_seen，不算漂移）与跨页重复稳定键（page_drift→partial），并校验 total/pages 翻页期间不变（pagination_metadata_changed→partial）。初版顺序误伤 3 个页内去重测试，调整顺序后全绿。
- 必修④ 令牌 claim 强校验：新增 `WMS_AGENT_SERVICE_ACCOUNT_NAME`（默认 agent-inspector，对齐 Java agent.service.username），worker 新增 `validate_service_principal` 强制 token_use=agent_service / insp_read / 账号名匹配 / warehouse_scope 非空且含本次仓库；新增覆盖 5 种失败 claim 的测试。
- 必修⑤（用户第 3 项含此）告警重放幂等：观测键 `(scanId,traceId,fingerprint)`——MemoryScanStore 用 dict、PG 用 V003 迁移新表 agent_scan_observations（原子认领），命中返回 UPSERT_REPLAYED 不增 occurrence/不写事件/不通知；service 增 alertsReplayed 计数。
- 2 处 evidence 修正已并入 feature_list.json F-015 第四轮条目：①旧 JSON 表述（DTO @JsonInclude(NON_NULL) 保证旧响应不输出 null，但默认排序由无序改确定性 DESC+id，属兼容性行为扩展而非完全不变）；②NoUpMapperXmlTest:94 定性（XML 解析+MetaObject 赋值，非 JDBC ResultSet 逐行实映射测试）。
- 验证：全量 pytest（不带 PG）**167 passed / 21 skipped / 1 warning in 13.28s**；带独立 PG 测试库契约测试通过；Java `./init.sh --java-test` JDK8 下 PASS。
- 3 项真实 e2e 全 PASS：①真实用户 JWT 手动扫描（网关 POST /auth/oauth/token 取 admin JWT，agent 直接接受 Bearer，POST /agent/scan→立即 202 queued→轮询 succeeded，scan-ee077b4c1976449b）；②201 行运行态分页不截断（zo_wms.wm_in_qm_i 插 201 行测后清理，daycheck 10320 分页端点 total=201/pages=3、3 页 100/100/1、唯一 rowId 201/201 全覆盖）；③进程崩溃接管（真实 PG 插 lease 过期 running，recover_stale→queued、attempt 保留，测后清理）。evidence 留档 `.runtime_tmp/e2e_round4_result.json`、`e2e_round4_pagination_result.json`、`wms-agent/_e2e_recovery_result.json`。
- 状态：F-015 仍 `in_progress/runtime_unverified`，本轮认定「主体修复完成」，不升级 passing（backlog/LLM/in_app/告警详情/前端未做）。下一步按用户指定顺序：告警详情/已读与 in_app → 最小前端+浏览器权限测试 → backlog → LLM 摘要 → v0.2.1。改动均未 git add/commit。

### 追加：F-011 真实 LLM 浏览器 e2e 复跑（2026-11-23 晚）

- 目标：用户要求用**真实 LLM**（而非之前的 mock 场景）重跑 F-011 浏览器端到端。
- 前置确认：`wms-agent/.env` 为 `provider=openai` / OpenRouter `baidu/ernie-5.5-flash-preview:free`；env 写入 22:49:44、agent 22:50:07 启动，确认加载真实 LLM。直接 `POST /agent/query` 探针拿到 LLM 生成的 Markdown 答案（非 mock 固定文案），证明真实模型链路可用。
- 浏览器链路：vite 重启到 `127.0.0.1:3000`（原 5173 进程已退出）；Redis `admin:token` 真实 JWT 经 base64 注入 localStorage → `/home` 登录态生效（`current-user`/`get-menus` 200）→ 点『问数助手』→ 输入『查询 A01 库位的库存情况』→ 提问。
- 失败路径实测：首轮 OpenRouter 免费额度瞬时 429 → `POST /api/agent/query` 返回 `{code:9994,message:模型调用失败}`；页面未渲染答案区且保留输入，符合 F-011「失败显式提示且不清空输入」要求。
- 成功路径实测：重试后 HAR 捕获 `{code:10000,answer:**结论：A01 库位当前没有库存数据。**...,traceId:t-20261123232712-583fb2,persisted:false,toolCalls:[STOCK-QUERY/empty/0 行/36 ms]}`；截图与 DOM 均显示答案、工具调用溯源与 traceId。
- 未粉饰：`persisted=false`（本轮 memory backend）；首次 429 失败如实记录。
- 证据：`zero-one-10wms/.runtime_tmp/f011_real_llm_e2e/e2e_retry.har`（6KB）、`panel_real_llm.png`（109KB），gitignore 排除；已扫描确认无 LLM API key 明文泄漏（HAR 中仅含真实用户 JWT 于 Authorization 头，属预期）。

### 追加：F-011 浏览器端到端实测（解除 runtime_unverified，升级 e2e_pass）

- 目标：用户要求实测此前 4 项未验证内容中的「浏览器端到端链路断」。结论：**不需要 C++**（6 个工具全是 Java 端点），需要 Java 业务服务 + 网关 + Python Agent + 前端。
- 私钥结论纠正：私钥就在仓库 `wms-java/wms-oauth2/src/main/resources/jwt.jks` / `jwt.pfx`（密码 `123456`、alias `01star`），modulus 与 `wms-common/src/main/resources/public.pem` 一致；此前「无私钥」结论作废。
- Redis 登录态关键事实：`TokenExtendsValidateImpl.isLogout`（`wms-gateway/.../TokenExtendsValidateImpl.java:38`）用 JSON 反序列化读 `<user_name>:token`，值必须是 **JSON 字符串（带引号）**；裸 JWT → `SerializationException` 500，键不存在 → 401「用户凭证已注销」。真实 wms-login 登录写同格式。
- 启动实例（JDK17 + `--add-opens`）：wms-login 10200、wms-j3-daycheck 10320、wms-j6-stockln 10610、wms-oauth2 10400、wms-j1-dashboard 10010（Redisson 需 16 个 opens、oauth2 JAXB 需 6 个），网关 10001、wms-agent 11200（mock 场景）、vite 5173。
- 6 个 Java 工具端点经网关全部 200/code=10000 拿到真实数据（STOCK total=6、EXP total=6、DAYCHECK-DELAY total=3、DASH-TREND 真实列表等）；agent `/agent/query` STOCK-QUERY status=success rowCount=6。
- **浏览器 e2e 实测通过**：把 Redis `admin:token` 中的 wms-login 真实登录 token（700 字符、经 public.pem 验签通过、网关 `/login/current-user` 返回 code=10000）注入 localStorage → agent-browser 打开 `http://127.0.0.1:5173/home` → 点击「问数助手」→ 输入「查询 A01 库位的库存情况」→ 点击「提问」；HAR 捕获 `POST /api/agent/query` → HTTP 200 `{"code":10000,"message":"ok","data":{answer,sessionId,traceId,persisted:false,toolCalls:[STOCK-QUERY/success/rowCount=6/endpoint=/stock/inventory-query/query-all/resultDigest]}}`；页面实际渲染出「库存查询完成。」「工具调用（1）STOCK-QUERY 成功 6 行 62 ms」与 traceId。
- feature_list F-011 `runtime_unverified` → `e2e_pass`；未粉饰：`persisted=false`（本轮 agent 用 memory backend，PG 持久化已由 F-012 单独 e2e 证明）。
- 工具坑：PowerShell 5.1 向原生 exe 传参会吃内嵌双引号（写 Redis 值须用文件 `setfile`）；agent-browser console 会刷验证码 base64，改用 HAR 录制 + 定向过滤；harness 函数命名避开 `Get-History` 别名 `h`。

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
- 未验证（本轮已消除前 3 项，保留后 2 项）：
  - ~~前端浏览器端到端链路~~ **本轮已实测打通**（见上「追加：F-011 浏览器端到端实测」），原「无私钥/无 wms-login 实例」结论作废。
  - ~~真实用户 JWT 经网关 → Java 业务端点的完整链路~~ **本轮已实测**：wms-login 真实登录 token 经网关验签 + Redis 登出校验 → 6 个 Java 工具端点返回真实数据 → agent 拿到真实库存 rowCount=6。
  - 网关 `inner-paths` 与 `RESOURCE_ROLES_MAP` 的实际判定（判定在 starter jar 内，本环境 `open-authorization=false`，无法区分 white/inner 差异；Python 侧 401 已兜底）。
  - F-012 落库用的是本机原生 PostgreSQL 16.15，**未在虚拟机 pgvector 镜像上复验**。
  - ~~本轮浏览器 e2e 使用 `persisted=false`（memory backend），未与 PG 持久化同时打开；两条链路各自单独通过。~~ **2026-11-24 已消除**：补做三合一合并 e2e（真实 LLM + 浏览器 + PG 持久化同时打开），`persisted=true`，详见下方「追加：三合一合并 e2e」。
- 下一步：`F-002` 储位管理前端页面（`next_candidate`）；`F-004` 运行时基线仍 `blocked`。2026-11-24 已补齐问数 Agent 三合一合并 e2e 缺口（见下），AI-Agent 轨道剩余风险仅剩 VM pgvector 复验等非阻塞项。
- 用户待办（可选）：若要把 trace 落到虚拟机，`192.168.89.128` 用 `pgvector/pgvector:pg16` 起库（库名 `ragent`），连接串 `postgresql+psycopg://postgres:postgres@192.168.89.128:5432/ragent`；不拉也不阻塞，F-006~F-013 均已通过，缺失时按 `persisted=false` 降级。
- 已知风险：
  - **AgentScope 探针已通过**（`uv pip install --dry-run agentscope` → 97 包可解析、agentscope 2.0.12 兼容 Python 3.14.7，故 F-010 不记 blocked）；但 ReAct 循环按方案自研 `LLMProvider` + ToolSchema 契约实现，**未引入 AgentScope 依赖**（避免引入未被使用的 73 个传递依赖）——与 `feature_list.json` F-010 标题/notes 一致记录。
  - Gateway `inner-paths` 通配符行为在 starter jar 内，本环境因鉴权开关关闭未能区分 white/inner 差异；F-010 用 Python 侧 401 实测兜底。
  - JWT 签发私钥明文存在于仓库历史，是独立安全问题；后续需轮换密钥并清理历史。
  - Python 不查 Redis 注销黑名单；已登出 token 在 JWT 过期前直连 Python 仍是理论风险。
  - 本机 `postgres/123456` 是明文口令且本轮在库中建了 `ragent` 库，属测试环境痕迹，交付前宜改口令或清理该库。

## 最近会话（append-only）

### 2026-11-24 F-015 第四轮缺陷返修（评审不通过后只修缺陷，不扩功能）

- 目标：用户转交评审结论（“队列与权限闭环”不通过），要求修复全部缺陷并纠正 evidence；保留第三轮成果，状态仍 `in_progress`。
- Java no_up：`NoUpGoods` 补 `id/im_notice_id`（`@ExcelIgnore`）；`NoUpServiceImpl` 显式映射 `rowId/noticeId`（`BeanUtils` 不会按语义映射）；Mapper 拆两条语句——旧 `getNoUpGoodsPage` 恢复不过滤（旧页面 `received-unsold/index.vue` 的 `statusText` 按 N/I/Y 三态展示，给旧端点加过滤才是改契约），新 `getNoUpGoodsForInspection` 未上架口径 + 显式列（避免三表 `select *` 同名列歧义）+ 稳定排序；DTO 新字段 `@JsonInclude(NON_NULL)`，旧 JSON 不变。修复前实测：旧实例上新端点直连 10320 也是 404（运行中的 daycheck 早于第三轮代码）。
- 队列：领取写 `lease_owner/leased_at` 且 `attempt` 列 +1；执行回写按租约 fencing（`ScanLeaseLostError`）；非 fencing 写入不覆盖 `queued_at/attempt/lease_*`；`recover_stale` 读 `attempt` 列（不再从 counts 读、不再归零）且有界（3 次后 `failed(stale)`）；worker 心跳续租 + 周期恢复；`payload_hash/trace_id` 入队生成并沿用；`rule_version` 回写组合版本串；执行身份取自服务令牌 claims；服务 scanKey 含仓库、无槽位不去重；`get_run_by_scan_key` 活动态优先。
- 告警事务：`upsert_alert` 先 `FOR UPDATE` 锁最新行，告警 + 事件 + 通知同事务；升级按“更新前级别”判定；去重键 `alertId:event:severity:trace:recipient`；ignored 显式返回 `suppressed`；接收人 = 手动扫描发起人 / 定时扫描配置 `WMS_AGENT_ALERT_RECIPIENTS`（解析不出按 `notificationsUnrouted` 记账）；新增迁移 V002（事件类型 + 级别变化）。
- 权限：拆分 `inspection:alert:view` / `inspection:scan:trigger` / `inspection:alert:handle`；菜单业务角色 `cg/ckjl` 可看/发起/操作；服务账号只允许 trigger；告警列表与状态操作按令牌仓库范围过滤（越权 403）；首版强制单仓（多仓拒绝启动）；`ignoredUntil` 非法/无时区/过去时间统一 422。
- 其他：三个数据源共用 `fetch_paged`（total 缺失不再按 0 首页即完成；总数不一致/翻页漂移/缺 total 标 partial）；迁移 rollback 只允许已应用且最新版本、down 先备份再删列、apply 加 advisory lock；list 环境变量改逗号分隔可解析；`init.sh --java-test` 门禁扩到 7 个测试类并逐一确认执行。
- 验证：新增 `tests/test_scan_round4.py`、`tests/test_scan_store_contract.py`（Memory/PG 同一份契约，共 53 个用例）；全量 pytest 带测试库 `wms_agent_scan_test` → **184 passed, 3 skipped**，不带 PG → **166 passed, 21 skipped**；Java `./init.sh --java-test` → **31 tests BUILD SUCCESS**（新增 `NoUpMapperXmlTest` 6 例用真实 MyBatis 解析并逐行映射）；运行态 42 项检查全过（巡检分页端点直连/经网关返回探针行且 `rowId/noticeId` 正确；服务令牌定时 no_up 扫描 202 → worker 消费 succeeded，PG 行 attempt=1/租约释放/payload_hash/trace_id/rule_version/executor_id 正确；告警 trace_id、created 事件与通知同事务、`recipient=admin`、去重键含事件与级别；权限负例与跨仓 403；`ignoredUntil` 422）。
- 既有测试的契约变更（按新契约更新，非削弱）：权限拆分后只读码不能发起/操作；`upsert_alert` 返回 `AlertUpsertResult`；残留 running 先重入队而非直接 failed；no_up 去重用例 `total` 改为原始行数 3（原 2 与 3 行原始数据不一致）；trace 表断言由“恰好三表”改为“包含三表”（同 schema 已有巡检表）；`test_scan_round3.py` 跨仓用例的 `_service(("W01",))` 原本把仓库误传成权限，改为 `_service()`。
- 运行态操作留痕：daycheck 重新打包重启（首次打包因旧进程占用 jar 致 repackage 失败，服务中断约 4 分钟后恢复）；agent 重启加载新代码；PG 开发库 `ragent` 应用 V002（增量、幂等）；新建本机测试库 `wms_agent_scan_test`；临时探针（MySQL 1 条 `codex-noup-probe-*` 验收行、PG 探针告警与扫描记录）已清理；结果留档 `.runtime_tmp/round4_runtime_result.json`。
- 未验证/剩余风险：开发库 `wm_in_qm_i` 为空表 → 真实多页数据未在运行态复现（由 mock 单测覆盖）；真实进程崩溃下的租约接管未在运行态演练（由 PG 契约测试覆盖并发/行锁）；真实用户 JWT 的手动扫描未在网关复跑（本轮用服务令牌经网关 + 自签 JWT 直连）；服务令牌为 Redis 等值校验，worker 每次扫描取新令牌会使旧服务令牌失效。
- 状态：`feature_list.json` F-015 纠正第三轮 evidence 中“同事务”“旧端点不变”“_pg_e2e 5 项”三处不准确表述并追加第四轮 2 条；仍 `in_progress/runtime_unverified`。下一步按用户顺序：告警详情/已读与 in_app → 最小前端 + 浏览器权限测试 → backlog → LLM 摘要。

### 2026-11-24 F-015 第三轮「队列与权限闭环加固」（用户 m00644 指定，P0+P1）

- 目标：用户复跑 121 passed 但只读 PG 发现 `agent_scan_runs` 仅 17 列、新字段根本没落库，MemoryScanStore 全绿不能证明真实队列正确；指定本轮不加 backlog、不上前端，先做闭环加固，8 条退出条件全满足再进前端/in_app。
- P0 队列表结构与迁移：新建 `app/scan/migrations/{__init__,runner}.py` 版本化迁移机制（无第三方框架，`wms_agent.schema_migrations` 记版本，`apply_migrations_sync`/`apply_migrations`/`rollback_migration`），`V001__scan_queue_columns.up.sql`/`.down.sql` 可回滚；`repository.py` 用 28 列 `RUN_COLUMNS` 统一 INSERT/SELECT/ON CONFLICT UPDATE，真实 PG `agent_scan_runs` 经迁移 17→28 列（新增 `queued_at/warehouse/dry_run/notification_mode/payload_hash/trace_id/attempt/lease_owner/leased_at/executor_type/executor_id`），`agent_notifications.dedupe_key` 部分唯一索引。
- P0 异步凭证：`POST /agent/scan` 只 `insert_run` 立即返回 202 `queued`，不再同步消费；`worker.execute_queued_scan` 统一用 `insp_read` 服务账号取短时令牌，失败→`failed(auth_failed)` 不回退，用户 JWT 不落库；run 保留发起用户 `actor_type/actor_id` 与执行身份 `executor_type/executor_id`。
- P0 权限与状态机：`security.py` 收紧 `can_start_scan`/`can_view_alerts` 为管理员或 `SCAN_AUTHORITIES`，新增 `can_operate_alert` 禁服务账号 ack/resolve/ignore；`repository.py` 加 `ALLOWED_TRANSITIONS`（open→acknowledged/resolved/ignored、acknowledged→resolved/ignored），非法转移→409，resolve/ignore 缺 reason→422，跨仓 403。
- P0 no_up 全量分页：Java 子代理新增 `GET /daycheck/no-up/get-no-up-goods-page`（`JsonVO<PageDTO<NoUpGoodsDTO>>`，data.rows/total/pages，旧裸 List 端点契约不变；JDK17+Maven 3.6.3 实跑 10 tests BUILD SUCCESS）；Python `sources/no_up.py` 改新端点按 data.rows/total/pages 循环翻页，裸 List 标 partial；201 行跨 3 页全覆盖测试通过。
- P1 告警一致性：upsert ON CONFLICT 同步 `severity/evidence/dimension/title/suggested_actions/rule_degraded`，`ignored_until` 未过期抑制复发（内存/PG 两后端），通知 `dedupeKey=alertId:digest` 去重 + `recipient=scan-owner`，PG 故障仍 503 拒绝受理。
- 验证：新增 `tests/test_scan_round3.py` 8 例 + `test_scan_no_up_delay.py` 2 例；真实 PG `_pg_e2e.py` 5 项全过（入队读出一致、并发同 requestId 只一条、残留 running 恢复、dryRun 零告警零通知、不可达 DSN 拒绝）；全量 pytest → **131 passed, 3 skipped, 1 warning in 10.61s**；Java `mvn -o -pl wms-j3-daycheck -am test -DskipTests=false -DfailIfNoTests=false` → 10 tests BUILD SUCCESS（static_pass + 单测通过，e2e runtime_unverified）。
- 未验证/剩余风险：Java 仅模块单测（无真实网关+DB e2e）；`WMS_AGENT_TEST_DB_URL` 未设使 `test_storage_postgres.py` skip（预期）；F-015 仍 in_progress/runtime_unverified（backlog、LLM 摘要、in_app 真实通知、告警详情/已读、前端页面未做）；用户指定后续顺序：告警详情/已读与 in_app → 最小前端+浏览器权限测试 → backlog → LLM 摘要 → v0.2.1；F-014 菜单浏览器/压测证据并行补。
- 状态：`feature_list.json` F-015 evidence 追加 2 条、notes 更新第三轮成果；`PROGRESS.md` 记本轮。

### 2026-11-24 F-015 第二轮 no_up/delay 两类规则（用户指定第一轮后再做）

- 目标（用户 m00001 开发顺序）：第一轮 5 项测试通过后，第二轮开发 no_up/delay 两类规则与数据源，backlog 后置；F-014 菜单浏览器/压测证据并行补。
- 公共取数：`sources/base.py` 抽出 `get_with_retry`（5xx/超时重试 1 次、4xx 不重试）、`classify_error`、`SUCCESS_CODES`、`SourceResult.fail`；`sources/expiry.py` 改为复用公共逻辑，行为不变、第一轮测试仍全绿。
- no_up：新增 `sources/no_up.py`（GET `/daycheck/no-up/get-no-up-goods`、显式 `sort=oldest`、裸 List/PageDTO 兼容、`rowId` 组合键去重）与 `rules/no_up.py`（NOUP-OVERDUE：>8h→P0 / >4h→P1 / >2h→P2，`objectId=notice|goods|tin_id` 不含储位，建议 MOVE_TO_BIN/CONTACT_CUSTOMER，未来/解析失败跳过）。
- delay：新增 `sources/delay.py`（GET `/daycheck/delay/im-delay`、`sort=oldest`、PageDTO rows、`noticeId` 去重）与 `rules/delay.py`（DELAY-OVERDUE：>24h→P0 / >2h→P1 / 0~2h→P2，`objectId=noticeId`，司机姓名/电话/车号脱敏保留头尾，建议 CONTACT_CUSTOMER/NOTIFY_QC）。
- 编排：`service.py` 的 `SUPPORTED_TYPES` 扩为 `(expiry, no_up, delay)`，`DEFAULT_CONFIG` 增 `noUp={8,4,2}h` / `delay={24,2,0}h` / `sourceBudgetSeconds=30`，新增 `HANDLERS` 分派三类取数与规则参数，统一按 fingerprint 去重；backlog 仍记入 `counts.skippedTypes`。
- 验证：新增 `tests/test_scan_no_up_delay.py` 17 例（分级/边界、未来时间/解析失败跳过、脱敏、source 去重与 sort=oldest、5xx 重试 1 次成功、4xx 不重试标 partial、service 三类合并+backlog skipped、自定义阈值生效）；自纠 1 处测试期望（3h 前 no_up 默认落 P2，抬高 p2 阈值才不触发，非生产缺陷）；全量 pytest → **121 passed, 3 skipped, 1 warning in 9.18s**（原 104 passed + 新增 17）。
- 未验证/剩余风险：仍只做单元/契约级，未做真实运行态 PG 队列恢复证据；backlog 规则后置、LLM 摘要、真实 in_app 通知、前端页面未做；F-015 仍 in_progress/runtime_unverified，F-014 6 项证据并行补。
- 状态：`feature_list.json` F-015 evidence 追加 2 条、notes 更新第二轮成果；`PROGRESS.md` 记本轮。

### 2026-11-24 F-015 第一轮 5 项加固（用户指定开发顺序）

- 目标（用户 m00001）：第一轮只做 5 项——①统一 dryRun 与通知 dry-run 语义；②补角色、仓库范围和查询越权控制；③实现持久队列、worker 恢复和 PG 故障拒绝；④补幂等、原子 upsert、告警升级；⑤修分页完整性并落盘网关路径。测试通过后再做 no_up/delay，backlog 后置；F-014 菜单浏览器/压测证据并行补，不需等待。
- ①语义：`service.py` 明确请求级 `dryRun=true`（只算 findings 写 scan_runs，不落告警不通知）与服务端 `notification_mode=dry_run`（仅通知策略，告警照常落库、只写 status=dry_run 通知记录）互不短路，`schemas.py` 更新 dryRun 文案；原 3 例旧语义断言测试已改为正确契约并新增 `test_request_dry_run_skips_alerts_and_notifications`。
- ②角色/越权：`security.py` 新增 `ADMIN_AUTHORITIES={gly,ROLE_ADMIN,admin}`、`SCAN_AUTHORITIES`、`has_authority/is_scan_admin/can_start_scan/can_view_scan/can_view_alerts`，服务扫描仅管理员可见、用户只看 actorId；router 入队前 `check_warehouse_scope` 越权拒绝；GET scans 越权返回 9997。
- ③持久队列/恢复/PG 故障拒绝：`repository.py` 新增 `ScanStoreUnavailableError`（PG 故障不降级内存）、`FOR UPDATE SKIP LOCKED` 领队列、部分唯一索引 uq_scan_runs_active_key、`build_scan_store` 未知后端/无 db_url 拒绝；`worker.py` 启动 `recover_stale` 残留 running→failed(stale)、后台轮询消费、服务令牌失败→failed(auth_failed) 不回退；`main.py` lifespan 巡检 store 故障拒绝启动。
- ④幂等/upsert/升级：`repository.py` 加 requestId 与 scheduleSlot+configHash+scanTypes 唯一索引，insert_run 冲突抛 `ScanStoreConflictError`→幂等命中返回既有扫描；`upsert_alert` 返回 (alertId, created, first_severity) 原子判定升级（`SEVERITY_RANK={P0:3,P1:2,P2:1}`），只在 created/escalated 通知；router 新增 `POST /agent/alerts/{id}/{ack,resolve,ignore}`（终态后 409、ignore 默认 7 天）。
- ⑤分页/网关：`sources/expiry.py` 5xx/超时重试 1 次（4xx 不重试）、单源预算 30s、按 id 去重、任一页失败标 partial + `SCAN-PARTIAL` P2 元告警；`wms-java/wms-gateway/.../application.yaml` inner-paths 补 `/agent/scan`、`/agent/scans/**`、`/agent/alerts`、`/agent/alerts/**`（真实 Nacos 需纯 ASCII，中文注释不可直接拷贝）。
- 修复缺陷：router 同步消费路径原直接调 `get_client(request)` 绕过可覆盖依赖，导致 E2E mock 网关失效只产生 1 条 partial 告警；改为注入 `client: GatewayClient = Depends(get_client)` 后 E2E 恢复 2 条告警。
- 验证：venv `.venv/Scripts/python.exe` 跑 `pytest` → **104 passed, 3 skipped, 1 warning in 9.23s**（原 92 passed + 新增 `tests/test_scan_round1.py` 16 例 + 原用例语义修正 1 例）。新增用例覆盖幂等键/冲突查找、upsert 三元组、状态机与 409、角色/越权、查询他人扫描 403、worker 残留恢复、PG 故障拒绝、5xx 重试成功/4xx 不重试。
- 未验证/剩余风险：第一轮只做单元/契约级（无真实 PG 队列恢复运行态证据）；F-015 仍 in_progress/runtime_unverified，no_up/delay/backlog、LLM 摘要、真实 in_app 通知、前端页面未做（用户指定后置）；F-014 6 项证据并行补。升级 passing 前需补真实队列恢复运行态证据。
- 状态：`feature_list.json` F-015 evidence 追加 2 条、notes 更新第一轮成果；`PROGRESS.md` 记本轮。

### 2026-11-24 F-015 效期规则纵向切片跑通真实链路

- 目标：用户确认启动 F-015，先做效期单类纵向切片，不把 no_up/delay/backlog 与 v0.2.1 混进来。
- 代码：新增 `wms-agent/app/scan/`（schemas / repository 四表 / service 编排 / router 三个端点 / rules 与 sources 的 expiry 实现），`app/main.py` 挂载 scan router 与 scan_store；规则确定性、LLM 不参与级别、dry_run 只落通知不发送。
- 自动化：`tests/test_scan_expiry.py` 15 例全通过（分级/降级/数据质量跳过、指纹分离、分页去重、partial、manual/schedule trigger、越权 failed、重复扫描只更新、router 端到端与缺 JWT 401）；全量 `uv run pytest` → 92 passed, 3 skipped。
- 真实运行态：重启 wms-agent 加载新代码，service token 经网关 `POST /agent/scan` → 202 `scanId=scan-3d2d32c67e2442dc`；`GET /agent/scans/{id}` → succeeded / schedule / service / partial=false / sourceStatus=expiry rows=6 / findings=5 / alertsCreated=5 / notifications=5；`GET /agent/alerts` → 5 条（2×EXP-EXPIRED/P0、3×EXP-NEAR/P1）。
- PG 核对（`psql -d ragent`）：`wms_agent.agent_scan_runs`=1、`agent_alerts`=5、`agent_notifications`=5（in_app/dry_run）、`agent_alert_events`=0（本切片无状态转移）。
- 状态：`feature_list.json` F-015 `not_started` → `in_progress/runtime_unverified`，evidence 记入本轮 4 条；F-014 因用户确认启动 F-015，按 single_in_progress 由 `in_progress` 转 `blocked`（保留证据、待补项可并行），`next_candidate`=F-015。
- 未做：no_up/delay/backlog 三类规则、告警状态机（ack/resolve/ignore 与 409）、LLM 摘要与真实 in_app 通知、前端 `/inspection/alerts` 页面；这些完成前 F-015 不能记 passing。

### 2026-11-24 F-014 前置项收口复验与状态纠偏

- 目标：按门槛补齐 F-014 运行态证据并纠正过宽状态，不继承「F-014 passing/e2e_pass、F-015 in_progress」的旧结论。
- 自动化复跑（本轮亲自执行）：Git Bash `./init.sh --java-test` → BUILD SUCCESS，Surefire 实测 `AgentServiceTokenTest` 12/12、`DaycheckSortContractTest` 3/3、`DelayServiceSortTest` 2/2、`DelayControllerSortTest` 1/1（18 例 0 失败），「0 tests 也算通过」保护通过；`wms-agent uv run pytest` → 77 passed, 3 skipped。
- service-token 经网关运行态（本轮实测）：`POST /login/service-token`（API Key + k1 + W01）→ `code=10000`、`expiresIn=1800`、`roles=[insp_read]`、`warehouseScope=[W01]`；JWT 解码 `exp-iat=1800`、`token_use=agent_service`、`warehouse_scope=[W01]`；Redis `agent-inspector:token` TTL=1800 且 JSON 反序列化后值与返回 token 一致；token 未入日志；无/错 Key→401、W02→403。
- 角色映射决策（用户确认）：`MENU-DAILY-CHECK-05` 授予 `ckjl/cg/gly`，`KH/cw/cs` 不可见；DB 实测映射一致，`agent-inspector` 仅绑定 `insp_read`；ckjl 当前 0 用户。
- 只读端点复验（本轮实测）：新 service token 经网关调用 no-up/delay/expiry/yichang/temperature + dashboard 4 计数，全部 `code=10000`；delay 无 sort 为 11-20→11-19→11-18，`sort=oldest` 为 11-18→11-19→11-20，`sort=invalid`→9995。
- 状态纠偏：`feature_list.json` F-014 `passing/e2e_pass` → `in_progress/runtime_unverified`（已完成证据与待补证据分开）；F-015 `in_progress` → `not_started`；`next_candidate` 改 F-014。校验 15 条 feature、唯一 in_progress=F-014。
- 待补证据（影响 F-015 验收）：菜单浏览器可见性、未上架真实数据 `bin_sta='N'` 过滤（当前 0 行）、201/2001 分页边界、未上架真实排序、性能压测、conda 根解释器包漂移清理。
- flaky 测试 `tests/test_query_replay.py::test_scenarios_are_deterministic`（determinism 断言排除 `durationMs`，`durationMs>=0` 仍在第 123 行断言）**待用户确认**后单独提交，不并入 F-014/F-015。

### 2026-11-24 异常巡检 v0.2 前置项实测与落地

- 目标：按用户授权完成 service-token、`insp_read` 角色、`sort=oldest`、菜单/资源映射、索引和网关链路测试。
- 结果：
  - `POST /login/service-token` 经网关 200：`expiresIn=1800`、`roles=[insp_read]`、`warehouseScope=[W01]`；服务账号 `agent-inspector` 已创建并绑定 `insp_read`。
  - 服务账号 JWT 调用 no-up、delay、expiry、dashboard 4 个计数端点均 200；`sort=oldest` 已生效（delay 按 `im_data` 升序）；无 sort 保持新→旧；非法 sort 返回 9995。
  - `MENU-DAILY-CHECK-05` 已创建并挂到 `MENU-DAILY-CHECK`；映射 `ckjl/cg/gly`；`ckjl` 当前 0 用户，实际可见主要来自 `cg/gly`。
  - 已创建 `idx_wm_in_qm_i_create_date`、`idx_wm_im_notice_h_im_data`、`idx_wm_to_down_goods_create_date`。
  - 鉴权负例：无/错 API Key → 401；越权仓库 → 403。
  - Maven：`wms-login`、`wms-oauth2`、`wms-j3-daycheck` 打包成功；服务已重启。
- 登记：`F-014` 前置项 `passing/e2e_pass`；`F-015` v0.2.0 实现 `in_progress`（代码尚未开始）；传统队列 F-002/F-003/F-004 后移为 13/14/15。
- 端到端复验（harness 环境）：service-token `expiresIn=1800` `roles=[insp_read]` `warehouseScope=[W01]`；`POST /agent/query` → `code=10000`、`persisted=true`、`traceId=t-20261124155015-7eb501`，真实 LLM 给出具体答案（含 A01 库位为 0 条记录、建议用实际储位编码），toolCalls=[STOCK-QUERY/empty/0 行]。
- 环境事实（重要）：**Codex 执行沙箱会阻断 Windows 原生扩展 DLL 加载**（`python314.dll` / `_ctypes.pyd` / `cryptography._rust.pyd` → 退出码 `0xC0000142`），因此沙箱内 `uv run pytest` 必然假失败；`wms-agent/.venv` 必须按 README 用 `uv sync --python /d/DownloadPackage/environment/python.exe` 从 conda 3.14.7 基座重建，**验证必须在 harness 环境（提权执行 = 用户终端）下跑**，不要为了迁就沙箱去改 pyproject / init.sh / .gitignore。
- 顺带修复：`tests/test_query_replay.py::test_scenarios_are_deterministic` 原先把 `durationMs` 也纳入两次回放比较，存在 1ms 抖动导致随机失败；现只比对确定性字段（排除 `durationMs`），`./init.sh --agent` → **69 passed / 3 skipped / PASS**。
- 运行态：wms-agent 已换回 harness 的 `.venv\Scripts\uvicorn.exe`（pid 22024，11200），直连与经网关 `/agent/health` 均 200。
- 待办：开始 F-015 的 `app/scan/`、四张表、`/agent/scan`、状态机、in_app dry-run 与前端最小页面；v0.2.1 另开条目。

### 2026-11-24 启动网关并实测异常巡检前置验证门 #3 / #6

- 目标：用户要求启动「无法实测」项所缺的服务（核心是网关 10001），把验证门 #3（网关 Redis 校验语义）与 #6（网关 IP 白名单实际地址）从「运行时缺服务」变为有运行态证据。
- 前置实测：VM `192.168.89.128` 的 Nacos 8848 / Redis 6379 / MySQL 3306 均可达；Java 业务服务 10010/10200/10320/10400/10610、wms-agent 11200、本机 PG 5432 均在运行；**唯独网关 10001 未监听**，即此前阻塞根因。
- 操作：以 JDK17 + 16 个 `--add-opens`（Redisson）启动 `wms-gateway-1.0.0-SNAPSHOT.jar`（日志 `.runtime_tmp/gateway.log`，gitignore 排除）。启动日志：`Netty started on port(s): 10001`、`nacos registry, DEFAULT_GROUP GATEWAY 192.168.101.91:10001 register finished`、`Started GatewayApplication in 16.072 seconds`。
- 验证门 #6（网关 IP 白名单实际地址）：**192.168.101.91**（网关注册到 Nacos 的本机 IP，端口 10001），即阶段 A `POST /login/service-token` 的 IP 白名单应放行地址；此前因网关未起无法取。
- 验证门 #3（Redis 校验语义）端到端实测：`TokenExtendsValidateImpl.java:38` 为 `Objects.equals(redisValue, token)`（Jackson 反序列化回明文 JWT，确为等值校验）。用 Redis `admin:token`（VM 6379，密码见 nacos-config/key-config.yaml，JSON 字符串去引号后 700 字符裸 JWT）经网关 `GET /login/current-user`：

  1. 真实 token → HTTP 200 `code=10000`（username=admin，roles=[gly]）；
  2. 临时把 Redis 值改为 `jwt+'X'`，原 token 再请求 → HTTP 200 `code=401 用户凭证已注销`（证明等值校验：新 token 覆盖会把旧 token 踢下线，支撑方案中「全局串行或按仓拆账号」结论）；
  3. `finally` 恢复原值后再次请求 → `code=10000`，且断言 Redis 值与原值完全一致（`restored_ok=True`），未破坏现有登录态。
- 边界（非启动服务可解，本轮未做）：`INSPECTION_READ` 角色注册（验证门 #4/#7）是 DB 资源/角色映射改造，属阶段 A Java 前置，不是服务；真实短信（#8）有外部费用副作用，仅能影子运行；温度地点词表（#10）是业务决策，需业务提供 `wenduDd` 受控词表与 aliases。
- 状态：仅补运行态证据，未改业务代码、未注册新功能条目、未提交；`feature_list.json` 不变。网关进程留在 10001 运行（pid 78544）。

### 2026-11-24 异常巡检 Agent v0.2 设计完成

- 目标：基于《异常巡检agent业务背景.md》完成 v0.2.0/v0.2.1 设计，不写业务代码。
- 决策：复用 `wms-agent` 进程新增 `app/scan/`；v0.2.0 四类（效期、收货未上架、进货延时、待办积压），v0.2.1 两类（出货异常、温度）；规则确定性判定，LLM 只摘要；手动 + 内部定时；Java 侧 `service-token` + `INSPECTION_READ`；告警四态；Agent 自有 `in_app`；四张表；版本化 YAML；Java 前置项单列。
- 结果：新增 `wms-agent/docs/implement/异常巡检Agent实施方案.md`；未改代码、未改 feature 状态；`./init.sh --quick --snapshot` PASS。
- 2026-11-24 追加实测：网关 `10001` 已启动并注册 `192.168.101.91:10001`；`/agent/health` 200，`/agent/tools` 无 token 401、带现有 admin token 200，`/agent/trace/not-exist` 200/code=9999；经网关验证 `pageSize=100` 对 delay/no-up/yichang/temperature/expiry 均 200；`sort=oldest` 直连与经网关均被忽略，delay 顺序为新→旧；`wm_in_qm_i` 无 `create_date` 索引、`wm_im_notice_h` 无 `im_data` 索引；`admin:token` Redis 值为带引号 JSON 字符串，网关接受；`MENU-DAILY-CHECK` 及子资源 `01~04` 已查到；`INSPECTION_READ` 角色未注册；`POST /agent/scan` 与 `/login/service-token` 当前 404；短信 Controller 固定模板/签名且只传 `message`。
- 待办：实施前补齐未验证项（网关 IP、服务账号端点权限、短信平台变量、温度词表），登记 v0.2.0/v0.2.1 功能条目，再按阶段 A 开始 Java 前置改造。

### 2026-11-24 问数 Agent 三合一合并 e2e（真实 LLM + 浏览器 + PG 持久化同时打开）

- 用户诉求（m00001/m00031）：此前浏览器 e2e 用 `persisted=false`（memory backend），PG 持久化由 F-012 单独 e2e 证明，两条链路仍未同时打开；用户确认「可以，你测试下端到端的验证」。目标是把真实 LLM、浏览器 e2e、PG 持久化放到同一次运行中验证，补齐唯一残留缺口后回填 `feature_list.json` 与 `PROGRESS.md`。
- 环境前置：wms-agent `.env` 为 `provider=openai` / OpenRouter `baidu/ernie-5.5-flash-preview:free`（真实 LLM）；通过 cmd 包装脚本 `zero-one-10wms/.runtime_tmp/start_agent_pg.cmd` 以 `WMS_AGENT_STORE_BACKEND=postgres` + `WMS_AGENT_DB_URL=postgresql://postgres:123456@127.0.0.1:5432/ragent` 重启 agent（pid 27272，日志 `agent_pg_combined.log`），即**同一进程同时开真实 LLM + PG 持久化**。JWT 取自 Redis `admin:token`（VM 192.168.89.128:6379，密码 `01star`），值须 `json.loads` 去外层引号得 700 字符裸 JWT（https:// 前缀无关），经网关 `/login/current-user` 验签通过。
- 直连探针：`POST http://127.0.0.1:11200/agent/query`（真实 JWT，body `{"query":"查询 A01 库位的库存情况"}`）→ HTTP 200 `code=10000`、**`persisted=true`**、`traceId=t-20261124092640-e16eb8`、真实 LLM Markdown 答案「结论：A01 库位当前没有库存数据」、`toolCalls=[STOCK-QUERY/empty/0 行/46 ms]`。
- 浏览器 e2e：Redis 真实 JWT 经 base64 注入 localStorage（`tokenLen=700`）→ `http://127.0.0.1:3000/home` 登录态生效（vite 代理 `/api`→网关 10001）→ 点『问数助手』→ 输入『查询 A01 库位的库存情况』→ 点『提问』。HAR（`zero-one-10wms/.runtime_tmp/f012_combined_e2e/combined.har`，gitignore 排除）捕获 `POST http://127.0.0.1:3000/api/agent/query`（Authorization: Bearer <真实 JWT>）→ HTTP 200 `{code:10000, data:{answer:**结论：A01 库位当前没有库存数据。** + 可能原因, sessionId:s-20261124092842-f68ae5, traceId:t-20261124092842-32b880, persisted:true, toolCalls:[STOCK-QUERY/status=empty/rowCount=0/durationMs=49/endpoint=/stock/inventory-query/query-all/resultDigest=sha256:4f53cda18c2baa0c]}}`；DOM 面板显示答案、『工具调用（1）STOCK-QUERY 无数据 0 行 49 ms』与『traceId t-20261124092842-32b880 · 已持久化』。
- 回读与落库：`GET http://127.0.0.1:10001/agent/trace/t-20261124092842-32b880`（经网关、真实 JWT）→ `code=10000`、status=ok、userName=admin、toolRounds=1、答案一致；`psql -d ragent` 核对三表均新增 1 行：`agent_traces`(`t-20261124092842-32b880`,admin,ok,1,3317ms)、`agent_tool_calls`(seq=0,STOCK-QUERY,empty,row_count=0,49ms,endpoint,sha256:4f53cda18c2baa0c)、`agent_sessions`(`s-20261124092842-f68ae5`,admin,user_id=2c9221a4717bb44c01717d01c6ff0540)。测试前基线各 1 行（tester），测试后 traces=3 行（含直连探针 1 行）。
- 结论：**两条链路已同时打开**，唯一残留缺口消除；`feature_list.json` F-011/F-012 evidence 已追加合并 e2e 条目，`updated_at` 改为 2026-11-24；F-011/F-012 仍为 `passing`+`e2e_pass`，F-006~F-013 状态不变。
- 未粉饰/剩余风险：PG 仍为本机原生 PostgreSQL 16.15（非 VM pgvector 镜像）；JWT 私钥明文、Redis 注销黑名单、网关 inner-paths 判定等既有风险不变；测试痕迹（库 `ragent` 与明文口令 `postgres/123456`）交付前宜清理。

### 2026-11-23 问数助手「库存查询完成。」答非所问修复（方案 A：真实 LLM）

- 用户反馈：问数助手不管问什么都只回「库存查询完成。」，是否符合实施文档？结论：**不完全符合**。该句是 mock 回放 fixture（`tests/fixtures/llm/query_single_tool.json:12`）的占位文案；实施方案虽在 §8.2 规定「只断言工具调用序列、不逐字断言文案」（测试层允许占位），但产品层要求具体回答（方案 :220 样例「当前待上架 128 件。」）。
- 根因：运行配置 `WMS_AGENT_LLM_PROVIDER=mock`，`MockProvider.complete()`（app/llm/mock.py:65-86）忽略 messages/tools 只按序吐 fixture 文本；真实作答链路（app/llm/openai_compatible.py + app/agent/react.py:40-50 工具结果回喂）代码早已存在但未启用。
- 处置（用户选方案 A）：把真实 LLM key 只写入本地 `wms-agent/.env`（根 .gitignore:32-34 排除，未提交），设 `WMS_AGENT_LLM_PROVIDER=openai` + base_url + model + timeout，重启 11200 的 wms-agent。
- 实测（合法 JWT 取自 Redis `admin:token`，经 public.pem RS256 验签有效至 2026-11-24）：三问三答全部 `code=10000`、答案各异且基于工具真实数据——①按仓库统计库存→共 540 件/成品库 6 行明细（STOCK-QUERY/success/6）；②临期批次→6 行效期表含已过期 -180/-27 天与 3 天临期（EXP-WARN-QUERY/success/6）；③A01 库位→0 件（STOCK-QUERY/empty/0）。彻底告别固定占位文案。
- 模型供应商：先用 Agnes（agnes-3.0-flash）验证真实调用成功，但该账号 chat/completions 有 429 RPM 限流（密集提问偶发 code=9994，provider 如实报错非缺陷）；按用户要求换 OpenRouter（`baidu/ernie-5.5-flash-preview:free`），重跑三问全部成功无 429。最终生效配置即 OpenRouter，key 仍未入库。
- 风险：Agnes key 与 OpenRouter key 均为用户直接提供的明文，已在本会话出现且曾落本地 .env；建议视为已泄露并择机轮换。feature_list F-008 证据已回填；F-006~F-013 状态不变。

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
