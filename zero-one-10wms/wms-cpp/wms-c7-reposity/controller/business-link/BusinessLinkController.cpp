#include "stdafx.h"
#include "BusinessLinkController.h"
#include "service/business-link/BusinessLinkService.h"

BusinessLinkNameListJsonVO::Wrapper BusinessLinkController::execQueryBusinessLinkNameList()
{
	// 定义一个Service
	BusinessLinkService service;
	// 查询业务环节名称列表
	auto result = service.listBusinessLinkName();
	// 响应结果
	auto jvo = BusinessLinkNameListJsonVO::createShared();
	jvo->success(result);
	return jvo;
}

BusinessLinkPageJsonVO::Wrapper BusinessLinkController::execQueryBusinessLink(const BusinessLinkQuery::Wrapper& query, const PayloadDTO& payload)
{
	// 定义一个Service
	BusinessLinkService service;
	// 分页查询业务环节
	auto result = service.listQueryBusinessLink(query);
	// 响应结果
	auto jvo = BusinessLinkPageJsonVO::createShared();
	jvo->success(result);
	return jvo;
}

Uint64JsonVO::Wrapper BusinessLinkController::execAddBusinessLink(const BusinessLinkAddDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	if (!dto->oper_step_code || !dto->oper_step_name)
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	if (dto->oper_step_code->empty() || dto->oper_step_name->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 定义一个Service
	BusinessLinkService service;
	// 执行数据新增
	uint64_t res = service.addBusinessLink(dto, payload);
	if (res > 0)
	{
		jvo->success(UInt64(res));
	}
	else
	{
		jvo->fail(UInt64(res));
	}
	return jvo;
}
