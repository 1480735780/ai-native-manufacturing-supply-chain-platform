package com.zeroone.star.daycheck;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
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
 * 异常巡检 Agent 与页面共用数据源端点的资源-角色映射种子契约测试（ADR-021 收尾，JDK8 兼容）。
 *
 * 不依赖 Nacos/MySQL/Redis：只读取仓库内提交的种子 SQL，按 oauth2 侧真实链路
 * ResourcesServiceImpl.listAllLinkUrl(functiontype=1) -> TSRoleMapper.selectRoleByFunctionUrl
 * -> AUTH:RESOURCE_ROLES(url -> rolecodes) -> 网关 LoadResourcesDataImpl.loadRolesByUrlPath
 * 的语义，静态还原映射并断言：
 * <ul>
 *   <li>/daycheck/delay/im-delay 与 /stock/expiry-warning/query-all 均被登记为可加载的链接资源，
 *       登记后巡检 Agent 经网关调用的 6 个数据源端点全部有资源角色映射；</li>
 *   <li>两个端点都是页面与巡检共用：角色集合 = 页面菜单既有授权角色 ∪ insp_read，
 *       页面菜单按前端路由（functionurl）查找而不是写死菜单 ID，同一页面挂在多个菜单下时角色取并集。</li>
 * </ul>
 * 另守护：insp_read 按 rolecode 动态查询、冲突 SIGNAL、无 DELETE、不引用任何 MENU-* 字面量、
 * 所有资源/绑定 ID 长度 <= 32（t_s_function.ID / t_s_role_function.ID 均为 varchar(32)）。
 */
class AgentSharedSourceResourceRoleSeedTest {

    private static final String DELAY_URL = "/daycheck/delay/im-delay";
    private static final String EXPIRY_URL = "/stock/expiry-warning/query-all";

    private static final String DELAY_FUNCTION_ID = "FN-DAYCHECK-DELAY-IM-DELAY";
    private static final String EXPIRY_FUNCTION_ID = "FN-STOCK-EXPIRY-QUERY-ALL";
    private static final String DELAY_BINDING_ID = "RF-DELAY-IM-INSPECT";
    private static final String EXPIRY_BINDING_ID = "RF-EXP-QALL-INSPECT";
    private static final String INSPECT_ROLE_CODE = "insp_read";

    /** 共用端点对应的页面路由：端点角色集合 = 该路由下所有页面菜单的既有授权角色 ∪ insp_read。 */
    private static final String DELAY_PAGE_ROUTE = "/daily-check/shipment-delay-warn";
    private static final String EXPIRY_PAGE_ROUTE = "/customer-report/validity-warn";
    private static final String DELAY_BINDING_PREFIX = "RF-DELAY-IM-";
    private static final String EXPIRY_BINDING_PREFIX = "RF-EXP-QALL-";
    private static final String INSPECT_BINDING_SUFFIX = "INSPECT";
    /** rolecode 的长度上限：最长前缀 12 字符 + 16 + 余量必须 <= 32。 */
    private static final int MAX_ROLECODE_LENGTH = 16;
    private static final int ID_MAX_LENGTH = 32;

    private static final String SEED_RELATIVE = "documents/02、项目需求/数据库/seed_agent_shared_source_role.sql";

