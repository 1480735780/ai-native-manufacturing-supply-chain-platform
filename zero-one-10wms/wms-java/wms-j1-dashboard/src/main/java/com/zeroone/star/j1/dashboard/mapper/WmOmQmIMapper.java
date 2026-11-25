package com.zeroone.star.j1.dashboard.mapper;

import com.zeroone.star.j1.dashboard.entity.WmOmQmI;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.math.BigDecimal;

/**
 * <p>
 *  Mapper 接口
 * </p>
 *
 * @author j1-yunyu
 * @since 2025-02-27
 */
@Mapper
public interface WmOmQmIMapper extends BaseMapper<WmOmQmI> {

    /**
     * 巡检专用：四个待办队列在同一语句内求和（天然处于同一快照）。
     *
     * 过滤条件与现有缓存端点逐字一致（receipt: bin_pre='N'；to_up: bin_sta='N'；
     * pick: bin_sta='I'；cur_pick: bin_sta='N'）。数值列在库中是 varchar(32)，
     * 这里在 SQL 侧 CAST 为 DECIMAL(18,4) 后求和：遇到非数字值 MySQL 直接报错，
     * 让整个快照失败，而不是像旧端点那样静默丢行或做字符串浮点求和。
     * 结果封装为 {@link PendSnapshotRow}；四个字段都不为 null（无行时 SUM 为 NULL，用 IFNULL 归 0）。
     */
    @Select("SELECT "
            + " IFNULL((SELECT SUM(CAST(goods_count AS DECIMAL(18,4))) FROM wm_im_notice_i WHERE bin_pre = 'N'), 0) AS receipt, "
            + " IFNULL((SELECT SUM(CAST(qm_ok_quat AS DECIMAL(18,4))) FROM wm_in_qm_i WHERE bin_sta = 'N'), 0) AS to_up, "
            + " IFNULL((SELECT SUM(CAST(qm_ok_quat AS DECIMAL(18,4))) FROM wm_om_qm_i WHERE bin_sta = 'I'), 0) AS pick, "
            + " IFNULL((SELECT SUM(CAST(qm_ok_quat AS DECIMAL(18,4))) FROM wm_om_qm_i WHERE bin_sta = 'N'), 0) AS cur_pick ")
    PendSnapshotRow selectPendSnapshot();

    /**
     * 四队列求和结果行。必须是可被 MyBatis 实例化的 JavaBean（无参构造 + setter），
     * 不能是接口：接口映射会抛 ReflectionException: Error instantiating interface … invalid types。
     * 列别名 cur_pick 经 map-underscore-to-camel-case 映射到 curPick。
     */
    class PendSnapshotRow {
        private BigDecimal receipt;
        private BigDecimal toUp;
        private BigDecimal pick;
        private BigDecimal curPick;

        public BigDecimal getReceipt() { return receipt; }
        public void setReceipt(BigDecimal receipt) { this.receipt = receipt; }
        public BigDecimal getToUp() { return toUp; }
        public void setToUp(BigDecimal toUp) { this.toUp = toUp; }
        public BigDecimal getPick() { return pick; }
        public void setPick(BigDecimal pick) { this.pick = pick; }
        public BigDecimal getCurPick() { return curPick; }
        public void setCurPick(BigDecimal curPick) { this.curPick = curPick; }
    }
}
