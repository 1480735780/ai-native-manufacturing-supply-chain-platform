package com.zeroone.star.daycheck.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.daycheck.entity.YichangDown;
import com.zeroone.star.project.query.j3.daycheck.Arr.YichangDownQuery;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface YichangDownMapper extends BaseMapper<YichangDown> {

    /** 旧页面端点：select * 契约不变，仅新增确定性排序防止翻页抖动。 */
    Page<YichangDown> getYichangDownPage(Page<YichangDown> page, @Param("query") YichangDownQuery condition);

    /** 巡检专用：显式列清单 + wtdg.id 稳定行键 + create_date/id 稳定排序，返回 total/pages。 */
    Page<YichangDown> getYichangDownForInspection(Page<YichangDown> page, @Param("query") YichangDownQuery condition);
}
