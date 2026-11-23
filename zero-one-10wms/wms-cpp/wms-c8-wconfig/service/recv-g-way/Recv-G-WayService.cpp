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
#include "Recv-G-WayService.h"
#include "../../dao/recv-g-way/Recv-G-WayFileDao.h"
#include "ExcelComponent.h"

Recv_G_WayAllDto::Wrapper Recv_G_WayService::listAll(const Recv_G_WayQuery::Wrapper& query)
{
	// 定义分页对象
	auto pages = Recv_G_WayAllDto::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	// 查询数据总数
	Recv_G_WayDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0)
	{
		return pages;
	}

	// 分页查询数据
	pages->total = count;
	pages->calcPages();
	list<Recv_G_WayDO> result = dao.selectWithPage(query);
	// 将DO转换成DTO
	for (Recv_G_WayDO sub : result)
	{
		auto dto = Recv_G_WayEditDto::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, del_mode_code, Del_mode_code, del_mode_name, Del_mode_name,id,Id);
		pages->addData(dto);
	}
	return pages;
}

int Recv_G_WayService::saveData(const Recv_G_WayAddDto::Wrapper& dto, string name, string realname, string orgcode, string companycode)
{
	// 组装DO数据
	Recv_G_WayDO data;
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Del_mode_code, del_mode_code, Del_mode_name, del_mode_name);
	// 执行数据插入
	Recv_G_WayDAO dao;
	return dao.insert(data, name, realname, orgcode, companycode);
}

bool Recv_G_WayService::updateData(const Recv_G_WayEditDto::Wrapper& dto)
{
	// 组装DO数据

	Recv_G_WayDO data;
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Del_mode_code, del_mode_code, Del_mode_name, del_mode_name,Id,id);
	// 执行数据修改
	Recv_G_WayDAO dao;
	return dao.update(data);
}

bool Recv_G_WayService::removeData(const string id)
{
	Recv_G_WayDAO dao;
	return dao.deleteById(id);
}

bool Recv_G_WayService::batchDeleteRecv_G_Way(const Recv_G_WayBatchDeleteDto::Wrapper& dto)
{
	if (!dto->ids || dto->ids->empty())
	{
		return false;
	}
	Recv_G_WayDAO dao;
	return dao.batchDelete(dto) > 0;
}

int Recv_G_WayService::importRecv_G_Way(const char* data, size_t size, string name, string realname, string orgcode, string companycode)
{
	if (data == nullptr || size == 0)
	{
		return -1;
	}
	// 页签名称（xlnx只能存储utf8，读取中文内容时需要转换）
	std::string sheetName = ZH_WORDS_GETTER("recv-g-way-file.excel.name");
	// 读取文件内容
	auto readData = ExcelComponent::readIntoVector(data, size, sheetName);
	if (readData.empty())
	{
		return -1;
	}

	list<Recv_G_WayDO> datas;
	int i = 1;
	int result = -1;
	for (auto row : readData)
	{
		// 第一行为表头，需要校验
		if (i == 1)
		{
			if (row.size() != 2 || row[0] != ZH_WORDS_GETTER("recv-g-way-file.excel.col.first") || row[1] != ZH_WORDS_GETTER("recv-g-way-file.excel.col.second"))
			{
				return -1;
			}
			result = 0;
			++i;
			continue;
		}
		// 跳过空行
		if (row.size() < 2 || row[0].empty() && row[1].empty())
		{
			continue;
		}
		Recv_G_WayDO temp;
		temp.setDel_mode_code(row[0]);
		temp.setDel_mode_name(row[1]);
		datas.push_back(temp);
	}

	if (datas.empty())
	{
		return result == 0 ? 0 : -1;
	}

	Recv_G_WayDAO dao;
	dao.insert(datas, name, realname, orgcode, companycode);
	return result;
}

std::vector<unsigned char> Recv_G_WayService::exportRecv_G_Way()
{
	Recv_G_WayDAO dao;
	list<Recv_G_WayDO> result = dao.selectAll();

	std::vector<std::vector<std::string>> data;
	// 写入表头
	std::vector<std::string> first;
	first.push_back(ZH_WORDS_GETTER("recv-g-way-file.excel.col.first"));
	first.push_back(ZH_WORDS_GETTER("recv-g-way-file.excel.col.second"));
	data.push_back(first);

	for (auto it = result.begin(); it != result.end(); ++it)
	{
		std::vector<std::string> row;
		row.push_back(it->getDel_mode_code());
		row.push_back(it->getDel_mode_name());
		data.push_back(row);
	}

	// 页签名称（xlnx只能存储utf8，读取中文内容时需要转换）
	std::string sheetName = ZH_WORDS_GETTER("recv-g-way-file.excel.name");
	// 将数据以excel格式写入buff中
	ExcelComponent excel;
	return excel.writeVectorToBuff(sheetName, data);
}
