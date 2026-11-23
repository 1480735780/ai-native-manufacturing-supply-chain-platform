#pragma once
#ifndef _STOCK_TRANSFER_MAPPER_
#define _STOCK_TRANSFER_MAPPER_

#include "Mapper.h"
#include "../domain/do/StockTransferDO.h"

/**
 * 可转移库存行字段映射
 * 查询列顺序：id,create_date,kuctype,ku_wei_bian_ma,bin_id,cus_code,zhong_wen_qch,
 * goods_id,goods_qua,shp_ming_cheng,goods_pro_data,bzhi_qi,goods_unit,move_sta
 */
class StockTransferMapper : public Mapper<StockTransferDO>
{
public:
	StockTransferDO mapper(ResultSet* resultSet) const override
	{
		StockTransferDO data;
		data.setId(resultSet->getString(1));
		data.setCreateDate(resultSet->getString(2));
		data.setKucType(resultSet->getString(3));
		data.setBin(resultSet->getString(4));
		data.setTin(resultSet->getString(5));
		data.setCusCode(resultSet->getString(6));
		data.setCusName(resultSet->getString(7));
		data.setGoodsId(resultSet->getString(8));
		data.setGoodsQua(resultSet->getString(9));
		data.setGoodsName(resultSet->getString(10));
		data.setGoodsProData(resultSet->getString(11));
		data.setBzhiQi(resultSet->getString(12));
		data.setGoodsUnit(resultSet->getString(13));
		data.setMoveSta(resultSet->getString(14));
		return data;
	}
};

#endif // !_STOCK_TRANSFER_MAPPER_
