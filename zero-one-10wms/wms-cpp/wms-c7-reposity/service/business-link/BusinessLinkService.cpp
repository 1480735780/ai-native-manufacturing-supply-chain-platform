#include "stdafx.h"
#include "BusinessLinkService.h"
#include "../../dao/business-link/BusinessLinkDAO.h"
#include "../../domain/do/bussiness-link/BusinessLinkDO.h"
#include "../../lib-common/include/id/UuidFacade.h"
#include "../../lib-oatpp/include/domain/dto/PayloadDTO.h"

/**
 * 分页查询业务环节列表
 */
BusinessLinkPageDTO::Wrapper BusinessLinkService::listQueryBusinessLink(const BusinessLinkQuery::Wrapper& query)
{
	// 构建返回对象
	auto pages = BusinessLinkPageDTO::createShared();
	pages->pageIndex = query->pageIndex;
	pages->pageSize = query->pageSize;

	BusinessLinkDAO dao;
	// 查询数据总条数
	uint64_t count = dao.count(query);
	if (count <= 0)
	{
		return pages;
	}

	// 分页查询数据
	pages->total = count;
	pages->calcPages();

	list<BusinessLinkDO> result = dao.selectWithPage(query);
	// 将DO转换成DTO
	for (const auto& sub : result)
	{
		auto dto = BusinessLinkDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub,
			id, Id,
			create_name, CreateName,
			create_by, CreateBy,
			create_date, CreateDate,
			update_name, UpdateName,
			update_by, UpdateBy,
			update_date, UpdateDate,
			sys_org_code, SysOrgCode,
			sys_company_code, SysCompanyCode,
			oper_step_code, OperStepCode,
			oper_step_name, OperStepName);
		pages->addData(dto);
	}
	return pages;
}

/**
 * 查询业务环节名称列表（用于表单下拉框）
 */
oatpp::List<BusinessLinkNameDTO::Wrapper> BusinessLinkService::listBusinessLinkName()
{
	auto list = oatpp::List<BusinessLinkNameDTO::Wrapper>::createShared();
	BusinessLinkDAO dao;
	for (const auto& sub : dao.selectAllName())
	{
		auto dto = BusinessLinkNameDTO::createShared();
		ZO_STAR_DOMAIN_DO_TO_DTO(dto, sub,
			id, Id,
			oper_step_code, OperStepCode,
			oper_step_name, OperStepName);
		list->push_back(dto);
	}
	return list;
}

/**
 * 录入业务环节
 */
uint64_t BusinessLinkService::addBusinessLink(const BusinessLinkAddDTO::Wrapper& dto, const PayloadDTO& payload)
{
	BusinessLinkDO data;
	// 组装DO数据（主键由服务端生成，不从DTO取值）
	ZO_STAR_DOMAIN_DTO_TO_DO(data, dto, OperStepCode, oper_step_code, OperStepName, oper_step_name);

	// 添加id
	data.setId(UuidFacade().genUuid());

	// 创建人名称、创建人登录名称、所属部门、所属公司
	// 注：create_date 由数据库 NOW() 生成
	data.setCreateName(payload.getUsername());
	data.setCreateBy(payload.getRealname());
	data.setSysOrgCode(payload.getOrgcode());
	data.setSysCompanyCode(payload.getCompanycode());

	BusinessLinkDAO dao;
	return dao.insert(data);
}
