package com.zeroone.star.stockln.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.project.dto.j6.stockln.AcceptDTO;
import com.zeroone.star.project.dto.j6.stockln.AcceptRequestDTO;
import com.zeroone.star.project.dto.j6.stockln.ToAcceptDTO;
import com.zeroone.star.stockln.mapper.AcceptMapper;
import com.zeroone.star.stockln.mapper.ToAcceptMapper;
import com.zeroone.star.stockln.service.AcceptService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.annotation.Resource;
import java.time.LocalDateTime;
import java.util.List;

@Slf4j
@Service
public class AcceptServiceImpl extends ServiceImpl<AcceptMapper, AcceptDTO> implements AcceptService {

    @Resource
    private AcceptMapper acceptMapper;

    @Resource
    private ToAcceptMapper toAcceptMapper;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean processAcceptance(AcceptRequestDTO requestDTO) {
        return doAccept(requestDTO);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int processBatchAcceptance(List<AcceptRequestDTO> requests) {
        if (requests == null || requests.isEmpty()) {
            throw new IllegalArgumentException("请选择要验收的货物");
        }
        int count = 0;
        for (AcceptRequestDTO request : requests) {
            try {
                if (doAccept(request)) {
                    count++;
                }
            } catch (Exception e) {
                log.error("批量验收失败，请求参数：{}", request, e);
                throw e;
            }
        }
        return count;
    }

    private boolean doAccept(AcceptRequestDTO requestDTO) {
        if (requestDTO == null || requestDTO.getId() == null || requestDTO.getId().isEmpty()) {
            throw new IllegalArgumentException("待验收货物ID不能为空");
        }
        ToAcceptDTO toAcceptDTO = toAcceptMapper.selectById(requestDTO.getId());
        if (toAcceptDTO == null) {
            throw new IllegalArgumentException("待验收货物不存在：" + requestDTO.getId());
        }

        int acceptCount;
        try {
            acceptCount = Integer.parseInt(requestDTO.getImQuat());
        } catch (Exception e) {
            throw new IllegalArgumentException("验收数量必须为数字");
        }
        if (acceptCount <= 0) {
            throw new IllegalArgumentException("验收数量必须大于 0");
        }

        AcceptDTO acceptDTO = new AcceptDTO();
        acceptDTO.setImNoticeId(toAcceptDTO.getImNoticeId());
        acceptDTO.setImNoticeItem(toAcceptDTO.getId());
        acceptDTO.setGoodsId(toAcceptDTO.getGoodsCode());
        acceptDTO.setGoodsName(toAcceptDTO.getGoodsName());
        acceptDTO.setCusCode(requestDTO.getCusCode());
        acceptDTO.setBinId(requestDTO.getBinId());
        acceptDTO.setImQuat(requestDTO.getImQuat());
        acceptDTO.setQmOkQuat(requestDTO.getImQuat());
        acceptDTO.setGoodsBatch(requestDTO.getGoodsBatch());
        acceptDTO.setRecDeg(requestDTO.getRecDeg());
        acceptDTO.setItemText(requestDTO.getItemText());
        acceptDTO.setProData(requestDTO.getProData());
        acceptDTO.setTinId(requestDTO.getTinId());
        acceptDTO.setTinZhl(requestDTO.getTinZhl());
        acceptDTO.setGoodsUnit(toAcceptDTO.getGoodsUnit());
        acceptDTO.setBaseUnit(toAcceptDTO.getBaseUnit());
        acceptDTO.setBaseGoodscount(requestDTO.getImQuat());
        acceptDTO.setBinSta("N");
        acceptDTO.setCreateDate(LocalDateTime.now());
        save(acceptDTO);

        int ordered = toAcceptDTO.getGoodsCount() == null ? 0 : toAcceptDTO.getGoodsCount();
        int oldQm = toAcceptDTO.getGoodsQmCount() == null ? 0 : toAcceptDTO.getGoodsQmCount();
        int oldWqm = toAcceptDTO.getGoodsWqmCount() == null
                ? Math.max(0, ordered - oldQm) : toAcceptDTO.getGoodsWqmCount();
        int newWqm = Math.max(0, oldWqm - acceptCount);
        toAcceptDTO.setGoodsWqmCount(newWqm);
        toAcceptDTO.setGoodsQmCount(oldQm + acceptCount);
        if (newWqm == 0) {
            toAcceptDTO.setNoticeiSta("已完成");
        }
        toAcceptMapper.updateById(toAcceptDTO);
        return true;
    }
}
