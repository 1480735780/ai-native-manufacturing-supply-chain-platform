/*
 Copyright Zero One Star. All rights reserved.

 @Author: dev-yuetaiguanli
 @Date: 2026/11/22

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
// 本文件为月台定义模块补充实现：名称列表、条件分页、录入、批量删除、导入、代码查重
#include "stdafx.h"
#include "DefPlatDAO.h"
#include "DefPlatMapper.h"
#include "../../lib-common/include/id/UuidFacade.h"
#include <algorithm>

// 查询条件构造器
std::string DefPlatDAO::queryConditionBuilder(const DefPlatQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	// 未停用（platform_del 为空或 0）
	if (query->platform_code) {
		sqlCondition << " AND `platform_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->platform_code.getValue(""));
	}
	if (query->platform_name) {
		sqlCondition << " AND `platform_name` LIKE CONCAT('%',?,'%')";
		SQLPARAMS_PUSH(params, "s", std::string, query->platform_name.getValue(""));
	}
	return sqlCondition.str();
}

// 当前时间字符串
std::string DefPlatDAO::getCurrentDateTime()
{
	std::time_t now = std::time(nullptr);
	char buf[20];
	std::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
	return std::string(buf);
}

// 查询月台名称列表（未停用）
std::list<PlatDO> DefPlatDAO::queryNameList() {
	string sql = "SELECT `id`,`platform_code`,`platform_name` FROM `ba_platform` WHERE `platform_del` IS NULL OR `platform_del`='0' OR `platform_del`=''";
	DefPlatMapper mapper;
	return sqlSession->executeQuery<PlatDO>(sql, mapper);
}

// 条件查询计数
uint64_t DefPlatDAO::count(const DefPlatQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM `ba_platform` ";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

// 条件分页查询
std::list<PlatDO> DefPlatDAO::selectWithPage(const DefPlatQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT `id`,`platform_code`,`platform_name`,`create_name`,`create_date` FROM `ba_platform` ";
	sql += queryConditionBuilder(query, params);
	sql += " ORDER BY `create_date` DESC, `id` DESC";
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	DefPlatPageMapper mapper;
	return sqlSession->executeQuery<PlatDO>(sql, mapper, params);
}

// 新增数据
int DefPlatDAO::insert(const PlatDO& iObj)
{
	std::string id = iObj.getid();
	if (id.empty()) {
		UuidFacade uf(0);
		id = uf.genUuid();
		id.erase(std::remove(id.begin(), id.end(), '-'), id.end());
	}
	string sql = "INSERT INTO `ba_platform` (`id`, `create_name`, `create_by`, `create_date`, `sys_org_code`, `sys_company_code`, `platform_code`, `platform_name`) "
		"VALUES(?, ?, ?, ?, ?, ?, ?, ?)";
	return sqlSession->executeInsert(sql, "%s%s%s%s%s%s%s%s",
		id, iObj.getcreate_name(), iObj.getcreate_by(), getCurrentDateTime(),
		iObj.getsys_org_code(), iObj.getsys_company_code(),
		iObj.getplatform_code(), iObj.getplatform_name());
}

// 批量删除（逻辑删除，置停用）
uint64_t DefPlatDAO::deleteBatch(const std::list<string>& ids)
{
	if (ids.empty()) return 0;
	string sql = "UPDATE `ba_platform` SET `platform_del`='1' WHERE `id` IN (";
	// 参数化 IN 列表
	SqlParams params;
	int i = 0;
	for (const auto& id : ids) {
		if (i > 0) sql += ",";
		sql += "?";
		SQLPARAMS_PUSH(params, "s", std::string, id);
		i++;
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

// 检查月台代码是否已存在
uint64_t DefPlatDAO::countByCode(const string& platform_code)
{
	string sql = "SELECT COUNT(*) FROM `ba_platform` WHERE `platform_code`=? AND (`platform_del` IS NULL OR `platform_del`='0' OR `platform_del`='')";
	return sqlSession->executeQueryNumerical(sql, "%s", platform_code);
}

// 批量导入数据
bool DefPlatDAO::importAllData(const std::vector<std::vector<std::string>>& xdata, const string& create_name, const string& create_by, const string& orgcode, const string& companycode)
{
	string sql = "INSERT INTO `ba_platform` (`id`, `create_name`, `create_by`, `create_date`, `sys_org_code`, `sys_company_code`, `platform_code`, `platform_name`) "
		"VALUES (?, ?, ?, NOW(), ?, ?, ?, ?)";
	try {
		auto conn = sqlSession->getConnection();
		if (conn == nullptr)return false;
		// 从第二行开始解析（第一行为表头）
		for (size_t i = 1; i < xdata.size(); i++) {
			const auto& row = xdata[i];
			if (row.size() < 2) continue; // 列不足跳过
			UuidFacade uuidObj;
			string uid = uuidObj.genUuid();
			uid.erase(std::remove(uid.begin(), uid.end(), '-'), uid.end());
			string platform_code = row[0];
			string platform_name = row[1];
			std::unique_ptr<sql::PreparedStatement> pstmt(conn->prepareStatement(sql));
			pstmt->setString(1, uid);
			pstmt->setString(2, create_name);
			pstmt->setString(3, create_by);
			pstmt->setString(4, orgcode);
			pstmt->setString(5, companycode);
			pstmt->setString(6, platform_code);
			pstmt->setString(7, platform_name);
			pstmt->executeUpdate();
		}
	}
	catch (sql::SQLException& ex) {
		cerr << ex.what() << endl;
		return false;
	}
	return true;
}
