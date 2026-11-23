package com.zeroone.star.project.dto.j6.stockln;



import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@ApiModel("进货入通知单修改页面显示对象")
public class ImportNoticeDTO {

//    @ApiModelProperty(value="主键",example="123123sdfa")
//    private String id;
    @ApiModelProperty(value="订单号")
    private String noticeId;

    @ApiModelProperty(value="客户编号",example="X00001")
    private String cusCode;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @ApiModelProperty(value = "预计到货时间",example = "2025-03-17 12:33:20")
    private LocalDateTime imData;

    @ApiModelProperty(value = "客户订单号",example = "001")
    private String imCusCode;

    @ApiModelProperty(value = "运输号码", example = "14435674566")
    private String imCarMobile;

    @ApiModelProperty(value = "车号", example = "苏A12345")
    private String imCarNo;

    @ApiModelProperty(value = "运输公司", example = "顺丰")
    private String imCarDri;

    @ApiModelProperty(value = "供应商编码", example = "G001")
    private String supCode;

    @ApiModelProperty(value = "供应商名称",example = "001-YYYY有限公司")
    private String supName;

    @ApiModelProperty(value = "预约库区",example = "A库区")
    private String areaCode;

    @ApiModelProperty(value = "订单类型",example = "01")
    private String orderTypeCode;

    @ApiModelProperty(value = "仓库", example = "01")
    private String storeCode;

    @ApiModelProperty(value = "月台", example = "P01")
    private String platformCode;

    @ApiModelProperty(value = "单据状态", example = "计划中")
    private String imSta;

    @ApiModelProperty(value = "创建人名称", example = "管理员")
    private String createName;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    @ApiModelProperty(value = "创建日期", example = "2025-03-17 12:33:20")
    private LocalDateTime createDate;

    @ApiModelProperty(value = "备注", example = "...")
    private String imBeiZhu;

    @ApiModelProperty(value = "附件(url)",example = "http//10.10.10.10:8877/aaa.png")
    private String fuJian;

    @JsonProperty("importNoticeItemDTOList")
    @ApiModelProperty(value = "进货通知单明细")
    private List<ImportNoticeItemDTO> importNoticeItemDTOList;
}
