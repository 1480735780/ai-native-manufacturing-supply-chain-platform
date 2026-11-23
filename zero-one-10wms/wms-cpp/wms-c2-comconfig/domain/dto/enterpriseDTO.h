#pragma once
/*
Copyright Zero One Star.All rights reserved.

@Author: z
@Date : 2025/2/22 10 : 01

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https ://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
#ifndef _ENTERPRISE_DTO_
#define _ENTERPRISE_DTO_
#include "../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO) //< Begin DTO codegen section
//录入企业分类DTO
class addEnterpriseDTO : public oatpp::DTO {

	DTO_INIT(addEnterpriseDTO, DTO);

	//企业分类唯一ID（分页列表回传，供修改/删除使用）
	DTO_FIELD(String, id);

	//企业分类代码
	DTO_FIELD(String, enterpriseClassificationCode);
	DTO_FIELD_INFO(enterpriseClassificationCode) {
		info->description = ZH_WORDS_GETTER("indclas.field.code");
	}

	//企业分类名称
	DTO_FIELD(String, enterpriseClassificationName);
	DTO_FIELD_INFO(enterpriseClassificationName) {
		info->description = ZH_WORDS_GETTER("indclas.field.name");
	}

	//停用信息
	DTO_FIELD(UInt64, stopInfo);
	DTO_FIELD_INFO(stopInfo) {
		info->description = ZH_WORDS_GETTER("indclas.field.stopInfo");
	}

};
/*
* 分页查询传输对象
*/
class enterprisePageDTO : public PageDTO< addEnterpriseDTO::Wrapper>//enterprisePageDTO
{
	DTO_INIT(enterprisePageDTO, PageDTO< addEnterpriseDTO::Wrapper>);
};

/*
* 查询企业名称DTO
*/
class enterpriseNameDTO :public oatpp::DTO
{
	DTO_INIT(enterpriseNameDTO, oatpp::DTO);

	//企业分类名称
	DTO_FIELD(List<String> , enterpriseNameList) = {};

	DTO_FIELD_INFO(enterpriseNameList) {
		info->description = ZH_WORDS_GETTER("indclas.field.namelist");
	}
public :
	void addData(const String& name)
	{
		this->enterpriseNameList->push_back(name);
	}
};

#include OATPP_CODEGEN_END(DTO) ///< End DTO codegen section
#endif // !_ADD_ENTERPRISE_DTO_
