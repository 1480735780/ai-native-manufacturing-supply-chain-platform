package com.zeroone.star.login.service.impl;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nimbusds.jose.JWSObject;
import com.zeroone.cloud.oauth2.entity.Oauth2Token;
import com.zeroone.star.login.config.AgentServiceProperties;
import com.zeroone.star.login.entity.TSBaseUser;
import com.zeroone.star.login.mapper.TSBaseUserMapper;
import com.zeroone.star.login.service.AgentTokenSigner;
import com.zeroone.star.login.service.OauthService;
import com.zeroone.star.login.vo.ServiceTokenVO;
import com.zeroone.star.project.components.user.UserDTO;
import com.zeroone.star.project.components.user.UserHolder;
import com.zeroone.star.project.vo.JsonVO;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.test.util.ReflectionTestUtils;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 异常巡检服务令牌（/login/service-token）行为契约。
 *
 * 覆盖：API Key（当前/上一把/错误/缺失）、IP 白名单、仓库范围（单仓省略/非法/多仓未指定）、
 * 服务账号未配置、账号停用、角色严格为 insp_read、OAuth2 认证失败、签名密钥未配置，
 * 以及成功路径的 Redis TTL、真实 JWT exp、token_use、warehouse_scope。
 */
class AgentServiceTokenTest {

    private UserServiceImpl service;
    private AgentServiceProperties properties;
    private AgentTokenSigner signer;
    private TSBaseUserMapper baseUserMapper;
    private OauthService oAuthService;
    private RedisTemplate<String, Object> redisTemplate;
    private ValueOperations<String, Object> valueOperations;
    private KeyPair keyPair;

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setUp() throws Exception {
        properties = new AgentServiceProperties();
        properties.setApiKey("key-current");
        properties.setApiKeyId("k1");
        properties.setApiKeyPrevious("key-previous");
        properties.setApiKeyPreviousId("k0");
        properties.setUsername("agent-inspector");
        properties.setPassword("pwd");
        properties.setTokenTtlSeconds(1800);
        properties.setIssuer("wms-login-agent");
        properties.setWarehouses(Collections.singletonList("W01"));
        properties.setIpWhitelist(Collections.singletonList("127.0.0.1"));

        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        keyPair = generator.generateKeyPair();
        Path pem = Files.createTempFile("agent-service-key", ".pem");
        String encoded = Base64.getMimeEncoder(64, new byte[]{'\n'})
                .encodeToString(keyPair.getPrivate().getEncoded());
        Files.write(pem, ("-----BEGIN PRIVATE KEY-----\n" + encoded
                + "\n-----END PRIVATE KEY-----\n").getBytes(StandardCharsets.UTF_8));
        properties.setPrivateKeyPath(pem.toString());
        signer = new AgentTokenSigner(properties);

        service = new UserServiceImpl();
        service.clientId = "admin";
        service.clientPassword = "123456";
        ReflectionTestUtils.setField(service, "agentServiceProperties", properties);
        ReflectionTestUtils.setField(service, "agentTokenSigner", signer);

        baseUserMapper = mock(TSBaseUserMapper.class);
        ReflectionTestUtils.setField(service, "TSBaseUserMapper", baseUserMapper);

        oAuthService = mock(OauthService.class);
        ReflectionTestUtils.setField(service, "oAuthService", oAuthService);

        redisTemplate = mock(RedisTemplate.class);
        valueOperations = mock(ValueOperations.class);
        when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        ReflectionTestUtils.setField(service, "redisTemplate", redisTemplate);
    }

    private TSBaseUser activeUser() {
        TSBaseUser user = new TSBaseUser();
        user.setId("USR-AGENT-INSPECTOR");
        user.setUsername("agent-inspector");
        user.setRealname("巡检服务账号");
        user.setStatus(1);
        user.setDeleteFlag(0);
        return user;
    }

    private void stubOAuthSuccess() {
        Oauth2Token token = new Oauth2Token();
        token.setToken("oauth2-token");
        token.setExpiresIn(86400);
        when(oAuthService.postAccessToken(any())).thenReturn(token);
    }

    @Test
    void missing_api_key_is_rejected() {
        JsonVO<ServiceTokenVO> result = service.serviceToken(null, null, "W01", "127.0.0.1");
        assertEquals(401, result.getCode());
        verify(valueOperations, never()).set(anyString(), any(), eq(1800L), any());
    }

    @Test
    void wrong_api_key_is_rejected() {
        JsonVO<ServiceTokenVO> result = service.serviceToken("nope", "k1", "W01", "127.0.0.1");
        assertEquals(401, result.getCode());
    }

    @Test
    void previous_api_key_is_accepted_during_rotation() {
        stubOAuthSuccess();
        when(baseUserMapper.selectBaseUserByUsername("agent-inspector")).thenReturn(activeUser());
        when(baseUserMapper.selectRoleCodesByUsername("agent-inspector"))
                .thenReturn(Collections.singletonList("insp_read"));

        JsonVO<ServiceTokenVO> result =
                service.serviceToken("key-previous", "k0", "W01", "127.0.0.1");

        assertEquals(10000, result.getCode());
        assertEquals("agent-inspector", result.getData().getUserName());
    }

    @Test
    void ip_not_allowed_is_rejected() {
        JsonVO<ServiceTokenVO> result =
                service.serviceToken("key-current", "k1", "W01", "10.0.0.9");
        assertEquals(403, result.getCode());
    }

