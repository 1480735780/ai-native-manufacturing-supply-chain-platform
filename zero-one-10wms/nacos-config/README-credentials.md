# Nacos 共享配置的凭据注入与生产上线准备

## 0. 当前边界（用户明确要求）

- **dev 当前不安排运维窗口**：不发布 Nacos、不重启服务、不生成或轮换凭据，不修改 DB / Redis / Mongo / JKS 口令。
- 本轮只做**生产上线准备**：环境变量模板、脱敏校验、Nacos 只读巡检脚本与上线/回滚文档；本地测试只使用假值和空值。
- **prod 必须使用独立环境和新凭据初始化**：独立 Nacos namespace/group、独立服务地址与账号、独立 API Key、独立 FastDFS secret、独立 JKS/PKCS#8 密钥对。不得复制或沿用 dev 凭据，也不得把 dev 的明文配置当作 prod 回滚基线。
- 下文“发布、初始化、切换、回滚”均为**未来 prod 变更单中的操作步骤**，不表示本轮已执行或已获准在 dev 执行。

2026-11-26 起，仓库内 `nacos-config/data-source.yaml`、`key-config.yaml`、`third-services.yaml` 的凭据类值使用 `${ENV}` 占位符。占位符在**消费方 Java 进程**中解析；发布配置前，目标环境必须先完成变量注入，否则服务会因空凭据或错误凭据启动失败。

## 1. 本次新增文件与只读检查

| 文件 | 作用 |
|---|---|
| `java-service.env.example` | Java 服务环境变量模板；全部为占位符或注释，不含真实口令 |
| `validate-java-env.py` | 检查必填、空值、占位符、弱默认值、端口/TTL、签名方式与双 key 配对；只输出变量名和错误码 |
| `inspect-nacos-config.py` | 只读巡检 Nacos 配置；输出 dataId、SHA-256、明文可疑凭据标记、环境变量占位符标记；不输出正文或口令 |

### 1.1 环境变量校验

```bash
# 校验受控 EnvironmentFile/Secret 生成的本地文件
python3 nacos-config/validate-java-env.py --env-file /secure/path/java-service.env

# 明确要求 JKS 签名；PEM 场景改用 --signing pem
python3 nacos-config/validate-java-env.py --env-file /secure/path/java-service.env --signing jks

# 校验当前进程已注入的环境（不传 --env-file）
python3 nacos-config/validate-java-env.py --json
```

约束与行为：

- 进程环境变量优先于 env 文件；不会执行 env 文件中的 shell 代码，也不会做变量展开。
- 必填项缺失、空字符串、`<...>`/`${...}` 占位符、常见弱默认值、过短口令、非法端口/TTL、仅回环 IP 白名单、签名配置不完整、旧 key 只配置一半都会失败。
- `AGENT_SERVICE_API_KEY_PREVIOUS` 与 `AGENT_SERVICE_API_KEY_PREVIOUS_ID` 必须同时设置或同时留空；设置时不得与当前 key/ID 相同。
- 输出只含变量名、错误码和计数，**永不输出变量值**；文件解析错误只给文件名/行号/变量名。
- 退出码：`0` 通过，`1` 校验失败，`2` 用法或文件解析失败。
- 该脚本**不验证凭据是否真实可用、不检查目标机路径是否存在、不评估完整熵、不连接任何服务**。这些仍需在 prod 灰度步骤中验证。

### 1.2 Nacos 配置只读巡检

当前 dev 参数仅为默认值：server `192.168.89.128:8848`，namespace `4833404f-4b82-462e-889a-3c508160c6b4`，group `DEFAULT_GROUP`，默认 dataId 为 `data-source.yaml`、`key-config.yaml`、`third-services.yaml`。

```bash
# 本地样本巡检，无网络请求
python3 nacos-config/inspect-nacos-config.py --local-dir nacos-config

# 远端只读 GET；NACOS_ACCESS_TOKEN 由受控进程环境注入，不放在命令行
python3 nacos-config/inspect-nacos-config.py \
  --server-url http://192.168.89.128:8848 \
  --namespace 4833404f-4b82-462e-889a-3c508160c6b4 \
  --group DEFAULT_GROUP \
  --json
```

输出字段固定为：

- `data_id`：被检查的 dataId。
- `sha256`：配置**原始字节**的 SHA-256，用于核对发布版本。
- `plaintext_credential_suspected`：是否发现非占位符的敏感键值、URI 内嵌凭据、`${ENV:非空默认值}` 或私钥块。
- `env_placeholder_present`：是否发现 `${ENV}` / `${ENV:default}` 占位符。
- `status` / `error`：读取结果；错误不输出 HTTP 响应正文。

