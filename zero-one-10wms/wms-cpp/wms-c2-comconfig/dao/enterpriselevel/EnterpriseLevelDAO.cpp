#include "stdafx.h"
#include "EnterpriseLevelDAO.h"
#include "EnterpriseLevelMapper.h"
#include <sstream>


//获取企业等级名称数据
std::list<CustomerLevelDO> EnterpriseLevelDAO::getEnterpriseName()
{
	EnterpriseLevelMapper map;
	/*添加redis*/
	// 等级名称列表：同时取code/id/ban，供前端下拉展示
	string sql = "SELECT DISTINCT `com_deg_name`, `com_deg_code`, `id`, `com_deg_del` FROM `ba_com_deg`";
	return sqlSession->executeQuery<CustomerLevelDO>(sql, map);
}
