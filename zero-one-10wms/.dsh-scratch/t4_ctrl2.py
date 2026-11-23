# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

R = "wms-cpp/wms-c8-wconfig/"
p = R + "controller/recv-g-way/Recv-G-WayController.cpp"
enc = detect(open(p, 'rb').read())
new_cpp = '''/*
 Copyright Zero One Star. All rights reserved.

 @Author: zero-one-star
 @Date: 2025/03/10 16:09:12

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

\t  https://www.apache.org/licenses/LICENSE-2.0

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
\tauto jvo = Uint64JsonVO::createShared();
\tRecv_G_WayService service;
\tuint64_t Idd = service.removeData(id);
\tif (Idd > 0) {
\t\tjvo->success(UInt64(Idd));
\t}
\telse
\t{
\t\tjvo->fail(UInt64(Idd));
\t}
\treturn jvo;
\t// 定义返回数据对象
}
//批量删除接货方式
Uint64JsonVO::Wrapper Recv_G_WayController::execBatchDelRecv_G_Way(const Recv_G_WayBatchDeleteDto::Wrapper& dto)
{
\t// 定义返回数据对象
\tauto jvo = Uint64JsonVO::createShared();
\t// 参数校验
\tif (!dto->ids || dto->ids->empty())
\t{
\t\tjvo->init(UInt64(-1), RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\t// 调用一个Service
\tRecv_G_WayService service;
\t// 执行数据批量删除
\tif (service.batchDeleteRecv_G_Way(dto)) {
\t\tjvo->success(UInt64(dto->ids->size()));
\t}
\telse
\t{
\t\tjvo->fail(UInt64(-1));
\t}
\t// 响应结果
\treturn jvo;
}
//修改接货方式
Uint64JsonVO::Wrapper Recv_G_WayController::execEditRecv_G_Way(const Recv_G_WayEditDto::Wrapper& dto)
{
\tauto jvo = Uint64JsonVO::createShared();
\tdto->del_mode_code.getValue({});
\tdto->del_mode_name.getValue({});
\tdto->id.getValue({});
\t// 参数校验
\tif (!dto->id)
\t{
\t\tjvo->init(UInt64(-1), RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\t// 调用一个Service
\tRecv_G_WayService service;
\tuint64_t id = service.updateData(dto);
\t// 执行数据修改
\tif (id>0) {
\t\tjvo->success(UInt64(id));
\t}
\telse
\t{
\t\tjvo->fail(UInt64(id));
\t}
\t// 响应结果
\treturn jvo;
}
//新增接货方式Recv_G_Way
Uint64JsonVO::Wrapper Recv_G_WayController::execAddRecv_G_Way(const Recv_G_WayAddDto::Wrapper& dto, const PayloadDTO& payload)
{
\t// 定义返回数据对象

\tauto jvo = Uint64JsonVO::createShared();
\tdto->del_mode_code.getValue({});
\tdto->del_mode_name.getValue({});
\t
\tstring a = dto->del_mode_code;
\tstring b = dto->del_mode_name;
\t// 参数校验
\t// 强制校验
\tif (!dto->del_mode_code || !dto->del_mode_name)
\t{
\t\tjvo->init(UInt64(-1), RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\t// 有效值校验
\tif (dto->del_mode_code->empty() || dto->del_mode_name->empty())
\t{
\t\tjvo->init(UInt64(-1), RS_PARAMS_INVALID);
\t\treturn jvo;
\t}

\t// 调用一个Service
\tRecv_G_WayService service;
\t// 执行数据新增
\tuint64_t id = service.saveData(dto, payload.getUsername(), payload.getRealname(), payload.getOrgcode(), payload.getCompanycode());
\tif (id >0) {
\t\tjvo->success(UInt64(id));
\t}
\telse
\t{
\t\tjvo->fail(UInt64(id));
\t}
\t//响应结果
\treturn jvo;
}
//查询接货方式
Recv_G_WayAllJsonVO::Wrapper Recv_G_WayController::execAllRecv_G_Way(const Recv_G_WayQuery::Wrapper& query, const PayloadDTO& payload)
{
\t// 定义一个Service
\tRecv_G_WayService service;
\t// 查询数据
\tauto result = service.listAll(query);
\t// 响应结果
\tauto jvo = Recv_G_WayAllJsonVO::createShared();
\tjvo->success(result);
\treturn jvo;

}

//接货方式数据导入
StringJsonVO::Wrapper Recv_G_WayController::execUploadRecv_G_Way(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
\t// 1 初始化
\tAPI_MULTIPART_INIT(container, reader);

\t// 2 配置读取器（把 file 字段整体读入内存）
\tAPI_MULTIPART_CONFIG_MEMO(reader, "file", -1);

\t// 3 读取数据
\trequest->transferBody(&reader);

\t// 4 解析文件
\tAPI_MULTIPART_PARSE_FILE_FIELD(container, "file", file);
\tif (!file)
\t{
\t\t// 5 响应结果
\t\tauto jvo = StringJsonVO::createShared();
\t\tjvo->fail("Parameter name must be file");
\t\treturn jvo;
\t}

\t// 5 执行导入
\tRecv_G_WayService service;
\tint result = service.importRecv_G_Way(file->data(), file->size(),
\t\tpayload.getUsername(), payload.getRealname(), payload.getOrgcode(), payload.getCompanycode());
\tif (result == -1)
\t{
\t\tauto jvo = StringJsonVO::createShared();
\t\tjvo->fail("error");
\t\treturn jvo;
\t}
\tauto jvo = StringJsonVO::createShared();
\tjvo->success("success");
\treturn jvo;
}
//接货方式数据导出
std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> Recv_G_WayController::execDownloadRecv_G_WayFile(const String& filename)
{
\tRecv_G_WayService service;
\tauto buff = service.exportRecv_G_Way();
\tif (buff.empty())
\t{
\t\treturn createResponse(Status::CODE_404, "File Not Found");
\t}
\t// 构造响应内容
\tstring content((const char*)buff.data(), buff.size());
\t// 创建响应头
\tauto response = createResponse(Status::CODE_200, content);
\t// 设置响应头信息
\tresponse->putHeader("Content-Disposition", "attachment; filename=" + filename.getValue("recv-g-way.xlsx"));
\tresponse->putHeader("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
\treturn response;
}
'''
open(p, 'wb').write(new_cpp.encode(enc))
print("Recv-G-WayController.cpp ->", enc)
