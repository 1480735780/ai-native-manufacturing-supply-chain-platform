package com.zeroone.star.project.dto.j5.basezl.customer;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * <p>
 * 描述：客户名称列表项，用于表单下拉框
 * </p>
 *
 * @author workbuddy
 * @since 2026-11-22
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@ApiModel("客户名称列表项")
public class CustomerNameDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    @ApiModelProperty(value = "客户唯一标识", example = "1234567890")
    private String id;

    @ApiModelProperty(value = "客户编码", example = "CC001")
    private String keHuBianMa;

    @ApiModelProperty(value = "客户中文全称", example = "可口可乐公司")
    private String zhongWenQch;
}
