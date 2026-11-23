#include "stdafx.h"
#include "OverallInventoryController.h"
#include "../../service/overallInventory/InventorylistService.h"
#include "../../service/check/CheckService.h"
#include "../../domain/do/check/CheckDO.h"
#include "FastDfsClient.h"
#include <ExcelComponent.h>

// 分页查询综合盘点列表
InventoryJsonPageVO::Wrapper OverallInventoryController::execQuerySample(const InventorylistQuery::Wrapper& query, const PayloadDTO& payload)
{
	// 定义一个Service
	InventorylistService service;
	// 查询数据
	auto result = service.listAll(query);
	// 响应结果
	auto jvo = InventoryJsonPageVO::createShared();
	jvo->success(result);
	return jvo;
}

// 批量生成盘点任务
InventoryInsertTaskJsonVO::Wrapper OverallInventoryController::execInsertSttTaskMulti(const InventoryInsertTaskDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// 构建返回数据（成功生成的id集合）
	auto returnDto = InventoryInsertTaskDTO::createShared();
	returnDto->ids = Vector<String>::createShared();
	// 定义返回数据对象
	auto jvo = InventoryInsertTaskJsonVO::createShared();

	// 参数校验：空集合直接返回参数错误
	if (!dto->ids || dto->ids->empty())
	{
		jvo->init(nullptr, RS_PARAMS_INVALID);
		return jvo;
	}

	// 调用业务层执行批量生成
	InventorylistService service;
	bool ok = service.saveBatchByStockIds(dto->ids, payload, returnDto->ids);
	if (ok && returnDto->ids->size() == dto->ids->size())
		jvo->success(returnDto);
	else
		jvo->fail(returnDto);
	return jvo;
}

// 编辑盘点任务
Uint64JsonVO::Wrapper OverallInventoryController::execModifySttTask(const InventoryModifyDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	if (!dto->id || dto->id->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 调用业务层执行修改
	InventorylistService service;
	bool ok = service.updateData(dto, payload);
	if (ok)
		jvo->success(UInt64(1));
	else
		jvo->fail(UInt64(0ULL));
	return jvo;
}

// 导出盘点差异数据（从盘点任务表导出全量数据，含账面数量与实盘数量，供前端计算差异）
std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> OverallInventoryController::execExportDifference(const CheckQuery::Wrapper& query)
{
	CheckService service;
	auto result = service.exportData(query);
	std::vector<CheckDO> datas(result.begin(), result.end());

	// 创建表头数据
	std::vector<std::string> headers = {
		ZH_WORDS_GETTER("mql.rest.id"),              // 唯一标识
		ZH_WORDS_GETTER("mql.rest.bin_id"),          // 储位
		ZH_WORDS_GETTER("mql.rest.tin_id"),          // 托盘
		ZH_WORDS_GETTER("mql.goods.goods_id"),       // 商品编码
		ZH_WORDS_GETTER("mql.goods.goods_name"),     // 商品名称
		ZH_WORDS_GETTER("mql.goods.goods_qua"),      // 账面数量
		ZH_WORDS_GETTER("mql.stt.stt_qua"),          // 实盘数量
		ZH_WORDS_GETTER("mql.goods.goods_unit"),     // 单位
		ZH_WORDS_GETTER("mql.goods.goods_pro_data"), // 生产日期
		ZH_WORDS_GETTER("mql.goods.goods_batch"),    // 批次
		ZH_WORDS_GETTER("mql.cus.cus_name"),         // 货主名称
		ZH_WORDS_GETTER("mql.cus.cus_code"),         // 货主
		ZH_WORDS_GETTER("mql.stt.stt_sta"),          // 盘点状态
		ZH_WORDS_GETTER("mql.stt.stt_type"),         // 盘点类型
		ZH_WORDS_GETTER("mql.creat.create_name"),    // 创建人名称
		ZH_WORDS_GETTER("mql.creat.create_date"),    // 创建日期
	};

	std::vector<std::vector<std::string>> data;
	data.push_back(headers);

	for (const auto &item : datas)
	{
		std::vector<std::string> row;
		row.push_back(item.getId());
		row.push_back(item.getBin_id());
		row.push_back(item.getTin_id());
		row.push_back(item.getGoods_id());
		row.push_back(item.getGoods_name());
		row.push_back(item.getGoods_qua());
		row.push_back(item.getStt_qua());
		row.push_back(item.getGoods_unit());
		row.push_back(item.getGoods_pro_data());
		row.push_back(item.getGoods_batch());
		row.push_back(item.getCus_name());
		row.push_back(item.getCus_code());
		row.push_back(item.getStt_sta());
		row.push_back(item.getStt_type());
		row.push_back(item.getCreate_name());
		row.push_back(item.getCreate_date());
		data.push_back(row);
	}

	// 定义保存数据位置和页签名称
	// 注意：因为xlnt不能存储非utf8编码的字符，所以中文字需要从配置文件中获取
	std::string sheetName = ZH_WORDS_GETTER("overall.inventorylist.excel.sheet");
	// 文件名
	std::string filename = ZH_WORDS_GETTER("overall.inventorylist.excel.filename") + ".xlsx";

	// 生成文件内容（内存直返，不依赖 FastDFS）
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff(sheetName, data);
	const char *tsData = reinterpret_cast<const char *>(buff.data());
	auto fstring = String(tsData, buff.size());

	if (!fstring)
	{
		std::cerr << "Failed to build excel buffer: " << std::strerror(errno) << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	// 创建响应头
	auto response = createResponse(Status::CODE_200, fstring);

	// 设置响应头信息
	response->putHeader("Content-Disposition", "attachment; filename=InventoryDifference.xlsx");

	return response;
}
