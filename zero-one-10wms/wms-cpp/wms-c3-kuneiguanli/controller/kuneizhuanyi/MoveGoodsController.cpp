#include "stdafx.h"	
#include "controller/kuneizhuanyi/MoveGoodsController.h"
#include "service/kuneizhuanyi/MoveGoodsService.h"
#include "ExcelComponent.h"
#include <SimpleDateTimeFormat.h>
#include <filesystem>
#include <sstream>

namespace
{
	std::vector<std::string> splitIds(const oatpp::String& value)
	{
		std::vector<std::string> ids;
		if (!value) return ids;
		std::stringstream ss(value->c_str());
		std::string item;
		while (std::getline(ss, item, ','))
		{
			if (!item.empty()) ids.push_back(item);
		}
		return ids;
	}
}

MoveGoodsPageJsonVO::Wrapper MoveGoodsController::execQueryMoveGoodsList(const MoveGoodsQuery::Wrapper& moveGoodsQuery, const PayloadDTO& payload)
{
	auto jvo = MoveGoodsPageJsonVO::createShared();
	MoveGoodsService service;
	auto res = service.queryList(moveGoodsQuery);
	jvo->success(res);
	return jvo;
}

Uint64JsonVO::Wrapper MoveGoodsController::execModifyMoveGoods(const MoveGoodsModifyDTO::Wrapper& moveGoodsModifyDTO, const PayloadDTO& payload)
{
	auto jvo = Uint64JsonVO::createShared();
	if (!moveGoodsModifyDTO || !moveGoodsModifyDTO->id || moveGoodsModifyDTO->id->empty())
	{
		jvo->init(v_uint64(0), RS_PARAMS_INVALID);
		return jvo;
	}

	MoveGoodsService service;
	if (service.modifyById(moveGoodsModifyDTO, payload.getUsername()))
	{
		jvo->success(v_uint64(1));
	}
	else
	{
		jvo->fail(v_uint64(0));
	}
	return jvo;
}

Uint64JsonVO::Wrapper MoveGoodsController::execBatchMoveGoods(const MoveGoodsBatchDTO::Wrapper& moveGoodsBatchDTO, const PayloadDTO& payload)
{
	auto jvo = Uint64JsonVO::createShared();
	if (!moveGoodsBatchDTO || !moveGoodsBatchDTO->items || moveGoodsBatchDTO->items->empty())
	{
		jvo->init(v_uint64(0), RS_PARAMS_INVALID);
		return jvo;
	}

	MoveGoodsService service;
	uint64_t affected = service.batchTransfer(moveGoodsBatchDTO, payload.getUsername());
	if (affected > 0)
	{
		jvo->success(v_uint64(affected));
	}
	else
	{
		jvo->fail(v_uint64(0));
	}
	return jvo;
}



MoveGoodsDetailedJsonVO::Wrapper MoveGoodsController::execQueryDetailedMoveGoods(const String& id)
{
	// 定义返回数据对象
	auto jvo = MoveGoodsDetailedJsonVO::createShared();

	// 参数校验
	// 非空校验
	if (!id)
	{
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}

	// 定义一个Service
	MoveGoodsService service;
	// 执行数据新增
	auto res = service.getDetailedById(id);
	jvo->success(res);

	//响应结果
	return jvo;
}

void WriteToXlsx(string fileName, vector<vector<string>> data) {
	std::string sheetName = ZH_WORDS_GETTER("move-goods.xlsx.sheet.s1");  // 获取表名

	// 创建 Excel 工作簿
	xlnt::workbook wb;
	xlnt::worksheet ws = wb.active_sheet();
	ws.title(sheetName);

	// 将数据写入 Excel
	for (size_t row = 0; row < data.size(); ++row) {
		for (size_t col = 0; col < data[row].size(); ++col) {
			ws.cell(static_cast<int>(col + 1), static_cast<int>(row + 1)).value(data[row][col]);
		}
	}

	// 保存 Excel 文件
	try {
		wb.save(fileName);
	}
	catch (const std::exception& e) {
		std::cerr << "Error saving Excel file: " << e.what() << std::endl;
	}
}

std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> MoveGoodsController::execDownLoadMoveGoods(const MoveGoodsExcelQuery::Wrapper& query){
	std::string idsStr = query && query->ids ? std::string(query->ids->c_str()) : "";
	std::vector<std::string> ids_str = splitIds(idsStr);
	if (ids_str.empty())
	{
		return createResponse(Status::CODE_400, "ids is required");
	}

	MoveGoodsService service;
	auto res = service.getDownLoadById(ids_str);
	if (res.size() <= 1)
	{
		return createResponse(Status::CODE_404, "No data found");
	}

	std::string filename{ "moveGoods_" + SimpleDateTimeFormat::format("%Y%m%d%H%M%S") + ".xlsx" };
	std::filesystem::path exportPath = std::filesystem::temp_directory_path() / filename;
	std::string export_path = exportPath.string();
	WriteToXlsx(export_path, res);

	auto fstring = String::loadFromFile(export_path.c_str());
	std::error_code ec;
	std::filesystem::remove(exportPath, ec);
	if (!fstring) {
		std::cerr << "Failed to open file: " << export_path << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	auto response = createResponse(Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=" + filename);
	return response;
}

StringJsonVO::Wrapper MoveGoodsController::execBatchRemoveMoveGoods(const String& ids,const PayloadDTO& payload)
{
	// 定义返回数据对象
	auto jvo = StringJsonVO::createShared();
	// 参数校验
	std::vector<std::string> ids_str = splitIds(ids);
	if (ids_str.empty())
	{
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}

	//获取当前用户名称
	std::string usrName = payload.getUsername();

	// 定义一个Service
	MoveGoodsService service;
	// 执行数据删除
	if (service.removeMoveGoods(ids_str,usrName)) {
		jvo->success(ids);
	}
	else
	{
		jvo->fail(ids);
	}
	// 响应结果
	return jvo;
}
