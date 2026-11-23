package com.zeroone.star.project.dto.j6.stockln.export;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

/**
 * 入库通知单-货品 ID 导出对象
 */
@Data
public class ImNoticeGoodsIdExportDTO {

    @ExcelProperty("通知单号")
    private String noticeId;

    @ExcelProperty("商品编码")
    private String goodsCode;

    @ExcelProperty("商品名称")
    private String goodsName;

    @ExcelProperty("商品条码")
    private String barcode;

    @ExcelProperty("数量")
    private String goodsCount;

    @ExcelProperty("单位")
    private String goodsUnit;
}
