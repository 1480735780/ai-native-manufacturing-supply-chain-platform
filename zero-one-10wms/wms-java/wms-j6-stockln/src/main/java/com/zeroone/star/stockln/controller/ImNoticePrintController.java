package com.zeroone.star.stockln.controller;

import com.zeroone.star.stockln.service.IImNoticePrintService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.annotation.Resource;
import java.nio.charset.StandardCharsets;

/**
 * 入库通知单打印/导出接口
 */
@Api(tags = "入库通知单打印导出")
@RestController
@RequestMapping("/stock/imNotice-manage")
public class ImNoticePrintController {

    private static final MediaType EXCEL_MEDIA_TYPE =
            MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");

    @Resource
    private IImNoticePrintService imNoticePrintService;

    @ApiOperation("打印入库通知单")
    @GetMapping("/print/notice/{noticeId}")
    public ResponseEntity<byte[]> printNotice(@PathVariable String noticeId) {
        return pdfResponse(imNoticePrintService.renderPdf(noticeId, "im-notice.fo"), "入库通知单.pdf");
    }

    @ApiOperation("打印货品信息")
    @GetMapping("/print/goods/{noticeId}")
    public ResponseEntity<byte[]> printGoods(@PathVariable String noticeId) {
        return pdfResponse(imNoticePrintService.renderPdf(noticeId, "im-notice-goods.fo"), "货品信息.pdf");
    }

    @ApiOperation("打印入库单")
    @GetMapping("/print/inbound/{noticeId}")
    public ResponseEntity<byte[]> printInbound(@PathVariable String noticeId) {
        return pdfResponse(imNoticePrintService.renderPdf(noticeId, "im-inbound.fo"), "入库单.pdf");
    }

    @ApiOperation("导出验收单")
    @GetMapping("/export/acceptance/{noticeId}")
    public ResponseEntity<byte[]> exportAcceptance(@PathVariable String noticeId) {
        return excelResponse(imNoticePrintService.exportExcel(noticeId, "acceptance"), "验收单.xlsx");
    }

    @ApiOperation("导出入库单")
    @GetMapping("/export/inbound/{noticeId}")
    public ResponseEntity<byte[]> exportInbound(@PathVariable String noticeId) {
        return excelResponse(imNoticePrintService.exportExcel(noticeId, "inbound"), "入库单.xlsx");
    }

    @ApiOperation("导出货品ID")
    @GetMapping("/export/goods-id/{noticeId}")
    public ResponseEntity<byte[]> exportGoodsId(@PathVariable String noticeId) {
        return excelResponse(imNoticePrintService.exportExcel(noticeId, "goods-id"), "货品ID.xlsx");
    }

    @ApiOperation("导出托盘标签")
    @GetMapping("/export/tin-label/{noticeId}")
    public ResponseEntity<byte[]> exportTinLabel(@PathVariable String noticeId) {
        return excelResponse(imNoticePrintService.exportExcel(noticeId, "tin-label"), "托盘标签.xlsx");
    }

    private ResponseEntity<byte[]> pdfResponse(byte[] content, String filename) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_PDF);
        headers.setContentDisposition(buildDisposition(filename));
        return ResponseEntity.ok().headers(headers).body(content);
    }

    private ResponseEntity<byte[]> excelResponse(byte[] content, String filename) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(EXCEL_MEDIA_TYPE);
        headers.setContentDisposition(buildDisposition(filename));
        return ResponseEntity.ok().headers(headers).body(content);
    }

    private ContentDisposition buildDisposition(String filename) {
        return ContentDisposition.builder("attachment")
                .filename(filename, StandardCharsets.UTF_8)
                .build();
    }
}
