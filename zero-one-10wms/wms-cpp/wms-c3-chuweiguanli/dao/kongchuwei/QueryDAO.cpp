#include "stdafx.h"
#include "QueryDAO.h"
#include "QueryMapper.h"
#include <sstream>

std::string QueryDAO::queryConditionBuilder(const DaoChuKongChuWeiQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->bin_store) {

		sqlCondition << " AND bin_store=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->bin_store.getValue(""));
	}
	if (query->ku_wei_shu_xing) {

		sqlCondition << " AND ku_wei_shu_xing=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->ku_wei_shu_xing.getValue(""));
	}
	if (query->CHP_SHU_XING) {

		sqlCondition << " AND CHP_SHU_XING=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->CHP_SHU_XING.getValue(""));
	}
	if (query->ku_wei_bian_ma) {

		sqlCondition << " AND ku_wei_bian_ma=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->ku_wei_bian_ma.getValue(""));
	}
	return sqlCondition.str();
}

uint64_t QueryDAO::count(const DaoChuKongChuWeiQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM md_bin ";
	// 构建查询条件
	sql += queryConditionBuilder(query, params);
	// 执行查询
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<BinDO> QueryDAO::selectWithPage(const DaoChuKongChuWeiQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT bin_store,ku_wei_shu_xing,CHP_SHU_XING,ku_wei_bian_ma,suo_shu_ke_hu,zui_da_ti_ji,shang_jia_ci_xu,chang,kuan,gao,zui_da_tuo_pan,ting_yong,ku_wei_lei_xing FROM md_bin ";
	// 构建查询条件
	sql += queryConditionBuilder(query, params);
	// 构建分页条件
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

	// 执行查询
	QueryMapper mapper;
	return sqlSession->executeQuery<BinDO>(sql, mapper, params);
}

// condition builder for the empty-bin query
// an "empty bin" = enabled (ting_yong=N) and no stock in wv_stock on its ku_wei_bian_ma
std::string QueryDAO::kongChuWeiConditionBuilder(const GetKongChuWeiListMycontrollerQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->id) {
		sqlCondition << " AND id=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->id.getValue(""));
	}
	if (query->bin_store) {
		sqlCondition << " AND bin_store=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->bin_store.getValue(""));
	}
	if (query->chuweishuxing) {
		sqlCondition << " AND ku_wei_shu_xing=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->chuweishuxing.getValue(""));
	}
	if (query->chp_shu_xing) {
		sqlCondition << " AND CHP_SHU_XING=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->chp_shu_xing.getValue(""));
	}
	if (query->chuweibaima) {
		sqlCondition << " AND ku_wei_bian_ma=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->chuweibaima.getValue(""));
	}
	if (query->suo_shu_ke_hu) {
		sqlCondition << " AND suo_shu_ke_hu=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->suo_shu_ke_hu.getValue(""));
	}
	if (query->zui_da_ti_ji) {
		sqlCondition << " AND zui_da_ti_ji=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->zui_da_ti_ji.getValue(""));
	}
	if (query->shang_jia_ci_XU) {
		sqlCondition << " AND shang_jia_ci_xu=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->shang_jia_ci_XU.getValue(""));
	}
	if (query->chang) {
		sqlCondition << " AND chang=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->chang.getValue(""));
	}
	if (query->kuan) {
		sqlCondition << " AND kuan=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->kuan.getValue(""));
	}
	if (query->gao) {
		sqlCondition << " AND gao=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->gao.getValue(""));
	}
	if (query->zui_da_tuo_pan) {
		sqlCondition << " AND zui_da_tuo_pan=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->zui_da_tuo_pan.getValue(""));
	}
	if (query->ku_wei_lei_xing) {
		sqlCondition << " AND ku_wei_lei_xing=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->ku_wei_lei_xing.getValue(""));
	}
	// status filter: N = enabled; only enabled bins can be "empty bins"
	sqlCondition << " AND ting_yong = ?";
	SQLPARAMS_PUSH(params, "s", std::string, "N");
	// emptiness: no in-stock record on this bin
	sqlCondition << " AND NOT EXISTS (SELECT 1 FROM wv_stock ws WHERE ws.ku_wei_bian_ma = md_bin.ku_wei_bian_ma)";
	return sqlCondition.str();
}

uint64_t QueryDAO::countKongChuWei(const GetKongChuWeiListMycontrollerQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM md_bin ";
	sql += kongChuWeiConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<BinDO> QueryDAO::selectKongChuWeiWithPage(const GetKongChuWeiListMycontrollerQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT id,bin_store,ku_wei_shu_xing,CHP_SHU_XING,ku_wei_bian_ma,suo_shu_ke_hu,zui_da_ti_ji,shang_jia_ci_xu,chang,kuan,gao,zui_da_tuo_pan,ting_yong,ku_wei_lei_xing FROM md_bin ";
	sql += kongChuWeiConditionBuilder(query, params);
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	KongChuWeiMapper mapper;
	return sqlSession->executeQuery<BinDO>(sql, mapper, params);
}
