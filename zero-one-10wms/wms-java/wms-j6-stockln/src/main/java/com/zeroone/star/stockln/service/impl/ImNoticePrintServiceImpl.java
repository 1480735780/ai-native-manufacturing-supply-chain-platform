package com.zeroone.star.stockln.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.zeroone.star.project.components.easyexcel.EasyExcelComponent;
import com.zeroone.star.project.components.pdf.PdfComponent;
import com.zeroone.star.project.dto.j6.stockln.export.ImNoticeAcceptanceExportDTO;
import com.zeroone.star.project.dto.j6.stockln.export.ImNoticeGoodsIdExportDTO;
import com.zeroone.star.project.dto.j6.stockln.export.ImNoticeInboundExportDTO;
import com.zeroone.star.project.dto.j6.stockln.export.ImNoticeTinLabelExportDTO;
import com.zeroone.star.stockln.entity.ImNoticeH;
import com.zeroone.star.stockln.entity.ImNoticeI;
import com.zeroone.star.stockln.service.IImNoticeHService;
import com.zeroone.star.stockln.service.IImNoticeIService;
import com.zeroone.star.stockln.service.IImNoticePrintService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import javax.annotation.Resource;
import java.io.ByteArrayOutputStream;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 入库通知单打印/导出服务实现
 */
@Slf4j
@Service
public class ImNoticePrintServiceImpl implements IImNoticePrintService {

    private static final DateTimeFormatter DATE_TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @Resource
    private IImNoticeHService imNoticeHService;

    @Resource
    private IImNoticeIService imNoticeIService;

    @Resource
    private PdfComponent pdfComponent;

    @Resource
    private EasyExcelComponent easyExcelComponent;

    @Override
    public byte[] renderPdf(String noticeId, String templateName) {
        try {
            ImNoticeH header = loadHeader(noticeId);
            List<ImNoticeI> items = loadItems(noticeId);
            Map<String, Object> data = buildPdfData(header, items);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            pdfComponent.generateToStream(templateName, data, out);
            return out.toByteArray();
        } catch (Throwable e) {
            log.error("生成入库通知单PDF失败，通知单号：{}，模板：{}", noticeId, templateName, e);
            throw new RuntimeException("生成PDF失败", e);
        }
    }

    @Override
    public byte[] exportExcel(String noticeId, String exportType) {
        ImNoticeH header = loadHeader(noticeId);
        List<ImNoticeI> items = loadItems(noticeId);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        try {
            switch (exportType) {
                case "acceptance":
                    easyExcelComponent.export("验收单", out, ImNoticeAcceptanceExportDTO.class,
                            buildAcceptanceList(header, items));
                    break;
                case "inbound":
                    easyExcelComponent.export("入库单", out, ImNoticeInboundExportDTO.class,
                            buildInboundList(header, items));
                    break;
                case "goods-id":
                    easyExcelComponent.export("货品ID", out, ImNoticeGoodsIdExportDTO.class,
                            buildGoodsIdList(header, items));
                    break;
                case "tin-label":
                    easyExcelComponent.export("托盘标签", out, ImNoticeTinLabelExportDTO.class,
                            buildTinLabelList(header, items));
                    break;
                default:
                    throw new IllegalArgumentException("不支持的导出类型：" + exportType);
            }
        } catch (Exception e) {
            throw new RuntimeException("导出入库通知单失败", e);
        }
        return out.toByteArray();
    }

    private ImNoticeH loadHeader(String noticeId) {
        ImNoticeH header = imNoticeHService.getOne(new QueryWrapper<ImNoticeH>()
                .eq("notice_id", noticeId));
        if (header == null) {
            throw new IllegalArgumentException("入库通知单不存在：" + noticeId);
        }
        return header;
    }

    private List<ImNoticeI> loadItems(String noticeId) {
        return imNoticeIService.list(new QueryWrapper<ImNoticeI>()
                .eq("im_notice_id", noticeId)
                .orderByAsc("goods_code"));
    }

