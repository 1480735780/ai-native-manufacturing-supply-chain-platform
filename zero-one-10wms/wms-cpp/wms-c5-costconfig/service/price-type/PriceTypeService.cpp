#include "stdafx.h"
#include "PriceTypeService.h"
#include "../../domain/do/price-type/PriceTypeDO.h"
#include "../../dao/price-type/PriceTypeDAO.h"
#include "SimpleDateTimeFormat.h"

// create one row
string PriceTypeService::insert(const PriceTypeAddDTO::Wrapper& dto)
{
	PriceTypeDO data;
	string now = SimpleDateTimeFormat::format();
	dto->update_date = now;
	dto->create_date = now;

	ZO_STAR_DOMAIN_DTO_TO_DO(
		data, dto,
		PriceTypeCode, code,
		PriceTypeName, name,
		CreateName, create_name,
		CreateBy, create_by,
		CreateDate, create_date,
		UpdateName, update_name,
		UpdateBy, update_by,
		UpdateDate, update_date,
		SysOrgCode, sys_org_code,
		SysCompanyCode, sys_company_code
		);

	PriceTypeDAO dao;
	return dao.insert(data);
}

// update one row
bool PriceTypeService::update(const PriceTypeModifyDTO::Wrapper& dto)
{
	PriceTypeDO data;
	string now = SimpleDateTimeFormat::format();
	dto->update_date = now;

	ZO_STAR_DOMAIN_DTO_TO_DO(
		data, dto,
		PriceTypeCode, code,
		PriceTypeName, name,
		Id, id,
		UpdateName, update_name,
		UpdateBy, update_by,
		UpdateDate, update_date,
		SysOrgCode, sys_org_code,
		SysCompanyCode, sys_company_code
		);

	PriceTypeDAO dao;
	return dao.update(data);
}

// name list
PriceTypeNameListPageDTO::Wrapper PriceTypeService::listName(const PriceTypeQuery::Wrapper& query)
{
	auto pages = PriceTypeNameListPageDTO::createShared();
	PriceTypeDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;
	list<PriceTypeDO> result = dao.selectName(query);
	for (PriceTypeDO sub : result)
	{
		auto dto = PriceTypeNameListDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, name, PriceTypeName);
		pages->addData(dto);
	}
	return pages;
}

// row list with paging
PriceTypePageDTO::Wrapper PriceTypeService::listAll(const PriceTypeQuery::Wrapper& query)
{
	auto pages = PriceTypePageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	PriceTypeDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;

	pages->total = count;
	pages->calcPages();
	list<PriceTypeDO> result = dao.selectAllWithPage(query);
	for (PriceTypeDO sub : result)
	{
		auto dto = PriceTypeDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub,
			code, PriceTypeCode,
			name, PriceTypeName,
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
int PriceTypeService::removeByIds(const std::vector<std::string>& ids)
{
	PriceTypeDAO dao;
	return dao.deleteByIds(ids);
}

// rows for export
std::list<PriceTypeDO> PriceTypeService::listForExport()
{
	PriceTypeDAO dao;
	return dao.selectForExport();
}

// single row detail
std::list<PriceTypeDO> PriceTypeService::getById(const std::string& id)
{
	PriceTypeDAO dao;
	return dao.selectById(id);
}

// import rows
int PriceTypeService::importRows(const std::vector<std::vector<std::string>>& rows,
	const std::string& createBy, const std::string& orgCode, const std::string& companyCode)
{
	int ok = 0;
	string now = SimpleDateTimeFormat::format();
	PriceTypeDAO dao;
	for (const auto& row : rows)
	{
		if (row.size() < 2) continue;
		if (row[0].empty()) continue;
		PriceTypeDO data;
		data.setPriceTypeCode(row[0]);
		data.setPriceTypeName(row[1]);
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
