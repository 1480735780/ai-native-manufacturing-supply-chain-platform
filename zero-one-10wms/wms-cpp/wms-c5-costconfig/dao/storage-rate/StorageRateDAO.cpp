#include "stdafx.h"
#include "StorageRateDAO.h"
#include "StorageRateMapper.h"
#include <sstream>

// build where clause from query
std::string StorageRateDAO::queryConditionBuilder(const StorageRateQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";

	if (query->code) {
        sqlCondition << " AND `cost_code` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->code.getValue("") + "%");
	}

	if (query->cost_yj) {
        sqlCondition << " AND `cost_yj` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cost_yj.getValue("") + "%");
	}

	if (query->cost_zk) {
        sqlCondition << " AND `cost_zk` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cost_zk.getValue("") + "%");
	}

	if (query->cost_sl) {
        sqlCondition << " AND `cost_sl` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cost_sl.getValue("") + "%");
	}

	if (query->cost_bhs) {
        sqlCondition << " AND `cost_bhs` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cost_bhs.getValue("") + "%");
	}

	if (query->cost_hsj) {
        sqlCondition << " AND `cost_hsj` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cost_hsj.getValue("") + "%");
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
std::string StorageRateDAO::insert(const StorageRateDO& iObj)
{
	UuidFacade uf(1);
	std::string id = uf.genUuid();

	string sql = "INSERT INTO `wm_cost_conf` ("
		"`id`, "
		"`cost_code`, "
		"`cost_yj`, "
		"`cost_zk`, "
		"`cost_sl`, "
		"`cost_bhs`, "
		"`cost_hsj`, "
		"`create_name`, "
		"`create_by`, "
		"`create_date`, "
		"`update_name`, "
		"`update_by`, "
		"`update_date`, "
		"`sys_org_code`, "
		"`sys_company_code`) "
		"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

	if (sqlSession->executeUpdate(sql,
		"%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s",
		id,
		iObj.getCostCode(),
		iObj.getCostYj(),
		iObj.getCostZk(),
		iObj.getCostSl(),
		iObj.getCostBhs(),
		iObj.getCostHsj(),
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
bool StorageRateDAO::update(const StorageRateDO& iObj)
{
	string sql = "UPDATE `wm_cost_conf` SET "
		"`cost_code` = ?, "
		"`cost_yj` = ?, "
		"`cost_zk` = ?, "
		"`cost_sl` = ?, "
		"`cost_bhs` = ?, "
		"`cost_hsj` = ?, "
		"`update_name` = ?, "
		"`update_by` = ?, "
		"`update_date` = ?, "
		"`sys_org_code` = ?, "
		"`sys_company_code` = ? "
		"WHERE `id` = ? ";

	return sqlSession->executeUpdate(sql,
		"%s%s%s%s%s%s%s%s%s%s%s%s",
		iObj.getCostCode(),
		iObj.getCostYj(),
		iObj.getCostZk(),
		iObj.getCostSl(),
		iObj.getCostBhs(),
		iObj.getCostHsj(),
		iObj.getUpdateName(),
		iObj.getUpdateBy(),
		iObj.getUpdateDate(),
		iObj.getSysOrgCode(),
		iObj.getSysCompanyCode(),
		iObj.getId()) == 1;
}

uint64_t StorageRateDAO::count(const StorageRateQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM `wm_cost_conf` ";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<StorageRateDO> StorageRateDAO::selectName(const StorageRateQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT `id`,`cost_code` FROM `wm_cost_conf` ";
	sql += queryConditionBuilder(query, params);
	StorageRateMapperName mapper;
	return sqlSession->executeQuery<StorageRateDO>(sql, mapper, params);
}

std::list<StorageRateDO> StorageRateDAO::selectAllWithPage(const StorageRateQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `cost_code`, `cost_yj`, `cost_zk`, `cost_sl`, `cost_bhs`, `cost_hsj`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `wm_cost_conf` ";
	sql += queryConditionBuilder(query, params);
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	StorageRateMapperAll mapper;
	return sqlSession->executeQuery<StorageRateDO>(sql, mapper, params);
}

// batch delete by ids
int StorageRateDAO::deleteByIds(const std::vector<std::string>& ids)
{
	if (ids.empty()) return 0;
	SqlParams params;
	string sql = "DELETE FROM `wm_cost_conf` WHERE `id` IN (";
	for (size_t i = 0; i < ids.size(); i++)
	{
		sql += (i == 0 ? "?" : ",?");
		SQLPARAMS_PUSH(params, "s", std::string, ids[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

// select all rows for export
std::list<StorageRateDO> StorageRateDAO::selectForExport()
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `cost_code`, `cost_yj`, `cost_zk`, `cost_sl`, `cost_bhs`, `cost_hsj`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `wm_cost_conf` ORDER BY `cost_code`";
	StorageRateMapperAll mapper;
	return sqlSession->executeQuery<StorageRateDO>(sql, mapper, params);
}

// select one row by id
std::list<StorageRateDO> StorageRateDAO::selectById(const std::string& id)
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `cost_code`, `cost_yj`, `cost_zk`, `cost_sl`, `cost_bhs`, `cost_hsj`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `wm_cost_conf` WHERE `id` = ?";
	SQLPARAMS_PUSH(params, "s", std::string, id);
	StorageRateMapperAll mapper;
	return sqlSession->executeQuery<StorageRateDO>(sql, mapper, params);
}
