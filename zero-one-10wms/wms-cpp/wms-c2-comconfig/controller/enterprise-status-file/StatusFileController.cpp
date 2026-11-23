#include "stdafx.h"
#include "../ApiDeclarativeServicesHelper.h"
#include "StatusFileController.h"
#include "domain/vo/enterprise-status/GetEnterpriseStatusVO.h"
#include "ApiHelper.h"
#include "../../service/enterprise-status/QueryAddEnterpirseStatusService.h"
#include <regex>
#include <filesystem>

// FastDFS需要导入的头
#include "ServerInfo.h"
#include "NacosClient.h"
#include "FastDfsClient.h"
#include "SimpleDateTimeFormat.h"
#include "ExcelComponent.h"

// 递归替换所有 `from` 为 `to`
void replaceAll_file(std::string& str, const std::string& from, const std::string& to) {
	if (from.empty() || from == to) return; // 避免死循环
	size_t startPos = 0;
	while ((startPos = str.find(from, startPos)) != std::string::npos) {
		str.replace(startPos, from.length(), to);
		startPos += to.length(); // 防止死循环
	}
}

// 处理路径字符串
std::string normalizePath_file(std::string path) {
	if (path.empty())return {};
	// 1. 移除引号
	replaceAll_file(path, "%22", "");
	replaceAll_file(path, "%27", "");

	// 2. 替换 URL 编码
	replaceAll_file(path, "%3A", ":"); // :冒号
	replaceAll_file(path, "%5C", "\\");// \斜线
	replaceAll_file(path, "%2F", "\\");// /斜线

	// 3. 处理可能出现的多个 `\` 叠加的情况，使用正则确保 `\` 统一为 `\\`
	path = std::regex_replace(path, std::regex(R"(\\+)"), R"(\)"); // 将多个 `\` 统一为 `\\`

	return path;
}

// 删除本地临时文件
void DeleteTempStatusExcel(const string& path) {
	if (std::filesystem::exists(path)) {
		std::filesystem::remove(path);
	}
}

StringJsonVO::Wrapper StatusFileController::execUploadMore(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	/* multipart 解析（与 /indclas/upload-file、/entleve/upload-file 同模式） */
	// 1 初始化
	API_MULTIPART_INIT(container, reader);
	// 2 配置读取器
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);
	// 3 读取数据
	request->transferBody(&reader);

	// 4 获取文件
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);

	auto jvo = StringJsonVO::createShared();
	if (!file)
	{
		jvo->fail("file is empty");
		return jvo;
	}

	// 将文件保存到本地临时目录
	string filename = partfile->getFilename().getValue("");
	// 防路径穿越：仅保留文件名部分
	size_t slashPos = filename.find_last_of("/\\");
	if (slashPos != string::npos) filename = filename.substr(slashPos + 1);
	string fullPath = "public/static/file/" + filename;
	file.saveToFile(fullPath.c_str());

	// 后缀校验：仅支持 .xlsx
	if (filename.rfind(".xlsx") == string::npos) {
		jvo->fail("Type is not right. Please use .xlsx file.");
		jvo->setStatus(ResultStatus("415 Unsupported Media Type", 415));
		DeleteTempStatusExcel(fullPath);
		return jvo;
	}

	// 读取 Excel 数据（工作表名沿用历史模板 Sheet1）
	std::vector<std::vector<std::string>> excelData = ExcelComponent::readIntoVector(fullPath, "Sheet1");
	if (excelData.size() <= 2) {
		jvo->fail("File is empty. Please try again.");
		jvo->setStatus(ResultStatus("204 No Content", 204));
		DeleteTempStatusExcel(fullPath);
		return jvo;
	}

	// 第1、2行为表头（中文/英文），从第3行开始为数据。
	// 模板列顺序：com_sta_code, com_sta_name, com_sta_del
	EnterpriseStatusService service;
	int imported = 0;
	for (size_t i = 2; i < excelData.size(); ++i) {
		const auto& row = excelData[i];
		if (row.size() < 3) { continue; }
		if (row[0].empty() && row[1].empty()) { continue; } // 跳过空行

		auto dto = EnterpriseStatusDTO::createShared();
		dto->code = row[0];
		dto->name = row[1];
		dto->ban = row[2];
		if (service.saveData(dto) > 0) { ++imported; }
	}

	// 删除本地临时文件
	DeleteTempStatusExcel(fullPath);

	jvo->success("Import Data successfully. rows=" + std::to_string(imported));
	jvo->setStatus(ResultStatus("200 OK", 200));
	return jvo;
}

std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> StatusFileController::execDownloadFile(const String& filename)
{
	// 表`ba_com_sta`对应结构：中文表头 + 英文表头
	// 直接使用中文字面表头，避免字典缺键导致表头为空
	std::vector<std::string> ba_comp = {
	"企业状态代码",
	"企业状态名称",
	"停用",
	};
	std::vector<std::string> ba_comp_en = {
		"com_sta_code", "com_sta_name", "com_sta_del"
	};

	// 从独立表 ba_com_sta 查询全部企业状态，不再使用模拟数据
	auto query = GetEnterpriseStatusQuery::createShared();
	query->pageIndex = 1;
	query->pageSize = 100000;
	EnterpriseStatusService service;
	auto page = service.listAll(query);

	std::vector<std::vector<std::string>> data;
	data.push_back(ba_comp);
	data.push_back(ba_comp_en);
	if (page && page->rows) {
		for (const auto& item : *page->rows) {
			data.push_back({
				item->code.getValue(""),
				item->name.getValue(""),
				item->ban.getValue("")
			});
		}
	}

	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff("Page1", data);
	const char* tsData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(tsData, buff.size());
	if (!fstring) {
		return createResponse(Status::CODE_404, "File Not Found");
	}

	auto response = createResponse(Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=" + filename.getValue(""));
	return response;
}
