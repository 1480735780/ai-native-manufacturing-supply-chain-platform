package com.zeroone.star.j1.dashboard.controller;

import com.zeroone.star.j1.dashboard.service.IPendSnapshotService;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.project.vo.j1.dashboard.PendSnapshotVO;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

import java.lang.reflect.Method;
import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/** 巡检专用一致快照端点契约：统一 observedAt、四队列 BigDecimal、整体失败不返回部分数据、事务隔离声明。 */
class PendSnapshotContractTest {

    private static PendSnapshotVO fullSnapshot(String observedAt) {
        PendSnapshotVO vo = new PendSnapshotVO();
        vo.setObservedAt(observedAt);
        vo.setReceipt(new PendSnapshotVO.QueueCount("receipt", new BigDecimal("0.0000")));
        vo.setToUp(new PendSnapshotVO.QueueCount("to_up", new BigDecimal("12.5000")));
        vo.setPick(new PendSnapshotVO.QueueCount("pick", new BigDecimal("45.0000")));
        vo.setCurPick(new PendSnapshotVO.QueueCount("cur_pick", new BigDecimal("74.0000")));
        return vo;
    }

    private DashboardController controllerFor(IPendSnapshotService service) {
        DashboardController controller = new DashboardController();
        controller.pendSnapshotService = service;
        return controller;
    }

    @Test
    void snapshot_endpoint_returns_four_queues_with_shared_observed_at() {
        IPendSnapshotService service = mock(IPendSnapshotService.class);
        when(service.snapshot(anyString())).thenAnswer(inv -> fullSnapshot(inv.getArgument(0)));
        JsonVO<PendSnapshotVO> vo = controllerFor(service).queryPendSnapshot();
        assertEquals(Integer.valueOf(10000), vo.getCode());
        PendSnapshotVO data = vo.getData();
        assertNotNull(data);
        assertNotNull(data.getObservedAt());
        assertEquals("receipt", data.getReceipt().getQueueType());
        assertEquals("to_up", data.getToUp().getQueueType());
        assertEquals("pick", data.getPick().getQueueType());
        assertEquals("cur_pick", data.getCurPick().getQueueType());
        assertEquals(new BigDecimal("12.5000"), data.getToUp().getValue());
        assertEquals(0, new BigDecimal("45").compareTo(data.getPick().getValue()));
    }

    @Test
    void snapshot_endpoint_fails_whole_when_service_fails() {
        IPendSnapshotService service = mock(IPendSnapshotService.class);
        when(service.snapshot(anyString())).thenThrow(new RuntimeException("待办快照查询失败：队列 pick 计数为空"));
        RuntimeException ex = assertThrows(RuntimeException.class, () -> controllerFor(service).queryPendSnapshot());
        assertTrue(ex.getMessage().contains("pick"));
    }

    @Test
    void snapshot_endpoint_fails_when_service_returns_null() {
        IPendSnapshotService service = mock(IPendSnapshotService.class);
        when(service.snapshot(anyString())).thenReturn(null);
        assertThrows(RuntimeException.class, () -> controllerFor(service).queryPendSnapshot());
    }

    @Test
    void snapshot_service_declares_readonly_repeatable_read_transaction() throws Exception {
        Method m = com.zeroone.star.j1.dashboard.service.impl.PendSnapshotServiceImpl.class
                .getMethod("snapshot", String.class);
        Transactional tx = m.getAnnotation(Transactional.class);
        assertNotNull(tx, "snapshot 必须在事务内执行");
        assertTrue(tx.readOnly());
        assertSame(Isolation.REPEATABLE_READ, tx.isolation());
    }
}
