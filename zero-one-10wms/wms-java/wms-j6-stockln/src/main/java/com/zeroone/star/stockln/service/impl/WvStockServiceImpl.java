package com.zeroone.star.stockln.service.impl;

import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.project.dto.PageDTO;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.project.dto.j6.stockln.WvStockDTO;
import com.zeroone.star.project.query.j6.stockln.WvStockQuery;
import com.zeroone.star.stockln.entity.WvStock;
import com.zeroone.star.stockln.mapper.WvStockMapper;
import com.zeroone.star.stockln.service.IWvStockService;
import org.mapstruct.Mapper;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.ArrayList;
import java.util.List;

@Mapper(componentModel = "spring")
interface MsWvStockMapper{
    WvStockDTO MsWvStockToWvStockDTO(WvStock wvStock);
}
/**
 * <p>
 * VIEW 服务实现类
 * </p>
 *
 * @author smt
 * @since 2025-03-07
 */
@Service
public class WvStockServiceImpl extends ServiceImpl<WvStockMapper, WvStock> implements IWvStockService {
    @Resource
    MsWvStockMapper msMapper;
    @Override
    public PageDTO<WvStockDTO> listallStock(WvStockQuery query) {
        long pageIndex = query.getPageIndex() > 0 ? query.getPageIndex() : 1;
        long pageSize = query.getPageSize() > 0 ? query.getPageSize() : 10;
        //分页对象
        Page<WvStock> page = new Page<>(pageIndex, pageSize);
        Page<WvStock> ps = baseMapper.selectPage(page, buildWrapper(query));
        return PageDTO.create(ps, msMapper::MsWvStockToWvStockDTO);
    }

    @Override
    public List<WvStockDTO> listAllForExport(WvStockQuery query) {
        List<WvStock> list = baseMapper.selectList(buildWrapper(query));
        List<WvStockDTO> result = new ArrayList<>();
        for (WvStock stock : list) {
            result.add(msMapper.MsWvStockToWvStockDTO(stock));
        }
        return result;
    }

    private QueryWrapper<WvStock> buildWrapper(WvStockQuery query) {
        //查询对象（视图列名为下划线，且未传条件时不能拼接 like）
        QueryWrapper<WvStock> wrapper = new QueryWrapper<>();
        if (StrUtil.isNotBlank(query.getKuWeiBianMa())) {
            wrapper.like("ku_wei_bian_ma", query.getKuWeiBianMa());
        }
        if (StrUtil.isNotBlank(query.getBinId())) {
            wrapper.like("bin_id", query.getBinId());
        }
        if (StrUtil.isNotBlank(query.getCusCode())) {
            wrapper.like("cus_code", query.getCusCode());
        }
        if (StrUtil.isNotBlank(query.getZhongWenQch())) {
            wrapper.like("zhong_wen_qch", query.getZhongWenQch());
        }
        if (StrUtil.isNotBlank(query.getGoodsCode())) {
            wrapper.like("goods_code", query.getGoodsCode());
        }
        if (StrUtil.isNotBlank(query.getShpMingCheng())) {
            wrapper.like("shp_ming_cheng", query.getShpMingCheng());
        }
        return wrapper;
    }
}
