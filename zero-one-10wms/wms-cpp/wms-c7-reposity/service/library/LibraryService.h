#pragma once
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
	// 修改数据
	bool updateData(const ModifyLibraryDTO::Wrapper& dto);
	// 通过ID删除数据
	bool removeData(string id);

	// 新增数据
	uint64_t addData(const LibraryDetailDTO::Wrapper& dto);
	// 分页查询库位类型列表
	LibraryPageDTO::Wrapper listQueryLibrary(const LibraryQuery::Wrapper& query);
	// 查询库位类型名称列表
	oatpp::List<LibraryNameDTO::Wrapper> listLibraryName();
};

#endif // !_LIBRARY_SERVICE_
