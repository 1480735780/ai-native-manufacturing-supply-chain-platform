#include "stdafx.h"
#include "CompanyStateController.h"

inline void init(const CompanyAddStateDTO::Wrapper& correct, const CompanyAddStateDTO::Wrapper& wrong) {
	correct->clientid = "1";
	correct->clientname = ZH_WORDS_GETTER("companystate.name");
	correct->state = ZH_WORDS_GETTER("companystate.state");


	wrong->clientid = "-1";
	wrong->clientname = "";
	wrong->state = "";
}

CompanyStateJsonVO::Wrapper CompanyStateController::execAddCompanyInfo(const CompanyAddStateDTO::Wrapper& dto, const PayloadDTO& payload) {
	auto jvo = CompanyStateJsonVO::createShared();

	auto correct = CompanyAddStateDTO::createShared();
	auto wrong = CompanyAddStateDTO::createShared();

	init(correct, wrong);

	// 参数校验：企业状态代码、名称、状态都不能为空
	if (!dto->clientid || !dto->clientname || !dto->state)
	{
		jvo->init(wrong, RS_PARAMS_INVALID);
		return jvo;
	}

	// 定义并执行 Service
	CompanyStateService service;
	uint64_t id = service.saveData(dto, payload);
	if (id > 0) {
		jvo->success(correct);
	}
	else
	{
		jvo->fail(wrong);
	}
	return jvo;
}
// 3.3 企业状态修改
CompanyStateJsonVO::Wrapper CompanyStateController::execModifyCompanyInfo(const CompanyUpdateStateDTO::Wrapper& dto, const PayloadDTO& payload) {
	auto jvo = CompanyStateJsonVO::createShared();

	auto correct = CompanyAddStateDTO::createShared();
	auto wrong = CompanyAddStateDTO::createShared();

	init(correct, wrong);

	// 参数校验：修改必须带主键 id，否则会更新到 0 行
	if (!dto->id)
	{
		jvo->init(wrong, RS_PARAMS_INVALID);
		return jvo;
	}

	// 定义并执行 Service
	CompanyStateService service;
	if (service.updateData(dto, payload)) {
		jvo->success(correct);
	}
	else
	{
		jvo->fail(wrong);
	}
	return jvo;
}

/*检查需要上传的批量公司id是否合法*/
inline bool check1(const CompanyRemoveStateDTO::Wrapper& id) {
	Vector<String> ids = id->companyId;
	if (!ids || ids->empty()) {
		return false;
	}
	for (const auto& companyId : *ids) {
		if (!companyId) {
			return false;
		}
	}
	return true;
}


//不可以传引用vector<string>&！！！返回的引用会指向一个已经被销毁的对象
inline std::vector<std::string> to_vector(const CompanyRemoveStateDTO::Wrapper& id) {
	vector<string> ans;
	Vector<String> ids = id->companyId;
	for (const auto& companyId : *ids) {
		ans.push_back(companyId);
	}
	return ans;
}


// 3.3 企业状态删除（支持批量）
CompanyStateJsonVO::Wrapper CompanyStateController::execRemoveCompanyInfo(const CompanyRemoveStateDTO::Wrapper& id) {
	auto jvo = CompanyStateJsonVO::createShared();

	auto correct = CompanyAddStateDTO::createShared();
	auto wrong = CompanyAddStateDTO::createShared();

	init(correct, wrong);

	// 参数校验
	if (!check1(id))
	{
		jvo->init(wrong, RS_PARAMS_INVALID);
		return jvo;
	}

	CompanyStateService service;
	// 只能调用一次删除：重复调用会因第二次删除 0 行而被判定为失败
	if (service.removeData1(to_vector(id))) {
		jvo->success(correct);
	}
	else
	{
		jvo->fail(wrong);
	}

	return jvo;
}
