#pragma once
/*
 @Author: laughter
*/
#ifndef _COMPANYATTR_MAPPER_
#define _COMPANYATTR_MAPPER_

#include "Mapper.h"
#include "../../domain/do/companyattr/CompanyattrDO.h"

/**
 * 字段匹配映射（ba_com_type：id / 属性代码 / 属性名称）
 */
class CompanyattrMapper : public Mapper<CompanyattrDO>
{
public:
	CompanyattrDO mapper(ResultSet* resultSet) const override
	{
		CompanyattrDO data;
		data.setId(resultSet->getString(1));
		data.setcom_type_Code(resultSet->getString(2));
		data.setcom_type_Name(resultSet->getString(3));
		return data;
	}
};

/**
 * 字段匹配映射-创建智能指针对象
 */
class PtrCompanyattrMapper : public Mapper<PtrCompanyattrDO>
{
public:
	PtrCompanyattrDO mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<CompanyattrDO>();
		data->setId(resultSet->getString(1));
		data->setcom_type_Code(resultSet->getString(2));
		data->setcom_type_Name(resultSet->getString(3));
		return data;
	}
};

#endif // !_COMPANYATTR_MAPPER_
