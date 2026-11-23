#pragma once

#ifndef _CDMCONFIG_CONTROLLER_
#define _CDMCONFIG_CONTROLLER_

#include "domain/GlobalInclude.h"
#include "domain/vo/CDMattr/CDMinfoVO.h"
#include "domain/dto/CDMattr/CDMDTO.h"
#include "domain/vo/BaseJsonVO.h"
#include "service/comdegdm/CDMService.h"

#include OATPP_CODEGEN_BEGIN(ApiController) ///< Begin ApiController codegen section

/*
企业等级资料信息管理
*/

class CDMController : public oatpp::web::server::api::ApiController {
	API_ACCESS_DECLARE(CDMController);
public:

	//// 修改企业等级
	API_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("com.attribute.mod"), modifyCDMAttr, StringJsonVO::Wrapper);
	API_HANDLER_ENDPOINT_AUTH(API_M_PUT,"/entleve/update-entleve", modifyCDMAttr, BODY_DTO(CdmDTO::Wrapper, dto), execModify(dto));

	//// 批量删除企业等级
	API_DEF_ENDPOINT_INFO_AUTH(ZH_WORDS_GETTER("com.attribute.mod"), removeCDM, Uint64JsonVO::Wrapper);
	API_HANDLER_ENDPOINT_AUTH(API_M_DEL, "/entleve/delete-entleve", removeCDM, BODY_DTO(CddDTO::Wrapper, dto), execRemove(dto));

private:

	StringJsonVO::Wrapper execModify(const CdmDTO::Wrapper& dto);
	Uint64JsonVO::Wrapper execRemove(const CddDTO::Wrapper& dto);
	
};

#include OATPP_CODEGEN_END(ApiController) ///< End ApiController codegen section

#endif // !_ENTERPRISE_CONTROLLER_
