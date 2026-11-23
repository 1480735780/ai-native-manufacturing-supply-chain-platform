#include "stdafx.h"
#include "TinTransferController.h"
#include "service/shengchengtuopanzhuanyi/TinTransferService.h"

TinTransferPageJsonVO::Wrapper TinTransferController::execQueryTinTransferList(const TinTransferQuery::Wrapper& query)
{
	TinTransferService service;
	auto result = service.queryList(query);
	auto jvo = TinTransferPageJsonVO::createShared();
	jvo->success(result);
	return jvo;
}

Uint64JsonVO::Wrapper TinTransferController::execModifyTinTransfer(const TinTransferBatchDTO::Wrapper& dto, const PayloadDTO& payload)
{
	auto jvo = Uint64JsonVO::createShared();
	if (!dto || !dto->items || dto->items->empty())
	{
		jvo->init(v_uint64(0), RS_PARAMS_INVALID);
		return jvo;
	}

	TinTransferService service;
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
