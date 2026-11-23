//#pragma once
/*
 Copyright Zero One Star. All rights reserved.

 @Author: qingbingwei
 @Date: 2025/2/26 11:08

*/

#include "stdafx.h"
#include "InventorylistService.h"
#include "../../dao/overallInventory/InventorylistDAO.h"
#include "Macros.h"
#include "ExcelComponent.h"
#include "FastDfsClient.h"
#include "../../dao/stt-on-move/SttOnMoveDAO.h"
#include "../../dao/stt-task/SttTaskDAO.h"
#include "../../service/stt-on-move/SttOnMoveService.h"
#include "../../service/stt-task/SttTaskService.h"
#include "../../domain/dto/stt-on-move/SttOnMoveDTO.h"

//..
#define TEST_EXCEL_FN "./" + ZH_WORDS_GETTER("review-stt.excel.path.good-diff-post") + ".xlsx"
#define TEST_EXCEL_SN ZH_WORDS_GETTER("review-stt.excel.sheet.s1")

// 条件分页查询所有数据
InventorylistDto::Wrapper InventorylistService::listAll(const InventorylistQuery::Wrapper& query)
{

	// 构建返回对象
	auto pages = InventorylistDto::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	// 查询数据总条数
	InventorylistDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0)
	{
		return pages;
	}

	// 分页查询数据
	pages->total = count;
	pages->calcPages();
	list<InventorylistDo> result = dao.selectWithPage(query);
	// 将DO转换成DTO
	for (InventorylistDo sub : result)
	{
		auto dto = InventoryBaseDTO::createShared();
		dto->yidongriqi = sub.getCreateDate();
		dto->cktype = sub.getSttType();
		dto->chuwei = sub.getBinId();
		dto->tuopan = sub.getTinId();
		dto->huozhu = sub.getCusCode();
		dto->huozhumingcheng = sub.getCusName();
		dto->shangpinbianma = sub.getGoodsId();
		dto->shangpinshuliang = sub.getSttQua();
		dto->shangpinmincheng = sub.getGoodsName();
		dto->shengchanriqi = sub.getGoodsProDate();
		pages->addData(dto);
	}
	return pages;
}


//uint64_t InventorylistService::saveData(const InventorylistDto::Wrapper& dto)
//{
//	// 组装DO数据
//	InventorylistDo data;
//	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Name, name, Sex, sex, Age, age);
//	// 执行数据添加
//	InventorylistDAO dao;
//	return dao.insert(data);
//}

// 通过条件分页查询数据
/*GoodsDiffPostListDTO::Wrapper GoodsManageService::getByCondition(const GoodsDiffPostQuery::Wrapper& query)
{
	return {};
}*/

// batch generate stocktake tasks: query stock view by ids, then insert into wm_stt_in_goods one by one
bool InventorylistService::saveBatchByStockIds(const oatpp::Vector<oatpp::String>& ids, const PayloadDTO& payload, oatpp::Vector<oatpp::String>& succeedIds)
{
	if (!ids || ids->empty())
		return false;
	SttOnMoveService sttOnMoveService;
	SttTaskService sttTaskService;
	bool allOk = true;
	for (int i = 0; i < ids->size(); i++)
	{
		auto stockItem = sttOnMoveService.getById(ids->at(i));
		if (!stockItem)
		{
			allOk = false;
			continue;
		}
		auto res = sttTaskService.insert(stockItem, payload);
		if (res > 0)
			succeedIds->push_back(ids->at(i));
		else
			allOk = false;
	}
	return allOk;
}

// update one stocktake task by id
bool InventorylistService::updateData(const InventoryModifyDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// check id
	if (!dto->id || dto->id->empty())
		return false;
	// assemble DO
	InventorylistDo data;
	data.setId(dto->id.getValue(""));
	data.setSttQua(dto->stt_qua.getValue(""));
	data.setGoodsQua(dto->goods_qua.getValue(""));
	data.setGoodsBatch(dto->goods_batch.getValue(""));
	data.setGoodsProDate(dto->goods_pro_data.getValue(""));
	data.setBinId(dto->bin_id.getValue(""));
	data.setTinId(dto->tin_id.getValue(""));
	data.setSttSta(dto->stt_sta.getValue(""));
	InventorylistDAO dao;
	return dao.updateById(data, payload) == 1;
}
