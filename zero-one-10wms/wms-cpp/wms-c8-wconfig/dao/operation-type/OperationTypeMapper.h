/*
 Copyright Zero One Star. All rights reserved.

 @Author: zero-one-star
 @Date: 2025/03/10 16:09:12

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
#ifndef _OPERATION_TYPE_MAPPER_
#define _OPERATION_TYPE_MAPPER_

#include "Mapper.h"
#include "../../domain/do/operation-type/OperationTypeDO.h"

/**
 * 操作类型字段匹配映射
 */
class OperationTypeMapper : public Mapper<OperationTypeDO>
{
public:
	OperationTypeDO mapper(ResultSet* resultSet) const override
	{
		OperationTypeDO data;
		data.setId(resultSet->getString(1));
		data.setCode(resultSet->getString(2));
		data.setName(resultSet->getString(3));
		return data;
	}
};

/**
 * 操作类型字段匹配映射-关联智能指针类型
 */
class PtrOperationTypeMapper : public Mapper<PtrOperationTypeDO>
{
public:
	PtrOperationTypeDO mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<OperationTypeDO>();
		data->setId(resultSet->getString(1));
		data->setCode(resultSet->getString(2));
		data->setName(resultSet->getString(3));
		return data;
	}
};

#endif // !_OPERATION_TYPE_MAPPER_
