package com.zeroone.star.project.query.j7.outbound;

import com.zeroone.star.project.query.PageQuery;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Getter;
import lombok.Setter;
import lombok.ToString;

/**
 * <p>
 * 月台计划分页查询对象
 * </p>
 *
 * @author dev-yuetaiguanli
 * @since 2026-11-22
 */
@ToString
@Setter
@Getter
@ApiModel("月台计划分页查询对象")
public class WmPlatIoQuery extends PageQuery {

    /**
     * 车号（模糊）
     */
    @ApiModelProperty(value = "车号", example = "京A88888")
    private String carno;

    /**
     * 单据编号（精确）
     */
    @ApiModelProperty(value = "单据编号", example = "DOC123456")
    private String docId;

    /**
     * 月台编号（精确）
     */
    @ApiModelProperty(value = "月台编号", example = "PLAT001")
    private String platId;

    /**
     * 月台状态（精确）
     */
    @ApiModelProperty(value = "月台状态", example = "占用中")
    private String platSta;
}
