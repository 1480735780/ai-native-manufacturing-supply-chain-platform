#include "stdafx.h"
#include "MeasurementTypeService.h"
#include "../../domain/do/measurement-type/MeasurementTypeDO.h"
#include "../../dao/measurement-type/MeasurementTypeDAO.h"
#include "SimpleDateTimeFormat.h"

// create one row
string MeasurementTypeService::insert(const MeasurementTypeAddDTO::Wrapper& dto)
{
	MeasurementTypeDO data;
	string now = SimpleDateTimeFormat::format();
	dto->update_date = now;
	dto->create_date = now;

	ZO_STAR_DOMAIN_DTO_TO_DO(
		data, dto,
		PronutTypeCode, code,
		PronutTypeName, name,
		CreateName, create_name,
		CreateBy, create_by,
		CreateDate, create_date,
		UpdateName, update_name,
		UpdateBy, update_by,
		UpdateDate, update_date,
		SysOrgCode, sys_org_code,
		SysCompanyCode, sys_company_code
		);

	MeasurementTypeDAO dao;
	return dao.insert(data);
}

// update one row
bool MeasurementTypeService::update(const MeasurementTypeModifyDTO::Wrapper& dto)
{
	MeasurementTypeDO data;
	string now = SimpleDateTimeFormat::format();
	dto->update_date = now;

	ZO_STAR_DOMAIN_DTO_TO_DO(
		data, dto,
		PronutTypeCode, code,
		PronutTypeName, name,
		Id, id,
		UpdateName, update_name,
		UpdateBy, update_by,
		UpdateDate, update_date,
		SysOrgCode, sys_org_code,
		SysCompanyCode, sys_company_code
		);

	MeasurementTypeDAO dao;
	return dao.update(data);
}

// name list
MeasurementTypeNameListPageDTO::Wrapper MeasurementTypeService::listName(const MeasurementTypeQuery::Wrapper& query)
{
	auto pages = MeasurementTypeNameListPageDTO::createShared();
	MeasurementTypeDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;
	list<MeasurementTypeDO> result = dao.selectName(query);
	for (MeasurementTypeDO sub : result)
	{
		auto dto = MeasurementTypeNameListDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, name, PronutTypeName);
		pages->addData(dto);
	}
	return pages;
}

// row list with paging
MeasurementTypePageDTO::Wrapper MeasurementTypeService::listAll(const MeasurementTypeQuery::Wrapper& query)
{
	auto pages = MeasurementTypePageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	MeasurementTypeDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;

	pages->total = count;
	pages->calcPages();
	list<MeasurementTypeDO> result = dao.selectAllWithPage(query);
	for (MeasurementTypeDO sub : result)
	{
		auto dto = MeasurementTypeDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub,
			code, PronutTypeCode,
			name, PronutTypeName,
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
int MeasurementTypeService::removeByIds(const std::vector<std::string>& ids)
{
	MeasurementTypeDAO dao;
	return dao.deleteByIds(ids);
}

// rows for export
std::list<MeasurementTypeDO> MeasurementTypeService::listForExport()
{
	MeasurementTypeDAO dao;
	return dao.selectForExport();
}

// single row detail
std::list<MeasurementTypeDO> MeasurementTypeService::getById(const std::string& id)
{
	MeasurementTypeDAO dao;
	return dao.selectById(id);
}

// import rows
int MeasurementTypeService::importRows(const std::vector<std::vector<std::string>>& rows,
	const std::string& createBy, const std::string& orgCode, const std::string& companyCode)
{
	int ok = 0;
	string now = SimpleDateTimeFormat::format();
	MeasurementTypeDAO dao;
	for (const auto& row : rows)
	{
		if (row.size() < 2) continue;
		if (row[0].empty()) continue;
		MeasurementTypeDO data;
		data.setPronutTypeCode(row[0]);
		data.setPronutTypeName(row[1]);
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
