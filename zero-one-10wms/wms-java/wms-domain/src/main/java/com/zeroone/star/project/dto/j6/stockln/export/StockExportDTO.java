package com.zeroone.star.project.dto.j6.stockln.export;

import com.alibaba.excel.annotation.ExcelProperty;
import lombok.Data;

/**
 * 库存查询导出对象
 */
@Data
public class StockExportDTO {

    @ExcelProperty("库存类型")
    private String kuctype;

    @ExcelProperty("储位")
    private String kuWeiBianMa;

    @ExcelProperty("托盘")
    private String binId;

    @ExcelProperty("客户编码")
    private String cusCode;

    @ExcelProperty("客户名称")
    private String zhongWenQch;

    @ExcelProperty("商品编码")
    private String goodsCode;

    @ExcelProperty("商品名称")
    private String shpMingCheng;

    @ExcelProperty("数量")
    private Long baseGoodscount;

    @ExcelProperty("单位")
    private String baseUnit;

    @ExcelProperty("生产日期")
    private String goodsProData;

    @ExcelProperty("保质期(天)")
    private String bzhiQi;

    @ExcelProperty("到期日")
    private String dqr;
}
