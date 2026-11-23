#include "stdafx.h"
#include "MoveGoodsDAO.h"
#include "MoveGoodsMapper.h"
#include <sstream>
#include <cstdlib>

namespace
{
	bool hasValue(const oatpp::String& value)
	{
		return value && !value->empty();
	}

	std::string likeValue(const oatpp::String& value)
	{
		return "%" + std::string(value->c_str()) + "%";
	}
}

std::string MoveGoodsDAO::queryConditionBuilder(const MoveGoodsQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE (move_sta IS NULL OR move_sta <> ?)";
	SQLPARAMS_PUSH(params, "s", std::string, std::string(ZH_WORDS_GETTER("move-goods.delete.move-sta.del")));
	if (hasValue(query->id)) {
		sqlCondition << " AND id=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->id->c_str()));
	}
	if (hasValue(query->goodsID)) {
		sqlCondition << " AND goods_id=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->goodsID->c_str()));
	}
	if (hasValue(query->goodsName)) {
		sqlCondition << " AND goods_name LIKE ?";
		SQLPARAMS_PUSH(params, "s", std::string, likeValue(query->goodsName));
	}
	if (hasValue(query->cusCode)) {
		sqlCondition << " AND cus_code=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->cusCode->c_str()));
	}
	if (hasValue(query->cusName)) {
		sqlCondition << " AND cus_name LIKE ?";
		SQLPARAMS_PUSH(params, "s", std::string, likeValue(query->cusName));
	}
	if (hasValue(query->toCusCode)) {
		sqlCondition << " AND to_cus_code=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->toCusCode->c_str()));
	}
	if (hasValue(query->toCusName)) {
		sqlCondition << " AND to_cus_name LIKE ?";
		SQLPARAMS_PUSH(params, "s", std::string, likeValue(query->toCusName));
	}
	if (hasValue(query->tinFrom)) {
		sqlCondition << " AND tin_from=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->tinFrom->c_str()));
	}
	if (hasValue(query->tinTo)) {
		sqlCondition << " AND tin_id=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->tinTo->c_str()));
	}
	if (hasValue(query->binFrom)) {
		sqlCondition << " AND bin_from=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->binFrom->c_str()));
	}
	if (hasValue(query->binTo)) {
		sqlCondition << " AND bin_to=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->binTo->c_str()));
	}
	if (hasValue(query->moveSta)) {
		sqlCondition << " AND move_sta=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->moveSta->c_str()));
	}
	if (hasValue(query->runSta)) {
		sqlCondition << " AND run_sta=?";
		SQLPARAMS_PUSH(params, "s", std::string, std::string(query->runSta->c_str()));
	}
	return sqlCondition.str();
}

uint64_t MoveGoodsDAO::count(const MoveGoodsQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM wm_to_move_goods";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<MoveGoodsDO> MoveGoodsDAO::selectWithPage(const MoveGoodsQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT id,create_name,create_by,create_date,update_name,update_by,update_date,"
		"sys_org_code,sys_company_code,order_type_code,order_id,order_id_i,goods_id,goods_name,"
		"goods_qua,goods_pro_data,goods_unit,cus_code,cus_name,tin_from,tin_id,bin_from,bin_to,"
		"move_sta,to_cus_code,to_cus_name,base_unit,base_goodscount,to_goods_pro_data,run_sta "
		"FROM wm_to_move_goods";
	sql += queryConditionBuilder(query, params);
	sql += " ORDER BY create_date DESC";
	uint64_t pageIndex = query->pageIndex.getValue(1);
	uint64_t pageSize = query->pageSize.getValue(10);
	if (pageIndex < 1) pageIndex = 1;
	if (pageSize < 1) pageSize = 10;
	sql += " LIMIT " + std::to_string((pageIndex - 1) * pageSize) + "," + std::to_string(pageSize);

	MoveGoodsMapper mapper;
	return sqlSession->executeQuery<MoveGoodsDO>(sql, mapper, params);
}

