package com.zeroone.star.daycheck.controller;

import com.zeroone.star.daycheck.service.YichangDownService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.daycheck.Arr.YichangDownDTO;
import com.zeroone.star.project.query.j3.daycheck.Arr.YichangDownQuery;
import com.zeroone.star.project.vo.JsonVO;
import org.junit.jupiter.api.Test;

import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/** 出货异常巡检分页端点契约：返回 rows/total/pages，且不改变旧端点行为。 */
class YichangDownPageContractTest {

    private YichangDownContrller controllerFor(PageDTO<YichangDownDTO> page) {
        YichangDownContrller controller = new YichangDownContrller();
        YichangDownService service = mock(YichangDownService.class);
        when(service.getYichangDownPageDTO(any(YichangDownQuery.class))).thenReturn(page);
        controller.yichangDownService = service;
        return controller;
    }

    @Test
    void paged_endpoint_exposes_rows_total_and_pages() {
        YichangDownDTO first = new YichangDownDTO();
        YichangDownDTO second = new YichangDownDTO();
        PageDTO<YichangDownDTO> page = new PageDTO<>();
        page.setRows(Arrays.asList(first, second));
        page.setTotal(88L);
        page.setPages(5L);
        page.setPageIndex(2L);
        page.setPageSize(20L);

        JsonVO<PageDTO<YichangDownDTO>> result = controllerFor(page)
                .getYichangDownPaged(new YichangDownQuery());

        assertEquals(10000, result.getCode());
        PageDTO<YichangDownDTO> data = result.getData();
        assertNotNull(data);
        assertSame(page.getRows(), data.getRows());
        assertEquals(88L, data.getTotal());
        assertEquals(5L, data.getPages());
        assertEquals(2L, data.getPageIndex());
        assertEquals(20L, data.getPageSize());
    }

    @Test
    void paged_endpoint_applies_sane_paging_defaults_when_omitted() {
        // 复核缺陷（2026-11-26）：不传 pageSize 时原始 long 默认 0，MyBatis 分页得到
        // total>0 但 pages=0、rows=[] 的静默空集。PageQuery 现在给出 1/10 的默认值。
        YichangDownQuery condition = new YichangDownQuery();

        assertEquals(1L, condition.getPageIndex(), "缺省页码应为第 1 页");
        assertEquals(10L, condition.getPageSize(), "缺省条数应为 10，而不是 0");

        JsonVO<PageDTO<YichangDownDTO>> result = controllerFor(new PageDTO<>())
                .getYichangDownPaged(condition);

        assertEquals(10000, result.getCode(), "缺省分页不应触发空集或错误");
    }

    @Test
    void paged_endpoint_rejects_invalid_sort() {
        YichangDownQuery condition = new YichangDownQuery();
        condition.setSort("newest");

        JsonVO<PageDTO<YichangDownDTO>> result = controllerFor(new PageDTO<>())
                .getYichangDownPaged(condition);

        assertEquals(9995, result.getCode());
    }

    @Test
    void paged_endpoint_accepts_oldest_sort() {
        YichangDownQuery condition = new YichangDownQuery();
        condition.setSort("oldest");
        PageDTO<YichangDownDTO> page = new PageDTO<>();
        page.setRows(Arrays.asList(new YichangDownDTO()));
        page.setTotal(1L);
        page.setPages(1L);

        JsonVO<PageDTO<YichangDownDTO>> result = controllerFor(page)
                .getYichangDownPaged(condition);

        assertEquals(10000, result.getCode());
        assertEquals(1L, result.getData().getTotal());
    }

    @Test
    void legacy_endpoint_rejects_invalid_sort_too() {
        YichangDownQuery condition = new YichangDownQuery();
        condition.setSort("newest");

        JsonVO<java.util.List<YichangDownDTO>> result = controllerFor(new PageDTO<>())
                .getYichangDown(condition);

        assertEquals(9995, result.getCode());
    }
}
