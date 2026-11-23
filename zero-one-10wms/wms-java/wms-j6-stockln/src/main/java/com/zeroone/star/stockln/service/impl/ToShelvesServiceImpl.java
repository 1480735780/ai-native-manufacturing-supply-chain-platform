package com.zeroone.star.stockln.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.IdWorker;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j6.stockln.InboundQmIDTO;
import com.zeroone.star.project.dto.j6.stockln.ModifyShelvesDTO;
import com.zeroone.star.project.dto.j6.stockln.ToShelvesDTO;
import com.zeroone.star.project.query.j6.stockln.ToShelvesQuery;
import com.zeroone.star.stockln.entity.MdGoods;
import com.zeroone.star.stockln.entity.ToShelves;
import com.zeroone.star.stockln.entity.WmToUpGoods;
import com.zeroone.star.stockln.mapper.MdGoodsMapper;
import com.zeroone.star.stockln.mapper.ToShelvesMapper;
import com.zeroone.star.stockln.mapper.WmToUpGoodsMapper;
import com.zeroone.star.stockln.service.IToShelvesService;
import org.mapstruct.Mapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Mapper(componentModel = "spring")
interface MsItemMapper {
    InboundQmIDTO ToShelvesToInboundQmIDTO(ToShelves toShelves);
}

@Service
public class ToShelvesServiceImpl extends ServiceImpl<ToShelvesMapper, ToShelves> implements IToShelvesService {
    @Resource
    MsItemMapper itemMapper;
    @Resource
    ToShelvesMapper toShelvesMapper;
    @Resource
    WmToUpGoodsMapper wmToUpGoodsMapper;
    @Resource
    MdGoodsMapper mdGoodsMapper;


    @Override
    public PageDTO<InboundQmIDTO> listall(ToShelvesQuery toShelvesQuery) {
        // 分页对象
        Page<ToShelves> page = new Page<>(toShelvesQuery.getPageIndex(), toShelvesQuery.getPageSize());
        QueryWrapper<ToShelves> wrapper = buildQueryWrapper(toShelvesQuery);
        Page<ToShelves> ps = baseMapper.selectPage(page, wrapper);
        return PageDTO.create(ps, itemMapper::ToShelvesToInboundQmIDTO);
    }

    @Override
    public List<InboundQmIDTO> listAllForExport(ToShelvesQuery query) {
        List<ToShelves> list = baseMapper.selectList(buildQueryWrapper(query));
        List<InboundQmIDTO> result = new ArrayList<>();
        for (ToShelves item : list) {
            result.add(itemMapper.ToShelvesToInboundQmIDTO(item));
        }
        return result;
    }

    @Override
    public PageDTO<InboundQmIDTO> listNotShelved(ToShelvesQuery query) {
        Page<ToShelves> page = new Page<>(query.getPageIndex(), query.getPageSize());
        Page<ToShelves> ps = baseMapper.selectPage(page, buildNotShelvedWrapper(query));
        return PageDTO.create(ps, itemMapper::ToShelvesToInboundQmIDTO);
    }

    @Override
    public List<InboundQmIDTO> listNotShelvedForExport(ToShelvesQuery query) {
        List<ToShelves> list = baseMapper.selectList(buildNotShelvedWrapper(query));
        List<InboundQmIDTO> result = new ArrayList<>();
        for (ToShelves item : list) {
            result.add(itemMapper.ToShelvesToInboundQmIDTO(item));
        }
        return result;
    }

    private QueryWrapper<ToShelves> buildNotShelvedWrapper(ToShelvesQuery query) {
        QueryWrapper<ToShelves> wrapper = buildQueryWrapper(query);
        wrapper.and(w -> w.ne("bin_sta", "Y").or().isNull("bin_sta"));
        return wrapper;
    }

