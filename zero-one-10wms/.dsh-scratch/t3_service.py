# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

# ---------- LibraryService.h ----------
p = "wms-cpp/wms-c7-reposity/service/library/LibraryService.h"
enc = detect(open(p, 'rb').read())
new_h = '''#pragma once
/*
 @Author: nanbowan
*/
#ifndef _LIBRARY_SERVICE_
#define _LIBRARY_SERVICE_
#include <list>
#include "domain/dto/library/LibraryDTO.h"
#include "domain/vo/library/LibraryVO.h"
#include "domain/query/library/LibraryQuery.h"

/**
 * 库位类型服务实现
 */
class LibraryService
{
public:
\t// 修改数据
\tbool updateData(const ModifyLibraryDTO::Wrapper& dto);
\t// 通过ID删除数据
\tbool removeData(string id);

\t// 新增数据
\tuint64_t addData(const LibraryDetailDTO::Wrapper& dto);
\t// 分页查询库位类型列表
\tLibraryPageDTO::Wrapper listQueryLibrary(const LibraryQuery::Wrapper& query);
\t// 查询库位类型名称列表
\toatpp::List<LibraryNameDTO::Wrapper> listLibraryName();
};

#endif // !_LIBRARY_SERVICE_
'''
open(p, 'wb').write(new_h.encode(enc))
print("LibraryService.h ->", enc)

# ---------- LibraryService.cpp ----------
p = "wms-cpp/wms-c7-reposity/service/library/LibraryService.cpp"
enc = detect(open(p, 'rb').read())
new_cpp = '''/*
 @Author: nanbowan
*/
#include "stdafx.h"
#include "LibraryService.h"
#include "../../dao/library/LibraryDAO.h"

bool LibraryService::updateData(const ModifyLibraryDTO::Wrapper& dto)
{
\t// 组装DO数据
\tLibraryDO data;
\tZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Id, id, Code, bin_type_code, Name, bin_type_name);
\t// 执行数据修改
\tLibraryDAO dao;
\treturn dao.update(data) == 1;
}

bool LibraryService::removeData(string id)
{
\tLibraryDAO dao;
\treturn dao.deleteById(id) == 1;
}

uint64_t LibraryService::addData(const LibraryDetailDTO::Wrapper& dto)
{
\t// 组装DO数据
\tLibraryDO data;
\tZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Id, id,
\t\tCreateName, create_name, CreateBy, create_by, CreateDate, create_date,
\t\tUpdateName, update_name, UpdateBy, update_by, UpdateDate, update_date,
\t\tSysOrgCode, sys_org_code, SysCompanyCode, sys_company_code,
\t\tCode, bin_type_code, Name, bin_type_name);
\t// 执行数据插入
\tLibraryDAO dao;
\treturn dao.insert(data);
}

LibraryPageDTO::Wrapper LibraryService::listQueryLibrary(const LibraryQuery::Wrapper& query)
{
\tauto pages = LibraryPageDTO::createShared();
\tpages->pageIndex = query->pageIndex;
\tpages->pageSize = query->pageSize;

\tLibraryDAO dao;
\tuint64_t count = dao.count(query);

\tif (count <= 0)
\t{
\t\treturn pages;
\t}

\t// 分页查询数据
\tpages->total = count;
\tpages->calcPages();

\tlist<LibraryDO> result = dao.selectWithPage(query);
\t// 将DO转换成DTO
\tfor (const auto& sub : result)
\t{
\t\tauto dto = LibraryListDTO::createShared();
\t\tZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, bin_type_code, Code, bin_type_name, Name);
\t\tpages->addData(dto);
\t}
\treturn pages;
}

oatpp::List<LibraryNameDTO::Wrapper> LibraryService::listLibraryName()
{
\tLibraryDAO dao;
\tlist<LibraryNameDO> result = dao.selectLibraryNameList();

\tauto namelist = oatpp::List<LibraryNameDTO::Wrapper>::createShared();
\tfor (const auto& sub : result)
\t{
\t\tauto dto = LibraryNameDTO::createShared();
\t\tZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, bin_type_code, Code, bin_type_name, Name);
\t\tnamelist->push_back(dto);
\t}
\treturn namelist;
}
'''
open(p, 'wb').write(new_cpp.encode(enc))
print("LibraryService.cpp ->", enc)
