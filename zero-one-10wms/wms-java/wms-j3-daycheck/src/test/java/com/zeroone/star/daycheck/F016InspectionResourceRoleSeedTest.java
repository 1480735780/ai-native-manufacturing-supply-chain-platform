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
 * F-016 巡检端点资源-角色映射种子契约测试（JDK8 兼容）。
 *
 * 不依赖 Nacos/MySQL/Redis：只读取仓库内提交的种子 SQL，按 oauth2 侧真实链路
 * ResourcesServiceImpl.listAllLinkUrl(functiontype=1) -> TSRoleMapper.selectRoleByFunctionUrl
 * -> AUTH:RESOURCE_ROLES(url -> rolecodes) -> 网关 LoadResourcesDataImpl.loadRolesByUrlPath
 * 的语义，静态还原映射并断言三个端点均被登记为可加载的链接资源，且角色集合符合下列口径：
 * <ul>
 *   <li>仅巡检使用的分页端点：只绑 insp_read；</li>
 *   <li>页面与巡检共用的端点（出货异常旧端点、温度查询）：insp_read ∪ 对应页面菜单的既有授权角色，
 *       否则网关启用资源角色校验后会对页面现有用户返回 403。</li>
 * </ul>
 * 另守护：insp_read 按 rolecode 动态查询、冲突 SIGNAL、无 DELETE、不改写任何 MENU-* 行、
 * 所有资源/绑定 ID 长度 <= 32（t_s_function.ID / t_s_role_function.ID 均为 varchar(32)）。
 */
class F016InspectionResourceRoleSeedTest {

    private static final String OUTBOUND_PAGE_URL = "/daycheck/yi-chang/get-yichang-down-page";
    private static final String OUTBOUND_LEGACY_URL = "/daycheck/yi-chang/get-yichang-down";
    private static final String TEMPERATURE_URL = "/daycheck/temperature/query";

    private static final String OUTBOUND_PAGE_FUNCTION_ID = "FN-DAYCHECK-YICHANG-PAGE";
    private static final String OUTBOUND_LEGACY_FUNCTION_ID = "FN-DAYCHECK-YICHANG-LEGACY";
    private static final String TEMPERATURE_FUNCTION_ID = "FN-DAYCHECK-TEMPERATURE-QUERY";
    private static final String OUTBOUND_PAGE_BINDING_ID = "RF-YC-PAGE-INSPECT";
    private static final String OUTBOUND_LEGACY_BINDING_ID = "RF-YC-LEGACY-INSPECT";
    private static final String TEMPERATURE_BINDING_ID = "RF-TEMP-Q-INSPECT";
    private static final String INSPECT_ROLE_CODE = "insp_read";

    /** 共用端点对应的页面菜单：端点角色集合 = 页面菜单既有授权角色 ∪ insp_read。 */
    private static final String OUTBOUND_PAGE_MENU_ID = "MENU-DAILY-CHECK-02";
    private static final String TEMPERATURE_PAGE_MENU_ID = "MENU-DAILY-CHECK-03";
    private static final String OUTBOUND_LEGACY_BINDING_PREFIX = "RF-YC-LEGACY-";
    private static final String TEMPERATURE_BINDING_PREFIX = "RF-TEMP-Q-";
    private static final String INSPECT_BINDING_SUFFIX = "INSPECT";
    /** rolecode 的长度上限：最长前缀 13 字符 + 16 + 余量必须 <= 32。 */
    private static final int MAX_ROLECODE_LENGTH = 16;
    private static final int ID_MAX_LENGTH = 32;

    private static final String SEED_RELATIVE = "documents/02、项目需求/数据库/seed_daycheck_f016_inspection_role.sql";

