/*
 Copyright Zero One Star. All rights reserved.

 @Author: greent
 @Date: 2025/3/6 18:22:55

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
#include "CompanyStateDAO.h"
#include "CompanyStateMapper.h"
#include <sstream>

// 企业状态的录入/修改/删除统一使用独立表 ba_com_sta（原为借用的 ba_kehuzhuangtai）
uint64_t CompanyStateDAO::insert(const CompanyStateDO& iObj)
{
	string sql = "INSERT INTO `ba_com_sta` (`id`, `com_sta_code`, `com_sta_name`, `com_sta_del`, `create_name`, `create_by`, `create_date`, `sys_org_code`, `sys_company_code`) VALUES (?, ?, ?, ?, ?, ?, ?, ?,?)";
	return sqlSession->executeInsert(sql, "%s%s%s%s%s%s%s%s%s", iObj.getId(), iObj.getClientId(), iObj.getClientName(), iObj.getState(), iObj.getUserName(), iObj.getLoginName(), iObj.getDate(), iObj.getOrgDept(), iObj.getOrgCompany());
}

int CompanyStateDAO::update(const CompanyStateDO& uObj)
{
	string sql = "UPDATE `ba_com_sta` SET `com_sta_code` = ?, `com_sta_name` = ?, `com_sta_del` = ?,  `update_name` = ?, `update_by` = ?, `update_date` = ?, `sys_org_code` = ?, `sys_company_code` = ? WHERE `id` = ?";
	return sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s%s%s", uObj.getClientId(), uObj.getClientName(), uObj.getState(), uObj.getUserName(), uObj.getLoginName(), uObj.getDate(), uObj.getOrgDept(), uObj.getOrgCompany(), uObj.getId());
}

int CompanyStateDAO::deleteById(vector<string>& ids)
{
	string sql = "DELETE FROM `ba_com_sta` WHERE `id`=?";

	for (auto id : ids)
	{
		int res = sqlSession->executeUpdate(sql, "%s", id);

		if (res != 1) {
			return res;
		}
	}
	return 1;
}
