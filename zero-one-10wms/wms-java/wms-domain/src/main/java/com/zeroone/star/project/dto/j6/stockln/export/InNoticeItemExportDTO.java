package com.zeroone.star.project.dto.j6.stockln.export;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

/**
 * 进货通知明细导出对象
 */
@Data
public class InNoticeItemExportDTO {

    @ExcelProperty("通知单号")
    private String imNoticeId;

    @ExcelProperty("客户编码")
    private String cusCode;

    @ExcelProperty("客户名称")
    private String cusName;

    @ExcelProperty("行项目状态")
    private String noticeiSta;

    @ExcelProperty("商品编码")
    private String goodsCode;

    @ExcelProperty("商品名称")
    private String goodsName;

    @ExcelProperty("通知数量")
    private Integer goodsCount;

    @ExcelProperty("验收数量")
    private Integer goodsQmCount;

    @ExcelProperty("单位")
    private String goodsUnit;

    @ExcelProperty("体积")
    private Double goodsFvol;

    @ExcelProperty("重量")
    private Double goodsWeight;

    @ExcelProperty("客户订单号")
    private String imCusCode;

    @ExcelProperty("基本单位数量")
    private Double baseGoodscount;

    @ExcelProperty("基本单位")
    private String baseUnit;

    @ExcelProperty("生产日期")
    private String goodsPrdData;
}
