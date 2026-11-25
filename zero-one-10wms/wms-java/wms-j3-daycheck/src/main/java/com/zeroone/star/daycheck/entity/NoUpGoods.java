package com.zeroone.star.daycheck.entity;

import com.alibaba.excel.annotation.ExcelIgnore;
import com.alibaba.excel.annotation.ExcelProperty;
import com.zeroone.star.daycheck.config.LocalDateTimeExcel;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import java.time.LocalDateTime;


/**
 * @author aaa
 * @version 1.0
 * @description 收货未上架-返回数据
 * @date 2025/2/22 11:40
 */
@Data
@ApiModel("收货未上架-返回数据")//下面的数据和业务参考项目返回数据 看是否存在在wm_tuopan上 wm_in_qm_i验收记录
public class NoUpGoods {
    // 巡检数据源需要稳定行键：NoUpMapper.xml 的 resultMap 映射 id/im_notice_id，
    // 实体必须有对应属性，否则 MyBatis 逐行映射时抛 There is no setter for property named 'id'。
    // 两列不参与旧页面的 Excel 导出。
    @ExcelIgnore
    @ApiModelProperty(value = "主键（wm_in_qm_i.id，巡检行键 rowId）")
    private String id;

    @ExcelIgnore
    @ApiModelProperty(value = "到货通知单（wm_in_qm_i.im_notice_id，巡检 noticeId）")
    private String im_notice_id;

    @ApiModelProperty(value = "库存状态")//wm_in_qm_i
    @ExcelProperty(value = "库存状态" ,index = 0)
    private String bin_sta;

    @ApiModelProperty(value = "储位")//wm_in_qm_i
    @ExcelProperty(value = "储位" ,index = 1)
    private String bin_id;

    @ApiModelProperty(value = "托盘")//wm_in_qm_i
    @ExcelProperty(value = "托盘" ,index = 2)
    private String tin_id;

    @ApiModelProperty(value = "客户编码")//wm_in_qm_i
    @ExcelProperty(value = "客户编码" ,index = 3)
    private String cus_code;

    private String sys_company_code;
    @ApiModelProperty(value = "客户名称")//md_cus!!!!
    @ExcelProperty(value = "客户名称" ,index = 4)
    private String zhong_wen_qch;

    @ApiModelProperty(value = "商品编码")//wm_in_qm_i其中的goods_id和md_goods里面的商品编码shp_bian_ma一样
    @ExcelProperty(value = "商品编码" ,index = 5)
    private String goods_id;

    @ApiModelProperty(value = "商品名称")//md_goods
    @ExcelProperty(value = "商品名称" ,index = 6)
    private String shp_ming_cheng;

    @ApiModelProperty(value = "数量")//wm_in_qm_i
    @ExcelProperty(value = "数量" ,index = 7)
    private String qm_ok_quat;

    @ApiModelProperty(value = "商品单位")//wm_in_qm_i
    @ExcelProperty(value = "商品单位" ,index = 8)
    private String goods_unit;

    @ApiModelProperty(value = "生产日期")//wm_in_qm_i
    @ExcelProperty(value = "生产日期" ,index = 9)
    private String pro_data;

    @ApiModelProperty(value = "收货日期")//wm_in_qm_i
    @ExcelProperty(value = "收货日期", index = 10, converter = LocalDateTimeExcel.class)
    private LocalDateTime create_date;

    @ApiModelProperty(value = "保质期")//md_goods
    @ExcelProperty(value = "保质期" ,index = 11)
    private String bzhi_qi;
}
