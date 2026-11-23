#pragma once
/*
 @Author: c7 group
*/
#ifndef _BUSINESS_LINK_SERVICE_
#define _BUSINESS_LINK_SERVICE_

#include <list>
#include "domain/dto/business-link/BusinessLinkDTO.h"
#include "domain/query/business-link/BusinessLinkQuery.h"
#include "domain/vo/BaseJsonVO.h"
#include "domain/GlobalInclude.h"

/**
 * 业务环节服务实现
 * 说明：业务环节与作业环节(OperStep)操作同一张 ba_oper_step 表，
 *       本服务负责「查、增、名称列表」，改、删、导入导出由 OperStepService 负责。
 */
class BusinessLinkService
{
public:
	/**
	 * 分页查询业务环节列表
	 * @param query 查询条件（条件+分页）
	 */
	BusinessLinkPageDTO::Wrapper listQueryBusinessLink(const BusinessLinkQuery::Wrapper& query);

	/**
	 * 查询业务环节名称列表（用于表单下拉框）
	 * 每条数据包含（唯一标识、编码、名称）
	 */
	oatpp::List<BusinessLinkNameDTO::Wrapper> listBusinessLinkName();

	/**
	 * 录入业务环节
	 * @param dto 录入数据
	 * @param payload 当前登录用户信息（用于填充创建人等审计字段）
	 * @return 新增记录的主键
	 */
	uint64_t addBusinessLink(const BusinessLinkAddDTO::Wrapper& dto, const PayloadDTO& payload);
};

#endif // !_BUSINESS_LINK_SERVICE_
