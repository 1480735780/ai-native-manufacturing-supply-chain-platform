#include "stdafx.h"
#include "DeleteController.h"
#include "service/delete-industry-class/InduDeleteService.h"

/*检查需要上传的批量id是否合法*/
inline bool check1(const DeleteDTO::Wrapper& id) {
	Vector<String> ids = id->Id;
	for (const auto& Id : *ids) {
		if (!Id) {
			return false;
		}
	}
	return true;
}

// 注意：不能返回 vector<string>& 引用，否则会指向已销毁的局部对象
inline vector<string> to_vector(const DeleteDTO::Wrapper& id) {
	vector<string> ans;
	Vector<String> ids = id->Id;
	for (const auto& Id : *ids) {
		ans.push_back(Id);
	}
	return ans;
}

Uint64JsonVO::Wrapper DeleteController::execDeleteClass(const DeleteDTO::Wrapper& id)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	if (!check1(id))
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 定义一个Service
	InduDeleteService service;
	// 执行数据删除（批量）
	vector<string> ids = to_vector(id);
	if (service.removeData(ids)) {
		jvo->success(UInt64(ids.size()));
	}
	else
	{
		jvo->fail(UInt64(-1));
	}
	// 响应结果
	return jvo;
}
