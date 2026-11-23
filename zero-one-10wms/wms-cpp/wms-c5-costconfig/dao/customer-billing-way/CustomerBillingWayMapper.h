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

#ifndef _CUSTOMERBILLINGWAY_MAPPER_
#define _CUSTOMERBILLINGWAY_MAPPER_

#include "Mapper.h"
#include "../../domain/do/customer-billing-way/CustomerBillingWayDO.h"

/**
 * Map result set to name list item
 */
class CustomerBillingWayMapperName : public Mapper<CustomerBillingWayDO>
{
public:
	CustomerBillingWayDO mapper(ResultSet* resultSet) const override
	{
		CustomerBillingWayDO data;
		data.setId(resultSet->getString(1));
		data.setKehuzhuangtaiName(resultSet->getString(2));
		return data;
	}
};

/**
 * Map result set to full row
 */
class CustomerBillingWayMapperAll : public Mapper<CustomerBillingWayDO>
{
public:
	CustomerBillingWayDO mapper(ResultSet* resultSet) const override
	{
		CustomerBillingWayDO data;
		data.setId(resultSet->getString(1));
		data.setKehuzhuangtaiCode(resultSet->getString(2));
		data.setKehuzhuangtaiName(resultSet->getString(3));
		data.setCusStaDel(resultSet->getString(4));
		data.setCreateName(resultSet->getString(5));
		data.setCreateBy(resultSet->getString(6));
		data.setCreateDate(resultSet->getString(7));
		data.setUpdateName(resultSet->getString(8));
		data.setUpdateBy(resultSet->getString(9));
		data.setUpdateDate(resultSet->getString(10));
		data.setSysOrgCode(resultSet->getString(11));
		data.setSysCompanyCode(resultSet->getString(12));
		return data;
	}
};

#endif // !_CUSTOMERBILLINGWAY_MAPPER_
