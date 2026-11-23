#pragma once

#ifndef BUSINESS_LINK_NAME_LIST_JsonVO
#define BUSINESS_LINK_NAME_LIST_JsonVO

#include "../../GlobalInclude.h"
#include "../../dto/business-link/BusinessLinkDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 业务环节名称列表响应对象
 * 每条数据包含（唯一标识、编码、名称），用于表单输入下拉列表框
 */
class BusinessLinkNameListJsonVO : public JsonVO<oatpp::List<BusinessLinkNameDTO::Wrapper>>
{
	DTO_INIT(BusinessLinkNameListJsonVO, JsonVO<oatpp::List<BusinessLinkNameDTO::Wrapper>>);
};

#include OATPP_CODEGEN_END(DTO)

#endif
