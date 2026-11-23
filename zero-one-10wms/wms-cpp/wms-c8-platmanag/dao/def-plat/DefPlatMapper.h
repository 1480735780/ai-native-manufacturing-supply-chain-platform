#pragma once
/*
 Copyright Zero One Star. All rights reserved.

 @Author: mao
 @Date: 2025/2/27 16:15:53

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
#ifndef _DEFPLAT_MAPPER_
#define _DEFPLAT_MAPPER_

#include "Mapper.h"
#include "../../domain/do/def-plat/PlatDO.h"

/**
 * 通用字段匹配映射（按列序显式映射，列序与 SELECT 语句一致）
 * 列序：1=id 2=platform_code 3=platform_name
 */
class DefPlatMapper : public Mapper<PlatDO>
{
public:
	PlatDO mapper(ResultSet* resultSet) const override
	{
		PlatDO data;
		data.setid(resultSet->getString(1));
		data.setplatform_code(resultSet->getString(2));
		data.setplatform_name(resultSet->getString(3));
		return data;
	}
};

/**
 * 分页列表字段映射（五列：1=id 2=code 3=name 4=create_name 5=create_date）
 */
class DefPlatPageMapper : public Mapper<PlatDO>
{
public:
	PlatDO mapper(ResultSet* resultSet) const override
	{
		PlatDO data;
		data.setid(resultSet->getString(1));
		data.setplatform_code(resultSet->getString(2));
		data.setplatform_name(resultSet->getString(3));
		data.setcreate_name(resultSet->getString(4));
		data.setcreate_date(resultSet->getString(5));
		return data;
	}
};

/**
 * 指针字段匹配映射-用于返回智能指针数据
 */
class PtrDefPlatMapper : public Mapper<PtrPlatDO>
{
public:
	PtrPlatDO mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<PlatDO>();
		data->setid(resultSet->getString(1));
		data->setplatform_code(resultSet->getString(2));
		data->setplatform_name(resultSet->getString(3));
		return data;
	}
};

#endif // !_SAMPLE_MAPPER_
