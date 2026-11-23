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

#ifndef _MEASUREMENTTYPE_DTO_
#define _MEASUREMENTTYPE_DTO_

#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * Business fields of Measurement Type
 */
class MeasurementTypeBaseDTO : public oatpp::DTO
{
	DTO_INIT(MeasurementTypeBaseDTO, oatpp::DTO);

	API_DTO_FIELD(String, code, ZH_WORDS_GETTER("measuretype.field.code"), true, "code");
	API_DTO_FIELD(String, name, ZH_WORDS_GETTER("measuretype.field.name"), false, "name");
};

/**
 * Create body
 */
class MeasurementTypeBaseAddDTO : public MeasurementTypeBaseDTO
{
	DTO_INIT(MeasurementTypeBaseAddDTO, MeasurementTypeBaseDTO);
};

/**
 * Update body
 */
class MeasurementTypeBaseModifyDTO : public MeasurementTypeBaseDTO
{
	DTO_INIT(MeasurementTypeBaseModifyDTO, MeasurementTypeBaseDTO);
	API_DTO_FIELD(String, id, ZH_WORDS_GETTER("measuretype.field.id"), true, "id");
};

/**
 * Full create DTO (business + audit)
 */
class MeasurementTypeAddDTO : public MeasurementTypeBaseDTO
{
	DTO_INIT(MeasurementTypeAddDTO, MeasurementTypeBaseDTO);
	API_DTO_FIELD_DEFAULT(String, create_name, ZH_WORDS_GETTER("measuretype.field.create_name"));
	API_DTO_FIELD_DEFAULT(String, create_by, ZH_WORDS_GETTER("measuretype.field.create_by"));
	API_DTO_FIELD_DEFAULT(String, create_date, ZH_WORDS_GETTER("measuretype.field.create_date"));
	API_DTO_FIELD_DEFAULT(String, update_name, ZH_WORDS_GETTER("measuretype.field.update_name"));
	API_DTO_FIELD_DEFAULT(String, update_by, ZH_WORDS_GETTER("measuretype.field.update_by"));
	API_DTO_FIELD_DEFAULT(String, update_date, ZH_WORDS_GETTER("measuretype.field.update_date"));
	API_DTO_FIELD_DEFAULT(String, sys_org_code, ZH_WORDS_GETTER("measuretype.field.sys_org_code"));
	API_DTO_FIELD_DEFAULT(String, sys_company_code, ZH_WORDS_GETTER("measuretype.field.sys_company_code"));
};

/**
 * Full modify DTO (business + audit + id)
 */
class MeasurementTypeModifyDTO : public MeasurementTypeAddDTO
{
	DTO_INIT(MeasurementTypeModifyDTO, MeasurementTypeAddDTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("measuretype.field.id"));
};

/**
 * Row DTO returned to client
 */
class MeasurementTypeDTO : public MeasurementTypeModifyDTO
{
	DTO_INIT(MeasurementTypeDTO, MeasurementTypeModifyDTO);
};

/**
 * Name list item
 */
class MeasurementTypeNameListDTO : public oatpp::DTO
{
	DTO_INIT(MeasurementTypeNameListDTO, oatpp::DTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("measuretype.field.id"));
	API_DTO_FIELD_DEFAULT(String, name, ZH_WORDS_GETTER("measuretype.field.name"));
};

/**
 * Name list page
 */
class MeasurementTypeNameListPageDTO : public PageDTO<MeasurementTypeNameListDTO::Wrapper>
{
	DTO_INIT(MeasurementTypeNameListPageDTO, PageDTO<MeasurementTypeNameListDTO::Wrapper>);
};

/**
 * Row page
 */
class MeasurementTypePageDTO : public PageDTO<MeasurementTypeDTO::Wrapper>
{
	DTO_INIT(MeasurementTypePageDTO, PageDTO<MeasurementTypeDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_MEASUREMENTTYPE_DTO_
