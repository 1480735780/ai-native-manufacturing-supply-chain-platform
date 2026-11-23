#include "stdafx.h"
#include "CangKuDingYiController.h"
#include "../../service/cangkudingyi/CangKuDingYiService.h"
#include "service/cangkudingyi/StoreService.h"
#include "ExcelComponent.h"

CangkuNameListJsonVO::Wrapper CangKuDingYiController::execListCangkuName(const PayloadDTO& payload) {
	//	构建响应结果
	auto jvo = CangkuNameListJsonVO::createShared();

	//	数据检验，暂时无需校验
	if (payload.getCode() != PayloadCode::SUCCESS) {
		
	}
	else {
		//	Service层
		CangKuDingYiService service;
		//	查询仓库名称列表
		auto result = service.getCangkuNameList();
        //	填充结果
		jvo->success(result);
	}
	
	

	return jvo;
}

//	删除仓库（支持批量删除）
StringJsonVO::Wrapper CangKuDingYiController::execDeleteCangku(const DeleteCangkuDTO::Wrapper& id_list, const PayloadDTO& payload) {
	//	构建响应结果
	auto jvo = StringJsonVO::createShared();

	if (payload.getCode() != PayloadCode::SUCCESS) {
		return {};
	}
	else {
		//	参数检验
		if (id_list->id->empty()) {	//	参数为空
			jvo->init("error", RS_PARAMS_INVALID);
			return jvo;
		}
		
		//	Service层
		CangKuDingYiService service;
		//	执行数据删除
		bool res = service.deleteCangkuById_List(id_list->id);
        if (res) {
			jvo->init("success", RS_SUCCESS);
		}
		else {
			jvo->init("error", RS_FAIL);
		}

		return jvo;
	}
}


//	将仓库名称列表导出为Excel文件，返回下载路径
StringJsonVO::Wrapper CangKuDingYiController::execDownLoadCangkuExcel(const ExportCangkuDTO::Wrapper& store_code_list, const PayloadDTO& payload) {
	//	构建响应结果
	auto jvo = StringJsonVO::createShared();
	
	if (payload.getCode() != PayloadCode::SUCCESS) {
		return {};
	}
	else {
		//	Service层
		CangKuDingYiService service;
		auto res = service.getpath_exportCangkuByCodeList(store_code_list->store_id);
		jvo->init("download_url: " + res, RS_SUCCESS);
	}

    return jvo;
}


CangkuListPageJsonVO::Wrapper CangKuDingYiController::execListCangku(const CangkuListQuery::Wrapper& query, const PayloadDTO& payload)
{
	StoreService service;

	//查询
	auto result = service.listAll(query);
	auto jvo = CangkuListPageJsonVO::createShared();
	jvo->success(result);
	return jvo;
}

StringJsonVO::Wrapper CangKuDingYiController::execUpload(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	auto jvo = StringJsonVO::createShared();

	// read the uploaded excel from the multipart body
	API_MULTIPART_INIT(container, reader);
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);
	request->transferBody(&reader);

	int fileCount = container->count();
	if (fileCount <= 0)
	{
		jvo->init("no file uploaded", RS_PARAMS_INVALID);
		return jvo;
	}

	int total = 0;
	for (int file_i = 0; file_i < fileCount; file_i++)
	{
		string filename = "file";
		filename += std::to_string(file_i);
		// parse the file field
		API_MULTIPART_PARSE_FILE_FIELD(container, filename, file);
		if (!file || file->empty())
		{
			continue;
		}
		// read sheet rows from memory buffer
		std::vector<std::vector<std::string>> data = ExcelComponent::readIntoVector(file->c_str(), file->size(), ZH_WORDS_GETTER("excel.sheet.s1"));
		if (data.empty())
		{
			continue;
		}
		StoreService service;
		int imported = service.importCangku(data, payload);
		total += imported;
	}

	if (total <= 0)
	{
		jvo->init("import failed", RS_FAIL);
		return jvo;
	}
	jvo->init("imported: " + std::to_string(total), RS_SUCCESS);
	return jvo;
}


