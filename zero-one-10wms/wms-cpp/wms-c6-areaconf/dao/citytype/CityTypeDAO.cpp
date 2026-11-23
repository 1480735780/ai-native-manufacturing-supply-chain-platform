#include "stdafx.h"
#include "CityTypeDAO.h"
#include "CityTypeMapper.h"
#include "id/UuidFacade.h"
#include "SimpleDateTimeFormat.h"
#include <sstream>

#define GET(val) obj.get##val()
bool CityTypeDAO::upd(const CityTypeUpdDO& obj)
{
	string sql = "UPDATE `ba_city_type` SET update_name=?,update_by=?,update_date=?,sys_org_code=?,sys_company_code=?,city_type_code=?,city_type_name=? WHERE id=?";
	return sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s%s", GET(Uname), GET(Uby), GET(Udate), GET(Orgcode), GET(Companycode), GET(Code), GET(Name), GET(Id)) == 1;
}
#undef GET

#define GET(val) obj.get##val()
bool CityTypeDAO::add(const CityTypeAddDO& obj)
{
	string sql = "INSERT INTO `ba_city_type` (id,create_name,create_by,create_date,update_name,update_by,update_date,sys_org_code,sys_company_code,city_type_code,city_type_name) VALUES (?,?,?,?,?,?,?,?,?,?,?)";
	return sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s%s%s%s%s",GET(Id),GET(Cname),GET(Cby),GET(Cdate),GET(Uname),GET(Uby),GET(Udate),GET(Orgcode),GET(Companycode),GET(Code),GET(Name)) == 1;
}
#undef GET

void CityTypeDAO::add(const list<CityTypeAddDO>& obj)
{
	for (auto sub : obj)
	{
		add(sub);
	}
}

std::list<CityTypeNameDO> CityTypeDAO::getDistinctCityTypes()
{
	string sql = "SELECT DISTINCT id,city_type_name FROM ba_city_type";
	CityTypeNameMapper mapper;
	return sqlSession->executeQuery<CityTypeNameDO>(sql, mapper);
}

std::string CityTypeDAO::queryConditionBuilder(const CityTypeQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->city_type_code)
	{
		sqlCondition << " AND `city_type_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->city_type_code.getValue(""));
	}
	if (query->city_type_name)
	{
		sqlCondition << " AND `city_type_name`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->city_type_name.getValue(""));
	}
	return sqlCondition.str();
}

uint64_t CityTypeDAO::count(const CityTypeQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM ba_city_type";
	sql += queryConditionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<CityTypeDO> CityTypeDAO::selectWithPage(const CityTypeQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT id,city_type_name,city_type_code FROM ba_city_type";
	sql += queryConditionBuilder(query, params);
	// append page limit
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	CityTypeMapper mapper;
	return sqlSession->executeQuery<CityTypeDO>(sql, mapper, params);
}

int CityTypeDAO::deleteById(string id)
{
	string sql = "DELETE FROM `ba_city_type` WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s", id);
	 
}

int CityTypeDAO::deleteByIds(const std::vector<std::string>& ids)
{
	if (ids.empty()) return 0;
	SqlParams params;
	string sql = "DELETE FROM `ba_city_type` WHERE `id` IN (";
	for (size_t i = 0; i < ids.size(); i++)
	{
		sql += (i == 0 ? "?" : ",?");
		SQLPARAMS_PUSH(params, "s", std::string, ids[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

int CityTypeDAO::countByName(const std::string& name, const std::string& excludeId)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM ba_city_type WHERE `city_type_name`=?";
	SQLPARAMS_PUSH(params, "s", std::string, name);
	if (!excludeId.empty())
	{
		sql += " AND `id`<>?";
		SQLPARAMS_PUSH(params, "s", std::string, excludeId);
	}
	return (int)sqlSession->executeQueryNumerical(sql, params);
}

std::vector<std::string> CityTypeDAO::listReferencedCodes(const std::vector<std::string>& codes)
{
	std::vector<std::string> refed;
	if (codes.empty()) return refed;
	for (const auto& code : codes)
	{
		SqlParams params;
		string sql = "SELECT COUNT(*) FROM ba_city WHERE `city_type_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, code);
		if (sqlSession->executeQueryNumerical(sql, params) > 0)
			refed.push_back(code);
	}
	return refed;
}

uint64_t CityTypeDAO::insertCityType(const std::string& cityName, const std::string& cityCode, const PayloadDTO& payload)
{
	auto name = payload.getUsername();
	auto by = payload.getRealname();
	auto date = SimpleDateTimeFormat::format();
	auto org = payload.getOrgcode();
	auto company = payload.getCompanycode();
	UuidFacade uuidGen;
	// 生成 UUID
	std::string newId = uuidGen.genUuid();
	// 构建 SQL 插入语句
	std::string sql = "INSERT INTO ba_city_type (id,create_name,create_by,create_date,update_name,update_by,update_date,sys_org_code,sys_company_code,city_type_code,city_type_name) VALUES (?,?,?,?,?,?,?,?,?,?,?)";
	// 使用可变参数插入数据
	return sqlSession->executeInsert(sql,"%s%s%s%s%s%s%s%s%s%s", newId, name, by , date, name, by , date, org, company, cityCode,cityName);
}

std::list<CityTypeBaseDO> CityTypeDAO::listAll()
{
	string sql = "SELECT city_type_code,city_type_name FROM ba_city_type";
	CityTypeBaseMapper mapper;
	return sqlSession->executeQuery<CityTypeBaseDO>(sql, mapper);
}

std::string CityTypeDAO::getCodeById(const std::string& id)
{
	SqlParams params;
	string sql = "SELECT city_type_code FROM ba_city_type WHERE `id`=?";
	SQLPARAMS_PUSH(params, "s", std::string, id);
	class CodeMapper : public Mapper<std::string> {
	public:
		std::string mapper(ResultSet* resultSet) const override {
			return resultSet->getString(1);
		}
	};
	CodeMapper mapper;
	auto rows = sqlSession->executeQuery<std::string>(sql, mapper, params);
	if (rows.empty()) return "";
	return rows.front();
}
