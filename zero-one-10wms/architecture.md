# 架构与工程约束

> 本文件是架构事实源。实现细节以代码和配置为准；发现文档与代码冲突时，先验证代码，再更新本文件。

## 1. 系统目标与核心路径

WMS 覆盖仓库履约全流程：

登录/权限 → 基础资料 → 入库/上架 → 库存与库内作业 → 出库 → 盘点/计费/报表。

关键质量属性：库存数据一致性、接口幂等与可追溯、权限边界、批量操作性能、导入导出稳定性。

## 2. 运行拓扑

```text
Browser (Vue3)
  → Vite dev server / 静态资源
  → wms-gateway (Spring Cloud Gateway)
      → Java 业务服务 (lb://...)
      → C++ 业务服务 (http://127.0.0.1:81xx)
  → Nacos（注册/配置）
  → MySQL / Redis / RocketMQ / FastDFS / ES / MongoDB
```

- 前端只通过 `src/apis/` 访问后端；页面不直接拼接后端地址。
- 网关负责路径路由与鉴权入口；业务服务不假设外部调用方绕过网关。
- C++ 服务端口以 `wms-java/wms-gateway/src/main/resources/application.yaml` 和各模块配置为准。

## 3. 仓库与模块地图

### Java（`wms-java/`）

| 模块 | 职责 |
|---|---|
| `wms-common` | 公共工具、异常、返回结构 |
| `wms-domain` | 领域模型、DTO/VO、Mapper |
| `wms-apis` | 服务间 API/Feign 契约 |
| `wms-gateway` | 网关路由、鉴权入口 |
| `wms-oauth2` / `wms-login` | 认证、登录、验证码 |
| `wms-j1-*` ~ `wms-j8-*` | 按业务域拆分的微服务（看板、系统管理、消息、日结、基础资料、入库、出库、其他配置/导出等） |
| `wms-doc` | 接口文档/聚合 |

模块清单以 `wms-java/pom.xml` 的 `<modules>` 为准。

### C++（`wms-cpp/`）

| 模块 | 职责 |
|---|---|
| `lib-common` / `lib-oatpp` / `lib-mysql` / `lib-dy` | 公共库、Web 组件、MySQL 组件、动态库 |
| `wms-c1-bconf` / `wms-c1-persalloc` | 基础配置、人员分配 |
| `wms-c2-comconfig` | 企业配置 |
| `wms-c3-chuweiguanli` / `wms-c3-kuneiguanli` | 储位/出库相关、库内管理 |
| `wms-c4-icmanagement` / `wms-c4-billingconfig` / `wms-c4-billingtype` | 盘点、计费配置、费用类型 |
| `wms-c5-costconfig` / `wms-c5-costmanagement` / `wms-c5-warningmanagement` | 费用配置、费用管理、预警 |
| `wms-c6-areaconf` / `wms-c6-staffconf` | 地区配置、人员配置 |
| `wms-c7-reposity` / `wms-c8-platmanag` / `wms-c8-wconfig` | 仓储/平台/仓库配置 |
| `arch-tests` | 架构与静态测试 |

模块清单以 `wms-cpp/CMakeLists.txt` 的 `add_subdirectory` 为准。

### 前端（`wms-frontend/`）

| 路径 | 职责 |
|---|---|
| `src/apis/` | 所有 HTTP 封装；按业务域分目录 |
| `src/views/` | 页面；文件路由 + `definePage` 菜单 |
| `src/views/ware-config/composables/use-dict-page.ts` | 字典页工厂 |
| `src/views/ware-config/components/DictPage.vue` | 字典页通用组件 |
| `src/composables/` | 权限、分页、通用逻辑 |
| `src/router/` / `types/typed-router.d.ts` | 自动路由与类型 |

## 4. 请求与数据契约

