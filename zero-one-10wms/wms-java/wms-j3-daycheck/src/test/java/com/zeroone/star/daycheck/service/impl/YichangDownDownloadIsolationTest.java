package com.zeroone.star.daycheck.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.daycheck.entity.YichangDown;
import com.zeroone.star.daycheck.mapper.YichangDownMapper;
import com.zeroone.star.project.query.j3.daycheck.Arr.YichangDownQuery;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Field;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * F-016 审计修复：出货异常下载不得从单例服务的共享 Map 字段读取上一次请求的数据。
 *
 * 守护点：
 * 1) 服务类上不存在存放查询结果的共享可变字段（data / Map<String,List<YichangDown>>）；
 * 2) getYichangDownDate() 每次调用都重新查询 mapper，两次调用不会串用彼此的结果；
 * 3) getYichangDownPage(...) 列表调用不会把结果写入任何字段供后续下载读取。
 */
class YichangDownDownloadIsolationTest {

    private YichangDownServiceImpl service;
    private YichangDownMapper mapper;

    @BeforeEach
    void setUp() {
        mapper = mock(YichangDownMapper.class);
        service = new YichangDownServiceImpl();
        ReflectionTestUtils.setField(service, "yichangDownMapper", mapper);
    }

    private YichangDown down(String id) {
        YichangDown item = new YichangDown();
        item.setId(id);
        return item;
    }

    @Test
    void no_shared_query_result_field_on_singleton_service() {
        for (Field field : YichangDownServiceImpl.class.getDeclaredFields()) {
            String name = field.getName();
            assertFalse("data".equals(name),
                    "服务上不得存在名为 data 的共享查询结果字段（跨请求泄漏）");
            assertFalse(List.class.isAssignableFrom(field.getType())
                            || java.util.Map.class.isAssignableFrom(field.getType()),
                    "服务上不得存在 List/Map 类型的共享查询结果字段: " + name);
        }
    }

    @Test
    @SuppressWarnings("unchecked")
    void download_refetches_each_time_instead_of_reusing_last_list_result() {
        Page<YichangDown> first = new Page<>(1, 10000);
        first.setRecords(Collections.singletonList(down("request-A")));
        Page<YichangDown> second = new Page<>(1, 10000);
        second.setRecords(Collections.singletonList(down("request-B")));

        when(mapper.getYichangDownPage(any(Page.class), any(YichangDownQuery.class)))
                .thenReturn(first, second);

        assertEquals("request-A", service.getYichangDownDate().get(0).getId());
        assertEquals("request-B", service.getYichangDownDate().get(0).getId());
        verify(mapper, times(2)).getYichangDownPage(any(Page.class), any(YichangDownQuery.class));

        // 即使此前发生过列表调用，下载依然走自己的全新查询，不读任何缓存字段
        Page<YichangDown> listPage = new Page<>(1, 10);
        listPage.setRecords(Arrays.asList(down("list-1"), down("list-2")));
        when(mapper.getYichangDownPage(any(Page.class), any(YichangDownQuery.class)))
                .thenReturn(listPage, second);
        service.getYichangDownPage(new YichangDownQuery());
        assertEquals("request-B", service.getYichangDownDate().get(0).getId());
    }

    /**
     * 审计 m01655：下载不得有“前 N 条静默截断”。
     * 连续两页都满页时必须继续翻页，直到某页不足一页为止。
     */
    @Test
    @SuppressWarnings("unchecked")
    void download_paginates_until_exhausted_instead_of_silently_capping() {
        long pageSize = (long) org.springframework.test.util.ReflectionTestUtils
                .getField(YichangDownServiceImpl.class, "DOWNLOAD_PAGE_SIZE");
        assertEquals(1000L, pageSize, "下载单页大小应为 1000（分页拉取，不截断）");

        Page<YichangDown> fullPage1 = new Page<>(1, pageSize);
        fullPage1.setRecords(fullPage((int) pageSize, "p1-"));
        Page<YichangDown> fullPage2 = new Page<>(2, pageSize);
        fullPage2.setRecords(fullPage((int) pageSize, "p2-"));
        Page<YichangDown> tailPage = new Page<>(3, pageSize);
        tailPage.setRecords(Collections.singletonList(down("tail-1")));

        when(mapper.getYichangDownPage(any(Page.class), any(YichangDownQuery.class)))
                .thenReturn(fullPage1, fullPage2, tailPage);

        List<YichangDown> all = service.getYichangDownDate();

        // 2000 + 1 条全部返回，没有任何截断
        assertEquals((int) pageSize * 2 + 1, all.size(),
                "下载必须拉完整表，不得在小阈值处静默截断");
        assertEquals("p1-0", all.get(0).getId());
        assertEquals("tail-1", all.get(all.size() - 1).getId());
        verify(mapper, times(3))
                .getYichangDownPage(any(Page.class), any(YichangDownQuery.class));
    }

