#pragma once
// batch delete DTO for education code
#ifndef _EDU_BATCH_DEL_DTO_
#define _EDU_BATCH_DEL_DTO_

#include "../../GlobalInclude.h"
#include "ApiHelper.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * batch delete by id list
 */
class EduBatchDelDTO : public oatpp::DTO
{
	DTO_INIT(EduBatchDelDTO, DTO);
	// id list
	DTO_FIELD(List<String>, ids);
	DTO_FIELD_INFO(ids)
	{
		info->description = "id list";
	}
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_EDU_BATCH_DEL_DTO_
