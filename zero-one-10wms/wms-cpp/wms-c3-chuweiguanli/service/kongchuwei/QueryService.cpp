#include "stdafx.h"
#include "QueryService.h"
#include "../../dao/kongchuwei/QueryDAO.h"

DaoChuKongChuWeiPageDTO::Wrapper QueryService::listAll(const DaoChuKongChuWeiQuery::Wrapper& query)
{
	// 构建返回对象
	auto pages = DaoChuKongChuWeiPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	// 查询数据总条数
	QueryDAO dao;
	uint64_t count = dao.count(query);
	if (count <= 0)
	{
		return pages;
	}

	// 分页查询数据
	pages->total = count;
	pages->calcPages();
	list<BinDO> result = dao.selectWithPage(query);
	// 将DO转换成DTO
	for (BinDO sub : result)
	{
		auto dto = DaoChuKongChuWeiDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, bin_store, BinStore, ku_wei_shu_xing, KuWeiShuXing, CHP_SHU_XING, CHPShuXing, ku_wei_bian_ma, KuWeiBianMa, suo_shu_ke_hu, SuoShuKeHu, zui_da_ti_ji, ZuiDaTiJi, shang_jia_ci_xu, ShangJiaCiXu, chang, Chang, kuan, Kuan, gao, Gao, zui_da_tuo_pan, ZuiDaTuoPan, ting_yong, TingYong, ku_wei_lei_xing, KuWeiLeiXing);
		pages->addData(dto);
	}
	return pages;
}

// paged list of empty bins
GetKongChuWeiListMycontrollerPageDTO::Wrapper QueryService::listKongChuWei(const GetKongChuWeiListMycontrollerQuery::Wrapper& query)
{
	auto pages = GetKongChuWeiListMycontrollerPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	QueryDAO dao;
	uint64_t count = dao.countKongChuWei(query);
	if (count <= 0)
	{
		return pages;
	}

	pages->total = count;
	pages->calcPages();
	std::list<BinDO> result = dao.selectKongChuWeiWithPage(query);
	for (BinDO sub : result)
	{
		auto dto = GetKongChuWeiListMycontrollerDTO::createShared();
		dto->id = sub.getId().c_str();
		dto->bin_store = sub.getBinStore().c_str();
		dto->chuweishuxing = sub.getKuWeiShuXing().c_str();
		dto->chp_shu_xing = sub.getCHPShuXing().c_str();
		dto->chuweibianma = sub.getKuWeiBianMa().c_str();
		dto->suo_shu_ke_hu = sub.getSuoShuKeHu().c_str();
		dto->zui_da_ti_ji = sub.getZuiDaTiJi().c_str();
		dto->shang_jia_ci_XU = sub.getShangJiaCiXu().c_str();
		dto->chang = sub.getChang().c_str();
		dto->kuan = sub.getKuan().c_str();
		dto->gao = sub.getGao().c_str();
		dto->zui_da_tuo_pan = sub.getZuiDaTuoPan().c_str();
		dto->zhuang_tai = sub.getTingYong().c_str();
		dto->ku_wei_lei_xing = sub.getKuWeiLeiXing().c_str();
		pages->addData(dto);
	}
	return pages;
}
