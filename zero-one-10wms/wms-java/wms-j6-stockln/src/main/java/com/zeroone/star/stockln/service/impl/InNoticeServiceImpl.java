package com.zeroone.star.stockln.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.dto.j6.stockln.InNoticeVO;
import com.zeroone.star.project.dto.j6.stockln.ToAcceptDTO;
import com.zeroone.star.project.dto.j6.stockln.export.InNoticeItemExportDTO;
import com.zeroone.star.project.query.j6.stockln.InNoticeQuery;
import com.zeroone.star.project.vo.j6.stockln.InNoticePageVO;
import com.zeroone.star.stockln.mapper.InNoticeMapper;
import com.zeroone.star.stockln.service.InNoticeService;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.io.ByteArrayOutputStream;
import java.util.List;
import java.util.stream.Collectors;

/**
 * <p>
 * 描述：入库通知明细服务实现类
 * </p>
 *
 * @author []
 * @version 1.0.0
 */
@Service
public class InNoticeServiceImpl extends ServiceImpl<InNoticeMapper, ToAcceptDTO> implements InNoticeService {

    @Resource
    private InNoticeMapper inNoticeMapper;

    @Resource
    private EasyExcelComponent easyExcelComponent;

    @Override
    public InNoticePageVO getInNoticeItems(InNoticeQuery query, int page, int size) {
        int pageIndex = page > 0 ? page : (int) query.getPageIndex();
        int pageSize = size > 0 ? size : (int) query.getPageSize();
        if (pageIndex <= 0) {
            pageIndex = 1;
        }
        if (pageSize <= 0) {
            pageSize = 10;
        }
        Page<InNoticeVO> pageObj = new Page<>(pageIndex, pageSize);
        Page<InNoticeVO> resultPage = inNoticeMapper.selectInNoticePage(pageObj, query);
        return new InNoticePageVO(resultPage.getRecords(), resultPage.getCurrent(),
                resultPage.getSize(), resultPage.getTotal());
    }

    @Override
    public byte[] exportInNotice(InNoticeQuery query) {
        List<InNoticeVO> rows = inNoticeMapper.selectInNoticeList(query);
        List<InNoticeItemExportDTO> data = rows.stream()
                .map(row -> BeanUtil.copyProperties(row, InNoticeItemExportDTO.class))
                .collect(Collectors.toList());
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try {
            easyExcelComponent.export("进货通知明细", out, InNoticeItemExportDTO.class, data);
        } catch (Exception e) {
            throw new RuntimeException("导出进货通知明细失败", e);
        }
        return out.toByteArray();
    }
}
