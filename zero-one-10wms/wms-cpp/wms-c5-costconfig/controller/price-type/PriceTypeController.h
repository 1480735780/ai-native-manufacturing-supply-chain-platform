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

#ifndef _PRICETYPE_CONTROLLER_
#define _PRICETYPE_CONTROLLER_

#include "domain/vo/BaseJsonVO.h"
#include "domain/query/price-type/PriceTypeQuery.h"
#include "domain/dto/price-type/PriceTypeDTO.h"
#include "domain/vo/price-type/PriceTypeVO.h"
#include "iostream"

#include OATPP_CODEGEN_BEGIN(ApiController)

/**
 * Price Type
 */
class PriceTypeController : public oatpp::web::server::api::ApiController
{
	API_ACCESS_DECLARE(PriceTypeController);
public:

	// name list
	ENDPOINT_INFO(queryPriceTypeName) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("pricetype.query-name.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(PriceTypeNameListPageJsonVO);
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("pricetype.field.code"), "code", false);
		API_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("pricetype.field.name"), "name", false);
	}
	ENDPOINT(API_M_GET, "/cost-config/price-type/query-price-type-name", queryPriceTypeName, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, PriceTypeQuery, queryParams);
		API_HANDLER_RESP_VO(execQueryPriceTypeName(query));
	}

	// page list
	ENDPOINT_INFO(queryPriceTypePage) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("pricetype.query-page.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(PriceTypePageJsonVO);
		API_DEF_ADD_PAGE_PARAMS();
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("pricetype.field.code"), "code", false);
		API_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("pricetype.field.name"), "name", false);
	}
	ENDPOINT(API_M_GET, "/cost-config/price-type/query-price-type-page", queryPriceTypePage, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, PriceTypeQuery, queryParams);
		API_HANDLER_RESP_VO(execQueryPriceTypePage(query));
	}

	// create
	ENDPOINT_INFO(addPriceType) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("pricetype.post.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	ENDPOINT(API_M_POST, "/cost-config/price-type/add-price-type", addPriceType, BODY_DTO(PriceTypeBaseAddDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		PriceTypeAddDTO::Wrapper adto = buildFullDTO(dto, authObject.get()->getPayload());
		API_HANDLER_RESP_VO(execAddPriceType(adto));
	}

	// update
	ENDPOINT_INFO(modifyPriceType) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("pricetype.put.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	ENDPOINT(API_M_PUT, "/cost-config/price-type/modify-price-type", modifyPriceType, BODY_DTO(PriceTypeBaseModifyDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		PriceTypeModifyDTO::Wrapper mdto = buildFullDTO(dto, authObject.get()->getPayload());
		API_HANDLER_RESP_VO(execModifyPriceType(mdto));
	}

	// batch delete
	ENDPOINT_INFO(deletePriceType) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("pricetype.delete.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/cost-config/price-type/delete-price-type", deletePriceType, BODY_DTO(List<String>, ids), execDeletePriceType(ids));

	// export
	ENDPOINT_INFO(exportPriceType) {
		API_DEF_ADD_AUTH();
		API_DEF_ADD_COMMON(ZH_WORDS_GETTER("pricetype.export.summary"), Void);
	}
	ENDPOINT(API_M_GET, "/cost-config/price-type/export-price-type", exportPriceType, API_HANDLER_AUTH_PARAME) {
		return execExportPriceType();
	}

	// import
	ENDPOINT_INFO(importPriceType) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("pricetype.import.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_POST, "/cost-config/price-type/import-price-type", importPriceType, REQUEST(std::shared_ptr<IncomingRequest>, request), execImportPriceType(request, authObject->getPayload()));

private:
	StringJsonVO::Wrapper execAddPriceType(const PriceTypeAddDTO::Wrapper& dto);
	StringJsonVO::Wrapper execModifyPriceType(const PriceTypeModifyDTO::Wrapper& dto);
	PriceTypeNameListPageJsonVO::Wrapper execQueryPriceTypeName(const PriceTypeQuery::Wrapper& query);
	PriceTypePageJsonVO::Wrapper execQueryPriceTypePage(const PriceTypeQuery::Wrapper& query);
	StringJsonVO::Wrapper execDeletePriceType(const List<String>& ids);
	std::shared_ptr<OutgoingResponse> execExportPriceType();
	StringJsonVO::Wrapper execImportPriceType(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);

	PriceTypeModifyDTO::Wrapper buildFullDTO(const PriceTypeBaseModifyDTO::Wrapper& baseDto, const PayloadDTO& payload);
	PriceTypeAddDTO::Wrapper buildFullDTO(const PriceTypeBaseAddDTO::Wrapper& baseDto, const PayloadDTO& payload);
};

#include OATPP_CODEGEN_END(ApiController)
#endif // !_PRICETYPE_CONTROLLER_
