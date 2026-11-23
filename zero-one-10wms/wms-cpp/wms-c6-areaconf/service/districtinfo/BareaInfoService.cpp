#include "stdafx.h"
#include "BareaInfoService.h"
#include "dao/districtinfo/BareaInfoDAO.h"

BareaInfoPageDTO::Wrapper BareaInfoService::list(const BareaInfoQuery::Wrapper& query)
{
	auto pages = BareaInfoPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	// count total rows with same conditions
	BareaInfoDAO dao;
	uint64_t total = dao.count(query);
	pages->total = total;
	if (total <= 0)
	{
		return pages;
	}
	pages->calcPages();

	auto list = dao.infoList(query);
	for (auto sub : list)
	{
		auto dto = BareaInfoDTO::createShared();
		dto->id = sub.getId();
		dto->code = sub.getBarea_code();
		dto->name = sub.getBarea_name();
		dto->rdata = sub.getBarea_rdata();
		pages->addData(dto);
	}
	return pages;
}
