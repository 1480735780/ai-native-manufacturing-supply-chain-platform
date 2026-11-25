package com.zeroone.star.j1.dashboard.service.impl;

import com.zeroone.star.j1.dashboard.mapper.WmOmQmIMapper;
import com.zeroone.star.j1.dashboard.service.IPendSnapshotService;
import com.zeroone.star.project.vo.j1.dashboard.PendSnapshotVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.math.BigDecimal;

/**
 * 货物待办一致快照实现（巡检专用）。
 *
 * 事务显式声明 readOnly + REPEATABLE_READ：四个队列的子查询在同一语句、同一快照内
 * 完成；不读写 Redis，所以不受现有 1–10 分钟缓存影响。数值来自 SQL 侧 DECIMAL 求和。
 * 任一队列为 null（映射失败）即抛异常，让整个快照失败——不返回部分数据。
 *
 * @author wms-agent stage3
 * @since 2026-11-25
 */
@Service
public class PendSnapshotServiceImpl implements IPendSnapshotService {

    @Resource
    private WmOmQmIMapper wmOmQmIMapper;

    @Override
    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public PendSnapshotVO snapshot(String observedAt) {
        if (observedAt == null || observedAt.isEmpty()) {
            throw new IllegalArgumentException("observedAt 不能为空");
        }
        WmOmQmIMapper.PendSnapshotRow row = wmOmQmIMapper.selectPendSnapshot();
        if (row == null) {
            throw new RuntimeException("待办快照查询失败：未返回结果行");
        }
        PendSnapshotVO vo = new PendSnapshotVO();
        vo.setObservedAt(observedAt);
        vo.setReceipt(require(row.getReceipt(), "receipt"));
        vo.setToUp(require(row.getToUp(), "to_up"));
        vo.setPick(require(row.getPick(), "pick"));
        vo.setCurPick(require(row.getCurPick(), "cur_pick"));
        return vo;
    }

    /** 任一队列值为 null 视为查询失败，整体失败而不返回部分数据。 */
    private static PendSnapshotVO.QueueCount require(BigDecimal value, String queueType) {
        if (value == null) {
            throw new RuntimeException("待办快照查询失败：队列 " + queueType + " 计数为空");
        }
        return new PendSnapshotVO.QueueCount(queueType, value);
    }
}
