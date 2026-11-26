package com.zeroone.star.daycheck.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.daycheck.entity.YichangDown;
import com.zeroone.star.daycheck.mapper.YichangDownMapper;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.daycheck.Arr.YichangDownDTO;
import com.zeroone.star.project.query.j3.daycheck.Arr.YichangDownQuery;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
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

/** 出货异常分页查询必须把 total/pages 与稳定行键 rowId 透传给巡检调用方。 */
class YichangDownPageServiceTest {

    private YichangDownServiceImpl service;
    private YichangDownMapper mapper;

    @BeforeEach
    void setUp() {
        mapper = mock(YichangDownMapper.class);
        service = new YichangDownServiceImpl();
        ReflectionTestUtils.setField(service, "yichangDownMapper", mapper);
    }

    private YichangDown down(String id, String goodsId, String binFrom, String binTo, String qua, String quaok) {
        YichangDown item = new YichangDown();
        item.setId(id);
        item.setGoods_id(goodsId);
        item.setBin_id_from(binFrom);
        item.setBin_id_to(binTo);
        item.setGoods_qua(qua);
        item.setGoods_quaok(quaok);
        item.setCreate_date(LocalDateTime.of(2026, 11, 24, 8, 0));
        return item;
    }

    @Test
    @SuppressWarnings("unchecked")
    void page_dto_uses_inspection_statement_and_maps_row_id() {
        Page<YichangDown> page = new Page<>(1, 20);
        page.setTotal(88L);
        page.setPages(5L);
        page.setRecords(Arrays.asList(
                down("down-0001", "G1", "PALLET-1", "D-001", "10", "9"),
                down("down-0002", "G2", "PALLET-2", "D-002", "5", "5.0")));

        YichangDownQuery query = new YichangDownQuery();
        query.setPageIndex(1);
        query.setPageSize(20);
        query.setSort("oldest");
        when(mapper.getYichangDownForInspection(any(Page.class), eq(query))).thenReturn(page);

        PageDTO<YichangDownDTO> result = service.getYichangDownPageDTO(query);

        verify(mapper).getYichangDownForInspection(any(Page.class), eq(query));
        verify(mapper, never()).getYichangDownPage(any(Page.class), any(YichangDownQuery.class));
        assertNotNull(result);
        assertEquals(88L, result.getTotal());
        assertEquals(5L, result.getPages());
        assertEquals(1L, result.getPageIndex());
        assertEquals(20L, result.getPageSize());
        assertEquals(2, result.getRows().size());

        YichangDownDTO first = result.getRows().get(0);
        // BeanUtils 不会把 id 映射成 rowId，必须显式赋值
        assertEquals("down-0001", first.getRowId());
        assertEquals("G1", first.getGoods_id());
        assertEquals("PALLET-1", first.getBin_id());
        assertEquals("D-001", first.getBin_id_to());
        assertEquals("10", first.getGoods_qua());
        assertEquals("9", first.getGoods_quaok());
        assertEquals(LocalDateTime.of(2026, 11, 24, 8, 0), first.getCreate_date());
        assertEquals("down-0002", result.getRows().get(1).getRowId());
    }

    @Test
    @SuppressWarnings("unchecked")
    void legacy_list_keeps_dto_contract_without_row_id() {
        Page<YichangDown> page = new Page<>(1, 10);
        page.setTotal(1L);
        page.setRecords(Arrays.asList(down("down-0001", "G1", "PALLET-1", "D-001", "10", "9")));
        YichangDownQuery query = new YichangDownQuery();
        when(mapper.getYichangDownPage(any(Page.class), eq(query))).thenReturn(page);

        List<YichangDownDTO> result = service.getYichangDownPage(query);

        verify(mapper).getYichangDownPage(any(Page.class), eq(query));
        verify(mapper, never()).getYichangDownForInspection(any(Page.class), any(YichangDownQuery.class));
        assertEquals(1, result.size());
        assertNull(result.get(0).getRowId());
        assertEquals("PALLET-1", result.get(0).getBin_id());
    }

    @Test
    void legacy_and_paged_share_field_mapping() {
        YichangDownDTO dto = YichangDownServiceImpl.toDTO(
                down("id-1", "G9", "P-9", "D-9", "3", "2"), true);
        assertEquals("id-1", dto.getRowId());
        assertEquals("P-9", dto.getBin_id());
        YichangDownDTO legacy = YichangDownServiceImpl.toDTO(
                down("id-1", "G9", "P-9", "D-9", "3", "2"), false);
        assertNull(legacy.getRowId());
        assertEquals("P-9", legacy.getBin_id());
    }
}
