#include "stdafx.h"
#include "CityTypeController.h"
#include "ExcelComponent.h"
#include "FastDfsClient.h"
#include "service/citytype/CityTypeService.h"
#ifdef _WIN32
#include <direct.h>  // Windows 的 _mkdir
#define mkdir(path, mode) _mkdir(path)  // 适配 Windows
#else
#include <sys/stat.h>
#include <sys/types.h>
#endif

StringJsonVO::Wrapper CityTypeController::execModifyCityTypeCode(const CityTypeDTO::Wrapper& dto, const PayloadDTO& payload) {
	CityTypeService service;
	auto jvo = StringJsonVO::createShared();
	if (service.Udp(dto, payload))
	{
		jvo->success(dto->id);
	}
	else
	{
		jvo->fail("-1");
	}
    return jvo;
}

CityTypeNameListJsonVO::Wrapper CityTypeController::execGetCityTypeNamesList() {
	CityTypeService service;
	auto ans = service.nameList();
	auto jvo = CityTypeNameListJsonVO::createShared();
	jvo->success(ans);
	return jvo;
}

CityTypePageJsonVO::Wrapper CityTypeController::execGetCityTypeList(const CityTypeQuery::Wrapper& query) {
	CityTypeService service;
	auto ans = service.listAll(query);
	auto jvo = CityTypePageJsonVO::createShared();
	jvo->success(ans);
    return jvo;
}

StringJsonVO::Wrapper CityTypeController::execCreateCityType(const CitytypeBaseDTO::Wrapper& dto, const PayloadDTO& payload) {
	CityTypeService service;
	auto jvo = StringJsonVO::createShared();
	std::string id = service.Add(dto, payload);
	if (id != "")
	{
		jvo->success(id);
	}
	else
	{
		jvo->fail("-1");
	}
    return jvo;
}

StringJsonVO::Wrapper CityTypeController::execCitytypeDel(const String& id)
{
	// 定义返回数据对象
	auto jvo = StringJsonVO::createShared();
	// 参数校验
	if (!id || id->empty())
	{
		jvo->init("-1", RS_PARAMS_INVALID);  
		return jvo;
	}
	// 定义一个Service
	CityTypeService service;
	// 执行数据删除
	if (service.removeData(id)) {
		jvo->success(id);
	}
	else
	{
		jvo->fail(id);
	}
	// 响应结果
	return jvo;
}

StringJsonVO::Wrapper CityTypeController::execCitytypeUpload(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
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
	auto vec = ExcelComponent::readIntoVector(file->data(), file->size(), ZH_WORDS_GETTER("citytype.type"));
	if (vec.size() <= 1)
	{
		jvo->fail("Empty File");
		return jvo;
	}

	// skip header row, validate columns, count result
	int ok = 0, skipped = 0, failed = 0;
	std::vector<std::vector<std::string>> valid;
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

	CityTypeService service;
	ok = service.import(valid, payload);
	failed = (int)valid.size() - ok;

	std::string msg = "imported " + std::to_string(ok) + " rows, skipped " + std::to_string(skipped) + ", failed " + std::to_string(failed);
	if (ok <= 0)
	{
		jvo->fail(String(msg));
		return jvo;
	}
	jvo->success(String(msg));
	return jvo;
}

std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> CityTypeController::execCitytypeDownload()
{
	CityTypeService service;
	auto vec = service.listAll();

	// build excel in memory, no template file needed
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff(ZH_WORDS_GETTER("citytype.type"), vec);
	const char* tsData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(tsData, buff.size());

	if (!fstring)
	{
		std::cerr << "Failed to build excel buffer" << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	auto response = createResponse(Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=citytype.xlsx");
	return response;
}

StringJsonVO::Wrapper CityTypeController::execCitytypeBatchDel(const BatchDelIdsDTO::Wrapper& dto)
{
	auto jvo = StringJsonVO::createShared();
	// validate ids
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

	CityTypeService service;
	// reference check: refuse when codes referenced by ba_city
	auto refed = service.listReferencedNames(ids);
	if (!refed.empty())
	{
		std::string msg = "referenced by area info, cannot delete: ";
		for (size_t i = 0; i < refed.size(); i++) msg += (i ? ", " : "") + refed[i];
		jvo->fail(String(msg));
		return jvo;
	}

	int removed = service.removeDataBatch(ids);
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
