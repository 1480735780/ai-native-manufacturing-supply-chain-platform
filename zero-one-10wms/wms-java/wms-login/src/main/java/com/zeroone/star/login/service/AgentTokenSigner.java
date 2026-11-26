package com.zeroone.star.login.service;

import cn.hutool.json.JSONObject;
import com.nimbusds.jose.JOSEObjectType;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.JWSObject;
import com.nimbusds.jose.Payload;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.zeroone.star.login.config.AgentServiceProperties;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.KeyFactory;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.interfaces.RSAPrivateKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.Base64;
import java.util.List;

/**
 * 服务令牌自签器（异常巡检 v0.2 前置项）。
 *
 * <p>OAuth2 签发的令牌有效期是全局 24 小时，无法为服务账号单独收紧，
 * 因此这里用同一把 RSA 私钥自签一个真实短时效的 JWT：
 * - exp 真实等于 now + tokenTtlSeconds（Redis TTL 只是第二道保险）；
 * - 带 token_use=agent_service 用途标识，与普通用户令牌区分；
 * - 带 warehouse_scope 仓库范围声明，由调用方（wms-agent）消费并校验。
 *
 * <p>私钥不复制到本模块：密钥库路径由 agent.service.jks-path 配置，
 * 默认留空表示未配置，此时签发直接失败，不回退到 24 小时令牌。
 */
@Component
public class AgentTokenSigner {

    private final AgentServiceProperties properties;

    public AgentTokenSigner(AgentServiceProperties properties) {
        this.properties = properties;
    }

    /** 签发服务令牌。 */
    public String sign(
            String userName,
            String userId,
            String realname,
            List<String> authorities,
            List<String> warehouseScope,
            int ttlSeconds
    ) throws Exception {
        long now = System.currentTimeMillis() / 1000L;
        JSONObject payload = new JSONObject();
        payload.set("sub", userName);
        payload.set("iat", now);
        payload.set("exp", now + ttlSeconds);
        payload.set("user_name", userName);
        payload.set("id", userId);
        payload.set("realname", realname);
        payload.set("authorities", authorities);
        payload.set("token_use", properties.getTokenUse());
        payload.set("warehouse_scope", warehouseScope);
        if (properties.getIssuer() != null && !properties.getIssuer().trim().isEmpty()) {
            payload.set("iss", properties.getIssuer().trim());
        }

        JWSHeader header = new JWSHeader.Builder(JWSAlgorithm.RS256)
                .type(JOSEObjectType.JWT)
                .build();
        JWSObject jwsObject = new JWSObject(header, new Payload(payload.toString()));
        jwsObject.sign(new RSASSASigner(privateKey()));
        return jwsObject.serialize();
    }

    private RSAPrivateKey privateKey() throws Exception {
        String pemPath = properties.getPrivateKeyPath();
        if (pemPath != null && !pemPath.trim().isEmpty()) {
            return readPemPrivateKey(pemPath);
        }
        String jksPath = properties.getJksPath();
        if (jksPath == null || jksPath.trim().isEmpty()) {
            throw new IllegalStateException(
                    "服务签名密钥未配置（agent.service.private-key-path 或 agent.service.jks-path）");
        }
        KeyStore keyStore = KeyStore.getInstance("JKS");
        try (InputStream in = openKeyStore(jksPath)) {
            keyStore.load(in, properties.getJksPassword().toCharArray());
        }
        PrivateKey key = (PrivateKey) keyStore.getKey(
                properties.getKeyAlias(),
                properties.getKeyPassword().toCharArray()
        );
        if (!(key instanceof RSAPrivateKey)) {
            throw new IllegalStateException("密钥库中未找到 RSA 私钥");
        }
        return (RSAPrivateKey) key;
    }

    private RSAPrivateKey readPemPrivateKey(String path) throws Exception {
        String pem;
        try (InputStream in = openKeyStore(path)) {
            // 项目以 Java 8 为目标（harness 用 JDK8 跑 mvn test），不能用 InputStream.readAllBytes()
            java.io.ByteArrayOutputStream buffer = new java.io.ByteArrayOutputStream();
            byte[] chunk = new byte[4096];
            int read;
            while ((read = in.read(chunk)) != -1) {
                buffer.write(chunk, 0, read);
            }
            pem = new String(buffer.toByteArray(), StandardCharsets.UTF_8);
        }
        StringBuilder base64 = new StringBuilder();
        for (String line : pem.split("\\R")) {
            String trimmed = line.trim();
            if (trimmed.isEmpty()
                    || trimmed.startsWith("-----")
                    || trimmed.startsWith("Proc-Type")) {
                continue;
            }
            base64.append(trimmed);
        }
        byte[] der = Base64.getDecoder().decode(base64.toString());
        return (RSAPrivateKey) KeyFactory.getInstance("RSA")
                .generatePrivate(new PKCS8EncodedKeySpec(der));
    }

    private InputStream openKeyStore(String path) throws Exception {
        if (path.startsWith("classpath:")) {
            return new ClassPathResource(path.substring("classpath:".length())).getInputStream();
        }
        return Files.newInputStream(Paths.get(path));
    }
}
