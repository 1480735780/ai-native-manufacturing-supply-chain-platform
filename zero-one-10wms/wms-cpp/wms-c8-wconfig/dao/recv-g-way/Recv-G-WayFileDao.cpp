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
#include "Recv-G-WayFileDao.h"
#include "Recv-G-WayMapper.h"
#include"../../lib-common/include/id/UuidFacade.h"




std::string Recv_G_WayDAO::Recv_G_WayqueryConditionBuilder(const Recv_G_WayQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->del_mode_name) {

		sqlCondition << " AND `del_mode_name`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->del_mode_name.getValue(""));
	}
	if (query->del_mode_code) {

		sqlCondition << " AND `del_mode_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->del_mode_code.getValue(""));
	}

	return sqlCondition.str();
}

uint64_t Recv_G_WayDAO::count(const Recv_G_WayQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM ba_del_mode ";
	// 构建查询条件
	sql += Recv_G_WayqueryConditionBuilder(query, params);
	// 执行查询
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<Recv_G_WayDO> Recv_G_WayDAO::selectWithPage(const Recv_G_WayQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT id,del_mode_name,del_mode_code FROM ba_del_mode ";
	// 构建查询条件
	sql += Recv_G_WayqueryConditionBuilder(query, params);
	// 构建分页条件
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

	// 执行查询
	Recv_G_WayMapper mapper;
	return sqlSession->executeQuery<Recv_G_WayDO>(sql, mapper, params);
}

std::list<Recv_G_WayDO> Recv_G_WayDAO::selectAll()
{
	string sql = "SELECT id,del_mode_name,del_mode_code FROM ba_del_mode ";
	// 执行查询
	Recv_G_WayMapper mapper;
	return sqlSession->executeQuery<Recv_G_WayDO>(sql, mapper);
}


int Recv_G_WayDAO::insert(const Recv_G_WayDO& iObj, string name, string realname, string orgcode, string companycode)
{

	std::string currentTime = getCurrentDateTime(); //update_date
	UuidFacade uf(1);
	std::string id = uf.genUuid();
	string sql = "INSERT INTO `ba_del_mode` (`id`,`create_name`, `create_by`, `create_date`, `sys_org_code`,`sys_company_code`, `del_mode_name`, `del_mode_code`) VALUES (?,?,?,?,?,?,?,?)";
	return sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s%s", id,name, realname, currentTime, orgcode, companycode, iObj.getDel_mode_name(), iObj.getDel_mode_code());
}

uint64_t Recv_G_WayDAO::insert(const list<Recv_G_WayDO>& data, string name, string realname, string orgcode, string companycode)
{
	if (data.empty())
	{
		return 0;
	}
	std::string currentTime = getCurrentDateTime();
	UuidFacade uf(1);
	// 构建多行插入语句
	string sql = "INSERT INTO `ba_del_mode` (`id`,`create_name`, `create_by`, `create_date`, `sys_org_code`,`sys_company_code`, `del_mode_name`, `del_mode_code`) VALUES ";
	SqlParams params;
	for (auto it = data.begin(); it != data.end(); ++it)
	{
		if (it != data.begin())
		{
			sql += ", ";
		}
		sql += "(?,?,?,?,?,?,?,?)";
		SQLPARAMS_PUSH(params, "s", string, uf.genUuid());
		SQLPARAMS_PUSH(params, "s", string, name);
		SQLPARAMS_PUSH(params, "s", string, realname);
		SQLPARAMS_PUSH(params, "dt", string, currentTime);
		SQLPARAMS_PUSH(params, "s", string, orgcode);
		SQLPARAMS_PUSH(params, "s", string, companycode);
		SQLPARAMS_PUSH(params, "s", string, it->getDel_mode_name());
		SQLPARAMS_PUSH(params, "s", string, it->getDel_mode_code());
	}
	// 主键为字符串uuid，LAST_INSERT_ID 无意义，故使用 executeUpdate 返回受影响行数
	return sqlSession->executeUpdate(sql, params);
}

int Recv_G_WayDAO::update(const Recv_G_WayDO& uObj)
{
	std::string currentTime = getCurrentDateTime();
	string sql = "UPDATE `ba_del_mode` SET `update_date`=?,`del_mode_name`=?,`del_mode_code`=? WHERE `id`=?";
	return sqlSession->executeUpdate(sql,"%s%s%s%s", currentTime,uObj.getDel_mode_name(), uObj.getDel_mode_code(), uObj.getId());
}

int Recv_G_WayDAO::deleteById(string id)
{
	string sql = "DELETE FROM `ba_del_mode` WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s", id);
}

int Recv_G_WayDAO::batchDelete(const Recv_G_WayBatchDeleteDto::Wrapper& dto)
{
	if (!dto->ids || dto->ids->empty())
	{
		return 0;
	}
	// 使用参数化查询，避免拼接字符串带来的注入风险
	SqlParams params;
	string sql = "DELETE FROM `ba_del_mode` WHERE `id` IN (";
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

std::string Recv_G_WayDAO::getCurrentDateTime() {
	std::time_t now = std::time(nullptr);
	char buf[20];
	std::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
	return std::string(buf);
}
