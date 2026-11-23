#pragma once
#ifndef _GETENTERPRISELEVELNAME_DTO_
#define _GETENTERPRISELEVELNAME_DTO_
#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 企业等级名称列表 DTO（参照企业属性名称列表，使用List字段承载下拉列表）
 */
class EnterpriseLevelNameDTO : public oatpp::DTO
{
	DTO_INIT(EnterpriseLevelNameDTO, DTO);
	// 企业等级名称列表
	DTO_FIELD(List<String>, name) = {};
	DTO_FIELD_INFO(name) {
		info->description = ZH_WORDS_GETTER("enterprise.level.name");
	}
	DTO_FIELD(List<String>, code) = {};
	DTO_FIELD_INFO(code) {
		info->description = ZH_WORDS_GETTER("enterprise.level.code");
	}
	DTO_FIELD(List<String>, id) = {};
	DTO_FIELD_INFO(id) {
		info->description = ZH_WORDS_GETTER("enterprise.level.id");
	}
	DTO_FIELD(List<String>, ban) = {};
	DTO_FIELD_INFO(ban) {
		info->description = ZH_WORDS_GETTER("enterprise.level.ban");
	}
};
class EnterpriseLevelNamePageDTO : public PageDTO<EnterpriseLevelNameDTO::Wrapper>
{
	DTO_INIT(EnterpriseLevelNamePageDTO, PageDTO<EnterpriseLevelNameDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_GETENTERPRISELEVELNAME_DTO_
