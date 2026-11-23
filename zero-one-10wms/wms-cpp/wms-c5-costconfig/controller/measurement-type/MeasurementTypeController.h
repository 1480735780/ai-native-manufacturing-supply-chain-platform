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

#ifndef _MEASUREMENTTYPE_CONTROLLER_
#define _MEASUREMENTTYPE_CONTROLLER_

#include "domain/vo/BaseJsonVO.h"
#include "domain/query/measurement-type/MeasurementTypeQuery.h"
#include "domain/dto/measurement-type/MeasurementTypeDTO.h"
#include "domain/vo/measurement-type/MeasurementTypeVO.h"
#include "iostream"

#include OATPP_CODEGEN_BEGIN(ApiController)

/**
 * Measurement Type
 */
class MeasurementTypeController : public oatpp::web::server::api::ApiController
{
	API_ACCESS_DECLARE(MeasurementTypeController);
public:

	// name list
	ENDPOINT_INFO(queryMeasurementTypeName) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("measuretype.query-name.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(MeasurementTypeNameListPageJsonVO);
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("measuretype.field.code"), "code", false);
		API_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("measuretype.field.name"), "name", false);
	}
	ENDPOINT(API_M_GET, "/cost-config/measurement-type/query-measurement-type-name", queryMeasurementTypeName, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, MeasurementTypeQuery, queryParams);
		API_HANDLER_RESP_VO(execQueryMeasurementTypeName(query));
	}

	// page list
	ENDPOINT_INFO(queryMeasurementTypePage) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("measuretype.query-page.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(MeasurementTypePageJsonVO);
		API_DEF_ADD_PAGE_PARAMS();
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("measuretype.field.code"), "code", false);
		API_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("measuretype.field.name"), "name", false);
	}
	ENDPOINT(API_M_GET, "/cost-config/measurement-type/query-measurement-type-page", queryMeasurementTypePage, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, MeasurementTypeQuery, queryParams);
		API_HANDLER_RESP_VO(execQueryMeasurementTypePage(query));
	}

	// create
	ENDPOINT_INFO(addMeasurementType) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("measuretype.post.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	ENDPOINT(API_M_POST, "/cost-config/measurement-type/add-measurement-type", addMeasurementType, BODY_DTO(MeasurementTypeBaseAddDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		MeasurementTypeAddDTO::Wrapper adto = buildFullDTO(dto, authObject.get()->getPayload());
		API_HANDLER_RESP_VO(execAddMeasurementType(adto));
	}

	// update
	ENDPOINT_INFO(modifyMeasurementType) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("measuretype.put.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	ENDPOINT(API_M_PUT, "/cost-config/measurement-type/modify-measurement-type", modifyMeasurementType, BODY_DTO(MeasurementTypeBaseModifyDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		MeasurementTypeModifyDTO::Wrapper mdto = buildFullDTO(dto, authObject.get()->getPayload());
		API_HANDLER_RESP_VO(execModifyMeasurementType(mdto));
	}

	// batch delete
	ENDPOINT_INFO(deleteMeasurementType) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("measuretype.delete.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/cost-config/measurement-type/delete-measurement-type", deleteMeasurementType, BODY_DTO(List<String>, ids), execDeleteMeasurementType(ids));

	// export
	ENDPOINT_INFO(exportMeasurementType) {
		API_DEF_ADD_AUTH();
		API_DEF_ADD_COMMON(ZH_WORDS_GETTER("measuretype.export.summary"), Void);
	}
	ENDPOINT(API_M_GET, "/cost-config/measurement-type/export-measurement-type", exportMeasurementType, API_HANDLER_AUTH_PARAME) {
		return execExportMeasurementType();
	}

	// import
	ENDPOINT_INFO(importMeasurementType) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("measuretype.import.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_POST, "/cost-config/measurement-type/import-measurement-type", importMeasurementType, REQUEST(std::shared_ptr<IncomingRequest>, request), execImportMeasurementType(request, authObject->getPayload()));

private:
	StringJsonVO::Wrapper execAddMeasurementType(const MeasurementTypeAddDTO::Wrapper& dto);
	StringJsonVO::Wrapper execModifyMeasurementType(const MeasurementTypeModifyDTO::Wrapper& dto);
	MeasurementTypeNameListPageJsonVO::Wrapper execQueryMeasurementTypeName(const MeasurementTypeQuery::Wrapper& query);
	MeasurementTypePageJsonVO::Wrapper execQueryMeasurementTypePage(const MeasurementTypeQuery::Wrapper& query);
	StringJsonVO::Wrapper execDeleteMeasurementType(const List<String>& ids);
	std::shared_ptr<OutgoingResponse> execExportMeasurementType();
	StringJsonVO::Wrapper execImportMeasurementType(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);

	MeasurementTypeModifyDTO::Wrapper buildFullDTO(const MeasurementTypeBaseModifyDTO::Wrapper& baseDto, const PayloadDTO& payload);
	MeasurementTypeAddDTO::Wrapper buildFullDTO(const MeasurementTypeBaseAddDTO::Wrapper& baseDto, const PayloadDTO& payload);
};

#include OATPP_CODEGEN_END(ApiController)
#endif // !_MEASUREMENTTYPE_CONTROLLER_
