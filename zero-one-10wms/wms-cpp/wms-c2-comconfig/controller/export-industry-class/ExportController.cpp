#include "stdafx.h"
#include <iostream>
#include "ExportController.h"
#include <regex>

// FastDFS需要导入的头
#include "ServerInfo.h"
#include "NacosClient.h"
#include "FastDfsClient.h"
#include "SimpleDateTimeFormat.h"
#include "ExcelComponent.h"

// 查询行业分类数据
#include "dao/enterprisedao/enterpriseDAO.h"
#include "domain/query/enterprisePageQuery.h"
#include "domain/do/enterpriseDO.h"


std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> ExportController::execExportExcel(const String& filename)
{
	//表`ba_classfl`对应结构
	std::vector<std::string> ba_classfl = {
	ZH_WORDS_GETTER("chengfeng.id"),
	ZH_WORDS_GETTER("chengfeng.code"),
	ZH_WORDS_GETTER("chengfeng.name"),
	ZH_WORDS_GETTER("chengfeng.del")
	};
	std::vector<std::string> ba_classfl_en = {
		"id","code","name","del"
	};

	// 从数据库查询全部行业分类数据（不伪造数据）
	auto query = enterprisePageQuery::createShared();
	query->pageIndex = 1;
	query->pageSize = 100000;

	enterpriseDAO dao;
	std::list<EnterpriseDO> list = dao.selectWithPage(query);

	// 构造表格数据
	std::vector<std::vector<std::string>> data;
	data.push_back(ba_classfl);
	data.push_back(ba_classfl_en);

	for (const auto& item : list)
	{
		std::vector<std::string> row = {
			item.getId(),
			item.getComTypeCode(),
			item.getComTypeName(),
			std::to_string(item.getComTypeDel())
		};
		data.push_back(row);
	}

	// 生成 excel 内存 buffer 并直接返回给客户端
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff("行业分类", data);
	const char* tsData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(tsData, buff.size());

	// 判断是否读取成功
	if (!fstring)
	{
		std::cerr << "Failed to build excel buffer: " << std::strerror(errno) << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	// 创建响应头
	auto response = createResponse(Status::CODE_200, fstring);

	// 设置响应头信息
	response->putHeader("Content-Disposition", "attachment; filename=" + filename.getValue(""));

	// 影响成功结果
	return response;
}