int MoveGoodsDAO::insert(const MoveGoodsDO& data)
{
	string sql = "INSERT INTO wm_to_move_goods("
		"id,create_name,create_by,create_date,order_type_code,goods_id,goods_name,goods_qua,"
		"goods_pro_data,goods_unit,cus_code,cus_name,tin_from,tin_id,bin_from,bin_to,move_sta,"
		"to_cus_code,to_cus_name,base_unit,base_goodscount,to_goods_pro_data,run_sta) "
		"VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";
	SqlParams params;
	SQLPARAMS_PUSH(params, "s", std::string, data.getId());
	SQLPARAMS_PUSH(params, "s", std::string, data.getCreateName());
	SQLPARAMS_PUSH(params, "s", std::string, data.getCreateBy());
	SQLPARAMS_PUSH(params, "s", std::string, data.getCreateDate());
	SQLPARAMS_PUSH(params, "s", std::string, data.getOrderTypeCode());
	SQLPARAMS_PUSH(params, "s", std::string, data.getGoodsId());
	SQLPARAMS_PUSH(params, "s", std::string, data.getGoodsName());
	SQLPARAMS_PUSH(params, "s", std::string, data.getGoodsQua());
	SQLPARAMS_PUSH(params, "s", std::string, data.getGoodsProData());
	SQLPARAMS_PUSH(params, "s", std::string, data.getGoodsUnit());
	SQLPARAMS_PUSH(params, "s", std::string, data.getCusCode());
	SQLPARAMS_PUSH(params, "s", std::string, data.getCusName());
	SQLPARAMS_PUSH(params, "s", std::string, data.getTinFrom());
	SQLPARAMS_PUSH(params, "s", std::string, data.getTinId());
	SQLPARAMS_PUSH(params, "s", std::string, data.getBinFrom());
	SQLPARAMS_PUSH(params, "s", std::string, data.getBinTo());
	SQLPARAMS_PUSH(params, "s", std::string, data.getMoveSta());
	SQLPARAMS_PUSH(params, "s", std::string, data.getToCusCode());
	SQLPARAMS_PUSH(params, "s", std::string, data.getToCusName());
	SQLPARAMS_PUSH(params, "s", std::string, data.getBaseUnit());
	SQLPARAMS_PUSH(params, "s", std::string, data.getBaseGoodscount());
	SQLPARAMS_PUSH(params, "s", std::string, data.getToGoodsProData());
	SQLPARAMS_PUSH(params, "s", std::string, data.getRunSta());
	return sqlSession->executeUpdate(sql, params);
}

int MoveGoodsDAO::updateById(const MoveGoodsDO& data)
{
	string sql = "UPDATE wm_to_move_goods SET "
		"goods_qua=COALESCE(NULLIF(?,''),goods_qua),"
		"base_goodscount=COALESCE(NULLIF(?,''),base_goodscount),"
		"tin_id=COALESCE(NULLIF(?,''),tin_id),"
		"bin_to=COALESCE(NULLIF(?,''),bin_to),"
		"to_cus_code=COALESCE(NULLIF(?,''),to_cus_code),"
		"to_cus_name=COALESCE(NULLIF(?,''),to_cus_name),"
		"goods_pro_data=COALESCE(NULLIF(?,''),goods_pro_data),"
		"to_goods_pro_data=COALESCE(NULLIF(?,''),to_goods_pro_data),"
		"move_sta=COALESCE(NULLIF(?,''),move_sta),"
		"update_by=?,update_date=? "
		"WHERE id=? AND (move_sta IS NULL OR move_sta<>?) AND (run_sta IS NULL OR run_sta<>?)";
	SqlParams params;
	SQLPARAMS_PUSH(params, "s", std::string, data.getGoodsQua());
	SQLPARAMS_PUSH(params, "s", std::string, data.getBaseGoodscount());
	SQLPARAMS_PUSH(params, "s", std::string, data.getTinId());
	SQLPARAMS_PUSH(params, "s", std::string, data.getBinTo());
	SQLPARAMS_PUSH(params, "s", std::string, data.getToCusCode());
	SQLPARAMS_PUSH(params, "s", std::string, data.getToCusName());
	SQLPARAMS_PUSH(params, "s", std::string, data.getGoodsProData());
	SQLPARAMS_PUSH(params, "s", std::string, data.getToGoodsProData());
	SQLPARAMS_PUSH(params, "s", std::string, data.getMoveSta());
	SQLPARAMS_PUSH(params, "s", std::string, data.getUpdateBy());
	SQLPARAMS_PUSH(params, "s", std::string, data.getUpdateDate());
	SQLPARAMS_PUSH(params, "s", std::string, data.getId());
	SQLPARAMS_PUSH(params, "s", std::string, std::string(ZH_WORDS_GETTER("move-goods.delete.move-sta.del")));
	SQLPARAMS_PUSH(params, "s", std::string, std::string(ZH_WORDS_GETTER("move-goods.run.done")));
	return sqlSession->executeUpdate(sql, params);
}

