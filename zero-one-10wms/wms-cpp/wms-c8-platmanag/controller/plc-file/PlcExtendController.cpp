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
// 本文件为PLC指令控制器补充实现：批量删除、导出、导入、执行
#include "stdafx.h"
#include "PlcController.h"
#include "../../service/plc-file/PlcService.h"
#include "../ApiDeclarativeServicesHelper.h"
#include "../../lib-common/include/ExcelComponent.h"
#include "../../lib-common/include/FastDfsClient.h"
#include "../../lib-common/include/NacosClient.h"
#include "../../ServerInfo.h"
#include <filesystem>

// 批量删除PLC指令
Uint64JsonVO::Wrapper PlcController::execRemovePlcBatch(const BatchDeleteRequestDto::Wrapper& dto)
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
	PlcService service;
	uint64_t rows = service.removeBatch(ids);
	if (rows > 0)
		jvo->success(UInt64(rows));
	else
		jvo->fail(UInt64(rows));
	return jvo;
}

// 导出PLC指令（按条件生成 Excel 并上传，返回下载地址）
StringJsonVO::Wrapper PlcController::execExportPlc(const PlcFileQuery::Wrapper& query, const PayloadDTO& payload)
{
	auto jvo = StringJsonVO::createShared();
	PlcService service;
	auto rows = service.listAllForExport(query);
	if (rows.empty())
	{
		jvo->fail("no data");
		return jvo;
	}
	// 组装 Excel 数据（表头 + 数据行）
	std::vector<std::vector<std::string>> data;
	std::vector<std::string> header = { "PLCIP", ZH_WORDS_GETTER("plc.file.plcport"), ZH_WORDS_GETTER("plc.file.plctype"),
		ZH_WORDS_GETTER("plc.file.remark"), ZH_WORDS_GETTER("plc.file.time"), ZH_WORDS_GETTER("plc.file.seq"),
		ZH_WORDS_GETTER("plc.file.insset"), ZH_WORDS_GETTER("plc.file.standby"), ZH_WORDS_GETTER("plc.file.number"),
		ZH_WORDS_GETTER("plc.file.sys1"), ZH_WORDS_GETTER("plc.file.sys2"), ZH_WORDS_GETTER("plc.file.steptime"), ZH_WORDS_GETTER("plc.file.step") };
	data.push_back(header);
	for (const auto& row : rows)
	{
		std::vector<std::string> r = { row.getplc_ip(), row.getplc_port(), row.getplc_type(), row.getcom_remark(),
			row.getcom_time(), row.getcom_seq(), row.getcom_cons(), row.getremark1(), row.getcom_no(),
			row.getquery01(), row.getquery02(), row.getsetp_time(), row.getsetp_num() };
		data.push_back(r);
	}
	// 写入缓冲区
	ExcelComponent excel;
	auto buffer = excel.writeVectorToBuff("plc", data);
	const char* charData = reinterpret_cast<const char*>(buffer.data());
	// 上传 FastDFS
	std::string result;
	try {
#ifdef LINUX
		NacosClient ns(ServerInfo::getInstance().getNacosAddr(), ServerInfo::getInstance().getNacosNs());
		std::string config = ns.getConfigText("client.conf");
		FastDfsClient dfs(config, false);
#else
		FastDfsClient dfs(ServerInfo::getInstance().getDbHost(), 22122);
#endif
		result = dfs.uploadFile(charData, buffer.size(), "xlsx");
	}
	catch (std::exception& ex) {
		std::cerr << "upload error: " << ex.what() << std::endl;
	}
	if (!result.empty())
		jvo->success("http://" + ServerInfo::getInstance().getDbHost() + ":8888/" + result);
	else
		jvo->fail("export failed");
	return jvo;
}

// 导入PLC指令
StringJsonVO::Wrapper PlcController::execImportPlc(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	namespace fs = std::filesystem;
	auto jvo = StringJsonVO::createShared();
	API_MULTIPART_INIT(container, reader);
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);
	request->transferBody(&reader);
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);
	if (!file) {
		jvo->fail("file is null");
		return jvo;
	}
	string filename = partfile->getFilename().getValue("");
	string fullPath = "public/static/file/" + filename;
	fs::path dir = fs::path("public/static/file/");
	if (!fs::exists(dir)) fs::create_directories(dir);
	file.saveToFile(fullPath.c_str());
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
	PlcService service;
	bool ok = service.importData(res, payload.getUsername(), payload.getRealname(), payload.getOrgcode(), payload.getCompanycode());
	if (ok)
		jvo->success("success");
	else
		jvo->fail("import failed");
	return jvo;
}

// 执行指令（支持批量）
Uint64JsonVO::Wrapper PlcController::execExecutePlc(const BatchDeleteRequestDto::Wrapper& dto)
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
	PlcService service;
	uint64_t okCount = service.executeBatch(ids);
	jvo->success(UInt64(okCount)); // 返回成功执行条数
	return jvo;
}
