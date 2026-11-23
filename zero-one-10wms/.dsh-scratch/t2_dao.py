# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, '.dsh-scratch')
R = "wms-cpp/wms-c8-wconfig/"

LICENSE = '''/*
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
'''

files = {}

files["dao/operation-type/OperationTypeMapper.h"] = LICENSE + '''#ifndef _OPERATION_TYPE_MAPPER_
#define _OPERATION_TYPE_MAPPER_

#include "Mapper.h"
#include "../../domain/do/operation-type/OperationTypeDO.h"

/**
 * 操作类型字段匹配映射
 */
class OperationTypeMapper : public Mapper<OperationTypeDO>
{
public:
\tOperationTypeDO mapper(ResultSet* resultSet) const override
\t{
\t\tOperationTypeDO data;
\t\tdata.setId(resultSet->getString(1));
\t\tdata.setCode(resultSet->getString(2));
\t\tdata.setName(resultSet->getString(3));
\t\treturn data;
\t}
};

/**
 * 操作类型字段匹配映射-关联智能指针类型
 */
class PtrOperationTypeMapper : public Mapper<PtrOperationTypeDO>
{
public:
\tPtrOperationTypeDO mapper(ResultSet* resultSet) const override
\t{
\t\tauto data = std::make_shared<OperationTypeDO>();
\t\tdata->setId(resultSet->getString(1));
\t\tdata->setCode(resultSet->getString(2));
\t\tdata->setName(resultSet->getString(3));
\t\treturn data;
\t}
};

#endif // !_OPERATION_TYPE_MAPPER_
'''

files["dao/operation-type/OperationTypeDAO.h"] = LICENSE + '''#ifndef _OPERATION_TYPE_DAO_
#define _OPERATION_TYPE_DAO_
#include "BaseDAO.h"
#include "../../domain/do/operation-type/OperationTypeDO.h"
#include "../../domain/query/operation-type/OperationTypeQuery.h"
#include "../../domain/dto/operation-type/OperationTypeBatchDeleteDto.h"

/**
 * 操作类型数据访问实现
 */
class OperationTypeDAO : public BaseDAO
{
private:
\t//************************************
\t// Method:      queryConditionBuilder
\t// FullName:    OperationTypeDAO::queryConditionBuilder
\t// Access:      private
\t// Returns:     std::string 返回条件SQL语句，即WHERE部分的语句
\t// Parameter:   const OperationTypeQuery::Wrapper& query 查询数据对象
\t// Parameter:   SqlParams& params 存放查询数据的参数对象
\t// Description: 查询条件构建器，根据OperationTypeQuery对象动态构建查询条件相关参数
\t//************************************
\tinline std::string queryConditionBuilder(const OperationTypeQuery::Wrapper& query, SqlParams& params);
\tstd::string getCurrentDateTime();
public:
\t// 统计数据条数
\tuint64_t count(const OperationTypeQuery::Wrapper& query);
\t// 分页查询数据
\tstd::list<OperationTypeDO> selectWithPage(const OperationTypeQuery::Wrapper& query);
\t// 查询全部数据（供导出使用）
\tstd::list<OperationTypeDO> selectAll();
\t// 插入数据（带审计信息，主键由后端生成）
\tint insert(const OperationTypeDO& iObj, string name, string realname, string orgcode, string companycode);
\t// 修改数据
\tint update(const OperationTypeDO& uObj);
\t// 通过ID删除数据
\tint deleteById(string id);
\t// 批量删除数据
\tint batchDelete(const OperationTypeBatchDeleteDto::Wrapper& dto);
};
#endif // !_OPERATION_TYPE_DAO_
'''

