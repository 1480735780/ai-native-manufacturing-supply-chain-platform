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
#include "CostTemplateController.h"
#include "service/cost-template/CostTemplateService.h"
#include "ExcelComponent.h"
#include <sstream>
#include <vector>
#include <string>

// create
StringJsonVO::Wrapper CostTemplateController::execAddCostTemplate(const CostTemplateAddDTO::Wrapper& dto) {
	CostTemplateService service;
	auto res = service.insert(dto);
	auto jvo = StringJsonVO::createShared();
	if (res != "") jvo->success(res);
	else jvo->fail(res);
	return jvo;
}

// update
StringJsonVO::Wrapper CostTemplateController::execModifyCostTemplate(const CostTemplateModifyDTO::Wrapper& dto) {
	auto jvo = StringJsonVO::createShared();
	if (dto->id == "") {
		jvo->init(String("error: parameter::id cannot be empty!"), RS_PARAMS_INVALID);
		return jvo;
	}
	CostTemplateService service;
	if (service.update(dto)) jvo->success(dto->id);
	else jvo->fail(dto->id);
	return jvo;
}

// name list
CostTemplateNameListPageJsonVO::Wrapper CostTemplateController::execQueryCostTemplateName(const CostTemplateQuery::Wrapper& query) {
	CostTemplateService service;
	auto res = service.listName(query);
	auto jvo = CostTemplateNameListPageJsonVO::createShared();
	jvo->success(res);
	return jvo;
}

// page list
CostTemplatePageJsonVO::Wrapper CostTemplateController::execQueryCostTemplatePage(const CostTemplateQuery::Wrapper& query) {
	CostTemplateService service;
	auto res = service.listAll(query);
	auto jvo = CostTemplatePageJsonVO::createShared();
	jvo->success(res);
	return jvo;
}

// batch delete
StringJsonVO::Wrapper CostTemplateController::execDeleteCostTemplate(const List<String>& ids)
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
	CostTemplateService service;
	int affected = service.removeByIds(idList);
	if (affected > 0) jvo->success(String(std::to_string(affected)));
	else jvo->fail(String("no row deleted"));
	return jvo;
}

// export
std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> CostTemplateController::execExportCostTemplate()
{
	CostTemplateService service;
	list<CostTemplateDO> result = service.listForExport();
	std::vector<std::vector<std::string>> data;
	std::vector<std::string> header;
	header.push_back(ZH_WORDS_GETTER("costtemplate.field.code"));
	header.push_back(ZH_WORDS_GETTER("costtemplate.field.cost_jg"));
	header.push_back(ZH_WORDS_GETTER("costtemplate.field.cost_sl"));
	header.push_back(ZH_WORDS_GETTER("costtemplate.field.cost_zk"));
	header.push_back(ZH_WORDS_GETTER("costtemplate.field.cost_bhs"));
	header.push_back(ZH_WORDS_GETTER("costtemplate.field.cost_hs"));
	header.push_back(ZH_WORDS_GETTER("costtemplate.field.free_day"));
	header.push_back(ZH_WORDS_GETTER("costtemplate.field.free_day2"));
	data.push_back(header);
	for (auto r : result) {
		std::vector<std::string> row;
		row.push_back(r.getCostCode());
		row.push_back(r.getCostJg());
		row.push_back(r.getCostSl());
		row.push_back(r.getCostZk());
		row.push_back(r.getCostBhs());
		row.push_back(r.getCostHs());
		row.push_back(r.getFreeDay());
		row.push_back(r.getFreeDay2());
		data.push_back(row);
	}
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff(ZH_WORDS_GETTER("costtemplate.file.sheetname"), data);
	auto fstring = String(reinterpret_cast<const char*>(buff.data()), buff.size());
	if (!fstring) {
		return createResponse(oatpp::web::protocol::http::Status::CODE_404, "Export failed");
	}
	auto response = createResponse(oatpp::web::protocol::http::Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=cost-template.xlsx");
	return response;
}

// import
StringJsonVO::Wrapper CostTemplateController::execImportCostTemplate(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
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
			if (cells.size() >= 8 && !cells[0].empty()) rows.push_back(cells);
		}
	}
	catch (const std::exception& e) {
		std::cout << "CostTemplate import load excel fail: " << e.what() << std::endl;
		jvo->init(String("error: invalid excel file"), RS_PARAMS_INVALID);
		return jvo;
	}

	CostTemplateService service;
	int ok = service.importRows(rows, payload.getUsername(), payload.getOrgcode(), payload.getCompanycode());
	if (ok > 0) jvo->success(String(std::to_string(ok)));
	else jvo->fail(String("0"));
	return jvo;
}

// build full create DTO
CostTemplateAddDTO::Wrapper CostTemplateController::buildFullDTO(const CostTemplateBaseAddDTO::Wrapper& baseDto, const PayloadDTO& payload) {
	auto fullDto = CostTemplateAddDTO::createShared();
	fullDto->code = baseDto->code;
	fullDto->cost_jg = baseDto->cost_jg;
	fullDto->cost_sl = baseDto->cost_sl;
	fullDto->cost_zk = baseDto->cost_zk;
	fullDto->cost_bhs = baseDto->cost_bhs;
	fullDto->cost_hs = baseDto->cost_hs;
	fullDto->free_day = baseDto->free_day;
	fullDto->free_day2 = baseDto->free_day2;

	fullDto->create_name = payload.getUsername();
	fullDto->create_by = payload.getUsername();
	fullDto->update_name = payload.getUsername();
	fullDto->update_by = payload.getUsername();
	fullDto->sys_org_code = payload.getOrgcode();
	fullDto->sys_company_code = payload.getCompanycode();
	return fullDto;
}

// build full update DTO
CostTemplateModifyDTO::Wrapper CostTemplateController::buildFullDTO(const CostTemplateBaseModifyDTO::Wrapper& baseDto, const PayloadDTO& payload) {
	auto fullDto = CostTemplateModifyDTO::createShared();
	fullDto->id = baseDto->id;
	fullDto->code = baseDto->code;
	fullDto->cost_jg = baseDto->cost_jg;
	fullDto->cost_sl = baseDto->cost_sl;
	fullDto->cost_zk = baseDto->cost_zk;
	fullDto->cost_bhs = baseDto->cost_bhs;
	fullDto->cost_hs = baseDto->cost_hs;
	fullDto->free_day = baseDto->free_day;
	fullDto->free_day2 = baseDto->free_day2;

	fullDto->update_name = payload.getUsername();
	fullDto->update_by = payload.getUsername();
	fullDto->sys_org_code = payload.getOrgcode();
	fullDto->sys_company_code = payload.getCompanycode();
	return fullDto;
}
