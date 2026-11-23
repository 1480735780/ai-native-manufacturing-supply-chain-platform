package com.zeroone.star.baseConfig.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.baseConfig.entity.BaUnitType;
import com.zeroone.star.baseConfig.mapper.BaUnitTypeMapper;
import com.zeroone.star.baseConfig.service.BaUnitTypeService;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j4.unitType.UnitTypeListDTO;
import com.zeroone.star.project.query.j4.unitType.UnitTypeListQuery;
import com.zeroone.star.project.vo.JsonVO;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.util.List;
import java.util.stream.Collectors;

/**
 * @author 1+5
 * @title
 * @date 2025/2/23 23 11
 * @description
 */

@Service
@Transactional
public class BaUnitTypeServiceImpl extends ServiceImpl<BaUnitTypeMapper, BaUnitType> implements BaUnitTypeService {


    @Resource
    BaUnitTypeMapper mapper;

    @Override
    public JsonVO<List<String>> getUnitTypeNameList() {

        // 设置查询条件
        QueryWrapper<BaUnitType> wrapper = new QueryWrapper<>();

        // 执行查询获取所有记录
        List<BaUnitType> baUnitTypeList = mapper.selectList(wrapper);

        // 提取名称列表
        List<String> nameList = baUnitTypeList.stream()
                .map(BaUnitType::getUnitTypeName)
                .collect(Collectors.toList());

        // 返回
        return JsonVO.success(nameList);
    }
    @Override
    public JsonVO<PageDTO<UnitTypeListDTO>> getUnitTypeList(UnitTypeListQuery unitTypeListQuery) {

        //设置查询条件
        QueryWrapper<BaUnitType> wrapper = new QueryWrapper<>();

        //排序参考（列名），未传时默认按更新时间排序
        String sortColumn = isBlank(unitTypeListQuery.getSort()) ? "update_date" : unitTypeListQuery.getSort();
        if ("desc".equalsIgnoreCase(unitTypeListQuery.getOrder())) {
            wrapper.orderByDesc(sortColumn);
        } else {
            wrapper.orderByAsc(sortColumn);
        }

        //设置分页参数
        long pageIndex = unitTypeListQuery.getPageIndex() > 0 ? unitTypeListQuery.getPageIndex() : 1;
        long pageSize = unitTypeListQuery.getPageSize() > 0 ? unitTypeListQuery.getPageSize() : 10;
        Page<BaUnitType> page = new Page<>(pageIndex, pageSize);

        // 执行分页查询
        Page<BaUnitType> baUnitTypePage = mapper.selectPage(page, wrapper);

        //转换成VO
        PageDTO<UnitTypeListDTO> unitTypeListDTOPageDTO = new PageDTO<UnitTypeListDTO>().create(baUnitTypePage, UnitTypeListDTO.class);

        //返回
        return JsonVO.success(unitTypeListDTOPageDTO);


    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
