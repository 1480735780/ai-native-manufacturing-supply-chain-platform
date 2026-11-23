#include "stdafx.h"
#include "CompanyController.h"
#include "service/company-conf/CompanyInfoService.h"


CompanyPageJsonVO::Wrapper CompanyController::execQueryALL(const CompanyInfoQuery::Wrapper& query)
{
	// 定义一个Service
	CompanyInfooService service;
	// 查询数据
	auto result = service.listAll(query);
	// 响应结果
	auto jvo = CompanyPageJsonVO::createShared();
	jvo->success(result);
	return jvo;
}


CompanyInfoVOJsonVO::Wrapper CompanyController::execQueryDETAIL(const String& id)
{
	// 定义返回数据对象
	auto jvo = CompanyInfoVOJsonVO::createShared();
	// 定义一个Service
	CompanyInfooService service;
	// 执行数据查询（ba_comp.id 为 varchar(36) 字符串主键）
	auto res = service.getById(id.getValue({}));
	if (!res)
	{
		jvo->fail(nullptr);
		return jvo;
	}
	jvo->success(res);

	// 响应结果
	return jvo;
}
