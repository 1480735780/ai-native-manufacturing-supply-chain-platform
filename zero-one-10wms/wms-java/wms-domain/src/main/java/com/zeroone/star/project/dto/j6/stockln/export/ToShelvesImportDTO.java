package com.zeroone.star.project.dto.j6.stockln.export;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

/**
 * 收货登记导入对象
 */
@Data
public class ToShelvesImportDTO {

    @ExcelProperty("通知单号")
    private String imNoticeId;

    @ExcelProperty("商品编码")
    private String goodsId;

    @ExcelProperty("客户编码")
    private String cusCode;

    @ExcelProperty("储位")
    private String binId;

    @ExcelProperty("数量")
    private String imQuat;

    @ExcelProperty("生产日期")
    private String proData;

    @ExcelProperty("批次")
    private String goodsBatch;

    @ExcelProperty("收货温度")
    private String recDeg;

    @ExcelProperty("备注")
    private String itemText;

    @ExcelProperty("托盘")
    private String tinId;

    @ExcelProperty("入库数量")
    private String baseInGoodscount;
}