files["dao/operation-type/OperationTypeDAO.cpp"] = LICENSE + '''#include "stdafx.h"
#include "OperationTypeDAO.h"
#include "OperationTypeMapper.h"
#include "../../lib-common/include/id/UuidFacade.h"
#include <sstream>


inline std::string OperationTypeDAO::queryConditionBuilder(const OperationTypeQuery::Wrapper& query, SqlParams& params)
{
\tstringstream sqlCondition;
\tsqlCondition << " WHERE 1=1";
\tif (query->code) {
\t\tsqlCondition << " AND `oper_type_code`=?";
\t\tSQLPARAMS_PUSH(params, "s", std::string, query->code.getValue(""));
\t}
\tif (query->name) {
\t\tsqlCondition << " AND `oper_type_name`=?";
\t\tSQLPARAMS_PUSH(params, "s", std::string, query->name.getValue(""));
\t}
\treturn sqlCondition.str();
}

uint64_t OperationTypeDAO::count(const OperationTypeQuery::Wrapper& query)
{
\tSqlParams params;
\tstring sql = "SELECT COUNT(*) FROM `ba_oper_type` ";
\tsql += queryConditionBuilder(query, params);
\treturn sqlSession->executeQueryNumerical(sql, params);
}

std::list<OperationTypeDO> OperationTypeDAO::selectWithPage(const OperationTypeQuery::Wrapper& query)
{
\tSqlParams params;
\tstring sql = "SELECT id,oper_type_code,oper_type_name FROM `ba_oper_type` ";
\tsql += queryConditionBuilder(query, params);
\tsql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
\tOperationTypeMapper mapper;
\treturn sqlSession->executeQuery<OperationTypeDO>(sql, mapper, params);
}

std::list<OperationTypeDO> OperationTypeDAO::selectAll()
{
\tstring sql = "SELECT id,oper_type_code,oper_type_name FROM `ba_oper_type` ";
\tOperationTypeMapper mapper;
\treturn sqlSession->executeQuery<OperationTypeDO>(sql, mapper);
}

int OperationTypeDAO::insert(const OperationTypeDO& iObj, string name, string realname, string orgcode, string companycode)
{
\tstd::string currentTime = getCurrentDateTime();
\tUuidFacade uf(1);
\tstd::string id = uf.genUuid();
\tstring sql = "INSERT INTO `ba_oper_type` (`id`,`create_name`, `create_by`, `create_date`, `sys_org_code`,`sys_company_code`, `oper_type_code`, `oper_type_name`) VALUES (?,?,?,?,?,?,?,?)";
\treturn sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s%s", id, name, realname, currentTime, orgcode, companycode, iObj.getCode(), iObj.getName());
}

int OperationTypeDAO::update(const OperationTypeDO& uObj)
{
\tstd::string currentTime = getCurrentDateTime();
\tstring sql = "UPDATE `ba_oper_type` SET `update_date`=?,`oper_type_code`=?,`oper_type_name`=? WHERE `id`=?";
\treturn sqlSession->executeUpdate(sql, "%s%s%s%s", currentTime, uObj.getCode(), uObj.getName(), uObj.getId());
}

int OperationTypeDAO::deleteById(string id)
{
\tstring sql = "DELETE FROM `ba_oper_type` WHERE `id`=?";
\treturn sqlSession->executeUpdate(sql, "%s", id);
}

int OperationTypeDAO::batchDelete(const OperationTypeBatchDeleteDto::Wrapper& dto)
{
\tif (!dto->ids || dto->ids->empty())
\t{
\t\treturn 0;
\t}
\t// 使用参数化查询，避免拼接字符串带来的注入风险
\tSqlParams params;
\tstring sql = "DELETE FROM `ba_oper_type` WHERE `id` IN (";
\tfor (auto it = dto->ids->begin(); it != dto->ids->end(); ++it)
\t{
\t\tif (it != dto->ids->begin())
\t\t{
\t\t\tsql += ", ";
\t\t}
\t\tsql += "?";
\t\tSQLPARAMS_PUSH(params, "s", std::string, it->getValue(""));
\t}
\tsql += ")";
\treturn sqlSession->executeUpdate(sql, params);
}

std::string OperationTypeDAO::getCurrentDateTime() {
\tstd::time_t now = std::time(nullptr);
\tchar buf[20];
\tstd::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", std::localtime(&now));
\treturn std::string(buf);
}
'''

