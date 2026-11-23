# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

R = "wms-cpp/wms-c8-wconfig/"

# ================= DAO.h =================
p = R + "dao/recv-g-way/Recv-G-WayFileDao.h"
enc = detect(open(p, 'rb').read())
new_h = '''#pragma once
/*
 Copyright Zero One Star. All rights reserved.

 @Author: zero-one-star
 @Date: 2025/03/10 16:09:12

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

\t  https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*/
#ifndef _RECV_G_WAY_DAO_
#define _RECV_G_WAY_DAO_
#include "BaseDAO.h"
#include "../../domain/do/recv-g-way/Recv-G-WayFileDo.h"
#include "../../domain/query/recv-g-way/Recv-G-Way-FileQuery.h"
#include "../../domain/dto/recv-g-way/Recv-G-WayBatchDeleteDto.h"

/**
 * 接货方式数据访问实现
 */
class Recv_G_WayDAO : public BaseDAO
{
private:
\t//************************************
\t// Method:      queryConditionBuilder
\t// FullName:    Recv_G_WayDAO::Recv_G_WayqueryConditionBuilder
\t// Access:      private
\t// Returns:     std::string 返回条件SQL语句，即WHERE部分的语句
\t// Parameter:   const Recv_G_WayQuery::Wrapper& query 查询数据对象
\t// Parameter:   SqlParams& params 存放查询数据的参数对象
\t// Description: 查询条件构建器，根据Recv_G_WayQuery对象动态构建查询条件相关参数
\t//************************************
\tinline std::string Recv_G_WayqueryConditionBuilder(const Recv_G_WayQuery::Wrapper& query, SqlParams& params);
\tstd::string getCurrentDateTime();
public:
\t// 统计数据条数
\tuint64_t count(const Recv_G_WayQuery::Wrapper& query);
\t// 分页查询数据
\tstd::list<Recv_G_WayDO> selectWithPage(const Recv_G_WayQuery::Wrapper& query);
\t// 插入数据
\tint insert(const Recv_G_WayDO& iObj, string name, string realname, string orgcode, string companycode);
\t// 批量插入数据
\tuint64_t insert(const list<Recv_G_WayDO>& data, string name, string realname, string orgcode, string companycode);
\t// 修改数据
\tint update(const Recv_G_WayDO& uObj);
\t// 通过ID删除数据
\tint deleteById(string id);
\t// 批量删除数据
\tint batchDelete(const Recv_G_WayBatchDeleteDto::Wrapper& dto);
\t// 查询全部数据（供导出使用）
\tstd::list<Recv_G_WayDO> selectAll();
};
#endif // !_RECV_G_WAY_DAO_
'''
open(p, 'wb').write(new_h.encode(enc))
print("Recv-G-WayFileDao.h ->", enc)

