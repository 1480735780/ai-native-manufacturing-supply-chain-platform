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
// 本文件为月台定义模块服务层补充实现：名称列表、条件分页、录入、批量删除、导入
#include "stdafx.h"
#include "DefPlatService.h"
#include "../../dao/def-plat/DefPlatDAO.h"

// 查询月台名称列表（未停用）
std::list<PlatDO> DefPlatService::DefNameListData()
{
	DefPlatDAO dao;
	return dao.queryNameList();
}

// 条件分页查询
DefListPageDTO::Wrapper DefPlatService::DefListData(const DefPlatQuery::Wrapper& query)
{
	auto pages = DefListPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;
	// 查询总数
	DefPlatDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0)
	{
		return pages;
	}
	pages->total = count;
	pages->calcPages();
	// 分页查询
	std::list<PlatDO> rows = dao.selectWithPage(query);
	for (const auto& sub : rows)
	{
		auto dto = DefListDto::createShared();
		dto->id = sub.getid();
		dto->platform_code = sub.getplatform_code();
		dto->platform_name = sub.getplatform_name();
		dto->create_name = sub.getcreate_name();
		dto->create_date = sub.getcreate_date();
		pages->addData(dto);
	}
	return pages;
}

// 录入月台
int DefPlatService::DefAddData(const DefAddDto::Wrapper& dto, const PayloadDTO& payload)
{
	// 参数校验
	if (!dto->platform_code || dto->platform_code->empty()
		|| !dto->platform_name || dto->platform_name->empty())
		return -1;
	// 代码查重
	DefPlatDAO dao;
	if (dao.countByCode(dto->platform_code.getValue("")) > 0)
		return 0;
	// 封装DO
	PlatDO data;
	data.setplatform_code(dto->platform_code.getValue(""));
	data.setplatform_name(dto->platform_name.getValue(""));
	data.setcreate_name(payload.getUsername());
	data.setcreate_by(payload.getRealname());
	data.setsys_org_code(payload.getOrgcode());
	data.setsys_company_code(payload.getCompanycode());
	// 执行插入
	return dao.insert(data);
}

// 批量删除（逻辑删除）
uint64_t DefPlatService::DefBatchDeleteData(const std::list<string>& ids)
{
	DefPlatDAO dao;
	return dao.deleteBatch(ids);
}

// 导入月台
bool DefPlatService::DefImportData(const std::vector<std::vector<std::string>>& xdata, const PayloadDTO& payload)
{
	if (xdata.size() <= 1) return false; // 至少需要表头+一行数据
	DefPlatDAO dao;
	return dao.importAllData(xdata, payload.getUsername(), payload.getId(), payload.getOrgcode(), payload.getCompanycode());
}
