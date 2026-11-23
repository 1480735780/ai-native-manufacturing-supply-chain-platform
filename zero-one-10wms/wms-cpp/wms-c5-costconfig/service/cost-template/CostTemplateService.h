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

#ifndef _COSTTEMPLATE_SERVICE_
#define _COSTTEMPLATE_SERVICE_
#include <list>
#include <vector>
#include <string>
#include "domain/do/cost-template/CostTemplateDO.h"
#include "domain/vo/cost-template/CostTemplateVO.h"
#include "domain/query/cost-template/CostTemplateQuery.h"
#include "domain/dto/cost-template/CostTemplateDTO.h"

/**
 * Service of Cost Template
 */
class CostTemplateService
{
public:
	// create one row, return id
	string insert(const CostTemplateAddDTO::Wrapper& dto);

	// update one row
	bool update(const CostTemplateModifyDTO::Wrapper& dto);

	// name list (no paging)
	CostTemplateNameListPageDTO::Wrapper listName(const CostTemplateQuery::Wrapper& query);

	// row list with paging
	CostTemplatePageDTO::Wrapper listAll(const CostTemplateQuery::Wrapper& query);

	// batch delete by ids
	int removeByIds(const std::vector<std::string>& ids);

	// rows for export
	std::list<CostTemplateDO> listForExport();

	// single row detail
	std::list<CostTemplateDO> getById(const std::string& id);

	// import rows and return inserted count
	int importRows(const std::vector<std::vector<std::string>>& rows,
		const std::string& createBy, const std::string& orgCode, const std::string& companyCode);
};

#endif // !_COSTTEMPLATE_SERVICE_