# ================= DAO.cpp =================
p = R + "dao/recv-g-way/Recv-G-WayFileDao.cpp"
enc = detect(open(p, 'rb').read())
new_cpp = '''/*
 Copyright Zero One Star. All rights reserved.

 @Author: zero-one-star
 @Date: 2025/03/10 16:09:12

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

\t  https://www.apache.org/licenses/LICENSE-2.0

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
\tstringstream sqlCondition;
\tsqlCondition << " WHERE 1=1";
\tif (query->del_mode_name) {

\t\tsqlCondition << " AND `del_mode_name`=?";
\t\tSQLPARAMS_PUSH(params, "s", std::string, query->del_mode_name.getValue(""));
\t}
\tif (query->del_mode_code) {

\t\tsqlCondition << " AND `del_mode_code`=?";
\t\tSQLPARAMS_PUSH(params, "s", std::string, query->del_mode_code.getValue(""));
\t}

\treturn sqlCondition.str();
}

uint64_t Recv_G_WayDAO::count(const Recv_G_WayQuery::Wrapper& query)
{
\tSqlParams params;
\tstring sql = "SELECT COUNT(*) FROM ba_del_mode ";
\t// 构建查询条件
\tsql += Recv_G_WayqueryConditionBuilder(query, params);
\t// 执行查询
\treturn sqlSession->executeQueryNumerical(sql, params);
}

std::list<Recv_G_WayDO> Recv_G_WayDAO::selectWithPage(const Recv_G_WayQuery::Wrapper& query)
{
\tSqlParams params;
\tstring sql = "SELECT id,del_mode_name,del_mode_code FROM ba_del_mode ";
\t// 构建查询条件
\tsql += Recv_G_WayqueryConditionBuilder(query, params);
\t// 构建分页条件
\tsql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

\t// 执行查询
\tRecv_G_WayMapper mapper;
\treturn sqlSession->executeQuery<Recv_G_WayDO>(sql, mapper, params);
}

std::list<Recv_G_WayDO> Recv_G_WayDAO::selectAll()
{
\tstring sql = "SELECT id,del_mode_name,del_mode_code FROM ba_del_mode ";
\t// 执行查询
\tRecv_G_WayMapper mapper;
\treturn sqlSession->executeQuery<Recv_G_WayDO>(sql, mapper);
}


int Recv_G_WayDAO::insert(const Recv_G_WayDO& iObj, string name, string realname, string orgcode, string companycode)
{

\tstd::string currentTime = getCurrentDateTime(); //update_date
\tUuidFacade uf(1);
\tstd::string id = uf.genUuid();
\tstring sql = "INSERT INTO `ba_del_mode` (`id`,`create_name`, `create_by`, `create_date`, `sys_org_code`,`sys_company_code`, `del_mode_name`, `del_mode_code`) VALUES (?,?,?,?,?,?,?,?)";
\treturn sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s%s", id,name, realname, currentTime, orgcode, companycode, iObj.getDel_mode_name(), iObj.getDel_mode_code());
}

uint64_t Recv_G_WayDAO::insert(const list<Recv_G_WayDO>& data, string name, string realname, string orgcode, string companycode)
{
\tif (data.empty())
\t{
\t\treturn 0;
\t}
\tstd::string currentTime = getCurrentDateTime();
\tUuidFacade uf(1);
\t// 构建多行插入语句
\tstring sql = "INSERT INTO `ba_del_mode` (`id`,`create_name`, `create_by`, `create_date`, `sys_org_code`,`sys_company_code`, `del_mode_name`, `del_mode_code`) VALUES ";
\tSqlParams params;
\tfor (auto it = data.begin(); it != data.end(); ++it)
\t{
\t\tif (it != data.begin())
\t\t{
\t\t\tsql += ", ";
\t\t}
\t\tsql += "(?,?,?,?,?,?,?,?)";
\t\tSQLPARAMS_PUSH(params, "s", string, uf.genUuid());
\t\tSQLPARAMS_PUSH(params, "s", string, name);
\t\tSQLPARAMS_PUSH(params, "s", string, realname);
\t\tSQLPARAMS_PUSH(params, "dt", string, currentTime);
\t\tSQLPARAMS_PUSH(params, "s", string, orgcode);
\t\tSQLPARAMS_PUSH(params, "s", string, companycode);
\t\tSQLPARAMS_PUSH(params, "s", string, it->getDel_mode_name());
\t\tSQLPARAMS_PUSH(params, "s", string, it->getDel_mode_code());
\t}
\t// 主键为字符串uuid，LAST_INSERT_ID 无意义，故使用 executeUpdate 返回受影响行数
\treturn sqlSession->executeUpdate(sql, params);
}

int Recv_G_WayDAO::update(const Recv_G_WayDO& uObj)
{
\tstd::string currentTime = getCurrentDateTime();
\tstring sql = "UPDATE `ba_del_mode` SET `update_date`=?,`del_mode_name`=?,`del_mode_code`=? WHERE `id`=?";
\treturn sqlSession->executeUpdate(sql,"%s%s%s%s", currentTime,uObj.getDel_mode_name(), uObj.getDel_mode_code(), uObj.getId());
}

int Recv_G_WayDAO::deleteById(string id)
{
\tstring sql = "DELETE FROM `ba_del_mode` WHERE `id`=?";
\treturn sqlSession->executeUpdate(sql, "%s", id);
}

int Recv_G_WayDAO::batchDelete(const Recv_G_WayBatchDeleteDto::Wrapper& dto)
{
\tif (!dto->ids || dto->ids->empty())
\t{
\t\treturn 0;
\t}
\t// 使用参数化查询，避免拼接字符串带来的注入风险
\tSqlParams params;
\tstring sql = "DELETE FROM `ba_del_mode` WHERE `id` IN (";
\tfor (auto it = dto->ids->begin(); it != dto->ids->end(); ++it)
\t{
\t\tif (it != dto->ids->begin())
\t\t{
\t\t\tsql += ", ";
\t\t}
\t\tsql += "?";
\t\tSQLPARAMS_PUSH(params, "s", std::string, it->getValue(""));
\t}
\tsql += ")";
\treturn sqlSession->executeUpdate(sql, params);
}

std::string Recv_G_WayDAO::getCurrentDateTime() {
\tstd::time_t now = std::time(nullptr);
\tchar buf[20];
\tstd::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
\treturn std::string(buf);
}
'''
open(p, 'wb').write(new_cpp.encode(enc))
print("Recv-G-WayFileDao.cpp ->", enc)
