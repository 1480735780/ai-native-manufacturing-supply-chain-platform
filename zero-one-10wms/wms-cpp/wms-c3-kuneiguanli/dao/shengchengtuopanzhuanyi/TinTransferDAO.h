#pragma once
#ifndef _TIN_TRANSFER_DAO_
#define _TIN_TRANSFER_DAO_
#include "BaseDAO.h"
#include "../../domain/do/StockTransferDO.h"
#include "../../domain/query/shengchengtuopanzhuanyi/TinTransferQuery.h"

/**
 * 托盘转移-可转移列表数据库操作
 */
class TinTransferDAO : public BaseDAO
{
private:
	inline std::string queryConditionBuilder(const TinTransferQuery::Wrapper& query, SqlParams& params);
public:
	uint64_t count(const TinTransferQuery::Wrapper& query);
	std::list<StockTransferDO> selectWithPage(const TinTransferQuery::Wrapper& query);
};

#endif // !_TIN_TRANSFER_DAO_
