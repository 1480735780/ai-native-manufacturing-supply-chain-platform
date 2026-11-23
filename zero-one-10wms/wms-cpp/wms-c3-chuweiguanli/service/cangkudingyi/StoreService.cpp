#include "stdafx.h"
#include "StoreService.h"
#include "dao/cangkudingyi/StoreDAO.h"
#include "domain/GlobalInclude.h"

string getTimeStr() {
	auto now = std::chrono::system_clock::now();
	auto now_c = std::chrono::system_clock::to_time_t(now);
	std::stringstream ss;
	ss << std::put_time(std::localtime(&now_c), "%Y-%m-%d %H:%M:%S");
	return ss.str();
}

string StoreService::addStore(const StoreAddDTO::Wrapper dto, const PayloadDTO& payload)
{
	StoreDO data;
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto,
		StoreCode, store_code,
		StoreName, store_name,
		StoreText, store_text);
	data.setCreateName(payload.getRealname());
	data.setCreateBy(payload.getUsername());
	data.setSysOrgCode(payload.getOrgcode());
	data.setSysCompanyCode(payload.getCompanycode());
	data.setCreateDate(getTimeStr());
	StoreDAO dao;
	return dao.add(data);
}

string StoreService::modifyStore(const StoreModifyDTO::Wrapper dto, const PayloadDTO& payload)
{
	StoreDO data;
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto,
		Id, id,
		StoreCode, store_code,
		StoreName, store_name,
		StoreText, store_text);
	data.setUpdateName(payload.getRealname());
	data.setUpdateBy(payload.getUsername());
	data.setUpdateDate(getTimeStr());
	StoreDAO dao;
	return dao.modify(data);
}

CangkuListPageDTO::Wrapper StoreService::listAll(const CangkuListQuery::Wrapper& query)
{
	auto pages = CangkuListPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	StoreDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0)
	{
		return pages;
	}

	//分页查询数据
	pages->total = count;
	pages->calcPages();
	list<StoreDO> result = dao.selectWithPage(query);

	for (StoreDO data : result)
	{
		auto dto = CangkuListDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, data,
			id, Id,
			store_code, StoreCode,
			store_name, StoreName,
			store_text, StoreText);
		pages->addData(dto);
	}
	return pages;

}
// import warehouses from excel rows
// excel layout: header rows first, then data rows of [store_code, store_name, store_text]
int StoreService::importCangku(const std::vector<std::vector<std::string>>& data, const PayloadDTO& payload)
{
	int imported = 0;
	int row_index = 0;
	for (auto& row : data)
	{
		row_index++;
		// skip header lines: the exported file has 2 header rows (title + column names)
		if (row_index <= 2)
		{
			continue;
		}
		// skip empty or malformed rows
		if (row.size() < 2 || row[0].empty())
		{
			continue;
		}
		auto dto = StoreAddDTO::createShared();
		dto->store_code = row[0].c_str();
		dto->store_name = row[1].c_str();
		if (row.size() > 2)
		{
			dto->store_text = row[2].c_str();
		}
		string res = addStore(dto, payload);
		if (res != "failed" && !res.empty())
		{
			imported++;
		}
	}
	return imported;
}