    private Map<String, Object> buildPdfData(ImNoticeH header, List<ImNoticeI> items) {
        Map<String, Object> data = new HashMap<>();
        data.put("noticeId", nullToEmpty(header.getNoticeId()));
        data.put("cusCode", nullToEmpty(header.getCusCode()));
        data.put("imData", formatDateTime(header.getImData()));
        data.put("imCusCode", nullToEmpty(header.getImCusCode()));
        data.put("imCarNo", nullToEmpty(header.getImCarNo()));
        data.put("imCarMobile", nullToEmpty(header.getImCarMobile()));
        data.put("imCarDri", nullToEmpty(header.getImCarDri()));
        data.put("supCode", nullToEmpty(header.getSupCode()));
        data.put("supName", nullToEmpty(header.getSupName()));
        data.put("orderTypeCode", nullToEmpty(header.getOrderTypeCode()));
        data.put("imBeiZhu", nullToEmpty(header.getImBeizhu()));
        data.put("imSta", nullToEmpty(header.getImSta()));
        data.put("createName", nullToEmpty(header.getCreateName()));
        data.put("createDate", formatDateTime(header.getCreateDate()));

        List<Map<String, Object>> itemList = new ArrayList<>();
        for (ImNoticeI item : items) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("goodsCode", nullToEmpty(item.getGoodsCode()));
            row.put("goodsName", nullToEmpty(item.getGoodsName()));
            row.put("goodsCount", nullToEmpty(item.getGoodsCount()));
            row.put("goodsUnit", nullToEmpty(item.getGoodsUnit()));
            row.put("binPlan", nullToEmpty(item.getBinPlan()));
            row.put("binPre", nullToEmpty(item.getBinPre()));
            row.put("goodsBatch", nullToEmpty(item.getGoodsBatch()));
            row.put("goodsPrdData", formatDateTime(item.getGoodsPrdData()));
            row.put("barcode", nullToEmpty(item.getBarcode()));
            itemList.add(row);
        }
        data.put("items", itemList);
        return data;
    }

    private List<ImNoticeAcceptanceExportDTO> buildAcceptanceList(ImNoticeH header, List<ImNoticeI> items) {
        List<ImNoticeAcceptanceExportDTO> list = new ArrayList<>();
        for (ImNoticeI item : items) {
            ImNoticeAcceptanceExportDTO dto = new ImNoticeAcceptanceExportDTO();
            dto.setNoticeId(header.getNoticeId());
            dto.setCusCode(header.getCusCode());
            dto.setSupName(header.getSupName());
            dto.setGoodsCode(item.getGoodsCode());
            dto.setGoodsName(item.getGoodsName());
            dto.setGoodsCount(item.getGoodsCount());
            dto.setGoodsQmCount(item.getGoodsQmCount());
            dto.setGoodsUnit(item.getGoodsUnit());
            dto.setGoodsBatch(item.getGoodsBatch());
            dto.setGoodsPrdData(formatDateTime(item.getGoodsPrdData()));
            dto.setBinPlan(item.getBinPlan());
            dto.setImBeizhu(header.getImBeizhu());
            list.add(dto);
        }
        return list;
    }

    private List<ImNoticeInboundExportDTO> buildInboundList(ImNoticeH header, List<ImNoticeI> items) {
        List<ImNoticeInboundExportDTO> list = new ArrayList<>();
        for (ImNoticeI item : items) {
            ImNoticeInboundExportDTO dto = new ImNoticeInboundExportDTO();
            dto.setNoticeId(header.getNoticeId());
            dto.setCusCode(header.getCusCode());
            dto.setSupName(header.getSupName());
            dto.setGoodsCode(item.getGoodsCode());
            dto.setGoodsName(item.getGoodsName());
            dto.setGoodsCount(item.getGoodsCount());
            dto.setGoodsUnit(item.getGoodsUnit());
            dto.setGoodsBatch(item.getGoodsBatch());
            dto.setGoodsPrdData(formatDateTime(item.getGoodsPrdData()));
            dto.setBinPlan(item.getBinPlan());
            dto.setImBeizhu(header.getImBeizhu());
            list.add(dto);
        }
        return list;
    }

    private List<ImNoticeGoodsIdExportDTO> buildGoodsIdList(ImNoticeH header, List<ImNoticeI> items) {
        List<ImNoticeGoodsIdExportDTO> list = new ArrayList<>();
        for (ImNoticeI item : items) {
            ImNoticeGoodsIdExportDTO dto = new ImNoticeGoodsIdExportDTO();
            dto.setNoticeId(header.getNoticeId());
            dto.setGoodsCode(item.getGoodsCode());
            dto.setGoodsName(item.getGoodsName());
            dto.setBarcode(item.getBarcode());
            dto.setGoodsCount(item.getGoodsCount());
            dto.setGoodsUnit(item.getGoodsUnit());
            list.add(dto);
        }
        return list;
    }

    private List<ImNoticeTinLabelExportDTO> buildTinLabelList(ImNoticeH header, List<ImNoticeI> items) {
        List<ImNoticeTinLabelExportDTO> list = new ArrayList<>();
        for (ImNoticeI item : items) {
            ImNoticeTinLabelExportDTO dto = new ImNoticeTinLabelExportDTO();
            dto.setTinId(item.getTinId());
            dto.setNoticeId(header.getNoticeId());
            dto.setGoodsCode(item.getGoodsCode());
            dto.setGoodsName(item.getGoodsName());
            dto.setGoodsCount(item.getGoodsCount());
            dto.setGoodsUnit(item.getGoodsUnit());
            dto.setBinPlan(item.getBinPlan());
            dto.setGoodsBatch(item.getGoodsBatch());
            dto.setGoodsPrdData(formatDateTime(item.getGoodsPrdData()));
            list.add(dto);
        }
        return list;
    }

    private String formatDateTime(LocalDateTime value) {
        return value == null ? "" : value.format(DATE_TIME_FORMATTER);
    }

    private String nullToEmpty(String value) {
        return value == null ? "" : value;
    }
}
