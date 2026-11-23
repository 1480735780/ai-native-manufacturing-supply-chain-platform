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

#ifndef _CUSTOMERBILLINGWAY_CONTROLLER_
#define _CUSTOMERBILLINGWAY_CONTROLLER_

#include "domain/vo/BaseJsonVO.h"
#include "domain/query/customer-billing-way/CustomerBillingWayQuery.h"
#include "domain/dto/customer-billing-way/CustomerBillingWayDTO.h"
#include "domain/vo/customer-billing-way/CustomerBillingWayVO.h"
#include "iostream"

#include OATPP_CODEGEN_BEGIN(ApiController)

/**
 * Customer Billing Way
 */
class CustomerBillingWayController : public oatpp::web::server::api::ApiController
{
	API_ACCESS_DECLARE(CustomerBillingWayController);
public:

	// name list
	ENDPOINT_INFO(queryCustomerBillingWayName) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("cusbillway.query-name.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(CustomerBillingWayNameListPageJsonVO);
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("cusbillway.field.code"), "code", false);
		API_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("cusbillway.field.name"), "name", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cus_sta_del", ZH_WORDS_GETTER("cusbillway.field.cus_sta_del"), "cus_sta_del", false);
	}
	ENDPOINT(API_M_GET, "/cost-config/customer-billing-way/query-customer-billing-way-name", queryCustomerBillingWayName, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, CustomerBillingWayQuery, queryParams);
		API_HANDLER_RESP_VO(execQueryCustomerBillingWayName(query));
	}

	// page list
	ENDPOINT_INFO(queryCustomerBillingWayPage) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("cusbillway.query-page.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(CustomerBillingWayPageJsonVO);
		API_DEF_ADD_PAGE_PARAMS();
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("cusbillway.field.code"), "code", false);
		API_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("cusbillway.field.name"), "name", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cus_sta_del", ZH_WORDS_GETTER("cusbillway.field.cus_sta_del"), "cus_sta_del", false);
	}
	ENDPOINT(API_M_GET, "/cost-config/customer-billing-way/query-customer-billing-way-page", queryCustomerBillingWayPage, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, CustomerBillingWayQuery, queryParams);
		API_HANDLER_RESP_VO(execQueryCustomerBillingWayPage(query));
	}

	// create
	ENDPOINT_INFO(addCustomerBillingWay) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("cusbillway.post.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	ENDPOINT(API_M_POST, "/cost-config/customer-billing-way/add-customer-billing-way", addCustomerBillingWay, BODY_DTO(CustomerBillingWayBaseAddDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		CustomerBillingWayAddDTO::Wrapper adto = buildFullDTO(dto, authObject.get()->getPayload());
		API_HANDLER_RESP_VO(execAddCustomerBillingWay(adto));
	}

	// update
	ENDPOINT_INFO(modifyCustomerBillingWay) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("cusbillway.put.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	ENDPOINT(API_M_PUT, "/cost-config/customer-billing-way/modify-customer-billing-way", modifyCustomerBillingWay, BODY_DTO(CustomerBillingWayBaseModifyDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		CustomerBillingWayModifyDTO::Wrapper mdto = buildFullDTO(dto, authObject.get()->getPayload());
		API_HANDLER_RESP_VO(execModifyCustomerBillingWay(mdto));
	}

	// batch delete
	ENDPOINT_INFO(deleteCustomerBillingWay) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("cusbillway.delete.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/cost-config/customer-billing-way/delete-customer-billing-way", deleteCustomerBillingWay, BODY_DTO(List<String>, ids), execDeleteCustomerBillingWay(ids));

	// export
	ENDPOINT_INFO(exportCustomerBillingWay) {
		API_DEF_ADD_AUTH();
		API_DEF_ADD_COMMON(ZH_WORDS_GETTER("cusbillway.export.summary"), Void);
	}
	ENDPOINT(API_M_GET, "/cost-config/customer-billing-way/export-customer-billing-way", exportCustomerBillingWay, API_HANDLER_AUTH_PARAME) {
		return execExportCustomerBillingWay();
	}

	// import
	ENDPOINT_INFO(importCustomerBillingWay) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("cusbillway.import.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_POST, "/cost-config/customer-billing-way/import-customer-billing-way", importCustomerBillingWay, REQUEST(std::shared_ptr<IncomingRequest>, request), execImportCustomerBillingWay(request, authObject->getPayload()));

private:
	StringJsonVO::Wrapper execAddCustomerBillingWay(const CustomerBillingWayAddDTO::Wrapper& dto);
	StringJsonVO::Wrapper execModifyCustomerBillingWay(const CustomerBillingWayModifyDTO::Wrapper& dto);
	CustomerBillingWayNameListPageJsonVO::Wrapper execQueryCustomerBillingWayName(const CustomerBillingWayQuery::Wrapper& query);
	CustomerBillingWayPageJsonVO::Wrapper execQueryCustomerBillingWayPage(const CustomerBillingWayQuery::Wrapper& query);
	StringJsonVO::Wrapper execDeleteCustomerBillingWay(const List<String>& ids);
	std::shared_ptr<OutgoingResponse> execExportCustomerBillingWay();
	StringJsonVO::Wrapper execImportCustomerBillingWay(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);

	CustomerBillingWayModifyDTO::Wrapper buildFullDTO(const CustomerBillingWayBaseModifyDTO::Wrapper& baseDto, const PayloadDTO& payload);
	CustomerBillingWayAddDTO::Wrapper buildFullDTO(const CustomerBillingWayBaseAddDTO::Wrapper& baseDto, const PayloadDTO& payload);
};

#include OATPP_CODEGEN_END(ApiController)
#endif // !_CUSTOMERBILLINGWAY_CONTROLLER_
