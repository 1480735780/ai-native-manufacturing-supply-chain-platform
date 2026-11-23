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

#ifndef _STORAGERATE_DTO_
#define _STORAGERATE_DTO_

#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * Business fields of Storage Rate
 */
class StorageRateBaseDTO : public oatpp::DTO
{
	DTO_INIT(StorageRateBaseDTO, oatpp::DTO);

	API_DTO_FIELD(String, code, ZH_WORDS_GETTER("storagerate.field.code"), true, "code");
	API_DTO_FIELD(String, cost_yj, ZH_WORDS_GETTER("storagerate.field.cost_yj"), false, "cost_yj");
	API_DTO_FIELD(String, cost_zk, ZH_WORDS_GETTER("storagerate.field.cost_zk"), false, "cost_zk");
	API_DTO_FIELD(String, cost_sl, ZH_WORDS_GETTER("storagerate.field.cost_sl"), false, "cost_sl");
	API_DTO_FIELD(String, cost_bhs, ZH_WORDS_GETTER("storagerate.field.cost_bhs"), false, "cost_bhs");
	API_DTO_FIELD(String, cost_hsj, ZH_WORDS_GETTER("storagerate.field.cost_hsj"), false, "cost_hsj");
};

/**
 * Create body
 */
class StorageRateBaseAddDTO : public StorageRateBaseDTO
{
	DTO_INIT(StorageRateBaseAddDTO, StorageRateBaseDTO);
};

/**
 * Update body
 */
class StorageRateBaseModifyDTO : public StorageRateBaseDTO
{
	DTO_INIT(StorageRateBaseModifyDTO, StorageRateBaseDTO);
	API_DTO_FIELD(String, id, ZH_WORDS_GETTER("storagerate.field.id"), true, "id");
};

/**
 * Full create DTO (business + audit)
 */
class StorageRateAddDTO : public StorageRateBaseDTO
{
	DTO_INIT(StorageRateAddDTO, StorageRateBaseDTO);
	API_DTO_FIELD_DEFAULT(String, create_name, ZH_WORDS_GETTER("storagerate.field.create_name"));
	API_DTO_FIELD_DEFAULT(String, create_by, ZH_WORDS_GETTER("storagerate.field.create_by"));
	API_DTO_FIELD_DEFAULT(String, create_date, ZH_WORDS_GETTER("storagerate.field.create_date"));
	API_DTO_FIELD_DEFAULT(String, update_name, ZH_WORDS_GETTER("storagerate.field.update_name"));
	API_DTO_FIELD_DEFAULT(String, update_by, ZH_WORDS_GETTER("storagerate.field.update_by"));
	API_DTO_FIELD_DEFAULT(String, update_date, ZH_WORDS_GETTER("storagerate.field.update_date"));
	API_DTO_FIELD_DEFAULT(String, sys_org_code, ZH_WORDS_GETTER("storagerate.field.sys_org_code"));
	API_DTO_FIELD_DEFAULT(String, sys_company_code, ZH_WORDS_GETTER("storagerate.field.sys_company_code"));
};

/**
 * Full modify DTO (business + audit + id)
 */
class StorageRateModifyDTO : public StorageRateAddDTO
{
	DTO_INIT(StorageRateModifyDTO, StorageRateAddDTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("storagerate.field.id"));
};

/**
 * Row DTO returned to client
 */
class StorageRateDTO : public StorageRateModifyDTO
{
	DTO_INIT(StorageRateDTO, StorageRateModifyDTO);
};

/**
 * Name list item
 */
class StorageRateNameListDTO : public oatpp::DTO
{
	DTO_INIT(StorageRateNameListDTO, oatpp::DTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("storagerate.field.id"));
	API_DTO_FIELD_DEFAULT(String, code, ZH_WORDS_GETTER("storagerate.field.code"));
};

/**
 * Name list page
 */
class StorageRateNameListPageDTO : public PageDTO<StorageRateNameListDTO::Wrapper>
{
	DTO_INIT(StorageRateNameListPageDTO, PageDTO<StorageRateNameListDTO::Wrapper>);
};

/**
 * Row page
 */
class StorageRatePageDTO : public PageDTO<StorageRateDTO::Wrapper>
{
	DTO_INIT(StorageRatePageDTO, PageDTO<StorageRateDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_STORAGERATE_DTO_
