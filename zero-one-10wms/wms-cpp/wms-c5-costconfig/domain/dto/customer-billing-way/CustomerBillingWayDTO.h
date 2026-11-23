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

#ifndef _CUSTOMERBILLINGWAY_DTO_
#define _CUSTOMERBILLINGWAY_DTO_

#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * Business fields of Customer Billing Way
 */
class CustomerBillingWayBaseDTO : public oatpp::DTO
{
	DTO_INIT(CustomerBillingWayBaseDTO, oatpp::DTO);

	API_DTO_FIELD(String, code, ZH_WORDS_GETTER("cusbillway.field.code"), true, "code");
	API_DTO_FIELD(String, name, ZH_WORDS_GETTER("cusbillway.field.name"), false, "name");
	API_DTO_FIELD(String, cus_sta_del, ZH_WORDS_GETTER("cusbillway.field.cus_sta_del"), false, "cus_sta_del");
};

/**
 * Create body
 */
class CustomerBillingWayBaseAddDTO : public CustomerBillingWayBaseDTO
{
	DTO_INIT(CustomerBillingWayBaseAddDTO, CustomerBillingWayBaseDTO);
};

/**
 * Update body
 */
class CustomerBillingWayBaseModifyDTO : public CustomerBillingWayBaseDTO
{
	DTO_INIT(CustomerBillingWayBaseModifyDTO, CustomerBillingWayBaseDTO);
	API_DTO_FIELD(String, id, ZH_WORDS_GETTER("cusbillway.field.id"), true, "id");
};

/**
 * Full create DTO (business + audit)
 */
class CustomerBillingWayAddDTO : public CustomerBillingWayBaseDTO
{
	DTO_INIT(CustomerBillingWayAddDTO, CustomerBillingWayBaseDTO);
	API_DTO_FIELD_DEFAULT(String, create_name, ZH_WORDS_GETTER("cusbillway.field.create_name"));
	API_DTO_FIELD_DEFAULT(String, create_by, ZH_WORDS_GETTER("cusbillway.field.create_by"));
	API_DTO_FIELD_DEFAULT(String, create_date, ZH_WORDS_GETTER("cusbillway.field.create_date"));
	API_DTO_FIELD_DEFAULT(String, update_name, ZH_WORDS_GETTER("cusbillway.field.update_name"));
	API_DTO_FIELD_DEFAULT(String, update_by, ZH_WORDS_GETTER("cusbillway.field.update_by"));
	API_DTO_FIELD_DEFAULT(String, update_date, ZH_WORDS_GETTER("cusbillway.field.update_date"));
	API_DTO_FIELD_DEFAULT(String, sys_org_code, ZH_WORDS_GETTER("cusbillway.field.sys_org_code"));
	API_DTO_FIELD_DEFAULT(String, sys_company_code, ZH_WORDS_GETTER("cusbillway.field.sys_company_code"));
};

/**
 * Full modify DTO (business + audit + id)
 */
class CustomerBillingWayModifyDTO : public CustomerBillingWayAddDTO
{
	DTO_INIT(CustomerBillingWayModifyDTO, CustomerBillingWayAddDTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("cusbillway.field.id"));
};

/**
 * Row DTO returned to client
 */
class CustomerBillingWayDTO : public CustomerBillingWayModifyDTO
{
	DTO_INIT(CustomerBillingWayDTO, CustomerBillingWayModifyDTO);
};

/**
 * Name list item
 */
class CustomerBillingWayNameListDTO : public oatpp::DTO
{
	DTO_INIT(CustomerBillingWayNameListDTO, oatpp::DTO);
	API_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("cusbillway.field.id"));
	API_DTO_FIELD_DEFAULT(String, name, ZH_WORDS_GETTER("cusbillway.field.name"));
};

/**
 * Name list page
 */
class CustomerBillingWayNameListPageDTO : public PageDTO<CustomerBillingWayNameListDTO::Wrapper>
{
	DTO_INIT(CustomerBillingWayNameListPageDTO, PageDTO<CustomerBillingWayNameListDTO::Wrapper>);
};

/**
 * Row page
 */
class CustomerBillingWayPageDTO : public PageDTO<CustomerBillingWayDTO::Wrapper>
{
	DTO_INIT(CustomerBillingWayPageDTO, PageDTO<CustomerBillingWayDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_CUSTOMERBILLINGWAY_DTO_
