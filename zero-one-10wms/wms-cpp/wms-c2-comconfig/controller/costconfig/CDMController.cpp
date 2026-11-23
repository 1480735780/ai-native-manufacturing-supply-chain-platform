#include"stdafx.h"
#include"CDMController.h"
#include"domain/dto/CDMattr/CDMDTO.h"

StringJsonVO::Wrapper CDMController::execModify(const CdmDTO::Wrapper& dto)
{
	auto jvo = StringJsonVO::createShared();

	CdmService service;
	if (service.updateData(dto)) {
		jvo->success("success");
	}
	else
	{
		jvo->fail( "fail" );
	}
	return jvo;

}

Uint64JsonVO::Wrapper CDMController::execRemove(const CddDTO::Wrapper& dto)
{
	auto jvo = Uint64JsonVO::createShared();
	Vector<String> ids = dto->companyId;
	if (!ids || ids->empty()) {
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 不能返回局部vector的引用，先拷贝为值
	vector<string> idList;
	for (const auto& id : *ids) {
		if (id) { idList.push_back(id); }
	}
	CdmService service;
	if (service.removeData(idList)) {
		jvo->success(UInt64(idList.size()));
	}
	else
	{
		jvo->fail(UInt64(-1));
	}
	return jvo;
}
