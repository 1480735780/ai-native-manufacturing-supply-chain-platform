package com.zeroone.star.gateway.security;

import com.zeroone.cloud.starter.gateway.service.LoadResourcesData;
import com.zeroone.cloud.starter.gateway.service.TokenExtendsValidate;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.security.oauth2.jwt.ReactiveJwtDecoder;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.Arrays;
import java.util.Collections;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * ADR-021 网关访问控制契约测试。
 *
 * <p>覆盖验收要求：无 token 401、错误角色 403、正确角色放行；另外覆盖白名单匿名放行、
 * 凭证注销 401、未登记路径的开关行为与父路径通配回退。</p>
 */
class GatewayAccessFilterTest {

    private static final String PROTECTED_PATH = "/daycheck/yi-chang/get-yichang-down";
    private static final String SCAN_SOURCE_PATH = "/daycheck/no-up/get-no-up-goods-page";
    private static final String BACKLOG_SOURCE_PATH = "/dashboard/query-pend-snapshot";

    private GatewayAccessProperties properties;
    private ReactiveJwtDecoder jwtDecoder;
    private LoadResourcesData loadResourcesData;
    private TokenExtendsValidate tokenExtendsValidate;
    private GatewayAccessFilter filter;
    private AtomicBoolean forwarded;

    @BeforeEach
    void setUp() {
        properties = new GatewayAccessProperties();
        properties.setWhitePaths(Arrays.asList("/actuator/**", "/agent/health", "/login/service-token"));
        properties.setInnerPaths(Arrays.asList("/agent/scan", "/agent/alerts/**"));
        properties.setAuthorityClaimName("authorities");
        properties.setAuthorityPrefix("");
        properties.setUnregisteredAllowPaths(Arrays.asList("/md/**"));
        properties.setServiceTokenPaths(Arrays.asList(
                "/agent/**", "/login/logout", SCAN_SOURCE_PATH, BACKLOG_SOURCE_PATH,
                "/daycheck/yi-chang/get-yichang-down-page",
                "/daycheck/delay/im-delay",
                "/daycheck/temperature/query",
                "/stock/expiry-warning/query-all"
        ));
        properties.setAllowedOrigins(Collections.singletonList("*"));

        jwtDecoder = Mockito.mock(ReactiveJwtDecoder.class);
        loadResourcesData = Mockito.mock(LoadResourcesData.class);
        tokenExtendsValidate = Mockito.mock(TokenExtendsValidate.class);
        filter = new GatewayAccessFilter(properties, jwtDecoder, loadResourcesData, tokenExtendsValidate);
        forwarded = new AtomicBoolean(false);

        Mockito.when(tokenExtendsValidate.isLogout(Mockito.anyString())).thenReturn(false);
        Mockito.when(loadResourcesData.loadRolesByUrlPath(Mockito.anyString())).thenReturn(Collections.<String>emptyList());
    }