int MoveGoodsDAO::batchUpdateStatus(const std::vector<std::string>& ids, const std::string& moveSta,
	const std::string& runSta, const std::string& usrName, const std::string& updateDate)
{
	if (ids.empty()) return 0;

	SqlParams params;
	string sql = "UPDATE wm_to_move_goods SET move_sta=?,run_sta=?,update_by=?,update_date=? "
		"WHERE (move_sta IS NULL OR move_sta<>?) AND (run_sta IS NULL OR run_sta<>?) AND id IN(";
	SQLPARAMS_PUSH(params, "s", std::string, moveSta);
	SQLPARAMS_PUSH(params, "s", std::string, runSta);
	SQLPARAMS_PUSH(params, "s", std::string, usrName);
	SQLPARAMS_PUSH(params, "s", std::string, updateDate);
	SQLPARAMS_PUSH(params, "s", std::string, std::string(ZH_WORDS_GETTER("move-goods.delete.move-sta.del")));
	SQLPARAMS_PUSH(params, "s", std::string, std::string(ZH_WORDS_GETTER("move-goods.run.done")));
	for (size_t i = 0; i < ids.size(); i++)
	{
		sql += "?";
		if (i < ids.size() - 1) sql += ",";
		SQLPARAMS_PUSH(params, "s", std::string, ids[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

PtrMoveGoodsDO MoveGoodsDAO::selectDetailedById(const oatpp::String  queryID)
{
	string sql = "SELECT goods_id,goods_name,goods_qua,goods_pro_data,goods_unit,cus_code,cus_name,"
		"tin_from,tin_id,bin_from,bin_to,move_sta,to_cus_code,to_cus_name,base_goodscount,"
		"to_goods_pro_data FROM wm_to_move_goods where id = ?";
	PtrMoveGoodsDetailedMapper mapper;
	string id = queryID->c_str();
	return sqlSession->executeQueryOne<PtrMoveGoodsDO>(sql, mapper, "%s", id);
}

std::vector<std::vector<string>> MoveGoodsDAO::selectDownLoadById(const vector<string>& ids)
{
	SqlParams params;
	string sql = "SELECT create_by,create_date,order_id_i,goods_id,goods_name,goods_qua,goods_pro_data,"
		"goods_unit,cus_code,cus_name,tin_from,tin_id,bin_from,bin_to,move_sta,to_cus_code,to_cus_name,"
		"base_unit, base_goodscount, to_goods_pro_data  FROM wm_to_move_goods  WHERE id IN(";
	for (size_t i = 0; i < ids.size(); i++)
	{
		sql += "?";
		if (i < ids.size() - 1)
		{
			sql += ",";
		}
		SQLPARAMS_PUSH(params, "s", std::string, ids[i]);
	}
	sql += ")";
	MoveGoodsDownLoadMapper mapper;
	auto list = sqlSession->executeQuery<MoveGoodsDO>(sql, mapper, params);
	std::vector<std::vector<string>> res;
	std::vector<string> sub;
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.create-by"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.create-date"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.order-id-i"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.cus-code"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.cus-name"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.goods-id"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.goods-name"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.now-num"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.goods-unit"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.move-num"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.goods-base-unit"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.produce-date"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.bin-from"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.tin-from"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.to-cus-code"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.to-cus-name"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.bin-to"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.tin-id"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.to-produce-date"));
	sub.push_back(ZH_WORDS_GETTER("move-goods.field.move-sta"));
	res.push_back(sub);
	for (auto& item : list)
	{
		std::vector<string> sub;
		sub.push_back(item.getCreateBy());
		sub.push_back(item.getCreateDate());
		sub.push_back(item.getOrderIdI());
		sub.push_back(item.getCusCode());
		sub.push_back(item.getCusName());
		sub.push_back(item.getGoodsId());
		sub.push_back(item.getGoodsName());
		sub.push_back(item.getGoodsQua());
		sub.push_back(item.getGoodsUnit());
		sub.push_back(item.getBaseGoodscount());
		sub.push_back(item.getBaseUnit());
		sub.push_back(item.getGoodsProData());
		sub.push_back(item.getBinFrom());
		sub.push_back(item.getTinFrom());
		sub.push_back(item.getToCusCode());
		sub.push_back(item.getToCusName());
		sub.push_back(item.getBinTo());
		sub.push_back(item.getTinId());
		sub.push_back(item.getToGoodsProData());
		sub.push_back(item.getMoveSta());
		res.push_back(sub);
	}
	return res;

}

//获取当前日期时间
std::string getCurrentDateTime() {
	// 获取当前时间点 
	auto now = std::chrono::system_clock::now();
	// 将时间点转换为time_t类型 
	std::time_t now_time_t = std::chrono::system_clock::to_time_t(now);
	// 将time_t转换为tm结构体 
	std::tm now_tm = *std::localtime(&now_time_t);
	// 使用stringstream格式化日期和时间 
	std::stringstream ss;
	ss << std::put_time(&now_tm, "%Y-%m-%d %H:%M:%S");
	// 返回格式化后的日期时间字符串 
	return ss.str();
}

int MoveGoodsDAO::deleteById(const vector<string> id,const string usrName)
{
	SqlParams params;
	string updateDate = getCurrentDateTime();
	string sql = "UPDATE wm_to_move_goods SET update_date=?,update_by=?,move_sta=? WHERE `id`IN(";
	SQLPARAMS_PUSH(params, "s", std::string, updateDate);
	SQLPARAMS_PUSH(params, "s", std::string, usrName);
	SQLPARAMS_PUSH(params, "s", std::string, std::string(ZH_WORDS_GETTER("move-goods.delete.move-sta.del")));
	for (size_t i = 0; i < id.size(); i++)
	{
		sql += "?";
		if (i < id.size() - 1)
		{
			sql += ",";
		}
		SQLPARAMS_PUSH(params, "s", std::string, id[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}
