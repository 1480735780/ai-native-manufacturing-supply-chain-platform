#include "stdafx.h"
#include "BinTransferService.h"
#include "../../dao/shengchengchuweizhuanyi/BinTransferDAO.h"
#include "../../dao/kuneizhuanyi/MoveGoodsDAO.h"
#include "id/UuidFacade.h"
#include <SimpleDateTimeFormat.h>
#include <cstdlib>

namespace
{
	oatpp::Int64 toInt64(const std::string& value)
	{
		if (value.empty()) return v_int64(0);
		return v_int64(std::strtoll(value.c_str(), nullptr, 10));
	}
}

BinTransferPageDTO::Wrapper BinTransferService::queryList(const BinTransferQuery::Wrapper& query)
{
	auto pages = BinTransferPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	BinTransferDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0)
	{
		return pages;
	}

	pages->total = count;
	pages->calcPages();
	list<StockTransferDO> result = dao.selectWithPage(query);
	for (auto& sub : result)
	{
		auto dto = BinTransferDTO::createShared();
		dto->id = sub.getId();
		dto->moveDate = sub.getCreateDate();
		dto->inventoryType = sub.getKucType();
		dto->bin = sub.getBin();
		dto->tin = sub.getTin();
		dto->cusCode = sub.getCusCode();
		dto->cusName = sub.getCusName();
		dto->goodsID = sub.getGoodsId();
		dto->goodsNum = toInt64(sub.getGoodsQua());
		dto->goodsName = sub.getGoodsName();
		dto->produceDate = sub.getGoodsProData();
		dto->produceShelfLife = sub.getBzhiQi();
		dto->produceUnit = sub.getGoodsUnit();
		dto->moveSta = sub.getMoveSta();
		pages->addData(dto);
	}
	return pages;
}

uint64_t BinTransferService::generateTasks(const BinTransferBatchDTO::Wrapper& dto, const PayloadDTO& payload)
{
	if (!dto || !dto->items || dto->items->empty())
	{
		return 0;
	}

	UuidFacade uf(1);
	std::string now = SimpleDateTimeFormat::format();
	MoveGoodsDAO dao;

	uint64_t inserted = 0;
	dao.getSqlSession()->beginTransaction();
	try
	{
		for (auto& item : *dto->items)
		{
			if (!item || !item->goodsID || item->goodsID->empty()
				|| !item->bin || item->bin->empty()
				|| !item->tin || item->tin->empty()
				|| !item->toBin || item->toBin->empty())
			{
				continue;
			}

			std::string goodsNum = item->goodsNum ? std::to_string(item->goodsNum.getValue(0)) : "";

			MoveGoodsDO data;
			data.setId(uf.genUuid());
			data.setCreateName(payload.getRealname());
			data.setCreateBy(payload.getUsername());
			data.setCreateDate(now);
			data.setOrderTypeCode("BIN_TRANSFER");
			data.setGoodsId(item->goodsID->c_str());
			data.setGoodsName(item->goodsName ? item->goodsName->c_str() : "");
			data.setGoodsQua(goodsNum);
			data.setGoodsProData(item->produceDate ? item->produceDate->c_str() : "");
			data.setGoodsUnit(item->produceUnit ? item->produceUnit->c_str() : "");
			data.setCusCode(item->cusCode ? item->cusCode->c_str() : "");
			data.setCusName(item->cusName ? item->cusName->c_str() : "");
			data.setTinFrom(item->tin->c_str());
			data.setTinId(item->tin->c_str());
			data.setBinFrom(item->bin->c_str());
			data.setBinTo(item->toBin->c_str());
			data.setMoveSta(ZH_WORDS_GETTER("move-goods.sta.wait"));
			data.setToCusCode(item->cusCode ? item->cusCode->c_str() : "");
			data.setToCusName(item->cusName ? item->cusName->c_str() : "");
			data.setBaseUnit(item->produceUnit ? item->produceUnit->c_str() : "");
			data.setBaseGoodscount(goodsNum);
			data.setToGoodsProData(item->produceDate ? item->produceDate->c_str() : "");
			data.setRunSta(ZH_WORDS_GETTER("move-goods.run.wait"));

			if (dao.insert(data) == 1)
			{
				inserted++;
			}
			else
			{
				throw std::runtime_error("insert move goods task failed");
			}
		}
		dao.getSqlSession()->commitTransaction();
	}
	catch (const std::exception& e)
	{
		dao.getSqlSession()->rollbackTransaction();
		cerr << "Generate bin transfer tasks exception. " << e.what() << endl;
		return 0;
	}
	return inserted;
}
