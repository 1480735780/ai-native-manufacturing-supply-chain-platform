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

#ifndef _COSTTEMPLATE_QUERY_
#define _COSTTEMPLATE_QUERY_

#include "../../GlobalInclude.h"
#include "domain/query/PageQuery.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * Query model of Cost Template
 */
class CostTemplateQuery : public PageQuery
{
	DTO_INIT(CostTemplateQuery, PageQuery);

	API_DTO_FIELD_DEFAULT(String, code, ZH_WORDS_GETTER("costtemplate.field.code"));
	API_DTO_FIELD_DEFAULT(String, cost_jg, ZH_WORDS_GETTER("costtemplate.field.cost_jg"));
	API_DTO_FIELD_DEFAULT(String, cost_sl, ZH_WORDS_GETTER("costtemplate.field.cost_sl"));
	API_DTO_FIELD_DEFAULT(String, cost_zk, ZH_WORDS_GETTER("costtemplate.field.cost_zk"));
	API_DTO_FIELD_DEFAULT(String, cost_bhs, ZH_WORDS_GETTER("costtemplate.field.cost_bhs"));
	API_DTO_FIELD_DEFAULT(String, cost_hs, ZH_WORDS_GETTER("costtemplate.field.cost_hs"));
	API_DTO_FIELD_DEFAULT(String, free_day, ZH_WORDS_GETTER("costtemplate.field.free_day"));
	API_DTO_FIELD_DEFAULT(String, free_day2, ZH_WORDS_GETTER("costtemplate.field.free_day2"));

	API_DTO_FIELD_DEFAULT(String, createName, ZH_WORDS_GETTER("costtemplate.field.create_name"));
	API_DTO_FIELD_DEFAULT(String, createBy, ZH_WORDS_GETTER("costtemplate.field.create_by"));
	API_DTO_FIELD_DEFAULT(String, updateName, ZH_WORDS_GETTER("costtemplate.field.update_name"));
	API_DTO_FIELD_DEFAULT(String, updateBy, ZH_WORDS_GETTER("costtemplate.field.update_by"));
	API_DTO_FIELD_DEFAULT(String, sysOrgCode, ZH_WORDS_GETTER("costtemplate.field.sys_org_code"));
	API_DTO_FIELD_DEFAULT(String, sysCompanyCode, ZH_WORDS_GETTER("costtemplate.field.sys_company_code"));
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_COSTTEMPLATE_QUERY_
