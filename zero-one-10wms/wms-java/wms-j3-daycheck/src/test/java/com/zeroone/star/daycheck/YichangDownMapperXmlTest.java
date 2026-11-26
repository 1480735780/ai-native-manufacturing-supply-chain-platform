package com.zeroone.star.daycheck;

import com.zeroone.star.daycheck.entity.YichangDown;
import com.zeroone.star.project.query.j3.daycheck.Arr.YichangDownQuery;
import org.apache.ibatis.builder.xml.XMLMapperBuilder;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.mapping.ResultMap;
import org.apache.ibatis.mapping.ResultMapping;
import org.apache.ibatis.reflection.MetaClass;
import org.apache.ibatis.reflection.MetaObject;
import org.apache.ibatis.session.Configuration;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 用真实 MyBatis 解析 YichangDownMapper.xml（不是对 XML 做字符串断言）。
 *
 * 守护点：
 * 1) resultMap 的每个 property 在 YichangDown 上都有 setter —— XML 映射 wtdg.id 而实体
 *    没有属性时，MyBatis 逐行映射会抛 "There is no setter for property named 'id'"；
 * 2) 按 resultMap 逐列赋值，实体 id 能被正确写入（供 DTO 的 rowId 使用）；
 * 3) 巡检语句显式列 + Decimal 安全的候选谓词（排除数值相等、保留 NULL/非法行）+ wtdg.id 稳定排序；旧语句 select * 契约不变；
 * 4) 禁止把 sort 拼进 SQL（无 ${sort}）。
 *
 * 注意：这是 XML 解析 + MetaObject 手工赋值，不是 JDBC ResultSet 逐行真实映射，不得夸大证据。
 */
class YichangDownMapperXmlTest {

    private static final String NS = "com.zeroone.star.daycheck.mapper.YichangDownMapper.";
    private static final String MAPPER_XML = "src/main/resources/mapper/YichangDownMapper.xml";

    private static Configuration configuration;

    @BeforeAll
    static void parseMapperXml() throws Exception {
        configuration = new Configuration();
        try (InputStream in = Files.newInputStream(Paths.get(MAPPER_XML))) {
            new XMLMapperBuilder(in, configuration, MAPPER_XML, configuration.getSqlFragments()).parse();
        }
    }

    private static String boundSql(String statementId, YichangDownQuery query) {
        Map<String, Object> param = new HashMap<>();
        param.put("query", query);
        MappedStatement ms = configuration.getMappedStatement(NS + statementId);
        return ms.getBoundSql(param).getSql().replaceAll("\\s+", " ").trim();
    }

    private static YichangDownQuery query(String sort) {
        YichangDownQuery query = new YichangDownQuery();
        query.setSort(sort);
        return query;
    }

    @Test
    void result_map_properties_all_have_setters_on_entity() {
        ResultMap resultMap = configuration.getResultMap(NS + "yichangDownResultMap");
        MetaClass meta = MetaClass.forClass(YichangDown.class, configuration.getReflectorFactory());
        Set<String> properties = new HashSet<>();
        for (ResultMapping mapping : resultMap.getResultMappings()) {
            properties.add(mapping.getProperty());
            assertTrue(meta.hasSetter(mapping.getProperty()),
                    "YichangDown 缺少属性 " + mapping.getProperty() + "：MyBatis 逐行映射会抛 There is no setter");
        }
        assertTrue(properties.contains("id"), "resultMap 必须映射 wtdg.id（巡检稳定行键 rowId）");
    }

    @Test
    void row_mapping_fills_identity_fields() {
        ResultMap resultMap = configuration.getResultMap(NS + "yichangDownResultMap");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", "down-0001");
        row.put("create_date", LocalDateTime.of(2026, 11, 24, 8, 0));
        row.put("goods_qua", "10");
        row.put("goods_quaok", "9");
        row.put("bin_id_to", "D-001");

        YichangDown entity = new YichangDown();
        MetaObject metaObject = configuration.newMetaObject(entity);
        for (ResultMapping mapping : resultMap.getResultMappings()) {
            Object value = row.get(mapping.getColumn().toLowerCase(Locale.ROOT));
            if (value == null) {
                continue;
            }
            metaObject.setValue(mapping.getProperty(), value);
        }
        assertEquals("down-0001", entity.getId());
        assertEquals(LocalDateTime.of(2026, 11, 24, 8, 0), entity.getCreate_date());
        assertEquals("10", entity.getGoods_qua());
        assertEquals("D-001", entity.getBin_id_to());
    }

    @Test
    void legacy_statement_keeps_select_star_contract() {
        String legacy = boundSql("getYichangDownPage", query(null));
        assertTrue(legacy.startsWith("SELECT * FROM wm_to_down_goods wtdg"), legacy);
        assertTrue(legacy.contains("wtdg.goods_qua != wtdg.goods_quaok"), legacy);
        assertTrue(legacy.contains("ORDER BY wtdg.create_date DESC, wtdg.id DESC"), legacy);
        assertTrue(boundSql("getYichangDownPage", query("oldest"))
                .contains("ORDER BY wtdg.create_date ASC, wtdg.id ASC"));
    }

