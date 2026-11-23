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

#ifndef _STORAGERATE_VO_
#define _STORAGERATE_VO_

#include "../../GlobalInclude.h"
#include "../../dto/storage-rate/StorageRateDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

class StorageRateNameListPageJsonVO : public JsonVO<StorageRateNameListPageDTO::Wrapper> {
	DTO_INIT(StorageRateNameListPageJsonVO, JsonVO<StorageRateNameListPageDTO::Wrapper>);
};

class StorageRatePageJsonVO : public JsonVO<StorageRatePageDTO::Wrapper> {
	DTO_INIT(StorageRatePageJsonVO, JsonVO<StorageRatePageDTO::Wrapper>);
};

class StorageRateDetailJsonVO : public JsonVO<StorageRateDTO::Wrapper> {
	DTO_INIT(StorageRateDetailJsonVO, JsonVO<StorageRateDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_STORAGERATE_VO_
