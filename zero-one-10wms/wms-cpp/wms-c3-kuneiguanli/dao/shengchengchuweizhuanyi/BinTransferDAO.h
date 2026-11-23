#pragma once
#ifndef _BIN_TRANSFER_DAO_
#define _BIN_TRANSFER_DAO_
#include "BaseDAO.h"
#include "../../domain/do/StockTransferDO.h"
#include "../../domain/query/shengchengchuweizhuanyi/BinTransferQuery.h"

/**
 * 储位转移-可移动列表数据库操作
 */
class BinTransferDAO : public BaseDAO
{
private:
	inline std::string queryConditionBuilder(const BinTransferQuery::Wrapper& query, SqlParams& params);
public:
	uint64_t count(const BinTransferQuery::Wrapper& query);
	std::list<StockTransferDO> selectWithPage(const BinTransferQuery::Wrapper& query);
};

#endif // !_BIN_TRANSFER_DAO_