    @Test
    void inspection_statement_uses_explicit_columns_and_stable_order() {
        String inspection = boundSql("getYichangDownForInspection", query("oldest"));
        // 显式列清单：三表 select * 有同名 id/create_date 歧义
        assertTrue(inspection.contains("wtdg.id as id"), inspection);
        assertTrue(inspection.contains("wtdg.create_date as create_date"), inspection);
        assertFalse(inspection.contains("select *"), inspection);
        assertTrue(inspection.contains("ORDER BY wtdg.create_date ASC, wtdg.id ASC"), inspection);
        assertTrue(boundSql("getYichangDownForInspection", query(null))
                .contains("ORDER BY wtdg.create_date DESC, wtdg.id DESC"));
    }

    @Test
    void inspection_statement_keeps_null_and_illegal_quantities_but_excludes_numeric_equal_rows() {
        // 候选谓词的目标：只排除「两侧都是合法数字、且原始字符串完全相同」的行。
        // 关键约束（审计 m01902）：SQL 里不得做任何数值 CAST——DECIMAL(38,10) 会截断小数位、
        // 超范围会截顶，把 1.00000000001/1.00000000004 或 29/30 位整数误判为相等而丢掉真实差异。
        String inspection = boundSql("getYichangDownForInspection", query("oldest"));
        assertTrue(inspection.contains("wtdg.goods_qua IS NULL"), inspection);
        assertTrue(inspection.contains("wtdg.goods_quaok IS NULL"), inspection);
        assertTrue(inspection.contains("REGEXP"), inspection);
        assertTrue(inspection.contains("^[+-]?[0-9]+(\\\\.[0-9]+)?$"), inspection);
        // 非法格式（abc/abc）与高精度差异都会保留，交给规则侧 Decimal 判定。
        assertTrue(inspection.contains("wtdg.goods_qua <> wtdg.goods_quaok"), inspection);
        // 有损数值比较必须彻底移除。
        assertFalse(inspection.contains("CAST"), inspection);
        assertFalse(inspection.toUpperCase(Locale.ROOT).contains("DECIMAL"), inspection);
    }

    @Test
    void inspection_statement_dedupes_join_keys_to_guarantee_one_row_per_id() {
        // md_cus.ke_hu_bian_ma 非唯一（zowms.sql:1882 仅普通 INDEX）：直接 JOIN 会复制 wtdg.id
        // 造成翻页漂移/Agent 停止评估。md_goods.shp_bian_ma 在 DDL 中有唯一索引（:1941），
        // 派生表保留以抵御历史重复数据，并与 md_cus 的写法对称。
        // 使用 parse 后的 BoundSql（空白折叠）做鲁棒断言，兼容格式化变化。
        String inspection = boundSql("getYichangDownForInspection", query(null)).toLowerCase(Locale.ROOT);
        assertTrue(inspection.contains("group by shp_bian_ma"), inspection);
        assertTrue(inspection.contains("group by ke_hu_bian_ma"), inspection);
        assertTrue(inspection.contains("max(shp_ming_cheng)"), inspection);
        assertTrue(inspection.contains("max(zhong_wen_qch)"), inspection);
        assertTrue(inspection.contains("mg.shp_ming_cheng as shp_ming_cheng"), inspection);
        assertTrue(inspection.contains("mc.zhong_wen_qch as zhong_wen_qch"), inspection);
        // base_unit 属于 wm_to_down_goods，md_goods 没有这一列（真实 MySQL 首跑 500 的根因）。
        assertTrue(inspection.contains("wtdg.base_unit as base_unit"), inspection);
        assertFalse(inspection.contains("mg.base_unit"), inspection);
        // 巡检语句不再出现直接 md_cus / md_goods 表别名，证明去重派生表生效。
        assertFalse(inspection.matches("(?s).*left join md_goods on .*"), inspection);
        assertFalse(inspection.matches("(?s).*left join md_cus on .*"), inspection);
    }

