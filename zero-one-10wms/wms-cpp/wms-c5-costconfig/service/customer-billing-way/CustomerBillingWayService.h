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

#ifndef _CUSTOMERBILLINGWAY_SERVICE_
#define _CUSTOMERBILLINGWAY_SERVICE_
#include <list>
#include <vector>
#include <string>
#include "domain/do/customer-billing-way/CustomerBillingWayDO.h"
#include "domain/vo/customer-billing-way/CustomerBillingWayVO.h"
#include "domain/query/customer-billing-way/CustomerBillingWayQuery.h"
#include "domain/dto/customer-billing-way/CustomerBillingWayDTO.h"

/**
 * Service of Customer Billing Way
 */
class CustomerBillingWayService
{
public:
	// create one row, return id
	string insert(const CustomerBillingWayAddDTO::Wrapper& dto);

	// update one row
	bool update(const CustomerBillingWayModifyDTO::Wrapper& dto);

	// name list (no paging)
	CustomerBillingWayNameListPageDTO::Wrapper listName(const CustomerBillingWayQuery::Wrapper& query);

	// row list with paging
	CustomerBillingWayPageDTO::Wrapper listAll(const CustomerBillingWayQuery::Wrapper& query);

	// batch delete by ids
	int removeByIds(const std::vector<std::string>& ids);

	// rows for export
	std::list<CustomerBillingWayDO> listForExport();

	// single row detail
	std::list<CustomerBillingWayDO> getById(const std::string& id);

	// import rows and return inserted count
	int importRows(const std::vector<std::vector<std::string>>& rows,
		const std::string& createBy, const std::string& orgCode, const std::string& companyCode);
};

#endif // !_CUSTOMERBILLINGWAY_SERVICE_
