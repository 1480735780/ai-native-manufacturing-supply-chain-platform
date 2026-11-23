package com.zeroone.star.project.vo.j8.other.goodsbrand;

import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.Data;
import org.springframework.web.multipart.MultipartFile;

/**
 * 商品品牌修改请求VO对象
 * 图片为可选项：不传图片时保留原有图片。
 */
@Data
@ApiModel("商品品牌修改请求VO对象")
public class GoodsBrandUpdateReqVO {
    @ApiModelProperty(value = "主键ID", example = "402880d38e31aba8018e35414b7f0008", required = true)
    private String id;
    @ApiModelProperty(value = "商品品牌代码", example = "KC")
    private String goodsBrandCode;
    @ApiModelProperty(value = "商品品牌名称", example = "可口可乐")
    private String goodsBrandName;
    @ApiModelProperty(value = "商品品牌网址", example = "www.koukele.com")
    private String goodsBrandWww;
    @ApiModelProperty(value = "商品品牌图片（可选，不传则保留原图）")
    private MultipartFile goodsBrandPic;
    @ApiModelProperty(value = "备注", example = "好喝的很")
    private String goodsBrandText;
    @ApiModelProperty(value = "停用状态", example = "0正常|1停用")
    private String goodsBrandDel;
}
