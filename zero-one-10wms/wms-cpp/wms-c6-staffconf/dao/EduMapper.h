#pragma once
#ifndef _EDU_MAPPER_
#define _EDU_MAPPER_

#include "Mapper.h"
#include "../domain/do/education/EducationDO.h"

/**
 * ѧ�����ֶ�ƥ��ӳ��
 */
class EduMapper : public Mapper<EducationDO>
{
public:
	EducationDO mapper(ResultSet* resultSet) const override
	{
		EducationDO data;
		// fix: map id column (SELECT id, edu_sta_code, edu_sta_name)
		data.setId(resultSet->getString(1));
		data.setEduCode(resultSet->getString(2));
		data.setEduName(resultSet->getString(3));
		return data;
	}
};

class EduBaseMapper : public Mapper<EduBaseDO>
{
public:
	EduBaseDO mapper(ResultSet* resultSet) const override
	{
		EduBaseDO data;
		data.setEduCode(resultSet->getString(1));
		data.setEduName(resultSet->getString(2));
		return data;
	}
};

/**
 * ѧ�����ֶ�ƥ��ӳ��-��������ָ�����
 */
class PtrEduMapper : public Mapper<PtrEducationDO>
{
public:
	PtrEducationDO mapper(ResultSet* resultSet) const override
	{
		auto data = std::make_shared<EducationDO>();
		data->setEduCode(resultSet->getString(1));
		data->setEduName(resultSet->getString(2));
		return data;
	}
};

#endif // !_EDU_MAPPER_