    private QueryWrapper<ToShelves> buildQueryWrapper(ToShelvesQuery query) {
        QueryWrapper<ToShelves> wrapper = new QueryWrapper<>();
        if (StrUtil.isNotBlank(query.getImNoticeId())) {
            wrapper.like("im_notice_id", query.getImNoticeId());
        }
        if (StrUtil.isNotBlank(query.getCusCode())) {
            wrapper.like("cus_code", query.getCusCode());
        }
        if (StrUtil.isNotBlank(query.getGoodsId())) {
            wrapper.like("goods_id", query.getGoodsId());
        }
        if (StrUtil.isNotBlank(query.getGoodsName())) {
            wrapper.like("goods_name", query.getGoodsName());
        }
        if (StrUtil.isNotBlank(query.getTinId())) {
            wrapper.like("tin_id", query.getTinId());
        }
        if (StrUtil.isNotBlank(query.getBinId())) {
            wrapper.like("bin_id", query.getBinId());
        }
        if (StrUtil.isNotBlank(query.getCusName())) {
            wrapper.like("cus_name", query.getCusName());
        }
        if (StrUtil.isNotBlank(query.getBinSta())) {
            wrapper.eq("bin_sta", query.getBinSta());
        }
        // 按入库通知单的订单类型过滤（子查询：只保留指定订单类型的通知单明细）
        if (StrUtil.isNotBlank(query.getOrderTypeCode())) {
            wrapper.inSql(
                    "im_notice_id",
                    "SELECT notice_id FROM wm_im_notice_h WHERE order_type_code = '"
                            + query.getOrderTypeCode().replace("'", "''") + "'");
        }
        wrapper.orderByDesc("create_date");
        return wrapper;
    }

    //
//    @Override
//    public void insertItem(InboundQmIDTO dto) {
//        ToShelves mdItem = BeanUtil.copyProperties(dto, ToShelves.class);
//        //TODO 需要添加创造人，新建时间等属性
//        this.save(mdItem);
//    }
    @Override
    public void insertItem(ToShelvesDTO dto) {
        this.save(toEntity(dto));
    }

    @Override
    @Transactional
    public int importItems(List<ToShelvesDTO> items) {
        if (items == null || items.isEmpty()) {
            return 0;
        }
        List<ToShelves> entities = new ArrayList<>();
        for (ToShelvesDTO dto : items) {
            entities.add(toEntity(dto));
        }
        saveBatch(entities);
        return entities.size();
    }

    private ToShelves toEntity(ToShelvesDTO dto) {
        ToShelves toShelves = new ToShelves();
        toShelves.setImNoticeId(dto.getImNoticeId());
        toShelves.setGoodsId(dto.getGoodsId());
        toShelves.setCusCode(dto.getCusCode());
        toShelves.setBinId(dto.getBinId());
        toShelves.setImQuat(dto.getImQuat());
        toShelves.setQmOkQuat(dto.getImQuat());
        toShelves.setProData(dto.getProData());
        toShelves.setGoodsBatch(dto.getGoodsBatch());
        toShelves.setRecDeg(dto.getRecDeg());
        toShelves.setItemText(dto.getItemText());
        toShelves.setTinId(dto.getTinId());
        toShelves.setBaseInGoodscount(dto.getBaseInGoodscount());
        toShelves.setBinSta("N");

        LocalDateTime now = LocalDateTime.now();
        toShelves.setCreateDate(now);
        toShelves.setUpdateDate(now);
        fillGoodsInfo(toShelves);
        return toShelves;
    }

    private void fillGoodsInfo(ToShelves toShelves) {
        if (StrUtil.isBlank(toShelves.getGoodsId())) {
            return;
        }
        MdGoods goods = mdGoodsMapper.selectOne(new QueryWrapper<MdGoods>()
                .eq("shp_bian_ma", toShelves.getGoodsId()));
        if (goods == null) {
            return;
        }
        toShelves.setGoodsName(goods.getShpMingCheng());
        toShelves.setGoodsUnit(goods.getShlDanWei());
        toShelves.setBaseUnit(goods.getJshDanWei());
        toShelves.setSysOrgCode(goods.getSysOrgCode());
        toShelves.setSysCompanyCode(goods.getSysCompanyCode());
    }


    @Override
    public boolean deleteById(String id) {
        int result = toShelvesMapper.deleteById(id);
        return result > 0;
    }

    @Override
    public InboundQmIDTO myGetById(String id) {
        ToShelves entity = this.getById(id);
        InboundQmIDTO productDTO = BeanUtil.copyProperties(entity, InboundQmIDTO.class);
        return productDTO;
    }

