package com.zeroone.star.daycheck;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 巡检分页端点 /daycheck/no-up/get-no-up-goods-page 的资源-角色映射种子契约测试（JDK8 兼容）。
 *
 * 不依赖 Nacos/MySQL/Redis：只读取仓库内提交的种子 SQL，按 oauth2 侧真实链路
 * ResourcesServiceImpl.listAllLinkUrl(functiontype=1) -> TSRoleMapper.selectRoleByFunctionUrl
 * -> AUTH:RESOURCE_ROLES(url -> rolecodes) -> 网关 LoadResourcesDataImpl.loadRolesByUrlPath
 * 的语义，静态还原映射并断言：
 * 1) 新/旧端点 URL 有显式 t_s_function 资源行（functiontype=1，可被 listAllLinkUrl 加载）；
 * 2) 资源行仅增量绑定 insp_read 角色（动态 rolecode 查询、冲突 SIGNAL、无 DELETE）；
 * 3) 生成的 AUTH:RESOURCE_ROLES 映射中两个端点值均含 insp_read（不走 obj==null 不确定分支）。
 */
class NoUpPageResourceRoleSeedTest {

    private static final String PAGE_URL = "/daycheck/no-up/get-no-up-goods-page";
    private static final String LEGACY_URL = "/daycheck/no-up/get-no-up-goods";
    private static final String PAGE_FUNCTION_ID = "FN-DAYCHECK-NO-UP-PAGE";
    private static final String LEGACY_FUNCTION_ID = "FN-DAYCHECK-NO-UP-LEGACY";
    private static final String INSPECT_ROLE_CODE = "insp_read";

    private static final String SEED_RELATIVE = "documents/02、项目需求/数据库/seed_daycheck_no_up_goods_page_role.sql";

    // (FN-...ID) 后紧跟（可跨行）一个 /daycheck/no-up/... URL 的 INSERT..SELECT 资源行
    private static final Pattern FUNCTION_ROW = Pattern.compile(
            "'(FN-DAYCHECK-NO-UP-[A-Z]+)'[^;]*?'(/daycheck/no-up/[^']+)'", Pattern.DOTALL);
    // 绑定行：(RF-...ID, FN-...ID, @insp_read_role_id)
    private static final Pattern BINDING_ROW = Pattern.compile(
            "'(RF-DAYCHECK-NO-UP-[A-Z]+-INSPECT)'\\s*,\\s*'(FN-DAYCHECK-NO-UP-[A-Z]+)'\\s*,\\s*@insp_read_role_id");

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

    /** 还原 t_s_function 中 URL -> functionId 的映射（本种子只插 functiontype=1 的链接资源行）。 */
    private static Map<String, String> functionRows(String sql) {
        Map<String, String> urlToId = new LinkedHashMap<>();
        Matcher m = FUNCTION_ROW.matcher(sql);
        while (m.find()) {
            urlToId.put(m.group(2), m.group(1));
        }
        return urlToId;
    }

    /** 还原 t_s_role_function 中 functionId -> roleId 的绑定（本种子只新增 insp_read 绑定）。 */
    private static Map<String, List<String>> roleBindings(String sql) {
        Map<String, List<String>> functionIdToRoleIds = new HashMap<>();
        Matcher m = BINDING_ROW.matcher(sql);
        while (m.find()) {
            String functionId = m.group(2);
            List<String> roleIds = functionIdToRoleIds.get(functionId);
            if (roleIds == null) {
                roleIds = new ArrayList<>();
                functionIdToRoleIds.put(functionId, roleIds);
            }
            // @insp_read_role_id 动态取自 rolecode=insp_read 的唯一行
            if (!roleIds.contains("@insp_read_role_id")) {
                roleIds.add("@insp_read_role_id");
            }
        }
        return functionIdToRoleIds;
    }

    /** 去掉 -- 行注释后再做关键字检查，避免注释里的“DELETE/MENU-DAILY-CHECK”字样误判。 */
    private static String stripComments(String sql) {
        StringBuilder sb = new StringBuilder();
        for (String line : sql.split("\\r?\\n")) {
            String t = line.trim();
            if (t.startsWith("--")) {
                continue;
            }
            sb.append(line).append('\n');
        }
        return sb.toString();
    }