- Java 成功码：`10000`；C++ `JsonVO` 成功码：`0`；文件导出兼容 `201`。
- 分页返回：`pageIndex / pageSize / total / pages / rows`。
- 前端分页封装：`cleanParams` 去掉空值；`requestList` 统一成功/失败回调；导出用 `requestBlob` + `saveBlob`。
- 跨服务调用优先走 `wms-apis` 契约或网关；不直接跨库写其他服务的数据表。
- 数据库脚本：`documents/02、项目需求/数据库/`（`zowms.sql`、`zowms_init_sys.sql`、`migrate_*.sql`）。
- 迁移脚本必须可回滚；破坏性变更先备份并在报告中记录。

## 5. 工程硬约定（已验证，违反即缺陷）

1. **编码与行尾**：C++ c7/c8 模块 UTF-8 与 GB18030 混存、行尾多为 CRLF；改文件前逐文件探测并原样保持。辅助脚本：`.dsh-scratch/enc.py`、`patchlib.py`。
2. **oatpp 主键**：`executeInsert` 返回 `LAST_INSERT_ID()`，对 varchar UUID 主键表无意义；判断插入成功用 `executeUpdate`（受影响行数）。
3. **路由**：PATH 必须以 `/` 开头（oatpp `info->path = PATH` 原样使用）；同路径不同 HTTP 方法合法，端点唯一性按「方法+路径」校验。
4. **SQL**：批量删除一律 `SQLPARAMS_PUSH` 参数化（IN 占位符逐个 push），禁止字符串拼接。
5. **YAML**：`zh-dict.yaml` 同名顶层键会被 yaml-cpp 后者覆盖；新增词条前先查重复键。
6. **前端字典页**：统一走 `views/ware-config/composables/use-dict-page.ts` + `views/ware-config/components/DictPage.vue` 工厂；接口集中在 `apis/ware-config/index.js`；导出兼容 201 状态码（`requestBlob`）。
7. **DTO 默认值**：动态更新场景用 `API_DTO_FIELD_DEFAULT`，避免未传字段被默认值覆盖；`API_DTO_FIELD` 第 5 参数是真默认值。
8. **C++ 无本地编译**：用 Python 静态校验（类声明/定义、宏映射、SQL 三一致、include 解析、端点唯一性、词条存在性），结果记 `static_pass + runtime_unverified`。

## 6. 验证架构

| 层 | Java | 前端 | C++ |
|---|---|---|---|
| 静态 | `mvn -o ... compile` | `corepack pnpm build` | `.dsh-scratch/` 静态脚本 |
| 行为 | 单测/接口测试 | 页面交互冒烟 | CI/Linux 启动 + 接口 |
| 系统 | 网关 + 服务 + DB 端到端 | 浏览器端到端 | Linux 编译 + 服务 + DB |

- 配置 CRUD 可止步静态；资金、库存过账、PLC、权限必须有系统层证据。
- 证据写入 `feature_list.json` 的 `evidence`，并在 `PROGRESS.md` 留摘要。

## 7. 可观测性与故障定位

- Java：日志 + Actuator；网关日志用于定位路由/鉴权问题。
- C++：服务日志 + 请求/响应；端点注册看 `ENDPOINT` 宏与 Router。
- 前端：浏览器 Network/Console；导出问题先看响应状态码与 blob 大小。
- 审计链：Git 基线、关键文件哈希、提交记录；见 `process.md`。

## 8. 关键决策（ADR-lite）

| 日期 | 决策 | 原因 | 状态 |
|---|---|---|---|
| 2026-11-22 | C++ 本机不编译，静态校验 + `runtime_unverified` | 无 MSVC/cmake 环境 | 生效 |
| 2026-11-23 | 引入 `feature_list.json` / `PROGRESS.md` / `init.sh` | 跨会话状态与完成证据 | 生效 |
| 2026-11-23 | 父/子模块分开提交，父仓库只更新 gitlink | 保持子模块历史独立 | 生效 |

## 9. 文档索引

- 编码规范：`documents/03、编码规范/`
- 数据库与需求：`documents/02、项目需求/`
- 环境搭建：`documents/05、环境搭建/`
- 版本计划：`documents/01、项目计划/版本计划.emmx`
- 流程与 Git 守卫：`process.md`
