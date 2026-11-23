#ifndef _AREAINFO_DAO_
#define _AREAINFO_DAO_
#include "BaseDAO.h"
#include "domain/do/areainfo/AreaInfoDO.h"
#include "domain/query/areainfo/AreaInfoQuery.h"
#include <vector>

class AreaInfoDAO : public BaseDAO
{
public:
	bool delet(const string& id);
	bool update(const AreaInfoUpdDO& uObj);
	bool add(const AreaInfoAddDO& uObj);
	bool insertUplExl(const std::list<AreaInfoAddDO>& iObj);
	std::list<AreaInfoDO> select();
	std::list<AreaInfoListDO> selectList(const AreaInfoQuery::Wrapper& query);
	std::list<AreaNameTreeDO> selectName();
	std::string queryConditionBuilder(const AreaInfoQuery::Wrapper& query, SqlParams& params);
	uint64_t count(const AreaInfoQuery::Wrapper& query);
	// batch delete by ids with parameterized IN clause
	int deleteByIds(const std::vector<std::string>& ids);
	// dict name resolve checks for import validation
	bool existsCityTypeByName(const std::string& name);
	bool existsBareaByName(const std::string& name);
	bool existsDareaByName(const std::string& name);
};

#endif