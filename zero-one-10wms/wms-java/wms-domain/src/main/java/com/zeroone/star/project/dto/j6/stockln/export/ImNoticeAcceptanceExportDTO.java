package com.zeroone.star.project.dto.j6.stockln.export;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

/**
 * 入库通知单-验收单导出对象
 */
@Data
public class ImNoticeAcceptanceExportDTO {

    @ExcelProperty("通知单号")
    private String noticeId;

    @ExcelProperty("客户编码")
    private String cusCode;

    @ExcelProperty("供应商")
    private String supName;

    @ExcelProperty("商品编码")
    private String goodsCode;

    @ExcelProperty("商品名称")
    private String goodsName;

    @ExcelProperty("通知数量")
    private String goodsCount;

    @ExcelProperty("已收数量")
    private String goodsQmCount;

    @ExcelProperty("单位")
    private String goodsUnit;

    @ExcelProperty("批次")
    private String goodsBatch;

    @ExcelProperty("生产日期")
    private String goodsPrdData;

    @ExcelProperty("计划库位")
    private String binPlan;

    @ExcelProperty("备注")
    private String imBeizhu;
}
