/*
 @Author: nanbowan
*/
#include"stdafx.h"
#include"LibraryController.h"
#include "../../service/library/LibraryService.h"
#include "../../lib-common/include/SimpleDateTimeFormat.h"

Uint64JsonVO::Wrapper LibraryController::execModifyLibrary(const ModifyLibraryDTO::Wrapper& dto)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	string stdId = dto->id->c_str();
	uint64_t idValue = std::stoull(stdId);
	if (!dto->id || idValue < 0)
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 调用一个Service
	LibraryService service;
	// 执行数据修改
	if (service.updateData(dto)) {
		jvo->success(idValue);
	}
	else
	{
		jvo->fail(idValue);
	}
	// 响应结果
	return jvo;
}

Uint64JsonVO::Wrapper LibraryController::execDeleteLibrary(const oatpp::String& id)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验

	if ( id->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 调用一个Service
	LibraryService service;
	string stdId = id->c_str();
	uint64_t idValue = std::stoull(stdId);
	if (service.removeData(id)){
		jvo->success(idValue);
	}
	else
	{
		jvo->fail(idValue);
	}
	// 响应结果
	return jvo;
}

LibraryPageJsonVO::Wrapper LibraryController::execQueryLibrary(const LibraryQuery::Wrapper& query)
{
	// 定义一个Service
	LibraryService service;
	// 查询数据
	auto result = service.listQueryLibrary(query);
	// 响应结果
	auto jvo = LibraryPageJsonVO::createShared();
	jvo->success(result);
	return jvo;
}

Uint64JsonVO::Wrapper LibraryController::execAddLibrary(const LibraryAddDTO::Wrapper& dto, const PayloadDTO& payload)
{
	// 定义返回数据对象
	auto jvo = Uint64JsonVO::createShared();
	// 参数校验
	if (!dto->bin_type_code || !dto->bin_type_name)
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}
	// 非空校验
	if (dto->bin_type_code->empty() || dto->bin_type_name->empty())
	{
		jvo->init(UInt64(-1), RS_PARAMS_INVALID);
		return jvo;
	}

	// 生成Id，获取创建人、日期等信息，组合数据生成成DetailDTO
	LibraryDetailDTO::Wrapper detaildto;
	detaildto->id = UuidFacade().genUuid();
	detaildto->bin_type_code = dto->bin_type_code;
	detaildto->bin_type_name = dto->bin_type_name;
	// 创建人 创建人登录名称
	detaildto->create_name = payload.getUsername();
	detaildto->create_by = payload.getRealname();
	// 时间使用SimpleDateTimeFormat
	detaildto->create_date = SimpleDateTimeFormat::format();
	// 所属部门 所属公司
	detaildto->sys_org_code = payload.getOrgcode();
	detaildto->sys_company_code = payload.getCompanycode();

	// 定义service
	LibraryService service;
	// 执行插入服务
	uint64_t id = service.addData(detaildto);
	if (id > 0) {
		jvo->success(UInt64(id));
	}
	else {
		jvo->fail(UInt64(id));
	}
	// 返回响应结果
	return jvo;
}

LibraryNameListJsonVO::Wrapper LibraryController::execQueryLibraryName()
{
	// 定义一个Service
	LibraryService service;
	// 查询数据
	auto result = service.listLibraryName();
	// 响应结果
	auto jvo = LibraryNameListJsonVO::createShared();
	jvo->success(result);
	return jvo;
}


