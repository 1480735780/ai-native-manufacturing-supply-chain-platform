/*
 Copyright Zero One Star. All rights reserved.

 @Author: zero-one-star
 @Date: 2025/03/10 16:09:12

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
#ifndef _OPERATION_TYPE_DTO_
#define _OPERATION_TYPE_DTO_

#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 操作类型新增数据对象（不提供唯一标识，由后端生成）
 */
class OperationTypeAddDTO : public oatpp::DTO
{
	DTO_INIT(OperationTypeAddDTO, oatpp::DTO);
	// 操作类型代码
	API_DTO_FIELD_DEFAULT(String, code, ZH_WORDS_GETTER("op.field.code"));
	// 操作类型名称
	API_DTO_FIELD_DEFAULT(String, name, ZH_WORDS_GETTER("op.field.name"));
};

/**
 * 操作类型数据对象（修改时需要唯一标识）
 */
class OperationTypeDTO : public OperationTypeAddDTO
{
	DTO_INIT(OperationTypeDTO, OperationTypeAddDTO);
	// 唯一标识
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("op.field.id"));
};

/**
 * 操作类型分页数据对象
 */
class OperationTypePageDTO : public PageDTO<OperationTypeDTO::Wrapper>
{
	DTO_INIT(OperationTypePageDTO, PageDTO<OperationTypeDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_OPERATION_TYPE_DTO_
