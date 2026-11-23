package com.zeroone.star.stockln.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import cn.hutool.core.util.StrUtil;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.stockln.ImportNoticeListDTO;
import com.zeroone.star.project.query.j6.stockln.ImportNoticeQuery;
import com.zeroone.star.stockln.entity.WmImNoticeH;
import com.zeroone.star.stockln.mapper.WmImNoticeHMapper;
import com.zeroone.star.stockln.service.IWmImNoticeHService;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import org.mapstruct.Mapper;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.util.List;


@Mapper(componentModel = "spring")
interface MsWmImNoticeHMapper{
    ImportNoticeListDTO WmImNoticeHToWmImNoticeHDTO(WmImNoticeH wmImNoticeH);
}


/**
 * <p>
 * 预约进货通知抬头 服务实现类
 * </p>
 *
 * @author juhao
 * @since 2025-03-06
 */
@Service
public class WmImNoticeHServiceImpl extends ServiceImpl<WmImNoticeHMapper, WmImNoticeH> implements IWmImNoticeHService {

    @Resource
    MsWmImNoticeHMapper msWmImNoticeHMapper;

    @Override
    public PageDTO<ImportNoticeListDTO> listAll(ImportNoticeQuery query) {

        Page<ImportNoticeListDTO> page = new Page<>(query.getPageIndex(), query.getPageSize());
        QueryWrapper<WmImNoticeH> wrapper = new QueryWrapper<>();
        if (StrUtil.isNotBlank(query.getNoticeId()))
            wrapper.like("notice_id", query.getNoticeId());
        if (StrUtil.isNotBlank(query.getCusCode()))
            wrapper.eq("cus_code", query.getCusCode());
        if (StrUtil.isNotBlank(query.getImCusCode()))
            wrapper.like("im_cus_code", query.getImCusCode());
        if (StrUtil.isNotBlank(query.getSupCode()))
            wrapper.like("sup_code", query.getSupCode());
        if (StrUtil.isNotBlank(query.getSupName()))
            wrapper.like("sup_name", query.getSupName());
        if (StrUtil.isNotBlank(query.getOrderTypeCode()))
            wrapper.eq("order_type_code", query.getOrderTypeCode());
        if (StrUtil.isNotBlank(query.getImSta()))
            wrapper.like("im_sta", query.getImSta());
        if (StrUtil.isNotBlank(query.getImCarDri()))
            wrapper.like("im_car_dri", query.getImCarDri());
        if (StrUtil.isNotBlank(query.getImCarNo()))
            wrapper.like("im_car_no",query.getImCarNo());
        if (query.getImDataBegin() != null && query.getImDataEnd() != null)
            wrapper.between("create_date", query.getImDataBegin(), query.getImDataEnd());

//        Page<WmImNoticeH> ps = baseMapper.selectPage(page, wrapper);
//        List<ImportNoticeListDTO> list_ =  baseMapper.searchAll(page, wrapper);
         page = baseMapper.searchAll(page, wrapper);

        return PageDTO.create(page, (s)->s);
    }


}
