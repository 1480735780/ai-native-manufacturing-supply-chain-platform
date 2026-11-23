#pragma once
/*
 @Author: nanbowan

*/
#ifndef _LIBRARY_MAPPER_
#define _LIBRARY_MAPPER_

#include "Mapper.h"
#include "../../domain/do/library/LibraryDO.h"

/**
 * 库位类型完整字段匹配映射（11 列：id + 9 个审计字段 + 业务字段）
 */
class LibraryDetailMapper : public Mapper<LibraryDO>
{
public:
	LibraryDO mapper(ResultSet* resultSet) const override
	{
		LibraryDO data;
		data.setId(resultSet->getString(1));
		data.setCreateName(resultSet->getString(2));
		data.setCreateBy(resultSet->getString(3));
		data.setCreateDate(resultSet->getString(4));
		data.setUpdateName(resultSet->getString(5));
		data.setUpdateBy(resultSet->getString(6));
		data.setUpdateDate(resultSet->getString(7));
		data.setSysOrgCode(resultSet->getString(8));
		data.setSysCompanyCode(resultSet->getString(9));
		data.setCode(resultSet->getString(10));
		data.setName(resultSet->getString(11));
		return data;
	}
};

class PtrLibraryDetailMapper : public Mapper<PtrLibraryDO>
{
public:
	PtrLibraryDO mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<LibraryDO>();
		data->setId(resultSet->getString(1));
		data->setCreateName(resultSet->getString(2));
		data->setCreateBy(resultSet->getString(3));
		data->setCreateDate(resultSet->getString(4));
		data->setUpdateName(resultSet->getString(5));
		data->setUpdateBy(resultSet->getString(6));
		data->setUpdateDate(resultSet->getString(7));
		data->setSysOrgCode(resultSet->getString(8));
		data->setSysCompanyCode(resultSet->getString(9));
		data->setCode(resultSet->getString(10));
		data->setName(resultSet->getString(11));
		return data;
	}
};

/**
 * 库位类型列表映射（3 列：id + bin_type_code + bin_type_name）
 */
class LibraryMapper : public Mapper<LibraryDO>
{
public:
	LibraryDO mapper(ResultSet* resultSet) const override
	{
		LibraryDO data;
		data.setId(resultSet->getString(1));
		data.setCode(resultSet->getString(2));
		data.setName(resultSet->getString(3));
		return data;
	}
};

class PtrLibraryMapper : public Mapper<PtrLibraryDO>
{
public:
	PtrLibraryDO mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<LibraryDO>();
		data->setId(resultSet->getString(1));
		data->setCode(resultSet->getString(2));
		data->setName(resultSet->getString(3));
		return data;
	}
};

/**
 * 库位类型名称列表映射（3 列：id + bin_type_code + bin_type_name）
 */
class LibraryNameMapper : public Mapper<LibraryNameDO>
{
public:
	LibraryNameDO mapper(ResultSet* resultSet) const override
	{
		LibraryNameDO data;
		data.setId(resultSet->getString(1));
		data.setCode(resultSet->getString(2));
		data.setName(resultSet->getString(3));
		return data;
	}
};

class PtrLibraryNameMapper : public Mapper<PtrLibraryNameDO>
{
public:
	PtrLibraryNameDO mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<LibraryNameDO>();
		data->setId(resultSet->getString(1));
		data->setCode(resultSet->getString(2));
		data->setName(resultSet->getString(3));
		return data;
	}
};

#endif // !_LIBRARY_MAPPER_
