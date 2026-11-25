package com.zeroone.star.j1.dashboard.controller;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 积压一致快照端点 /dashboard/query-pend-snapshot 的资源-角色映射种子契约测试（JDK8 兼容）。
 *
 * 与 daycheck 的 NoUpPageResourceRoleSeedTest 同一契约：不依赖 Nacos/MySQL/Redis，只读取仓库内提交的
 * 种子 SQL，按 oauth2 侧 ResourcesServiceImpl.listAllLinkUrl(functiontype=1) ->
 * TSRoleMapper.selectRoleByFunctionUrl -> AUTH:RESOURCE_ROLES(url -> rolecodes) 的语义静态还原并断言：
 * 1) 快照端点 URL 有显式 t_s_function 资源行（functiontype=1，可被 listAllLinkUrl 加载）；
 * 2) 资源行仅增量绑定 insp_read（动态 rolecode 查询、冲突 SIGNAL、无 DELETE、不触碰 MENU-*）；
 * 3) 生成的 AUTH:RESOURCE_ROLES 映射中快照 URL 值含 insp_read。
 */
class PendSnapshotResourceRoleSeedTest {

    private static final String SNAPSHOT_URL = "/dashboard/query-pend-snapshot";
    private static final String SNAPSHOT_FUNCTION_ID = "FN-DASH-PEND-SNAPSHOT";
    private static final String INSPECT_ROLE_CODE = "insp_read";

    private static final String SEED_RELATIVE = "documents/02、项目需求/数据库/seed_dashboard_pend_snapshot_role.sql";

    // (FN-...ID) 后紧跟（可跨行）一个 /dashboard/... URL 的 INSERT..SELECT 资源行
    private static final Pattern FUNCTION_ROW = Pattern.compile(
            "'(FN-DASH-[A-Z-]+)'[^;]*?'(/dashboard/[^']+)'", Pattern.DOTALL);
    // 绑定行：(RF-...ID, FN-...ID, @insp_read_role_id)
    private static final Pattern BINDING_ROW = Pattern.compile(
            "'(RF-DASH-[A-Z-]+-INSPECT)'\\s*,\\s*'(FN-DASH-[A-Z-]+)'\\s*,\\s*@insp_read_role_id");

    private static String seedSql() throws IOException {
        List<Path> candidates = Arrays.asList(
                Paths.get("../../", SEED_RELATIVE),
                Paths.get("../", SEED_RELATIVE),
                Paths.get(SEED_RELATIVE));
        for (Path candidate : candidates) {
            if (Files.exists(candidate)) {
                return new String(Files.readAllBytes(candidate), StandardCharsets.UTF_8);
            }
        }
        throw new IOException("找不到资源角色种子 SQL，尝试过: " + candidates);
    }

    private static String stripComments(String sql) {
        StringBuilder sb = new StringBuilder();
        for (String line : sql.split("\\r?\\n")) {
            if (line.trim().startsWith("--")) {
                continue;
            }
            sb.append(line).append('\n');
        }
        return sb.toString();
    }

    private static String functionIdForUrl(String sql, String url) {
        Matcher m = FUNCTION_ROW.matcher(sql);
        while (m.find()) {
            if (url.equals(m.group(2))) {
                return m.group(1);
            }
        }
        return null;
    }

    private static boolean hasInspectBinding(String sql, String functionId) {
        Matcher m = BINDING_ROW.matcher(sql);
        while (m.find()) {
            if (functionId.equals(m.group(2))) {
                return true;
            }
        }
        return false;
    }

    @Test
    void seed_declares_snapshot_url_as_linkable_function() throws IOException {
        String sql = seedSql();
        String functionId = functionIdForUrl(sql, SNAPSHOT_URL);
        assertNotNull(functionId, "种子缺少快照端点资源行: " + SNAPSHOT_URL);
        assertEquals(SNAPSHOT_FUNCTION_ID, functionId,
                "快照端点 function_id 必须是 " + SNAPSHOT_FUNCTION_ID + "（独立非菜单资源行）");
        assertTrue(sql.contains("NULL, 2, '待处理积压一致快照（巡检）'"),
                "资源行必须是 functiontype=1 的链接资源（functionlevel=2），不参与菜单");
    }

    @Test
    void seed_binds_snapshot_endpoint_to_dynamic_insp_read_only() throws IOException {
        String sql = seedSql();
        assertTrue(hasInspectBinding(sql, SNAPSHOT_FUNCTION_ID),
                "快照端点必须绑定动态 insp_read 角色");
        String code = stripComments(sql);
        assertTrue(code.contains("`rolecode` = 'insp_read'"), "必须按 rolecode 动态查询 insp_read");
        assertFalse(code.matches("(?s).*\\bDELETE\\b.*"), "纯增量种子不得包含任何 DELETE");
        assertFalse(code.contains("MENU-"), "种子不得触碰任何 MENU-* 菜单授权");
        // 不硬编码角色 ID：只允许通过 @insp_read_role_id 变量绑定
        assertFalse(code.matches("(?s).*'RF-DASH-PEND-SNAPSHOT-INSPECT'\\s*,\\s*'FN-DASH-PEND-SNAPSHOT'\\s*,\\s*'[^@].*"),
                "绑定行不得硬编码角色 ID，必须使用 @insp_read_role_id");
    }

    @Test
    void generated_resource_roles_contain_snapshot_url_with_insp_read() throws IOException {
        String sql = seedSql();
        String functionId = functionIdForUrl(sql, SNAPSHOT_URL);
        assertNotNull(functionId, "AUTH:RESOURCE_ROLES 必须包含快照 URL，否则网关 loadRolesByUrlPath 返回 null");
        List<String> roles = hasInspectBinding(sql, functionId)
                ? Collections.singletonList(INSPECT_ROLE_CODE)
                : Collections.<String>emptyList();
        assertTrue(roles.contains(INSPECT_ROLE_CODE), "快照端点角色集合必须含 insp_read: " + roles);
    }
}
