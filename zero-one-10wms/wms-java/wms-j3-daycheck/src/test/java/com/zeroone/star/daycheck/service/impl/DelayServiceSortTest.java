package com.zeroone.star.daycheck.service.impl;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.daycheck.entity.Delay;
import com.zeroone.star.daycheck.mapper.DelayMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 进货延时的排序契约。
 *
 * oldest → im_data 升序；默认 → im_data 降序；两者都必须带 id 二级排序键，
 * 避免同一 im_data 的多行顺序在多次查询之间漂移。
 */
class DelayServiceSortTest {

    private DelayServiceImpl service;
    private DelayMapper mapper;

    @BeforeEach
    void setUp() {
        mapper = mock(DelayMapper.class);
        service = new DelayServiceImpl();
        ReflectionTestUtils.setField(service, "baseMapper", mapper);
        when(mapper.selectPage(any(Page.class), any(Wrapper.class)))
                .thenReturn(new Page<Delay>());
    }

    @SuppressWarnings("unchecked")
    private String sqlSegmentFor(String sort) {
        service.selectAll(1, 10, sort);
        ArgumentCaptor<Wrapper<Delay>> captor = ArgumentCaptor.forClass(Wrapper.class);
        verify(mapper).selectPage(any(Page.class), captor.capture());
        return captor.getValue().getSqlSegment();
    }

    @Test
    void oldest_orders_by_im_data_ascending_with_id_tie_breaker() {
        String sql = sqlSegmentFor("oldest");
        assertTrue(sql.contains("im_data ASC"), "oldest 必须按 im_data 升序：" + sql);
        assertTrue(sql.contains("id ASC"), "oldest 必须带 id 二级键：" + sql);
    }

    @Test
    void default_orders_by_im_data_descending_with_id_tie_breaker() {
        String sql = sqlSegmentFor(null);
        assertTrue(sql.contains("im_data DESC"), "默认必须按 im_data 降序：" + sql);
        assertTrue(sql.contains("id DESC"), "默认必须带 id 二级键：" + sql);
    }
}
