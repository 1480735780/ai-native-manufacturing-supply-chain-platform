#ifndef _BAWORKST_QUERY_
#define _BAWORKST_QUERY_

#include "../../GlobalInclude.h"
#include "domain/query/PageQuery.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 分页查询工作状态
 */
class BaWorkStQuery : public PageQuery
{
	DTO_INIT(BaWorkStQuery, PageQuery);
	// id
	DTO_FIELD(String, id);
	DTO_FIELD_INFO(id) {
		info->description = ZH_WORDS_GETTER("ba_work_st.field.id");
	}
	// 创建人名称
	DTO_FIELD(String, create_name);
	DTO_FIELD_INFO(create_name) {
		info->description = ZH_WORDS_GETTER("ba_work_st.field.create_name");
	}
	// 更新人名称
	DTO_FIELD(String, update_name);
	DTO_FIELD_INFO(update_name) {
		info->description = ZH_WORDS_GETTER("ba_work_st.field.age");
	}
	// 工作状态代码
	DTO_FIELD(String, work_sta_code);
	DTO_FIELD_INFO(work_sta_code) {
		info->description = ZH_WORDS_GETTER("ba_work_st.field.work_sta_code");
	}
	// 工作状态名称
	DTO_FIELD(String, work_sta_name);
	DTO_FIELD_INFO(work_sta_name) {
		info->description = ZH_WORDS_GETTER("ba_work_st.field.work_sta_name");
	}
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_SA_QUERY_