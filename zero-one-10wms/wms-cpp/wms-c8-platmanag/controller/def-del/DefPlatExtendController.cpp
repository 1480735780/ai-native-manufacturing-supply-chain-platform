/*
 Copyright Zero One Star. All rights reserved.

 @Author: dev-yuetaiguanli
 @Date: 2026/11/22

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
// 本文件为月台定义控制器补充实现：名称列表、条件分页、录入、批量删除、导入
#include "stdafx.h"
#include "DefPlatController.h"
#include "../../service/def-plat/DefPlatService.h"
#include "../ApiDeclarativeServicesHelper.h"
#include "../../lib-common/include/ExcelComponent.h"
#include <filesystem>

// 获取月台名称列表（用于下拉）
DefNameListJsonVO::Wrapper DefPlatController::execNameListPlat()
{
	auto jvo = DefNameListJsonVO::createShared();
	auto list = List<DefNameDto::Wrapper>::createShared();
	DefPlatService service;
	std::list<PlatDO> rows = service.DefNameListData();
	for (const auto& row : rows)
	{
		auto item = DefNameDto::createShared();
		item->id = row.getid();
		item->platform_code = row.getplatform_code();
		item->platform_name = row.getplatform_name();
		list->push_back(item);
	}
	jvo->success(list);
	return jvo;
}

// 获取月台列表（条件+分页）
DefPageJsonVO::Wrapper DefPlatController::execListPlat(const DefPlatQuery::Wrapper& query)
{
	DefPlatService service;
	auto result = service.DefListData(query);
	auto jvo = DefPageJsonVO::createShared();
	jvo->success(result);
	return jvo;
}

// 录入月台
Uint64JsonVO::Wrapper DefPlatController::execAddPlat(const DefAddDto::Wrapper& dto, const PayloadDTO& payload)
{
	auto jvo = Uint64JsonVO::createShared();
	// 必填校验
	if (!dto->platform_code || dto->platform_code->empty()
		|| !dto->platform_name || dto->platform_name->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	DefPlatService service;
	int rows = service.DefAddData(dto, payload);
	if (rows > 0)
		jvo->success(UInt64(rows));
	else if (rows == 0)
		jvo->fail(UInt64((v_uint64)0)); // 代码重复
	else
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
	return jvo;
}

// 批量删除月台（逻辑删除）
Uint64JsonVO::Wrapper DefPlatController::execBatchDelPlat(const BatchDeleteRequestDto::Wrapper& dto)
{
	auto jvo = Uint64JsonVO::createShared();
	if (!dto->ids || dto->ids->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	std::list<string> ids;
	for (auto& id : *dto->ids)
		ids.push_back(std::to_string(id.getValue(0)));
	DefPlatService service;
	uint64_t rows = service.DefBatchDeleteData(ids);
	if (rows > 0)
		jvo->success(UInt64(rows));
	else
		jvo->fail(UInt64(rows));
	return jvo;
}

// 导入月台（Excel xlsx）
StringJsonVO::Wrapper DefPlatController::execImportPlat(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	namespace fs = std::filesystem;
	auto jvo = StringJsonVO::createShared();
	// 1 初始化
	API_MULTIPART_INIT(container, reader);
	// 2 设置读取器
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);
	// 3 读取请求
	request->transferBody(&reader);
	// 获取上传文件
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);
	if (!file) {
		jvo->fail("file is null");
		return jvo;
	}
	// 保存到本地临时目录
	string filename = partfile->getFilename().getValue("");
	string fullPath = "public/static/file/" + filename;
	fs::path dir = fs::path("public/static/file/");
	if (!fs::exists(dir)) fs::create_directories(dir);
	file.saveToFile(fullPath.c_str());
	// 解析 Excel（第一个页签）
	ExcelComponent excel;
	xlnt::workbook wb;
	wb.load(fullPath);
	const std::vector<std::string> sheetNames = wb.sheet_titles();
	if (sheetNames.empty()) {
		jvo->fail("invalid xlsx: no sheet");
		return jvo;
	}
	auto res = excel.readIntoVector(fullPath, sheetNames[0]);
	if (res.size() <= 1) {
		jvo->fail("empty or invalid file");
		return jvo;
	}
	// 调用服务导入
	DefPlatService service;
	bool ok = service.DefImportData(res, payload);
	if (ok)
		jvo->success("success");
	else
		jvo->fail("import failed");
	return jvo;
}
