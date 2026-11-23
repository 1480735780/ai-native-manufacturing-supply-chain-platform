#include "stdafx.h"
#include "DareaInfoDAO.h"
#include "DareaInfoMapper.h"

std::string DareaInfoDAO::queryConditionBuilder(const DareaInfoQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->area_code)
	{
		sqlCondition << " AND `area_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->area_code.getValue(""));
	}
	if (query->area_name)
	{
		sqlCondition << " AND `area_name`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->area_name.getValue(""));
	}
	return sqlCondition.str();
}

uint64_t DareaInfoDAO::count(const DareaInfoQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM `ba_area`";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<DareaInfoDO> DareaInfoDAO::select(const DareaInfoQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT id,area_code,area_name FROM `ba_area`";
	sql += queryConditionBuilder(query, params);
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	DareaInfoMapper mapper;
	return sqlSession->executeQuery<DareaInfoDO>(sql, mapper, params);
}

bool DareaInfoDAO::insert(const DareaInfoAddDO& iObj)
{
	std::string sql = "INSERT INTO `ba_area` (`id`,`create_name`,`create_by`,`create_date`,`update_name`,`update_by`,`update_date`,`sys_org_code`,`sys_company_code`,`area_code`,`area_name`) VALUES (?,?,?,?,?,?,?,?,?,?,?)";
	return sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s%s%s%s%s",iObj.getId(),iObj.getCreate_name(),iObj.getCreate_by(),iObj.getCreate_date(), iObj.getUpdate_name(), iObj.getUpdate_by(), iObj.getUpdate_date(), iObj.getSys_org_code(),iObj.getSys_company_code(), iObj.getArea_code(), iObj.getArea_name()) == 1;
}

void DareaInfoDAO::insert(const list<DareaInfoAddDO>& Obj)
{
	for (auto iObj : Obj)
	{
		insert(iObj);
	}
}

#define GET(val) iObj.get##val()
bool DareaInfoDAO::update(const DareaInfoUpdDO& iObj)
{
	std::string sql = "UPDATE `ba_area` SET `update_name`=?,`update_by`=?,`update_date`=?,`area_code`=?,`area_name`=? WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s%s%s%s%s%s", GET(Update_name), GET(Update_by), GET(Update_date), GET(Area_code), GET(Area_name), GET(Id)) == 1;
}
#undef GET

bool DareaInfoDAO::delet(const string& id)
{
	std::string sql = "DELETE FROM `ba_area` WHERE `id`=?";
	return sqlSession->executeUpdate(sql,"%s", id) == 1;
}

std::list<DareaInfoExportDO> DareaInfoDAO::select()
{
	string sql = "SELECT area_code,area_name FROM `ba_area`";
	DareaInfoExportMapper mapper;
	return sqlSession->executeQuery<DareaInfoExportDO>(sql, mapper);
}

int DareaInfoDAO::deleteByIds(const std::vector<std::string>& ids)
{
	if (ids.empty()) return 0;
	SqlParams params;
	string sql = "DELETE FROM `ba_area` WHERE `id` IN (";
	for (size_t i = 0; i < ids.size(); i++)
	{
		sql += (i == 0 ? "?" : ",?");
		SQLPARAMS_PUSH(params, "s", std::string, ids[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

int DareaInfoDAO::countByName(const std::string& name, const std::string& excludeId)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM `ba_area` WHERE `area_name`=?";
	SQLPARAMS_PUSH(params, "s", std::string, name);
	if (!excludeId.empty())
	{
		sql += " AND `id`<>?";
		SQLPARAMS_PUSH(params, "s", std::string, excludeId);
	}
	return (int)sqlSession->executeQueryNumerical(sql, params);
}

std::vector<std::string> DareaInfoDAO::listReferencedCodes(const std::vector<std::string>& codes)
{
	std::vector<std::string> refed;
	if (codes.empty()) return refed;
	for (const auto& code : codes)
	{
		SqlParams params;
		string sql = "SELECT COUNT(*) FROM ba_city WHERE `darea_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, code);
		if (sqlSession->executeQueryNumerical(sql, params) > 0)
			refed.push_back(code);
	}
	return refed;
}

std::vector<std::string> DareaInfoDAO::getCodesByIds(const std::vector<std::string>& ids)
{
	std::vector<std::string> codes;
	if (ids.empty()) return codes;
	for (const auto& id : ids)
	{
		SqlParams params;
		string sql = "SELECT area_code FROM `ba_area` WHERE `id`=?";
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
