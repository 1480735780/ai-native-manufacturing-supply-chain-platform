#pragma once
#ifndef _STOCK_TRANSFER_DO_
#define _STOCK_TRANSFER_DO_
#include "domain/do/DoInclude.h"

/**
 * 可转移库存行数据对象(来源视图 wv_stock_stt)
 */
class StockTransferDO {
	CC_SYNTHESIZE(string, id, Id);							// 库存行唯一标识
	CC_SYNTHESIZE(string, create_date, CreateDate);			// 移动日期
	CC_SYNTHESIZE(string, kuctype, KucType);				// 库存类型
	CC_SYNTHESIZE(string, bin, Bin);						// 储位
	CC_SYNTHESIZE(string, tin, Tin);						// 托盘
	CC_SYNTHESIZE(string, cus_code, CusCode);				// 货主
	CC_SYNTHESIZE(string, cus_name, CusName);				// 货主名称
	CC_SYNTHESIZE(string, goods_id, GoodsId);				// 商品编码
	CC_SYNTHESIZE(string, goods_qua, GoodsQua);				// 商品数量
	CC_SYNTHESIZE(string, goods_name, GoodsName);			// 商品名称
	CC_SYNTHESIZE(string, goods_pro_data, GoodsProData);	// 生产日期
	CC_SYNTHESIZE(string, bzhi_qi, BzhiQi);					// 保质期
	CC_SYNTHESIZE(string, goods_unit, GoodsUnit);			// 单位
	CC_SYNTHESIZE(string, move_sta, MoveSta);				// 状态

public:
	StockTransferDO()
	{
		id = "";
		create_date = "";
		kuctype = "";
		bin = "";
		tin = "";
		cus_code = "";
		cus_name = "";
		goods_id = "";
		goods_qua = "";
		goods_name = "";
		goods_pro_data = "";
		bzhi_qi = "";
		goods_unit = "";
		move_sta = "";
	}
};

typedef std::shared_ptr<StockTransferDO> PtrStockTransferDO;

#endif // !_STOCK_TRANSFER_DO_
