#include "stdafx.h"
#include "EnterpriseStatusDAO.h"
#include "EnterpriseStatusMapper.h"
#include <sstream>

std::string EnterpriseStatusDAO::queryConditionBuilder(const EnterpriseQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->enterpriseid) {

		sqlCondition << " AND com_sta_code=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->enterpriseid.getValue(""));
	}
	if (query->enterprisename) {

		sqlCondition << " AND com_sta_name=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->enterprisename.getValue(""));
	}
	return sqlCondition.str();
}

uint64_t EnterpriseStatusDAO::count(const EnterpriseQuery::Wrapper& query)
{
	SqlParams params;
	// 企业状态使用独立表 ba_com_sta，不再借用客户状态表 ba_kehuzhuangtai
	string sql = "SELECT COUNT(*) FROM ba_com_sta ";
	// 构建查询条件
	sql += queryConditionBuilder(query, params);
	// 执行查询
	auto res = sqlSession->executeQueryNumerical(sql, params);
	return res;
}

uint64_t EnterpriseStatusDAO::count1()
{
	// 下拉列表只取未停用的企业状态
	string sql = "SELECT COUNT(*) FROM ba_com_sta WHERE com_sta_del<> 'Y'  ";
	// 执行查询
	return sqlSession->executeQueryNumerical(sql);
}

std::list<EnterpriseStatusDO> EnterpriseStatusDAO::selectWithPage(const EnterpriseQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT id, com_sta_code, com_sta_name, com_sta_del FROM ba_com_sta ";


	// 构建查询条件
	sql += queryConditionBuilder(query, params);
	// 构建分页条件
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

	// 执行查询
	EnterpriseStatusMapper mapper;
	auto res = sqlSession->executeQuery<EnterpriseStatusDO>(sql, mapper, params);
	return res;
}


std::list<EnterpriseStatusListDO> EnterpriseStatusDAO::selectForList()
{
	string sql = "SELECT id,com_sta_code,com_sta_name FROM ba_com_sta WHERE com_sta_del<> 'Y' ";
	EnterpriseStatusListMapper mapper;
	return sqlSession->executeQuery<EnterpriseStatusListDO>(sql, mapper);
}
