#include "stdafx.h"
#include "ModifyController.h"
#include "service/modify-industry-class/ModifyService.h"

Uint64JsonVO::Wrapper ModifyController::execModifyClass(const ModifyDTO::Wrapper& dto)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	std::string yes = ZH_WORDS_GETTER("chengfeng.yes");
	std::string no = ZH_WORDS_GETTER("chengfeng.no");

	std::string del = dto->classfl_del;

	// 参数校验：id 必填；停用标记兼容字典值（是/否）与库内实际取值（1/0）
	bool delValid = (del == yes || del == no || del == "1" || del == "0");
	if (!dto->id || !delValid)
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 定义一个Service
	ModifyService service;
	// 执行数据修改
	if (service.updateData(dto)) {
		jvo->success(UInt64(1));
	}
	else
	{
		jvo->fail(UInt64(-1));
	}

	// 响应结果
	return jvo;
}
