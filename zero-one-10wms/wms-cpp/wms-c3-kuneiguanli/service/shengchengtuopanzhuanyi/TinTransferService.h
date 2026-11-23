#pragma once
#ifndef _TIN_TRANSFER_SERVICE_
#define _TIN_TRANSFER_SERVICE_
#include "domain/vo/shengchengtuopanzhuanyi/TinTransferVO.h"
#include "domain/query/shengchengtuopanzhuanyi/TinTransferQuery.h"
#include "domain/dto/shengchengtuopanzhuanyi/TinTransferDTO.h"

/**
 * 生成托盘转移服务
 */
class TinTransferService
{
public:
	// 分页获取托盘可转移列表
	TinTransferPageDTO::Wrapper queryList(const TinTransferQuery::Wrapper& query);
	// 批量生成托盘转移任务
	uint64_t generateTasks(const TinTransferBatchDTO::Wrapper& dto, const PayloadDTO& payload);
};

#endif // !_TIN_TRANSFER_SERVICE_