files["service/operation-type/OperationTypeService.h"] = LICENSE + '''#ifndef _OPERATION_TYPE_SERVICE_
#define _OPERATION_TYPE_SERVICE_
#include <list>
#include <vector>
#include "domain/vo/operation-type/OperationTypeVO.h"
#include "domain/query/operation-type/OperationTypeQuery.h"
#include "domain/dto/operation-type/OperationTypeDTO.h"
#include "domain/dto/operation-type/OperationTypeBatchDeleteDto.h"

/**
 * 操作类型服务实现
 */
class OperationTypeService
{
public:
\t// 分页查询操作类型
\tOperationTypePageDTO::Wrapper listAll(const OperationTypeQuery::Wrapper& query);
\t// 新增操作类型
\tint saveData(const OperationTypeAddDTO::Wrapper& dto, string name, string realname, string orgcode, string companycode);
\t// 修改操作类型
\tbool updateData(const OperationTypeDTO::Wrapper& dto);
\t// 通过ID删除操作类型
\tbool removeData(const string id);
\t// 批量删除操作类型
\tbool batchDeleteOperationType(const OperationTypeBatchDeleteDto::Wrapper& dto);
\t// 导入操作类型（解析上传的Excel文件内容）
\tint importOperationType(const char* data, size_t size, string name, string realname, string orgcode, string companycode);
\t// 导出操作类型（返回Excel文件二进制内容）
\tstd::vector<unsigned char> exportOperationType();
};

#endif // !_OPERATION_TYPE_SERVICE_
'''

files["service/operation-type/OperationTypeService.cpp"] = LICENSE + '''#include "stdafx.h"
#include "OperationTypeService.h"
#include "../../dao/operation-type/OperationTypeDAO.h"
#include "ExcelComponent.h"

OperationTypePageDTO::Wrapper OperationTypeService::listAll(const OperationTypeQuery::Wrapper& query)
{
\t// 定义分页对象
\tauto pages = OperationTypePageDTO::createShared();
\tpages->pageIndex = query->pageIndex;
\tpages->pageSize = query->pageSize;

\t// 查询数据总数
\tOperationTypeDAO dao;
\tuint64_t count = dao.count(query);
\tif (count <= 0)
\t{
\t\treturn pages;
\t}

\t// 分页查询数据
\tpages->total = count;
\tpages->calcPages();
\tlist<OperationTypeDO> result = dao.selectWithPage(query);
\t// 将DO转换成DTO
\tfor (OperationTypeDO sub : result)
\t{
\t\tauto dto = OperationTypeDTO::createShared();
\t\tZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, id, Id, code, Code, name, Name);
\t\tpages->addData(dto);
\t}
\treturn pages;
}

int OperationTypeService::saveData(const OperationTypeAddDTO::Wrapper& dto, string name, string realname, string orgcode, string companycode)
{
\t// 组装DO数据
\tOperationTypeDO data;
\tZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Code, code, Name, name);
\t// 执行数据插入
\tOperationTypeDAO dao;
\treturn dao.insert(data, name, realname, orgcode, companycode);
}

bool OperationTypeService::updateData(const OperationTypeDTO::Wrapper& dto)
{
\t// 组装DO数据
\tOperationTypeDO data;
\tZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Id, id, Code, code, Name, name);
\t// 执行数据修改
\tOperationTypeDAO dao;
\treturn dao.update(data) == 1;
}

bool OperationTypeService::removeData(const string id)
{
\tOperationTypeDAO dao;
\treturn dao.deleteById(id) == 1;
}

bool OperationTypeService::batchDeleteOperationType(const OperationTypeBatchDeleteDto::Wrapper& dto)
{
\tif (!dto->ids || dto->ids->empty())
\t{
\t\treturn false;
\t}
\tOperationTypeDAO dao;
\treturn dao.batchDelete(dto) > 0;
}

int OperationTypeService::importOperationType(const char* data, size_t size, string name, string realname, string orgcode, string companycode)
{
\tif (data == nullptr || size == 0)
\t{
\t\treturn -1;
\t}
\t// 页签名称（xlnt只能存储utf8，读取中文内容时需要转换）
\tstd::string sheetName = ZH_WORDS_GETTER("op.excel.name");
\t// 读取文件内容
\tauto readData = ExcelComponent::readIntoVector(data, size, sheetName);
\tif (readData.empty())
\t{
\t\treturn -1;
\t}

\tint result = -1;
\tfor (size_t i = 0; i < readData.size(); i++)
\t{
\t\tauto& row = readData[i];
\t\t// 第一行为表头，需要校验
\t\tif (i == 0)
\t\t{
\t\t\tif (row.size() != 2 || row[0] != ZH_WORDS_GETTER("op.excel.col.first") || row[1] != ZH_WORDS_GETTER("op.excel.col.second"))
\t\t\t{
\t\t\t\treturn -1;
\t\t\t}
\t\t\tresult = 0;
\t\t\tcontinue;
\t\t}
\t\t// 跳过空行
\t\tif (row.size() < 2 || (row[0].empty() && row[1].empty()))
\t\t{
\t\t\tcontinue;
\t\t}
\t\tOperationTypeDO temp;
\t\ttemp.setCode(row[0]);
\t\ttemp.setName(row[1]);
\t\t// 逐条插入（携带审计信息）
\t\tOperationTypeDAO dao;
\t\tdao.insert(temp, name, realname, orgcode, companycode);
\t}
\treturn result;
}

std::vector<unsigned char> OperationTypeService::exportOperationType()
{
\tOperationTypeDAO dao;
\tlist<OperationTypeDO> result = dao.selectAll();

\tstd::vector<std::vector<std::string>> data;
\t// 写入表头
\tstd::vector<std::string> first;
\tfirst.push_back(ZH_WORDS_GETTER("op.excel.col.first"));
\tfirst.push_back(ZH_WORDS_GETTER("op.excel.col.second"));
\tdata.push_back(first);

\tfor (auto it = result.begin(); it != result.end(); ++it)
\t{
\t\tstd::vector<std::string> row;
\t\trow.push_back(it->getCode());
\t\trow.push_back(it->getName());
\t\tdata.push_back(row);
\t}

\t// 页签名称（xlnt只能存储utf8，读取中文内容时需要转换）
\tstd::string sheetName = ZH_WORDS_GETTER("op.excel.name");
\t// 将数据以excel格式写入buff中
\tExcelComponent excel;
\treturn excel.writeVectorToBuff(sheetName, data);
}
'''

