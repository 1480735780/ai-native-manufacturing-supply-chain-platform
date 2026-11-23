
#pragma once
#ifndef _MOVEGOODS_SERVICE_
#define _MOVEGOODS_SERVICE_
#include <list>
#include "domain/vo/kuneizhuanyi/MoveGoodsVO.h"
#include "domain/query/kuneizhuanyi/MoveGoodsQuery.h"
#include "domain/dto/kuneizhuanyi/MoveGoodsDTO.h"

/**
 * 库内转移任务服务
 */
class MoveGoodsService
{
public:
	// 分页查询转移任务列表
	MoveGoodsPageDTO::Wrapper queryList(const MoveGoodsQuery::Wrapper& query);
	// 修改转移任务
	bool modifyById(const MoveGoodsModifyDTO::Wrapper& dto, const std::string& usrName);
	// 批量转移(仅更新任务状态)
	uint64_t batchTransfer(const MoveGoodsBatchDTO::Wrapper& dto, const std::string& usrName);
	// 通过ID查询详细转移任务信息
	MoveGoodsDetailedDTO::Wrapper getDetailedById(const oatpp::String queryID);
	// 通过ID删除数据
	bool removeMoveGoods(const vector<string> id,const string usrName);
	// 通过ID查询导出转移任务信息
	vector<vector<string>> getDownLoadById(const vector<string>& ids);
};

#endif // !_MOVEGOODS_SERVICE_
