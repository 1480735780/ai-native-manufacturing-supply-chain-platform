package com.zeroone.star.project.vo.j1.dashboard;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Getter;
import lombok.Setter;
import lombok.ToString;

import java.math.BigDecimal;

/**
 * <p>
 * 描述：货物待办一致快照（巡检专用，绕过 Redis 缓存）
 * </p>
 * 四个队列在同一个 REPEATABLE READ 事务内读取，共用 observedAt；
 * 数值是 BigDecimal（SQL 侧 SUM(CAST(... AS DECIMAL))），不做字符串浮点求和。
 * 任一队列查询失败则整张快照失败，不返回部分数据。
 *
 * @author wms-agent stage3
 * @version 1.0.0
 */
@ApiModel("货物待办一致快照")
@Getter
@Setter
@ToString
public class PendSnapshotVO {

    @ApiModelProperty(value = "快照观察时间（ISO-8601，带时区），四个队列共用", example = "2026-11-25T12:00:00+08:00")
    private String observedAt;

    @ApiModelProperty(value = "待收货件数")
    private QueueCount receipt;

    @ApiModelProperty(value = "待上架件数")
    private QueueCount toUp;

    @ApiModelProperty(value = "待拣货件数")
    private QueueCount pick;

    @ApiModelProperty(value = "拣货中件数（仅诊断，不参与积压分级）")
    private QueueCount curPick;

    /** 单个队列的计数值；queueType 固定为 receipt / to_up / pick / cur_pick。 */
    @ApiModel("队列计数")
    @Getter
    @Setter
    @ToString
    public static class QueueCount {
        @ApiModelProperty(value = "队列类型", example = "receipt")
        private String queueType;
        @ApiModelProperty(value = "件数合计（精确小数）", example = "45.0000")
        private BigDecimal value;

        public QueueCount() {
        }

        public QueueCount(String queueType, BigDecimal value) {
            this.queueType = queueType;
            this.value = value;
        }
    }
}
