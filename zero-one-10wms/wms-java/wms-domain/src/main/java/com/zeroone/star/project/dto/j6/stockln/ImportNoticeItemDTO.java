package com.zeroone.star.project.dto.j6.stockln;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@ApiModel("进货通知单明细")
public class ImportNoticeItemDTO {

    @ApiModelProperty(value = "明细主键", example = "123123sdfa")
    private String id;

    @ApiModelProperty(value = "商品编号",example = "20292")
    private String goodsCode;

    @ApiModelProperty(value = "商品名称",example = "蔗糖")
    private String goodsName;

    @ApiModelProperty(value = "数量",example = "100")
    private String goodsCount;

    @ApiModelProperty(value = "计划占用存储位数",example = "10")
    private String binPlan;

    @ApiModelProperty(value = "收货完成",allowableValues = "Y N I")
    private String binPre;

    @ApiModelProperty(value = "单位", example = "箱")
    private String goodsUnit;

    @ApiModelProperty(value = "批次", example = "BATCH001")
    private String goodsBatch;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @ApiModelProperty(value = "生产日期", example = "2025-03-17 12:33:20")
    private LocalDateTime goodsPrdData;

    @ApiModelProperty(value = "行项目状态", example = "计划中")
    private String noticeiSta;

    @ApiModelProperty(value = "基本单位", example = "箱")
    private String baseUnit;

    @ApiModelProperty(value = "基本单位数量", example = "100")
    private String baseGoodscount;

    @ApiModelProperty(value = "商品条码", example = "AD001")
    private String barcode;

    @ApiModelProperty(value = "托盘号", example = "T001")
    private String tinId;

    @ApiModelProperty(value = "体积", example = "1000")
    private String goodsFvol;

    @ApiModelProperty(value = "重量", example = "50")
    private String goodsWeight;
}
