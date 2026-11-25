package com.zeroone.star.login.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * 异常巡检服务账号配置（ADR-007 / 实施方案 §4.1）。
 *
 * 密钥只允许来自环境变量或本地 .env，不写入代码、Nacos 明文、日志或快照。
 */
@Data
@Component
@ConfigurationProperties(prefix = "agent.service")
public class AgentServiceProperties {

    /** 当前有效的 Agent API Key。 */
    private String apiKey = "";

    /** 当前 API Key 的 ID，支持轮换时双 key 并存。 */
    private String apiKeyId = "k1";

    /** 上一把 API Key，轮换窗口期内仍然有效。 */
    private String apiKeyPrevious = "";

    /** 上一把 API Key 的 ID。 */
    private String apiKeyPreviousId = "";

    /** 固定只读服务账号用户名。 */
    private String username = "";

    /** 固定只读服务账号密码，只来自环境变量。 */
    private String password = "";

    /** 服务账号 token 的有效秒数；Redis TTL 取 min(OAuth2 expiresIn, 该值)。 */
    private Integer tokenTtlSeconds = 1800;

    /** 允许访问的仓库列表。 */
    private List<String> warehouses = new ArrayList<>();

    /** 允许调用 service-token 的来源 IP 白名单。 */
    private List<String> ipWhitelist = new ArrayList<>();

    /**
     * 签名密钥库路径（支持 classpath: 前缀或绝对路径）。
     * 服务令牌用它自签短时效 JWT，因此不能留空；留空时 service-token 直接拒绝。
     */
    private String jksPath = "";

    /**
     * PKCS#8 PEM 私钥路径（与 private-key-path 二选一，优先 PEM）。
     */
    private String privateKeyPath = "";

    /** 密钥库口令。 */
    private String jksPassword = "";

    /** 密钥别名。 */
    private String keyAlias = "";

    /** 私钥口令。 */
    private String keyPassword = "";

    /** 服务令牌用途标识，写入 JWT claim，用于与普通用户令牌区分。 */
    private String tokenUse = "agent_service";
}
