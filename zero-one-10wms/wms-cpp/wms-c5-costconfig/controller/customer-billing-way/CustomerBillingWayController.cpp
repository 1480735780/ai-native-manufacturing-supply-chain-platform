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
#include "CustomerBillingWayController.h"
#include "service/customer-billing-way/CustomerBillingWayService.h"
#include "ExcelComponent.h"
#include <sstream>
#include <vector>
#include <string>

// create
StringJsonVO::Wrapper CustomerBillingWayController::execAddCustomerBillingWay(const CustomerBillingWayAddDTO::Wrapper& dto) {
	CustomerBillingWayService service;
	auto res = service.insert(dto);
	auto jvo = StringJsonVO::createShared();
	if (res != "") jvo->success(res);
	else jvo->fail(res);
	return jvo;
}

// update
StringJsonVO::Wrapper CustomerBillingWayController::execModifyCustomerBillingWay(const CustomerBillingWayModifyDTO::Wrapper& dto) {
	auto jvo = StringJsonVO::createShared();
	if (dto->id == "") {
		jvo->init(String("error: parameter::id cannot be empty!"), RS_PARAMS_INVALID);
		return jvo;
	}
	CustomerBillingWayService service;
	if (service.update(dto)) jvo->success(dto->id);
	else jvo->fail(dto->id);
	return jvo;
}

// name list
CustomerBillingWayNameListPageJsonVO::Wrapper CustomerBillingWayController::execQueryCustomerBillingWayName(const CustomerBillingWayQuery::Wrapper& query) {
	CustomerBillingWayService service;
	auto res = service.listName(query);
	auto jvo = CustomerBillingWayNameListPageJsonVO::createShared();
	jvo->success(res);
	return jvo;
}

// page list
CustomerBillingWayPageJsonVO::Wrapper CustomerBillingWayController::execQueryCustomerBillingWayPage(const CustomerBillingWayQuery::Wrapper& query) {
	CustomerBillingWayService service;
	auto res = service.listAll(query);
	auto jvo = CustomerBillingWayPageJsonVO::createShared();
	jvo->success(res);
	return jvo;
}

// batch delete
StringJsonVO::Wrapper CustomerBillingWayController::execDeleteCustomerBillingWay(const List<String>& ids)
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
	CustomerBillingWayService service;
	int affected = service.removeByIds(idList);
	if (affected > 0) jvo->success(String(std::to_string(affected)));
	else jvo->fail(String("no row deleted"));
	return jvo;
}

// export
std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> CustomerBillingWayController::execExportCustomerBillingWay()
{
	CustomerBillingWayService service;
	list<CustomerBillingWayDO> result = service.listForExport();
	std::vector<std::vector<std::string>> data;
	std::vector<std::string> header;
	header.push_back(ZH_WORDS_GETTER("cusbillway.field.code"));
	header.push_back(ZH_WORDS_GETTER("cusbillway.field.name"));
	header.push_back(ZH_WORDS_GETTER("cusbillway.field.cus_sta_del"));
	data.push_back(header);
	for (auto r : result) {
		std::vector<std::string> row;
		row.push_back(r.getKehuzhuangtaiCode());
		row.push_back(r.getKehuzhuangtaiName());
		row.push_back(r.getCusStaDel());
		data.push_back(row);
	}
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff(ZH_WORDS_GETTER("cusbillway.file.sheetname"), data);
	auto fstring = String(reinterpret_cast<const char*>(buff.data()), buff.size());
	if (!fstring) {
		return createResponse(oatpp::web::protocol::http::Status::CODE_404, "Export failed");
	}
	auto response = createResponse(oatpp::web::protocol::http::Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=customer-billing-way.xlsx");
	return response;
}

// import
StringJsonVO::Wrapper CustomerBillingWayController::execImportCustomerBillingWay(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
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
			if (cells.size() >= 3 && !cells[0].empty()) rows.push_back(cells);
		}
	}
	catch (const std::exception& e) {
		std::cout << "CustomerBillingWay import load excel fail: " << e.what() << std::endl;
		jvo->init(String("error: invalid excel file"), RS_PARAMS_INVALID);
		return jvo;
	}

	CustomerBillingWayService service;
	int ok = service.importRows(rows, payload.getUsername(), payload.getOrgcode(), payload.getCompanycode());
	if (ok > 0) jvo->success(String(std::to_string(ok)));
	else jvo->fail(String("0"));
	return jvo;
}

// build full create DTO
CustomerBillingWayAddDTO::Wrapper CustomerBillingWayController::buildFullDTO(const CustomerBillingWayBaseAddDTO::Wrapper& baseDto, const PayloadDTO& payload) {
	auto fullDto = CustomerBillingWayAddDTO::createShared();
	fullDto->code = baseDto->code;
	fullDto->name = baseDto->name;
	fullDto->cus_sta_del = baseDto->cus_sta_del;

	fullDto->create_name = payload.getUsername();
	fullDto->create_by = payload.getUsername();
	fullDto->update_name = payload.getUsername();
	fullDto->update_by = payload.getUsername();
	fullDto->sys_org_code = payload.getOrgcode();
	fullDto->sys_company_code = payload.getCompanycode();
	return fullDto;
}

// build full update DTO
CustomerBillingWayModifyDTO::Wrapper CustomerBillingWayController::buildFullDTO(const CustomerBillingWayBaseModifyDTO::Wrapper& baseDto, const PayloadDTO& payload) {
	auto fullDto = CustomerBillingWayModifyDTO::createShared();
	fullDto->id = baseDto->id;
	fullDto->code = baseDto->code;
	fullDto->name = baseDto->name;
	fullDto->cus_sta_del = baseDto->cus_sta_del;

	fullDto->update_name = payload.getUsername();
	fullDto->update_by = payload.getUsername();
	fullDto->sys_org_code = payload.getOrgcode();
	fullDto->sys_company_code = payload.getCompanycode();
	return fullDto;
}
