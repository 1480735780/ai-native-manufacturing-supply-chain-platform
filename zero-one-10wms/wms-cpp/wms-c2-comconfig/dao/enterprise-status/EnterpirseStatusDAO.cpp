#include "stdafx.h"
#include <sstream>
#include "EnterpirseStatusDAO.h"
#include "EnterpirseStatusMapper.h"
#include "stdafx.h"

std::string EnterpriseStatusDAO::queryConditionBuilder(const GetEnterpriseStatusQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->name) {

		sqlCondition << " AND `com_sta_name`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->name.getValue(""));
	}
	if (query->code) {

		sqlCondition << " AND `com_sta_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->code.getValue(""));
	}
	if (query->id) {

		sqlCondition << " AND `id`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->id.getValue(""));
	}
	if (query->ban) {

		sqlCondition << " AND `com_sta_del`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->ban.getValue(""));
	}
	return sqlCondition.str();
}

std::list<CustomerStatusDO> EnterpriseStatusDAO::selectWithPage(const GetEnterpriseStatusQuery::Wrapper& query)
{
	SqlParams params;
	// 企业状态独立表 ba_com_sta，不再借用 jeewms.ba_cus_sta（客户状态表）
	string sql = "SELECT com_sta_name, com_sta_code, id, com_sta_del FROM ba_com_sta ";
	// 构建查询条件
	sql += queryConditionBuilder(query, params);
	// 构建分页条件
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

	// 执行查询
	EnterpriseStatusMapper mapper;
	return sqlSession->executeQuery<CustomerStatusDO>(sql, mapper, params);
}

uint64_t EnterpriseStatusDAO::count(const GetEnterpriseStatusQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM ba_com_sta ";
	// 构建查询条件
	sql += queryConditionBuilder(query, params);
	// 执行查询
	return sqlSession->executeQueryNumerical(sql, params);
}

uint64_t EnterpriseStatusDAO::insert(const CustomerStatusDO& iObj)
{
	string sql = "INSERT INTO `ba_com_sta` (com_sta_name, com_sta_code, id, com_sta_del) VALUES(?, ?, ?, ?)";
	return sqlSession->executeInsert(sql, "%s%s%s%s", iObj.getName(), iObj.getCode(), iObj.getId(), iObj.getBan());
}
