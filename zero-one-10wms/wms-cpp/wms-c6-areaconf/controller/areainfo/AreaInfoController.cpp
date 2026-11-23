#include "stdafx.h"
#include "AreaInfoController.h"
#include "service/areainfo/AreaInfoService.h"
#include "ExcelComponent.h"

std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> AreaInfoController::execDownloadExcel()
{
	AreaInfoService service;
	auto vec = service.selectAll();

	// build excel in memory, no template file needed
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff(ZH_WORDS_GETTER("AreaInfo.info"), vec);
	const char* tsData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(tsData, buff.size());

	if (!fstring)
	{
		std::cerr << "Failed to build excel buffer" << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	auto response = createResponse(Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=areainfo.xlsx");
	return response;
}

StringJsonVO::Wrapper AreaInfoController::execUploadExcel(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
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
	auto vec = ExcelComponent::readIntoVector(file->data(), file->size(), ZH_WORDS_GETTER("AreaInfo.info"));
	if (vec.size() <= 1)
	{
		jvo->fail("Empty File");
		return jvo;
	}

	// skip header, validate 7 columns, verify dict names resolvable
	std::vector<std::vector<std::string>> valid;
	int skipped = 0;
	AreaInfoService service;
	for (size_t i = 1; i < vec.size(); i++)
	{
		auto& row = vec[i];
		if (row.size() < 7 || row[0].empty() || row[1].empty()) { skipped++; continue; }
		// city_type / barea / darea name must resolve to a code
		if (!service.existsCityTypeByName(row[3]) || !service.existsBareaByName(row[4]) || !service.existsDareaByName(row[5]))
		{
			skipped++; continue;
		}
		valid.push_back(row);
	}
	if (valid.empty())
	{
		jvo->fail("No Valid Rows");
		return jvo;
	}

	int ok = service.upload(valid, payload);
	std::string msg = "imported " + std::to_string(ok) + " rows, skipped " + std::to_string(skipped) + ", failed " + std::to_string((int)valid.size() - ok);
	if (ok <= 0)
	{
		jvo->fail(String(msg));
		return jvo;
	}
	jvo->success(String(msg));
	return jvo;
}

StringJsonVO::Wrapper AreaInfoController::execModify(const AreaInfoUpdDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// 定义返回数据对象
	auto jvo = StringJsonVO::createShared();
	// 参数校验
	if (!dto->id)
	{
		jvo->init(String("-1"), RS_PARAMS_INVALID);
		return jvo;
	}
	AreaInfoService service;
	if (service.modifyData(dto, payload))
	{
		jvo->success(dto->id);
	}
	else {
		jvo->fail(dto->id);
	}
	return jvo;
}

StringJsonVO::Wrapper AreaInfoController::execDelete(const String& dto)
{
	auto jvo = StringJsonVO::createShared();
	AreaInfoService service;
	if (service.deleteData(dto->data()))
	{
		jvo->success(dto);
	}
	else
	{
		jvo->fail(dto);
	}
	return jvo;
}

AreaNameTreeJsonVO::Wrapper AreaInfoController::execNameTreeAreaInfo()
{
	auto jvo = AreaNameTreeJsonVO::createShared();

	AreaInfoService service;
	for (auto node : service.nameTree())
	{
		jvo->data->push_back(AreaNameTreeDTO::Wrapper(dynamic_pointer_cast<AreaNameTreeDTO>(node), AreaNameTreeDTO::Wrapper::Class::getType()));
	}

	return jvo;
}

AreaInfoPageJsonVO::Wrapper AreaInfoController::execAreaInfoList(const AreaInfoQuery::Wrapper& query)
{
	auto jvo = AreaInfoPageJsonVO::createShared();
	AreaInfoService service;
	auto list = service.List(query);
	jvo->success(list);
	return jvo;
}

StringJsonVO::Wrapper AreaInfoController::execAddAreaInfo(const AreaInfoUpdDTO::Wrapper& dto, const PayloadDTO& payload)
{
	auto jvo = StringJsonVO::createShared();
	AreaInfoService service;
	if (service.addData(dto, payload))
	{
		jvo->success("OK");
	}
	else {
		jvo->fail("NO");
	}
	return jvo;
}

StringJsonVO::Wrapper AreaInfoController::execBatchDel(const BatchDelIdsDTO::Wrapper& dto)
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

	// ba_city is the leaf table, no downstream reference check needed
	AreaInfoService service;
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
