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

#ifndef _CUSTOMERBILLINGWAY_VO_
#define _CUSTOMERBILLINGWAY_VO_

#include "../../GlobalInclude.h"
#include "../../dto/customer-billing-way/CustomerBillingWayDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

class CustomerBillingWayNameListPageJsonVO : public JsonVO<CustomerBillingWayNameListPageDTO::Wrapper> {
	DTO_INIT(CustomerBillingWayNameListPageJsonVO, JsonVO<CustomerBillingWayNameListPageDTO::Wrapper>);
};

class CustomerBillingWayPageJsonVO : public JsonVO<CustomerBillingWayPageDTO::Wrapper> {
	DTO_INIT(CustomerBillingWayPageJsonVO, JsonVO<CustomerBillingWayPageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_CUSTOMERBILLINGWAY_VO_
