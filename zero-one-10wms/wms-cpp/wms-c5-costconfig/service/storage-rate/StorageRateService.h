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

#ifndef _STORAGERATE_SERVICE_
#define _STORAGERATE_SERVICE_
#include <list>
#include <vector>
#include <string>
#include "domain/do/storage-rate/StorageRateDO.h"
#include "domain/vo/storage-rate/StorageRateVO.h"
#include "domain/query/storage-rate/StorageRateQuery.h"
#include "domain/dto/storage-rate/StorageRateDTO.h"

/**
 * Service of Storage Rate
 */
class StorageRateService
{
public:
	// create one row, return id
	string insert(const StorageRateAddDTO::Wrapper& dto);

	// update one row
	bool update(const StorageRateModifyDTO::Wrapper& dto);

	// name list (no paging)
	StorageRateNameListPageDTO::Wrapper listName(const StorageRateQuery::Wrapper& query);

	// row list with paging
	StorageRatePageDTO::Wrapper listAll(const StorageRateQuery::Wrapper& query);

	// batch delete by ids
	int removeByIds(const std::vector<std::string>& ids);

	// rows for export
	std::list<StorageRateDO> listForExport();

	// single row detail
	std::list<StorageRateDO> getById(const std::string& id);

	// import rows and return inserted count
	int importRows(const std::vector<std::vector<std::string>>& rows,
		const std::string& createBy, const std::string& orgCode, const std::string& companyCode);
};

#endif // !_STORAGERATE_SERVICE_