files["controller/operation-type/OperationTypeController.h"] = LICENSE + '''#ifndef _OPERATION_TYPE_CONTROLLER_
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

\tAPI_ACCESS_DECLARE(OperationTypeController);

public:
\t// 查询操作类型（分页+条件）
\tENDPOINT_INFO(queryAll) {
\t\t// 定义接口标题
\t\tAPI_DEF_ADD_TITLE(ZH_WORDS_GETTER("op.query-all.summary"));
\t\t// 定义默认授权参数（可选定义，如果定义了，下面ENDPOINT里面需要加入API_HANDLER_AUTH_PARAME）
\t\tAPI_DEF_ADD_AUTH();
\t\t// 定义响应参数格式
\t\tAPI_DEF_ADD_RSP_JSON_WRAPPER(OperationTypePageJsonVO);
\t\t// 定义分页查询参数描述
\t\tAPI_DEF_ADD_PAGE_PARAMS();
\t\t// 定义其他查询参数描述
\t\tAPI_DEF_ADD_QUERY_PARAMS(String, "code", ZH_WORDS_GETTER("op.field.code"), "OPER", false);
\t\tAPI_DEF_ADD_QUERY_PARAMS(String, "name", ZH_WORDS_GETTER("op.field.name"), "test", false);
\t}
\t// 查询接口处理
\tENDPOINT(API_M_GET, "/wconfig/operation-type", queryAll, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
\t\t// 解析查询参数为Query领域模型
\t\tAPI_HANDLER_QUERY_PARAM(query, OperationTypeQuery, queryParams);
\t\t// 呼叫执行函数响应结果
\t\tAPI_HANDLER_RESP_VO(execQueryAll(query));
\t}

\t// 录入操作类型
\tENDPOINT_INFO(addOperationType) {
\t\t// 定义接口标题
\t\tAPI_DEF_ADD_TITLE(ZH_WORDS_GETTER("op.post.summary"));
\t\t// 定义默认授权参数
\t\tAPI_DEF_ADD_AUTH();
\t\t// 定义响应参数格式
\t\tAPI_DEF_ADD_RSP_JSON_WRAPPER(Uint64JsonVO);
\t}
\t// 录入接口处理
\tENDPOINT(API_M_POST, "/wconfig/operation-type", addOperationType, BODY_DTO(OperationTypeAddDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME) {
\t\t// 呼叫执行函数响应结果
\t\tAPI_HANDLER_RESP_VO(execAddOperationType(dto, authObject->getPayload()));
\t}

\t// 修改操作类型
\tAPI_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("op.modify.summary"), modifyOperationType, Uint64JsonVO::Wrapper);
\t// 修改接口处理
\tAPI_HANDLER_ENDPOINT_AUTH(API_M_PUT, "/wconfig/operation-type", modifyOperationType, BODY_DTO(OperationTypeDTO::Wrapper, dto), execModifyOperationType(dto));

\t// 删除操作类型
\tENDPOINT_INFO(deleteOperationType) {
\t\t// 定义标题和返回类型以及授权支持
\t\tAPI_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("op.delete.summary"), Uint64JsonVO::Wrapper);
\t\t// 定义路径参数说明
\t\tAPI_DEF_ADD_PATH_PARAMS(String, "id", ZH_WORDS_GETTER("op.field.id"), "1", true);
\t}
\t// 删除接口处理
\tAPI_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/wconfig/operation-type/{id}", deleteOperationType, PATH(String, id), execDeleteOperationType(id));

\t// 批量删除操作类型
\tENDPOINT_INFO(batchDeleteOperationType) {
\t\t// 定义标题和返回类型以及授权支持
\t\tAPI_DEF_ADD_COMMON_AUTH(ZH_WORDS_GETTER("op.batchDelete.summary"), Uint64JsonVO::Wrapper);
\t}
\t// 批量删除接口处理
\tAPI_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/wconfig/operation-type/batch-delete", batchDeleteOperationType, BODY_DTO(OperationTypeBatchDeleteDto::Wrapper, dto), execBatchDeleteOperationType(dto));

\t// 导入操作类型（Excel上传）
\tAPI_DEF_ENDPOINT_INFO(ZH_WORDS_GETTER("op.import.summary"), importOperationType, StringJsonVO::Wrapper);
\t// 导入接口处理
\tAPI_HANDLER_ENDPOINT_AUTH(API_M_POST, "/wconfig/operation-type/import", importOperationType, REQUEST(std::shared_ptr<IncomingRequest>, request), execImportOperationType(request, authObject->getPayload()));

\t// 导出操作类型（Excel下载）
\tENDPOINT_INFO(exportOperationType) {
\t\tAPI_DEF_ADD_COMMON(ZH_WORDS_GETTER("op.export.summary"), Void);
\t\tAPI_DEF_ADD_QUERY_PARAMS(String, "filename", ZH_WORDS_GETTER("recv-g-way-file.filed.filename"), "operation-type.xlsx", true);
\t}
\t// 导出接口处理
\tENDPOINT(API_M_GET, "/wconfig/operation-type/export", exportOperationType, QUERY(String, filename)) {
\t\treturn execExportOperationType(filename);
\t}

private:
\t// 分页查询
\tOperationTypePageJsonVO::Wrapper execQueryAll(const OperationTypeQuery::Wrapper& query);
\t// 录入
\tUint64JsonVO::Wrapper execAddOperationType(const OperationTypeAddDTO::Wrapper& dto, const PayloadDTO& payload);
\t// 修改
\tUint64JsonVO::Wrapper execModifyOperationType(const OperationTypeDTO::Wrapper& dto);
\t// 删除
\tUint64JsonVO::Wrapper execDeleteOperationType(const String& id);
\t// 批量删除
\tUint64JsonVO::Wrapper execBatchDeleteOperationType(const OperationTypeBatchDeleteDto::Wrapper& dto);
\t// 导入
\tStringJsonVO::Wrapper execImportOperationType(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload);
\t// 导出
\tstd::shared_ptr<OutgoingResponse> execExportOperationType(const String& filename);
};

#include OATPP_CODEGEN_END(ApiController) ///< End ApiController codegen section

#endif // !_OPERATION_TYPE_CONTROLLER_
'''

