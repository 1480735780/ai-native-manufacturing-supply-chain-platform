package com.zeroone.star.project.query.j6.stockln;

import com.zeroone.star.project.query.PageQuery;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;

@Data
@ApiModel("待上架货物查询对象")
public class ToShelvesQuery extends PageQuery {

    @ApiModelProperty(value = "托盘编号",example = "AAA")
    private String tinId;

    @ApiModelProperty(value = "货主编码",example = "123456789",required = true)
    private String cusCode;

    @ApiModelProperty(value = "商品编码",example = "123456789-小蓝管-支")
    private String goodsId;

    @ApiModelProperty(value = "到货通知ID",example = "2c9efaca91697e98019226efea7b1c2e")
    private String imNoticeId;

    @ApiModelProperty(value = "货物名字")
    private String goodsName;

    @ApiModelProperty(value = "客户名称")
    private String cusName;

    @ApiModelProperty(value = "仓位")
    private String binId;

    @ApiModelProperty(value = "是否已上架")
    private String binSta;

    @ApiModelProperty(value = "订单类型编码（可选，按入库通知单订单类型过滤，如 03=退货通知 04=越库通知）", example = "03")
    private String orderTypeCode;

}
