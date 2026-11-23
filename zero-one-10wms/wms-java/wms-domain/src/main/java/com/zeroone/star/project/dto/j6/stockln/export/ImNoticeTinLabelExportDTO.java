package com.zeroone.star.project.dto.j6.stockln.export;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

/**
 * 入库通知单-托盘标签导出对象
 */
@Data
public class ImNoticeTinLabelExportDTO {

    @ExcelProperty("托盘号")
    private String tinId;

    @ExcelProperty("通知单号")
    private String noticeId;

    @ExcelProperty("商品编码")
    private String goodsCode;

    @ExcelProperty("商品名称")
    private String goodsName;

    @ExcelProperty("数量")
    private String goodsCount;

    @ExcelProperty("单位")
    private String goodsUnit;

    @ExcelProperty("计划库位")
    private String binPlan;

    @ExcelProperty("批次")
    private String goodsBatch;

    @ExcelProperty("生产日期")
    private String goodsPrdData;
}
