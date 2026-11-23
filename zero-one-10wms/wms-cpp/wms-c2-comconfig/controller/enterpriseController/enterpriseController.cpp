#include "stdafx.h"
#include "enterpriseController.h"
/*
FastDfs 保存到服务器
mongodb 文件数据库
*/
//增加企业分类信息
addEnterpriseJsonVO::Wrapper enterpriseController::execAddEnterprise(const addEnterpriseDTO::Wrapper& enterpriseInfo, const PayloadDTO& payload)
{
	auto jvo = addEnterpriseJsonVO::createShared();
	enterpriseService service;
	string code = enterpriseInfo->enterpriseClassificationCode.getValue({});
	string name = enterpriseInfo->enterpriseClassificationName.getValue({});
	// 只校验非空：分类代码/名称本身允许包含数字（如 HYFL01、仓储1类），
	// 原实现逐字符拒绝数字会导致绝大多数正常编码无法录入
	if (code.empty() || name.empty()) {
		jvo->fail((uint64_t)0);
		return jvo;
	}

	//调用函数,返回状态
	int res = 0;
	try {
		res = service.saveData(enterpriseInfo, payload);
		if(res)
			jvo->success(res);
		else 
			jvo->fail(res);
	}
	catch (const exception& ep)
	{
		cout << "Exception : " << ep.what() << endl;
		jvo->fail(res);
	}
	return jvo;
}
//企业分页查询
enterprisePageJsonVO::Wrapper enterpriseController::execEnterprisePageQuery(const enterprisePageQuery::Wrapper& query)
{
	auto jvo = enterprisePageJsonVO::createShared(); // std::list<enterprisePageJsonVO>
	enterpriseService service;

	auto res = enterprisePageDTO::createShared();
	try {
		res = service.listAll(query);
		jvo->success(res);
	}
	catch (const exception& ep)
	{
		cout << "Exception : " << ep.what() << endl;
		jvo->fail(res);
	}

	return jvo;
}
//获得企业分类列表
enterpriseNameJsonVO::Wrapper enterpriseController::execGetEnterpriseName()//const PageQuery::Wrapper& query
{
	auto jvo = enterpriseNameJsonVO::createShared();
	enterpriseService service;
	auto res = enterpriseNameDTO::createShared();
	try {
		res = service.getEnterpriseName();
		jvo->success(res);
	}
	catch (const exception& ep)
	{
		cout << "Exception : " << ep.what() << endl;
		jvo->fail(res);
	}


	return jvo;
}