安全边界：

- 远端模式只调用 `GET /nacos/v1/cs/configs`，不发布、不修改、不删除；禁止重定向和隐式代理，避免凭据被转发。
- `NACOS_ACCESS_TOKEN` 只从环境读取并随请求发送，不写入输出、日志或示例文件。
- 本地模式只读取指定 dataId 对应文件，防止路径穿越。
- 明文检测是保守启发式，不是完整 YAML 解析器或全仓秘密扫描器；空口令不算“明文”，但必须由环境变量校验器拦截。注释中的占位符和口令不参与判断。
- 退出码：`0` 全部读取成功且未发现可疑明文，`1` 发现可疑明文，`2` 任一 dataId 读取失败。即使发现可疑项也会输出其哈希和标记，不输出内容。

## 2. 变量清单

生产环境变量模板见 [`java-service.env.example`](java-service.env.example)。以下变量必须在每个实际消费它们的 Java 服务进程中可见；不能只在一台发布机上设置。

| 变量 | 配置来源/用途 | prod 要求 |
|---|---|---|
| `WMS_DB_HOST` / `WMS_DB_PORT` | `data-source.yaml` MySQL 地址 | 必填；独立 prod 地址 |
| `WMS_DB_USERNAME` / `WMS_DB_PASSWORD` | MySQL 账号/口令 | 必填；最小权限账号、新强口令 |
| `WMS_REDIS_HOST` / `WMS_REDIS_PORT` | Redis 地址 | 必填；独立 prod 地址 |
| `WMS_REDIS_PASSWORD` | Redis AUTH | 必填；新强口令或 ACL 用户凭据 |
| `WMS_MONGO_HOST` / `WMS_MONGO_PORT` | MongoDB 地址 | 必填；独立 prod 地址 |
| `WMS_MONGO_USERNAME` / `WMS_MONGO_PASSWORD` | MongoDB 账号/口令 | 必填；最小权限账号、新强口令 |
| `WMS_OAUTH2_MGR_ID` / `WMS_OAUTH2_MGR_PASSWORD` | `key-config.yaml` oauth2 starter 管理端客户端 | 必填；独立 prod 客户端与新 secret |
| `AGENT_SERVICE_API_KEY` / `AGENT_SERVICE_API_KEY_ID` | 巡检服务当前 API Key | 必填；新 key 与全新 ID |
| `AGENT_SERVICE_USERNAME` / `AGENT_SERVICE_PASSWORD` | 固定只读巡检服务账号 | 必填；prod 独立账号与新口令 |
| `AGENT_SERVICE_WAREHOUSES` | 服务账号仓库范围 | 必填；业务确认的仓库编码，不使用默认 `W01` |
| `AGENT_SERVICE_TOKEN_TTL_SECONDS` | 服务令牌 TTL | 必填；60–86400 秒，按安全策略设置 |
| `AGENT_SERVICE_TOKEN_USE` | JWT 用途 claim | 必填；协议值必须严格为 `agent_service` |
| `AGENT_SERVICE_TOKEN_ISSUER` | JWT 签发者 | 必填；`wms-login` 与 `wms-gateway` 必须一致 |
| `AGENT_SERVICE_IP_WHITELIST` | service-token 来源 IP 白名单 | 必填；prod Agent 实际出口 IP，不得仅为回环地址 |
| `AGENT_SERVICE_JKS_PATH` / `AGENT_SERVICE_JKS_PASSWORD` / `AGENT_SERVICE_KEY_ALIAS` / `AGENT_SERVICE_KEY_PASSWORD` | JKS 签名配置 | JKS 模式四者必填；prod 使用新密钥库与外部挂载路径 |
| `AGENT_SERVICE_PRIVATE_KEY_PATH` | PKCS#8 PEM 签名配置 | PEM 模式必填；与 JKS 二选一，PEM 优先 |
| `AGENT_SERVICE_API_KEY_PREVIOUS` / `AGENT_SERVICE_API_KEY_PREVIOUS_ID` | 可选双 key 宽限期 | 仅灰度过渡期使用；成对设置，验收后清空 |
| `FASTDFS_HTTP_SECRET_KEY` | `third-services.yaml` FastDFS anti-steal token | 必填；prod 新强 secret |

