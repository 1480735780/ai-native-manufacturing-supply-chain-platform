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

#ifndef _PRICETYPE_MAPPER_
#define _PRICETYPE_MAPPER_

#include "Mapper.h"
#include "../../domain/do/price-type/PriceTypeDO.h"

/**
 * Map result set to name list item
 */
class PriceTypeMapperName : public Mapper<PriceTypeDO>
{
public:
	PriceTypeDO mapper(ResultSet* resultSet) const override
	{
		PriceTypeDO data;
		data.setId(resultSet->getString(1));
		data.setPriceTypeName(resultSet->getString(2));
		return data;
	}
};

/**
 * Map result set to full row
 */
class PriceTypeMapperAll : public Mapper<PriceTypeDO>
{
public:
	PriceTypeDO mapper(ResultSet* resultSet) const override
	{
		PriceTypeDO data;
		data.setId(resultSet->getString(1));
		data.setPriceTypeCode(resultSet->getString(2));
		data.setPriceTypeName(resultSet->getString(3));
		data.setCreateName(resultSet->getString(4));
		data.setCreateBy(resultSet->getString(5));
		data.setCreateDate(resultSet->getString(6));
		data.setUpdateName(resultSet->getString(7));
		data.setUpdateBy(resultSet->getString(8));
		data.setUpdateDate(resultSet->getString(9));
		data.setSysOrgCode(resultSet->getString(10));
		data.setSysCompanyCode(resultSet->getString(11));
		return data;
	}
};

#endif // !_PRICETYPE_MAPPER_