    /**
     * 显式列清单最容易犯的错是把列归到错误的表：静态 XML 断言全绿，真实 MySQL 上一执行就是
     * 500 Unknown column（2026-11-26 的 mg.base_unit）。这里以仓库 DDL zowms.sql 为准，逐列校验
     * 巡检语句里每个「别名.列」引用确实存在于该别名对应的表。仍是静态校验（对 DDL 而非对活库），
     * 活库证据由真实网关实测提供。
     */
    @Test
    void inspection_statement_columns_exist_in_repo_ddl() throws Exception {
        Map<String, Set<String>> ddl = repoDdlColumns();
        Map<String, String> aliasTable = new HashMap<>();
        aliasTable.put("wtdg", "wm_to_down_goods");
        aliasTable.put("mg", "md_goods");
        aliasTable.put("mc", "md_cus");
        aliasTable.put("md_cus", "md_cus");
        for (String table : aliasTable.values()) {
            assertTrue(ddl.containsKey(table), "DDL 中找不到表 " + table);
        }

        String sql = boundSql("getYichangDownForInspection", query(null)).toLowerCase(Locale.ROOT);
        Matcher ref = Pattern.compile("\\b(wtdg|mg|mc|md_cus)\\.(\\w+)").matcher(sql);
        int checked = 0;
        while (ref.find()) {
            String column = ref.group(2);
            assertTrue(ddl.get(aliasTable.get(ref.group(1))).contains(column),
                    "列不存在于仓库 DDL: " + ref.group(1) + "." + column);
            checked++;
        }
        assertTrue(checked >= 16, "应逐列校验显式列清单，实际匹配到 " + checked + " 处引用");

        // 派生表内部「(select ... from <表> group by <列>)」引用的列同样必须属于该表。
        // 必须从 "(" 起匹配：不带括号锚定时惰性分组会从主语句的 select 一路吞到派生表。
        Matcher derived = Pattern.compile("\\(\\s*select (.+?) from (md_goods|md_cus) group by (\\w+)\\)").matcher(sql);
        int derivedTables = 0;
        while (derived.find()) {
            Set<String> columns = ddl.get(derived.group(2));
            for (String item : derived.group(1).replace("max(", " ").replace(")", " ").split(",")) {
                String[] parts = item.trim().split("\\s+as\\s+");
                assertTrue(columns.contains(parts[0].trim()),
                        "派生表列不存在于仓库 DDL: " + derived.group(2) + "." + parts[0].trim());
            }
            assertTrue(columns.contains(derived.group(3)), "分组列不存在于仓库 DDL: " + derived.group(3));
            derivedTables++;
        }
        assertEquals(2, derivedTables, "应恰有两个去重派生表（md_goods / md_cus）");
    }

    private static Map<String, Set<String>> repoDdlColumns() throws Exception {
        Path ddl = null;
        for (String candidate : new String[]{
                "../../documents/02、项目需求/数据库/zowms.sql",
                "../documents/02、项目需求/数据库/zowms.sql",
                "documents/02、项目需求/数据库/zowms.sql"}) {
            Path path = Paths.get(candidate);
            if (Files.isRegularFile(path)) {
                ddl = path;
                break;
            }
        }
        assertNotNull(ddl, "找不到仓库 DDL zowms.sql");
        Map<String, Set<String>> tables = new HashMap<>();
        Pattern create = Pattern.compile("^CREATE TABLE `(\\w+)`\\s*\\(");
        Pattern column = Pattern.compile("^\\s+`(\\w+)`\\s+\\w+");
        String current = null;
        for (String line : Files.readAllLines(ddl, StandardCharsets.UTF_8)) {
            Matcher head = create.matcher(line);
            if (head.find()) {
                current = head.group(1);
                tables.put(current, new HashSet<String>());
                continue;
            }
            if (current == null) {
                continue;
            }
            if (line.startsWith(")")) {
                current = null;
                continue;
            }
            Matcher col = column.matcher(line);
            if (col.find()) {
                tables.get(current).add(col.group(1).toLowerCase(Locale.ROOT));
            }
        }
        return tables;
    }

    @Test
    void optional_filters_apply_to_both_statements() {
        YichangDownQuery filter = query("oldest");
        filter.setBin_id("PALLET-1");
        filter.setZhong_wen_qch("客户甲");
        String legacy = boundSql("getYichangDownPage", filter);
        assertTrue(legacy.contains("wtdg.bin_id_from = ?"), legacy);
        assertTrue(legacy.contains("md_cus.zhong_wen_qch = ?"), legacy);
        // 巡检语句客户过滤必须走 EXISTS 对原始 md_cus 表匹配，不能只用派生表 mc 的 MAX 名称：
        // 客户名重复时 MAX 只留一个名字，按其它合法客户名过滤会丢掉候选行。
        String inspection = boundSql("getYichangDownForInspection", filter);
        String inspectionLower = inspection.toLowerCase(Locale.ROOT);
        assertTrue(inspectionLower.contains("wtdg.bin_id_from = ?"), inspection);
        assertTrue(inspectionLower.contains("exists (select 1 from md_cus"), inspection);
        assertTrue(inspectionLower.contains("md_cus.ke_hu_bian_ma = wtdg.cus_code"), inspection);
        assertTrue(inspectionLower.contains("md_cus.zhong_wen_qch = ?"), inspection);
        assertFalse(inspectionLower.contains("mc.zhong_wen_qch = ?"), inspection);
        assertFalse(boundSql("getYichangDownPage", query(null)).contains("bin_id_from = ?"));
    }

    @Test
    void statements_never_concatenate_sort_parameter() throws Exception {
        String xml = new String(Files.readAllBytes(Paths.get(MAPPER_XML)), StandardCharsets.UTF_8);
        assertFalse(xml.contains("${sort}"), "禁止把 sort 参数直接拼进 SQL");
    }
}
