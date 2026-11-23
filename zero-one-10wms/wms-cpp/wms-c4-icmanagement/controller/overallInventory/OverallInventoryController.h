#pragma once
#ifndef _OVERALLINVENTORY_CONTROLLER_
#define _OVERALLINVENTORY_CONTROLLER_

#include "../../../lib-oatpp/include/domain/vo/BaseJsonVO.h"
#include "../../domain/vo/overallInventory/InventorylistVo.h"
#include "../../domain/query/overallInventory/InventorylistQuery.h"
#include "../../domain/dto/overallInventory/InventorylistDto.h"
#include "../../domain/query/check/CheckQuery.h"

// 0 声明API控制器使用宏
#include OATPP_CODEGEN_BEGIN(ApiController) //<- Begin Codegen

/**
 * 盘点管理-综合盘点
 */
class OverallInventoryController : public oatpp::web::server::api::ApiController // 1 继承控制器
{
	// 2 声明控制器构造函数
	API_ACCESS_DECLARE(OverallInventoryController);
	// 3 定义接口
public:
	// 3.1 定义查询接口描述
	ENDPOINT_INFO(querySample) {
		// 定义接口标题
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("overall.inventorylist.huoqupandianlist"));
		// 定义默认授权参数（可选定义，如果定义了，那么下面ENDPOINT里面需要加入API_HANDLER_AUTH_PARAME）
		API_DEF_ADD_AUTH();
		// 定义响应参数格式
		API_DEF_ADD_RSP_JSON_WRAPPER(InventoryJsonPageVO);
		// 定义分页查询参数描述
		API_DEF_ADD_PAGE_PARAMS();
		// 定义其他查询参数描述
		API_DEF_ADD_QUERY_PARAMS(String, "yidongriqi", ZH_WORDS_GETTER("overall.inventorylist.yidongriqi"), "2001-01-01", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cktype", ZH_WORDS_GETTER("overall.inventorylist.cktype"), ZH_WORDS_GETTER("sttOnMove.exampleVal.kuc"), false);
		API_DEF_ADD_QUERY_PARAMS(String, "chuwei", ZH_WORDS_GETTER("overall.inventorylist.chuwei"), "1", false);
		API_DEF_ADD_QUERY_PARAMS(String, "tuopan", ZH_WORDS_GETTER("overall.inventorylist.tuopan"), "A", false);
		API_DEF_ADD_QUERY_PARAMS(String, "huozhu", ZH_WORDS_GETTER("overall.inventorylist.huozhu"), "1250", false);
		API_DEF_ADD_QUERY_PARAMS(String, "huozhumingcheng", ZH_WORDS_GETTER("overall.inventorylist.huozhumingcheng"), "xxxCompany", false);
		API_DEF_ADD_QUERY_PARAMS(String, "shangpinbianma", ZH_WORDS_GETTER("overall.inventorylist.shangpinbianma"), "123", false);
		API_DEF_ADD_QUERY_PARAMS(String, "shangpinshuliang", ZH_WORDS_GETTER("overall.inventorylist.shangpinshuliang"), "100", false);
		API_DEF_ADD_QUERY_PARAMS(String, "shangpinmincheng", ZH_WORDS_GETTER("overall.inventorylist.shangpinmincheng"), "ThinkPad p14s", false);
		API_DEF_ADD_QUERY_PARAMS(String, "shengchanriqi", ZH_WORDS_GETTER("overall.inventorylist.shengchanriqi"), "2001-01-01", false);
	}
	// 3.2 定义查询接口处理
	ENDPOINT(API_M_GET, "/overall-inventory/query", querySample, QUERIES(QueryParams, queryParams), API_HANDLER_AUTH_PARAME) {
		// 解析查询参数为Query领域模型
		API_HANDLER_QUERY_PARAM(userQuery, InventorylistQuery, queryParams);
		// 执行函数并响应结果
		API_HANDLER_RESP_VO(execQuerySample(userQuery, authObject->getPayload()));
	}

	// 定义生成盘点任务接口描述（支持批量）
	API_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("overall.inventorylist.shengchenpdtest"), insertSttTaskMulti, InventoryInsertTaskJsonVO::Wrapper);

	// 定义生成盘点任务接口处理（支持批量）
	ENDPOINT(API_M_POST, "/overall-inventory/create", insertSttTaskMulti, BODY_DTO(InventoryInsertTaskDTO::Wrapper, dto), API_HANDLER_AUTH_PARAME)
	{
		API_HANDLER_RESP_VO(execInsertSttTaskMulti(dto, authObject->getPayload()));
	}

	// 定义编辑盘点任务接口描述
	API_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("overall.inventorylist.modify-check"), modifySttTask, Uint64JsonVO::Wrapper);
	// 定义编辑盘点任务接口处理
	API_HANDLER_ENDPOINT_AUTH(API_M_PUT, "/overall-inventory/modify", modifySttTask, BODY_DTO(InventoryModifyDTO::Wrapper, dto), execModifySttTask(dto, authObject->getPayload()));

	// 定义导出盘点差异数据接口描述
	ENDPOINT_INFO(exportDifference) {
		// 定义接口标题
		API_DEF_ADD_TITLE(ZH_WORDS_GETTER("overall.inventorylist.export-difference"));
		// 定义默认授权参数
		API_DEF_ADD_AUTH();
		// 定义分页查询参数描述
		API_DEF_ADD_PAGE_PARAMS();
		API_DEF_ADD_QUERY_PARAMS(String, "bin_id", ZH_WORDS_GETTER("mql.rest.bin_id"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "tin_id", ZH_WORDS_GETTER("mql.rest.tin_id"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "goods_id", ZH_WORDS_GETTER("mql.goods.goods_id"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "goods_name", ZH_WORDS_GETTER("mql.goods.goods_name"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cus_name", ZH_WORDS_GETTER("mql.cus.cus_name"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "cus_code", ZH_WORDS_GETTER("mql.cus.cus_code"), "", false);
		API_DEF_ADD_QUERY_PARAMS(String, "stt_sta", ZH_WORDS_GETTER("mql.stt.stt_sta"), "", false);
	}
	// 定义导出盘点差异数据接口处理
	ENDPOINT(API_M_GET, "/overall-inventory/difference-download", exportDifference, QUERIES(QueryParams, exportParams), API_HANDLER_AUTH_PARAME)
	{
		API_HANDLER_QUERY_PARAM(exportQuery, CheckQuery, exportParams);
		return execExportDifference(exportQuery);
	}

private:
	// 分页查询处理函数
	InventoryJsonPageVO::Wrapper execQuerySample(const InventorylistQuery::Wrapper& query, const PayloadDTO& payload);
	// 批量生成盘点任务处理函数
	InventoryInsertTaskJsonVO::Wrapper execInsertSttTaskMulti(const InventoryInsertTaskDTO::Wrapper& dto, const PayloadDTO& payload);
	// 编辑盘点任务处理函数
	Uint64JsonVO::Wrapper execModifySttTask(const InventoryModifyDTO::Wrapper& dto, const PayloadDTO& payload);
	// 导出盘点差异处理函数
	std::shared_ptr<OutgoingResponse> execExportDifference(const CheckQuery::Wrapper& query);
};
#include OATPP_CODEGEN_END(ApiController) //<- < End ApiController codegen section
#endif // !_OVERALLINVENTORY_CONTROLLER_
