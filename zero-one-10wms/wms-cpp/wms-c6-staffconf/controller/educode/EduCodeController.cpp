#include "stdafx.h"
#include "EduCodeController.h"
#include "../../service/EducationService.h"
#include "../ApiDeclarativeServicesHelper.h"

#include <filesystem>  // C++17 file system lib
#include <fstream>     // file stream
#include <string>      // string lib
#include <iostream>    // log lib

#include "Macros.h"
#include "ExcelComponent.h"
#include "SimpleDateTimeFormat.h"

StringJsonVO::Wrapper EduCodeController::execDelEducate(const String& code)
{
	auto jvo = StringJsonVO::createShared();

	if (!code || code->empty())
	{
		jvo->init("-1", RS_PARAMS_INVALID);
		return jvo;
	}
	// create service
	DelRoleService service;
	// execute delete

	if (service.removeData(code)) {
		jvo->success(code);
	}
	else
	{
		jvo->fail(code);
	}
	// response
	return jvo;
}

EduPageJsonVO::Wrapper EduCodeController::execQueryEdu(const EduQuery::Wrapper& query)
{
	EduService service;
	auto result = service.listAll(query);
	auto jvo = EduPageJsonVO::createShared();
	jvo->success(result);
	return jvo;
}

Uint64JsonVO::Wrapper EduCodeController::execAddEdu(const EduAddDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// define response vo
	auto jvo = Uint64JsonVO::createShared();
	// params check
	if (dto->educode->empty() || dto->eduname->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}

	// create service
	EduService service;
	// execute insert
	uint64_t id = service.saveData(dto, payload);
	if (id > 0) {
		jvo->success(UInt64(id));
	}
	else
	{
		jvo->fail(UInt64(id));
	}
	// response
	return jvo;

}

StringJsonVO::Wrapper EduCodeController::execModifyEducode(const EducationalDTO::Wrapper& educationalDTO, const PayloadDTO& payload)
{
	// define response vo
	auto jvo = StringJsonVO::createShared();
	// params check
	if (!educationalDTO->code || !educationalDTO->name)
	{
		jvo->fail(" ");
		return jvo;
	}
	// create service
	DelRoleService service;
	// execute modify
	if (service.updateData(educationalDTO, payload)) {
		jvo->success(educationalDTO->code);
	}
	else
	{
		jvo->fail(educationalDTO->code);
	}
	// response
	return jvo;
}

StringJsonVO::Wrapper EduCodeController::importEduCode(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	auto jvo = StringJsonVO::createShared();

	// 1 read multipart file field
	API_MULTIPART_INIT(container, reader);
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);
	request->transferBody(&reader);
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);

	if (!file)
	{
		jvo->fail("Not Found File");
		return jvo;
	}

	// 2 parse excel from memory, sheet name unified as Sheet1
	// fix: old code used a non-existent dict key as sheet name and a shared ./file/edu.xlsx path
	auto vec = ExcelComponent::readIntoVector(file->data(), file->size(), "Sheet1");
	if (vec.size() <= 1)
	{
		jvo->fail("Empty File");
		return jvo;
	}

	// 3 keep header + valid rows only (skip header row, empty or short rows)
	std::vector<std::vector<std::string>> valid;
	valid.push_back(vec[0]);
	for (size_t i = 1; i < vec.size(); i++)
	{
		auto& row = vec[i];
		if (row.size() < 2 || row[0].empty() || row[1].empty()) continue;
		valid.push_back(row);
	}
	if (valid.size() <= 1)
	{
		jvo->fail("No Valid Rows");
		return jvo;
	}

	// 4 batch insert and report real inserted count (dedup-aware)
	EduService service;
	uint64_t inserted = service.saveData(valid, payload);
	jvo->success(String("imported " + std::to_string(inserted) + " rows, skipped " + std::to_string(valid.size() - 1 - inserted)));
	return jvo;
}

std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> EduCodeController::execexportEducode()
{
	// fix: build excel in memory (writeVectorToBuff) instead of sharing ./file/edu.xlsx with import
	EduService service;
	auto vec = service.listAll();

	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff("Sheet1", vec);
	const char* tsData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(tsData, buff.size());

	if (!fstring)
	{
		std::cerr << "Failed to build excel buffer" << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	auto response = createResponse(Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=edu.xlsx");
	return response;
}

// batch delete education code: loop over ids, report deleted count
StringJsonVO::Wrapper EduCodeController::execDelEducateBatch(const EduBatchDelDTO::Wrapper& dto)
{
	auto jvo = StringJsonVO::createShared();
	if (!dto || !dto->ids || dto->ids->empty())
	{
		jvo->init("-1", RS_PARAMS_INVALID);
		return jvo;
	}

	DelRoleService service;
	uint64_t okCount = 0;
	for (auto it = dto->ids->begin(); it != dto->ids->end(); ++it) {
		std::string id = it->getValue("");
		if (id.empty()) continue;
		if (service.removeData(id)) {
			okCount++;
		}
	}
	if (okCount > 0) {
		jvo->success(String("deleted " + std::to_string(okCount)));
	}
	else {
		jvo->fail(String("0"));
	}
	return jvo;
}
