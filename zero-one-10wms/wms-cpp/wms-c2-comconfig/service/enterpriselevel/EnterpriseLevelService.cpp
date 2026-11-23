#include "stdafx.h"
#include "EnterpriseLevelService.h"
#include "../../dao/enterpriselevel/EnterpriseLevelDAO.h"

EnterpriseLevelNameDTO::Wrapper EnterpriseLevelService::getEnterpriseLevelName()
{
	auto res = EnterpriseLevelNameDTO::createShared();
	EnterpriseLevelDAO dao;
	auto ans = dao.getEnterpriseName();
	// 组装企业等级名称/编号/id/停用状态列表
	for (const auto& item : ans) {
		res->name->push_back(item.getName());
		res->code->push_back(item.getCode());
		res->id->push_back(item.getId());
		res->ban->push_back(item.getBan());
	}
	return res;
}
