/*
 @Author: nanbowan
*/
#include "stdafx.h"
#include "OrderTypesDAO.h"

#include <sstream>
#include <vector>


int OrderTypesDAO::update(const OrderTypesDO& uObj)
{
	string sql = "UPDATE `ba_order_type` SET `order_type_code`=?, `order_type_name`=? WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s%s%s", uObj.getCode(), uObj.getName(), uObj.getId());
}

int OrderTypesDAO::deleteById(string id)
{
	if (id == "0") {
		string sql = "DELETE FROM `ba_order_type` ";
		sqlSession->executeUpdate(sql);
		return 1;
	}

	string sql = "DELETE FROM `ba_order_type` WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s", id);
}

int OrderTypesDAO::deleteByIds(const std::string& ids)
{
	if (ids.empty())
	{
		return 0;
	}
	// 将逗号分隔的id拆分为参数，避免拼接字符串造成的注入风险
	std::vector<std::string> idList;
	std::string item;
	std::stringstream ss(ids);
	while (std::getline(ss, item, ','))
	{
		if (!item.empty())
		{
			idList.push_back(item);
		}
	}
	if (idList.empty())
	{
		return 0;
	}
	string sql = "DELETE FROM `ba_order_type` WHERE `id` IN (";
	SqlParams params;
	for (size_t i = 0; i < idList.size(); i++)
	{
		if (i > 0)
		{
			sql += ",";
		}
		sql += "?";
		SQLPARAMS_PUSH(params, "s", std::string, idList[i]);
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}