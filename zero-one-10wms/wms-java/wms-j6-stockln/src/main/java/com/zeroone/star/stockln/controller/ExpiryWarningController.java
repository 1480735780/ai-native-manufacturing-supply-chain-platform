package com.zeroone.star.stockln.controller;

import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.query.j6.stockln.MvStockYjQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.stockln.entity.MvStockYj;
import com.zeroone.star.stockln.mapper.MvStockYjMapper;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;

/**
 * 效期预警报表
 */
@Api(tags = "效期预警报表")
@RestController
@RequestMapping("/stock/expiry-warning")
public class ExpiryWarningController {

    @Resource
    private MvStockYjMapper mvStockYjMapper;

    @GetMapping("query-all")
    @ApiOperation(value = "分页查询效期预警")
    public JsonVO<PageDTO<MvStockYj>> queryAll(MvStockYjQuery query) {
        long pageIndex = query.getPageIndex() > 0 ? query.getPageIndex() : 1;
        long pageSize = query.getPageSize() > 0 ? query.getPageSize() : 10;

        QueryWrapper<MvStockYj> wrapper = new QueryWrapper<>();
        if (StrUtil.isNotBlank(query.getCusCode())) {
            wrapper.like("cus_code", query.getCusCode());
        }
        if (StrUtil.isNotBlank(query.getZhongWenQch())) {
            wrapper.like("zhong_wen_qch", query.getZhongWenQch());
        }
        if (StrUtil.isNotBlank(query.getGoodsId())) {
            wrapper.like("goods_id", query.getGoodsId());
        }
        if (StrUtil.isNotBlank(query.getShpMingCheng())) {
            wrapper.like("shp_ming_cheng", query.getShpMingCheng());
        }
        wrapper.orderByAsc("dqr");

        Page<MvStockYj> page = mvStockYjMapper.selectPage(new Page<>(pageIndex, pageSize), wrapper);
        return JsonVO.success(PageDTO.create(page));
    }
}
