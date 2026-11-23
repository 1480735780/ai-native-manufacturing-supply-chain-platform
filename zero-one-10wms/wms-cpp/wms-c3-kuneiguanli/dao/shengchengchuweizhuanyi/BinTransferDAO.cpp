#include "stdafx.h"
#include "BinTransferDAO.h"
#include "../StockTransferMapper.h"
#include <sstream>

namespace
{
	bool hasValue(const oatpp::String& value)
	{
		return value && !value->empty();
	}
}

std::string BinTransferDAO::queryConditionBuilder(const BinTransferQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (hasValue(query->id)) {
		sqlCondition << " AND ws.id=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->id->c_str()));
	}
	if (hasValue(query->inventoryType)) {
		sqlCondition << " AND ws.kuctype=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->inventoryType->c_str()));
	}
	if (hasValue(query->bin)) {
		sqlCondition << " AND ws.ku_wei_bian_ma=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->bin->c_str()));
	}
	if (hasValue(query->tin)) {
		sqlCondition << " AND ws.bin_id=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->tin->c_str()));
	}
	if (hasValue(query->cusCode)) {
		sqlCondition << " AND ws.cus_code=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->cusCode->c_str()));
	}
	if (hasValue(query->cusName)) {
		sqlCondition << " AND ws.zhong_wen_qch LIKE ?";
		SQLPARAMS_PUSH(params, "s", std::string, "%" + std::string(query->cusName->c_str()) + "%");
	}
	if (hasValue(query->goodsID)) {
		sqlCondition << " AND ws.goods_id=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->goodsID->c_str()));
	}
	if (hasValue(query->goodsName)) {
		sqlCondition << " AND ws.shp_ming_cheng LIKE ?";
		SQLPARAMS_PUSH(params, "s", std::string, "%" + std::string(query->goodsName->c_str()) + "%");
	}
	if (hasValue(query->produceDate)) {
		sqlCondition << " AND ws.goods_pro_data>=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->produceDate->c_str()));
	}
	if (hasValue(query->toProduceDate)) {
		sqlCondition << " AND ws.goods_pro_data<=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->toProduceDate->c_str()));
	}
	if (hasValue(query->moveDate)) {
		sqlCondition << " AND DATE(ws.create_date)>=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->moveDate->c_str()));
	}
	if (hasValue(query->toMoveDate)) {
		sqlCondition << " AND DATE(ws.create_date)<=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->toMoveDate->c_str()));
	}
	return sqlCondition.str();
}

uint64_t BinTransferDAO::count(const BinTransferQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM wv_stock_stt ws";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<StockTransferDO> BinTransferDAO::selectWithPage(const BinTransferQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT ws.id,ws.create_date,ws.kuctype,ws.ku_wei_bian_ma,ws.bin_id,ws.cus_code,"
		"ws.zhong_wen_qch,ws.goods_id,ws.goods_qua,ws.shp_ming_cheng,ws.goods_pro_data,"
		"ws.bzhi_qi,ws.goods_unit,ws.move_sta FROM wv_stock_stt ws";
	sql += queryConditionBuilder(query, params);
	sql += " ORDER BY ws.ku_wei_bian_ma,ws.bin_id";
	uint64_t pageIndex = query->pageIndex.getValue(1);
	uint64_t pageSize = query->pageSize.getValue(10);
	if (pageIndex < 1) pageIndex = 1;
	if (pageSize < 1) pageSize = 10;
	sql += " LIMIT " + std::to_string((pageIndex - 1) * pageSize) + "," + std::to_string(pageSize);

	StockTransferMapper mapper;
	return sqlSession->executeQuery<StockTransferDO>(sql, mapper, params);
}
