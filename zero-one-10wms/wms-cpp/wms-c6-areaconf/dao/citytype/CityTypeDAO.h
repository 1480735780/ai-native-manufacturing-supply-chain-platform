#pragma once
/*
 @Author: 002
 @Date: 2025.3.4
*/
#ifndef _CITY_TYPE_DAO_
#define _CITY_TYPE_DAO_
#include "BaseDAO.h"
#include "domain/do/citytype/CityTypeDO.h"
#include "domain/query/citytype/CityTypeQuery.h"
#include <vector>

/**
 * ba_city_type�����ݿ����ʵ��
 */
class CityTypeDAO : public BaseDAO
{
public:
	bool add(const CityTypeAddDO& obj);
	void add(const list<CityTypeAddDO>& obj);
	bool upd(const CityTypeUpdDO& obj);
	//��ѯ����
	std::list<CityTypeNameDO> getDistinctCityTypes();
	std::string queryConditionBuilder(const CityTypeQuery::Wrapper& query, SqlParams& params);
	uint64_t count(const CityTypeQuery::Wrapper& query);
	std::list<CityTypeDO> selectWithPage(const CityTypeQuery::Wrapper& query);
	std::list<CityTypeBaseDO> listAll();
	// ͨ��IDɾ������
	int deleteById(string id);
	// batch delete with parameterized IN clause
	int deleteByIds(const std::vector<std::string>& ids);
	// name duplicate check (excludeId empty for add, else for modify)
	int countByName(const std::string& name, const std::string& excludeId = "");
	// codes of this dict referenced by ba_city
	std::vector<std::string> listReferencedCodes(const std::vector<std::string>& codes);
	// resolve id to city_type_code, empty when not found
	std::string getCodeById(const std::string& id);
	uint64_t insertCityType(const std::string& cityName, const std::string& cityCode, const PayloadDTO& payload);
};
#endif // !_CITY_TYPE_DAO_
