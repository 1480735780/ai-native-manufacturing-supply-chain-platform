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

#ifndef _MEASUREMENTTYPE_QUERY_
#define _MEASUREMENTTYPE_QUERY_

#include "../../GlobalInclude.h"
#include "domain/query/PageQuery.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * Query model of Measurement Type
 */
class MeasurementTypeQuery : public PageQuery
{
	DTO_INIT(MeasurementTypeQuery, PageQuery);

	API_DTO_FIELD_DEFAULT(String, code, ZH_WORDS_GETTER("measuretype.field.code"));
	API_DTO_FIELD_DEFAULT(String, name, ZH_WORDS_GETTER("measuretype.field.name"));

	API_DTO_FIELD_DEFAULT(String, createName, ZH_WORDS_GETTER("measuretype.field.create_name"));
	API_DTO_FIELD_DEFAULT(String, createBy, ZH_WORDS_GETTER("measuretype.field.create_by"));
	API_DTO_FIELD_DEFAULT(String, updateName, ZH_WORDS_GETTER("measuretype.field.update_name"));
	API_DTO_FIELD_DEFAULT(String, updateBy, ZH_WORDS_GETTER("measuretype.field.update_by"));
	API_DTO_FIELD_DEFAULT(String, sysOrgCode, ZH_WORDS_GETTER("measuretype.field.sys_org_code"));
	API_DTO_FIELD_DEFAULT(String, sysCompanyCode, ZH_WORDS_GETTER("measuretype.field.sys_company_code"));
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_MEASUREMENTTYPE_QUERY_
