package com.zeroone.star.j5.basezl.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.support.SFunction;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.j5.basezl.entity.rfid.RfidBuseDO;
import com.zeroone.star.j5.basezl.entity.rfid.RfidBuseExcelDO;
import com.zeroone.star.j5.basezl.mapper.RFIDMapper;
import com.zeroone.star.j5.basezl.service.RFIDService;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.dto.PageDTO;
import com.zeroone.star.project.dto.j5.basezl.rfid.RFIDAddDTO;
import com.zeroone.star.project.dto.j5.basezl.rfid.RFIDDetailDTO;
import com.zeroone.star.project.dto.j5.basezl.rfid.RFIDListDTO;
import com.zeroone.star.project.dto.j5.basezl.rfid.RFIDModifyDTO;
import com.zeroone.star.project.query.j5.basezl.rfid.RFIDQuery;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.Resource;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * @author meiqin liu(叶子）
 * @date 2025/2/27 15:07
 */
@Slf4j
@Service("rfidService")
public class RFIDServiceImp extends ServiceImpl<RFIDMapper, RfidBuseDO> implements RFIDService {

    @Resource
    private EasyExcelComponent easyExcelComponent;

    @Override
    public PageDTO<RFIDListDTO> queryRFIDAll(RFIDQuery rfidQuery) {
        LambdaQueryWrapper<RfidBuseDO> queryWrapper = new LambdaQueryWrapper<>();
        // 动态构建查询条件
        addEqualIfPresent(queryWrapper, RfidBuseDO::getRfidType, rfidQuery.getType());
        addEqualIfPresent(queryWrapper, RfidBuseDO::getRfidBuseno, rfidQuery.getBuseCode());
        addEqualIfPresent(queryWrapper, RfidBuseDO::getRfidBusecont, rfidQuery.getBuseContent());
        addEqualIfPresent(queryWrapper, RfidBuseDO::getRfidId1, rfidQuery.getRfid1());
        // 创建人按模糊匹配，与导出保持一致
        if (StrUtil.isNotBlank(rfidQuery.getCreateName())) {
            queryWrapper.like(RfidBuseDO::getCreateName, rfidQuery.getCreateName());
        }
        queryWrapper.orderByDesc(RfidBuseDO::getId);

        Page<RfidBuseDO> page = new Page<>(rfidQuery.getPageIndex(), rfidQuery.getPageSize());
        this.page(page, queryWrapper);
        return PageDTO.create(page, RFIDListDTO.class);
    }

    private <T> void addEqualIfPresent(LambdaQueryWrapper<T> wrapper, SFunction<T, ?> column, String value) {
        if (StrUtil.isNotBlank(value)) {
            wrapper.eq(column, value);
        }
    }

    @Override
    public RFIDDetailDTO queryRFIDDetail(String rfid) {
        if (StrUtil.isBlank(rfid)) {
            throw new IllegalArgumentException("查询对象不能为空");
        }
        LambdaQueryWrapper<RfidBuseDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(RfidBuseDO::getRfidBuseno, rfid);
        RfidBuseDO entity = baseMapper.selectOne(queryWrapper);
        if (entity == null) {
            return null;
        }
        return BeanUtil.copyProperties(entity, RFIDDetailDTO.class);
    }

    @Override
    public String addRfid(RFIDAddDTO rfidAddDTO) {
        RfidBuseDO rfidBuseDO = BeanUtil.copyProperties(rfidAddDTO, RfidBuseDO.class);
        if (baseMapper.insert(rfidBuseDO) > 0) {
            return "添加成功";
        }
        return "添加失败";
    }

    @Override
    public String modifyRfid(RFIDModifyDTO rfidModifyDTO) {
        if (rfidModifyDTO == null || StrUtil.isBlank(rfidModifyDTO.getRfidBuseno())) {
            throw new IllegalArgumentException("对象不存在");
        }

        LambdaQueryWrapper<RfidBuseDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(RfidBuseDO::getRfidBuseno, rfidModifyDTO.getRfidBuseno());

        RfidBuseDO rfidBuseDO = BeanUtil.copyProperties(rfidModifyDTO, RfidBuseDO.class);
        if (baseMapper.update(rfidBuseDO, queryWrapper) > 0) {
            return "修改成功";
        }
        return "修改失败";
    }

    @Override
    public int deleteRfid(List<Long> rfidList) {
        if (rfidList == null || rfidList.isEmpty()) {
            throw new IllegalArgumentException("请选择要删除的数据");
        }
        return baseMapper.deleteBatchIds(rfidList);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public String importRfid(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("导入文件不能为空");
        }
        String filename = file.getOriginalFilename();
        if (filename == null || !(filename.toLowerCase().endsWith(".xls") || filename.toLowerCase().endsWith(".xlsx"))) {
            throw new IllegalArgumentException("仅支持 .xls/.xlsx 文件");
        }

        List<RfidBuseExcelDO> rows = easyExcelComponent.parseExcel(file, RfidBuseExcelDO.class);
        int skip = 0;
        int fail = 0;
        List<RfidBuseDO> toSave = new ArrayList<>();
        for (RfidBuseExcelDO row : rows) {
            if (row == null || (StrUtil.isBlank(row.getRfidId1()) && StrUtil.isBlank(row.getRfidBuseno()))) {
                fail++;
                continue;
            }
            LambdaQueryWrapper<RfidBuseDO> wrapper = new LambdaQueryWrapper<>();
            if (StrUtil.isNotBlank(row.getRfidId1())) {
                wrapper.eq(RfidBuseDO::getRfidId1, row.getRfidId1());
            } else {
                wrapper.eq(RfidBuseDO::getRfidBuseno, row.getRfidBuseno());
            }
            if (baseMapper.selectCount(wrapper) > 0) {
                skip++;
                continue;
            }
            RfidBuseDO entity = new RfidBuseDO();
            entity.setRfidType(row.getRfidType());
            entity.setRfidBuseno(row.getRfidBuseno());
            entity.setRfidBusecont(row.getRfidBusecont());
            entity.setRfidId1(row.getRfidId1());
            entity.setRfidId2(row.getRfidId2());
            entity.setRfidId3(row.getRfidId3());
            toSave.add(entity);
        }

        int success = 0;
        if (!toSave.isEmpty()) {
            boolean saved = this.saveBatch(toSave);
            if (!saved) {
                throw new RuntimeException("导入失败");
            }
            success = toSave.size();
        }
        log.info("RFID 导入完成：成功 {} 条，跳过 {} 条，失败 {} 条", success, skip, fail);
        return String.format("导入成功 %d 条，跳过重复 %d 条，失败 %d 条", success, skip, fail);
    }

    @Override
    public List<RfidBuseExcelDO> selectAll(RFIDQuery query) {
        LambdaQueryWrapper<RfidBuseDO> wrapper = new LambdaQueryWrapper<>();
        if (query != null) {
            if (StrUtil.isNotBlank(query.getCreateName())) {
                wrapper.like(RfidBuseDO::getCreateName, query.getCreateName());
            }
            if (StrUtil.isNotBlank(query.getType())) {
                wrapper.eq(RfidBuseDO::getRfidType, query.getType());
            }
            if (StrUtil.isNotBlank(query.getBuseCode())) {
                wrapper.eq(RfidBuseDO::getRfidBuseno, query.getBuseCode());
            }
            if (StrUtil.isNotBlank(query.getBuseContent())) {
                wrapper.eq(RfidBuseDO::getRfidBusecont, query.getBuseContent());
            }
            if (StrUtil.isNotBlank(query.getRfid1())) {
                wrapper.eq(RfidBuseDO::getRfidId1, query.getRfid1());
            }
        }
        return baseMapper.selectList(wrapper).stream().map(this::toExcelDO).collect(Collectors.toList());
    }

    @Override
    public List<RfidBuseExcelDO> selectByIds(List<Long> ids) {
        if (ids == null || ids.isEmpty()) {
            return new ArrayList<>();
        }
        return baseMapper.selectBatchIds(ids).stream().map(this::toExcelDO).collect(Collectors.toList());
    }

    private RfidBuseExcelDO toExcelDO(RfidBuseDO source) {
        RfidBuseExcelDO target = new RfidBuseExcelDO();
        target.setCreateName(source.getCreateName());
        if (source.getCreateDate() != null) {
            target.setCreateDate(Timestamp.valueOf(source.getCreateDate()));
        }
        target.setRfidType(source.getRfidType());
        target.setRfidBuseno(source.getRfidBuseno());
        target.setRfidBusecont(source.getRfidBusecont());
        target.setRfidId1(source.getRfidId1());
        target.setRfidId2(source.getRfidId2());
        target.setRfidId3(source.getRfidId3());
        return target;
    }
}
