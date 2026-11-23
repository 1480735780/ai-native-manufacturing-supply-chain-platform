#ifndef _DAREAINFO_DAO_
#define _DAREAINFO_DAO_
#include "BaseDAO.h"
#include "domain/query/dareainfo/DareaInfoQuery.h"
#include "DareaInfoMapper.h"
#include "domain/do/regioninfo/DareaInfoDO.h"
#include <vector>

class DareaInfoDAO : public BaseDAO
{
public:
	std::list<DareaInfoDO> select(const DareaInfoQuery::Wrapper& query);
	std::list<DareaInfoExportDO> select();
	bool insert(const DareaInfoAddDO& iObj);
	void insert(const list<DareaInfoAddDO>& iObj);
	bool update(const DareaInfoUpdDO& iObj);
	bool delet(const string& area_code);
	std::string queryConditionBuilder(const DareaInfoQuery::Wrapper& query, SqlParams& params);
	uint64_t count(const DareaInfoQuery::Wrapper& query);
	// batch delete by ids with parameterized IN clause
	int deleteByIds(const std::vector<std::string>& ids);
	// name duplicate check (excludeId empty for add, else for modify)
	int countByName(const std::string& name, const std::string& excludeId = "");
	// codes referenced by ba_city.darea_code
	std::vector<std::string> listReferencedCodes(const std::vector<std::string>& codes);
	// resolve ids to darea codes
	std::vector<std::string> getCodesByIds(const std::vector<std::string>& ids);
};

#endif // !_DAREAINFO_DAO_
