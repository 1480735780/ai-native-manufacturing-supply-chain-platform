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

#ifndef _COSTTEMPLATE_DTO_
#define _COSTTEMPLATE_DTO_

#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * Business fields of Cost Template
 */
class CostTemplateBaseDTO : public oatpp::DTO
{
	DTO_INIT(CostTemplateBaseDTO, oatpp::DTO);

	API_DTO_FIELD(String, code, ZH_WORDS_GETTER("costtemplate.field.code"), true, "code");
	API_DTO_FIELD(String, cost_jg, ZH_WORDS_GETTER("costtemplate.field.cost_jg"), false, "cost_jg");
	API_DTO_FIELD(String, cost_sl, ZH_WORDS_GETTER("costtemplate.field.cost_sl"), false, "cost_sl");
	API_DTO_FIELD(String, cost_zk, ZH_WORDS_GETTER("costtemplate.field.cost_zk"), false, "cost_zk");
	API_DTO_FIELD(String, cost_bhs, ZH_WORDS_GETTER("costtemplate.field.cost_bhs"), false, "cost_bhs");
	API_DTO_FIELD(String, cost_hs, ZH_WORDS_GETTER("costtemplate.field.cost_hs"), false, "cost_hs");
	API_DTO_FIELD(String, free_day, ZH_WORDS_GETTER("costtemplate.field.free_day"), false, "free_day");
	API_DTO_FIELD(String, free_day2, ZH_WORDS_GETTER("costtemplate.field.free_day2"), false, "free_day2");
};

/**
 * Create body
 */
class CostTemplateBaseAddDTO : public CostTemplateBaseDTO
{
	DTO_INIT(CostTemplateBaseAddDTO, CostTemplateBaseDTO);
};

/**
 * Update body
 */
class CostTemplateBaseModifyDTO : public CostTemplateBaseDTO
{
	DTO_INIT(CostTemplateBaseModifyDTO, CostTemplateBaseDTO);
	API_DTO_FIELD(String, id, ZH_WORDS_GETTER("costtemplate.field.id"), true, "id");
};

/**
 * Full create DTO (business + audit)
 */
class CostTemplateAddDTO : public CostTemplateBaseDTO
{
	DTO_INIT(CostTemplateAddDTO, CostTemplateBaseDTO);
	API_DTO_FIELD_DEFAULT(String, create_name, ZH_WORDS_GETTER("costtemplate.field.create_name"));
	API_DTO_FIELD_DEFAULT(String, create_by, ZH_WORDS_GETTER("costtemplate.field.create_by"));
	API_DTO_FIELD_DEFAULT(String, create_date, ZH_WORDS_GETTER("costtemplate.field.create_date"));
	API_DTO_FIELD_DEFAULT(String, update_name, ZH_WORDS_GETTER("costtemplate.field.update_name"));
	API_DTO_FIELD_DEFAULT(String, update_by, ZH_WORDS_GETTER("costtemplate.field.update_by"));
	API_DTO_FIELD_DEFAULT(String, update_date, ZH_WORDS_GETTER("costtemplate.field.update_date"));
	API_DTO_FIELD_DEFAULT(String, sys_org_code, ZH_WORDS_GETTER("costtemplate.field.sys_org_code"));
	API_DTO_FIELD_DEFAULT(String, sys_company_code, ZH_WORDS_GETTER("costtemplate.field.sys_company_code"));
};

/**
 * Full modify DTO (business + audit + id)
 */
class CostTemplateModifyDTO : public CostTemplateAddDTO
{
	DTO_INIT(CostTemplateModifyDTO, CostTemplateAddDTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("costtemplate.field.id"));
};

/**
 * Row DTO returned to client
 */
class CostTemplateDTO : public CostTemplateModifyDTO
{
	DTO_INIT(CostTemplateDTO, CostTemplateModifyDTO);
};

/**
 * Name list item
 */
class CostTemplateNameListDTO : public oatpp::DTO
{
	DTO_INIT(CostTemplateNameListDTO, oatpp::DTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("costtemplate.field.id"));
	API_DTO_FIELD_DEFAULT(String, code, ZH_WORDS_GETTER("costtemplate.field.code"));
};

/**
 * Name list page
 */
class CostTemplateNameListPageDTO : public PageDTO<CostTemplateNameListDTO::Wrapper>
{
	DTO_INIT(CostTemplateNameListPageDTO, PageDTO<CostTemplateNameListDTO::Wrapper>);
};

/**
 * Row page
 */
class CostTemplatePageDTO : public PageDTO<CostTemplateDTO::Wrapper>
{
	DTO_INIT(CostTemplatePageDTO, PageDTO<CostTemplateDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_COSTTEMPLATE_DTO_