    private List<YichangDown> fullPage(int size, String prefix) {
        java.util.List<YichangDown> rows = new java.util.ArrayList<>(size);
        for (int i = 0; i < size; i++) {
            rows.add(down(prefix + i));
        }
        return rows;
    }

    /**
     * 审计 m01902：OFFSET 分页并发变更时会出现重复行——必须明确失败，不得导出重复/缺数的 Excel。
     */
    @Test
    @SuppressWarnings("unchecked")
    void download_aborts_when_a_row_id_repeats_across_pages() {
        long pageSize = (long) ReflectionTestUtils.getField(YichangDownServiceImpl.class, "DOWNLOAD_PAGE_SIZE");
        Page<YichangDown> fullPage1 = new Page<>(1, pageSize);
        fullPage1.setRecords(fullPage((int) pageSize, "p1-"));
        Page<YichangDown> repeatedPage = new Page<>(2, pageSize);
        repeatedPage.setRecords(fullPage((int) pageSize, "p1-"));   // 与第一页完全重复

        when(mapper.getYichangDownPage(any(Page.class), any(YichangDownQuery.class)))
                .thenReturn(fullPage1, repeatedPage);

        IllegalStateException ex = assertThrows(IllegalStateException.class, service::getYichangDownDate);
        assertTrue(ex.getMessage().contains("重复"), ex.getMessage());
        verify(mapper, times(2)).getYichangDownPage(any(Page.class), any(YichangDownQuery.class));
    }

    /**
     * 审计 m01902：导出必须有硬上限，且超限要报错——不能无限翻页、也不能静默截断。
     */
    @Test
    @SuppressWarnings("unchecked")
    void download_aborts_when_row_count_exceeds_the_hard_cap() {
        int maxRows = (int) ReflectionTestUtils.getField(YichangDownServiceImpl.class, "MAX_EXPORT_ROWS");
        assertTrue(maxRows > 0 && maxRows <= 200000, "导出上限必须有界: " + maxRows);
        long pageSize = (long) ReflectionTestUtils.getField(YichangDownServiceImpl.class, "DOWNLOAD_PAGE_SIZE");

        // 让每页都返回满页且 id 各不相同，行数在超过上限的那一页被拦下。
        java.util.concurrent.atomic.AtomicInteger seq = new java.util.concurrent.atomic.AtomicInteger();
        when(mapper.getYichangDownPage(any(Page.class), any(YichangDownQuery.class))).thenAnswer(inv -> {
            Page<YichangDown> p = inv.getArgument(0);
            java.util.List<YichangDown> rows = new java.util.ArrayList<>();
            for (int i = 0; i < pageSize; i++) {
                rows.add(down("row-" + seq.incrementAndGet()));
            }
            p.setRecords(rows);
            return p;
        });

        IllegalStateException ex = assertThrows(IllegalStateException.class, service::getYichangDownDate);
        assertTrue(ex.getMessage().contains("上限"), ex.getMessage());
        assertTrue(seq.get() > maxRows, "必须在超过上限时才中止，已取行数=" + seq.get());
    }

    @Test
    void inspection_page_also_does_not_cache_into_a_field() {
        // 反射确认没有任何字段在巡检分页调用后被赋值成 List/Map（除 mapper 注入字段）
        Page<YichangDown> page = new Page<>(1, 10);
        page.setRecords(Collections.singletonList(down("inspection-1")));
        when(mapper.getYichangDownForInspection(any(Page.class), any(YichangDownQuery.class)))
                .thenReturn(page);

        YichangDownQuery query = new YichangDownQuery();
        service.getYichangDownPageDTO(query);

        for (Field field : YichangDownServiceImpl.class.getDeclaredFields()) {
            if ("yichangDownMapper".equals(field.getName())) {
                continue;
            }
            // static final 常量（如 DOWNLOAD_PAGE_SIZE）不是 per-request 共享可变状态。
            if (java.lang.reflect.Modifier.isStatic(field.getModifiers())
                    && java.lang.reflect.Modifier.isFinal(field.getModifiers())) {
                continue;
            }
            field.setAccessible(true);
            try {
                Object value = field.get(service);
                assertNull(value, "调用分页后不应有字段缓存查询结果: " + field.getName());
            } catch (IllegalAccessException e) {
                throw new AssertionError(e);
            }
        }
    }
}
