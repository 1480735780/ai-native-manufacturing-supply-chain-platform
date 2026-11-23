package com.zeroone.star.stockln.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.io.Serializable;

/**
 * 客户库存报表视图 mv_stock_cus
 */
@Getter
@Setter
@TableName("mv_stock_cus")
public class MvStockCus implements Serializable {

    private static final long serialVersionUID = 1L;

    private String id;

    /**
     * 库存类型
     */
    private String kuctype;

    /**
     * 数量
     */
    private Long goodsQua;

    private String goodsUnit;

    /**
     * 基本数量
     */
    private Long baseGoodscount;

    private String baseUnit;

    /**
     * 储位
     */
    private String kuWeiBianMa;

    /**
     * 托盘
     */
    private String binId;

    /**
     * 客户编码
     */
    private String cusCode;

    /**
     * 客户名称
     */
    private String zhongWenQch;

    /**
     * 生产日期
     */
    private String goodsProData;

    /**
     * 保质期
     */
    private String bzhiQi;

    /**
     * 到期日
     */
    private String dqr;

    private String kuWeiLeiXing;

    private String quHuoCiXu;

    private String shangJiaCiXu;

    /**
     * 商品编码
     */
    private String goodsId;

    /**
     * 商品名称
     */
    private String shpMingCheng;

    private String shlDanWei;

    private String hiti;

    private String shpBianMakh;

    /**
     * 重量
     */
    private String zhongLiang;
}
