package com.zeroone.star.stockln.service;

/**
 * 入库通知单打印/导出服务
 */
public interface IImNoticePrintService {

    /**
     * 生成 PDF
     *
     * @param noticeId     入库通知单号
     * @param templateName FO 模板名称
     * @return PDF 字节数组
     */
    byte[] renderPdf(String noticeId, String templateName);

    /**
     * 导出 Excel
     *
     * @param noticeId   入库通知单号
     * @param exportType acceptance / inbound / goods-id / tin-label
     * @return Excel 字节数组
     */
    byte[] exportExcel(String noticeId, String exportType);
}
