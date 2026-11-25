package com.zeroone.star.daycheck.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.daycheck.entity.NoUpGoods;
import com.zeroone.star.daycheck.mapper.NoUpMapper;
import com.zeroone.star.daycheck.service.NoUpService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j3.daycheck.Arr.NoUpGoodsDTO;
import com.zeroone.star.project.query.j3.daycheck.Arr.NoUpGoodsQuery;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.*;

/**
 * @author aaa
 * @version 1.0
 * @description TODO
 * @date 2025/2/27 10:30
 */
@Service
public class NoUpServiceImpl implements NoUpService {

    @Resource
    NoUpMapper noUpMapper;

    Map<String,List<NoUpGoods>> data ;

    @Override
    public List<NoUpGoodsDTO> getNoUpGoodsPage(NoUpGoodsQuery condition) {
        data = new HashMap<>();
        Page<NoUpGoods> page = new Page<>(condition.getPageIndex(), condition.getPageSize());
        // 旧页面端点：沿用旧语句（不过滤 bin_sta），DTO 不带 rowId/noticeId，契约不变
        Page<NoUpGoods> pages = noUpMapper.getNoUpGoodsPage(page, condition);
        ArrayList<NoUpGoodsDTO> result = new ArrayList<>();
        for(NoUpGoods noUpGoods : pages.getRecords()){
            result.add(toDTO(noUpGoods, false));
        }
        data.put("a1",pages.getRecords());
        return result;
    }

    @Override
    public PageDTO<NoUpGoodsDTO> getNoUpGoodsPageDTO(NoUpGoodsQuery condition) {
        Page<NoUpGoods> page = new Page<>(condition.getPageIndex(), condition.getPageSize());
        // 巡检专用语句：未上架口径 + 显式列 + 稳定排序；不再复用旧页面的 select *
        Page<NoUpGoods> pages = noUpMapper.getNoUpGoodsForInspection(page, condition);
        data = new HashMap<>();
        data.put("a1", pages.getRecords());
        // 与旧方法共用字段映射，额外透传 MyBatis-Plus 的 total/pages 与稳定行键
        return PageDTO.create(pages, src -> toDTO(src, true));
    }

    /**
     * 实体 → DTO。BeanUtils 只按同名属性拷贝：实体 id/im_notice_id 与 DTO rowId/noticeId
     * 名字不同，必须显式赋值，否则巡检侧拿到的 rowId/noticeId 永远为 null。
     *
     * @param withIdentity 是否输出巡检行键（旧端点传 false，保持旧 JSON 不变）
     */
    static NoUpGoodsDTO toDTO(NoUpGoods src, boolean withIdentity) {
        NoUpGoodsDTO dto = new NoUpGoodsDTO();
        BeanUtils.copyProperties(src, dto);
        dto.setKucunsta(src.getBin_sta());
        dto.setShl_dan_wei(src.getGoods_unit());
        if (withIdentity) {
            dto.setRowId(src.getId());
            dto.setNoticeId(src.getIm_notice_id());
        }
        return dto;
    }

    @Override
    public List<NoUpGoods> getDate() {
        return data.get("a1");
    }
}