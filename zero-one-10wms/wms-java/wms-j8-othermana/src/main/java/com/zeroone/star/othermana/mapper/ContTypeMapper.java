package com.zeroone.star.othermana.mapper;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.zeroone.star.othermana.entity.BaContType;

import com.zeroone.star.project.dto.j8.other.baconttype.BaContTypeDTO;
import com.zeroone.star.project.query.j8.other.baconttype.BaContTypeQuery;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import org.springframework.util.StringUtils;

import java.util.List;

@Mapper
public interface ContTypeMapper extends BaseMapper<BaContType> {

    default Page<BaContType> selectByQuery(BaContTypeQuery query){
        Page<BaContType> page=new Page<>(query.getPageIndex(), query.getPageSize());
        QueryWrapper<BaContType> wrapper=new QueryWrapper<>();
        wrapper.select("id","cont_type_code","cont_type_name");
        boolean hasId = StringUtils.hasText(query.getId());
        boolean hasCode = StringUtils.hasText(query.getContTypeCode());
        boolean hasName = StringUtils.hasText(query.getContTypeName());
        // 仅在条件非空时拼接，避免空条件生成 LIKE null 导致查询结果为空
        if (hasId || hasCode || hasName) {
            wrapper.and(w -> {
                if (hasId) w.like("id", query.getId());
                if (hasCode) {
                    if (hasId) w.or();
                    w.like("cont_type_code", query.getContTypeCode());
                }
                if (hasName) {
                    if (hasId || hasCode) w.or();
                    w.like("cont_type_name", query.getContTypeName());
                }
            });
        }
        return this.selectPage(page,wrapper);
    }

    default List<BaContType> selectAll(){
        QueryWrapper<BaContType> wrapper=new QueryWrapper<>();
        wrapper.select("id","cont_type_code","cont_type_name");
        return this.selectList(wrapper);
    }
}
