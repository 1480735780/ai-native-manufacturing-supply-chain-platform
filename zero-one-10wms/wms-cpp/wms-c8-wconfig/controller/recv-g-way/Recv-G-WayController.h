/*
 Copyright Zero One Star. All rights reserved.

 @Author: zero-one-star
 @Date: 2025/03/10 16:09:12

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
#ifndef _Recv_G_Way_CONTROLLER_
#define _Recv_G_Way_CONTROLLER_

#include "domain/GlobalInclude.h"
#include "domain/vo/BaseJsonVO.h"
#include "domain/vo/recv-g-way/Recv-G-Way-FileVo.h"
#include "domain/dto/recv-g-way/Recv-G-WayFileDto.h"
#include "domain/dto/recv-g-way/Recv-G-WayBatchDeleteDto.h"
#include "domain/query/recv-g-way/Recv-G-Way-FileQuery.h"
#include OATPP_CODEGEN_BEGIN(ApiController) ///< Begin ApiController codegen section

/**
 * 接货方式相关接口
 */
class Recv_G_WayController : public oatpp::web::server::api::ApiController {

	API_ACCESS_DECLARE(Recv_G_WayController);

public:
	// 接货方式删除接口
	ENDPOINT_INFO(DelRecv_G_Way) {
		// 定义标题和返回类型以及授权支持
		API_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("recv-g-way.delete.description"), Uint64JsonVO::Wrapper);
		// 定义其他路径参数说明
		API_DEF_ADD_PATH_PARAMS(String, "id", ZH_WORDS_GETTER("recv-g-way.file.id"), "1", true);
	}
	// 3.2 定义删除接口处理
	API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/wconfig/recv-g-way/{id}", DelRecv_G_Way, PATH(String, id), execDelRecv_G_Way(id));

	// 接货方式批量删除接口
	ENDPOINT_INFO(BatchDelRecv_G_Way) {
		// 定义标题和返回类型以及授权支持
		API_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("recv-g-way.batchDelete.summary"), Uint64JsonVO::Wrapper);
	}
	// 定义批量删除接口处理
	API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/wconfig/recv-g-way/batch-delete", BatchDelRecv_G_Way, BODY_DTO(Recv_G_WayBatchDeleteDto::Wrapper, dto), execBatchDelRecv_G_Way(dto));


	// 接货方式新增接口
	ENDPOINT_INFO(AddRecv_G_Way) {
		// 定义接口标题
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("recv-g-way.post.description"));
		// 定义默认授权参数（可选定义，如果定义了，下面ENDPOINT里面需要加入API_HANDLER_AUTH_PARAME）
		API_DEF_ADD_AUTH();
		// 定义响应参数格式
		API_DEF_ADD_RSP_JSON_WRAPPER(Uint64JsonVO);
	}
	ENDPOINT(API_M_POST, "/wconfig/recv-g-way", AddRecv_G_Way, BODY_DTO(Recv_G_WayAddDto::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		// 呼叫执行函数响应结果
		API_HANDLER_RESP_VO(execAddRecv_G_Way(dto, authObject->getPayload()));
	}

	// 3.1 定义修改接货方式接口
	API_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("recv-g-way.put.description"), EditRecv_G_Way, Uint64JsonVO::Wrapper);
	// 3.2 定义修改接货方式接口处理
	API_HANDLER_ENDPOINT_AUTH(API_M_PUT, "/wconfig/recv-g-way", EditRecv_G_Way, BODY_DTO(Recv_G_WayEditDto::Wrapper, dto), execEditRecv_G_Way(dto));




	//查询接货方式
	ENDPOINT_INFO(AllRecv_G_Way) {
		// 定义接口标题
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("recv-g-way.query-all.description"));
		// 定义默认授权参数（可选定义，如果定义了，下面ENDPOINT里面需要加入API_HANDLER_AUTH_PARAME）
		API_DEF_ADD_AUTH();
		// 定义响应参数格式
		API_DEF_ADD_RSP_JSON_WRAPPER(Recv_G_WayAllJsonVO);
		// 定义分页查询参数描述
		API_DEF_ADD_PAGE_PARAMS();
		// 定义其他查询参数描述
		API_DEF_ADD_QUERY_PARAMS(String, "del_mode_name", ZH_WORDS_GETTER("recv-g-way.file.del_mode_name"), "li ming", false);
		

	}
	ENDPOINT(API_M_GET, "/wconfig/recv-g-way", AllRecv_G_Way, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		// 解析查询参数为Query领域模型  
		API_HANDLER_QUERY_PARAM(Recv_G_WayQuery, Recv_G_WayQuery, queryParams);
		// 呼叫执行函数响应结果
		API_HANDLER_RESP_VO(execAllRecv_G_Way(Recv_G_WayQuery, authObject->getPayload()));
	}

	// 接货方式数据导入（Excel上传）
	// 定义描述
	API_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("recv-g-way-file.upload_f.description"), uploadRecv_G_WayFile, StringJsonVO::Wrapper);
	// 定义说明
	API_HANDLER_ENDPOINT_AUTH(API_M_POST, "/wconfig/recv-g-way-file/upload_f", uploadRecv_G_WayFile, REQUEST(std::shared_ptr<IncomingRequest>, request), execUploadRecv_G_Way(request, authObject->getPayload()));

	// 接货方式数据导出（Excel下载）
	// 定义描述
	ENDPOINT_INFO(downloadRecv_G_WayFile) {
		API_DEF_ADD_COMMON(ZH_WORDS_GETTER("recv-g-way-file.download_f.description"), Void);
		API_DEF_ADD_QUERY_PARAMS(String, "filename", ZH_WORDS_GETTER("recv-g-way-file.filed.filename"), "recv-g-way.xlsx", true);
	}
	// 定义说明
	ENDPOINT(API_M_GET, "/wconfig/recv-g-way-file/download_f", downloadRecv_G_WayFile, QUERY(String, filename)) {
		return execDownloadRecv_G_WayFile(filename);
	}


private:
	//删除
	Uint64JsonVO::Wrapper execDelRecv_G_Way(const String& id);
	//批量删除
	Uint64JsonVO::Wrapper execBatchDelRecv_G_Way(const Recv_G_WayBatchDeleteDto::Wrapper& dto);
	//修改
	Uint64JsonVO::Wrapper execEditRecv_G_Way(const Recv_G_WayEditDto::Wrapper& dto);
	//新增
	Uint64JsonVO::Wrapper execAddRecv_G_Way(const Recv_G_WayAddDto::Wrapper& dto, const PayloadDTO& payload);
	//查询
	Recv_G_WayAllJsonVO::Wrapper execAllRecv_G_Way(const Recv_G_WayQuery::Wrapper& query, const PayloadDTO& payload);
	
	// 执行接货方式数据导入
	StringJsonVO::Wrapper execUploadRecv_G_Way(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);

	// 执行接货方式数据导出
	std::shared_ptr<OutgoingResponse> execDownloadRecv_G_WayFile(const String& filename);
};

#include OATPP_CODEGEN_END(ApiController) ///< End ApiController codegen section

#endif // !_Recv_G_Way_CONTROLLER_
