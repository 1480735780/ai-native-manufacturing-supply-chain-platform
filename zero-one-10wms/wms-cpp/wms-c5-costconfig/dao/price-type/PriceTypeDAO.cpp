#include "stdafx.h"
#include "PriceTypeDAO.h"
#include "PriceTypeMapper.h"
#include <sstream>

// build where clause from query
std::string PriceTypeDAO::queryConditionBuilder(const PriceTypeQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";

	if (query->code) {
        sqlCondition << " AND `price_type_code` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->code.getValue("") + "%");
	}

	if (query->name) {
        sqlCondition << " AND `price_type_name` LIKE ?";
        SQLPARAMS_PUSH(params, "s", std::string, "%" + query->name.getValue("") + "%");
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
std::string PriceTypeDAO::insert(const PriceTypeDO& iObj)
{
	UuidFacade uf(1);
	std::string id = uf.genUuid();

	string sql = "INSERT INTO `ba_price_type` ("
		"`id`, "
		"`price_type_code`, "
		"`price_type_name`, "
		"`create_name`, "
		"`create_by`, "
		"`create_date`, "
		"`update_name`, "
		"`update_by`, "
		"`update_date`, "
		"`sys_org_code`, "
		"`sys_company_code`) "
		"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

	if (sqlSession->executeUpdate(sql,
		"%s%s%s%s%s%s%s%s%s%s%s",
		id,
		iObj.getPriceTypeCode(),
		iObj.getPriceTypeName(),
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
bool PriceTypeDAO::update(const PriceTypeDO& iObj)
{
	string sql = "UPDATE `ba_price_type` SET "
		"`price_type_code` = ?, "
		"`price_type_name` = ?, "
		"`update_name` = ?, "
		"`update_by` = ?, "
		"`update_date` = ?, "
		"`sys_org_code` = ?, "
		"`sys_company_code` = ? "
		"WHERE `id` = ? ";

	return sqlSession->executeUpdate(sql,
		"%s%s%s%s%s%s%s%s",
		iObj.getPriceTypeCode(),
		iObj.getPriceTypeName(),
		iObj.getUpdateName(),
		iObj.getUpdateBy(),
		iObj.getUpdateDate(),
		iObj.getSysOrgCode(),
		iObj.getSysCompanyCode(),
		iObj.getId()) == 1;
}

uint64_t PriceTypeDAO::count(const PriceTypeQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM `ba_price_type` ";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<PriceTypeDO> PriceTypeDAO::selectName(const PriceTypeQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT `id`,`price_type_name` FROM `ba_price_type` ";
	sql += queryConditionBuilder(query, params);
	PriceTypeMapperName mapper;
	return sqlSession->executeQuery<PriceTypeDO>(sql, mapper, params);
}

std::list<PriceTypeDO> PriceTypeDAO::selectAllWithPage(const PriceTypeQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `price_type_code`, `price_type_name`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `ba_price_type` ";
	sql += queryConditionBuilder(query, params);
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	PriceTypeMapperAll mapper;
	return sqlSession->executeQuery<PriceTypeDO>(sql, mapper, params);
}

// batch delete by ids
int PriceTypeDAO::deleteByIds(const std::vector<std::string>& ids)
{
	if (ids.empty()) return 0;
	SqlParams params;
	string sql = "DELETE FROM `ba_price_type` WHERE `id` IN (";
	for (size_t i = 0; i < ids.size(); i++)
	{
		sql += (i == 0 ? "?" : ",?");
		SQLPARAMS_PUSH(params, "s", std::string, ids[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

// select all rows for export
std::list<PriceTypeDO> PriceTypeDAO::selectForExport()
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `price_type_code`, `price_type_name`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `ba_price_type` ORDER BY `price_type_code`";
	PriceTypeMapperAll mapper;
	return sqlSession->executeQuery<PriceTypeDO>(sql, mapper, params);
}

// select one row by id
std::list<PriceTypeDO> PriceTypeDAO::selectById(const std::string& id)
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, `price_type_code`, `price_type_name`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code` "
		"FROM `ba_price_type` WHERE `id` = ?";
	SQLPARAMS_PUSH(params, "s", std::string, id);
	PriceTypeMapperAll mapper;
	return sqlSession->executeQuery<PriceTypeDO>(sql, mapper, params);
}
