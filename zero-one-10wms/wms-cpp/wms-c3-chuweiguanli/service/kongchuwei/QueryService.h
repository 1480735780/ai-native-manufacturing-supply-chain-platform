#pragma once
#ifndef _QUERY_SERVICE_
#define _QUERY_SERVICE_
#include <list>
#include "domain/query/kongchuwei/DaoChuKongChuWeiQuery.h"
#include "domain/dto/kongchuwei/DaoChuKongChuWeiDTO.h"
#include "domain/dto/kongchuwei/GetKongChuWeiListMycontrollerDTO.h"
#include "domain/query/kongchuwei/GetKongChuWeiListMycontrollerQuery.h"

/**
 * 示例服务实现，演示基础的示例服务实现
 */
class QueryService
{
public:
	// 分页查询所有数据
	DaoChuKongChuWeiPageDTO::Wrapper listAll(const DaoChuKongChuWeiQuery::Wrapper& query);
	// paged list of empty bins (no stock, enabled)
	GetKongChuWeiListMycontrollerPageDTO::Wrapper listKongChuWei(const GetKongChuWeiListMycontrollerQuery::Wrapper& query);
	
};

#endif // !_QUERY_SERVICE_