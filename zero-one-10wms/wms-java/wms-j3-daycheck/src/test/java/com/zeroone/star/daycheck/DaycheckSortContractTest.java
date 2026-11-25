package com.zeroone.star.daycheck;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 未上架两条查询语句的契约（静态断言 Mapper XML；真实 MyBatis 解析见 NoUpMapperXmlTest）。
 *
 * 守护点：
 * - 旧页面语句 getNoUpGoodsPage 不过滤 bin_sta（页面按 N/I/Y 三态展示，旧契约不变）；
 * - 巡检语句 getNoUpGoodsForInspection 只取未上架（bin_sta='N'，兼容历史 NULL）；
 * - oldest 升序、默认降序，且都必须带稳定二级排序键 id；
 * - 禁止把请求参数直接拼进 SQL（${sort}）。
 */
class DaycheckSortContractTest {

    private static String mapperXml() throws Exception {
        return new String(
                Files.readAllBytes(Paths.get("src/main/resources/mapper/NoUpMapper.xml")),
                StandardCharsets.UTF_8);
    }

    private static String block(String tag, String id) throws Exception {
        Matcher matcher = Pattern.compile("<" + tag + " id=\"" + id + "\"[\\s\\S]*?</" + tag + ">")
                .matcher(mapperXml());
        assertTrue(matcher.find(), "缺少 <" + tag + " id=\"" + id + "\">");
        return matcher.group();
    }

    @Test
    void legacy_statement_keeps_old_filter_semantics() throws Exception {
        String legacy = block("select", "getNoUpGoodsPage");
        assertFalse(legacy.contains("bin_sta = 'N'"),
                "旧裸 List 端点不得改变过滤语义（页面按 N/I/Y 三态展示库存状态）");
        assertFalse(legacy.contains("bin_sta IS NULL"));
        assertTrue(legacy.contains("select * from wm_in_qm_i wiqi"), "旧语句保持 HEAD 的 select *");
    }

    @Test
    void inspection_query_filters_unshelved_only() throws Exception {
        String inspection = block("select", "getNoUpGoodsForInspection");
        assertTrue(inspection.contains("wiqi.bin_sta = 'N'"),
                "巡检查询必须过滤 bin_sta='N'");
        assertTrue(inspection.contains("wiqi.bin_sta IS NULL"),
                "巡检查询必须兼容历史 NULL 状态");
        assertFalse(inspection.contains("select *"), "巡检查询必须显式列清单，避免同名列歧义");
    }

    @Test
    void both_statements_share_stable_order_by() throws Exception {
        String orderBy = block("sql", "noUpOrderBy");
        assertTrue(orderBy.contains("ORDER BY wiqi.create_date ASC, wiqi.id ASC"),
                "oldest 分支必须按 create_date 升序并带 id 二级键");
        assertTrue(orderBy.contains("ORDER BY wiqi.create_date DESC, wiqi.id DESC"),
                "默认分支必须按 create_date 降序并带 id 二级键");
        for (String id : new String[] {"getNoUpGoodsPage", "getNoUpGoodsForInspection"}) {
            assertTrue(block("select", id).contains("<include refid=\"noUpOrderBy\"/>"),
                    id + " 必须引用统一排序片段");
        }
    }

    @Test
    void no_up_query_never_concatenates_sort_parameter() throws Exception {
        assertFalse(mapperXml().contains("${sort}"),
                "禁止把 sort 参数直接拼进 SQL");
    }
}