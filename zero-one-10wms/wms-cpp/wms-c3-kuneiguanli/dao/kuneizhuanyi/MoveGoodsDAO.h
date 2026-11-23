#pragma once
#ifndef _MOVEGOODS_DAO_
#define _MOVEGOODS_DAO_
#include "BaseDAO.h"
#include "../../domain/do/MoveGoodsDO.h"
#include "../../domain/query/kuneizhuanyi/MoveGoodsQuery.h"


class MoveGoodsDAO : public BaseDAO
{
private:
	// 查询条件构建器，根据MoveGoodsQuery对象动态构建WHERE部分
	inline std::string queryConditionBuilder(const MoveGoodsQuery::Wrapper& query, SqlParams& params);
public:
	// 统计转移任务条数
	uint64_t count(const MoveGoodsQuery::Wrapper& query);
	// 分页查询转移任务列表
	std::list<MoveGoodsDO> selectWithPage(const MoveGoodsQuery::Wrapper& query);
	// 新增转移任务
	int insert(const MoveGoodsDO& data);
	// 修改转移任务
	int updateById(const MoveGoodsDO& data);
	// 批量转移
	int batchUpdateStatus(const std::vector<std::string>& ids, const std::string& moveSta,
		const std::string& runSta, const std::string& usrName, const std::string& updateDate);
	// 通过ID查询转移任务详细数据
	PtrMoveGoodsDO selectDetailedById(const oatpp::String  queryID);
	// 通过ID查询转移任务导出数据
	std::vector<std::vector<string>> selectDownLoadById(const vector<string>& ids);
	// 通过ID删除数据
	int deleteById(const vector<string> id,const string usrName);
};
#endif // !_MOVEGOODS_DAO_
