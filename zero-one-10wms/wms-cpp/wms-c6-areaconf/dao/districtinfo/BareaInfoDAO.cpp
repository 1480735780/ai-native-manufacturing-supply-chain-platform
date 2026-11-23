#include "stdafx.h"
#include "BareaInfoDAO.h"
#include "BareaInfoMapper.h"

std::list<BareaInfoDO> BareaInfoDAO::exportBareaInfo()
{
	std::string sql = "SELECT barea_code,barea_name,barea_rdata FROM ba_barea";
	BareaInfoExportMapper mapper;
	return sqlSession->executeQuery<BareaInfoDO>(sql, mapper);
}

std::list<BareaNameDO> BareaInfoDAO::nameList()
{
	std::string sql = "SELECT id,barea_name FROM ba_barea";
	BareaNameMapper mapper;
	return sqlSession->executeQuery<BareaNameDO>(sql, mapper);
}

std::string BareaInfoDAO::queryConditionBuilder(const BareaInfoQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->barea_code)
	{
		sqlCondition << " AND `barea_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->barea_code.getValue(""));
	}
	if (query->barea_name)
	{
		sqlCondition << " AND `barea_name`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->barea_name.getValue(""));
	}
	return sqlCondition.str();
}

uint64_t BareaInfoDAO::count(const BareaInfoQuery::Wrapper& query)
{
	SqlParams params;
	std::string sql = "SELECT COUNT(*) FROM ba_barea";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<BareaInfoDO> BareaInfoDAO::infoList(const BareaInfoQuery::Wrapper& query)
{
	SqlParams params;
	std::string sql = "SELECT id,barea_code,barea_name,barea_rdata FROM ba_barea";
	sql += queryConditionBuilder(query, params);
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	BareaInfoMapper mapper;
	return sqlSession->executeQuery<BareaInfoDO>(sql, mapper, params);
}

int BareaInfoDAO::deleteByIds(const std::vector<std::string>& ids)
{
	if (ids.empty()) return 0;
	SqlParams params;
	std::string sql = "DELETE FROM `ba_barea` WHERE `id` IN (";
	for (size_t i = 0; i < ids.size(); i++)
	{
		sql += (i == 0 ? "?" : ",?");
		SQLPARAMS_PUSH(params, "s", std::string, ids[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

int BareaInfoDAO::countByName(const std::string& name, const std::string& excludeId)
{
	SqlParams params;
	std::string sql = "SELECT COUNT(*) FROM ba_barea WHERE `barea_name`=?";
	SQLPARAMS_PUSH(params, "s", std::string, name);
	if (!excludeId.empty())
	{
		sql += " AND `id`<>?";
		SQLPARAMS_PUSH(params, "s", std::string, excludeId);
	}
	return (int)sqlSession->executeQueryNumerical(sql, params);
}

std::vector<std::string> BareaInfoDAO::listReferencedCodes(const std::vector<std::string>& codes)
{
	std::vector<std::string> refed;
	if (codes.empty()) return refed;
	for (const auto& code : codes)
	{
		SqlParams params;
		std::string sql = "SELECT COUNT(*) FROM ba_city WHERE `barea_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, code);
		if (sqlSession->executeQueryNumerical(sql, params) > 0)
			refed.push_back(code);
	}
	return refed;
}

std::vector<std::string> BareaInfoDAO::getCodesByIds(const std::vector<std::string>& ids)
{
	std::vector<std::string> codes;
	if (ids.empty()) return codes;
	for (const auto& id : ids)
	{
		SqlParams params;
		std::string sql = "SELECT barea_code FROM ba_barea WHERE `id`=?";
		SQLPARAMS_PUSH(params, "s", std::string, id);
		class CodeMapper : public Mapper<std::string> {
		public:
			std::string mapper(ResultSet* resultSet) const override {
				return resultSet->getString(1);
			}
		};
		CodeMapper mapper;
		auto rows = sqlSession->executeQuery<std::string>(sql, mapper, params);
		if (!rows.empty() && !rows.front().empty()) codes.push_back(rows.front());
	}
	return codes;
}
