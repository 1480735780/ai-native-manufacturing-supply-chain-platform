#pragma once
/*
 @Author: nanbowan
*/
#ifndef _LIBRARY_QUERY_
#define _LIBRARY_QUERY_

#include "../../GlobalInclude.h"
#include "domain/query/PageQuery.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 库位类型分页查询对象
 */
class LibraryQuery : public PageQuery
{
	DTO_INIT(LibraryQuery, PageQuery);

	// 库位类型代码
	API_DTO_FIELD_DEFAULT(String, bin_type_code, ZH_WORDS_GETTER("dictionary.library.code.summary"));

	// 库位类型名称
	API_DTO_FIELD_DEFAULT(String, bin_type_name, ZH_WORDS_GETTER("dictionary.library.type.summary"));
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_LIBRARY_QUERY_
