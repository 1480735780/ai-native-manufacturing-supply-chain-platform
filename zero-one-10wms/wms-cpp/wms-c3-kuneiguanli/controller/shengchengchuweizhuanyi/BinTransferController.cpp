#include "stdafx.h"
#include "BinTransferController.h"
#include "service/shengchengchuweizhuanyi/BinTransferService.h"

BinTransferPageJsonVO::Wrapper BinTransferController::execQueryBinTransfer(const BinTransferQuery::Wrapper& query)
{
	BinTransferService service;
	auto result = service.queryList(query);
	auto jvo = BinTransferPageJsonVO::createShared();
	jvo->success(result);
	return jvo;
}

Uint64JsonVO::Wrapper BinTransferController::execModifyBinTransfer(const BinTransferBatchDTO::Wrapper& dto, const PayloadDTO& payload)
{
	auto jvo = Uint64JsonVO::createShared();
	if (!dto || !dto->items || dto->items->empty())
	{
		jvo->init(v_uint64(0), RS_PARAMS_INVALID);
		return jvo;
	}

	BinTransferService service;
	uint64_t inserted = service.generateTasks(dto, payload);
	if (inserted > 0)
	{
		jvo->success(v_uint64(inserted));
	}
	else
	{
		jvo->fail(v_uint64(0));
	}
	return jvo;
}
