#include "Macros.h"
#include "enterpriseDAO.h"

//查询条件构建器
std::string enterpriseDAO::queryCondionBuilder(const enterprisePageQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->enterpriseClassificationCode && !query->enterpriseClassificationCode->empty()) {
		sqlCondition << " AND `classfl_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->enterpriseClassificationCode.getValue(""));
	}
	if (query->enterpriseClassificationName && !query->enterpriseClassificationName->empty()) {
		sqlCondition << " AND `classfl_name`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->enterpriseClassificationName.getValue(""));
	}
	return sqlCondition.str();
}
//计数
uint64_t enterpriseDAO::count(const enterprisePageQuery::Wrapper& query)
{
	string sql = "SELECT COUNT(*) FROM `ba_classfl`";
	SqlParams params;
	sql += queryCondionBuilder(query, params);
	return sqlSession->executeQueryNumerical(sql, params);
}
//增加企业分类信息
uint64_t enterpriseDAO::insert(const EnterpriseDO& enterpriseInfo)
{
	uint64_t jvo;
	/*
	添加redis
	缓存双写一致性
	*/
	string sql = "INSERT INTO `ba_classfl` (`id`,`create_name`,`create_by`,`create_date`,`classfl_code` ,`classfl_name`, `classfl_del`) VALUES(?,?,?,?,?,?,?)";
	jvo = sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s", enterpriseInfo.getId(), enterpriseInfo.getCreateName(), enterpriseInfo.getCreateBy(), enterpriseInfo.getCreateDate(), enterpriseInfo.getComTypeCode(), enterpriseInfo.getComTypeName(), to_string(enterpriseInfo.getComTypeDel()));
	return jvo;
}
//企业分类数据分页查询
std::list<EnterpriseDO> enterpriseDAO::selectWithPage(const enterprisePageQuery::Wrapper& query) {

	/*添加redis*/
	//回传 id，供前端修改/删除使用；列顺序与 EnterpriseDoMapper1 保持一致
	string sql = "SELECT `id`,`classfl_code` , `classfl_name`,`classfl_del` FROM `ba_classfl`";
	SqlParams params;
	EnterpriseDoMapper1 mapper;
	sql += queryCondionBuilder(query, params);
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);
	auto res = sqlSession->executeQuery<EnterpriseDO>(sql, mapper, params);
	return res;

}

//获取企业分类名称数据
std::list<EnterpriseDO> enterpriseDAO::getEnterpriseName()
{
	EnterpriseDoMapper map;
	/*添加redis*/
	string sql = "SELECT DISTINCT `classfl_name` FROM `ba_classfl`";
	return sqlSession->executeQuery<EnterpriseDO>(sql, map);
}
