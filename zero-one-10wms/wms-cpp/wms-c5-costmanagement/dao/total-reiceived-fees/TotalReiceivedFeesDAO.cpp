#include "TotalReiceivedFeesDAO.h"
#include "stdafx.h"
#include "TotalReiceivedFeesMapper.h"
#include "sstream"


uint64_t TotalReiceivedFeesDAO::count(const TotalReiceivedFeesQuery::Wrapper& query) {
	stringstream ss;
	SqlParams params;
	ss << "SELECT count(*) FROM wm_day_cost WHERE cost_js='Y'";
	if (query->feestartdate && !query->feestartdate->empty()) {
		ss << " AND cost_data>=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->feestartdate.getValue(""));
	}
	if (query->feeenddate && !query->feeenddate->empty()) {
		ss << " AND cost_data<=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->feeenddate.getValue(""));
	}
	if (query->customers && !query->customers->empty()) {
		ss << " AND cus_code=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->customers.getValue(""));
	}
	if (query->fees && !query->fees->empty()) {
		ss << " AND cost_code=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->fees.getValue(""));
	}
	return sqlSession->executeQueryNumerical(ss.str(), params);
}
// 分页查询数据
std::list<DayCostDO> TotalReiceivedFeesDAO::selectWithPage(const TotalReiceivedFeesQuery::Wrapper& query) {
	stringstream ss;
	SqlParams params;
	ss << "SELECT cost_data,cus_code,cus_name,cost_code,\
		cost_name,cost_sl,cost_unit,day_cost_yj,day_cost_bhs,day_cost_se,\
		day_cost_hsj,id FROM wm_day_cost WHERE cost_js='Y'";
	if (query->feestartdate && !query->feestartdate->empty()) {
		ss << " AND cost_data>=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->feestartdate.getValue(""));
	}
	if (query->feeenddate && !query->feeenddate->empty()) {
		ss << " AND cost_data<=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->feeenddate.getValue(""));
	}
	if (query->customers && !query->customers->empty()) {
		ss << " AND cus_code=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->customers.getValue(""));
	}
	if (query->fees && !query->fees->empty()) {
		ss << " AND cost_code=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->fees.getValue(""));
	}
	ss << " LIMIT " << std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	TotalReiceivedFeesMapper mapper;
	return sqlSession->executeQuery<DayCostDO>(ss.str(), mapper, params);
}