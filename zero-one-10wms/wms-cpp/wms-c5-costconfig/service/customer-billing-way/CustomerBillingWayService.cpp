#include "stdafx.h"
#include "CustomerBillingWayService.h"
#include "../../domain/do/customer-billing-way/CustomerBillingWayDO.h"
#include "../../dao/customer-billing-way/CustomerBillingWayDAO.h"
#include "SimpleDateTimeFormat.h"

// create one row
string CustomerBillingWayService::insert(const CustomerBillingWayAddDTO::Wrapper& dto)
{
	CustomerBillingWayDO data;
	string now = SimpleDateTimeFormat::format();
	dto->update_date = now;
	dto->create_date = now;

	ZO_STAR_DOMAIN_DTO_TO_DO(
		data, dto,
		KehuzhuangtaiCode, code,
		KehuzhuangtaiName, name,
		CusStaDel, cus_sta_del,
		CreateName, create_name,
		CreateBy, create_by,
		CreateDate, create_date,
		UpdateName, update_name,
		UpdateBy, update_by,
		UpdateDate, update_date,
		SysOrgCode, sys_org_code,
		SysCompanyCode, sys_company_code
		);

	CustomerBillingWayDAO dao;
	return dao.insert(data);
}

// update one row
bool CustomerBillingWayService::update(const CustomerBillingWayModifyDTO::Wrapper& dto)
{
	CustomerBillingWayDO data;
	string now = SimpleDateTimeFormat::format();
	dto->update_date = now;

	ZO_STAR_DOMAIN_DTO_TO_DO(
		data, dto,
		KehuzhuangtaiCode, code,
		KehuzhuangtaiName, name,
		CusStaDel, cus_sta_del,
		Id, id,
		UpdateName, update_name,
		UpdateBy, update_by,
		UpdateDate, update_date,
		SysOrgCode, sys_org_code,
		SysCompanyCode, sys_company_code
		);

	CustomerBillingWayDAO dao;
	return dao.update(data);
}

// name list
CustomerBillingWayNameListPageDTO::Wrapper CustomerBillingWayService::listName(const CustomerBillingWayQuery::Wrapper& query)
{
	auto pages = CustomerBillingWayNameListPageDTO::createShared();
	CustomerBillingWayDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;
	list<CustomerBillingWayDO> result = dao.selectName(query);
	for (CustomerBillingWayDO sub : result)
	{
		auto dto = CustomerBillingWayNameListDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, name, KehuzhuangtaiName);
		pages->addData(dto);
	}
	return pages;
}

// row list with paging
CustomerBillingWayPageDTO::Wrapper CustomerBillingWayService::listAll(const CustomerBillingWayQuery::Wrapper& query)
{
	auto pages = CustomerBillingWayPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	CustomerBillingWayDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0) return pages;

	pages->total = count;
	pages->calcPages();
	list<CustomerBillingWayDO> result = dao.selectAllWithPage(query);
	for (CustomerBillingWayDO sub : result)
	{
		auto dto = CustomerBillingWayDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub,
			code, KehuzhuangtaiCode,
			name, KehuzhuangtaiName,
			cus_sta_del, CusStaDel,
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
int CustomerBillingWayService::removeByIds(const std::vector<std::string>& ids)
{
	CustomerBillingWayDAO dao;
	return dao.deleteByIds(ids);
}

// rows for export
std::list<CustomerBillingWayDO> CustomerBillingWayService::listForExport()
{
	CustomerBillingWayDAO dao;
	return dao.selectForExport();
}

// single row detail
std::list<CustomerBillingWayDO> CustomerBillingWayService::getById(const std::string& id)
{
	CustomerBillingWayDAO dao;
	return dao.selectById(id);
}

// import rows
int CustomerBillingWayService::importRows(const std::vector<std::vector<std::string>>& rows,
	const std::string& createBy, const std::string& orgCode, const std::string& companyCode)
{
	int ok = 0;
	string now = SimpleDateTimeFormat::format();
	CustomerBillingWayDAO dao;
	for (const auto& row : rows)
	{
		if (row.size() < 3) continue;
		if (row[0].empty()) continue;
		CustomerBillingWayDO data;
		data.setKehuzhuangtaiCode(row[0]);
		data.setKehuzhuangtaiName(row[1]);
		data.setCusStaDel(row[2]);
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