签名方式使用 `--signing any|jks|pem` 校验。`wms-login` 的自签私钥与 `wms-oauth2` 的用户令牌验签必须使用**同一把 prod 新密钥**；只改一侧会造成登录成功但网关验签失败。

> 范围限制：本模板覆盖当前 Nacos YAML 与 `wms-login` / `wms-oauth2` / `wms-gateway` 中已有的环境变量引用。`wms-common` 的 oauth2 用户端默认配置、Easy-ES、Seata、`wms-agent/.env`（LLM/PG）等其它凭据源不在本模板内，仍是 prod 前独立审计项，不能据此宣称全仓已无明文凭据。

## 3. 正式上线前切换顺序（仅 prod，未执行）

1. **冻结 dev 与审批变更单**
   - 明确 prod namespace/group、三个 dataId、目标实例清单、变更窗口、负责人、回滚决策人和观测指标。
   - 记录当前父仓库 HEAD、配置样本 SHA-256 和发布物哈希；任何配置正文备份放入受控存储，不放入仓库或日志。

2. **离线预检**
   - 对三个 YAML 做评审并运行本地只读巡检，确认 `plaintext_credential_suspected=false`、`env_placeholder_present=true`，记录 SHA-256。
   - 在每台目标机使用填值后的 env 文件运行校验器；确认无缺失、空值、占位符或弱默认值。
   - 检查 Secret/EnvironmentFile 权限（建议 `0600`）、挂载路径、JKS/PEM 文件权限与属主；校验器本身不检查目标机路径。
   - 确认旧 prod 配置、旧 env、旧签名密钥和已知良好实例可按受控流程恢复。

3. **prod 独立初始化新凭据**
   - 通过受控 Secret 管理流程生成 DB、Redis、Mongo、oauth2 管理端、Agent 服务账号/API Key、FastDFS secret；一律新生成，不复用 dev。
   - 生成新的 JKS/PKCS#8 密钥对，同时配置 `wms-login` 与 `wms-oauth2`；旧 prod 密钥保留到回滚窗口结束。
   - 初始化只读巡检账号、仓库范围和资源角色；确认 Agent 出口 IP 与白名单一致。
   - 若是已有 prod 环境，优先创建新账号/新密钥并与旧凭据并存；不要在所有实例仍使用旧口令时原地修改 DB/Redis/Mongo 口令。

4. **先注入环境，再发布配置**
   - 将 prod env 注入全部消费服务的启动环境，并在 canary 节点确认进程能读取完整变量。
   - **禁止先把共享配置切成占位符再补环境**。若不能一次覆盖全部消费者，使用独立灰度 namespace/group，或先完成兼容性部署，避免 Nacos 自动刷新后批量连接失败。
   - 环境与预检通过后，按审批的发布流程将三个 YAML 发布到**独立 prod namespace/group**；本脚本不提供发布功能。
   - 发布后立即只读巡检，核对 dataId 与 SHA-256，确认没有可疑明文且保留环境变量占位符。

5. **canary 灰度验证**
   - 先启动/重启关键链路 canary：`wms-oauth2` → `wms-login` → `wms-gateway`，再启动一个业务服务与 Agent。
   - 完成第 4 节检查，观察至少一个完整登录/令牌刷新周期和一次巡检周期，或按变更单要求延长。
   - 无异常后按实例滚动重启其余服务；每次只推进一个实例，等待健康检查和指标稳定后再继续。

6. **结束宽限期与留证**
   - 仅 API Key 需要双 key 时，在 canary 验证新 key、Agent 切到新 key/ID 后，清除旧 key 对；旧 key 清除后再次验证 service-token 与巡检取数。
   - DB/Redis/Mongo 没有通用“双口令”机制，必须在独立账号或成对切换方案下执行，不能把清旧口令当作独立收尾动作。
   - 记录变更单号、操作人、时间、配置哈希、校验结果、灰度结果和回滚窗口结束时间；证据中不得出现口令、token、配置正文或完整连接串。

## 4. 灰度验证清单

