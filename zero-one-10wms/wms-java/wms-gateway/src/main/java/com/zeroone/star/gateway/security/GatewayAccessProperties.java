package com.zeroone.star.gateway.security;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * <p>
 * 描述：网关访问控制配置（ADR-021 网关侧修复）。
 * </p>
 * <p>
 * 复用 starter 已声明的 {@code zo.cloud.starter.gateway.white-paths / inner-paths} 配置，
 * 并增加独立开关，避免鉴权行为被 starter 的 {@code open-authorization} 整体旁路：
 * </p>
 * <ul>
 *   <li>{@code deny-unregistered}：未登记资源路径是否直接拒绝；</li>
 *   <li>{@code unregistered-allow-paths}：{@code deny-unregistered=false} 时仍必须显式命中的前缀清单，
 *       清单外的新路径一律 403（ADR-021 复核结论：不能再「未登记即放行」）；</li>
 *   <li>{@code service-token-paths}：服务令牌（异常巡检账号）只能访问自身的 Agent 端点，
 *       不能进入任何业务接口；</li>
 *   <li>{@code issuer}：配置后校验 JWT 的 {@code iss}。</li>
 * </ul>
 *
 * @author zero-one
 * @version 1.1.0
 */
@Data
@Component
@ConfigurationProperties(prefix = "zo.cloud.starter.gateway")
public class GatewayAccessProperties {

    /** 匿名可访问的白名单路径（Ant 风格）。 */
    private List<String> whitePaths = new ArrayList<>();

    /** 需要凭证但不需要资源角色校验的路径（Ant 风格）。 */
    private List<String> innerPaths = new ArrayList<>();

    /** JWT 中承载角色的 claim 名称，默认 authorities。 */
    private String authorityClaimName = "authorities";

    /** 角色前缀；配置后比较时两侧都会剥离该前缀。 */
    private String authorityPrefix = "";

    /**
     * 未在 {@code AUTH:RESOURCE_ROLES} 登记的路径是否拒绝。
     *
     * <p>为 true 时直接 403；为 false 时仍需命中 {@link #unregisteredAllowPaths}，否则 403。</p>
     */
    private boolean denyUnregistered = false;

    /**
     * {@code deny-unregistered=false} 时允许通过的未登记路径前缀（Ant 风格）。
     *
     * <p>ADR-021 复核（2026-11-26）：{@code t_s_function} 中带资源角色的端点只有 8 条，
     * 前端 535 个接口路径里 518 个未登记。为避免「未登记即放行任何路径」，把这些存量接口的
     * 一级前缀在配置中显式列出：清单内仍只验登录（存量债，待资源行补齐后收敛），
     * 清单外的新路径一律 403。清单为空表示未登记路径全部拒绝。</p>
     */
    private List<String> unregisteredAllowPaths = new ArrayList<>();

    /** 服务令牌的标识 claim 名称，默认 token_use。 */
    private String serviceTokenClaim = "token_use";

    /** 服务令牌的标识 claim 取值，默认 agent_service。 */
    private String serviceTokenValue = "agent_service";

    /** 服务令牌允许访问的路径（Ant 风格）；清单外一律 403。 */
    private List<String> serviceTokenPaths = new ArrayList<>();

    /** 开发观察模式：记录未登记/角色不匹配并放行，不改变服务令牌硬边界。 */
    private boolean auditAuthorization = false;

    /** 服务令牌期望的 JWT 签发者；为空则不校验 iss（存量用户令牌暂无 iss）。 */
    private String issuer = "";

    /** 401/403 响应允许的跨域来源；"*" 表示回显任意来源。 */
    private List<String> allowedOrigins = new ArrayList<>();
}
