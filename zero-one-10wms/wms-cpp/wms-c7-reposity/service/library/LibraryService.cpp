/*
 @Author: nanbowan
*/
#include "stdafx.h"
#include "LibraryService.h"
#include "../../dao/library/LibraryDAO.h"

bool LibraryService::updateData(const ModifyLibraryDTO::Wrapper& dto)
{
	// 组装DO数据
	LibraryDO data;
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Id, id, Code, bin_type_code, Name, bin_type_name);
	// 执行数据修改
	LibraryDAO dao;
	return dao.update(data) == 1;
}

bool LibraryService::removeData(string id)
{
	LibraryDAO dao;
	return dao.deleteById(id) == 1;
}

uint64_t LibraryService::addData(const LibraryDetailDTO::Wrapper& dto)
{
	// 组装DO数据
	LibraryDO data;
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Id, id,
		CreateName, create_name, CreateBy, create_by, CreateDate, create_date,
		SysOrgCode, sys_org_code, SysCompanyCode, sys_company_code,
		Code, bin_type_code, Name, bin_type_name);
	// 执行数据插入
	LibraryDAO dao;
	return dao.insert(data);
}

LibraryPageDTO::Wrapper LibraryService::listQueryLibrary(const LibraryQuery::Wrapper& query)
{
	auto pages = LibraryPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	LibraryDAO dao;
	uint64_t count = dao.count(query);

	if (count <= 0)
	{
		return pages;
	}

	// 分页查询数据
	pages->total = count;
	pages->calcPages();

	list<LibraryDO> result = dao.selectWithPage(query);
	// 将DO转换成DTO
	for (const auto& sub : result)
	{
		auto dto = LibraryListDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, bin_type_code, Code, bin_type_name, Name);
		pages->addData(dto);
	}
	return pages;
}

oatpp::List<LibraryNameDTO::Wrapper> LibraryService::listLibraryName()
{
	LibraryDAO dao;
	list<LibraryNameDO> result = dao.selectLibraryNameList();

	auto namelist = oatpp::List<LibraryNameDTO::Wrapper>::createShared();
	for (const auto& sub : result)
	{
		auto dto = LibraryNameDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, bin_type_code, Code, bin_type_name, Name);
		namelist->push_back(dto);
	}
	return namelist;
}
