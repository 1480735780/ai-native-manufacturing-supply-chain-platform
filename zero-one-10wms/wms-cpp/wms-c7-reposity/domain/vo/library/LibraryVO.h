#pragma once
/*
 用于前端做显示
 @Author: nanbowan

*/
#ifndef _LIBRARY_VO_
#define _LIBRARY_VO_

#include "../../GlobalInclude.h"
#include "../../dto/library/LibraryDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 库位类型分页列表JsonVO，用于响应给客户端的Json对象
 * LibraryPageDTO: id + bin_type_code + bin_type_name
 */
class LibraryPageJsonVO : public JsonVO<LibraryPageDTO::Wrapper> {
	DTO_INIT(LibraryPageJsonVO, JsonVO<LibraryPageDTO::Wrapper>);
};

/**
 * 库位类型名称列表JsonVO，用于响应给客户端的Json对象
 * LibraryNameDTO: id + bin_type_code + bin_type_name
 */
class LibraryNameListJsonVO : public JsonVO<oatpp::List<LibraryNameDTO::Wrapper>> {
	DTO_INIT(LibraryNameListJsonVO, JsonVO<oatpp::List<LibraryNameDTO::Wrapper>>);
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_LIBRARY_VO_
