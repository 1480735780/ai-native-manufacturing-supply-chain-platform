package com.zeroone.star.stockln.controller;

import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.query.j6.stockln.MvStockCusQuery;
import com.zeroone.star.project.vo.JsonVO;
import com.zeroone.star.stockln.entity.MvStockCus;
import com.zeroone.star.stockln.mapper.MvStockCusMapper;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;

/**
 * 客户库存报表
 */
@Api(tags = "客户库存报表")
@RestController
@RequestMapping("/stock/customer-stock")
public class CustomerStockController {

    @Resource
    private MvStockCusMapper mvStockCusMapper;

    @GetMapping("query-all")
    @ApiOperation(value = "分页查询客户库存")
    public JsonVO<PageDTO<MvStockCus>> queryAll(MvStockCusQuery query) {
        long pageIndex = query.getPageIndex() > 0 ? query.getPageIndex() : 1;
        long pageSize = query.getPageSize() > 0 ? query.getPageSize() : 10;

        QueryWrapper<MvStockCus> wrapper = new QueryWrapper<>();
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
        wrapper.orderByAsc("cus_code").orderByAsc("dqr");

        Page<MvStockCus> page = mvStockCusMapper.selectPage(new Page<>(pageIndex, pageSize), wrapper);
        return JsonVO.success(PageDTO.create(page));
    }
}
