package com.zeroone.star.daycheck.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.daycheck.entity.NoUpGoods;
import com.zeroone.star.daycheck.mapper.NoUpMapper;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.daycheck.Arr.NoUpGoodsDTO;
import com.zeroone.star.project.query.j3.daycheck.Arr.NoUpGoodsQuery;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/** 分页查询必须把 MyBatis-Plus 的 total/pages 与稳定行键透传给巡检调用方。 */
class NoUpPageServiceTest {

    private NoUpServiceImpl service;
    private NoUpMapper mapper;

    @BeforeEach
    void setUp() {
        mapper = mock(NoUpMapper.class);
        service = new NoUpServiceImpl();
        ReflectionTestUtils.setField(service, "noUpMapper", mapper);
    }

    private NoUpGoods goods(String id, String noticeId, String goodsId, String binSta, String unit) {
        NoUpGoods item = new NoUpGoods();
        item.setId(id);
        item.setIm_notice_id(noticeId);
        item.setGoods_id(goodsId);
        item.setBin_sta(binSta);
        item.setGoods_unit(unit);
        item.setCreate_date(LocalDateTime.of(2026, 1, 1, 0, 0));
        return item;
    }

    @Test
    @SuppressWarnings("unchecked")
    void page_dto_uses_inspection_statement_and_maps_identity_fields() {
        Page<NoUpGoods> page = new Page<>(1, 20);
        page.setTotal(201L);
        page.setPages(11L);
        page.setRecords(Arrays.asList(
                goods("wm-in-qm-0001", "NOTICE-001", "G1", "N", "箱"),
                goods("wm-in-qm-0002", "NOTICE-002", "G2", null, "个")));

        NoUpGoodsQuery query = new NoUpGoodsQuery();
        query.setPageIndex(1);
        query.setPageSize(20);
        query.setSort("oldest");
        when(mapper.getNoUpGoodsForInspection(any(Page.class), eq(query))).thenReturn(page);

        PageDTO<NoUpGoodsDTO> result = service.getNoUpGoodsPageDTO(query);

        // 巡检端点必须走独立语句，不能复用旧页面的 select *
        verify(mapper).getNoUpGoodsForInspection(any(Page.class), eq(query));
        verify(mapper, never()).getNoUpGoodsPage(any(Page.class), any(NoUpGoodsQuery.class));

        assertNotNull(result);
        assertEquals(201L, result.getTotal());
        assertEquals(11L, result.getPages());
        assertEquals(1L, result.getPageIndex());
        assertEquals(20L, result.getPageSize());
        assertEquals(2, result.getRows().size());

        NoUpGoodsDTO first = result.getRows().get(0);
        // BeanUtils 不会把 id/im_notice_id 映射成 rowId/noticeId，必须显式赋值
        assertEquals("wm-in-qm-0001", first.getRowId());
        assertEquals("NOTICE-001", first.getNoticeId());
        assertEquals("G1", first.getGoods_id());
        assertEquals("N", first.getKucunsta());
        assertEquals("箱", first.getShl_dan_wei());
        assertEquals("wm-in-qm-0002", result.getRows().get(1).getRowId());
        assertNull(result.getRows().get(1).getKucunsta());

        // 传给 Mapper 的分页参数与排序原样透传
        ArgumentCaptor<Page<NoUpGoods>> pageCaptor = ArgumentCaptor.forClass(Page.class);
        verify(mapper).getNoUpGoodsForInspection(pageCaptor.capture(), eq(query));
        assertEquals(1, pageCaptor.getValue().getCurrent());
        assertEquals(20, pageCaptor.getValue().getSize());
        assertEquals("oldest", query.getSort());
    }

    @Test
    @SuppressWarnings("unchecked")
    void legacy_list_keeps_dto_contract_without_identity_fields() {
        Page<NoUpGoods> page = new Page<>(1, 10);
        page.setTotal(1L);
        page.setRecords(Arrays.asList(goods("wm-in-qm-0001", "NOTICE-001", "G1", "N", "箱")));
        NoUpGoodsQuery query = new NoUpGoodsQuery();
        when(mapper.getNoUpGoodsPage(any(Page.class), eq(query))).thenReturn(page);

        List<NoUpGoodsDTO> result = service.getNoUpGoodsPage(query);

        verify(mapper).getNoUpGoodsPage(any(Page.class), eq(query));
        verify(mapper, never()).getNoUpGoodsForInspection(any(Page.class), any(NoUpGoodsQuery.class));
        assertEquals(1, result.size());
        // 旧端点不输出 rowId/noticeId（DTO 上保持 null，序列化时省略）
        assertNull(result.get(0).getRowId());
        assertNull(result.get(0).getNoticeId());
        assertEquals("N", result.get(0).getKucunsta());
        assertEquals("箱", result.get(0).getShl_dan_wei());
    }

    @Test
    @SuppressWarnings("unchecked")
    void legacy_and_paged_share_field_mapping() {
        NoUpGoodsDTO dto = NoUpServiceImpl.toDTO(goods("id-1", "N-1", "G9", "Y", "托"), true);
        assertEquals("id-1", dto.getRowId());
        assertEquals("N-1", dto.getNoticeId());
        assertEquals("Y", dto.getKucunsta());
        assertEquals("托", dto.getShl_dan_wei());
        NoUpGoodsDTO legacy = NoUpServiceImpl.toDTO(goods("id-1", "N-1", "G9", "Y", "托"), false);
        assertNull(legacy.getRowId());
        assertNull(legacy.getNoticeId());
        assertEquals("Y", legacy.getKucunsta());
    }
}