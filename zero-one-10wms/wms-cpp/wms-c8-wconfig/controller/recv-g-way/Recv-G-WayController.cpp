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
#include "Recv-G-WayController.h"
#include "../../service/recv-g-way/Recv-G-WayService.h"
#include "../ApiDeclarativeServicesHelper.h"
//删除接货方式
Uint64JsonVO::Wrapper Recv_G_WayController::execDelRecv_G_Way(const String& id)
{
	auto jvo = Uint64JsonVO::createShared();
	Recv_G_WayService service;
	uint64_t Idd = service.removeData(id);
	if (Idd > 0) {
		jvo->success(UInt64(Idd));
	}
	else
	{
		jvo->fail(UInt64(Idd));
	}
	return jvo;
	// 定义返回数据对象
}
//批量删除接货方式
Uint64JsonVO::Wrapper Recv_G_WayController::execBatchDelRecv_G_Way(const Recv_G_WayBatchDeleteDto::Wrapper& dto)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	if (!dto->ids || dto->ids->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 调用一个Service
	Recv_G_WayService service;
	// 执行数据批量删除
	if (service.batchDeleteRecv_G_Way(dto)) {
		jvo->success(UInt64(dto->ids->size()));
	}
	else
	{
		jvo->fail(UInt64(-1));
	}
	// 响应结果
	return jvo;
}
//修改接货方式
Uint64JsonVO::Wrapper Recv_G_WayController::execEditRecv_G_Way(const Recv_G_WayEditDto::Wrapper& dto)
{
	auto jvo = Uint64JsonVO::createShared();
	dto->del_mode_code.getValue({});
	dto->del_mode_name.getValue({});
	dto->id.getValue({});
	// 参数校验
	if (!dto->id)
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 调用一个Service
	Recv_G_WayService service;
	uint64_t id = service.updateData(dto);
	// 执行数据修改
	if (id>0) {
		jvo->success(UInt64(id));
	}
	else
	{
		jvo->fail(UInt64(id));
	}
	// 响应结果
	return jvo;
}
//新增接货方式Recv_G_Way
Uint64JsonVO::Wrapper Recv_G_WayController::execAddRecv_G_Way(const Recv_G_WayAddDto::Wrapper& dto, const PayloadDTO& payload)
{
	// 定义返回数据对象

	auto jvo = Uint64JsonVO::createShared();
	dto->del_mode_code.getValue({});
	dto->del_mode_name.getValue({});
	
	string a = dto->del_mode_code;
	string b = dto->del_mode_name;
	// 参数校验
	// 强制校验
	if (!dto->del_mode_code || !dto->del_mode_name)
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 有效值校验
	if (dto->del_mode_code->empty() || dto->del_mode_name->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}

	// 调用一个Service
	Recv_G_WayService service;
	// 执行数据新增
	uint64_t id = service.saveData(dto, payload.getUsername(), payload.getRealname(), payload.getOrgcode(), payload.getCompanycode());
	if (id >0) {
		jvo->success(UInt64(id));
	}
	else
	{
		jvo->fail(UInt64(id));
	}
	//响应结果
	return jvo;
}
//查询接货方式
Recv_G_WayAllJsonVO::Wrapper Recv_G_WayController::execAllRecv_G_Way(const Recv_G_WayQuery::Wrapper& query, const PayloadDTO& payload)
{
	// 定义一个Service
	Recv_G_WayService service;
	// 查询数据
	auto result = service.listAll(query);
	// 响应结果
	auto jvo = Recv_G_WayAllJsonVO::createShared();
	jvo->success(result);
	return jvo;

}

//接货方式数据导入
StringJsonVO::Wrapper Recv_G_WayController::execUploadRecv_G_Way(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
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
	Recv_G_WayService service;
	int result = service.importRecv_G_Way(file->data(), file->size(),
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
//接货方式数据导出
std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> Recv_G_WayController::execDownloadRecv_G_WayFile(const String& filename)
{
	Recv_G_WayService service;
	auto buff = service.exportRecv_G_Way();
	if (buff.empty())
	{
		return createResponse(Status::CODE_404, "File Not Found");
	}
	// 构造响应内容
	string content((const char*)buff.data(), buff.size());
	// 创建响应头
	auto response = createResponse(Status::CODE_200, content);
	// 设置响应头信息
	response->putHeader("Content-Disposition", "attachment; filename=" + filename.getValue("recv-g-way.xlsx"));
	response->putHeader("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
	return response;
}
