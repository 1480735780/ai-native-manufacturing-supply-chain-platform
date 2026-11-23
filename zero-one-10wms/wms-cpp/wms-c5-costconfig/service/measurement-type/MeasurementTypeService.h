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

#ifndef _MEASUREMENTTYPE_SERVICE_
#define _MEASUREMENTTYPE_SERVICE_
#include <list>
#include <vector>
#include <string>
#include "domain/do/measurement-type/MeasurementTypeDO.h"
#include "domain/vo/measurement-type/MeasurementTypeVO.h"
#include "domain/query/measurement-type/MeasurementTypeQuery.h"
#include "domain/dto/measurement-type/MeasurementTypeDTO.h"

/**
 * Service of Measurement Type
 */
class MeasurementTypeService
{
public:
	// create one row, return id
	string insert(const MeasurementTypeAddDTO::Wrapper& dto);

	// update one row
	bool update(const MeasurementTypeModifyDTO::Wrapper& dto);

	// name list (no paging)
	MeasurementTypeNameListPageDTO::Wrapper listName(const MeasurementTypeQuery::Wrapper& query);

	// row list with paging
	MeasurementTypePageDTO::Wrapper listAll(const MeasurementTypeQuery::Wrapper& query);

	// batch delete by ids
	int removeByIds(const std::vector<std::string>& ids);

	// rows for export
	std::list<MeasurementTypeDO> listForExport();

	// single row detail
	std::list<MeasurementTypeDO> getById(const std::string& id);

	// import rows and return inserted count
	int importRows(const std::vector<std::vector<std::string>>& rows,
		const std::string& createBy, const std::string& orgCode, const std::string& companyCode);
};

#endif // !_MEASUREMENTTYPE_SERVICE_
