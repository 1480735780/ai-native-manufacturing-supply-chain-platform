package com.zeroone.star.daycheck;

import com.zeroone.star.daycheck.entity.NoUpGoods;
import com.zeroone.star.project.query.j3.daycheck.Arr.NoUpGoodsQuery;
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
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 用真实 MyBatis 解析 NoUpMapper.xml（不是对 XML 做字符串断言）。
 *
 * 守护点（第三轮评审阻断项）：
 * 1) resultMap 的每个 property 在 NoUpGoods 上都有 setter —— XML 映射 id/im_notice_id 而实体
 *    没有属性时，MyBatis 逐行映射会抛 "There is no setter for property named 'id'"；
 * 2) 按 resultMap 逐列赋值，实体的 id/im_notice_id 能被正确写入（供 DTO 的 rowId/noticeId 使用）；
 * 3) 两条语句的 BoundSql：旧端点不过滤 bin_sta（旧契约不变）；巡检语句过滤未上架、显式列、
 *    稳定排序；禁止把 sort 拼进 SQL。
 */
class NoUpMapperXmlTest {

    private static final String NS = "com.zeroone.star.daycheck.mapper.NoUpMapper.";
    private static final String MAPPER_XML = "src/main/resources/mapper/NoUpMapper.xml";

    private static Configuration configuration;

    @BeforeAll
    static void parseMapperXml() throws Exception {
        configuration = new Configuration();
        try (InputStream in = Files.newInputStream(Paths.get(MAPPER_XML))) {
            new XMLMapperBuilder(in, configuration, MAPPER_XML, configuration.getSqlFragments()).parse();
        }
    }

    private static String boundSql(String statementId, NoUpGoodsQuery query) {
        Map<String, Object> param = new HashMap<>();
        param.put("query", query);
        MappedStatement ms = configuration.getMappedStatement(NS + statementId);
        return ms.getBoundSql(param).getSql().replaceAll("\\s+", " ").trim();
    }

    private static NoUpGoodsQuery query(String sort) {
        NoUpGoodsQuery query = new NoUpGoodsQuery();
        query.setSort(sort);
        return query;
    }

    @Test
    void result_map_properties_all_have_setters_on_entity() {
        ResultMap resultMap = configuration.getResultMap(NS + "NoUpGoodsResultMap");
        MetaClass meta = MetaClass.forClass(NoUpGoods.class, configuration.getReflectorFactory());
        Set<String> properties = new HashSet<>();
        for (ResultMapping mapping : resultMap.getResultMappings()) {
            properties.add(mapping.getProperty());
            assertTrue(meta.hasSetter(mapping.getProperty()),
                    "NoUpGoods 缺少属性 " + mapping.getProperty() + "：MyBatis 逐行映射会抛 There is no setter");
        }
        assertTrue(properties.containsAll(Arrays.asList("id", "im_notice_id")),
                "resultMap 必须映射 id/im_notice_id（巡检行键与通知单号）");
    }

    @Test
    void row_mapping_fills_identity_fields() {
        ResultMap resultMap = configuration.getResultMap(NS + "NoUpGoodsResultMap");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", "wm-in-qm-0001");
        row.put("im_notice_id", "NOTICE-001");
        row.put("bin_sta", "N");
        row.put("shp_ming_cheng", "小蓝管");
        row.put("create_date", LocalDateTime.of(2026, 11, 24, 8, 0));

        NoUpGoods entity = new NoUpGoods();
        MetaObject metaObject = configuration.newMetaObject(entity);
        for (ResultMapping mapping : resultMap.getResultMappings()) {
            Object value = row.get(mapping.getColumn().toLowerCase(Locale.ROOT));
            if (value == null) {
                continue;
            }
            metaObject.setValue(mapping.getProperty(), value);
        }
        assertEquals("wm-in-qm-0001", entity.getId());
        assertEquals("NOTICE-001", entity.getIm_notice_id());
        assertEquals("N", entity.getBin_sta());
        assertEquals(LocalDateTime.of(2026, 11, 24, 8, 0), entity.getCreate_date());
    }

    @Test
    void legacy_statement_keeps_unfiltered_contract() {
        String legacy = boundSql("getNoUpGoodsPage", query(null));
        assertTrue(legacy.startsWith("select * from wm_in_qm_i wiqi"), legacy);
        // 旧页面按 N/I/Y 三态展示库存状态：旧端点不能偷偷加上未上架过滤
        assertFalse(legacy.contains("bin_sta = 'N'"), legacy);
        assertFalse(legacy.contains("bin_sta IS NULL"), legacy);
        assertTrue(legacy.contains("ORDER BY wiqi.create_date DESC, wiqi.id DESC"), legacy);
        assertTrue(boundSql("getNoUpGoodsPage", query("oldest"))
                .contains("ORDER BY wiqi.create_date ASC, wiqi.id ASC"));
    }

    @Test
    void inspection_statement_filters_unshelved_with_explicit_columns() {
        String inspection = boundSql("getNoUpGoodsForInspection", query("oldest"));
        assertTrue(inspection.contains("(wiqi.bin_sta = 'N' OR wiqi.bin_sta IS NULL)"), inspection);
        // 显式列清单：三表都有 id/create_date/sys_company_code，select * 会产生同名列歧义
        assertTrue(inspection.contains("wiqi.id as id"), inspection);
        assertTrue(inspection.contains("wiqi.im_notice_id as im_notice_id"), inspection);
        assertFalse(inspection.contains("select *"), inspection);
        assertTrue(inspection.contains("ORDER BY wiqi.create_date ASC, wiqi.id ASC"), inspection);
        assertTrue(boundSql("getNoUpGoodsForInspection", query(null))
                .contains("ORDER BY wiqi.create_date DESC, wiqi.id DESC"));
    }

    @Test
    void optional_filters_apply_to_both_statements() {
        NoUpGoodsQuery filter = query("oldest");
        filter.setGoods_id("G1");
        filter.setZhong_wen_qch("客户甲");
        for (String statement : Arrays.asList("getNoUpGoodsPage", "getNoUpGoodsForInspection")) {
            String sql = boundSql(statement, filter);
            assertTrue(sql.contains("md_goods.shp_bian_ma = ?"), statement + ": " + sql);
            assertTrue(sql.contains("md_cus.zhong_wen_qch = ?"), statement + ": " + sql);
        }
        // 不传过滤条件时不带 WHERE 片段里的占位符以外的参数
        assertFalse(boundSql("getNoUpGoodsPage", query(null)).contains("shp_bian_ma = ?"));
    }

    @Test
    void statements_never_concatenate_sort_parameter() throws Exception {
        String xml = new String(Files.readAllBytes(Paths.get(MAPPER_XML)), StandardCharsets.UTF_8);
        assertFalse(xml.contains("${sort}"), "禁止把 sort 参数直接拼进 SQL");
    }
}