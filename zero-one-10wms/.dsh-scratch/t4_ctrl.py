# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

R = "wms-cpp/wms-c8-wconfig/"

# ================= Controller.h =================
p = R + "controller/recv-g-way/Recv-G-WayController.h"
enc = detect(open(p, 'rb').read())
new_h = '''/*
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

\tAPI_ACCESS_DECLARE(Recv_G_WayController);

public:
\t// 接货方式删除接口
\tENDPOINT_INFO(DelRecv_G_Way) {
\t\t// 定义标题和返回类型以及授权支持
\t\tAPI_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("recv-g-way.delete.description"), Uint64JsonVO::Wrapper);
\t\t// 定义其他路径参数说明
\t\tAPI_DEF_ADD_PATH_PARAMS(String, "id", ZH_WORDS_GETTER("recv-g-way.file.id"), "1", true);
\t}
\t// 3.2 定义删除接口处理
\tAPI_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/wconfig/recv-g-way/{id}", DelRecv_G_Way, PATH(String, id), execDelRecv_G_Way(id));

\t// 接货方式批量删除接口
\tENDPOINT_INFO(BatchDelRecv_G_Way) {
\t\t// 定义标题和返回类型以及授权支持
\t\tAPI_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("recv-g-way.batchDelete.summary"), Uint64JsonVO::Wrapper);
\t}
\t// 定义批量删除接口处理
\tAPI_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/wconfig/recv-g-way/batch-delete", BatchDelRecv_G_Way, BODY_DTO(Recv_G_WayBatchDeleteDto::Wrapper, dto), execBatchDelRecv_G_Way(dto));


\t// 接货方式新增接口
\tENDPOINT_INFO(AddRecv_G_Way) {
\t\t// 定义接口标题
\t\tAPI_DEF_ADD_TITLE(ZH_WORDS_GETTER("recv-g-way.post.description"));
\t\t// 定义默认授权参数（可选定义，如果定义了，下面ENDPOINT里面需要加入API_HANDLER_AUTH_PARAME）
\t\tAPI_DEF_ADD_AUTH();
\t\t// 定义响应参数格式
\t\tAPI_DEF_ADD_RSP_JSON_WRAPPER(Uint64JsonVO);
\t}
\tENDPOINT(API_M_POST, "/wconfig/recv-g-way", AddRecv_G_Way, BODY_DTO(Recv_G_WayAddDto::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
\t\t// 呼叫执行函数响应结果
\t\tAPI_HANDLER_RESP_VO(execAddRecv_G_Way(dto, authObject->getPayload()));
\t}

\t// 3.1 定义修改接货方式接口
\tAPI_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("recv-g-way.put.description"), EditRecv_G_Way, Uint64JsonVO::Wrapper);
\t// 3.2 定义修改接货方式接口处理
\tAPI_HANDLER_ENDPOINT_AUTH(API_M_PUT, "/wconfig/recv-g-way", EditRecv_G_Way, BODY_DTO(Recv_G_WayEditDto::Wrapper, dto), execEditRecv_G_Way(dto));




\t//查询接货方式
\tENDPOINT_INFO(AllRecv_G_Way) {
\t\t// 定义接口标题
\t\tAPI_DEF_ADD_TITLE(ZH_WORDS_GETTER("recv-g-way.query-all.description"));
\t\t// 定义默认授权参数（可选定义，如果定义了，下面ENDPOINT里面需要加入API_HANDLER_AUTH_PARAME）
\t\tAPI_DEF_ADD_AUTH();
\t\t// 定义响应参数格式
\t\tAPI_DEF_ADD_RSP_JSON_WRAPPER(Recv_G_WayAllJsonVO);
\t\t// 定义分页查询参数描述
\t\tAPI_DEF_ADD_PAGE_PARAMS();
\t\t// 定义其他查询参数描述
\t\tAPI_DEF_ADD_QUERY_PARAMS(String, "del_mode_name", ZH_WORDS_GETTER("recv-g-way.file.del_mode_name"), "li ming", false);
\t\t

\t}
\tENDPOINT(API_M_GET, "/wconfig/recv-g-way", AllRecv_G_Way, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
\t\t// 解析查询参数为Query领域模型  
\t\tAPI_HANDLER_QUERY_PARAM(Recv_G_WayQuery, Recv_G_WayQuery, queryParams);
\t\t// 呼叫执行函数响应结果
\t\tAPI_HANDLER_RESP_VO(execAllRecv_G_Way(Recv_G_WayQuery, authObject->getPayload()));
\t}

\t// 接货方式数据导入（Excel上传）
\t// 定义描述
\tAPI_DEF_ENDPOINT_INFO(ZH_WORDS_GETTER("recv-g-way-file.upload_f.description"), uploadRecv_G_WayFile, StringJsonVO::Wrapper);
\t// 定义说明
\tAPI_HANDLER_ENDPOINT_AUTH(API_M_POST, "/wconfig/recv-g-way-file/upload_f", uploadRecv_G_WayFile, REQUEST(std::shared_ptr<IncomingRequest>, request), execUploadRecv_G_Way(request, authObject->getPayload()));

\t// 接货方式数据导出（Excel下载）
\t// 定义描述
\tENDPOINT_INFO(downloadRecv_G_WayFile) {
\t\tAPI_DEF_ADD_COMMON(ZH_WORDS_GETTER("recv-g-way-file.download_f.description"), Void);
\t\tAPI_DEF_ADD_QUERY_PARAMS(String, "filename", ZH_WORDS_GETTER("recv-g-way-file.filed.filename"), "recv-g-way.xlsx", true);
\t}
\t// 定义说明
\tENDPOINT(API_M_GET, "/wconfig/recv-g-way-file/download_f", downloadRecv_G_WayFile, QUERY(String, filename)) {
\t\treturn execDownloadRecv_G_WayFile(filename);
\t}


private:
\t//删除
\tUint64JsonVO::Wrapper execDelRecv_G_Way(const String& id);
\t//批量删除
\tUint64JsonVO::Wrapper execBatchDelRecv_G_Way(const Recv_G_WayBatchDeleteDto::Wrapper& dto);
\t//修改
\tUint64JsonVO::Wrapper execEditRecv_G_Way(const Recv_G_WayEditDto::Wrapper& dto);
\t//新增
\tUint64JsonVO::Wrapper execAddRecv_G_Way(const Recv_G_WayAddDto::Wrapper& dto, const PayloadDTO& payload);
\t//查询
\tRecv_G_WayAllJsonVO::Wrapper execAllRecv_G_Way(const Recv_G_WayQuery::Wrapper& query, const PayloadDTO& payload);
\t
\t// 执行接货方式数据导入
\tStringJsonVO::Wrapper execUploadRecv_G_Way(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);

\t// 执行接货方式数据导出
\tstd::shared_ptr<OutgoingResponse> execDownloadRecv_G_WayFile(const String& filename);
};

#include OATPP_CODEGEN_END(ApiController) ///< End ApiController codegen section

#endif // !_Recv_G_Way_CONTROLLER_
'''
open(p, 'wb').write(new_h.encode(enc))
print("Recv-G-WayController.h ->", enc)
