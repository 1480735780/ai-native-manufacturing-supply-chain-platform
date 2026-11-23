#pragma once
// batch delete DTO for work state and education code
#ifndef _BATCH_DEL_DTO_
#define _BATCH_DEL_DTO_

#include "../../GlobalInclude.h"
#include "ApiHelper.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * batch delete by id list
 */
class WorkStateBatchDelDTO : public oatpp::DTO
{
	DTO_INIT(WorkStateBatchDelDTO, DTO);
	// id list
	API_DTO_FIELD_DEFAULT(List<String>, ids, "id list");
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_BATCH_DEL_DTO_
