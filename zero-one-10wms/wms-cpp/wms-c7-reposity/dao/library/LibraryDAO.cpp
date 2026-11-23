/*
 @Author: nanbowan
*/
#include "stdafx.h"
#include "LibraryDAO.h"

#include <sstream>


int LibraryDAO::update(const LibraryDO& uObj)
{
	string sql = "UPDATE `ba_bin_type` SET `bin_type_code`=?, `bin_type_name`=? WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s%s%s", uObj.getCode(), uObj.getName(), uObj.getId());
}

int LibraryDAO::deleteById(string id)
{
	if (id == "0") {
		string sql = "DELETE FROM `ba_bin_type` ";
		sqlSession->executeUpdate(sql);
		return 1;
	}

	string sql = "DELETE FROM `ba_bin_type` WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s", id);
}

uint64_t LibraryDAO::count(const LibraryQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM `ba_bin_type` ";
	// 构建查询条件
	sql += queryConditionBuilder(query, params);
	// 执行查询
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<LibraryDO> LibraryDAO::selectWithPage(const LibraryQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT id, bin_type_code, bin_type_name FROM `ba_bin_type` ";
	// 构建查询条件
	sql += queryConditionBuilder(query, params);
	// 构建分页条件
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	// 执行查询
	LibraryMapper mapper;
	return sqlSession->executeQuery<LibraryDO>(sql, mapper, params);
}

std::list<LibraryNameDO> LibraryDAO::selectLibraryNameList()
{
	string sql = "SELECT id, bin_type_code, bin_type_name FROM `ba_bin_type` ";
	LibraryNameMapper mapper;
	return sqlSession->executeQuery<LibraryNameDO>(sql, mapper);
}

uint64_t LibraryDAO::insert(const LibraryDO& iObj)
{
	string sql = "INSERT INTO `ba_bin_type` (`id`, `create_name`, `create_by`, `create_date`, `sys_org_code`, `sys_company_code`, `bin_type_code`, `bin_type_name`) VALUES (?,?,?,?,?,?,?,?)";
	return sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s%s", iObj.getId(), iObj.getCreateName(), iObj.getCreateBy(),
		iObj.getCreateDate(), iObj.getSysOrgCode(), iObj.getSysCompanyCode(), iObj.getCode(), iObj.getName());
}

inline std::string LibraryDAO::queryConditionBuilder(const LibraryQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->bin_type_code)
	{
		sqlCondition << " AND bin_type_code = ?";
		SQLPARAMS_PUSH(params, "s", std::string, query->bin_type_code.getValue(""));
	}
	if (query->bin_type_name)
	{
		sqlCondition << " AND bin_type_name = ?";
		SQLPARAMS_PUSH(params, "s", std::string, query->bin_type_name.getValue(""));
	}
	return sqlCondition.str();
}
