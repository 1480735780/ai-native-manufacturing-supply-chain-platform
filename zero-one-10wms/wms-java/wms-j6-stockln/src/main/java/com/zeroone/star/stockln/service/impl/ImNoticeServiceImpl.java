package com.zeroone.star.stockln.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.IdWorker;
import com.zeroone.star.project.dto.j6.stockln.ImNoticeDTO;
import com.zeroone.star.project.dto.j6.stockln.ImportNoticeDTO;
import com.zeroone.star.project.dto.j6.stockln.ImportNoticeItemDTO;
import com.zeroone.star.stockln.entity.ImNoticeH;
import com.zeroone.star.stockln.entity.ImNoticeI;
import com.zeroone.star.stockln.entity.MdGoods;
import com.zeroone.star.stockln.mapper.ImNoticeHMapper;
import com.zeroone.star.stockln.mapper.ImNoticeIMapper;
import com.zeroone.star.stockln.mapper.MdGoodsMapper;
import com.zeroone.star.stockln.service.IImNoticeHService;
import com.zeroone.star.stockln.service.IImNoticeIService;
import com.zeroone.star.stockln.service.IImNoticeService;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.UUID;

@Mapper(componentModel = "spring")
interface ImNoticeMapper{
    @Mapping(target = "imBeizhu", source = "imBeiZhu")
    ImNoticeH imNoticeDTOToImNoticeH(ImportNoticeDTO importNoticeDTO);
    ImNoticeI imNoticeDTOToImNoticeI(ImportNoticeItemDTO importNoticeItemDTO);

    @Mapping(target = "imBeiZhu", source = "imBeizhu")
    ImportNoticeDTO  imNoticeHToImNoticeDTO(ImNoticeH imNoticeH);
    ImportNoticeItemDTO  imNoticeHToImNoticeItemDTO(ImNoticeI imNoticeI);
}

@Service
public class ImNoticeServiceImpl implements IImNoticeService {
    @Resource
    private ImNoticeMapper imNoticeMapper;
    @Resource
    private IImNoticeHService imNoticeHService;
    @Resource
    private IImNoticeIService imNoticeIService;
    @Resource
    private MdGoodsMapper mdGoodsMapper;
    @Resource
    private ImNoticeIMapper imNoticeIMapper;

    @Transactional
    @Override
    public void updateImport(ImportNoticeDTO importNoticeDTO) {
        ImNoticeH imNoticeH = imNoticeMapper.imNoticeDTOToImNoticeH(importNoticeDTO);
        imNoticeHService.update(imNoticeH, new QueryWrapper<ImNoticeH>().eq("notice_id", imNoticeH.getNoticeId()));

        List<ImportNoticeItemDTO> imDTOList = importNoticeDTO.getImportNoticeItemDTOList();
        if (imDTOList == null || imDTOList.isEmpty()) {
            return;
        }
        String noticeId = imNoticeH.getNoticeId();
        for (ImportNoticeItemDTO itemDTO : imDTOList) {
            ImNoticeI imNoticeI = BeanUtil.copyProperties(itemDTO, ImNoticeI.class);
            imNoticeI.setImNoticeId(noticeId);
            if (itemDTO.getId() != null && !itemDTO.getId().isEmpty()) {
                // 已有明细按主键更新，避免按通知单号批量更新导致“后行覆盖前行”
                imNoticeIService.updateById(imNoticeI);
            } else {
                imNoticeI.setId(String.valueOf(IdWorker.getId()));
                imNoticeI.setImNoticeItem(imNoticeI.getId());
                fillGoodsInfo(imNoticeI);
                imNoticeIService.save(imNoticeI);
            }
        }
    }

