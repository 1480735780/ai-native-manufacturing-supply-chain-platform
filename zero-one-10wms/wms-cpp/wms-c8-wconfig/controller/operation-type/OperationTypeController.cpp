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
#include "stdafx.h"
#include "OperationTypeController.h"
#include "../../service/operation-type/OperationTypeService.h"

//分页查询操作类型
OperationTypePageJsonVO::Wrapper OperationTypeController::execQueryAll(const OperationTypeQuery::Wrapper& query)
{
	// 定义一个Service
	OperationTypeService service;
	// 查询数据
	auto result = service.listAll(query);
	// 响应结果
	auto jvo = OperationTypePageJsonVO::createShared();
	jvo->success(result);
	return jvo;
}

//录入操作类型
Uint64JsonVO::Wrapper OperationTypeController::execAddOperationType(const OperationTypeAddDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	if (!dto->code || !dto->name)
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 有效值校验
	if (dto->code->empty() || dto->name->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 定义一个Service
	OperationTypeService service;
	// 执行数据新增
	uint64_t id = service.saveData(dto, payload.getUsername(), payload.getRealname(), payload.getOrgcode(), payload.getCompanycode());
	if (id > 0) {
		jvo->success(UInt64(id));
	}
	else
	{
		jvo->fail(UInt64(id));
	}
	// 响应结果
	return jvo;
}

//修改操作类型
Uint64JsonVO::Wrapper OperationTypeController::execModifyOperationType(const OperationTypeDTO::Wrapper& dto)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	if (!dto->id || dto->id->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 定义一个Service
	OperationTypeService service;
	// 执行数据修改
	if (service.updateData(dto)) {
		jvo->success(UInt64(1));
	}
	else
	{
		jvo->fail(UInt64(-1));
	}
	// 响应结果
	return jvo;
}

//删除操作类型
Uint64JsonVO::Wrapper OperationTypeController::execDeleteOperationType(const String& id)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	if (!id || id->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 定义一个Service
	OperationTypeService service;
	// 执行数据删除
	if (service.removeData(id->c_str())) {
		jvo->success(UInt64(1));
	}
	else
	{
		jvo->fail(UInt64(-1));
	}
	// 响应结果
	return jvo;
}

//批量删除操作类型
Uint64JsonVO::Wrapper OperationTypeController::execBatchDeleteOperationType(const OperationTypeBatchDeleteDto::Wrapper& dto)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	if (!dto->ids || dto->ids->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 定义一个Service
	OperationTypeService service;
	// 执行批量删除
	if (service.batchDeleteOperationType(dto)) {
		jvo->success(UInt64(dto->ids->size()));
	}
	else
	{
		jvo->fail(UInt64(-1));
	}
	// 响应结果
	return jvo;
}

//导入操作类型
StringJsonVO::Wrapper OperationTypeController::execImportOperationType(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	// 1 初始化
	API_MULTIPART_INIT(container, reader);

	// 2 配置读取器（把 file 字段整体读入内存）
	API_MULTIPART_CONFIG_MEMO(reader, "file", -1);

	// 3 读取数据
	request->transferBody(&reader);

	// 4 解析文件
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);
	if (!file)
	{
		// 5 响应结果
		auto jvo = StringJsonVO::createShared();
		jvo->fail("Parameter name must be file");
		return jvo;
	}

	// 5 执行导入
	OperationTypeService service;
	int result = service.importOperationType(file->data(), file->size(),
		payload.getUsername(), payload.getRealname(), payload.getOrgcode(), payload.getCompanycode());
	if (result == -1)
	{
		auto jvo = StringJsonVO::createShared();
		jvo->fail("error");
		return jvo;
	}
	auto jvo = StringJsonVO::createShared();
	jvo->success("success");
	return jvo;
}

//导出操作类型
std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> OperationTypeController::execExportOperationType(const String& filename)
{
	OperationTypeService service;
	auto buff = service.exportOperationType();
	if (buff.empty())
	{
		return createResponse(Status::CODE_404, "File Not Found");
	}
	// 构造响应内容
	string content((const char*)buff.data(), buff.size());
	// 创建响应头
	auto response = createResponse(Status::CODE_200, content);
	// 设置响应头信息
	response->putHeader("Content-Disposition", "attachment; filename=" + filename.getValue("operation-type.xlsx"));
	response->putHeader("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
	return response;
}
