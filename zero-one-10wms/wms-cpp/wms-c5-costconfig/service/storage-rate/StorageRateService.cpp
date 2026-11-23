#include "stdafx.h"
#include "StorageRateService.h"
#include "../../domain/do/storage-rate/StorageRateDO.h"
#include "../../dao/storage-rate/StorageRateDAO.h"
#include "SimpleDateTimeFormat.h"

// create one row
string StorageRateService::insert(const StorageRateAddDTO::Wrapper& dto)
{
	StorageRateDO data;
	string now = SimpleDateTimeFormat::format();
	dto->update_date = now;
	dto->create_date = now;

	ZO_STAR_DOMAIN_DTO_TO_DO(
		data, dto,
		CostCode, code,
		CostYj, cost_yj,
		CostZk, cost_zk,
		CostSl, cost_sl,
		CostBhs, cost_bhs,
		CostHsj, cost_hsj,
		CreateName, create_name,
		CreateBy, create_by,
		CreateDate, create_date,
		UpdateName, update_name,
		UpdateBy, update_by,
		UpdateDate, update_date,
		SysOrgCode, sys_org_code,
		SysCompanyCode, sys_company_code
		);

	StorageRateDAO dao;
	return dao.insert(data);
}

// update one row
bool StorageRateService::update(const StorageRateModifyDTO::Wrapper& dto)
{
	StorageRateDO data;
	string now = SimpleDateTimeFormat::format();
	dto->update_date = now;

	ZO_STAR_DOMAIN_DTO_TO_DO(
		data, dto,
		CostCode, code,
		CostYj, cost_yj,
		CostZk, cost_zk,
		CostSl, cost_sl,
		CostBhs, cost_bhs,
		CostHsj, cost_hsj,
		Id, id,
		UpdateName, update_name,
		UpdateBy, update_by,
		UpdateDate, update_date,
		SysOrgCode, sys_org_code,
		SysCompanyCode, sys_company_code
		);

	StorageRateDAO dao;
	return dao.update(data);
}

// name list
StorageRateNameListPageDTO::Wrapper StorageRateService::listName(const StorageRateQuery::Wrapper& query)
{
	auto pages = StorageRateNameListPageDTO::createShared();
	StorageRateDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;
	list<StorageRateDO> result = dao.selectName(query);
	for (StorageRateDO sub : result)
	{
		auto dto = StorageRateNameListDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, code, CostCode);
		pages->addData(dto);
	}
	return pages;
}

// row list with paging
StorageRatePageDTO::Wrapper StorageRateService::listAll(const StorageRateQuery::Wrapper& query)
{
	auto pages = StorageRatePageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	StorageRateDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;

	pages->total = count;
	pages->calcPages();
	list<StorageRateDO> result = dao.selectAllWithPage(query);
	for (StorageRateDO sub : result)
	{
		auto dto = StorageRateDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub,
			code, CostCode,
			cost_yj, CostYj,
			cost_zk, CostZk,
			cost_sl, CostSl,
			cost_bhs, CostBhs,
			cost_hsj, CostHsj,
			create_name, CreateName,
			create_by, CreateBy,
			create_date, CreateDate,
			update_name, UpdateName,
			update_by, UpdateBy,
			update_date, UpdateDate,
			sys_org_code, SysOrgCode,
			sys_company_code, SysCompanyCode,
			id, Id
		);
		pages->addData(dto);
	}
	return pages;
}

// batch delete
int StorageRateService::removeByIds(const std::vector<std::string>& ids)
{
	StorageRateDAO dao;
	return dao.deleteByIds(ids);
}

// rows for export
std::list<StorageRateDO> StorageRateService::listForExport()
{
	StorageRateDAO dao;
	return dao.selectForExport();
}

// single row detail
std::list<StorageRateDO> StorageRateService::getById(const std::string& id)
{
	StorageRateDAO dao;
	return dao.selectById(id);
}

// import rows
int StorageRateService::importRows(const std::vector<std::vector<std::string>>& rows,
	const std::string& createBy, const std::string& orgCode, const std::string& companyCode)
{
	int ok = 0;
	string now = SimpleDateTimeFormat::format();
	StorageRateDAO dao;
	for (const auto& row : rows)
	{
		if (row.size() < 6) continue;
		if (row[0].empty()) continue;
		StorageRateDO data;
		data.setCostCode(row[0]);
		data.setCostYj(row[1]);
		data.setCostZk(row[2]);
		data.setCostSl(row[3]);
		data.setCostBhs(row[4]);
		data.setCostHsj(row[5]);
		data.setCreateName(createBy);
		data.setCreateBy(createBy);
		data.setCreateDate(now);
		data.setUpdateName(createBy);
		data.setUpdateBy(createBy);
		data.setUpdateDate(now);
		data.setSysOrgCode(orgCode);
		data.setSysCompanyCode(companyCode);
		if (!dao.insert(data).empty()) ok++;
	}
	return ok;
}
