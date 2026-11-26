package com.zeroone.star.daycheck;

import com.zeroone.star.project.vo.j3.daycheck.tem.TemperatureVO;
import org.apache.ibatis.builder.xml.XMLMapperBuilder;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.reflection.MetaClass;
import org.apache.ibatis.session.Configuration;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 用真实 MyBatis 解析 TemperatureMapper.xml：守护温度巡检分页契约。
 *
 * 守护点：
 * 1) pageQueryAll 显式列包含 create_date（映射 VO.createDate），不再依赖 this.page(page) 自动拼 SQL；
 * 2) 稳定排序 wendu_cjsj + id，防止翻页抖动；
 * 3) VO 必须有 createDate setter，否则逐行映射会抛 There is no setter；
 * 4) SQL 无尾部分号（分页插件包裹时尾部分号会导致语法错误）。
 *
 * 注意：这是 XML 解析断言，不是 JDBC ResultSet 逐行真实映射，不得夸大证据。
 */
class TemperatureMapperXmlTest {

    private static final String NS = "com.zeroone.star.daycheck.mapper.TemperatureMapper.";
    private static final String MAPPER_XML = "src/main/resources/mapper/TemperatureMapper.xml";

    private static Configuration configuration;

    @BeforeAll
    static void parseMapperXml() throws Exception {
        configuration = new Configuration();
        try (InputStream in = Files.newInputStream(Paths.get(MAPPER_XML))) {
            new XMLMapperBuilder(in, configuration, MAPPER_XML, configuration.getSqlFragments()).parse();
        }
    }

    private static String boundSql(String statementId) {
        MappedStatement ms = configuration.getMappedStatement(NS + statementId);
        // pageQueryAll 的分页由插件在 Page 参数注入；这里不带 Page，得到原始 SQL 即可断言列与排序
        return ms.getBoundSql(new HashMap<String, Object>()).getSql().replaceAll("\\s+", " ").trim();
    }

    @Test
    void page_query_selects_create_date_and_stable_order() {
        String sql = boundSql("pageQueryAll");
        assertTrue(sql.contains("create_date"), "温度巡检必须返回 create_date: " + sql);
        assertTrue(sql.contains("wendu_cjsj"), sql);
        assertTrue(sql.contains("order by wendu_cjsj asc, id asc"), "必须按采集时间+id稳定排序: " + sql);
        assertFalse(sql.trim().endsWith(";"), "SQL 不应带尾部分号，分页插件包裹会出错: " + sql);
    }

    @Test
    void temperature_vo_has_create_date_setter() {
        MetaClass meta = MetaClass.forClass(TemperatureVO.class, configuration.getReflectorFactory());
        assertTrue(meta.hasSetter("createDate"),
                "TemperatureVO 必须有 createDate setter，否则逐行映射会抛 There is no setter");
        assertTrue(meta.hasSetter("wenduCjsj"), "TemperatureVO 必须有 wenduCjsj setter");
        assertTrue(meta.hasSetter("id"), "TemperatureVO 必须有 id setter");
    }

    @Test
    void xml_files_are_readable_utf8() throws Exception {
        String xml = new String(Files.readAllBytes(Paths.get(MAPPER_XML)), StandardCharsets.UTF_8);
        assertTrue(xml.contains("pageQueryAll"), "XML 必须定义 pageQueryAll");
    }
}
