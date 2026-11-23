#include "stdafx.h"
#include "CostTemplateService.h"
#include "../../domain/do/cost-template/CostTemplateDO.h"
#include "../../dao/cost-template/CostTemplateDAO.h"
#include "SimpleDateTimeFormat.h"

// create one row
string CostTemplateService::insert(const CostTemplateAddDTO::Wrapper& dto)
{
	CostTemplateDO data;
	string now = SimpleDateTimeFormat::format();
	dto->update_date = now;
	dto->create_date = now;

	ZO_STAR_DOMAIN_DTO_TO_DO(
		data, dto,
		CostCode, code,
		CostJg, cost_jg,
		CostSl, cost_sl,
		CostZk, cost_zk,
		CostBhs, cost_bhs,
		CostHs, cost_hs,
		FreeDay, free_day,
		FreeDay2, free_day2,
		CreateName, create_name,
		CreateBy, create_by,
		CreateDate, create_date,
		UpdateName, update_name,
		UpdateBy, update_by,
		UpdateDate, update_date,
		SysOrgCode, sys_org_code,
		SysCompanyCode, sys_company_code
		);

	CostTemplateDAO dao;
	return dao.insert(data);
}

// update one row
bool CostTemplateService::update(const CostTemplateModifyDTO::Wrapper& dto)
{
	CostTemplateDO data;
	string now = SimpleDateTimeFormat::format();
	dto->update_date = now;

	ZO_STAR_DOMAIN_DTO_TO_DO(
		data, dto,
		CostCode, code,
		CostJg, cost_jg,
		CostSl, cost_sl,
		CostZk, cost_zk,
		CostBhs, cost_bhs,
		CostHs, cost_hs,
		FreeDay, free_day,
		FreeDay2, free_day2,
		Id, id,
		UpdateName, update_name,
		UpdateBy, update_by,
		UpdateDate, update_date,
		SysOrgCode, sys_org_code,
		SysCompanyCode, sys_company_code
		);

	CostTemplateDAO dao;
	return dao.update(data);
}

// name list
CostTemplateNameListPageDTO::Wrapper CostTemplateService::listName(const CostTemplateQuery::Wrapper& query)
{
	auto pages = CostTemplateNameListPageDTO::createShared();
	CostTemplateDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;
	list<CostTemplateDO> result = dao.selectName(query);
	for (CostTemplateDO sub : result)
	{
		auto dto = CostTemplateNameListDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, code, CostCode);
		pages->addData(dto);
	}
	return pages;
}

// row list with paging
CostTemplatePageDTO::Wrapper CostTemplateService::listAll(const CostTemplateQuery::Wrapper& query)
{
	auto pages = CostTemplatePageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	CostTemplateDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;

	pages->total = count;
	pages->calcPages();
	list<CostTemplateDO> result = dao.selectAllWithPage(query);
	for (CostTemplateDO sub : result)
	{
		auto dto = CostTemplateDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub,
			code, CostCode,
			cost_jg, CostJg,
			cost_sl, CostSl,
			cost_zk, CostZk,
			cost_bhs, CostBhs,
			cost_hs, CostHs,
			free_day, FreeDay,
			free_day2, FreeDay2,
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
int CostTemplateService::removeByIds(const std::vector<std::string>& ids)
{
	CostTemplateDAO dao;
	return dao.deleteByIds(ids);
}

// rows for export
std::list<CostTemplateDO> CostTemplateService::listForExport()
{
	CostTemplateDAO dao;
	return dao.selectForExport();
}

// single row detail
std::list<CostTemplateDO> CostTemplateService::getById(const std::string& id)
{
	CostTemplateDAO dao;
	return dao.selectById(id);
}

// import rows
int CostTemplateService::importRows(const std::vector<std::vector<std::string>>& rows,
	const std::string& createBy, const std::string& orgCode, const std::string& companyCode)
{
	int ok = 0;
	string now = SimpleDateTimeFormat::format();
	CostTemplateDAO dao;
	for (const auto& row : rows)
	{
		if (row.size() < 8) continue;
		if (row[0].empty()) continue;
		CostTemplateDO data;
		data.setCostCode(row[0]);
		data.setCostJg(row[1]);
		data.setCostSl(row[2]);
		data.setCostZk(row[3]);
		data.setCostBhs(row[4]);
		data.setCostHs(row[5]);
		data.setFreeDay(row[6]);
		data.setFreeDay2(row[7]);
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
