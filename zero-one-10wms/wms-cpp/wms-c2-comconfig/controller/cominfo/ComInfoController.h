#pragma once

#ifndef _COMPANY_INFORMATION_CONTROLLER_
#define _COMPANY_INFORMATION_CONTROLLER_

#include "domain/GlobalInclude.h"
#include "domain/vo/BaseJsonVO.h"
#include "domain/query/PageQuery.h" 
#include "ExcelComponent.h"
#include "FastDfsClient.h"
#include "ApiHelper.h"
#include "ServerInfo.h"

#include OATPP_CODEGEN_BEGIN(ApiController) ///< Begin ApiController codegen section

/*
* 导入和导出公司信息
*/

class ComInfoController : public oatpp::web::server::api::ApiController {
	// 定义控制器访问入口
	API_ACCESS_DECLARE(ComInfoController);
public:
	// 导入企业信息
	ENDPOINT_INFO(importCompanyInfo) {
		API_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("comconfig.cominfo.import"), StringJsonVO::Wrapper);
	}
	API_HANDLER_ENDPOINT_AUTH(API_M_POST, "/cominfo/upload-cominfo", importCompanyInfo, REQUEST(std::shared_ptr<IncomingRequest>, request), execInputComInfo(request, authObject->getPayload()));

	// 导出企业信息
	ENDPOINT_INFO(exportCompanyInfo) {
		API_DEF_ADD_COMMON(ZH_WORDS_GETTER("comconfig.cominfo.export"), Void);
		API_DEF_ADD_QUERY_PARAMS(String, "filename", ZH_WORDS_GETTER("comconfig.file.filename"), "file.xlsx", true);
	}
	ENDPOINT(API_M_GET, "/cominfo/download-cominfo", exportCompanyInfo, QUERY(String, filename)) {
		return execOutputComInfo(filename);
	}
private:
	// 导入企业信息
	StringJsonVO::Wrapper execInputComInfo(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);

	// 导出企业信息
	std::shared_ptr<OutgoingResponse> execOutputComInfo(const String& filename);
};

#include OATPP_CODEGEN_END(ApiController) ///< End ApiController codegen section

#endif // !_COMPANY_INFORMATION_CONTROLLER_
