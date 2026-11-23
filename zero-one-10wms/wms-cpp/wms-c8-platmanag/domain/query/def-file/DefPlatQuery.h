#pragma once
/*
 Copyright Zero One Star. All rights reserved.

 @Author: mao
 @Date: 2025/2/28 08:59:29

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

	  https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*/
#ifndef _DEFPLAT_QUERY_
#define _DEFPLAT_QUERY_

#include "../../GlobalInclude.h"
#include "domain/query/PageQuery.h"

#include OATPP_CODEGEN_BEGIN(DTO)
// 月台分页查询参数
class DefPlatQuery : public PageQuery
{
	DTO_INIT(DefPlatQuery, PageQuery);

	// 月台代码（精确）
	API_DTO_FIELD_DEFAULT(String, platform_code, ZH_WORDS_GETTER("def.query.code"));
	// 月台名称（模糊）
	API_DTO_FIELD_DEFAULT(String, platform_name, ZH_WORDS_GETTER("def.query.name"));
};

// 锟斤拷锟斤拷删锟斤拷锟斤拷锟斤拷锟绞絛to
class BatchDeleteRequestDto : public oatpp::DTO {
	DTO_INIT(BatchDeleteRequestDto, DTO);
	// id锟叫憋拷
	API_DTO_FIELD_DEFAULT(List<oatpp::UInt64>, ids, ZH_WORDS_GETTER("lad.field.ids"));
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_DEFPLAT_QUERY_