    @Transactional
    @Override
    public void insertImport(ImportNoticeDTO importNoticeDTO) {
        //生成主键
        LocalDateTime now = LocalDateTime.now();
        String data = now.format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        String uuid = UUID.randomUUID().toString().replace("-", ""); // 32 位
        String shortUuid = uuid.substring(0, 10); // 截取前 10 位
        String noticeId=shortUuid+data;

        String hId = String.valueOf(IdWorker.getId());
        //封装通知单抬头
        ImNoticeH imNoticeH = imNoticeMapper.imNoticeDTOToImNoticeH(importNoticeDTO);
        imNoticeH.setId(hId);
        imNoticeH.setNoticeId(noticeId);
        if (imNoticeH.getImSta() == null || imNoticeH.getImSta().isEmpty()) {
            imNoticeH.setImSta("计划中");
        }
        if (imNoticeH.getCreateDate() == null) {
            imNoticeH.setCreateDate(now);
        }
        imNoticeHService.save(imNoticeH);
        //封装通知单项
        List<ImportNoticeItemDTO> importNoticeItemDTOList = importNoticeDTO.getImportNoticeItemDTOList();
        if (importNoticeItemDTOList == null || importNoticeItemDTOList.isEmpty()) {
            return;
        }
        List<ImNoticeI> list = new LinkedList<>();
        for (ImportNoticeItemDTO itemDTO : importNoticeItemDTOList) {
            ImNoticeI imNoticeI = imNoticeMapper.imNoticeDTOToImNoticeI(itemDTO);
            imNoticeI.setId(String.valueOf(IdWorker.getId()));
            imNoticeI.setImNoticeId(noticeId);
            imNoticeI.setImNoticeItem(imNoticeI.getId());
            imNoticeI.setImBeizhu(imNoticeH.getImBeizhu());
            fillGoodsInfo(imNoticeI);
            list.add(imNoticeI);
        }
        imNoticeIService.saveBatch(list);
    }

    /**
     * 根据商品编码补全明细中的商品名称、单位、体积、重量等信息
     */
    private void fillGoodsInfo(ImNoticeI imNoticeI) {
        MdGoods mdGoods = mdGoodsMapper.selectOne(new QueryWrapper<MdGoods>()
                .eq("shp_bian_ma", imNoticeI.getGoodsCode()));
        if (mdGoods == null) {
            return;
        }
        imNoticeI.setSysOrgCode(mdGoods.getSysOrgCode());
        imNoticeI.setSysCompanyCode(mdGoods.getSysCompanyCode());
        imNoticeI.setGoodsUnit(mdGoods.getShlDanWei());
        imNoticeI.setBaseUnit(mdGoods.getJshDanWei());
        imNoticeI.setGoodsName(mdGoods.getShpMingCheng());
        imNoticeI.setChpShuXing(mdGoods.getChpShuXing());

        String countS = imNoticeI.getGoodsCount();
        if (countS == null || countS.isEmpty()) {
            return;
        }
        Long count = Long.parseLong(countS);
        String fvolS = mdGoods.getTiJiCm();
        if (fvolS != null && !fvolS.isEmpty()) {
            imNoticeI.setGoodsFvol(String.valueOf(count * Long.parseLong(fvolS)));
        }
        String weightS = mdGoods.getZhlKg();
        if (weightS != null && !weightS.isEmpty()) {
            imNoticeI.setGoodsWeight(String.valueOf(count * Long.parseLong(weightS)));
        }
    }

    @Override
    public ImportNoticeDTO searchImport(String imNoticeId) {
        ImNoticeH imNoticeH = imNoticeHService.getOne(new QueryWrapper<ImNoticeH>()
                .eq("notice_id",imNoticeId));
        ImportNoticeDTO imNoticeDTO = imNoticeMapper.imNoticeHToImNoticeDTO(imNoticeH);
        List<ImNoticeI> list = imNoticeIMapper.selectList(new QueryWrapper<ImNoticeI>()
                .eq("im_notice_id",imNoticeId));
        Iterator<ImNoticeI> iterator = list.iterator();
        List<ImportNoticeItemDTO> list_ = new LinkedList();
        while(iterator.hasNext()){
            ImportNoticeItemDTO importNoticeItemDTO = imNoticeMapper
                    .imNoticeHToImNoticeItemDTO(iterator.next());
            list_.add(importNoticeItemDTO);
        }
        imNoticeDTO.setImportNoticeItemDTOList(list_);
        return imNoticeDTO;
    }
}
