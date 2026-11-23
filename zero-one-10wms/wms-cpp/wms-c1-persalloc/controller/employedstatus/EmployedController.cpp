#include "stdafx.h"
#include "EmployedController.h"
#include "../../service/employedstatus/EmployedService.h"
#include <iostream>

// FastDFS需要导入的头
#include "ServerInfo.h"
#include "NacosClient.h"
#include "FastDfsClient.h"
#include "ExcelComponent.h"
#include <filesystem> 
// 不手动typedef的话不识别，不知道为什么
typedef oatpp::web::protocol::http::outgoing::Response OutgoingResponse;
//#include "SimpleDateTimeFormat.h"

Uint64JsonVO::Wrapper EmployedController::execRemoveByCode(const EmployedBatchRemoveDTO::Wrapper& dto_list)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	auto row = dto_list->rows;
	// fix: aggregate per-row results
	uint64_t okCount = 0;
	uint64_t failCount = 0;

	for (auto iter = row->begin(); iter != row->end(); iter++) {
		auto dto = *iter;

		// 参数校验
		// 非空校验
		if (!dto->code)
		{
			jvo->init(UInt64(-1), RS_PARAMS_INVALID);
			return jvo;
		}
		// 有效值校验
		if (dto->code->empty())
		{
			jvo->init(UInt64(-1), RS_PARAMS_INVALID);
			return jvo;
		}

		// 定义一个Service
		EmployedService service;
		// 执行数据删除
		auto res = service.removeData(dto);
		if (res) {
			okCount++;
		}
		else {
			failCount++;
		}
	}
	if (okCount > 0) {
		jvo->success(UInt64((v_uint64)okCount));
	}
	else {
		jvo->fail(UInt64((v_uint64)0));
	}
	return jvo;
}

std::shared_ptr<OutgoingResponse> EmployedController::execDownloadFile()
{
	string filename = "ba_pos_sta.xlsx";
	EmployedService service;
	string loaclpath = "public/static/";
	bool success = service.exportAllData(loaclpath);

	// 构建文件全路径
	std::string fullPath = loaclpath + filename;

	// 读取文件
	auto fstring = String::loadFromFile(fullPath.c_str());

	// 判断是否读取成功
	if (!fstring || !success)
	{
		std::cerr << "Failed to open file: " << std::strerror(errno) << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	// 创建响应头
	auto response = createResponse(Status::CODE_200, fstring);

	// 设置响应头信息
	response->putHeader("Content-Disposition", "attachment; filename=" + filename);

	// 影响成功结果
	return response;
}

StringJsonVO::Wrapper EmployedController::execUploadOne(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	auto jvo = StringJsonVO::createShared();

	// 1 init multipart reader
	API_MULTIPART_INIT(container, reader);
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);

	// 2 read body
	request->transferBody(&reader);
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);
	if (!file) {
		jvo->fail("Not Found File");
		return jvo;
	}

	// fix: parse excel from memory with unified sheet name
	// old code created an empty xlnt workbook and took sheet_titles()[0], which is undefined behavior
	auto res = ExcelComponent::readIntoVector(file->data(), file->size(), "Sheet1");
	if (res.size() <= 1) {
		jvo->fail("Empty File");
		return jvo;
	}

	EmployedService service;
	bool success = service.importAllData(res, payload);

	if (success)
		jvo->success("success");
	else jvo->fail("fail");
	return jvo;
}