files["controller/operation-type/OperationTypeController.cpp"] = LICENSE + '''#include "stdafx.h"
#include "OperationTypeController.h"
#include "../../service/operation-type/OperationTypeService.h"

//分页查询操作类型
OperationTypePageJsonVO::Wrapper OperationTypeController::execQueryAll(const OperationTypeQuery::Wrapper& query)
{
\t// 定义一个Service
\tOperationTypeService service;
\t// 查询数据
\tauto result = service.listAll(query);
\t// 响应结果
\tauto jvo = OperationTypePageJsonVO::createShared();
\tjvo->success(result);
\treturn jvo;
}

//录入操作类型
Uint64JsonVO::Wrapper OperationTypeController::execAddOperationType(const OperationTypeAddDTO::Wrapper& dto, const PayloadDTO& payload)
{
\t// 定义返回数据对象
\tauto jvo = Uint64JsonVO::createShared();
\t// 参数校验
\tif (!dto->code || !dto->name)
\t{
\t\tjvo->init(UInt64(-1), RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\t// 有效值校验
\tif (dto->code->empty() || dto->name->empty())
\t{
\t\tjvo->init(UInt64(-1), RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\t// 定义一个Service
\tOperationTypeService service;
\t// 执行数据新增
\tuint64_t id = service.saveData(dto, payload.getUsername(), payload.getRealname(), payload.getOrgcode(), payload.getCompanycode());
\tif (id > 0) {
\t\tjvo->success(UInt64(id));
\t}
\telse
\t{
\t\tjvo->fail(UInt64(id));
\t}
\t// 响应结果
\treturn jvo;
}

//修改操作类型
Uint64JsonVO::Wrapper OperationTypeController::execModifyOperationType(const OperationTypeDTO::Wrapper& dto)
{
\t// 定义返回数据对象
\tauto jvo = Uint64JsonVO::createShared();
\t// 参数校验
\tif (!dto->id || dto->id->empty())
\t{
\t\tjvo->init(UInt64(-1), RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\t// 定义一个Service
\tOperationTypeService service;
\t// 执行数据修改
\tif (service.updateData(dto)) {
\t\tjvo->success(UInt64(1));
\t}
\telse
\t{
\t\tjvo->fail(UInt64(-1));
\t}
\t// 响应结果
\treturn jvo;
}

//删除操作类型
Uint64JsonVO::Wrapper OperationTypeController::execDeleteOperationType(const String& id)
{
\t// 定义返回数据对象
\tauto jvo = Uint64JsonVO::createShared();
\t// 参数校验
\tif (!id || id->empty())
\t{
\t\tjvo->init(UInt64(-1), RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\t// 定义一个Service
\tOperationTypeService service;
\t// 执行数据删除
\tif (service.removeData(id->c_str())) {
\t\tjvo->success(UInt64(1));
\t}
\telse
\t{
\t\tjvo->fail(UInt64(-1));
\t}
\t// 响应结果
\treturn jvo;
}

//批量删除操作类型
Uint64JsonVO::Wrapper OperationTypeController::execBatchDeleteOperationType(const OperationTypeBatchDeleteDto::Wrapper& dto)
{
\t// 定义返回数据对象
\tauto jvo = Uint64JsonVO::createShared();
\t// 参数校验
\tif (!dto->ids || dto->ids->empty())
\t{
\t\tjvo->init(UInt64(-1), RS_PARAMS_INVALID);
\t\treturn jvo;
\t}
\t// 定义一个Service
\tOperationTypeService service;
\t// 执行批量删除
\tif (service.batchDeleteOperationType(dto)) {
\t\tjvo->success(UInt64(dto->ids->size()));
\t}
\telse
\t{
\t\tjvo->fail(UInt64(-1));
\t}
\t// 响应结果
\treturn jvo;
}

//导入操作类型
StringJsonVO::Wrapper OperationTypeController::execImportOperationType(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
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
\tOperationTypeService service;
\tint result = service.importOperationType(file->data(), file->size(),
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

//导出操作类型
std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> OperationTypeController::execExportOperationType(const String& filename)
{
\tOperationTypeService service;
\tauto buff = service.exportOperationType();
\tif (buff.empty())
\t{
\t\treturn createResponse(Status::CODE_404, "File Not Found");
\t}
\t// 构造响应内容
\tstring content((const char*)buff.data(), buff.size());
\t// 创建响应头
\tauto response = createResponse(Status::CODE_200, content);
\t// 设置响应头信息
\tresponse->putHeader("Content-Disposition", "attachment; filename=" + filename.getValue("operation-type.xlsx"));
\tresponse->putHeader("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
\treturn response;
}
'''

for path, content in files.items():
    full = R + path
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'wb').write(content.encode('utf-8'))
    print("新建", path)