    // (FN-...ID) 后紧跟（可跨行）一个 API URL 的 INSERT..SELECT 资源行
    private static final Pattern FUNCTION_ROW = Pattern.compile(
            "'(FN-[A-Z-]+)'[^;]*?'(/(?:daycheck|stock)/[^']+)'", Pattern.DOTALL);
    // insp_read 绑定行：(RF-...ID, FN-...ID, @insp_read_role_id)
    private static final Pattern BINDING_ROW = Pattern.compile(
            "'(RF-[A-Z0-9-]+)'\\s*,\\s*'(FN-[A-Z-]+)'\\s*,\\s*@insp_read_role_id");
    // 页面角色绑定行：绑定 ID 由前缀 + rolecode 拼出，角色取自「按前端路由查到的页面菜单」，且带「函数+角色」幂等守卫
    private static final Pattern PAGE_ROLE_BINDING_ROW = Pattern.compile(
            "SELECT DISTINCT CONCAT\\('(RF-[A-Z0-9-]+)', UPPER\\(r\\.`rolecode`\\)\\),\\s*"
                    + "'(FN-[A-Z-]+)',\\s*mr\\.`roleid`\\s+"
                    + "FROM `t_s_role_function` mr\\s+JOIN `t_s_role` r ON r\\.`ID` = mr\\.`roleid`\\s+"
                    + "WHERE mr\\.`functionid` IN \\(\\s+SELECT `ID` FROM `t_s_function`\\s+"
                    + "WHERE `functionurl` = '(/[^']+)'" + "\\)\\s+AND NOT EXISTS \\(\\s*"
                    + "SELECT 1 FROM `t_s_role_function` x\\s+"
                    + "WHERE x\\.`functionid` = '(FN-[A-Z-]+)' AND x\\.`roleid` = mr\\.`roleid`\\)");
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
        throw new IOException("找不到巡检共用数据源资源角色种子 SQL，尝试过: " + candidates);
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
     * 再列页面角色绑定（记为对应的页面路由）。
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
            if (line.trim().startsWith("--")) {
                continue;
            }
            sb.append(line).append('\n');
        }
        return sb.toString();
    }

    /** 按 ResourcesServiceImpl 的语义静态还原 AUTH:RESOURCE_ROLES(url -> rolecodes)。 */
    private static Map<String, List<String>> buildResourceRoles(String sql) {
        String code = stripComments(sql);
        assertTrue(code.contains("`rolecode` = 'insp_read'"),
                "种子必须按 rolecode 动态查询 insp_read 角色");
        assertTrue(code.contains("SIGNAL SQLSTATE '45000'"),
                "角色 ID 不唯一或 URL/ID 冲突时必须 SIGNAL 中止");
        assertFalse(Pattern.compile("(?is)\\bDELETE\\b").matcher(code).find(),
                "纯增量种子不得包含任何 DELETE（既有权限只增不减）");
        assertFalse(Pattern.compile("(?is)\\b(UPDATE|ALTER|DROP|TRUNCATE|REPLACE|CREATE|GRANT)\\s+(TABLE|MENU-)")
                .matcher(code).find(),
                "种子不得改写任何表或菜单授权");
        assertEquals(2, code.split("INSERT INTO `t_s_function`", -1).length - 1,
                "种子只应新增 2 条资源行");
        assertEquals(4, code.split("INSERT INTO `t_s_role_function`", -1).length - 1,
                "种子只应新增 2 条 insp_read 绑定与 2 条页面角色派生绑定");

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
    void seed_declares_both_shared_source_urls_as_linkable_functions() throws IOException {
        String code = stripComments(seedSql());
        for (String id : new String[] {DELAY_FUNCTION_ID, EXPIRY_FUNCTION_ID}) {
            // 资源行必须显式写 functiontype = 1，否则 OAuth 的 listAllLinkUrl 不会加载
            assertTrue(Pattern.compile("SELECT '" + Pattern.quote(id) + "', NULL, 2, '[^']+', '\\d+',\\s+"
                    + "'/[^']+', NULL, 1\\s+WHERE NOT EXISTS").matcher(code).find(),
                    "资源行必须以 functiontype=1 纯增量插入: " + id);
        }
        Map<String, String> rows = functionRows(seedSql());
        assertEquals(DELAY_FUNCTION_ID, rows.get(DELAY_URL), "进货延时端点必须是独立非菜单资源行");
        assertEquals(EXPIRY_FUNCTION_ID, rows.get(EXPIRY_URL), "效期预警端点必须是独立非菜单资源行");
        assertEquals(2, rows.size(), "种子只登记两个共用数据源端点");
    }

    @Test
    void seed_binds_both_endpoints_to_insp_read() throws IOException {
        String sql = seedSql();
        Matcher bindingMatcher = BINDING_ROW.matcher(sql);
        Map<String, String> functionIdToBindingId = new HashMap<>();
        while (bindingMatcher.find()) {
            functionIdToBindingId.put(bindingMatcher.group(2), bindingMatcher.group(1));
        }
        assertEquals(DELAY_BINDING_ID, functionIdToBindingId.get(DELAY_FUNCTION_ID));
        assertEquals(EXPIRY_BINDING_ID, functionIdToBindingId.get(EXPIRY_FUNCTION_ID));
    }

    @Test
    void shared_endpoints_derive_page_roles_from_page_routes() throws IOException {
        Map<String, List<String>> bindings = roleBindings(seedSql());
        assertEquals(Arrays.asList("@insp_read_role_id", DELAY_PAGE_ROUTE), bindings.get(DELAY_FUNCTION_ID),
                "进货延时端点 = insp_read ∪ 进货延时示警页面菜单角色");
        assertEquals(Arrays.asList("@insp_read_role_id", EXPIRY_PAGE_ROUTE), bindings.get(EXPIRY_FUNCTION_ID),
                "效期预警端点 = insp_read ∪ 效期预警页面菜单角色");

        // 页面角色绑定行：前缀、路由、幂等守卫都指向本端点
        Matcher page = PAGE_ROLE_BINDING_ROW.matcher(seedSql());
        int rows = 0;
        while (page.find()) {
            rows++;
            assertEquals(page.group(2), page.group(4),
                    "页面角色绑定的幂等守卫必须按本端点的 functionid 判断");
            assertTrue(page.group(1).length() + MAX_ROLECODE_LENGTH <= ID_MAX_LENGTH,
                    "前缀 + rolecode 上限会超出 varchar(32): " + page.group(1));
            String expectedPrefix;
            String expectedRoute;
            if (DELAY_FUNCTION_ID.equals(page.group(2))) {
                expectedPrefix = DELAY_BINDING_PREFIX;
                expectedRoute = DELAY_PAGE_ROUTE;
            } else {
                expectedPrefix = EXPIRY_BINDING_PREFIX;
                expectedRoute = EXPIRY_PAGE_ROUTE;
            }
            assertEquals(expectedPrefix, page.group(1), "绑定 ID 前缀与端点不匹配");
            assertEquals(expectedRoute, page.group(3), "页面路由与端点不匹配");
        }
        assertEquals(2, rows, "应有进货延时、效期预警两条页面角色绑定");

        assertTrue((DELAY_BINDING_PREFIX + INSPECT_BINDING_SUFFIX).length() <= ID_MAX_LENGTH);
        assertTrue((EXPIRY_BINDING_PREFIX + INSPECT_BINDING_SUFFIX).length() <= ID_MAX_LENGTH);

        // 页面菜单按路由查找：种子不得写死 MENU-* 字面量，否则菜单重建/复用后角色推导会失效
        assertFalse(Pattern.compile("MENU-[A-Z0-9-]+").matcher(seedSql()).find(),
                "页面角色必须按 functionurl（前端路由）推导，不得写死 MENU-* 菜单 ID");
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
        assertTrue(checked >= 4, "应至少检出 2 个资源 ID 与 2 个绑定 ID，实际: " + checked);
    }

    @Test
    void generated_resource_roles_contain_both_urls_with_insp_read_and_page_roles() throws IOException {
        Map<String, List<String>> resourceRoles = buildResourceRoles(seedSql());
        for (String url : Arrays.asList(DELAY_URL, EXPIRY_URL)) {
            List<String> roles = resourceRoles.get(url);
            assertNotNull(roles, "AUTH:RESOURCE_ROLES 必须包含端点 URL，否则网关返回 null: " + url);
            assertFalse(roles.isEmpty(), "端点角色集合不能为空: " + url);
            assertTrue(roles.contains(INSPECT_ROLE_CODE), "端点角色集合必须含 insp_read: " + url + " -> " + roles);
        }
        assertTrue(resourceRoles.get(DELAY_URL).contains("page:" + DELAY_PAGE_ROUTE),
                "进货延时端点必须包含进货延时示警页面菜单的角色");
        assertTrue(resourceRoles.get(EXPIRY_URL).contains("page:" + EXPIRY_PAGE_ROUTE),
                "效期预警端点必须包含效期预警页面菜单的角色");
    }

    @Test
    void seed_preflights_functiontype_for_all_ids_and_urls() throws IOException {
        String code = stripComments(seedSql());
        // 预检必须先按「行是否存在」判断，再校验 functionurl/functiontype。
        // 若用 `IS NOT NULL` 过滤，既有行 functionurl/functiontype 为 NULL 时预检全部跳过、
        // INSERT ... WHERE NOT EXISTS 也不写，却照旧绑定角色并 COMMIT —— 种子"成功"但 OAuth 加载不到。
        for (String id : new String[] {DELAY_FUNCTION_ID, EXPIRY_FUNCTION_ID}) {
            assertTrue(Pattern.compile("SELECT COUNT\\(\\*\\) INTO v_exists FROM `t_s_function`\\s+"
                    + "WHERE `ID` = '" + Pattern.quote(id) + "'").matcher(code).find(),
                    "缺少 ID 的存在性预检: " + id);
            assertTrue(code.contains(id + " exists but functionurl is NULL or a different URL"),
                    "缺少 ID 的 URL 冲突 SIGNAL: " + id);
            assertTrue(code.contains(id + " exists but functiontype is NULL or <>1"),
                    "缺少 ID 的 functiontype 不可激活 SIGNAL: " + id);
        }
        for (String url : new String[] {DELAY_URL, EXPIRY_URL}) {
            assertTrue(Pattern.compile("SELECT COUNT\\(\\*\\) INTO v_exists FROM `t_s_function`\\s+"
                    + "WHERE `functionurl` = '" + Pattern.quote(url) + "'\\s+AND `ID` <> 'FN-").matcher(code).find(),
                    "缺少 URL 被别的 function id 占用的预检: " + url);
            assertTrue(code.contains(url + " already mapped to a different function id"),
                    "缺少 URL 占用的 SIGNAL: " + url);
            assertTrue(Pattern.compile("SELECT COUNT\\(\\*\\) INTO v_exists FROM `t_s_function`\\s+"
                    + "WHERE `functionurl` = '" + Pattern.quote(url) + "'\\s+"
                    + "AND \\(`functiontype` IS NULL OR `functiontype` <> 1\\)").matcher(code).find(),
                    "缺少 URL 下 functiontype<>1/NULL 的检测: " + url);
            assertTrue(code.contains(url + " exists but functiontype is NULL or <>1"),
                    "缺少 URL 的 functiontype 不可激活 SIGNAL: " + url);
        }
        assertFalse(code.contains("WHERE `functionurl` IS NOT NULL AND `functiontype` <> 1"),
                "不得再用 IS NOT NULL 过滤做预检（会让 NULL 坏行假成功）");
    }

    @Test
    void seed_preflights_page_routes_rolecodes_and_derived_binding_conflicts() throws IOException {
        String code = stripComments(seedSql());
        // 共用端点的页面菜单（按路由）必须存在，否则无法推导页面角色（退化为只绑 insp_read 会让页面用户 403）
        for (String route : new String[] {DELAY_PAGE_ROUTE, EXPIRY_PAGE_ROUTE}) {
            assertTrue(Pattern.compile("SELECT COUNT\\(\\*\\) INTO v_exists FROM `t_s_function`\\s+"
                    + "WHERE `functionurl` = '" + Pattern.quote(route) + "';\\s+IF v_exists < 1 THEN").matcher(code).find(),
                    "缺少页面路由的存在性预检: " + route);
            assertTrue(code.contains("no page menu with functionurl=" + route),
                    "缺少页面菜单缺失的 SIGNAL: " + route);
        }
        // rolecode 过长会让拼出的绑定 ID 超出 varchar(32)：必须中止而不是被截断
        assertTrue(code.contains("CHAR_LENGTH(r.`rolecode`) > " + MAX_ROLECODE_LENGTH),
                "缺少 rolecode 长度守卫");
        assertTrue(code.contains("derived binding id would exceed varchar(32)"),
                "缺少 rolecode 过长的 SIGNAL");
        // 拼出的绑定 ID 前缀被别的函数占用（或 functionid 为 NULL）-> 中止
        assertTrue(code.contains("an RF-DELAY-IM-* binding exists but functionid is NULL or a different function"),
                "缺少 RF-DELAY-IM-* 前缀冲突的 SIGNAL");
        assertTrue(code.contains("an RF-EXP-QALL-* binding exists but functionid is NULL or a different function"),
                "缺少 RF-EXP-QALL-* 前缀冲突的 SIGNAL");
        assertTrue(Pattern.compile("`ID` LIKE 'RF-DELAY-IM-%'\\s+AND \\(`functionid` IS NULL OR `functionid` <> '"
                + Pattern.quote(DELAY_FUNCTION_ID) + "'\\)").matcher(code).find(),
                "RF-DELAY-IM-* 前缀冲突预检必须先容忍 NULL 再比对 functionid");
        assertTrue(Pattern.compile("`ID` LIKE 'RF-EXP-QALL-%'\\s+AND \\(`functionid` IS NULL OR `functionid` <> '"
                + Pattern.quote(EXPIRY_FUNCTION_ID) + "'\\)").matcher(code).find(),
                "RF-EXP-QALL-* 前缀冲突预检必须先容忍 NULL 再比对 functionid");
    }

    @Test
    void seed_preflights_binding_id_conflicts_and_wraps_inserts_in_transaction() throws IOException {
        String code = stripComments(seedSql());
        String[] bindings = {DELAY_BINDING_ID, EXPIRY_BINDING_ID};
        String[] bindingFunctions = {DELAY_FUNCTION_ID, EXPIRY_FUNCTION_ID};
        for (int i = 0; i < bindings.length; i++) {
            // 绑定同样先查存在性，再校验 functionid 与归属角色
            assertTrue(Pattern.compile("SELECT COUNT\\(\\*\\) INTO v_exists FROM `t_s_role_function`\\s+"
                    + "WHERE `ID` = '" + Pattern.quote(bindings[i]) + "'").matcher(code).find(),
                    "缺少绑定 ID 的存在性预检: " + bindings[i]);
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
        // insp_read 角色必须按 rolecode 动态查询且唯一
        assertTrue(code.contains("WHERE `rolecode` = 'insp_read'"), "insp_read 必须按 rolecode 动态查询");
        assertTrue(code.contains("expected exactly one t_s_role row with rolecode=insp_read"),
                "insp_read 不唯一时必须 SIGNAL");
        // insp_read 字面量绑定同样必须带「函数+角色」幂等守卫，重复执行不产生重复行
        for (String functionId : bindingFunctions) {
            assertTrue(Pattern.compile("WHERE `functionid` = '" + Pattern.quote(functionId)
                    + "'\\s+AND `roleid` = @insp_read_role_id\\);").matcher(code).find(),
                    "缺少 insp_read 绑定的幂等守卫: " + functionId);
        }
    }
}
