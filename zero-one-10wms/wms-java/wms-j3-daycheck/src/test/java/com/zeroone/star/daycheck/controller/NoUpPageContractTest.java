package com.zeroone.star.daycheck.controller;

import com.zeroone.star.daycheck.service.NoUpService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.daycheck.Arr.NoUpGoodsDTO;
import com.zeroone.star.project.query.j3.daycheck.Arr.NoUpGoodsQuery;
import com.zeroone.star.project.vo.JsonVO;
import org.junit.jupiter.api.Test;

import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/** 巡检专用分页端点契约：返回 rows/total/pages，且不改变旧端点行为。 */
class NoUpPageContractTest {

    private NoUpController controllerFor(PageDTO<NoUpGoodsDTO> page) {
        NoUpController controller = new NoUpController();
        NoUpService service = mock(NoUpService.class);
        when(service.getNoUpGoodsPageDTO(any(NoUpGoodsQuery.class))).thenReturn(page);
        controller.noUpService = service;
        return controller;
    }

    @Test
    void paged_endpoint_exposes_rows_total_and_pages() {
        NoUpGoodsDTO first = new NoUpGoodsDTO();
        NoUpGoodsDTO second = new NoUpGoodsDTO();
        PageDTO<NoUpGoodsDTO> page = new PageDTO<>();
        page.setRows(Arrays.asList(first, second));
        page.setTotal(137L);
        page.setPages(7L);
        page.setPageIndex(3L);
        page.setPageSize(20L);

        JsonVO<PageDTO<NoUpGoodsDTO>> result = controllerFor(page)
                .getNoUpGoodsPaged(new NoUpGoodsQuery());

        assertEquals(10000, result.getCode());
        PageDTO<NoUpGoodsDTO> data = result.getData();
        assertNotNull(data);
        assertSame(page.getRows(), data.getRows());
        assertEquals(137L, data.getTotal());
        assertEquals(7L, data.getPages());
        assertEquals(3L, data.getPageIndex());
        assertEquals(20L, data.getPageSize());
    }

    @Test
    void paged_endpoint_rejects_invalid_sort_like_legacy_endpoint() {
        NoUpGoodsQuery condition = new NoUpGoodsQuery();
        condition.setSort("newest");

        JsonVO<PageDTO<NoUpGoodsDTO>> result = controllerFor(new PageDTO<>())
                .getNoUpGoodsPaged(condition);

        assertEquals(9995, result.getCode());
    }

    @Test
    void paged_endpoint_accepts_oldest_sort() {
        NoUpGoodsQuery condition = new NoUpGoodsQuery();
        condition.setSort("oldest");
        PageDTO<NoUpGoodsDTO> page = new PageDTO<>();
        page.setRows(Arrays.asList(new NoUpGoodsDTO()));
        page.setTotal(1L);
        page.setPages(1L);

        JsonVO<PageDTO<NoUpGoodsDTO>> result = controllerFor(page)
                .getNoUpGoodsPaged(condition);

        assertEquals(10000, result.getCode());
        assertEquals(1L, result.getData().getTotal());
    }
}
