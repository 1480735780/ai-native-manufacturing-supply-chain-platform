#pragma once
#ifndef _BIN_TRANSFER_SERVICE_
#define _BIN_TRANSFER_SERVICE_
#include "domain/vo/shengchengchuweizhuanyi/BinTransferVO.h"
#include "domain/query/shengchengchuweizhuanyi/BinTransferQuery.h"
#include "domain/dto/shengchengchuweizhuanyi/BinTransferDTO.h"

/**
 * 生成储位转移服务
 */
class BinTransferService
{
public:
	// 分页获取储位可移动列表
	BinTransferPageDTO::Wrapper queryList(const BinTransferQuery::Wrapper& query);
	// 批量生成储位转移任务
	uint64_t generateTasks(const BinTransferBatchDTO::Wrapper& dto, const PayloadDTO& payload);
};

#endif // !_BIN_TRANSFER_SERVICE_
