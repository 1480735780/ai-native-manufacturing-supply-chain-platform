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

#ifndef _COSTTEMPLATE_VO_
#define _COSTTEMPLATE_VO_

#include "../../GlobalInclude.h"
#include "../../dto/cost-template/CostTemplateDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

class CostTemplateNameListPageJsonVO : public JsonVO<CostTemplateNameListPageDTO::Wrapper> {
	DTO_INIT(CostTemplateNameListPageJsonVO, JsonVO<CostTemplateNameListPageDTO::Wrapper>);
};

class CostTemplatePageJsonVO : public JsonVO<CostTemplatePageDTO::Wrapper> {
	DTO_INIT(CostTemplatePageJsonVO, JsonVO<CostTemplatePageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_COSTTEMPLATE_VO_
