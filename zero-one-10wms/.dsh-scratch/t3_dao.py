# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

# ---------- DAO.h (gb18030) ----------
p = "wms-cpp/wms-c7-reposity/dao/library/LibraryDAO.h"
enc = detect(open(p, 'rb').read())
new_h = '''#pragma once
/*
 @Author: nanbowan
*/

#ifndef _LIBRARY_DAO_
#define _LIBRARY_DAO_
#include "BaseDAO.h"
#include "domain/do/library/LibraryDO.h"
#include "domain/dto/library/LibraryDTO.h"
#include "domain/query/library/LibraryQuery.h"
#include "LibraryMapper.h"

/**
 * 库位类型数据操作实现
 */
class LibraryDAO : public BaseDAO
{
private:
\t//************************************
\t// Method:      queryConditionBuilder
\t// FullName:    LibraryDAO::queryConditionBuilder
\t// Access:      private
\t// Returns:     std::string 返回条件SQL语句，即WHERE部分的语句
\t// Parameter:   const LibraryQuery::Wrapper& query 查询数据对象
\t// Parameter:   SqlParams& params 存放查询数据的参数对象
\t// Description: 查询条件构建器，根据LibraryQuery对象动态构建查询条件相关参数
\t//************************************
\tinline std::string queryConditionBuilder(const LibraryQuery::Wrapper& query, SqlParams& params);
public:
\t// 修改数据
\tint update(const LibraryDO& uObj);
\t// 通过ID删除数据
\tint deleteById(string id);

\t// 统计数据条数
\tuint64_t count(const LibraryQuery::Wrapper& query);
\t// 分页查询数据
\tstd::list<LibraryDO> selectWithPage(const LibraryQuery::Wrapper& query);
\t// 查询库位类型名称列表
\tstd::list<LibraryNameDO> selectLibraryNameList();
\t// 插入数据
\tuint64_t insert(const LibraryDO& iObj);
};
#endif // !_LIBRARY_DAO_

'''
open(p, 'wb').write(new_h.encode(enc))
print("LibraryDAO.h ->", enc)

# ---------- DAO.cpp (utf-8) ----------
p2 = "wms-cpp/wms-c7-reposity/dao/library/LibraryDAO.cpp"
enc2 = detect(open(p2, 'rb').read())
new_cpp = '''/*
 @Author: nanbowan
*/
#include "stdafx.h"
#include "LibraryDAO.h"

#include <sstream>


int LibraryDAO::update(const LibraryDO& uObj)
{
\tstring sql = "UPDATE `ba_bin_type` SET `bin_type_code`=?, `bin_type_name`=? WHERE `id`=?";
\treturn sqlSession->executeUpdate(sql, "%s%s%s", uObj.getCode(), uObj.getName(), uObj.getId());
}

int LibraryDAO::deleteById(string id)
{
\tif (id == "0") {
\t\tstring sql = "DELETE FROM `ba_bin_type` ";
\t\tsqlSession->executeUpdate(sql);
\t\treturn 1;
\t}

\tstring sql = "DELETE FROM `ba_bin_type` WHERE `id`=?";
\treturn sqlSession->executeUpdate(sql, "%s", id);
}

uint64_t LibraryDAO::count(const LibraryQuery::Wrapper& query)
{
\tSqlParams params;
\tstring sql = "SELECT COUNT(*) FROM `ba_bin_type` ";
\t// 构建查询条件
\tsql += queryConditionBuilder(query, params);
\t// 执行查询
\treturn sqlSession->executeQueryNumerical(sql, params);
}

std::list<LibraryDO> LibraryDAO::selectWithPage(const LibraryQuery::Wrapper& query)
{
\tSqlParams params;
\tstring sql = "SELECT id, bin_type_code, bin_type_name FROM `ba_bin_type` ";
\t// 构建查询条件
\tsql += queryConditionBuilder(query, params);
\t// 构建分页条件
\tsql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
\t// 执行查询
\tLibraryMapper mapper;
\treturn sqlSession->executeQuery<LibraryDO>(sql, mapper, params);
}

std::list<LibraryNameDO> LibraryDAO::selectLibraryNameList()
{
\tstring sql = "SELECT id, bin_type_code, bin_type_name FROM `ba_bin_type` ";
\tLibraryNameMapper mapper;
\treturn sqlSession->executeQuery<LibraryNameDO>(sql, mapper);
}

uint64_t LibraryDAO::insert(const LibraryDO& iObj)
{
\tstring sql = "INSERT INTO `ba_bin_type` (`id`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code`, `bin_type_code`, `bin_type_name`) VALUES (?,?,?,NOW(),?,?,NOW(),?,?,?,?)";
\treturn sqlSession->executeInsert(sql, "%s%s%s%s%s%s%s%s", iObj.getId(), iObj.getCreateName(), iObj.getCreateBy(),
\t\tiObj.getUpdateName(), iObj.getUpdateBy(), iObj.getSysOrgCode(), iObj.getSysCompanyCode(),
\t\tiObj.getCode(), iObj.getName());
}

inline std::string LibraryDAO::queryConditionBuilder(const LibraryQuery::Wrapper& query, SqlParams& params)
{
\tstringstream sqlCondition;
\tsqlCondition << " WHERE 1=1";
\tif (query->bin_type_code)
\t{
\t\tsqlCondition << " AND bin_type_code = ?";
\t\tSQLPARAMS_PUSH(params, "s", std::string, query->bin_type_code.getValue(""));
\t}
\tif (query->bin_type_name)
\t{
\t\tsqlCondition << " AND bin_type_name = ?";
\t\tSQLPARAMS_PUSH(params, "s", std::string, query->bin_type_name.getValue(""));
\t}
\treturn sqlCondition.str();
}
'''
open(p2, 'wb').write(new_cpp.encode(enc2))
print("LibraryDAO.cpp ->", enc2)
