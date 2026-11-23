#pragma once
#ifndef _ENTERPRISESTATUSMAPPER_
#define _ENTERPRISESTATUSMAPPER_

#include "Mapper.h"
#include "../../domain/do/enterprisestatus/EnterpriseStatusDO.h"

/**
 * 企业状态表字段匹配映射（ba_com_sta）
 */
class EnterpriseStatusMapper : public Mapper<EnterpriseStatusDO>
{
public:
	EnterpriseStatusDO mapper(ResultSet* resultSet) const override
	{
		EnterpriseStatusDO data;
		data.setId(resultSet->getString(1));
		data.setkehuzhuangtai_code(resultSet->getString(2));
		data.setkehuzhuangtai_name(resultSet->getString(3));
		data.setcus_sta_del(resultSet->getString(4));
		return data;
	}
};

/**
 * 企业状态表字段匹配映射-创建智能指针对象
 */
class PtrEnterpriseStatusMapper : public Mapper<PtrEnterpriseStatusDO>
{
public:
	PtrEnterpriseStatusDO mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<EnterpriseStatusDO>();
		data->setId(resultSet->getString(1));
		data->setkehuzhuangtai_code(resultSet->getString(2));
		data->setkehuzhuangtai_name(resultSet->getString(3));
		data->setcus_sta_del(resultSet->getString(4));
		return data;
	}
};


class EnterpriseStatusListMapper : public Mapper<EnterpriseStatusListDO>
{
public:
	EnterpriseStatusListDO mapper(ResultSet* resultSet) const override
	{
		EnterpriseStatusListDO data;
		data.setid(resultSet->getString(1));
		data.setkehuzhuangtai_code(resultSet->getString(2));
		data.setkehuzhuangtai_name(resultSet->getString(3));
		return data;
	}
};
class PtrEnterpriseStatusListMapper : public Mapper<PtrEnterpriseStatusListDO>
{
public:
	PtrEnterpriseStatusListDO mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<EnterpriseStatusListDO>();
		data->setid(resultSet->getString(1));
		data->setkehuzhuangtai_code(resultSet->getString(2));
		data->setkehuzhuangtai_name(resultSet->getString(3));
		return data;
	}
};

#endif // !_ENTERPRISESTATUSMAPPER_
