package com.zeroone.star.daycheck.service;

import com.zeroone.star.daycheck.entity.NoUpGoods;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.daycheck.Arr.NoUpGoodsDTO;
import com.zeroone.star.project.query.j3.daycheck.Arr.NoUpGoodsQuery;

import java.util.List;

public interface NoUpService {
    List<NoUpGoodsDTO> getNoUpGoodsPage(NoUpGoodsQuery condition);

    /**
     * 巡检专用分页查询：与旧方法共用同一 Mapper 分页查询，但额外返回 total/pages。
     */
    PageDTO<NoUpGoodsDTO> getNoUpGoodsPageDTO(NoUpGoodsQuery condition);

    List<NoUpGoods> getDate();
}