    @Override
    public boolean modifyShelvesInfo(ModifyShelvesDTO dto) {
        // 根据 id 查询记录
        ToShelves existingItem = toShelvesMapper.selectById(dto.getId());

        // 如果记录存在，则更新相关字段
        if (existingItem != null) {
            // 只更新用户可以修改的字段
            existingItem.setTinId(dto.getTinId());
            existingItem.setBinId(dto.getBinId());
            existingItem.setQmOkQuat(dto.getQmOkQuat());
            existingItem.setTinTj(dto.getTinTj());
            existingItem.setTinZhl(dto.getTinZhl());
            existingItem.setProData(dto.getProData());
            existingItem.setGoodsBatch(dto.getGoodsBatch());
            existingItem.setRecDeg(dto.getRecDeg());
            existingItem.setItemText(dto.getItemText());
            existingItem.setBaseInGoodscount(dto.getBaseInGoodscount());
            existingItem.setBaseOutGoodscount(dto.getBaseOutGoodscount());

            // 执行更新操作，使用主键 id 来更新记录
            return toShelvesMapper.updateById(existingItem) > 0; // 如果更新成功，返回 true
        } else {
            return false; // 如果没有找到记录，返回 false
        }
    }

    @Override
    public boolean batchModifyBin(List<String> ids, String binId) {
        // 使用 UpdateWrapper 构建批量更新条件
        UpdateWrapper<ToShelves> updateWrapper = new UpdateWrapper<>();
        updateWrapper.in("id", ids); // 设置需要更新的记录的 id 列表
        updateWrapper.set("bin_id", binId); // 设置新的储位值
        updateWrapper.set("update_date", LocalDateTime.now());

        // 执行批量更新操作
        int rowsUpdated = toShelvesMapper.update(null, updateWrapper);

        // 如果更新的行数大于 0，说明更新成功
        return rowsUpdated > 0;
    }

    @Override
    public boolean batchModifyProductionDate(List<String> ids, String proData) {
        UpdateWrapper<ToShelves> updateWrapper = new UpdateWrapper<>();
        updateWrapper.in("id", ids);
        updateWrapper.set("pro_data", proData);
        updateWrapper.set("update_date", LocalDateTime.now());
        return toShelvesMapper.update(null, updateWrapper) > 0;
    }

    @Override
    @Transactional
    public int batchShelf(List<String> ids) {
        if (ids == null || ids.isEmpty()) {
            return 0;
        }
        List<ToShelves> list = listByIds(ids);
        int success = 0;
        for (ToShelves item : list) {
            if ("Y".equals(item.getBinSta())) {
                continue;
            }
            // 写入库存上架记录，供库存查询视图使用
            Long exists = wmToUpGoodsMapper.selectCount(new QueryWrapper<WmToUpGoods>()
                    .eq("wm_to_up_id", item.getId()));
            if (exists == null || exists == 0) {
                WmToUpGoods up = new WmToUpGoods();
                up.setId(String.valueOf(IdWorker.getId()));
                up.setGoodsId(item.getGoodsId());
                up.setGoodsQua(StrUtil.isNotBlank(item.getQmOkQuat()) ? item.getQmOkQuat() : item.getImQuat());
                up.setOrderTypeCode("IO");
                up.setOrderId(item.getImNoticeId());
                up.setOrderIdI(item.getId());
                up.setWmToUpId(item.getId());
                up.setGoodsUnit(item.getGoodsUnit());
                up.setGoodsBatch(item.getGoodsBatch());
                up.setGoodsProData(item.getProData());
                up.setActTypeCode("上架");
                up.setKuWeiBianMa(item.getBinId());
                up.setBinId(item.getTinId());
                up.setCusCode(item.getCusCode());
                up.setBaseUnit(item.getBaseUnit());
                up.setBaseGoodscount(StrUtil.isNotBlank(item.getBaseInGoodscount())
                        ? item.getBaseInGoodscount() : item.getQmOkQuat());
                up.setGoodsName(item.getGoodsName());
                up.setSysOrgCode(item.getSysOrgCode());
                up.setSysCompanyCode(item.getSysCompanyCode());
                up.setCreateName("system");
                up.setCreateBy("system");
                up.setCreateDate(LocalDateTime.now());
                up.setUpdateDate(LocalDateTime.now());
                wmToUpGoodsMapper.insert(up);
            }
            UpdateWrapper<ToShelves> updateWrapper = new UpdateWrapper<>();
            updateWrapper.eq("id", item.getId());
            updateWrapper.set("bin_sta", "Y");
            updateWrapper.set("update_date", LocalDateTime.now());
            toShelvesMapper.update(null, updateWrapper);
            success++;
        }
        return success;
    }

//    /**
//     * 根据id查询待上架货物详细信息
//     * @param id
//     * @return
//     */
//    public ToShelves getInfo(String id){
//        return toShelvesMapper.selectById(id);
//    }
}
