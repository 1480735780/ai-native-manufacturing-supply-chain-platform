#include "stdafx.h"
#include "ComInfoController.h"
#include "domain/vo/cominfo/ComInfoVO.h"
#include "domain/dto/companyinfo/CompanyInfoDTO.h"
#include "service/companyinfo/CompanyInfoService.h"
#include "dao/company-conf/CompanyInfoDAO.h"
#include "domain/query/company-conf/CompanyInfoQuery.h"
#include "domain/do/company-conf/CompanyInfoDO.h"
#include <regex>

// FastDFS需要导入的头
#include "ServerInfo.h"
#include "NacosClient.h"
#include "FastDfsClient.h"
#include "SimpleDateTimeFormat.h"
#include "ExcelComponent.h"

StringJsonVO::Wrapper ComInfoController::execInputComInfo(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	auto jvo = StringJsonVO::createShared();
	// 1 初始化并读取上传的多部分表单
	API_MULTIPART_INIT(container, reader);
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);
	request->transferBody(&reader);
	OATPP_LOGD("Multipart", "parts_count=%d", container->count());

	// 2 解析文件字段
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);
	if (!file) {
		jvo->fail("Path is not right. Don't find file. Please try again.");
		ResultStatus rs("404 Not Found", 404);
		jvo->setStatus(rs);
		return jvo;
	}

	string filename = partfile->getFilename().getValue("");
	OATPP_LOGD("Multipart", "file='%s'", filename.c_str());

	// 3 校验文件后缀，只接受 .xlsx
	string filetype = "";
	size_t pos = filename.rfind(".");
	if (pos != string::npos) { filetype = filename.substr(pos + 1); }
	if (filetype != "xlsx") {
		jvo->fail("Type is not right. Please try again.");
		ResultStatus rs("415 Unsupported Media Type", 415);
		jvo->setStatus(rs);
		return jvo;
	}

	// 4 读取工作簿数据（第1行为中文表头，第2行为英文表头，从第3行开始为数据）
	std::vector<std::vector<std::string>> excelData = ExcelComponent::readIntoVector(file->data(), file->size(), "Page1");
	if (excelData.size() <= 2) {
		jvo->fail("File is empty. Please try again.");
		ResultStatus rs("204 No Content", 204);
		jvo->setStatus(rs);
		return jvo;
	}

	CompanyInfoService service;
	int imported = 0;
	for (size_t i = 2; i < excelData.size(); ++i) {
		const auto& row = excelData[i];
		// 列：id / 审计字段(7列) / com_code / com_zh_name / com_zh_aname / com_zh_addr / com_en_name / com_en_aname
		if (row.size() < 15) { continue; }
		if (row[9].empty() && row[10].empty()) { continue; } // 跳过空行

		auto dto = CompanyAddInfoDTO::createShared();
		dto->companyId = row[9];
		dto->zhabbr = row[10];
		dto->zhful = row[11];
		dto->zhaddr = row[12];
		dto->enabbr = row[13];
		dto->enful = row[14];
		if (service.saveData(dto, payload) > 0) { ++imported; }
	}

	// 5 响应结果
	jvo->success("Import Data successfully. rows=" + std::to_string(imported));
	ResultStatus rs("200 OK", 200);
	jvo->setStatus(rs);
	return jvo;
}

std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> ComInfoController::execOutputComInfo(const String& filename)
{
	// 表`ba_comp`对应结构：中文表头 + 英文表头
	std::vector<std::string> ba_comp = {
		ZH_WORDS_GETTER("comconfig.cominfo.id"),
		ZH_WORDS_GETTER("comconfig.cominfo.create_name"),
		ZH_WORDS_GETTER("comconfig.cominfo.create_by"),
		ZH_WORDS_GETTER("comconfig.cominfo.create_date"),
		ZH_WORDS_GETTER("comconfig.cominfo.update_name"),
		ZH_WORDS_GETTER("comconfig.cominfo.update_by"),
		ZH_WORDS_GETTER("comconfig.cominfo.update_date"),
		ZH_WORDS_GETTER("comconfig.cominfo.sys_org_code"),
		ZH_WORDS_GETTER("comconfig.cominfo.sys_company_code"),
		ZH_WORDS_GETTER("comconfig.cominfo.com_code"),
		ZH_WORDS_GETTER("comconfig.cominfo.com_zh_name"),
		ZH_WORDS_GETTER("comconfig.cominfo.com_zh_aname"),
		ZH_WORDS_GETTER("comconfig.cominfo.com_zh_addr"),
		ZH_WORDS_GETTER("comconfig.cominfo.com_en_name"),
		ZH_WORDS_GETTER("comconfig.cominfo.com_en_aname")
	};
	std::vector<std::string> ba_comp_en = {
		"id", "create_name", "create_by", "create_date", "update_name",
		"update_by", "update_date", "sys_org_code", "sys_company_code",
		"com_code", "com_zh_name", "com_zh_aname", "com_zh_addr",
		"com_en_name", "com_en_aname"
	};

	// 从数据库查询全部企业信息（不再使用模拟数据）
	// 注意：查询对象是 oatpp DTO，必须用 createShared() 构造，不能用栈对象
	auto query = CompanyInfoQuery::createShared();
	query->pageIndex = 1;
	query->pageSize = 100000;
	CompanyInfoDAO dao;
	std::list<CompanyInfoDO> companies = dao.selectWithPage(query);

	std::vector<std::vector<std::string>> data;
	data.push_back(ba_comp);
	data.push_back(ba_comp_en);
	for (const auto& c : companies) {
		data.push_back({
			c.getId(), "", "", "", "", "", "", "", "",
			c.getCode(), c.getZh_name(), c.getZh_aname(), c.getZh_addr(),
			c.getEn_name(), c.getEn_aname()
		});
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
