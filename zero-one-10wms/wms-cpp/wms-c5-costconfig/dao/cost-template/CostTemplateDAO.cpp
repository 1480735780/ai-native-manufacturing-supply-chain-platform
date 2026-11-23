#include "stdafx.h"
#include "CostTemplateDAO.h"
#include "CostTemplateMapper.h"
#include <sstream>

// build where clause from query
std::string CostTemplateDAO::queryConditionBuilder(const CostTemplateQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";

	if (query->code) {
        sqlCondition << " AND `cost_code` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->code.getValue("") + "%");
	}

	if (query->cost_jg) {
        sqlCondition << " AND `cost_jg` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cost_jg.getValue("") + "%");
	}

	if (query->cost_sl) {
        sqlCondition << " AND `cost_sl` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cost_sl.getValue("") + "%");
	}

	if (query->cost_zk) {
        sqlCondition << " AND `cost_zk` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cost_zk.getValue("") + "%");
	}

	if (query->cost_bhs) {
        sqlCondition << " AND `cost_bhs` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cost_bhs.getValue("") + "%");
	}

	if (query->cost_hs) {
        sqlCondition << " AND `cost_hs` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->cost_hs.getValue("") + "%");
	}

	if (query->free_day) {
        sqlCondition << " AND `free_day` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->free_day.getValue("") + "%");
	}

	if (query->free_day2) {
        sqlCondition << " AND `free_day2` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->free_day2.getValue("") + "%");
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
std::string CostTemplateDAO::insert(const CostTemplateDO& iObj)
{
	UuidFacade uf(1);
	std::string id = uf.genUuid();

	string sql = "INSERT INTO `ba_cost_conf` ("
		"`id`, "
		"`cost_code`, "
		"`cost_jg`, "
		"`cost_sl`, "
		"`cost_zk`, "
		"`cost_bhs`, "
		"`cost_hs`, "
		"`free_day`, "
		"`free_day2`, "
		"`create_name`, "
		"`create_by`, "
		"`create_date`, "
		"`update_name`, "
		"`update_by`, "
		"`update_date`, "
		"`sys_org_code`, "
		"`sys_company_code`) "
		"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

	if (sqlSession->executeUpdate(sql,
		"%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s",
		id,
		iObj.getCostCode(),
		iObj.getCostJg(),
		iObj.getCostSl(),
		iObj.getCostZk(),
		iObj.getCostBhs(),
		iObj.getCostHs(),
		iObj.getFreeDay(),
		iObj.getFreeDay2(),
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
bool CostTemplateDAO::update(const CostTemplateDO& iObj)
{
	string sql = "UPDATE `ba_cost_conf` SET "
		"`cost_code` = ?, "
		"`cost_jg` = ?, "
		"`cost_sl` = ?, "
		"`cost_zk` = ?, "
		"`cost_bhs` = ?, "
		"`cost_hs` = ?, "
		"`free_day` = ?, "
		"`free_day2` = ?, "
		"`update_name` = ?, "
		"`update_by` = ?, "
		"`update_date` = ?, "
		"`sys_org_code` = ?, "
		"`sys_company_code` = ? "
		"WHERE `id` = ? ";

	return sqlSession->executeUpdate(sql,
		"%s%s%s%s%s%s%s%s%s%s%s%s%s%s",
		iObj.getCostCode(),
		iObj.getCostJg(),
		iObj.getCostSl(),
		iObj.getCostZk(),
		iObj.getCostBhs(),
		iObj.getCostHs(),
		iObj.getFreeDay(),
		iObj.getFreeDay2(),
		iObj.getUpdateName(),
		iObj.getUpdateBy(),
		iObj.getUpdateDate(),
		iObj.getSysOrgCode(),
		iObj.getSysCompanyCode(),
		iObj.getId()) == 1;
}

uint64_t CostTemplateDAO::count(const CostTemplateQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM `ba_cost_conf` ";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<CostTemplateDO> CostTemplateDAO::selectName(const CostTemplateQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT `id`,`cost_code` FROM `ba_cost_conf` ";
	sql += queryConditionBuilder(query, params);
	CostTemplateMapperName mapper;
	return sqlSession->executeQuery<CostTemplateDO>(sql, mapper, params);
}

std::list<CostTemplateDO> CostTemplateDAO::selectAllWithPage(const CostTemplateQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `cost_code`, `cost_jg`, `cost_sl`, `cost_zk`, `cost_bhs`, `cost_hs`, `free_day`, `free_day2`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `ba_cost_conf` ";
	sql += queryConditionBuilder(query, params);
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	CostTemplateMapperAll mapper;
	return sqlSession->executeQuery<CostTemplateDO>(sql, mapper, params);
}

// batch delete by ids
int CostTemplateDAO::deleteByIds(const std::vector<std::string>& ids)
{
	if (ids.empty()) return 0;
	SqlParams params;
	string sql = "DELETE FROM `ba_cost_conf` WHERE `id` IN (";
	for (size_t i = 0; i < ids.size(); i++)
	{
		sql += (i == 0 ? "?" : ",?");
		SQLPARAMS_PUSH(params, "s", std::string, ids[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

// select all rows for export
std::list<CostTemplateDO> CostTemplateDAO::selectForExport()
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `cost_code`, `cost_jg`, `cost_sl`, `cost_zk`, `cost_bhs`, `cost_hs`, `free_day`, `free_day2`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `ba_cost_conf` ORDER BY `cost_code`";
	CostTemplateMapperAll mapper;
	return sqlSession->executeQuery<CostTemplateDO>(sql, mapper, params);
}

// select one row by id
std::list<CostTemplateDO> CostTemplateDAO::selectById(const std::string& id)
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `cost_code`, `cost_jg`, `cost_sl`, `cost_zk`, `cost_bhs`, `cost_hs`, `free_day`, `free_day2`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `ba_cost_conf` WHERE `id` = ?";
	SQLPARAMS_PUSH(params, "s", std::string, id);
	CostTemplateMapperAll mapper;
	return sqlSession->executeQuery<CostTemplateDO>(sql, mapper, params);
}
