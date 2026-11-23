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
#ifndef _OPERATION_TYPE_CONTROLLER_
#define _OPERATION_TYPE_CONTROLLER_

#include "domain/GlobalInclude.h"
#include "domain/vo/BaseJsonVO.h"
#include "domain/vo/operation-type/OperationTypeVO.h"
#include "domain/dto/operation-type/OperationTypeDTO.h"
#include "domain/dto/operation-type/OperationTypeBatchDeleteDto.h"
#include "domain/query/operation-type/OperationTypeQuery.h"
#include OATPP_CODEGEN_BEGIN(ApiController) ///< Begin ApiController codegen section

/**
 * 操作类型相关接口
 */
class OperationTypeController : public oatpp::web::server::api::ApiController {

	API_ACCESS_DECLARE(OperationTypeController);

public:
	// 查询操作类型（分页+条件）
	ENDPOINT_INFO(queryAll) {
		// 定义接口标题
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("op.query-all.summary"));
		// 定义默认授权参数（可选定义，如果定义了，下面ENDPOINT里面需要加入API_HANDLER_AUTH_PARAME）
		API_DEF_ADD_AUTH();
		// 定义响应参数格式
		API_DEF_ADD_RSP_JSON_WRAPPER(OperationTypePageJsonVO);
		// 定义分页查询参数描述
		API_DEF_ADD_PAGE_PARAMS();
		// 定义其他查询参数描述
		API_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("op.field.code"), "OPER", false);
		API_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("op.field.name"), "test", false);
	}
	// 查询接口处理
	ENDPOINT(API_M_GET, "/wconfig/operation-type", queryAll, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		// 解析查询参数为Query领域模型
		API_HANDLER_QUERY_PARAM(query, OperationTypeQuery, queryParams);
		// 呼叫执行函数响应结果
		API_HANDLER_RESP_VO(execQueryAll(query));
	}

	// 录入操作类型
	ENDPOINT_INFO(addOperationType) {
		// 定义接口标题
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("op.post.summary"));
		// 定义默认授权参数
		API_DEF_ADD_AUTH();
		// 定义响应参数格式
		API_DEF_ADD_RSP_JSON_WRAPPER(Uint64JsonVO);
	}
	// 录入接口处理
	ENDPOINT(API_M_POST, "/wconfig/operation-type", addOperationType, BODY_DTO(OperationTypeAddDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
		// 呼叫执行函数响应结果
		API_HANDLER_RESP_VO(execAddOperationType(dto, authObject->getPayload()));
	}

	// 修改操作类型
	API_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("op.modify.summary"), modifyOperationType, Uint64JsonVO::Wrapper);
	// 修改接口处理
	API_HANDLER_ENDPOINT_AUTH(API_M_PUT, "/wconfig/operation-type", modifyOperationType, BODY_DTO(OperationTypeDTO::Wrapper, dto), execModifyOperationType(dto));

	// 删除操作类型
	ENDPOINT_INFO(deleteOperationType) {
		// 定义标题和返回类型以及授权支持
		API_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("op.delete.summary"), Uint64JsonVO::Wrapper);
		// 定义路径参数说明
		API_DEF_ADD_PATH_PARAMS(String, "id", ZH_WORDS_GETTER("op.field.id"), "1", true);
	}
	// 删除接口处理
	API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/wconfig/operation-type/{id}", deleteOperationType, PATH(String, id), execDeleteOperationType(id));

	// 批量删除操作类型
	ENDPOINT_INFO(batchDeleteOperationType) {
		// 定义标题和返回类型以及授权支持
		API_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("op.batchDelete.summary"), Uint64JsonVO::Wrapper);
	}
	// 批量删除接口处理
	API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/wconfig/operation-type/batch-delete", batchDeleteOperationType, BODY_DTO(OperationTypeBatchDeleteDto::Wrapper, dto), execBatchDeleteOperationType(dto));

	// 导入操作类型（Excel上传）
	API_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("op.import.summary"), importOperationType, StringJsonVO::Wrapper);
	// 导入接口处理
	API_HANDLER_ENDPOINT_AUTH(API_M_POST, "/wconfig/operation-type/import", importOperationType, REQUEST(std::shared_ptr<IncomingRequest>, request), execImportOperationType(request, authObject->getPayload()));

	// 导出操作类型（Excel下载）
	ENDPOINT_INFO(exportOperationType) {
		API_DEF_ADD_COMMON(ZH_WORDS_GETTER("op.export.summary"), Void);
		API_DEF_ADD_QUERY_PARAMS(String, "filename", ZH_WORDS_GETTER("recv-g-way-file.filed.filename"), "operation-type.xlsx", true);
	}
	// 导出接口处理
	ENDPOINT(API_M_GET, "/wconfig/operation-type/export", exportOperationType, QUERY(String, filename)) {
		return execExportOperationType(filename);
	}

private:
	// 分页查询
	OperationTypePageJsonVO::Wrapper execQueryAll(const OperationTypeQuery::Wrapper& query);
	// 录入
	Uint64JsonVO::Wrapper execAddOperationType(const OperationTypeAddDTO::Wrapper& dto, const PayloadDTO& payload);
	// 修改
	Uint64JsonVO::Wrapper execModifyOperationType(const OperationTypeDTO::Wrapper& dto);
	// 删除
	Uint64JsonVO::Wrapper execDeleteOperationType(const String& id);
	// 批量删除
	Uint64JsonVO::Wrapper execBatchDeleteOperationType(const OperationTypeBatchDeleteDto::Wrapper& dto);
	// 导入
	StringJsonVO::Wrapper execImportOperationType(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);
	// 导出
	std::shared_ptr<OutgoingResponse> execExportOperationType(const String& filename);
};

#include OATPP_CODEGEN_END(ApiController) ///< End ApiController codegen section

#endif // !_OPERATION_TYPE_CONTROLLER_
