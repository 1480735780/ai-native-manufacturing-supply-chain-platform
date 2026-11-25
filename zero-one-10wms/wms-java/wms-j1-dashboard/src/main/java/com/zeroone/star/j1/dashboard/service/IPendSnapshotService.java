package com.zeroone.star.j1.dashboard.service;

import com.zeroone.star.project.vo.j1.dashboard.PendSnapshotVO;

import java.math.BigDecimal;

/**
 * 货物待办一致快照（巡检专用）。
 *
 * 四个队列在同一个 REPEATABLE READ 只读事务内读取，绕过 Redis 缓存；
 * 数值由 SQL 侧 SUM(CAST(... AS DECIMAL(18,4))) 计算，以 BigDecimal 接收。
 * 任一队列查询失败则整个快照失败，不返回部分数据。
 */
public interface IPendSnapshotService {

    /**
     * 读取四个队列的同一快照。
     *
     * @param observedAt 本次快照统一使用的观察时间（ISO-8601 带时区）
     * @return 完整快照；任何队列为 null 或 SQL 失败都抛异常，不返回部分数据
     */
    PendSnapshotVO snapshot(String observedAt);

    /** 四队列的原始行：与现有缓存端点完全相同的过滤条件与数值表达式。 */
    interface Row {
        BigDecimal getReceipt();

        BigDecimal getToUp();

        BigDecimal getPick();

        BigDecimal getCurPick();
    }
}
