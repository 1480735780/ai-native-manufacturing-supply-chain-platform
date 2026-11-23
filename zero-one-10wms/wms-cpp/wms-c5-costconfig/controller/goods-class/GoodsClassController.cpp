/*
 Copyright Zero One Star. All rights reserved.
 
 @Author: Ann
 @Date: 2025/2/23 17:47
 
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
#include "GoodsClassController.h"
#include "service/goods-class/GoodsClassService.h"
#include "ExcelComponent.h"
#include <sstream>
#include <vector>
#include <string>


// 新增计费商品类接口处理
StringJsonVO::Wrapper GoodsClassController::execAddGoodsClass(const GoodsClassAddDTO::Wrapper& dto) {
	// 不需要参数验证
	// 直接传给service即可
	GoodsClassService service;

	// service执行插入,仍然使用DTO,返回操作的id 
	// 是否考虑只用返回是否操作成功 ?
	auto res = service.insert(dto);
	auto jvo = StringJsonVO::createShared();

	// 插入成功
	if (res != "") {
		jvo->success(res);
	}
	else {
		jvo->fail(res);
	}

	return jvo;

}



// 修改计费商品类接口处理
StringJsonVO::Wrapper GoodsClassController::execModifyGoodsClass(const GoodsClassModifyDTO::Wrapper& dto) {

	// 验证下id是否合法
	// 只要传入的id存在，我们就认为是合法的
	auto jvo = StringJsonVO::createShared();
	if (dto->id == "") {
		// 是否更新成功
		jvo->fail("");
	}
	else {
		GoodsClassService service;
		auto res = service.update(dto);
		if (res) {
			jvo->success(dto->id);
		}
		else {
			jvo->fail(dto->id);
		}
	}


	return jvo;

}



// 查询计费商品类名称接口处理
GoodsClassNameListPageJsonVO::Wrapper GoodsClassController::execQueryGoodClassName(const GoodClassQuery::Wrapper& query) {

	// 直接调用service
	GoodsClassService service;

	auto res = service.listName(query);

	// 报错 返回空
	auto jvo = GoodsClassNameListPageJsonVO::createShared();

	jvo->success(res);

	return jvo;

}



// 查询计费商品类(分页)接口处理
GoodsClassPageJsonVO::Wrapper GoodsClassController::execQueryGoodClassPage(const GoodClassQuery::Wrapper& query) {

	// 直接调用service
	GoodsClassService service;

	auto res = service.listAll(query);

	// 报错 返回空
	auto jvo = GoodsClassPageJsonVO::createShared();

	jvo->success(res);

	return jvo;

}




// 辅助方法：组装完整DTO
GoodsClassModifyDTO::Wrapper GoodsClassController::buildFullDTO(const GoodsClassBaseModifyDTO::Wrapper& baseDto, const PayloadDTO& payload) {
	auto fullDto = GoodsClassModifyDTO::createShared();

	// 复制基础字段
	fullDto->id = baseDto->id;
	fullDto->name = baseDto->name;
	fullDto->code = baseDto->code;


	// 填充Token中的信息
	//fullDto->create_name = payload.getUsername();
	//fullDto->create_by = payload.getUsername();
	fullDto->update_by = payload.getUsername();
	fullDto->sys_org_code = payload.getOrgcode();
	fullDto->sys_company_code = payload.getCompanycode();
	//fullDto->create_date = DateUtil::getCurrentTime();

	return fullDto;

}



GoodsClassAddDTO::Wrapper GoodsClassController::buildFullDTO(const GoodsClassBaseAddDTO::Wrapper& baseDto, const PayloadDTO& payload) {
	auto fullDto = GoodsClassAddDTO::createShared();

	// 复制基础字段
	fullDto->name = baseDto->name;
	fullDto->code = baseDto->code;


	// 填充Token中的信息
	//fullDto->create_name = payload.getUsername();
	fullDto->create_by = payload.getUsername();
	fullDto->update_by = payload.getUsername();
	fullDto->sys_org_code = payload.getOrgcode();
	fullDto->sys_company_code = payload.getCompanycode();
	//fullDto->sys_org_code = payload->getOrgCode();
	//fullDto->sys_company_code = payload->getCompanyCode();
	//fullDto->create_date = DateUtil::getCurrentTime();

	return fullDto;

}
// 批量删除计费商品类接口处理
StringJsonVO::Wrapper GoodsClassController::execDeleteGoodsClass(const List<String>& ids)
{
	auto jvo = StringJsonVO::createShared();
	if (!ids || ids->size() == 0)
	{
		jvo->init(String("error: parameter::ids cannot be empty!"), RS_PARAMS_INVALID);
		return jvo;
	}
	std::vector<std::string> idList;
	for (const auto& id : *ids)
	{
		if (*id == "") continue;
		idList.push_back(id.getValue(""));
	}
	if (idList.empty())
	{
		jvo->init(String("error: parameter::ids cannot be empty!"), RS_PARAMS_INVALID);
		return jvo;
	}
	GoodsClassService service;
	int affected = service.removeByIds(idList);
	if (affected > 0) jvo->success(String(std::to_string(affected)));
	else jvo->fail(String("no row deleted"));
	return jvo;
}

// 导出计费商品类接口处理
std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> GoodsClassController::execExportGoodsClass()
{
	GoodsClassService service;
	list<GoodsClassDO> result = service.listForExport();
	std::vector<std::vector<std::string>> data;
	std::vector<std::string> header;
	header.push_back(ZH_WORDS_GETTER("goodsclass.field.code"));
	header.push_back(ZH_WORDS_GETTER("goodsclass.field.name"));
	data.push_back(header);
	for (auto r : result)
	{
		std::vector<std::string> row;
		row.push_back(r.getGoodsClassCode());
		row.push_back(r.getGoodsClassName());
		data.push_back(row);
	}
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff(ZH_WORDS_GETTER("goodsclass.file.sheetname"), data);
	auto fstring = String(reinterpret_cast<const char*>(buff.data()), buff.size());
	if (!fstring)
	{
		return createResponse(oatpp::web::protocol::http::Status::CODE_404, "Export failed");
	}
	auto response = createResponse(oatpp::web::protocol::http::Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=goods-class.xlsx");
	return response;
}

// 导入计费商品类接口处理
StringJsonVO::Wrapper GoodsClassController::execImportGoodsClass(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	// 1 初始化多部分读取器
	API_MULTIPART_INIT(container, reader);
	// 2 配置读取器
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);
	// 3 读取请求体
	request->transferBody(&reader);
	// 4 解析文件字段
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);

	auto jvo = StringJsonVO::createShared();
	if (!file)
	{
		jvo->init(String("error: file is required"), RS_PARAMS_INVALID);
		return jvo;
	}

	// 5 内存解析 excel，取活动工作表，跳过表头
	std::vector<std::vector<std::string>> rows;
	try
	{
		xlnt::workbook wb;
		std::stringstream ss;
		ss.write(file->data(), file->size());
		wb.load(ss);
		xlnt::worksheet ws = wb.active_sheet();
		bool header = true;
		for (const auto& row : ws.rows())
		{
			if (header) { header = false; continue; }
			std::vector<std::string> cells;
			for (const auto& cell : row) cells.push_back(cell.to_string());
			if (cells.size() >= 2 && !cells[0].empty()) rows.push_back(cells);
		}
	}
	catch (const std::exception& e)
	{
		std::cout << "GoodsClass import load excel fail: " << e.what() << std::endl;
		jvo->init(String("error: invalid excel file"), RS_PARAMS_INVALID);
		return jvo;
	}

	// 6 写入数据库
	GoodsClassService service;
	int ok = service.importRows(rows, payload.getUsername(), payload.getOrgcode(), payload.getCompanycode());
	if (ok > 0) jvo->success(String(std::to_string(ok)));
	else jvo->fail(String("0"));
	return jvo;
}
