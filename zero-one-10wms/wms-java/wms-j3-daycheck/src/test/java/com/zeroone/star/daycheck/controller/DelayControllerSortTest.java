package com.zeroone.star.daycheck.controller;

import com.zeroone.star.daycheck.service.DelayService;
import com.zeroone.star.project.vo.JsonVO;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;

/** sort 只接受枚举 oldest；非法值返回 9995，不落 500。 */
class DelayControllerSortTest {

    @Test
    void invalid_sort_is_rejected_with_params_invalid() {
        DelayController controller = new DelayController();
        controller.delayService = mock(DelayService.class);

        JsonVO<?> result = controller.queryAll(1, 20, "newest");

        assertEquals(9995, result.getCode());
    }
}
