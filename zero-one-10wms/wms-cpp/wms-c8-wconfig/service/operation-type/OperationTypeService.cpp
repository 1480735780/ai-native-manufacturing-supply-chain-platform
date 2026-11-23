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
#include "OperationTypeService.h"
#include "../../dao/operation-type/OperationTypeDAO.h"
#include "ExcelComponent.h"

OperationTypePageDTO::Wrapper OperationTypeService::listAll(const OperationTypeQuery::Wrapper& query)
{
	// 定义分页对象
	auto pages = OperationTypePageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	// 查询数据总数
	OperationTypeDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0)
	{
		return pages;
	}

	// 分页查询数据
	pages->total = count;
	pages->calcPages();
	list<OperationTypeDO> result = dao.selectWithPage(query);
	// 将DO转换成DTO
	for (OperationTypeDO sub : result)
	{
		auto dto = OperationTypeDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, code, Code, name, Name);
		pages->addData(dto);
	}
	return pages;
}

int OperationTypeService::saveData(const OperationTypeAddDTO::Wrapper& dto, string name, string realname, string orgcode, string companycode)
{
	// 组装DO数据
	OperationTypeDO data;
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Code, code, Name, name);
	// 执行数据插入
	OperationTypeDAO dao;
	return dao.insert(data, name, realname, orgcode, companycode);
}

bool OperationTypeService::updateData(const OperationTypeDTO::Wrapper& dto)
{
	// 组装DO数据
	OperationTypeDO data;
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Id, id, Code, code, Name, name);
	// 执行数据修改
	OperationTypeDAO dao;
	return dao.update(data) == 1;
}

bool OperationTypeService::removeData(const string id)
{
	OperationTypeDAO dao;
	return dao.deleteById(id) == 1;
}

bool OperationTypeService::batchDeleteOperationType(const OperationTypeBatchDeleteDto::Wrapper& dto)
{
	if (!dto->ids || dto->ids->empty())
	{
		return false;
	}
	OperationTypeDAO dao;
	return dao.batchDelete(dto) > 0;
}

int OperationTypeService::importOperationType(const char* data, size_t size, string name, string realname, string orgcode, string companycode)
{
	if (data == nullptr || size == 0)
	{
		return -1;
	}
	// 页签名称（xlnt只能存储utf8，读取中文内容时需要转换）
	std::string sheetName = ZH_WORDS_GETTER("op.excel.name");
	// 读取文件内容
	auto readData = ExcelComponent::readIntoVector(data, size, sheetName);
	if (readData.empty())
	{
		return -1;
	}

	int result = -1;
	for (size_t i = 0; i < readData.size(); i++)
	{
		auto& row = readData[i];
		// 第一行为表头，需要校验
		if (i == 0)
		{
			if (row.size() != 2 || row[0] != ZH_WORDS_GETTER("op.excel.col.first") || row[1] != ZH_WORDS_GETTER("op.excel.col.second"))
			{
				return -1;
			}
			result = 0;
			continue;
		}
		// 跳过空行
		if (row.size() < 2 || (row[0].empty() && row[1].empty()))
		{
			continue;
		}
		OperationTypeDO temp;
		temp.setCode(row[0]);
		temp.setName(row[1]);
		// 逐条插入（携带审计信息）
		OperationTypeDAO dao;
		dao.insert(temp, name, realname, orgcode, companycode);
	}
	return result;
}

std::vector<unsigned char> OperationTypeService::exportOperationType()
{
	OperationTypeDAO dao;
	list<OperationTypeDO> result = dao.selectAll();

	std::vector<std::vector<std::string>> data;
	// 写入表头
	std::vector<std::string> first;
	first.push_back(ZH_WORDS_GETTER("op.excel.col.first"));
	first.push_back(ZH_WORDS_GETTER("op.excel.col.second"));
	data.push_back(first);

	for (auto it = result.begin(); it != result.end(); ++it)
	{
		std::vector<std::string> row;
		row.push_back(it->getCode());
		row.push_back(it->getName());
		data.push_back(row);
	}

	// 页签名称（xlnt只能存储utf8，读取中文内容时需要转换）
	std::string sheetName = ZH_WORDS_GETTER("op.excel.name");
	// 将数据以excel格式写入buff中
	ExcelComponent excel;
	return excel.writeVectorToBuff(sheetName, data);
}