    @Test
    @DisplayName("白名单路径匿名放行")
    void whitePathIsAnonymous() {
        MockServerWebExchange exchange = exchange("/agent/health", null);
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "白名单路径应放行到下游");
    }

    @Test
    @DisplayName("OPTIONS 预检放行")
    void optionsRequestIsAllowed() {
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.options(PROTECTED_PATH).build());
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "OPTIONS 不应被认证拦截");
    }

    @Test
    @DisplayName("无 token 返回 401")
    void missingTokenReturns401() {
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, null);
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get(), "无 token 不得放行到下游");
    }

    @Test
    @DisplayName("非 Bearer 头返回 401")
    void nonBearerHeaderReturns401() {
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Basic abc");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get());
    }

    @Test
    @DisplayName("JWT 验签失败返回 401")
    void invalidTokenReturns401() {
        Mockito.when(jwtDecoder.decode("bad-token")).thenReturn(Mono.error(new JwtException("bad")));
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Bearer bad-token");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get());
    }

    @Test
    @DisplayName("验签同步抛异常也返回真实 401（不落到 500）")
    void synchronouslyThrownDecodeErrorReturns401() {
        Mockito.when(jwtDecoder.decode("bad-token")).thenThrow(new JwtException("Invalid JWT serialization"));
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Bearer bad-token");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get());
    }

    @Test
    @DisplayName("已注销凭证返回 401")
    void loggedOutTokenReturns401() {        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("insp_read")));
        Mockito.when(tokenExtendsValidate.isLogout("t")).thenReturn(true);
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Bearer t");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get());
    }

    @Test
    @DisplayName("正确角色放行")
    void requiredRolePasses() {
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("insp_read")));
        Mockito.when(loadResourcesData.loadRolesByUrlPath(PROTECTED_PATH))
                .thenReturn(Collections.singletonList("insp_read"));
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Bearer t");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "角色匹配应放行");
    }

    @Test
    @DisplayName("错误角色返回 403")
    void wrongRoleReturns403() {
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("cw")));
        Mockito.when(loadResourcesData.loadRolesByUrlPath(PROTECTED_PATH))
                .thenReturn(Collections.singletonList("insp_read"));
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Bearer t");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.FORBIDDEN, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get(), "角色不匹配不得放行");
    }

    @Test
    @DisplayName("未登记路径在 deny-unregistered=false 时放行")
    void unregisteredPathPassesWhenDenyDisabled() {
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("cw")));
        properties.setDenyUnregistered(false);
        MockServerWebExchange exchange = exchange("/md/goods/query", "Bearer t");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "存量功能表未全量登记时不应拦截");
    }

    @Test
    @DisplayName("未登记路径在 deny-unregistered=true 时返回 403")
    void unregisteredPathIsForbiddenWhenDenyEnabled() {
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("cw")));
        properties.setDenyUnregistered(true);
        MockServerWebExchange exchange = exchange("/md/goods/query", "Bearer t");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.FORBIDDEN, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get());
    }

    @Test
    @DisplayName("内部路径只需凭证、不做资源角色校验")
    void innerPathSkipsRoleCheck() {
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("cw")));
        MockServerWebExchange exchange = exchange("/agent/scan", "Bearer t");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "内部路径凭证有效即放行");
    }

    @Test
    @DisplayName("资源角色按父路径通配回退命中")
    void parentWildcardRoleIsResolved() {
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("insp_read")));
        Mockito.when(loadResourcesData.loadRolesByUrlPath("/daycheck/no-up/get-no-up-goods-page/detail"))
                .thenReturn(Collections.<String>emptyList());
        Mockito.when(loadResourcesData.loadRolesByUrlPath("/daycheck/no-up/get-no-up-goods-page/**"))
                .thenReturn(Collections.singletonList("insp_read"));
        MockServerWebExchange exchange = exchange("/daycheck/no-up/get-no-up-goods-page/detail", "Bearer t");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "父级通配登记的角色应生效");
    }

    @Test
    @DisplayName("角色前缀在比较前被剥离")
    void authorityPrefixIsStripped() {
        properties.setAuthorityPrefix("ROLE_");
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("ROLE_insp_read")));
        Mockito.when(loadResourcesData.loadRolesByUrlPath(PROTECTED_PATH))
                .thenReturn(Collections.singletonList("insp_read"));
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Bearer t");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "配置前缀后两侧都应归一化比较");
    }

    @Test
    @DisplayName("401/403 响应体为 JSON 且声明 UTF-8")
    void rejectionBodyIsJson() {
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, null);
        filter.filter(exchange, chain()).block();
        assertEquals(MediaType.parseMediaType("application/json;charset=UTF-8"),
                exchange.getResponse().getHeaders().getContentType());
    }

    @Test
    @DisplayName("未登记且不在显式清单内的新路径返回 403")
    void unregisteredPathOutsideAllowListReturns403() {
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("gly")));
        MockServerWebExchange exchange = exchange("/brand-new-module/query", "Bearer t");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.FORBIDDEN, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get(), "清单外的新路径必须默认拒绝");
    }

    @Test
    @DisplayName("审计模式放行未登记路径但仍要求有效令牌")
    void auditModeAllowsUnregisteredButStillRequiresToken() {
        properties.setAuditAuthorization(true);
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("gly")));
        MockServerWebExchange exchange = exchange("/brand-new-module/query", "Bearer t");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "审计模式只记录不拦截未登记路径");

        forwarded.set(false);
        MockServerWebExchange anonymous = exchange("/brand-new-module/query", null);
        filter.filter(anonymous, chain()).block();
        assertEquals(HttpStatus.UNAUTHORIZED, anonymous.getResponse().getStatusCode());
        assertFalse(forwarded.get(), "审计模式不放开匿名访问");
    }

    @Test
    @DisplayName("审计模式放行角色不匹配并保留服务令牌硬边界")
    void auditModeAllowsRoleMismatchButKeepsServiceScope() {
        properties.setAuditAuthorization(true);
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("cw")));
        Mockito.when(loadResourcesData.loadRolesByUrlPath(PROTECTED_PATH))
                .thenReturn(Collections.singletonList("insp_read"));
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Bearer t");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "审计模式只记录角色不匹配");

        forwarded.set(false);
        Mockito.when(jwtDecoder.decode("svc")).thenReturn(Mono.just(serviceToken()));
        MockServerWebExchange service = exchange("/md/goods/query", "Bearer svc");
        filter.filter(service, chain()).block();
        assertEquals(HttpStatus.FORBIDDEN, service.getResponse().getStatusCode());
        assertFalse(forwarded.get(), "服务令牌边界不随审计模式放开");
    }

    @Test
    @DisplayName("服务令牌不得进入业务接口")
    void serviceTokenCannotReachBusinessEndpoint() {
        Mockito.when(jwtDecoder.decode("svc")).thenReturn(Mono.just(serviceToken()));
        Mockito.when(loadResourcesData.loadRolesByUrlPath(PROTECTED_PATH))
                .thenReturn(Collections.singletonList("gly"));
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Bearer svc");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.FORBIDDEN, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get(), "服务令牌即使角色匹配也不得进入业务接口");
    }

    @Test
    @DisplayName("服务令牌可访问自身 Agent 端点")
    void serviceTokenCanReachAgentEndpoint() {
        Mockito.when(jwtDecoder.decode("svc")).thenReturn(Mono.just(serviceToken()));
        MockServerWebExchange exchange = exchange("/agent/scan", "Bearer svc");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "服务令牌应能访问 /agent/**");
    }

    @Test
    @DisplayName("服务令牌可访问巡检取数的只读数据源")
    void serviceTokenCanReachScanSourceEndpoint() {
        Mockito.when(jwtDecoder.decode("svc")).thenReturn(Mono.just(serviceToken()));
        Mockito.when(loadResourcesData.loadRolesByUrlPath(SCAN_SOURCE_PATH))
                .thenReturn(Collections.singletonList("insp_read"));
        MockServerWebExchange exchange = exchange(SCAN_SOURCE_PATH, "Bearer svc");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "服务令牌应能访问已声明的巡检取数端点");
    }

    @Test
    @DisplayName("六条巡检数据源路径都必须留在服务令牌边界内")
    void allScanSourcePathsRemainAllowed() {
        Mockito.when(jwtDecoder.decode("svc")).thenReturn(Mono.just(serviceToken()));
        String[] paths = {
                SCAN_SOURCE_PATH,
                "/daycheck/yi-chang/get-yichang-down-page",
                "/daycheck/delay/im-delay",
                "/daycheck/temperature/query",
                "/stock/expiry-warning/query-all",
                BACKLOG_SOURCE_PATH,
        };
        for (String path : paths) {
            forwarded.set(false);
            MockServerWebExchange exchange = exchange(path, "Bearer svc");
            filter.filter(exchange, chain()).block();
            assertTrue(forwarded.get(), "服务令牌数据源路径被移除: " + path);
        }
    }

    @Test
    @DisplayName("服务令牌可调用 logout 撤销自身会话")
    void serviceTokenCanReachLogoutEndpoint() {
        Mockito.when(jwtDecoder.decode("svc")).thenReturn(Mono.just(serviceToken()));
        MockServerWebExchange exchange = exchange("/login/logout", "Bearer svc");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "服务令牌必须能撤销自己的 Redis 会话");
    }

    @Test
    @DisplayName("服务令牌可访问 backlog 快照取数端点")
    void serviceTokenCanReachBacklogSourceEndpoint() {
        Mockito.when(jwtDecoder.decode("svc")).thenReturn(Mono.just(serviceToken()));
        Mockito.when(loadResourcesData.loadRolesByUrlPath(BACKLOG_SOURCE_PATH))
                .thenReturn(Collections.singletonList("insp_read"));
        MockServerWebExchange exchange = exchange(BACKLOG_SOURCE_PATH, "Bearer svc");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "backlog 数据源必须允许服务令牌，否则待办积压巡检恒为 partial");
    }

    @Test
    @DisplayName("服务令牌不得访问未声明的其它 daycheck 端点")
    void serviceTokenCannotReachUndeclaredDaycheckEndpoint() {
        Mockito.when(jwtDecoder.decode("svc")).thenReturn(Mono.just(serviceToken()));
        Mockito.when(loadResourcesData.loadRolesByUrlPath("/daycheck/yi-chang/get-yichang-down"))
                .thenReturn(Collections.singletonList("insp_read"));
        MockServerWebExchange exchange = exchange("/daycheck/yi-chang/get-yichang-down", "Bearer svc");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.FORBIDDEN, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get(), "未声明的取数端点必须仍然拒绝服务令牌");
    }

    @Test
    @DisplayName("角色缓存异常时 fail-closed 返回 503")
    void roleLookupFailureFailsClosed() {
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("gly")));
        Mockito.when(loadResourcesData.loadRolesByUrlPath(Mockito.anyString()))
                .thenThrow(new IllegalStateException("redis down"));
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Bearer t");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get(), "缓存不可用时不得退化成放行");
    }

    @Test
    @DisplayName("尾斜杠与矩阵参数不能绕过精确角色键")
    void pathVariantsCannotBypassRoleLookup() {
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("cw")));
        Mockito.when(loadResourcesData.loadRolesByUrlPath(PROTECTED_PATH))
                .thenReturn(Collections.singletonList("insp_read"));
        MockServerWebExchange trailing = exchange(PROTECTED_PATH + "/", "Bearer t");
        filter.filter(trailing, chain()).block();
        assertEquals(HttpStatus.FORBIDDEN, trailing.getResponse().getStatusCode());
        MockServerWebExchange matrix = exchange(PROTECTED_PATH + ";x=1", "Bearer t");
        filter.filter(matrix, chain()).block();
        assertEquals(HttpStatus.FORBIDDEN, matrix.getResponse().getStatusCode());
        assertFalse(forwarded.get(), "路径变体必须归一到同一角色键");
    }

    @Test
    @DisplayName("路径规范化：去重复斜杠、去尾斜杠、去矩阵参数")
    void normalizePathCollapsesVariants() {
        assertEquals(PROTECTED_PATH, GatewayAccessFilter.normalizePath(PROTECTED_PATH + "/"));
        assertEquals(PROTECTED_PATH, GatewayAccessFilter.normalizePath("//" + PROTECTED_PATH.substring(1) + ";a=b"));
        assertEquals("/", GatewayAccessFilter.normalizePath("/"));
        assertEquals("/", GatewayAccessFilter.normalizePath(""));
    }

    @Test
    @DisplayName("路径包含 .. 段返回 400")
    void pathTraversalReturns400() {
        MockServerWebExchange exchange = exchange("/daycheck/../md/goods/query", "Bearer t");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.BAD_REQUEST, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get());
    }

    @Test
    @DisplayName("401 响应带 CORS 头，浏览器可读取统一 JSON")
    void rejectionCarriesCorsHeaders() {
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get(PROTECTED_PATH)
                        .header(HttpHeaders.ORIGIN, "http://localhost:3000")
                        .build());
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
        assertEquals("http://localhost:3000",
                exchange.getResponse().getHeaders().getFirst(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN));
        assertEquals("true",
                exchange.getResponse().getHeaders().getFirst(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS));
    }

    @Test
    @DisplayName("配置 issuer 后服务令牌签发者不匹配返回 401")
    void issuerMismatchReturns401() {
        properties.setIssuer("wms-login-agent");
        Mockito.when(jwtDecoder.decode("svc")).thenReturn(Mono.just(serviceTokenWithIssuer("someone-else")));
        MockServerWebExchange exchange = exchange("/agent/scan", "Bearer svc");
        filter.filter(exchange, chain()).block();
        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
        assertFalse(forwarded.get());
    }

    @Test
    @DisplayName("存量用户令牌没有 iss 时仍按原角色规则放行")
    void legacyUserTokenWithoutIssuerStillAllowed() {
        properties.setIssuer("wms-login-agent");
        Mockito.when(jwtDecoder.decode("t")).thenReturn(Mono.just(jwt("gly")));
        Mockito.when(loadResourcesData.loadRolesByUrlPath(PROTECTED_PATH))
                .thenReturn(Collections.singletonList("gly"));
        MockServerWebExchange exchange = exchange(PROTECTED_PATH, "Bearer t");
        filter.filter(exchange, chain()).block();
        assertTrue(forwarded.get(), "不能因服务令牌 issuer 配置打断存量用户登录");
    }

    private MockServerWebExchange exchange(String path, String authorization) {
        MockServerHttpRequest.BaseBuilder<?> builder = MockServerHttpRequest.get(path);
        if (authorization != null) {
            builder.header(HttpHeaders.AUTHORIZATION, authorization);
        }
        return MockServerWebExchange.from(builder.build());
    }

    private org.springframework.web.server.WebFilterChain chain() {
        return exchange -> {
            forwarded.set(true);
            return Mono.empty();
        };
    }

    private Jwt jwt(String... authorities) {
        Instant now = Instant.parse("2026-11-26T05:00:00Z");
        return Jwt.withTokenValue("t")
                .header("alg", "RS256")
                .claim("authorities", Arrays.asList(authorities))
                .claim("user_name", "agent-inspector")
                .issuedAt(now)
                .expiresAt(now.plusSeconds(1800))
                .build();
    }

    private Jwt serviceToken() {
        Instant now = Instant.parse("2026-11-26T05:00:00Z");
        return Jwt.withTokenValue("svc")
                .header("alg", "RS256")
                .claim("authorities", Arrays.asList("insp_read"))
                .claim("token_use", "agent_service")
                .claim("user_name", "agent-inspector")
                .issuedAt(now)
                .expiresAt(now.plusSeconds(1800))
                .build();
    }

    private Jwt serviceTokenWithIssuer(String issuer) {
        Instant now = Instant.parse("2026-11-26T05:00:00Z");
        return Jwt.withTokenValue("svc")
                .header("alg", "RS256")
                .claim("authorities", Arrays.asList("insp_read"))
                .claim("token_use", "agent_service")
                .claim("user_name", "agent-inspector")
                .claim("iss", issuer)
                .issuedAt(now)
                .expiresAt(now.plusSeconds(1800))
                .build();
    }
}
