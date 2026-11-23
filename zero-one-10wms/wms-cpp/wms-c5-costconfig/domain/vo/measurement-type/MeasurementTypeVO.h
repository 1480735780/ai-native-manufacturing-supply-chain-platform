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

#ifndef _MEASUREMENTTYPE_VO_
#define _MEASUREMENTTYPE_VO_

#include "../../GlobalInclude.h"
#include "../../dto/measurement-type/MeasurementTypeDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

class MeasurementTypeNameListPageJsonVO : public JsonVO<MeasurementTypeNameListPageDTO::Wrapper> {
	DTO_INIT(MeasurementTypeNameListPageJsonVO, JsonVO<MeasurementTypeNameListPageDTO::Wrapper>);
};

class MeasurementTypePageJsonVO : public JsonVO<MeasurementTypePageDTO::Wrapper> {
	DTO_INIT(MeasurementTypePageJsonVO, JsonVO<MeasurementTypePageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_MEASUREMENTTYPE_VO_
