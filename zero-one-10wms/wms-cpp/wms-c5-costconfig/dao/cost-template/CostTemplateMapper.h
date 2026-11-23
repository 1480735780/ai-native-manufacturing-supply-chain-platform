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

#ifndef _COSTTEMPLATE_MAPPER_
#define _COSTTEMPLATE_MAPPER_

#include "Mapper.h"
#include "../../domain/do/cost-template/CostTemplateDO.h"

/**
 * Map result set to name list item
 */
class CostTemplateMapperName : public Mapper<CostTemplateDO>
{
public:
	CostTemplateDO mapper(ResultSet* resultSet) const override
	{
		CostTemplateDO data;
		data.setId(resultSet->getString(1));
		data.setCostCode(resultSet->getString(2));
		return data;
	}
};

/**
 * Map result set to full row
 */
class CostTemplateMapperAll : public Mapper<CostTemplateDO>
{
public:
	CostTemplateDO mapper(ResultSet* resultSet) const override
	{
		CostTemplateDO data;
		data.setId(resultSet->getString(1));
		data.setCostCode(resultSet->getString(2));
		data.setCostJg(resultSet->getString(3));
		data.setCostSl(resultSet->getString(4));
		data.setCostZk(resultSet->getString(5));
		data.setCostBhs(resultSet->getString(6));
		data.setCostHs(resultSet->getString(7));
		data.setFreeDay(resultSet->getString(8));
		data.setFreeDay2(resultSet->getString(9));
		data.setCreateName(resultSet->getString(10));
		data.setCreateBy(resultSet->getString(11));
		data.setCreateDate(resultSet->getString(12));
		data.setUpdateName(resultSet->getString(13));
		data.setUpdateBy(resultSet->getString(14));
		data.setUpdateDate(resultSet->getString(15));
		data.setSysOrgCode(resultSet->getString(16));
		data.setSysCompanyCode(resultSet->getString(17));
		return data;
	}
};

#endif // !_COSTTEMPLATE_MAPPER_
