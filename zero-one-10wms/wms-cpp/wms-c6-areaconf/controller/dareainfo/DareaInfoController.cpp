#include "stdafx.h"
#include "DareaInfoController.h"
#include "service/regioninfo/DareaInfoService.h"
#include "service/regioninfo/RegionInfoService.h"
#include "domain/do/regioninfo/RegionInfoDO.h"
#include <string>
#include "ServerInfo.h"
#include "NacosClient.h"
#include "FastDfsClient.h"
#include "SimpleDateTimeFormat.h"
#include "Macros.h"
#include "ExcelComponent.h"
#include <filesystem>
namespace fs = std::filesystem;

std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> DareaInfoController::execExport()
{
	DareaInfoService service;
	auto vec = service.Export();

	// build excel in memory, no template file needed
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff(ZH_WORDS_GETTER("DareaInfo.info"), vec);
	const char* tsData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(tsData, buff.size());

	if (!fstring)
	{
		std::cerr << "Failed to build excel buffer" << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	auto response = createResponse(Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=dareainfo.xlsx");
	return response;
}

StringJsonVO::Wrapper DareaInfoController::execImport(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	// read multipart file field
	API_MULTIPART_INIT(container, reader);
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);
	request->transferBody(&reader);
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);

	auto jvo = StringJsonVO::createShared();
	if (!file)
	{
		jvo->fail("Not Found File");
		return jvo;
	}

	// parse excel from memory, unified sheet name
	auto vec = ExcelComponent::readIntoVector(file->data(), file->size(), ZH_WORDS_GETTER("DareaInfo.info"));
	if (vec.size() <= 1)
	{
		jvo->fail("Empty File");
		return jvo;
	}

	// skip header, validate 2 columns
	std::vector<std::vector<std::string>> valid;
	int skipped = 0;
	for (size_t i = 1; i < vec.size(); i++)
	{
		auto& row = vec[i];
		if (row.size() < 2 || row[0].empty() || row[1].empty()) { skipped++; continue; }
		valid.push_back(row);
	}
	if (valid.empty())
	{
		jvo->fail("No Valid Rows");
		return jvo;
	}

	DareaInfoService service;
	int ok = service.Import(valid, payload);
	std::string msg = "imported " + std::to_string(ok) + " rows, skipped " + std::to_string(skipped) + ", failed " + std::to_string((int)valid.size() - ok);
	if (ok <= 0)
	{
		jvo->fail(String(msg));
		return jvo;
	}
	jvo->success(String(msg));
	return jvo;
}

DareaInfoPageJsonVO::Wrapper DareaInfoController::executeQueryAll(const DareaInfoQuery::Wrapper& query)
{
	DareaInfoService service;
	auto result = service.listAll(query);
	auto jvo = DareaInfoPageJsonVO::createShared();

	jvo->success(result);
	return jvo;
}

StringJsonVO::Wrapper DareaInfoController::execAddDareaInfo(const DareaInfoAddDTO::Wrapper& dto, const PayloadDTO& payload)
{
	auto jvo = StringJsonVO::createShared();
	DareaInfoService service;
	std::string id = service.AddOne(dto, payload);
	if (id != "")
	{
		jvo->init(String(id), RS_SUCCESS);
		return jvo;
	}
	else {
		jvo->init(String("-1"), RS_FAIL);
		return jvo;
	}
}

StringJsonVO::Wrapper DareaInfoController::execModifyDareaInfo(const DareaInfoDTO::Wrapper& dto, const PayloadDTO& payload)
{
	auto jvo = StringJsonVO::createShared();
	DareaInfoService service;
	if (service.Update(dto, payload))
	{
		jvo->success("ok");
	}
	else {
		jvo->fail("no");
	}
	return jvo;
}

StringJsonVO::Wrapper DareaInfoController::execRemoveDareaInfo(const String& id)
{
	auto jvo = StringJsonVO::createShared();
	DareaInfoService service;
	std::cout << "remove dareainfo: id = " << id.getValue("") << std::endl;
	if (service.Delete(id.getValue("")))
	{
		jvo->success(id);
	}
	else {
		jvo->fail("-1");
	}
	return jvo;
}

RegionNameJsonVO::Wrapper DareaInfoController::execQueryName()
{
	// 定义返回数据对象
	auto jvo = RegionNameJsonVO::createShared();

	// 定义一个Service
	RegionInfoService service;
	// 执行数据新增
	auto res = service.getByName();
	jvo->success(res);

	//响应结果
	return jvo;
}

StringJsonVO::Wrapper DareaInfoController::execBatchDel(const BatchDelIdsDTO::Wrapper& dto)
{
	auto jvo = StringJsonVO::createShared();
	if (!dto || !dto->ids || dto->ids->empty())
	{
		jvo->init("-1", RS_PARAMS_INVALID);
		return jvo;
	}
	std::vector<std::string> ids;
	for (auto& id : *dto->ids)
	{
		if (id && !id->empty()) ids.push_back(id.getValue(""));
	}
	if (ids.empty())
	{
		jvo->init("-1", RS_PARAMS_INVALID);
		return jvo;
	}

	// reference check: refuse when darea codes referenced by ba_city
	DareaInfoDAO dao;
	auto refed = dao.listReferencedCodes(dao.getCodesByIds(ids));
	if (!refed.empty())
	{
		std::string msg = "referenced by area info, cannot delete: ";
		for (size_t i = 0; i < refed.size(); i++) msg += (i ? ", " : "") + refed[i];
		jvo->fail(String(msg));
		return jvo;
	}

	int removed = dao.deleteByIds(ids);
	if (removed > 0)
	{
		jvo->success(String("deleted " + std::to_string(removed)));
	}
	else
	{
		jvo->fail("-1");
	}
	return jvo;
}
