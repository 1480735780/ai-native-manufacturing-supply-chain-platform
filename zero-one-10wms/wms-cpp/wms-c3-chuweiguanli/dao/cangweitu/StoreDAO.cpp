#include "stdafx.h"
#include "StoreDAO.h"
#include "StoreMapper.h"
#include <sstream>

std::string StoreDAO::queryConditionBuilder(const HuoQuCangWeiShuJuQuery::Wrapper& query, SqlParams& params)
{
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->bin_store) {

		sqlCondition << " AND md.bin_store=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->bin_store.getValue(""));
	}
	if (query->bin_id) {

		sqlCondition << " AND md.ku_wei_bian_ma=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->bin_id.getValue(""));
	}
	if (query->znode) {

		sqlCondition << " AND md.znode=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->znode.getValue(""));
	}
	if (query->xnode) {

		sqlCondition << " AND cast(ifnull(md.xnode,'') AS unsigned)<=? ";
		SQLPARAMS_PUSH(params, "s", std::string, query->xnode.getValue(""));
	}
	if (query->ynode) {

		sqlCondition << " AND cast(ifnull(md.ynode,'') AS unsigned)<=? ";
		SQLPARAMS_PUSH(params, "s", std::string, query->ynode.getValue(""));
	}
	return sqlCondition.str();
}

std::list<WvDO> StoreDAO::selectWithPage(const HuoQuCangWeiShuJuQuery::Wrapper& query)
{
	SqlParams params;
	// 直查 md_bin 并计算占用数/颜色，绕开嵌套视图（视图相关子查询 + order by 隐藏列会导致 mysqlcppconn 挂死）
	string sql =
		"SELECT md.bin_store, md.ku_wei_bian_ma AS binid, "
		"ifnull(md.znode,'') AS znode, ifnull(md.xnode,'') AS xnode, ifnull(md.ynode,'') AS ynode, "
		"if((SELECT COUNT(0) FROM wv_stock ws WHERE ws.goods_qua<>0 AND ws.ku_wei_bian_ma=md.ku_wei_bian_ma)>1,'red','green') AS colour, "
		"(SELECT COUNT(0) FROM wv_stock ws WHERE ws.goods_qua<>0 AND ws.ku_wei_bian_ma=md.ku_wei_bian_ma) AS tincount "
		"FROM md_bin md ";
	// 构建查询条件
	sql += queryConditionBuilder(query, params);

	// 直接使用普通 Statement 执行（绕开 mysqlcppconn prepared statement 对表达式列的断言问题）
	try
	{
		std::unique_ptr<sql::Statement> stmt(sqlSession->getConnection()->createStatement());
		std::unique_ptr<sql::ResultSet> res(stmt->executeQuery(sql));
		StoreMapper mapper;
		std::list<WvDO> dataList;
		while (res->next()) {
			dataList.push_back(mapper.mapper(res.get()));
		}
		return dataList;
	}
	catch (const std::exception& e)
	{
		cerr << "StoreDAO selectWithPage Exception. " << e.what() << endl;
		return std::list<WvDO>();
	}
}