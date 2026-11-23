#include "stdafx.h"
#include "CostConfigController.h"

StringJsonVO::Wrapper CostConfigController::execwaydelete(const UInt64& code)
{
	auto jvo = StringJsonVO::createShared();
	if (performDeleteOperation(code)) {
		jvo->success("success");
	}
	else
	{
		jvo->fail("fail");
	}
	return jvo;
}
