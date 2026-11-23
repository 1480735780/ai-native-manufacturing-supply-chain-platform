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

#ifndef _COSTTEMPLATE_DAO_
#define _COSTTEMPLATE_DAO_

#include "stdafx.h"
#include "BaseDAO.h"
#include "../../domain/do/cost-template/CostTemplateDO.h"
#include "../../domain/query/cost-template/CostTemplateQuery.h"
#include "id/UuidFacade.h"
#include <iostream>
#include <vector>

/**
 * DAO of table ba_cost_conf
 */
class CostTemplateDAO : public BaseDAO
{
	inline std::string queryConditionBuilder(const CostTemplateQuery::Wrapper& query, SqlParams& params);
public:
	// insert one row, return generated id or empty string
	std::string insert(const CostTemplateDO& udo);

	// update one row by id
	bool update(const CostTemplateDO& udo);

	// count rows by condition
	uint64_t count(const CostTemplateQuery::Wrapper& query);

	// select id + name list
	std::list<CostTemplateDO> selectName(const CostTemplateQuery::Wrapper& query);

	// select rows with paging
	std::list<CostTemplateDO> selectAllWithPage(const CostTemplateQuery::Wrapper& query);

	// batch delete by primary key ids, return affected rows
	int deleteByIds(const std::vector<std::string>& ids);

	// select all rows for excel export
	std::list<CostTemplateDO> selectForExport();

	// select one row by id
	std::list<CostTemplateDO> selectById(const std::string& id);
};

#endif // !_COSTTEMPLATE_DAO_
