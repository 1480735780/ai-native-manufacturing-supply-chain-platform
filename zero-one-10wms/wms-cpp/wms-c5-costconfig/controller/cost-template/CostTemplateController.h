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

#ifndef _COSTTEMPLATE_CONTROLLER_
#define _COSTTEMPLATE_CONTROLLER_

#include "domain/vo/BaseJsonVO.h"
#include "domain/query/cost-template/CostTemplateQuery.h"
#include "domain/dto/cost-template/CostTemplateDTO.h"
#include "domain/vo/cost-template/CostTemplateVO.h"
#include "iostream"

#include OATPP_CODEGEN_BEGIN(ApiController)

/**
 * Cost Template
 */
class CostTemplateController : public oatpp::web::server::api::ApiController
{
	API_ACCESS_DECLARE(CostTemplateController);
public:

	// name list
	ENDPOINT_INFO(queryCostTemplateName) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("costtemplate.query-name.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(CostTemplateNameListPageJsonVO);
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("costtemplate.field.code"), "code", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_jg", ZH_WORDS_GETTER("costtemplate.field.cost_jg"), "cost_jg", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_sl", ZH_WORDS_GETTER("costtemplate.field.cost_sl"), "cost_sl", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_zk", ZH_WORDS_GETTER("costtemplate.field.cost_zk"), "cost_zk", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_bhs", ZH_WORDS_GETTER("costtemplate.field.cost_bhs"), "cost_bhs", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_hs", ZH_WORDS_GETTER("costtemplate.field.cost_hs"), "cost_hs", false);
		API_DEF_ADD_QUERY_PARAMS(String, "free_day", ZH_WORDS_GETTER("costtemplate.field.free_day"), "free_day", false);
		API_DEF_ADD_QUERY_PARAMS(String, "free_day2", ZH_WORDS_GETTER("costtemplate.field.free_day2"), "free_day2", false);
	}
	ENDPOINT(API_M_GET, "/cost-config/cost-template/query-cost-template-name", queryCostTemplateName, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, CostTemplateQuery, queryParams);
		API_HANDLER_RESP_VO(execQueryCostTemplateName(query));
	}

	// page list
	ENDPOINT_INFO(queryCostTemplatePage) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("costtemplate.query-page.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(CostTemplatePageJsonVO);
		API_DEF_ADD_PAGE_PARAMS();
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("costtemplate.field.code"), "code", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_jg", ZH_WORDS_GETTER("costtemplate.field.cost_jg"), "cost_jg", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_sl", ZH_WORDS_GETTER("costtemplate.field.cost_sl"), "cost_sl", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_zk", ZH_WORDS_GETTER("costtemplate.field.cost_zk"), "cost_zk", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_bhs", ZH_WORDS_GETTER("costtemplate.field.cost_bhs"), "cost_bhs", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cost_hs", ZH_WORDS_GETTER("costtemplate.field.cost_hs"), "cost_hs", false);
		API_DEF_ADD_QUERY_PARAMS(String, "free_day", ZH_WORDS_GETTER("costtemplate.field.free_day"), "free_day", false);
		API_DEF_ADD_QUERY_PARAMS(String, "free_day2", ZH_WORDS_GETTER("costtemplate.field.free_day2"), "free_day2", false);
	}
	ENDPOINT(API_M_GET, "/cost-config/cost-template/query-cost-template-page", queryCostTemplatePage, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		API_HANDLER_QUERY_PARAM(query, CostTemplateQuery, queryParams);
		API_HANDLER_RESP_VO(execQueryCostTemplatePage(query));
	}

	// create
	ENDPOINT_INFO(addCostTemplate) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("costtemplate.post.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	ENDPOINT(API_M_POST, "/cost-config/cost-template/add-cost-template", addCostTemplate, BODY_DTO(CostTemplateBaseAddDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		CostTemplateAddDTO::Wrapper adto = buildFullDTO(dto, authObject.get()->getPayload());
		API_HANDLER_RESP_VO(execAddCostTemplate(adto));
	}

	// update
	ENDPOINT_INFO(modifyCostTemplate) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("costtemplate.put.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	ENDPOINT(API_M_PUT, "/cost-config/cost-template/modify-cost-template", modifyCostTemplate, BODY_DTO(CostTemplateBaseModifyDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		CostTemplateModifyDTO::Wrapper mdto = buildFullDTO(dto, authObject.get()->getPayload());
		API_HANDLER_RESP_VO(execModifyCostTemplate(mdto));
	}

	// batch delete
	ENDPOINT_INFO(deleteCostTemplate) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("costtemplate.delete.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/cost-config/cost-template/delete-cost-template", deleteCostTemplate, BODY_DTO(List<String>, ids), execDeleteCostTemplate(ids));

	// export
	ENDPOINT_INFO(exportCostTemplate) {
		API_DEF_ADD_AUTH();
		API_DEF_ADD_COMMON(ZH_WORDS_GETTER("costtemplate.export.summary"), Void);
	}
	ENDPOINT(API_M_GET, "/cost-config/cost-template/export-cost-template", exportCostTemplate, API_HANDLER_AUTH_PARAME) {
		return execExportCostTemplate();
	}

	// import
	ENDPOINT_INFO(importCostTemplate) {
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("costtemplate.import.summary"));
		API_DEF_ADD_AUTH();
		API_DEF_ADD_RSP_JSON_WRAPPER(StringJsonVO);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_POST, "/cost-config/cost-template/import-cost-template", importCostTemplate, REQUEST(std::shared_ptr<IncomingRequest>, request), execImportCostTemplate(request, authObject->getPayload()));

private:
	StringJsonVO::Wrapper execAddCostTemplate(const CostTemplateAddDTO::Wrapper& dto);
	StringJsonVO::Wrapper execModifyCostTemplate(const CostTemplateModifyDTO::Wrapper& dto);
	CostTemplateNameListPageJsonVO::Wrapper execQueryCostTemplateName(const CostTemplateQuery::Wrapper& query);
	CostTemplatePageJsonVO::Wrapper execQueryCostTemplatePage(const CostTemplateQuery::Wrapper& query);
	StringJsonVO::Wrapper execDeleteCostTemplate(const List<String>& ids);
	std::shared_ptr<OutgoingResponse> execExportCostTemplate();
	StringJsonVO::Wrapper execImportCostTemplate(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);

	CostTemplateModifyDTO::Wrapper buildFullDTO(const CostTemplateBaseModifyDTO::Wrapper& baseDto, const PayloadDTO& payload);
	CostTemplateAddDTO::Wrapper buildFullDTO(const CostTemplateBaseAddDTO::Wrapper& baseDto, const PayloadDTO& payload);
};

#include OATPP_CODEGEN_END(ApiController)
#endif // !_COSTTEMPLATE_CONTROLLER_
