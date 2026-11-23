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
// 本文件为PLC指令服务层补充实现：批量删除、导出、执行、导入
#include "stdafx.h"
#include "PlcService.h"
#include "../../dao/plc-file/PlcDAO.h"

// 批量删除
uint64_t PlcService::removeBatch(const std::list<string>& ids)
{
	PlcDAO dao;
	return dao.deleteBatch(ids);
}

// 导出查询
std::list<PlcDO> PlcService::listAllForExport(const PlcFileQuery::Wrapper& query)
{
	PlcDAO dao;
	return dao.selectAllForExport(query);
}

// 执行单条指令
// 说明：当前为服务器侧执行模拟，核心为取出指令集并更新执行时间/结果；
// 接入真实 PLC 硬件时在此处替换为设备通道调用（TCP/Modbus 等）。
bool PlcService::executeOne(const string& id)
{
	PlcDAO dao;
	auto plc = dao.selectConsById(id);
	if (!plc) return false;
	// 指令集不能为空
	if (plc->getcom_cons().empty()) return false;
	// 模拟执行成功，记录执行结果与时间
	return dao.markExecuted(id, "executed") == 1;
}

// 批量执行
uint64_t PlcService::executeBatch(const std::list<string>& ids)
{
	uint64_t successCount = 0;
	for (const auto& id : ids)
	{
		if (executeOne(id)) successCount++;
	}
	return successCount;
}

// 导入
bool PlcService::importData(const std::vector<std::vector<std::string>>& xdata, const string& name, const string& realname, const string& orgcode, const string& companycode)
{
	if (xdata.size() <= 1) return false;
	PlcDAO dao;
	return dao.importAllData(xdata, name, realname, orgcode, companycode);
}
