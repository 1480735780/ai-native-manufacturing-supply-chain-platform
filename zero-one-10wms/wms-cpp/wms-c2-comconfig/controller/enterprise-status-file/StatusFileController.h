#pragma once
#ifndef _STATUSFILECONTROLLER_H_
#define _STATUSFILECONTROLLER_H_

#include "domain/vo/BaseJsonVO.h"
#include "ApiHelper.h"
#include "ServerInfo.h"

#include OATPP_CODEGEN_BEGIN(ApiController)

/**
 * 文件操作示例接口
 */
class StatusFileController : public oatpp::web::server::api::ApiController
{
	// 定义控制器访问入口
	API_ACCESS_DECLARE(StatusFileController);
public:

	// **导入企业状态**
	// 定义描述
	ENDPOINT_INFO(uploadFileMore) {
		API_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("file.upload-more.status-summary"), Void);
	}
	// 定义端点（multipart 文件直传，与其他导入接口统一模式）
	API_HANDLER_ENDPOINT_AUTH(API_M_POST, "/entstat/upload-file", uploadFileMore, REQUEST(std::shared_ptr<IncomingRequest>, request), execUploadMore(request, authObject->getPayload()));



	// 定义一个文件下载接口
	// 定义描述
	ENDPOINT_INFO(downloadFile) {
		API_DEF_ADD_COMMON(ZH_WORDS_GETTER("file.download.summary"), Void);
		API_DEF_ADD_QUERY_PARAMS(String, "filename", ZH_WORDS_GETTER("file.field.filename"), "file/test.xlsx", true);
	}
	// 定义端点
	ENDPOINT(API_M_GET, "/entstat/download-file", downloadFile, QUERY(String, filename)) {
		return execDownloadFile(filename);
	}

private: // 定义接口执行函数
	// 执行文件上传导入（multipart 直传 excel 文件）
	StringJsonVO::Wrapper execUploadMore(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);
	// 执行文件下载处理
	std::shared_ptr<OutgoingResponse> execDownloadFile(const String& filename);
};

#include OATPP_CODEGEN_END(ApiController)

#endif // !_STATUSFILECONTROLLER_H_