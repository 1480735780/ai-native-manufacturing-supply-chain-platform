#include "stdafx.h"
#include "GoodsClassDAO.h"
#include "GoodsClassMapper.h"
#include <sstream>

// 查询条件构建器
std::string GoodsClassDAO::queryConditionBuilder(const GoodClassQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";

	// 计费商品类名称
	if (query->name) {
		sqlCondition << " AND `goods_class_name`=?"; // 使用字段
		SQLPARAMS_PUSH(params, "s", std::string, query->name.getValue(""));
	}

	// 计费商品类代码
	if (query->code) {
		sqlCondition << " AND `goods_class_code`=?"; // 使用字段
		SQLPARAMS_PUSH(params, "s", std::string, query->code.getValue(""));
	}

	// 创建人名称
	if (query->createName) {
		sqlCondition << " AND `create_name`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->createName.getValue(""));
	}

	// 创建人记录
	if (query->createBy) {
		sqlCondition << " AND `create_by`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->createBy.getValue(""));
	}

	//// 创建时间
	//if (query->create_date) {
	//    sqlCondition << " AND `create_date`=?";
	//    SQLPARAMS_PUSH(params, "s", std::string, query->create_date.getValue(""));
	//}

	// 更新人名称
	if (query->updateName) {
		sqlCondition << " AND `update_name`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->updateName.getValue(""));
	}

	// 更新人记录
	if (query->updateBy) {
		sqlCondition << " AND `update_by`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->updateBy.getValue(""));
	}

	//// 更新时间
	//if (query->update_date) {
	//    sqlCondition << " AND `update_date`=?";
	//    SQLPARAMS_PUSH(params, "s", std::string, query->update_date.getValue(""));
	//}

	// 系统组织代码
	if (query->sysOrgCode) {
		sqlCondition << " AND `sys_org_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->sysOrgCode.getValue(""));
	}

	// 系统公司代码
	if (query->sysCompanyCode) {
		sqlCondition << " AND `sys_company_code`=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->sysCompanyCode.getValue(""));
	}

	return sqlCondition.str();
}


// 插入
std::string GoodsClassDAO::insert(const GoodsClassDO& iObj)
{
	UuidFacade uf(1);
	std::string id = uf.genUuid();

	string sql = "INSERT INTO `ba_goods_class` ("
		"`id`, `goods_class_code`, `goods_class_name`, "
		"`create_name`, `create_by`,`create_date` , "
		"`update_name`, `update_by`, `update_date`, "
		"`sys_org_code`, `sys_company_code`) "
		"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

	if (sqlSession->executeUpdate(sql,
		"%s%s%s%s%s%s%s%s%s%s%s",
		id,
		iObj.getGoodsClassCode(),
		iObj.getGoodsClassName(),
		iObj.getCreateName(),
		iObj.getCreateBy(),
		iObj.getCreateDate(),
		iObj.getUpdateName(),
		iObj.getUpdateBy(),
		iObj.getUpdateDate(),
		iObj.getSysOrgCode(),
		iObj.getSysCompanyCode()) == 1) {
		return id;
	}
	return "";
}

// 修改
bool GoodsClassDAO::update(const GoodsClassDO& iObj)
{
	string sql = "UPDATE `ba_goods_class` SET "
		"`goods_class_code` = ?, "
		"`goods_class_name` = ?, "
		"`update_name` = ?, "
		"`update_by` = ?,"
		"`update_date` = ?,"
		"`sys_org_code` = ?,"
		"`sys_company_code` = ? "
		"WHERE `id` = ? ";

	return sqlSession->executeUpdate(sql,
		"%s%s%s%s%s%s%s%s",
		iObj.getGoodsClassCode(),
		iObj.getGoodsClassName	(),
		iObj.getUpdateName(),
		iObj.getUpdateBy(),
		iObj.getUpdateDate(),
		iObj.getSysOrgCode(),
		iObj.getSysCompanyCode(),
		iObj.getId()) == 1;
}

uint64_t GoodsClassDAO::count(const GoodClassQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM `ba_goods_class` ";
	// 使用查询条件构建器
	sql += queryConditionBuilder(query, params);
	// 执行查询
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<GoodsClassDO> GoodsClassDAO::selectName(const GoodClassQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT `id`,`goods_class_name` FROM `ba_goods_class` ";
	// 使用查询条件构建器
	sql += queryConditionBuilder(query, params);
	//// 使用分页参数
	//sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

	// 执行查询
	GoodsClassMapperName mapper;
	return sqlSession->executeQuery<GoodsClassDO>(sql, mapper, params);
}

std::list<GoodsClassDO> GoodsClassDAO::selectAllWithPage(const GoodClassQuery::Wrapper& query)
{
	SqlParams params;
	// 使用 SELECT 语句，查询所有字段
	string sql = "SELECT "
		"`id`, "                           // 主键
		"`goods_class_name`, "             // 计费商品类名称
		"`goods_class_code`, "             // 计费商品类代码
		"`create_name`, "                  // 创建人名称
		"`create_by`, "                    // 创建人记录
		"`update_name`, "                  // 更新人名称
		"`update_by`, "                    // 更新人记录
		"`sys_org_code`, "                // 系统组织代码
		"`sys_company_code`, "              // 系统公司代码
		"`create_date`, "                  // 创建时间
		"`update_date` "                  // 更新时间
		"FROM `ba_goods_class` ";
	// 使用查询条件构建器
	sql += queryConditionBuilder(query, params);
	// 使用分页参数
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

	// 执行查询
	GoodsClassMapperAll mapper;
	return sqlSession->executeQuery<GoodsClassDO>(sql, mapper, params);
}
// Batch delete rows by primary key ids
int GoodsClassDAO::deleteByIds(const std::vector<std::string>& ids)
{
	if (ids.empty()) return 0;
	SqlParams params;
	string sql = "DELETE FROM `ba_goods_class` WHERE `id` IN (";
	for (size_t i = 0; i < ids.size(); i++)
	{
		sql += (i == 0 ? "?" : ",?");
		SQLPARAMS_PUSH(params, "s", std::string, ids[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

// Select all rows for excel export
std::list<GoodsClassDO> GoodsClassDAO::selectForExport()
{
	SqlParams params;
	string sql = "SELECT "
		"`id`, "
		"`goods_class_name`, "
		"`goods_class_code`, "
		"`create_name`, "
		"`create_by`, "
		"`update_name`, "
		"`update_by`, "
		"`sys_org_code`, "
		"`sys_company_code`, "
		"`create_date`, "
		"`update_date` "
		"FROM `ba_goods_class` ORDER BY `goods_class_code`";
	GoodsClassMapperAll mapper;
	return sqlSession->executeQuery<GoodsClassDO>(sql, mapper, params);
}
