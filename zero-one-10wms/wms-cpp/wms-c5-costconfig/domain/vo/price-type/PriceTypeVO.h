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

#ifndef _PRICETYPE_VO_
#define _PRICETYPE_VO_

#include "../../GlobalInclude.h"
#include "../../dto/price-type/PriceTypeDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

class PriceTypeNameListPageJsonVO : public JsonVO<PriceTypeNameListPageDTO::Wrapper> {
	DTO_INIT(PriceTypeNameListPageJsonVO, JsonVO<PriceTypeNameListPageDTO::Wrapper>);
};

class PriceTypePageJsonVO : public JsonVO<PriceTypePageDTO::Wrapper> {
	DTO_INIT(PriceTypePageJsonVO, JsonVO<PriceTypePageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_PRICETYPE_VO_