    /** 按 ResourcesServiceImpl 的语义静态还原 AUTH:RESOURCE_ROLES(url -> rolecodes)。 */
    private static Map<String, List<String>> buildResourceRoles(String sql) {
        String code = stripComments(sql);
        // 动态 rolecode 查询必须存在，且不再硬编码角色 ID 赋值
        assertTrue(code.contains("`rolecode` = 'insp_read'"),
                "种子必须按 rolecode 动态查询 insp_read 角色");
        assertTrue(code.contains("SIGNAL SQLSTATE '45000'"),
                "角色 ID 不唯一或 URL/ID 冲突时必须 SIGNAL 中止");
        assertFalse(code.matches("(?s).*\\bDELETE\\b.*"),
                "纯增量种子不得包含任何 DELETE（旧端点权限只增不减）");
        assertFalse(code.contains("MENU-DAILY-CHECK"),
                "种子不得触碰 MENU-DAILY-CHECK-04/05 菜单授权");

        Map<String, String> urlToId = functionRows(sql);
        Map<String, List<String>> functionIdToRoleIds = roleBindings(sql);
        Map<String, List<String>> resourceRoles = new LinkedHashMap<>();
        for (Map.Entry<String, String> entry : urlToId.entrySet()) {
            List<String> roleIds = functionIdToRoleIds.get(entry.getValue());
            List<String> codes = new ArrayList<>();
            if (roleIds != null) {
                for (String roleId : roleIds) {
                    if ("@insp_read_role_id".equals(roleId)) {
                        codes.add(INSPECT_ROLE_CODE);
                    }
                }
            }
            resourceRoles.put(entry.getKey(), codes);
        }
        return resourceRoles;
    }

    @Test
    void seed_declares_page_url_as_linkable_function() throws IOException {
        String sql = seedSql();
        Map<String, String> rows = functionRows(sql);
        assertTrue(rows.containsKey(PAGE_URL), "种子缺少新端点资源行: " + PAGE_URL);
        assertEquals(PAGE_FUNCTION_ID, rows.get(PAGE_URL),
                "新端点 function_id 必须是 " + PAGE_FUNCTION_ID + "（独立非菜单资源行）");
        assertTrue(rows.containsKey(LEGACY_URL), "种子缺少旧端点资源行: " + LEGACY_URL);
        assertEquals(LEGACY_FUNCTION_ID, rows.get(LEGACY_URL),
                "旧端点 function_id 必须是 " + LEGACY_FUNCTION_ID + "（独立非菜单资源行）");
    }

    @Test
    void seed_binds_page_and_legacy_endpoint_to_insp_read() throws IOException {
        String sql = seedSql();
        Map<String, List<String>> bindings = roleBindings(sql);
        assertEquals(Collections.singletonList("@insp_read_role_id"), bindings.get(PAGE_FUNCTION_ID),
                "新端点必须绑定动态 insp_read 角色");
        assertEquals(Collections.singletonList("@insp_read_role_id"), bindings.get(LEGACY_FUNCTION_ID),
                "旧端点必须绑定动态 insp_read 角色（角色集合与新端点一致）");
    }

    @Test
    void generated_resource_roles_contain_page_url_with_insp_read() throws IOException {
        Map<String, List<String>> resourceRoles = buildResourceRoles(seedSql());
        List<String> pageRoles = resourceRoles.get(PAGE_URL);
        assertNotNull(pageRoles, "AUTH:RESOURCE_ROLES 必须包含新端点 URL，否则网关返回 null");
        assertFalse(pageRoles.isEmpty(), "新端点角色集合不能为空");
        assertTrue(pageRoles.contains(INSPECT_ROLE_CODE), "新端点角色集合必须含 insp_read: " + pageRoles);
        assertEquals(resourceRoles.get(LEGACY_URL), pageRoles,
                "巡检分页端点与旧端点必须拥有相同角色集合");
    }
}
