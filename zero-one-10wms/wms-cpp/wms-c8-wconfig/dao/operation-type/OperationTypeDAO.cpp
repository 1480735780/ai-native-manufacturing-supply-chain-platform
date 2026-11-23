/*
 Copyright Zero One Star. All rights reserved.

 @Author: zero-one-star
 @Date: 2025/03/10 16:09:12

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

	  https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*/
#include "stdafx.h"
#include "OperationTypeDAO.h"
#include "OperationTypeMapper.h"
#include "../../lib-common/include/id/UuidFacade.h"
#include <sstream>


inline std::string OperationTypeDAO::queryConditionBuilder(const OperationTypeQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->code) {
		sqlCondition << " AND `oper_type_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->code.getValue(""));
	}
	if (query->name) {
		sqlCondition << " AND `oper_type_name`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->name.getValue(""));
	}
	return sqlCondition.str();
}

uint64_t OperationTypeDAO::count(const OperationTypeQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM `ba_oper_type` ";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<OperationTypeDO> OperationTypeDAO::selectWithPage(const OperationTypeQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT id,oper_type_code,oper_type_name FROM `ba_oper_type` ";
	sql += queryConditionBuilder(query, params);
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	OperationTypeMapper mapper;
	return sqlSession->executeQuery<OperationTypeDO>(sql, mapper, params);
}

std::list<OperationTypeDO> OperationTypeDAO::selectAll()
{
	string sql = "SELECT id,oper_type_code,oper_type_name FROM `ba_oper_type` ";
	OperationTypeMapper mapper;
	return sqlSession->executeQuery<OperationTypeDO>(sql, mapper);
}

int OperationTypeDAO::insert(const OperationTypeDO& iObj, string name, string realname, string orgcode, string companycode)
{
	std::string currentTime = getCurrentDateTime();
	UuidFacade uf(1);
	std::string id = uf.genUuid();
	string sql = "INSERT INTO `ba_oper_type` (`id`,`create_name`, `create_by`, `create_date`, `sys_org_code`,`sys_company_code`, `oper_type_code`, `oper_type_name`) VALUES (?,?,?,?,?,?,?,?)";
	return sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s%s", id, name, realname, currentTime, orgcode, companycode, iObj.getCode(), iObj.getName());
}

int OperationTypeDAO::update(const OperationTypeDO& uObj)
{
	std::string currentTime = getCurrentDateTime();
	string sql = "UPDATE `ba_oper_type` SET `update_date`=?,`oper_type_code`=?,`oper_type_name`=? WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s%s%s%s", currentTime, uObj.getCode(), uObj.getName(), uObj.getId());
}

int OperationTypeDAO::deleteById(string id)
{
	string sql = "DELETE FROM `ba_oper_type` WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s", id);
}

int OperationTypeDAO::batchDelete(const OperationTypeBatchDeleteDto::Wrapper& dto)
{
	if (!dto->ids || dto->ids->empty())
	{
		return 0;
	}
	// 使用参数化查询，避免拼接字符串带来的注入风险
	SqlParams params;
	string sql = "DELETE FROM `ba_oper_type` WHERE `id` IN (";
	for (auto it = dto->ids->begin(); it != dto->ids->end(); ++it)
	{
		if (it != dto->ids->begin())
		{
			sql += ", ";
		}
		sql += "?";
		SQLPARAMS_PUSH(params, "s", std::string, it->getValue(""));
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

std::string OperationTypeDAO::getCurrentDateTime() {
	std::time_t now = std::time(nullptr);
	char buf[20];
	std::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
	return std::string(buf);
}
