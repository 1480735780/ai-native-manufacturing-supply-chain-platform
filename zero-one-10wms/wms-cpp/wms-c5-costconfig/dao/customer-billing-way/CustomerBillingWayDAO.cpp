#include "stdafx.h"
#include "CustomerBillingWayDAO.h"
#include "CustomerBillingWayMapper.h"
#include <sstream>

// build where clause from query
std::string CustomerBillingWayDAO::queryConditionBuilder(const CustomerBillingWayQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";

	if (query->code) {
        sqlCondition << " AND `kehuzhuangtai_code` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->code.getValue("") + "%");
	}

	if (query->name) {
        sqlCondition << " AND `kehuzhuangtai_name` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->name.getValue("") + "%");
	}

	if (query->cus_sta_del) {
        sqlCondition << " AND `cus_sta_del` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cus_sta_del.getValue("") + "%");
	}

	if (query->createName) {
        sqlCondition << " AND `create_name`=?";
        SQLPARAMS_PUSH(params, "s", std::string, query->createName.getValue(""));
	}

	if (query->createBy) {
        sqlCondition << " AND `create_by`=?";
        SQLPARAMS_PUSH(params, "s", std::string, query->createBy.getValue(""));
	}

	if (query->updateName) {
        sqlCondition << " AND `update_name`=?";
        SQLPARAMS_PUSH(params, "s", std::string, query->updateName.getValue(""));
	}

	if (query->updateBy) {
        sqlCondition << " AND `update_by`=?";
        SQLPARAMS_PUSH(params, "s", std::string, query->updateBy.getValue(""));
	}

	if (query->sysOrgCode) {
        sqlCondition << " AND `sys_org_code`=?";
        SQLPARAMS_PUSH(params, "s", std::string, query->sysOrgCode.getValue(""));
	}

	if (query->sysCompanyCode) {
        sqlCondition << " AND `sys_company_code`=?";
        SQLPARAMS_PUSH(params, "s", std::string, query->sysCompanyCode.getValue(""));
	}

	return sqlCondition.str();
}

// insert one row
std::string CustomerBillingWayDAO::insert(const CustomerBillingWayDO& iObj)
{
	UuidFacade uf(1);
	std::string id = uf.genUuid();

	string sql = "INSERT INTO `ba_kehuzhuangtai` ("
		"`id`, "
		"`kehuzhuangtai_code`, "
		"`kehuzhuangtai_name`, "
		"`cus_sta_del`, "
		"`create_name`, "
		"`create_by`, "
		"`create_date`, "
		"`update_name`, "
		"`update_by`, "
		"`update_date`, "
		"`sys_org_code`, "
		"`sys_company_code`) "
		"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

	if (sqlSession->executeUpdate(sql,
		"%s%s%s%s%s%s%s%s%s%s%s%s",
		id,
		iObj.getKehuzhuangtaiCode(),
		iObj.getKehuzhuangtaiName(),
		iObj.getCusStaDel(),
		iObj.getCreateName(),
		iObj.getCreateBy(),
		iObj.getCreateDate(),
		iObj.getUpdateName(),
		iObj.getUpdateBy(),
		iObj.getUpdateDate(),
		iObj.getSysOrgCode(),
		iObj.getSysCompanyCode()) == 1) {
		return id;
	}
	return "";
}

// update one row by id
bool CustomerBillingWayDAO::update(const CustomerBillingWayDO& iObj)
{
	string sql = "UPDATE `ba_kehuzhuangtai` SET "
		"`kehuzhuangtai_code` = ?, "
		"`kehuzhuangtai_name` = ?, "
		"`cus_sta_del` = ?, "
		"`update_name` = ?, "
		"`update_by` = ?, "
		"`update_date` = ?, "
		"`sys_org_code` = ?, "
		"`sys_company_code` = ? "
		"WHERE `id` = ? ";

	return sqlSession->executeUpdate(sql,
		"%s%s%s%s%s%s%s%s%s",
		iObj.getKehuzhuangtaiCode(),
		iObj.getKehuzhuangtaiName(),
		iObj.getCusStaDel(),
		iObj.getUpdateName(),
		iObj.getUpdateBy(),
		iObj.getUpdateDate(),
		iObj.getSysOrgCode(),
		iObj.getSysCompanyCode(),
		iObj.getId()) == 1;
}

uint64_t CustomerBillingWayDAO::count(const CustomerBillingWayQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM `ba_kehuzhuangtai` ";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<CustomerBillingWayDO> CustomerBillingWayDAO::selectName(const CustomerBillingWayQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT `id`,`kehuzhuangtai_name` FROM `ba_kehuzhuangtai` ";
	sql += queryConditionBuilder(query, params);
	CustomerBillingWayMapperName mapper;
	return sqlSession->executeQuery<CustomerBillingWayDO>(sql, mapper, params);
}

std::list<CustomerBillingWayDO> CustomerBillingWayDAO::selectAllWithPage(const CustomerBillingWayQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `kehuzhuangtai_code`, `kehuzhuangtai_name`, `cus_sta_del`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `ba_kehuzhuangtai` ";
	sql += queryConditionBuilder(query, params);
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	CustomerBillingWayMapperAll mapper;
	return sqlSession->executeQuery<CustomerBillingWayDO>(sql, mapper, params);
}

// batch delete by ids
int CustomerBillingWayDAO::deleteByIds(const std::vector<std::string>& ids)
{
	if (ids.empty()) return 0;
	SqlParams params;
	string sql = "DELETE FROM `ba_kehuzhuangtai` WHERE `id` IN (";
	for (size_t i = 0; i < ids.size(); i++)
	{
		sql += (i == 0 ? "?" : ",?");
		SQLPARAMS_PUSH(params, "s", std::string, ids[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

// select all rows for export
std::list<CustomerBillingWayDO> CustomerBillingWayDAO::selectForExport()
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `kehuzhuangtai_code`, `kehuzhuangtai_name`, `cus_sta_del`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `ba_kehuzhuangtai` ORDER BY `kehuzhuangtai_code`";
	CustomerBillingWayMapperAll mapper;
	return sqlSession->executeQuery<CustomerBillingWayDO>(sql, mapper, params);
}

// select one row by id
std::list<CustomerBillingWayDO> CustomerBillingWayDAO::selectById(const std::string& id)
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `kehuzhuangtai_code`, `kehuzhuangtai_name`, `cus_sta_del`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `ba_kehuzhuangtai` WHERE `id` = ?";
	SQLPARAMS_PUSH(params, "s", std::string, id);
	CustomerBillingWayMapperAll mapper;
	return sqlSession->executeQuery<CustomerBillingWayDO>(sql, mapper, params);
}
