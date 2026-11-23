#include "stdafx.h"
#include "MoveGoodsService.h"
#include "../../dao/kuneizhuanyi/MoveGoodsDAO.h"
#include <SimpleDateTimeFormat.h>

MoveGoodsPageDTO::Wrapper MoveGoodsService::queryList(const MoveGoodsQuery::Wrapper& query)
{
	// 构建返回对象
	auto pages = MoveGoodsPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	// 查询数据总条数
	MoveGoodsDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0)
	{
		return pages;
	}

	// 分页查询数据
	pages->total = count;
	pages->calcPages();
	list<MoveGoodsDO> result = dao.selectWithPage(query);
	for (auto& sub : result)
	{
		auto dto = MoveGoodsDTO::createShared();
		dto->id = sub.getId();
		dto->createBy = sub.getCreateBy();
		dto->createDate = sub.getCreateDate();
		dto->goodsID = sub.getGoodsId();
		dto->goodsName = sub.getGoodsName();
		dto->goodsQua = sub.getGoodsQua();
		dto->goodsUnit = sub.getGoodsUnit();
		dto->goodsProData = sub.getGoodsProData();
		dto->cusCode = sub.getCusCode();
		dto->cusName = sub.getCusName();
		dto->tinFrom = sub.getTinFrom();
		dto->tinId = sub.getTinId();
		dto->binFrom = sub.getBinFrom();
		dto->binTo = sub.getBinTo();
		dto->toCusCode = sub.getToCusCode();
		dto->toCusName = sub.getToCusName();
		dto->moveNum = sub.getGoodsQua();
		dto->produceDate = sub.getGoodsProData();
		dto->toProduceDate = sub.getToGoodsProData();
		dto->moveStatus = sub.getMoveSta();
		dto->runSta = sub.getRunSta();
		pages->addData(dto);
	}
	return pages;
}

bool MoveGoodsService::modifyById(const MoveGoodsModifyDTO::Wrapper& dto, const std::string& usrName)
{
	if (!dto || !dto->id || dto->id->empty())
	{
		return false;
	}

	MoveGoodsDO data;
	data.setId(dto->id->c_str());
	if (dto->moveNum) data.setGoodsQua(dto->moveNum->c_str());
	if (dto->moveNum) data.setBaseGoodscount(dto->moveNum->c_str());
	if (dto->tinId) data.setTinId(dto->tinId->c_str());
	if (dto->binTo) data.setBinTo(dto->binTo->c_str());
	if (dto->toCusCode) data.setToCusCode(dto->toCusCode->c_str());
	if (dto->toCusName) data.setToCusName(dto->toCusName->c_str());
	if (dto->produceDate) data.setGoodsProData(dto->produceDate->c_str());
	if (dto->toProduceDate) data.setToGoodsProData(dto->toProduceDate->c_str());
	if (dto->moveStatus) data.setMoveSta(dto->moveStatus->c_str());
	data.setUpdateBy(usrName);
	data.setUpdateDate(SimpleDateTimeFormat::format());

	MoveGoodsDAO dao;
	return dao.updateById(data) > 0;
}

uint64_t MoveGoodsService::batchTransfer(const MoveGoodsBatchDTO::Wrapper& dto, const std::string& usrName)
{
	if (!dto || !dto->items || dto->items->empty())
	{
		return 0;
	}

	std::vector<std::string> ids;
	for (auto& item : *dto->items)
	{
		if (item && item->id && !item->id->empty())
		{
			ids.push_back(item->id->c_str());
		}
	}
	if (ids.empty())
	{
		return 0;
	}

	MoveGoodsDAO dao;
	return dao.batchUpdateStatus(ids, ZH_WORDS_GETTER("move-goods.sta.moved"),
		ZH_WORDS_GETTER("move-goods.run.done"), usrName, SimpleDateTimeFormat::format());
}

MoveGoodsDetailedDTO::Wrapper MoveGoodsService::getDetailedById(const oatpp::String queryID)
{
	// 查询数据
	MoveGoodsDAO dao;
	auto res = dao.selectDetailedById(queryID);
	// 没有查询到数据
	if (!res)
		return nullptr;

	// 查询到数据转换成DTO
	auto dto = MoveGoodsDetailedDTO::createShared();
	ZO_STAR_DOMAIN_DO_TO_DTO_1(dto, res,
		goodsID, GoodsId, goodsName, GoodsName, nowNum, GoodsQua,
		moveNum, BaseGoodscount, produceDate, GoodsProData, toProduceDate, ToGoodsProData,
		goodsUnit, GoodsUnit, cusCode, CusCode, cusName, CusName,
		toCusCode, ToCusCode, toCusName, ToCusName,
		tinFrom, TinFrom, tinTo, TinId, binFrom, BinFrom,
		binTo, BinTo, moveStatus, MoveSta
	);
	return dto;
}

bool  MoveGoodsService::removeMoveGoods(const vector<string> id,const string usrName)
{
	MoveGoodsDAO dao;
	return dao.deleteById(id,usrName) > 0;
}

vector<vector<string>> MoveGoodsService::getDownLoadById(const vector<string>& ids)
{
	MoveGoodsDAO dao;
	return dao.selectDownLoadById(ids);
}
