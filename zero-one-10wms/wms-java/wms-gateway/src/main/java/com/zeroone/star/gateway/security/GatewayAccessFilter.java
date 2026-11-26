package com.zeroone.star.gateway.security;

import com.zeroone.cloud.starter.gateway.service.LoadResourcesData;
import com.zeroone.cloud.starter.gateway.service.TokenExtendsValidate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.ReactiveJwtDecoder;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * <p>
 * 描述：网关认证与授权过滤器（ADR-021 网关侧修复）。
 * </p>
 * <p>
 * 背景：starter 的 {@code AuthGlobalFilter} 在缺少 Authorization 头时直接放行下游，
 * 且 {@code AuthorizationManager} 在 {@code open-authorization=false} 时对一切请求返回允许，
 * 两者叠加导致匿名可访问业务接口、资源角色不生效（ADR-021）。
 * </p>
 * <p>
 * 本过滤器在自己的顺序位（早于 starter 过滤器）完成判定，且不依赖 {@code open-authorization}：
 * </p>
 * <ol>
 *   <li>路径先做规范化（去 {@code ;matrix} 参数、去重复斜杠、去尾斜杠、拒绝 {@code ..}），
 *       避免用 {@code /a/b/}、{@code //a/b}、{@code /a/b;x=1} 绕过精确角色键；</li>
 *   <li>非白名单、非 OPTIONS 请求必须携带 {@code Authorization: Bearer <JWT>}，否则 401；</li>
 *   <li>JWT 通过资源服务器验签（{@link ReactiveJwtDecoder}）且未注销（{@link TokenExtendsValidate}），
 *       服务令牌配置 {@code issuer} 时同时校验 {@code iss}，否则 401；</li>
 *   <li>服务令牌（{@code token_use=agent_service}）只允许访问 {@code service-token-paths}，否则 403；</li>
 *   <li>已登记资源路径按 {@code AUTH:RESOURCE_ROLES} 校验角色，角色不匹配 403；
 *       角色缓存不可用时 fail-closed（503），不再退化成「空角色⇒放行」；</li>
 *   <li>未登记路径：{@code deny-unregistered=true} 直接 403；否则必须命中
 *       {@code unregistered-allow-paths} 显式清单，清单外一律 403。</li>
 * </ol>
 * <p>
 * 为什么是 {@link WebFilter} 而不是 {@code GlobalFilter}：实测发现 Spring Security 的
 * {@code WebFilterChainProxy}（资源服务器）在网关 GlobalFilter 链路之前执行，非法令牌会先被 starter 的
 * {@code RestfulAuthenticationEntryPoint} 处理成「HTTP 200 + body code=401」，既不是真正的 401 也无法统一文案。
 * 因此本过滤器注册为最早执行的 {@link WebFilter}，在安全链之前完成认证与授权判定。
 * </p>
 *
 * @author zero-one
 * @version 1.1.0
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class GatewayAccessFilter implements WebFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(GatewayAccessFilter.class);

    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();
    private static final String BEARER_PREFIX = "Bearer ";
    private static final String WILDCARD_SUFFIX = "/**";
    private static final int MAX_PARENT_LOOKUP = 8;
    private static final String CREDENTIAL_INVALID = "凭证无效或已过期";

    private final GatewayAccessProperties accessProperties;
    private final ReactiveJwtDecoder jwtDecoder;
    private final LoadResourcesData loadResourcesData;
    private final TokenExtendsValidate tokenExtendsValidate;

    public GatewayAccessFilter(GatewayAccessProperties accessProperties,
                               ReactiveJwtDecoder jwtDecoder,
                               LoadResourcesData loadResourcesData,
                               TokenExtendsValidate tokenExtendsValidate) {
        this.accessProperties = accessProperties;
        this.jwtDecoder = jwtDecoder;
        this.loadResourcesData = loadResourcesData;
        this.tokenExtendsValidate = tokenExtendsValidate;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path;
        try {
            path = normalizePath(request.getURI().getPath());
        } catch (IllegalArgumentException invalidPath) {
            log.debug("gateway access: invalid path rejected, raw={}", request.getURI().getRawPath());
            return reject(exchange, HttpStatus.BAD_REQUEST, "请求路径不合法");
        }

        if (HttpMethod.OPTIONS.equals(request.getMethod()) || matches(accessProperties.getWhitePaths(), path)) {
            return chain.filter(exchange);
        }

        String authorization = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (!StringUtils.hasText(authorization)
                || !authorization.startsWith(BEARER_PREFIX)
                || authorization.length() <= BEARER_PREFIX.length()) {
            log.debug("gateway access: missing bearer credential, path={}", path);
            return reject(exchange, HttpStatus.UNAUTHORIZED, "缺少 Authorization: Bearer 凭证");
        }
        String token = authorization.substring(BEARER_PREFIX.length()).trim();

        // 注意：NimbusReactiveJwtDecoder 对「格式非法」的令牌可能在 decode 调用处直接抛出
        // BadJwtException（同步异常，不会进入 Mono 的错误信号），若不在此捕获就会变成 500。
        Mono<Jwt> decoded;
        try {
            decoded = jwtDecoder.decode(token);
        } catch (RuntimeException error) {
            log.debug("gateway access: jwt decode threw synchronously, path={}, reason={}", path, error.getClass().getSimpleName());
            return reject(exchange, HttpStatus.UNAUTHORIZED, CREDENTIAL_INVALID);
        }
        if (decoded == null) {
            log.debug("gateway access: jwt decoder returned null, path={}", path);
            return reject(exchange, HttpStatus.UNAUTHORIZED, CREDENTIAL_INVALID);
        }
        return decoded
                .map(jwt -> decide(jwt, token, path))
                .onErrorResume(error -> {
                    log.debug("gateway access: jwt decode failed, path={}, reason={}, message={}", path, error.getClass().getSimpleName(), error.getMessage());
                    return Mono.just(Decision.reject(HttpStatus.UNAUTHORIZED, CREDENTIAL_INVALID));
                })
                .defaultIfEmpty(Decision.reject(HttpStatus.UNAUTHORIZED, CREDENTIAL_INVALID))
                .flatMap(decision -> decision.allowed
                        ? chain.filter(exchange)
                        : reject(exchange, decision.status, decision.message));
    }

    /**
     * 验签通过后的同步判定：注销状态、签发者、服务令牌边界、内部路径、资源角色。
     */
    private Decision decide(Jwt jwt, String token, String path) {
        if (tokenExtendsValidate.isLogout(token)) {
            return Decision.reject(HttpStatus.UNAUTHORIZED, "用户凭证已注销");
        }
        if (isServiceToken(jwt)) {
            String expectedIssuer = accessProperties.getIssuer();
            if (StringUtils.hasText(expectedIssuer)) {
                String actualIssuer = jwt.getClaimAsString("iss");
                if (!expectedIssuer.equals(actualIssuer)) {
                    log.info("gateway access: service token issuer mismatch, path={}, expected={}, actual={}", path, expectedIssuer, actualIssuer);
                    return Decision.reject(HttpStatus.UNAUTHORIZED, CREDENTIAL_INVALID);
                }
            }
            if (!matches(accessProperties.getServiceTokenPaths(), path)) {
                log.info("gateway access: service token denied outside its scope, path={}", path);
                return Decision.reject(HttpStatus.FORBIDDEN, "服务令牌不可访问该资源");
            }
            return Decision.allow();
        }
        if (matches(accessProperties.getInnerPaths(), path)) {
            return Decision.allow();
        }
        List<String> requiredRoles;
        try {
            requiredRoles = resolveRequiredRoles(path);
        } catch (RoleLookupException error) {
            log.error("gateway access: role lookup failed, fail-closed, path={}", path, error.getCause());
            return Decision.reject(HttpStatus.SERVICE_UNAVAILABLE, "角色缓存不可用，暂时拒绝访问");
        }
        List<String> authorities = claimAuthorities(jwt);
        String userName = jwt.getClaimAsString("user_name");
        if (requiredRoles.isEmpty()) {
            if (accessProperties.isAuditAuthorization()) {
                log.info("AUTHZ_AUDIT event=unregistered path={} user={} roles={} action=allow", path, userName, authorities);
                return Decision.allow();
            }
            if (accessProperties.isDenyUnregistered()) {
                return Decision.reject(HttpStatus.FORBIDDEN, "资源未登记，默认拒绝");
            }
            if (!matches(accessProperties.getUnregisteredAllowPaths(), path)) {
                log.warn("gateway access: unregistered path not in allow-list, denied, path={}", path);
                return Decision.reject(HttpStatus.FORBIDDEN, "资源未登记且不在放行清单，默认拒绝");
            }
            log.warn("gateway access: unregistered path allowed by explicit allow-list, path={}", path);
            return Decision.allow();
        }
        for (String role : requiredRoles) {
            if (authorities.contains(stripPrefix(role))) {
                return Decision.allow();
            }
        }
        if (accessProperties.isAuditAuthorization()) {
            log.info("AUTHZ_AUDIT event=role_mismatch path={} user={} roles={} required={} action=allow", path, userName, authorities, requiredRoles);
            return Decision.allow();
        }
        log.debug("gateway access: role mismatch, path={}, required={}, actual={}", path, requiredRoles, authorities);
        return Decision.reject(HttpStatus.FORBIDDEN, "当前角色无权访问该资源");
    }

    /**
     * 与 starter 一致：先按精确路径查角色，未登记则逐级回退到 {@code 父路径/**}。
     *
     * <p>修复点：回退时必须先剥掉尾部的 {@code /**} 再取上一级，否则
     * {@code /a/b/**} 会算出 {@code /a/b/**} 自身，形成死循环。</p>
     */
    private List<String> resolveRequiredRoles(String path) {
        Set<String> visited = new LinkedHashSet<>();
        String current = path;
        for (int depth = 0; depth <= MAX_PARENT_LOOKUP; depth++) {
            if (!visited.add(current)) {
                break;
            }
            List<String> roles = loadRoles(current);
            if (!roles.isEmpty()) {
                return roles;
            }
            String parent = parentOf(current);
            if (parent == null) {
                break;
            }
            current = parent;
        }
        return Collections.emptyList();
    }

    private static String parentOf(String current) {
        String base = current.endsWith(WILDCARD_SUFFIX)
                ? current.substring(0, current.length() - WILDCARD_SUFFIX.length())
                : current;
        int lastSeparator = base.lastIndexOf('/');
        if (lastSeparator <= 0) {
            return null;
        }
        return base.substring(0, lastSeparator) + WILDCARD_SUFFIX;
    }

    private List<String> loadRoles(String path) {
        try {
            List<String> roles = loadResourcesData.loadRolesByUrlPath(path);
            return roles == null ? Collections.<String>emptyList() : roles;
        } catch (RuntimeException error) {
            // 不能退化成空角色：空角色在「未登记」分支可能被放行，等于缓存故障时全网 fail-open。
            throw new RoleLookupException(path, error);
        }
    }

    private boolean isServiceToken(Jwt jwt) {
        String claim = accessProperties.getServiceTokenClaim();
        String expected = accessProperties.getServiceTokenValue();
        if (!StringUtils.hasText(claim) || !StringUtils.hasText(expected)) {
            return false;
        }
        String actual = jwt.getClaimAsString(claim);
        return expected.equalsIgnoreCase(StringUtils.hasText(actual) ? actual.trim() : "");
    }

    private List<String> claimAuthorities(Jwt jwt) {
        String claimName = accessProperties.getAuthorityClaimName();
        if (!StringUtils.hasText(claimName)) {
            claimName = "authorities";
        }
        List<String> raw = jwt.getClaimAsStringList(claimName);
        if (raw == null || raw.isEmpty()) {
            String single = jwt.getClaimAsString(claimName);
            raw = StringUtils.hasText(single) ? Collections.singletonList(single) : Collections.<String>emptyList();
        }
        List<String> normalized = new ArrayList<>(raw.size());
        for (String value : raw) {
            if (StringUtils.hasText(value)) {
                normalized.add(stripPrefix(value.trim()));
            }
        }
        return normalized;
    }

    private String stripPrefix(String role) {
        String prefix = accessProperties.getAuthorityPrefix();
        if (StringUtils.hasText(prefix) && role.startsWith(prefix)) {
            return role.substring(prefix.length());
        }
        return role;
    }

    private boolean matches(List<String> patterns, String path) {
        if (patterns == null || patterns.isEmpty()) {
            return false;
        }
        for (String pattern : patterns) {
            if (StringUtils.hasText(pattern) && PATH_MATCHER.match(pattern.trim(), path)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 路径规范化：丢弃空段（含重复斜杠与尾斜杠）、去掉 {@code ;matrix} 参数、拒绝 {@code ..}。
     *
     * @param rawPath 原始路径
     * @return 规范化后的路径，根路径返回 {@code /}
     * @throws IllegalArgumentException 路径包含 {@code ..} 段
     */
    static String normalizePath(String rawPath) {
        if (!StringUtils.hasText(rawPath)) {
            return "/";
        }
        StringBuilder normalized = new StringBuilder(rawPath.length());
        for (String segment : rawPath.split("/", -1)) {
            if (segment.isEmpty() || ".".equals(segment)) {
                continue;
            }
            int matrixIndex = segment.indexOf(';');
            String cleaned = matrixIndex >= 0 ? segment.substring(0, matrixIndex) : segment;
            if (cleaned.isEmpty()) {
                continue;
            }
            if ("..".equals(cleaned)) {
                throw new IllegalArgumentException("path traversal segment");
            }
            normalized.append('/').append(cleaned);
        }
        return normalized.length() == 0 ? "/" : normalized.toString();
    }

    private Mono<Void> reject(ServerWebExchange exchange, HttpStatus status, String message) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(status);
        HttpHeaders headers = response.getHeaders();
        headers.setContentType(MediaType.parseMediaType("application/json;charset=UTF-8"));
        appendCorsHeaders(exchange, headers);
        String body = "{\"code\":" + status.value() + ",\"message\":\"" + message + "\"}";
        DataBuffer buffer = response.bufferFactory().wrap(body.getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(buffer));
    }

    /**
     * 401/403 也要能被浏览器读到响应体：没有 CORS 头时前端只能看到 CORS 错误。
     */
    private void appendCorsHeaders(ServerWebExchange exchange, HttpHeaders headers) {
        String origin = exchange.getRequest().getHeaders().getFirst(HttpHeaders.ORIGIN);
        if (!StringUtils.hasText(origin) || !originAllowed(origin)) {
            return;
        }
        headers.set(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, origin);
        headers.set(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS, "true");
        headers.add(HttpHeaders.VARY, HttpHeaders.ORIGIN);
    }

    private boolean originAllowed(String origin) {
        List<String> allowed = accessProperties.getAllowedOrigins();
        if (allowed == null || allowed.isEmpty()) {
            return false;
        }
        for (String pattern : allowed) {
            if (!StringUtils.hasText(pattern)) {
                continue;
            }
            String candidate = pattern.trim();
            if ("*".equals(candidate) || candidate.equalsIgnoreCase(origin) || PATH_MATCHER.match(candidate, origin)) {
                return true;
            }
        }
        return false;
    }

    @Override
    public int getOrder() {
        // 最早执行：必须早于 Spring Security 的 WebFilterChainProxy，否则非法令牌会被 starter 的
        // RestfulAuthenticationEntryPoint 处理成「HTTP 200 + code=401」，拿不到真实 401。
        return Ordered.HIGHEST_PRECEDENCE;
    }

    private static final class RoleLookupException extends RuntimeException {

        private RoleLookupException(String path, RuntimeException cause) {
            super(path, cause);
        }
    }

    private static final class Decision {

        private final boolean allowed;
        private final HttpStatus status;
        private final String message;

        private Decision(boolean allowed, HttpStatus status, String message) {
            this.allowed = allowed;
            this.status = status;
            this.message = message;
        }

        private static Decision allow() {
            return new Decision(true, HttpStatus.OK, "");
        }

        private static Decision reject(HttpStatus status, String message) {
            return new Decision(false, status, message);
        }
    }
}
