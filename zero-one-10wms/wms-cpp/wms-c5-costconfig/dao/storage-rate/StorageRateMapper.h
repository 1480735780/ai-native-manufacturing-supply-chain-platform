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

#ifndef _STORAGERATE_MAPPER_
#define _STORAGERATE_MAPPER_

#include "Mapper.h"
#include "../../domain/do/storage-rate/StorageRateDO.h"

/**
 * Map result set to name list item
 */
class StorageRateMapperName : public Mapper<StorageRateDO>
{
public:
	StorageRateDO mapper(ResultSet* resultSet) const override
	{
		StorageRateDO data;
		data.setId(resultSet->getString(1));
		data.setCostCode(resultSet->getString(2));
		return data;
	}
};

/**
 * Map result set to full row
 */
class StorageRateMapperAll : public Mapper<StorageRateDO>
{
public:
	StorageRateDO mapper(ResultSet* resultSet) const override
	{
		StorageRateDO data;
		data.setId(resultSet->getString(1));
		data.setCostCode(resultSet->getString(2));
		data.setCostYj(resultSet->getString(3));
		data.setCostZk(resultSet->getString(4));
		data.setCostSl(resultSet->getString(5));
		data.setCostBhs(resultSet->getString(6));
		data.setCostHsj(resultSet->getString(7));
		data.setCreateName(resultSet->getString(8));
		data.setCreateBy(resultSet->getString(9));
		data.setCreateDate(resultSet->getString(10));
		data.setUpdateName(resultSet->getString(11));
		data.setUpdateBy(resultSet->getString(12));
		data.setUpdateDate(resultSet->getString(13));
		data.setSysOrgCode(resultSet->getString(14));
		data.setSysCompanyCode(resultSet->getString(15));
		return data;
	}
};

#endif // !_STORAGERATE_MAPPER_
