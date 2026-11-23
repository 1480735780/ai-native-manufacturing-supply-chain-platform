package com.zeroone.star.project.dto.j6.stockln.export;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

/**
 * 收货登记导出对象
 */
@Data
public class ToShelvesExportDTO {

    @ExcelProperty("通知单号")
    private String imNoticeId;

    @ExcelProperty("客户编码")
    private String cusCode;

    @ExcelProperty("客户名称")
    private String cusName;

    @ExcelProperty("商品编码")
    private String goodsId;

    @ExcelProperty("商品名称")
    private String goodsName;

    @ExcelProperty("到货数量")
    private String imQuat;

    @ExcelProperty("收货数量")
    private String qmOkQuat;

    @ExcelProperty("单位")
    private String goodsUnit;

    @ExcelProperty("批次")
    private String goodsBatch;

    @ExcelProperty("生产日期")
    private String proData;

    @ExcelProperty("储位")
    private String binId;

    @ExcelProperty("托盘")
    private String tinId;

    @ExcelProperty("上架状态")
    private String binSta;

    @ExcelProperty("收货日期")
    private String createDate;
}