- [ ] 三个 dataId 的 SHA-256 与审批版本一致；只读巡检无可疑明文。
- [ ] 每个目标实例的环境变量校验通过；服务日志无未解析占位符、`Access denied`、`NOAUTH`、Mongo 认证失败或 keystore 口令错误。
- [ ] MySQL：健康检查通过，使用专用 canary 账号完成最小读写探针并按变更单清理。
- [ ] Redis：AUTH/ACL 通过，合成 token 键的写入、读取、删除通过，不触碰真实用户 token。
- [ ] MongoDB：认证与只读 ping/查询通过。
- [ ] oauth2：管理端客户端可换取令牌；用户登录、刷新、注销正常。
- [ ] JKS：`wms-login` 签发的服务令牌含正确 issuer，网关验签通过；`wms-oauth2` 用户令牌与网关验签一致，无算法/密钥错位。
- [ ] Agent：新 API Key 可换取 service-token，六类只读数据源访问正常，未出现认证失败或非预期 partial。
- [ ] FastDFS：anti-steal token 校验通过；小文件上传/下载及清理按变更单执行。
- [ ] 网关匿名、错角色、注销令牌等负例仍被拒绝；不得因切凭据放大权限。
- [ ] 登录成功率、5xx、连接池等待、Redis/Mongo 错误率和令牌刷新错误率未劣于发布前基线。
- [ ] 所有证据已脱敏，未输出 env 值、配置正文、JKS 内容或访问令牌。

## 5. 回滚触发条件与步骤

### 5.1 触发条件（命中任一即停止推进并评估回滚）

- canary 无法启动、健康检查失败，或出现未解析占位符、认证失败、keystore/私钥错误。
- 登录、令牌换取/刷新/注销失败，或网关对合法令牌拒绝、对匿名/错角色令牌放行。
- DB / Redis / Mongo 连接错误、`NOAUTH`、认证失败或连接池耗尽。
- `wms-login` 与 `wms-oauth2` 签名/验签错位，issuer 不一致，或 service-token 无法访问既定只读端点。
- FastDFS anti-steal token 校验失败，Agent 取数失败或出现非预期 partial。
- 配置 SHA-256 与审批版本不一致，或只读巡检发现可疑明文。
- 关键错误率、延迟或登录成功率持续劣于发布前基线，或出现数据一致性异常。

### 5.2 回滚步骤

1. **停止 rollout 与发布**：不再发布新配置、不再重启更多实例；保留现场与脱敏日志。
2. **切回已知良好实例**：使用发布前健康实例或流量调度规则隔离 canary；不要删除新 env 或密钥，先保留排查材料。
3. **恢复 prod 上一版本配置**：通过受控发布流程恢复已审批的 prod 配置版本并核对 SHA-256；严禁回退到 dev 明文配置或 dev namespace。
4. **恢复配套环境与密钥**：受影响实例恢复上一版 env 包；`wms-login`、`wms-oauth2`、`wms-gateway` 必须成组恢复匹配的签名密钥/issuer，避免单侧回滚。
5. **处理双 key**：若已启用宽限期，将 Agent 切回旧 key/ID 对并验证；若 DB/Redis/Mongo 已原地改口令，只有按应急变更单恢复旧凭据并同步重启全部消费者，不能只改一端。
6. **复跑灰度清单**：先验证登录、令牌、网关鉴权和三类数据存储，再恢复业务流量与 Agent；持续观察到指标回到基线。
7. **留证与清理**：记录触发条件、回滚配置哈希、操作人、时间和验证结果；新 prod 凭据在根因闭环前保持隔离，不泄露、不复用到其它环境。

若这是首次 prod 上线且没有已知良好 prod 基线，回滚意味着**终止上线并保留现有系统流量**，不是回退到 dev。

## 6. 历史记录与未执行项

### 仓库配置整改（历史）

- `data-source.yaml`、`key-config.yaml` 的凭据类值已改为环境变量占位符；`third-services.yaml` 的 FastDFS secret 已改为环境变量占位符。
- `wms-login/application.yaml` 的 JKS/私钥口令默认值已移除；`init.sh` 的凭据门禁覆盖 password/secret/api-key 类键，失败时只输出文件、行号和键名。
- 早期 dev 联调曾执行过 Agent API Key 轮换并关闭宽限期；该历史动作**不是本轮授权，也不适用于 prod**。

### 明确未执行

- dev 未发布上述占位符配置，未生成/轮换新凭据，未修改 DB / Redis / Mongo / JKS 口令。
- `jwt.jks` 的 storepass/keypass 未轮换；`wms-oauth2` 运行期实际加载的 prod keystore 与口令来源仍需在 prod 变更单中确认。
- DB / Redis / Mongo / oauth2 管理端 / FastDFS 的 prod 新凭据尚未初始化。
- 本轮只做本地假值/空值测试与仓库样本只读巡检，**未调用远端 dev/prod Nacos，未执行任何发布或服务变更**。
