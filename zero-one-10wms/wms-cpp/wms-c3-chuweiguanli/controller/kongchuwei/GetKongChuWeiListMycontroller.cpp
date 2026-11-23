#include "stdafx.h"
#include "GetKongChuWeiListMycontroller.h"
#include "service/kongchuwei/QueryService.h"

// paged list of empty bins (enabled + no stock)
GetKongChuWeiListMycontrollerPageJsonVO::Wrapper GetKongChuWeiListMycontroller::GetKongChuWeiListMycontrollerTest(const GetKongChuWeiListMycontrollerQuery::Wrapper& query)
{
	QueryService service;
	auto pages = service.listKongChuWei(query);
	auto jvo = GetKongChuWeiListMycontrollerPageJsonVO::createShared();
	jvo->success(pages);
	return jvo;
}
