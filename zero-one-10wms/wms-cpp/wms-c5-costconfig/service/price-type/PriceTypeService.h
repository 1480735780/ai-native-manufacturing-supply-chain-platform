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

#ifndef _PRICETYPE_SERVICE_
#define _PRICETYPE_SERVICE_
#include <list>
#include <vector>
#include <string>
#include "domain/do/price-type/PriceTypeDO.h"
#include "domain/vo/price-type/PriceTypeVO.h"
#include "domain/query/price-type/PriceTypeQuery.h"
#include "domain/dto/price-type/PriceTypeDTO.h"

/**
 * Service of Price Type
 */
class PriceTypeService
{
public:
	// create one row, return id
	string insert(const PriceTypeAddDTO::Wrapper& dto);

	// update one row
	bool update(const PriceTypeModifyDTO::Wrapper& dto);

	// name list (no paging)
	PriceTypeNameListPageDTO::Wrapper listName(const PriceTypeQuery::Wrapper& query);

	// row list with paging
	PriceTypePageDTO::Wrapper listAll(const PriceTypeQuery::Wrapper& query);

	// batch delete by ids
	int removeByIds(const std::vector<std::string>& ids);

	// rows for export
	std::list<PriceTypeDO> listForExport();

	// single row detail
	std::list<PriceTypeDO> getById(const std::string& id);

	// import rows and return inserted count
	int importRows(const std::vector<std::vector<std::string>>& rows,
		const std::string& createBy, const std::string& orgCode, const std::string& companyCode);
};

#endif // !_PRICETYPE_SERVICE_
