package com.zeroone.star.stockln.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.Setter;

import java.io.Serializable;

/**
 * 效期预警报表视图 mv_stock_yj
 */
@Getter
@Setter
@TableName("mv_stock_yj")
public class MvStockYj implements Serializable {

    private static final long serialVersionUID = 1L;

    private String id;

    /**
     * 库存类型
     */
    private String kuctype;

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
     * 商品编码
     */
    private String goodsId;

    /**
     * 商品名称
     */
    private String shpMingCheng;

    private String shlDanWei;

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

    /**
     * 剩余天数
     */
    private Double resDate;

    private String quHuoCiXu;

    private String shangJiaCiXu;

    private String shpBianMakh;

    /**
     * 过期比例（剩余比例）
     */
    private String guoqibili;
}
