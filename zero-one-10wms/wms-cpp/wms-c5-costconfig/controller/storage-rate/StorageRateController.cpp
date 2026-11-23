/*
 Copyright Zero One Star. All rights reserved.

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

#include "stdafx.h"
#include "StorageRateController.h"
#include "service/storage-rate/StorageRateService.h"
#include "ExcelComponent.h"
#include <sstream>
#include <vector>
#include <string>

// create
StringJsonVO::Wrapper StorageRateController::execAddStorageRate(const StorageRateAddDTO::Wrapper& dto) {
	StorageRateService service;
	auto res = service.insert(dto);
	auto jvo = StringJsonVO::createShared();
	if (res != "") jvo->success(res);
	else jvo->fail(res);
	return jvo;
}

// update
StringJsonVO::Wrapper StorageRateController::execModifyStorageRate(const StorageRateModifyDTO::Wrapper& dto) {
	auto jvo = StringJsonVO::createShared();
	if (dto->id == "") {
		jvo->init(String("error: parameter::id cannot be empty!"), RS_PARAMS_INVALID);
		return jvo;
	}
	StorageRateService service;
	if (service.update(dto)) jvo->success(dto->id);
	else jvo->fail(dto->id);
	return jvo;
}

// name list
StorageRateNameListPageJsonVO::Wrapper StorageRateController::execQueryStorageRateName(const StorageRateQuery::Wrapper& query) {
	StorageRateService service;
	auto res = service.listName(query);
	auto jvo = StorageRateNameListPageJsonVO::createShared();
	jvo->success(res);
	return jvo;
}

// page list
StorageRatePageJsonVO::Wrapper StorageRateController::execQueryStorageRatePage(const StorageRateQuery::Wrapper& query) {
	StorageRateService service;
	auto res = service.listAll(query);
	auto jvo = StorageRatePageJsonVO::createShared();
	jvo->success(res);
	return jvo;
}

// detail
StorageRateDetailJsonVO::Wrapper StorageRateController::execQueryStorageRateDetail(const String& id)
{
	auto jvo = StorageRateDetailJsonVO::createShared();
	if (!id || id->empty()) {
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}
	StorageRateService service;
	auto rows = service.getById(id.getValue(""));
	if (rows.empty()) {
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}
	auto sub = rows.front();
	auto dto = StorageRateDTO::createShared();
	ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub,
		code, CostCode,
		cost_yj, CostYj,
		cost_zk, CostZk,
		cost_sl, CostSl,
		cost_bhs, CostBhs,
		cost_hsj, CostHsj,
		create_name, CreateName,
		create_by, CreateBy,
		create_date, CreateDate,
		update_name, UpdateName,
		update_by, UpdateBy,
		update_date, UpdateDate,
		sys_org_code, SysOrgCode,
		sys_company_code, SysCompanyCode,
		id, Id
	);
	jvo->success(dto);
	return jvo;
}

// batch delete
StringJsonVO::Wrapper StorageRateController::execDeleteStorageRate(const List<String>& ids)
{
	auto jvo = StringJsonVO::createShared();
	if (!ids || ids->size() == 0) {
		jvo->init(String("error: parameter::ids cannot be empty!"), RS_PARAMS_INVALID);
		return jvo;
	}
	std::vector<std::string> idList;
	for (const auto& id : *ids) {
		if (*id == "") continue;
		idList.push_back(id.getValue(""));
	}
	if (idList.empty()) {
		jvo->init(String("error: parameter::ids cannot be empty!"), RS_PARAMS_INVALID);
		return jvo;
	}
	StorageRateService service;
	int affected = service.removeByIds(idList);
	if (affected > 0) jvo->success(String(std::to_string(affected)));
	else jvo->fail(String("no row deleted"));
	return jvo;
}

// export
std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> StorageRateController::execExportStorageRate()
{
	StorageRateService service;
	list<StorageRateDO> result = service.listForExport();
	std::vector<std::vector<std::string>> data;
	std::vector<std::string> header;
	header.push_back(ZH_WORDS_GETTER("storagerate.field.code"));
	header.push_back(ZH_WORDS_GETTER("storagerate.field.cost_yj"));
	header.push_back(ZH_WORDS_GETTER("storagerate.field.cost_zk"));
	header.push_back(ZH_WORDS_GETTER("storagerate.field.cost_sl"));
	header.push_back(ZH_WORDS_GETTER("storagerate.field.cost_bhs"));
	header.push_back(ZH_WORDS_GETTER("storagerate.field.cost_hsj"));
	data.push_back(header);
	for (auto r : result) {
		std::vector<std::string> row;
		row.push_back(r.getCostCode());
		row.push_back(r.getCostYj());
		row.push_back(r.getCostZk());
		row.push_back(r.getCostSl());
		row.push_back(r.getCostBhs());
		row.push_back(r.getCostHsj());
		data.push_back(row);
	}
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff(ZH_WORDS_GETTER("storagerate.file.sheetname"), data);
	auto fstring = String(reinterpret_cast<const char*>(buff.data()), buff.size());
	if (!fstring) {
		return createResponse(oatpp::web::protocol::http::Status::CODE_404, "Export failed");
	}
	auto response = createResponse(oatpp::web::protocol::http::Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=storage-rate.xlsx");
	return response;
}

// import
StringJsonVO::Wrapper StorageRateController::execImportStorageRate(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	API_MULTIPART_INIT(container, reader);
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);
	request->transferBody(&reader);
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);

	auto jvo = StringJsonVO::createShared();
	if (!file) {
		jvo->init(String("error: file is required"), RS_PARAMS_INVALID);
		return jvo;
	}

	std::vector<std::vector<std::string>> rows;
	try {
		xlnt::workbook wb;
		std::stringstream ss;
		ss.write(file->data(), file->size());
		wb.load(ss);
		xlnt::worksheet ws = wb.active_sheet();
		bool header = true;
		for (const auto& row : ws.rows()) {
			if (header) { header = false; continue; }
			std::vector<std::string> cells;
			for (const auto& cell : row) cells.push_back(cell.to_string());
			if (cells.size() >= 6 && !cells[0].empty()) rows.push_back(cells);
		}
	}
	catch (const std::exception& e) {
		std::cout << "StorageRate import load excel fail: " << e.what() << std::endl;
		jvo->init(String("error: invalid excel file"), RS_PARAMS_INVALID);
		return jvo;
	}

	StorageRateService service;
	int ok = service.importRows(rows, payload.getUsername(), payload.getOrgcode(), payload.getCompanycode());
	if (ok > 0) jvo->success(String(std::to_string(ok)));
	else jvo->fail(String("0"));
	return jvo;
}

// build full create DTO
StorageRateAddDTO::Wrapper StorageRateController::buildFullDTO(const StorageRateBaseAddDTO::Wrapper& baseDto, const PayloadDTO& payload) {
	auto fullDto = StorageRateAddDTO::createShared();
	fullDto->code = baseDto->code;
	fullDto->cost_yj = baseDto->cost_yj;
	fullDto->cost_zk = baseDto->cost_zk;
	fullDto->cost_sl = baseDto->cost_sl;
	fullDto->cost_bhs = baseDto->cost_bhs;
	fullDto->cost_hsj = baseDto->cost_hsj;

	fullDto->create_name = payload.getUsername();
	fullDto->create_by = payload.getUsername();
	fullDto->update_name = payload.getUsername();
	fullDto->update_by = payload.getUsername();
	fullDto->sys_org_code = payload.getOrgcode();
	fullDto->sys_company_code = payload.getCompanycode();
	return fullDto;
}

// build full update DTO
StorageRateModifyDTO::Wrapper StorageRateController::buildFullDTO(const StorageRateBaseModifyDTO::Wrapper& baseDto, const PayloadDTO& payload) {
	auto fullDto = StorageRateModifyDTO::createShared();
	fullDto->id = baseDto->id;
	fullDto->code = baseDto->code;
	fullDto->cost_yj = baseDto->cost_yj;
	fullDto->cost_zk = baseDto->cost_zk;
	fullDto->cost_sl = baseDto->cost_sl;
	fullDto->cost_bhs = baseDto->cost_bhs;
	fullDto->cost_hsj = baseDto->cost_hsj;

	fullDto->update_name = payload.getUsername();
	fullDto->update_by = payload.getUsername();
	fullDto->sys_org_code = payload.getOrgcode();
	fullDto->sys_company_code = payload.getCompanycode();
	return fullDto;
}
