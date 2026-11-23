#ifndef _BAREAINFO_DAO_
#define _BAREAINFO_DAO_
#include "BaseDAO.h"
#include "domain/query/bareainfo/BareaInfoQuery.h"
#include "domain/do/districtinfo/districtinfoDO.h"
#include <vector>

class BareaInfoDAO : public BaseDAO
{
public:
	std::list<BareaInfoDO> exportBareaInfo();
	std::list<BareaNameDO> nameList();
	std::list<BareaInfoDO> infoList(const BareaInfoQuery::Wrapper& query);
	std::string queryConditionBuilder(const BareaInfoQuery::Wrapper& query, SqlParams& params);
	uint64_t count(const BareaInfoQuery::Wrapper& query);
	// batch delete by ids with parameterized IN clause
	int deleteByIds(const std::vector<std::string>& ids);
	// name duplicate check (excludeId empty for add, else for modify)
	int countByName(const std::string& name, const std::string& excludeId = "");
	// codes referenced by ba_city.barea_code
	std::vector<std::string> listReferencedCodes(const std::vector<std::string>& codes);
	// resolve ids to barea codes
	std::vector<std::string> getCodesByIds(const std::vector<std::string>& ids);
};

#endif 