package com.zeroone.star.daycheck.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.daycheck.entity.NoUpGoods;
import com.zeroone.star.project.query.j3.daycheck.Arr.NoUpGoodsQuery;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface NoUpMapper extends BaseMapper {
    /** 旧页面端点：不过滤 bin_sta（页面按 N/I/Y 三态展示库存状态），契约不变。 */
    Page<NoUpGoods> getNoUpGoodsPage(Page<NoUpGoods> page, @Param("query") NoUpGoodsQuery condition);

    /** 巡检专用：只取未上架（bin_sta='N'，兼容历史 NULL），显式列清单 + 稳定排序，返回 total/pages。 */
    Page<NoUpGoods> getNoUpGoodsForInspection(Page<NoUpGoods> page, @Param("query") NoUpGoodsQuery condition);
}
