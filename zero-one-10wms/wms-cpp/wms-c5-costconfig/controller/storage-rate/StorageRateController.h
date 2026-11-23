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

#ifndef _STORAGERATE_CONTROLLER_
#define _STORAGERATE_CONTROLLER_

#include "domain/vo/BaseJsonVO.h"
#include "domain/query/storage-rate/StorageRateQuery.h"
#include "domain/dto/storage-rate/StorageRateDTO.h"
#include "domain/vo/storage-rate/StorageRateVO.h"
#include "iostream"

#include OATPP_CODEGEN_BEGIN(ApiController)

/**
 * Storage Rate
 */
class StorageRateController : public oatpp::web::server::api::ApiController
{
	API_ACCESS_DECLARE(StorageRateController);
public:

	// name list
	ENDPOINT_INFO(queryStorageRateName) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("storagerate.query-name.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StorageRateNameListPageJsonVO);
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("storagerate.field.code"), "code", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_yj", ZH_WORDS_GETTER("storagerate.field.cost_yj"), "cost_yj", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_zk", ZH_WORDS_GETTER("storagerate.field.cost_zk"), "cost_zk", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_sl", ZH_WORDS_GETTER("storagerate.field.cost_sl"), "cost_sl", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_bhs", ZH_WORDS_GETTER("storagerate.field.cost_bhs"), "cost_bhs", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_hsj", ZH_WORDS_GETTER("storagerate.field.cost_hsj"), "cost_hsj", false);
	}
	ENDPOINT(API_M_GET, "/cost-config/storage-rate/query-storage-rate-name", queryStorageRateName, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, StorageRateQuery, queryParams);
		API_HANDLER_RESP_VO(execQueryStorageRateName(query));
	}

	// page list
	ENDPOINT_INFO(queryStorageRatePage) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("storagerate.query-page.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StorageRatePageJsonVO);
		API_DEF_ADD_PAGE_PARAMS();
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("storagerate.field.code"), "code", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_yj", ZH_WORDS_GETTER("storagerate.field.cost_yj"), "cost_yj", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_zk", ZH_WORDS_GETTER("storagerate.field.cost_zk"), "cost_zk", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_sl", ZH_WORDS_GETTER("storagerate.field.cost_sl"), "cost_sl", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_bhs", ZH_WORDS_GETTER("storagerate.field.cost_bhs"), "cost_bhs", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_hsj", ZH_WORDS_GETTER("storagerate.field.cost_hsj"), "cost_hsj", false);
	}
	ENDPOINT(API_M_GET, "/cost-config/storage-rate/query-storage-rate-page", queryStorageRatePage, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, StorageRateQuery, queryParams);
		API_HANDLER_RESP_VO(execQueryStorageRatePage(query));
	}

	// detail
	ENDPOINT_INFO(queryStorageRateDetail) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("storagerate.detail.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StorageRateDetailJsonVO);
		API_DEF_ADD_QUERY_PARAMS(String, "id", ZH_WORDS_GETTER("storagerate.field.id"), "id", true);
	}
	ENDPOINT(API_M_GET, "/cost-config/storage-rate/query-storage-rate-detail", queryStorageRateDetail, QUERY(String, id), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_RESP_VO(execQueryStorageRateDetail(id));
	}

	// create
	ENDPOINT_INFO(addStorageRate) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("storagerate.post.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	ENDPOINT(API_M_POST, "/cost-config/storage-rate/add-storage-rate", addStorageRate, BODY_DTO(StorageRateBaseAddDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		StorageRateAddDTO::Wrapper adto = buildFullDTO(dto, authObject.get()->getPayload());
		API_HANDLER_RESP_VO(execAddStorageRate(adto));
	}

	// update
	ENDPOINT_INFO(modifyStorageRate) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("storagerate.put.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	ENDPOINT(API_M_PUT, "/cost-config/storage-rate/modify-storage-rate", modifyStorageRate, BODY_DTO(StorageRateBaseModifyDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		StorageRateModifyDTO::Wrapper mdto = buildFullDTO(dto, authObject.get()->getPayload());
		API_HANDLER_RESP_VO(execModifyStorageRate(mdto));
	}

	// batch delete
	ENDPOINT_INFO(deleteStorageRate) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("storagerate.delete.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/cost-config/storage-rate/delete-storage-rate", deleteStorageRate, BODY_DTO(List<String>, ids), execDeleteStorageRate(ids));

	// export
	ENDPOINT_INFO(exportStorageRate) {
		API_DEF_ADD_AUTH();
		API_DEF_ADD_COMMON(ZH_WORDS_GETTER("storagerate.export.summary"), Void);
	}
	ENDPOINT(API_M_GET, "/cost-config/storage-rate/export-storage-rate", exportStorageRate, API_HANDLER_AUTH_PARAME) {
		return execExportStorageRate();
	}

	// import
	ENDPOINT_INFO(importStorageRate) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("storagerate.import.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_POST, "/cost-config/storage-rate/import-storage-rate", importStorageRate, REQUEST(std::shared_ptr<IncomingRequest>, request), execImportStorageRate(request, authObject->getPayload()));

private:
	StringJsonVO::Wrapper execAddStorageRate(const StorageRateAddDTO::Wrapper& dto);
	StringJsonVO::Wrapper execModifyStorageRate(const StorageRateModifyDTO::Wrapper& dto);
	StorageRateNameListPageJsonVO::Wrapper execQueryStorageRateName(const StorageRateQuery::Wrapper& query);
	StorageRatePageJsonVO::Wrapper execQueryStorageRatePage(const StorageRateQuery::Wrapper& query);
	StorageRateDetailJsonVO::Wrapper execQueryStorageRateDetail(const String& id);
	StringJsonVO::Wrapper execDeleteStorageRate(const List<String>& ids);
	std::shared_ptr<OutgoingResponse> execExportStorageRate();
	StringJsonVO::Wrapper execImportStorageRate(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);

	StorageRateModifyDTO::Wrapper buildFullDTO(const StorageRateBaseModifyDTO::Wrapper& baseDto, const PayloadDTO& payload);
	StorageRateAddDTO::Wrapper buildFullDTO(const StorageRateBaseAddDTO::Wrapper& baseDto, const PayloadDTO& payload);
};

#include OATPP_CODEGEN_END(ApiController)
#endif // !_STORAGERATE_CONTROLLER_
