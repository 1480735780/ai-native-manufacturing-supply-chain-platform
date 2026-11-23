package com.zeroone.star.project.query.j6.stockln;

import com.zeroone.star.project.query.PageQuery;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;
import lombok.EqualsAndHashCode;

/**
 * 客户库存报表查询对象
 */
@EqualsAndHashCode(callSuper = true)
@Data
@ApiModel("客户库存报表查询对象")
public class MvStockCusQuery extends PageQuery {
    @ApiModelProperty(value = "客户编码", example = "1250")
    private String cusCode;
    @ApiModelProperty(value = "客户名称", example = "大成陶瓷有限公司")
    private String zhongWenQch;
    @ApiModelProperty(value = "商品编码", example = "123456789")
    private String goodsId;
    @ApiModelProperty(value = "商品名称", example = "小蓝管")
    private String shpMingCheng;
}
