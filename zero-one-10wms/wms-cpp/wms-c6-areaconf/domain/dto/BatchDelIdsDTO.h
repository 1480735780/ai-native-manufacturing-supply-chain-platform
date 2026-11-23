#pragma once
/*
 Copyright Zero One Star. All rights reserved.

 Batch delete request DTO for areaconf module (citytype / barea / darea / city).

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

#ifndef _AREACONF_BATCH_DELETE_DTO_
#define _AREACONF_BATCH_DELETE_DTO_

#include "../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)
// id list for batch delete (string ids: snowflake / uuid both supported)
class BatchDelIdsDTO : public oatpp::DTO {
	DTO_INIT(BatchDelIdsDTO, DTO);
	// id list
	API_DTO_FIELD_DEFAULT(List<String>, ids, u8"id列表");
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_AREACONF_BATCH_DELETE_DTO_