    @Test
    void warehouse_outside_allow_list_is_rejected() {
        JsonVO<ServiceTokenVO> result =
                service.serviceToken("key-current", "k1", "W99", "127.0.0.1");
        assertEquals(403, result.getCode());
    }

    @Test
    void multi_warehouse_without_request_is_rejected() {
        properties.setWarehouses(java.util.Arrays.asList("W01", "W02"));
        JsonVO<ServiceTokenVO> result =
                service.serviceToken("key-current", "k1", null, "127.0.0.1");
        assertEquals(403, result.getCode());
    }

    @Test
    void service_account_not_configured_is_rejected() {
        properties.setUsername("");
        JsonVO<ServiceTokenVO> result =
                service.serviceToken("key-current", "k1", "W01", "127.0.0.1");
        assertEquals(9994, result.getCode());
    }

    @Test
    void disabled_service_account_is_rejected() {
        TSBaseUser user = activeUser();
        user.setStatus(0);
        when(baseUserMapper.selectBaseUserByUsername("agent-inspector")).thenReturn(user);
        JsonVO<ServiceTokenVO> result =
                service.serviceToken("key-current", "k1", "W01", "127.0.0.1");
        assertEquals(401, result.getCode());
    }

    @Test
    void missing_insp_read_role_is_rejected() {
        when(baseUserMapper.selectBaseUserByUsername("agent-inspector")).thenReturn(activeUser());
        when(baseUserMapper.selectRoleCodesByUsername("agent-inspector"))
                .thenReturn(Collections.singletonList("cw"));
        JsonVO<ServiceTokenVO> result =
                service.serviceToken("key-current", "k1", "W01", "127.0.0.1");
        assertEquals(403, result.getCode());
    }

    @Test
    void oauth2_authentication_failure_is_rejected() {
        when(baseUserMapper.selectBaseUserByUsername("agent-inspector")).thenReturn(activeUser());
        when(baseUserMapper.selectRoleCodesByUsername("agent-inspector"))
                .thenReturn(Collections.singletonList("insp_read"));
        Oauth2Token failed = new Oauth2Token();
        failed.setErrorMsg("bad credentials");
        when(oAuthService.postAccessToken(any())).thenReturn(failed);

        JsonVO<ServiceTokenVO> result =
                service.serviceToken("key-current", "k1", "W01", "127.0.0.1");
        assertEquals(401, result.getCode());
    }

    @Test
    void missing_signing_key_is_rejected() {
        properties.setPrivateKeyPath("");
        properties.setJksPath("");
        stubOAuthSuccess();
        when(baseUserMapper.selectBaseUserByUsername("agent-inspector")).thenReturn(activeUser());
        when(baseUserMapper.selectRoleCodesByUsername("agent-inspector"))
                .thenReturn(Collections.singletonList("insp_read"));

        JsonVO<ServiceTokenVO> result =
                service.serviceToken("key-current", "k1", "W01", "127.0.0.1");
        assertEquals(9994, result.getCode());
    }

    @Test
    void service_logout_succeeds_without_refresh_token() throws Exception {
        UserHolder holder = mock(UserHolder.class);
        when(holder.getCurrentToken()).thenReturn("service-token");
        when(holder.getCurrentUser()).thenReturn(UserDTO.builder().username("agent-inspector").build());
        ReflectionTestUtils.setField(service, "userHolder", holder);
        when(redisTemplate.delete("agent-inspector:token")).thenReturn(true);
        when(redisTemplate.delete("agent-inspector:refreshToken")).thenReturn(false);

        JsonVO<String> result = service.logout();

        assertEquals(10000, result.getCode());
        verify(redisTemplate).delete("agent-inspector:token");
        verify(redisTemplate).delete("agent-inspector:refreshToken");
    }

    @Test
    void success_issues_short_lived_scoped_token() throws Exception {
        stubOAuthSuccess();
        when(baseUserMapper.selectBaseUserByUsername("agent-inspector")).thenReturn(activeUser());
        when(baseUserMapper.selectRoleCodesByUsername("agent-inspector"))
                .thenReturn(java.util.Arrays.asList("insp_read", "cw"));

        JsonVO<ServiceTokenVO> result =
                service.serviceToken("key-current", "k1", "W01", "127.0.0.1");

        assertEquals(10000, result.getCode());
        ServiceTokenVO data = result.getData();
        assertEquals("agent-inspector", data.getUserName());
        assertEquals(Collections.singletonList("insp_read"), data.getRoles());
        assertEquals(Collections.singletonList("W01"), data.getWarehouseScope());
        assertEquals(1800, data.getExpiresIn());

        verify(valueOperations).set(
                eq("agent-inspector:token"), anyString(), eq(1800L), eq(TimeUnit.SECONDS));

        Map<String, Object> claims = new ObjectMapper().readValue(
                JWSObject.parse(data.getToken()).getPayload().toString(),
                new TypeReference<Map<String, Object>>() {
                });
        assertEquals("agent_service", claims.get("token_use"));
        assertEquals("wms-login-agent", claims.get("iss"));
        assertEquals("agent-inspector", claims.get("user_name"));
        assertEquals(1800L,
                ((Number) claims.get("exp")).longValue()
                        - ((Number) claims.get("iat")).longValue());
        assertEquals(Collections.singletonList("W01"), claims.get("warehouse_scope"));
        assertEquals(Collections.singletonList("insp_read"), claims.get("authorities"));
        assertNotNull(claims.get("id"));
    }
}
