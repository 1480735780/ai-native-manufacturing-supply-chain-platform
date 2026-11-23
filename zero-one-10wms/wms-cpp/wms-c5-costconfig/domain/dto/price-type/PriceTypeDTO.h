/*
 Copyright Zero One Star. All rights reserved.

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

#ifndef _PRICETYPE_DTO_
#define _PRICETYPE_DTO_

#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * Business fields of Price Type
 */
class PriceTypeBaseDTO : public oatpp::DTO
{
	DTO_INIT(PriceTypeBaseDTO, oatpp::DTO);

	API_DTO_FIELD(String, code, ZH_WORDS_GETTER("pricetype.field.code"), true, "code");
	API_DTO_FIELD(String, name, ZH_WORDS_GETTER("pricetype.field.name"), false, "name");
};

/**
 * Create body
 */
class PriceTypeBaseAddDTO : public PriceTypeBaseDTO
{
	DTO_INIT(PriceTypeBaseAddDTO, PriceTypeBaseDTO);
};

/**
 * Update body
 */
class PriceTypeBaseModifyDTO : public PriceTypeBaseDTO
{
	DTO_INIT(PriceTypeBaseModifyDTO, PriceTypeBaseDTO);
	API_DTO_FIELD(String, id, ZH_WORDS_GETTER("pricetype.field.id"), true, "id");
};

/**
 * Full create DTO (business + audit)
 */
class PriceTypeAddDTO : public PriceTypeBaseDTO
{
	DTO_INIT(PriceTypeAddDTO, PriceTypeBaseDTO);
	API_DTO_FIELD_DEFAULT(String, create_name, ZH_WORDS_GETTER("pricetype.field.create_name"));
	API_DTO_FIELD_DEFAULT(String, create_by, ZH_WORDS_GETTER("pricetype.field.create_by"));
	API_DTO_FIELD_DEFAULT(String, create_date, ZH_WORDS_GETTER("pricetype.field.create_date"));
	API_DTO_FIELD_DEFAULT(String, update_name, ZH_WORDS_GETTER("pricetype.field.update_name"));
	API_DTO_FIELD_DEFAULT(String, update_by, ZH_WORDS_GETTER("pricetype.field.update_by"));
	API_DTO_FIELD_DEFAULT(String, update_date, ZH_WORDS_GETTER("pricetype.field.update_date"));
	API_DTO_FIELD_DEFAULT(String, sys_org_code, ZH_WORDS_GETTER("pricetype.field.sys_org_code"));
	API_DTO_FIELD_DEFAULT(String, sys_company_code, ZH_WORDS_GETTER("pricetype.field.sys_company_code"));
};

/**
 * Full modify DTO (business + audit + id)
 */
class PriceTypeModifyDTO : public PriceTypeAddDTO
{
	DTO_INIT(PriceTypeModifyDTO, PriceTypeAddDTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("pricetype.field.id"));
};

/**
 * Row DTO returned to client
 */
class PriceTypeDTO : public PriceTypeModifyDTO
{
	DTO_INIT(PriceTypeDTO, PriceTypeModifyDTO);
};

/**
 * Name list item
 */
class PriceTypeNameListDTO : public oatpp::DTO
{
	DTO_INIT(PriceTypeNameListDTO, oatpp::DTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("pricetype.field.id"));
	API_DTO_FIELD_DEFAULT(String, name, ZH_WORDS_GETTER("pricetype.field.name"));
};

/**
 * Name list page
 */
class PriceTypeNameListPageDTO : public PageDTO<PriceTypeNameListDTO::Wrapper>
{
	DTO_INIT(PriceTypeNameListPageDTO, PageDTO<PriceTypeNameListDTO::Wrapper>);
};

/**
 * Row page
 */
class PriceTypePageDTO : public PageDTO<PriceTypeDTO::Wrapper>
{
	DTO_INIT(PriceTypePageDTO, PageDTO<PriceTypeDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_PRICETYPE_DTO_
