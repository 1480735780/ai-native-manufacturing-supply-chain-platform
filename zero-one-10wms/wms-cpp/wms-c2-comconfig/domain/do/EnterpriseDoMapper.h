#pragma once
#ifndef _EnterpriseDoMapper_H_
#define _EnterpriseDoMapper_H_
#include "enterpriseDO.h"
#include "Mapper.h"
class EnterpriseDoMapper : public Mapper<EnterpriseDO>
{
public:
	EnterpriseDO mapper(ResultSet* res) const override
	{
		EnterpriseDO ans;

		//取查询结果的第1列（行业分类名称，用于名称列表）
		ans.setComTypeName(res->getString(1));
		return ans;
	}
};
class EnterpriseDoMapper1 : public Mapper<EnterpriseDO>
{
public:
	EnterpriseDO mapper(ResultSet* res) const override
	{
		EnterpriseDO ans;

		//分页列表：id / 分类代码 / 分类名称 / 停用标志
		//id 必须回传，前端修改/删除依赖它
		ans.setId(res->getString(1));
		ans.setComTypeCode(res->getString(2));
		ans.setComTypeName(res->getString(3));
		ans.setComTypeDel(res->getUInt64(4));
		return ans;
	}
};
#endif // !_EnterpriseDoMapper_H_