    // (FN-...ID) 后紧跟（可跨行）一个 /daycheck/... URL 的 INSERT..SELECT 资源行
    private static final Pattern FUNCTION_ROW = Pattern.compile(
            "'(FN-DAYCHECK-[A-Z-]+)'[^;]*?'(/daycheck/[^']+)'", Pattern.DOTALL);
    // insp_read 绑定行：(RF-...ID, FN-...ID, @insp_read_role_id)
    // 绑定 ID 已缩短以适配 t_s_role_function.ID varchar(32)，不再以 RF-DAYCHECK- 开头。
    private static final Pattern BINDING_ROW = Pattern.compile(
            "'(RF-[A-Z0-9-]+)'\\s*,\\s*'(FN-DAYCHECK-[A-Z-]+)'\\s*,\\s*@insp_read_role_id");
    // 页面角色绑定行：绑定 ID 由前缀 + rolecode 拼出，角色取自页面菜单，且带「函数+角色」幂等守卫
    private static final Pattern PAGE_ROLE_BINDING_ROW = Pattern.compile(
            "SELECT DISTINCT CONCAT\\('(RF-[A-Z0-9-]+)', UPPER\\(r\\.`rolecode`\\)\\),\\s*"
                    + "'(FN-DAYCHECK-[A-Z-]+)',\\s*mr\\.`roleid`\\s+"
                    + "FROM `t_s_role_function` mr\\s+JOIN `t_s_role` r ON r\\.`ID` = mr\\.`roleid`\\s+"
                    + "WHERE mr\\.`functionid` = '(MENU-[A-Z0-9-]+)'\\s+AND NOT EXISTS \\(\\s*"
                    + "SELECT 1 FROM `t_s_role_function` x\\s+"
                    + "WHERE x\\.`functionid` = '(FN-DAYCHECK-[A-Z-]+)' AND x\\.`roleid` = mr\\.`roleid`\\)");
    // 所有字面量资源 ID / 绑定 ID：用于 varchar(32) 长度守卫
    private static final Pattern ANY_FUNCTION_ID = Pattern.compile("'((?:FN|RF)-[A-Z0-9-]+)'");

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
        throw new IOException("找不到 F-016 资源角色种子 SQL，尝试过: " + candidates);
    }

    private static Map<String, String> functionRows(String sql) {
        Map<String, String> urlToId = new LinkedHashMap<>();
        Matcher m = FUNCTION_ROW.matcher(sql);
        while (m.find()) {
            urlToId.put(m.group(2), m.group(1));
        }
        return urlToId;
    }

    /**
     * function id -> 角色来源列表。先列字面量 insp_read 绑定（记为 "@insp_read_role_id"），
     * 再列页面角色绑定（记为对应的页面菜单 ID）。
     */
    private static Map<String, List<String>> roleBindings(String sql) {
        Map<String, List<String>> functionIdToRoles = new HashMap<>();
        Matcher literal = BINDING_ROW.matcher(sql);
        while (literal.find()) {
            List<String> roles = functionIdToRoles.computeIfAbsent(literal.group(2), k -> new ArrayList<>());
            if (!roles.contains("@insp_read_role_id")) {
                roles.add("@insp_read_role_id");
            }
        }
        Matcher page = PAGE_ROLE_BINDING_ROW.matcher(sql);
        while (page.find()) {
            List<String> roles = functionIdToRoles.computeIfAbsent(page.group(2), k -> new ArrayList<>());
            if (!roles.contains(page.group(3))) {
                roles.add(page.group(3));
            }
        }
        return functionIdToRoles;
    }

    /** 去掉 -- 行注释后再做关键字检查，避免注释里的 DELETE/MENU 字样误判。 */
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

    /** MENU-* 只允许出现在读取位置：不得作为写语句的目标或写入值。 */
    private static void assertMenuRowsAreOnlyRead(String code) {
        for (String statement : code.split(";")) {
            if (!statement.contains("MENU-")) {
                continue;
            }
            assertFalse(Pattern.compile("(?is)\\b(UPDATE|DELETE|ALTER|DROP|TRUNCATE|REPLACE|CREATE|GRANT)\\b")
                            .matcher(statement).find(),
                    "种子不得改写任何 MENU-* 菜单授权: " + statement.trim());
            Matcher insert = Pattern.compile("(?is)INSERT\\s+INTO\\s+`?(\\w+)`?").matcher(statement);
            if (insert.find()) {
                assertEquals("t_s_role_function", insert.group(1),
                        "涉及 MENU-* 的写语句只能是向 t_s_role_function 追加端点绑定");
                int from = statement.indexOf("FROM");
                assertTrue(from > 0, "页面角色绑定必须是 INSERT ... SELECT ... FROM: " + statement.trim());
                assertFalse(statement.substring(0, from).contains("MENU-"),
                        "MENU-* 只能出现在读取条件里，不得作为写入值: " + statement.trim());
            }
        }
    }

    /** 按 ResourcesServiceImpl 的语义静态还原 AUTH:RESOURCE_ROLES(url -> rolecodes)。 */
    private static Map<String, List<String>> buildResourceRoles(String sql) {
        String code = stripComments(sql);
        assertTrue(code.contains("`rolecode` = 'insp_read'"),
                "种子必须按 rolecode 动态查询 insp_read 角色");
        assertTrue(code.contains("SIGNAL SQLSTATE '45000'"),
                "角色 ID 不唯一或 URL/ID 冲突时必须 SIGNAL 中止");
        assertFalse(code.matches("(?s).*\\bDELETE\\b.*"),
                "纯增量种子不得包含任何 DELETE（旧端点权限只增不减）");
        assertMenuRowsAreOnlyRead(code);

        Map<String, String> urlToId = functionRows(sql);
        Map<String, List<String>> functionIdToRoles = roleBindings(sql);
        Map<String, List<String>> resourceRoles = new LinkedHashMap<>();
        for (Map.Entry<String, String> entry : urlToId.entrySet()) {
            List<String> roles = functionIdToRoles.get(entry.getValue());
            List<String> codes = new ArrayList<>();
            if (roles != null) {
                for (String role : roles) {
                    codes.add("@insp_read_role_id".equals(role) ? INSPECT_ROLE_CODE : "page:" + role);
                }
            }
            resourceRoles.put(entry.getKey(), codes);
        }
        return resourceRoles;
    }

    @Test
    void seed_declares_all_f016_urls_as_linkable_functions() throws IOException {
        Map<String, String> rows = functionRows(seedSql());
        assertEquals(OUTBOUND_PAGE_FUNCTION_ID, rows.get(OUTBOUND_PAGE_URL),
                "出货异常新分页端点必须是独立非菜单资源行");
        assertEquals(OUTBOUND_LEGACY_FUNCTION_ID, rows.get(OUTBOUND_LEGACY_URL),
                "出货异常旧端点必须是独立非菜单资源行");
        assertEquals(TEMPERATURE_FUNCTION_ID, rows.get(TEMPERATURE_URL),
                "温度查询端点必须是独立非菜单资源行");
    }

    @Test
    void seed_binds_all_endpoints_to_insp_read() throws IOException {
        String sql = seedSql();
        // 绑定 ID 匹配新短 ID，且每个端点都有 insp_read 的字面量绑定
        Matcher bindingMatcher = BINDING_ROW.matcher(sql);
        Map<String, String> functionIdToBindingId = new HashMap<>();
        while (bindingMatcher.find()) {
            functionIdToBindingId.put(bindingMatcher.group(2), bindingMatcher.group(1));
        }
        assertEquals(OUTBOUND_PAGE_BINDING_ID, functionIdToBindingId.get(OUTBOUND_PAGE_FUNCTION_ID));
        assertEquals(OUTBOUND_LEGACY_BINDING_ID, functionIdToBindingId.get(OUTBOUND_LEGACY_FUNCTION_ID));
        assertEquals(TEMPERATURE_BINDING_ID, functionIdToBindingId.get(TEMPERATURE_FUNCTION_ID));
    }

    @Test
    void shared_endpoints_derive_page_roles_from_their_menus() throws IOException {
        Map<String, List<String>> bindings = roleBindings(seedSql());
        assertEquals(Collections.singletonList("@insp_read_role_id"), bindings.get(OUTBOUND_PAGE_FUNCTION_ID),
                "仅巡检使用的分页端点不得绑定页面角色");
        assertEquals(Arrays.asList("@insp_read_role_id", OUTBOUND_PAGE_MENU_ID),
                bindings.get(OUTBOUND_LEGACY_FUNCTION_ID),
                "出货异常旧端点 = insp_read ∪ 出货异常页面菜单角色");
        assertEquals(Arrays.asList("@insp_read_role_id", TEMPERATURE_PAGE_MENU_ID),
                bindings.get(TEMPERATURE_FUNCTION_ID),
                "温度查询端点 = insp_read ∪ 温度维护页面菜单角色");

        // 页面角色绑定行：前缀、菜单、幂等守卫都指向本端点
        Matcher page = PAGE_ROLE_BINDING_ROW.matcher(seedSql());
        int rows = 0;
        while (page.find()) {
            rows++;
            assertEquals(page.group(2), page.group(4),
                    "页面角色绑定的幂等守卫必须按本端点的 functionid 判断");
            assertTrue(page.group(1).length() + MAX_ROLECODE_LENGTH <= ID_MAX_LENGTH,
                    "前缀 + rolecode 上限会超出 varchar(32): " + page.group(1));
            String expectedPrefix;
            String expectedMenu;
            if (OUTBOUND_LEGACY_FUNCTION_ID.equals(page.group(2))) {
                expectedPrefix = OUTBOUND_LEGACY_BINDING_PREFIX;
                expectedMenu = OUTBOUND_PAGE_MENU_ID;
            } else {
                expectedPrefix = TEMPERATURE_BINDING_PREFIX;
                expectedMenu = TEMPERATURE_PAGE_MENU_ID;
            }
            assertEquals(expectedPrefix, page.group(1), "绑定 ID 前缀与端点不匹配");
            assertEquals(expectedMenu, page.group(3), "页面菜单与端点不匹配");
        }
        assertEquals(2, rows, "应有出货异常旧端点、温度查询两条页面角色绑定");

        // insp_read 绑定 ID 的后缀不得与任何 rolecode 拼出的 ID 相同（insp_read 不是页面角色时才成立，
        // 这里只守护前缀 + INSPECT 后缀本身不超长）
        assertTrue((OUTBOUND_LEGACY_BINDING_PREFIX + INSPECT_BINDING_SUFFIX).length() <= ID_MAX_LENGTH);
        assertTrue((TEMPERATURE_BINDING_PREFIX + INSPECT_BINDING_SUFFIX).length() <= ID_MAX_LENGTH);
    }

    @Test
    void all_resource_and_binding_ids_fit_varchar32() throws IOException {
        Matcher m = ANY_FUNCTION_ID.matcher(seedSql());
        int checked = 0;
        while (m.find()) {
            String id = m.group(1);
            assertTrue(id.length() <= 32,
                    "t_s_function/t_s_role_function.ID 为 varchar(32)，ID 超长: " + id + " (" + id.length() + ")");
            checked++;
        }
        assertTrue(checked >= 6, "应至少检出 3 个资源 ID 与 3 个绑定 ID，实际: " + checked);
    }

    @Test
    void generated_resource_roles_contain_all_urls_with_insp_read() throws IOException {
        Map<String, List<String>> resourceRoles = buildResourceRoles(seedSql());
        for (String url : Arrays.asList(OUTBOUND_PAGE_URL, OUTBOUND_LEGACY_URL, TEMPERATURE_URL)) {
            List<String> roles = resourceRoles.get(url);
            assertNotNull(roles, "AUTH:RESOURCE_ROLES 必须包含端点 URL，否则网关返回 null: " + url);
            assertFalse(roles.isEmpty(), "端点角色集合不能为空: " + url);
            assertTrue(roles.contains(INSPECT_ROLE_CODE), "端点角色集合必须含 insp_read: " + url + " -> " + roles);
        }
        assertEquals(Collections.singletonList(INSPECT_ROLE_CODE), resourceRoles.get(OUTBOUND_PAGE_URL),
                "仅巡检使用的分页端点只能有 insp_read");
        assertTrue(resourceRoles.get(OUTBOUND_LEGACY_URL).contains("page:" + OUTBOUND_PAGE_MENU_ID),
                "出货异常旧端点必须包含出货异常页面菜单的角色");
        assertTrue(resourceRoles.get(TEMPERATURE_URL).contains("page:" + TEMPERATURE_PAGE_MENU_ID),
                "温度查询端点必须包含温度维护页面菜单的角色");
    }

    @Test
    void seed_preflights_functiontype_for_all_ids_and_urls() throws IOException {
        String code = stripComments(seedSql());
        // 审计 m01902：预检必须先按「行是否存在」判断，再校验 functionurl/functiontype。
        // 旧写法用 `IS NOT NULL` 过滤，既有行 functionurl/functiontype 为 NULL 时预检全部跳过、
        // INSERT ... WHERE NOT EXISTS 也不写，却照旧绑定角色并 COMMIT —— 种子"成功"但 OAuth 加载不到。
        String[] ids = {OUTBOUND_PAGE_FUNCTION_ID, OUTBOUND_LEGACY_FUNCTION_ID, TEMPERATURE_FUNCTION_ID};
        String[] urls = {OUTBOUND_PAGE_URL, OUTBOUND_LEGACY_URL, TEMPERATURE_URL};
        for (String id : ids) {
            // 1) 先查存在性（COUNT(*)，不附加任何 WHERE 值过滤）
            assertTrue(Pattern.compile("SELECT COUNT\\(\\*\\) INTO v_exists FROM `t_s_function`\\s+"
                    + "WHERE `ID` = '" + Pattern.quote(id) + "'").matcher(code).find(),
                    "缺少 ID 的存在性预检: " + id);
            // 2) 存在时再读 functionurl/functiontype 并校验
            assertTrue(Pattern.compile("SELECT `functionurl`, `functiontype` INTO v_probe, v_probe_type").matcher(code).find(),
                    "缺少 functionurl/functiontype 读取: " + id);
            assertTrue(code.contains(id + " exists but functiontype is NULL or <>1"),
                    "缺少 ID 的 functiontype 不可激活 SIGNAL: " + id);
        }
        for (String url : urls) {
            // URL 占用检测同样先查存在性，再校验该 URL 下所有行的 functiontype 都必须为 1
            assertTrue(Pattern.compile("SELECT COUNT\\(\\*\\) INTO v_exists FROM `t_s_function`\\s+"
                    + "WHERE `functionurl` = '" + Pattern.quote(url) + "'").matcher(code).find(),
                    "缺少 URL 的存在性预检: " + url);
            assertTrue(Pattern.compile("SELECT COUNT\\(\\*\\) INTO v_exists FROM `t_s_function`\\s+"
                    + "WHERE `functionurl` = '" + Pattern.quote(url) + "'\\s+"
                    + "AND \\(`functiontype` IS NULL OR `functiontype` <> 1\\)").matcher(code).find(),
                    "缺少 URL 下 functiontype<>1/NULL 的检测: " + url);
            assertTrue(code.contains(url + " exists but functiontype is NULL or <>1"),
                    "缺少 URL 的 functiontype 不可激活 SIGNAL: " + url);
        }
        // 旧写法（IS NOT NULL 过滤）必须彻底消失，否则 NULL 坏行仍会被当成"不存在"
        assertFalse(code.contains("WHERE `functionurl` IS NOT NULL AND `functiontype` <> 1"),
                "不得再用 IS NOT NULL 过滤做预检（会让 NULL 坏行假成功）");
    }

    @Test
    void seed_preflights_shared_endpoint_menu_roles() throws IOException {
        String code = stripComments(seedSql());
        // 共用端点的页面菜单必须存在，否则无法推导页面角色（退化为只绑 insp_read 会让页面用户 403）
        for (String menu : new String[] {OUTBOUND_PAGE_MENU_ID, TEMPERATURE_PAGE_MENU_ID}) {
            assertTrue(Pattern.compile("SELECT COUNT\\(\\*\\) INTO v_exists FROM `t_s_function`\\s+"
                    + "WHERE `ID` = '" + Pattern.quote(menu) + "'").matcher(code).find(),
                    "缺少页面菜单的存在性预检: " + menu);
            assertTrue(code.contains(menu + " not found"),
                    "缺少页面菜单缺失的 SIGNAL: " + menu);
        }
        // rolecode 过长会让拼出的绑定 ID 超出 varchar(32)：必须中止而不是被截断
        assertTrue(code.contains("CHAR_LENGTH(r.`rolecode`) > " + MAX_ROLECODE_LENGTH),
                "缺少 rolecode 长度守卫");
        assertTrue(code.contains("derived binding id would exceed varchar(32)"),
                "缺少 rolecode 过长的 SIGNAL");
        // 拼出的绑定 ID 前缀被别的函数占用（或 functionid 为 NULL）-> 中止
        for (String prefix : new String[] {"RF-YC-LEGACY-*", "RF-TEMP-Q-*"}) {
            assertTrue(code.contains("an " + prefix + " binding exists but functionid is NULL or a different function"),
                    "缺少绑定 ID 前缀冲突的 SIGNAL: " + prefix);
        }
        assertTrue(Pattern.compile("`ID` LIKE 'RF-YC-LEGACY-%'\\s+AND \\(`functionid` IS NULL OR `functionid` <> '"
                + Pattern.quote(OUTBOUND_LEGACY_FUNCTION_ID) + "'\\)").matcher(code).find(),
                "RF-YC-LEGACY-* 前缀冲突预检必须先容忍 NULL 再比对 functionid");
        assertTrue(Pattern.compile("`ID` LIKE 'RF-TEMP-Q-%'\\s+AND \\(`functionid` IS NULL OR `functionid` <> '"
                + Pattern.quote(TEMPERATURE_FUNCTION_ID) + "'\\)").matcher(code).find(),
                "RF-TEMP-Q-* 前缀冲突预检必须先容忍 NULL 再比对 functionid");
    }

    @Test
    void seed_preflights_binding_id_conflicts_and_wraps_inserts_in_transaction() throws IOException {
        String code = stripComments(seedSql());
        String[] bindings = {OUTBOUND_LEGACY_BINDING_ID, OUTBOUND_PAGE_BINDING_ID, TEMPERATURE_BINDING_ID};
        String[] bindingFunctions = {OUTBOUND_LEGACY_FUNCTION_ID, OUTBOUND_PAGE_FUNCTION_ID, TEMPERATURE_FUNCTION_ID};
        for (int i = 0; i < bindings.length; i++) {
            // 绑定同样先查存在性，再校验 functionid 与归属角色
            assertTrue(Pattern.compile("SELECT COUNT\\(\\*\\) INTO v_exists FROM `t_s_role_function`\\s+"
                    + "WHERE `ID` = '" + Pattern.quote(bindings[i]) + "'").matcher(code).find(),
                    "缺少绑定 ID 的存在性预检: " + bindings[i]);
            assertTrue(Pattern.compile("SELECT `functionid` INTO v_probe FROM `t_s_role_function`").matcher(code).find(),
                    "缺少绑定 functionid 读取: " + bindings[i]);
            assertTrue(code.contains(bindings[i] + " binding exists but functionid is NULL or a different function"),
                    "缺少绑定 ID 冲突的 SIGNAL 消息: " + bindings[i]);
            assertTrue(code.contains("v_probe <> '" + bindingFunctions[i] + "'"),
                    "绑定 ID 预检未与期望 function id 比对: " + bindings[i]);
            assertTrue(code.contains(bindings[i] + " binding exists but is not bound to rolecode=insp_read"),
                    "缺少绑定越权的 SIGNAL 消息: " + bindings[i]);
        }
        // 事务与异常处理：所有 INSERT 必须在 START TRANSACTION / COMMIT 之间，
        // 并且有 EXIT HANDLER 做 ROLLBACK + RESIGNAL。
        assertTrue(code.contains("DECLARE EXIT HANDLER FOR SQLEXCEPTION"), "缺少 EXIT HANDLER");
        assertTrue(code.contains("ROLLBACK;"), "EXIT HANDLER 必须 ROLLBACK");
        assertTrue(code.contains("RESIGNAL;"), "EXIT HANDLER 必须 RESIGNAL");
        int start = code.indexOf("START TRANSACTION;");
        int commit = code.indexOf("COMMIT;");
        int firstInsert = code.indexOf("INSERT INTO `t_s_function`");
        int lastInsert = code.lastIndexOf("INSERT INTO `t_s_role_function`");
        assertTrue(start >= 0, "INSERT 序列前必须有 START TRANSACTION");
        assertTrue(commit >= 0, "INSERT 序列后必须有 COMMIT");
        assertTrue(start < firstInsert && firstInsert < commit,
                "所有 INSERT 必须位于 START TRANSACTION 与 COMMIT 之间");
        assertTrue(start < lastInsert && lastInsert < commit,
                "页面角色绑定 INSERT 也必须位于 START TRANSACTION 与 COMMIT 之间");
    }
}
