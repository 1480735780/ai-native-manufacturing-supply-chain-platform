#include "stdafx.h"
#include "BareaInfoController.h"
#include "dao/districtinfo/BareaInfoDAO.h"
#include "Macros.h"
#include "ExcelComponent.h"
#include "service/regioninfo/DareaInfoService.h"
#include "service/regioninfo/RegionInfoService.h"
#include "service/districtinfo/BareaInfoService.h"
#include "domain/do/regioninfo/RegionInfoDO.h"
#include <string>
#include "ServerInfo.h"
#include "NacosClient.h"
#include "FastDfsClient.h"
#include "SimpleDateTimeFormat.h"

StringJsonVO::Wrapper BareaInfoController::execImport(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
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
	auto vec = ExcelComponent::readIntoVector(file->data(), file->size(), ZH_WORDS_GETTER("BareaInfo.info"));
	if (vec.size() <= 1)
	{
		jvo->fail("Empty File");
		return jvo;
	}

	// skip header, validate 3 columns, tolerate bad number
	std::vector<std::vector<std::string>> valid;
	int skipped = 0;
	for (size_t i = 1; i < vec.size(); i++)
	{
		auto& row = vec[i];
		if (row.size() < 3 || row[0].empty() || row[1].empty()) { skipped++; continue; }
		try {
			(void)std::stod(row[2]);
		} catch (...) {
			skipped++; continue;
		}
		valid.push_back(row);
	}
	if (valid.empty())
	{
		jvo->fail("No Valid Rows");
		return jvo;
	}

	RegionInfoService service;
	int ok = service.import(valid, payload);
	std::string msg = "imported " + std::to_string(ok) + " rows, skipped " + std::to_string(skipped) + ", failed " + std::to_string((int)valid.size() - ok);
	if (ok <= 0)
	{
		jvo->fail(String(msg));
		return jvo;
	}
	jvo->success(String(msg));
	return jvo;
}

std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> BareaInfoController::execExport()
{
	BareaInfoDAO dao;
	std::list<BareaInfoDO> d = dao.exportBareaInfo();
	std::vector<std::vector<std::string>> data;
	std::vector<std::string> head;
	head.push_back(ZH_WORDS_GETTER("BareaInfo.excel.head1"));
	head.push_back(ZH_WORDS_GETTER("BareaInfo.excel.head2"));
	head.push_back(ZH_WORDS_GETTER("BareaInfo.excel.head3"));
	data.push_back(head);
	for (BareaInfoDO Obj : d)
	{
		std::vector<std::string> vec;
		vec.push_back(Obj.getBarea_code());
		vec.push_back(Obj.getBarea_name());
		vec.push_back(std::to_string(Obj.getBarea_rdata()));
		data.push_back(vec);
	}

	// build excel in memory, no template file needed
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff(ZH_WORDS_GETTER("BareaInfo.info"), data);
	const char* tsData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(tsData, buff.size());

	if (!fstring)
	{
		std::cerr << "Failed to build excel buffer" << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	auto response = createResponse(Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=bareainfo.xlsx");
	return response;
}

Uint64JsonVO::Wrapper BareaInfoController::execAdd(const RegionInfoDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	// 非空校验
	if (!dto->region_code || !dto->region_name || !dto->region_rdata)
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}

	// 定义一个Service
	RegionInfoService service;
	// 执行数据新增
	uint64_t id = service.saveData(dto, payload);
	if (id > 0) {
		jvo->success(UInt64(id));
	}
	else
	{
		jvo->fail(UInt64(id));
	}
	//响应结果
	return jvo;
}

StringJsonVO::Wrapper BareaInfoController::execDelete(const String& region_code)
{
	// 定义返回数据对象
	auto jvo = StringJsonVO::createShared();
	// 参数校验
	if (!region_code || region_code->empty())
	{
		jvo->init("-1", RS_PARAMS_INVALID);
		return jvo;
	}
	// 定义一个Service
	RegionInfoService service;
	// 执行数据删除

	if (service.removeData(region_code)) {
		jvo->success(region_code);
	}
	else
	{
		jvo->fail(region_code);
	}
	// 响应结果
	return jvo;
}

StringJsonVO::Wrapper BareaInfoController::execModify(const RegionModifyDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// 定义返回数据对象
	auto jvo = StringJsonVO::createShared();
	// 参数校验
	if (!dto->region_code || !dto->region_name || !dto->region_rdata || !dto->id)
	{
		jvo->init("-1", RS_PARAMS_INVALID);
		return jvo;
	}
	// 定义一个Service
	RegionInfoService service;
	// 执行数据修改
	if (service.updateData(dto, payload)) {
		jvo->success(dto->id);
	}
	else
	{
		jvo->fail("-1");
	}
	// 响应结果
	return jvo;
}

BareaNameListJsonVO::Wrapper BareaInfoController::execNameList()
{
	auto jvo = BareaNameListJsonVO::createShared();
	BareaInfoDAO dao;
	auto namelist = dao.nameList();
	auto list = List<BareaNameDTO::Wrapper>::createShared();
	for (auto obj : namelist)
	{
		auto dto = BareaNameDTO::createShared();
		dto->id = obj.getId();
		dto->name = obj.getBarea_name();
		list->push_back(dto);
	}
	jvo->success(list);
	return jvo;
}

BareaInfoPageJsonVO::Wrapper BareaInfoController::execInfoList(const BareaInfoQuery::Wrapper& query)
{
	auto jvo = BareaInfoPageJsonVO::createShared();
	BareaInfoService service;
	auto list = service.list(query);
	jvo->success(list);
	return jvo;
}

StringJsonVO::Wrapper BareaInfoController::execBatchDel(const BatchDelIdsDTO::Wrapper& dto)
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

	// reference check: refuse when barea codes referenced by ba_city
	BareaInfoDAO dao;
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
