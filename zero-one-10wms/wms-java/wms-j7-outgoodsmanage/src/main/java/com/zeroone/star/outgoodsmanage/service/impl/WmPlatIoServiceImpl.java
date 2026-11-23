package com.zeroone.star.outgoodsmanage.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.outgoodsmanage.entity.WmPlatIo;
import com.zeroone.star.outgoodsmanage.mapper.WmPlatIoMapper;
import com.zeroone.star.outgoodsmanage.service.IWmPlatIoService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j7.outbound.WmPlatIoDTO;
import com.zeroone.star.project.query.j7.outbound.WmPlatIoQuery;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * <p>
 * 月台计划 服务实现类
 * </p>
 *
 * @author lenyan
 * @since 2025-02-21
 */
@Service
public class WmPlatIoServiceImpl extends ServiceImpl<WmPlatIoMapper, WmPlatIo> implements IWmPlatIoService {

    @Override
    public PageDTO<WmPlatIoDTO> listPlatIo(WmPlatIoQuery query) {
        // 构造查询条件
        QueryWrapper<WmPlatIo> wrapper = new QueryWrapper<>();
        if (StringUtils.hasText(query.getCarno())) {
            wrapper.like("carno", query.getCarno());
        }
        if (StringUtils.hasText(query.getDocId())) {
            wrapper.eq("doc_id", query.getDocId());
        }
        if (StringUtils.hasText(query.getPlatId())) {
            wrapper.eq("plat_id", query.getPlatId());
        }
        if (StringUtils.hasText(query.getPlatSta())) {
            wrapper.eq("plat_sta", query.getPlatSta());
        }
        wrapper.orderByDesc("create_date");
        // 分页查询
        Page<WmPlatIo> page = new Page<>(query.getPageIndex(), query.getPageSize());
        Page<WmPlatIo> result = page(page, wrapper);
        // 转换为DTO（Spring BeanUtils 属性同名拷贝）
        List<WmPlatIoDTO> rows = new ArrayList<>();
        for (WmPlatIo record : result.getRecords()) {
            WmPlatIoDTO dto = new WmPlatIoDTO();
            BeanUtils.copyProperties(record, dto);
            rows.add(dto);
        }
        PageDTO<WmPlatIoDTO> pageDTO = new PageDTO<>();
        pageDTO.setTotal(result.getTotal());
        pageDTO.setPageIndex(result.getCurrent());
        pageDTO.setPageSize(result.getSize());
        pageDTO.setPages(result.getPages());
        pageDTO.setRows(rows);
        return pageDTO;
    }

    @Override
    public WmPlatIoDTO addPlatIo(WmPlatIoDTO dto) {
        // 参数校验：车号/单据/月台必填
        if (!StringUtils.hasText(dto.getCarno()) || !StringUtils.hasText(dto.getDocId())
                || !StringUtils.hasText(dto.getPlatId())) {
            throw new IllegalArgumentException("车号、单据编号、月台编号不能为空");
        }
        // 幂等键检查：doc_id + plat_id + plan_indata
        QueryWrapper<WmPlatIo> dup = new QueryWrapper<>();
        dup.eq("doc_id", dto.getDocId()).eq("plat_id", dto.getPlatId());
        if (dto.getPlanIndata() != null) {
            dup.eq("plan_indata", dto.getPlanIndata());
        }
        if (count(dup) > 0) {
            throw new IllegalArgumentException("该单据在指定月台与计划进入时间已存在月台计划");
        }
        // 填充审计字段
        LocalDateTime now = LocalDateTime.now();
        dto.setId(UUID.randomUUID().toString().replace("-", ""));
        dto.setCreateDate(now);
        WmPlatIo entity = new WmPlatIo();
        BeanUtils.copyProperties(dto, entity);
        save(entity);
        return dto;
    }

    @Override
    public WmPlatIoDTO updatePlatIo(WmPlatIoDTO dto) {
        if (!StringUtils.hasText(dto.getId())) {
            throw new IllegalArgumentException("月台计划id不能为空");
        }
        WmPlatIo exist = getById(dto.getId());
        if (exist == null) {
            throw new IllegalArgumentException("月台计划不存在");
        }
        dto.setUpdateDate(LocalDateTime.now());
        WmPlatIo entity = new WmPlatIo();
        BeanUtils.copyProperties(dto, entity);
        updateById(entity);
        return dto;
    }
}
