#define _CRT_SECURE_NO_WARNINGS
#include "stdafx.h"
#include "GoodsDiffPostController.h"
#include "ExcelComponent.h"

// 企业等级（ba_com_deg）查询所需
#include "dao/comdegfig/ComdegfigDAO.h"
#include "domain/query/comdeg/ComdegQuery.h"
#include "domain/do/condegfig/ComdegfigDO.h"


std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> GoodsDiffPostController::execExportDiffPost(const ExportGoodsDiffPostQuery::Wrapper& query)
{
	// 导出企业等级数据：直接查询 ba_com_deg，返回真实的 Excel 内容
	auto degQuery = ComdegQuery::createShared();
	// 导出场景需要全量数据，固定使用大分页（PageQuery 默认 pageSize 只有 5）
	degQuery->pageIndex = 1;
	degQuery->pageSize = 100000;

	ComdegfigDAO dao;
	std::list<ComdegfigDO> list = dao.selectWithPage(degQuery);

	// 表头（中文 + 英文），与企业等级字段一一对应
	std::vector<std::string> header = { "ID", "企业等级代码", "企业等级名称", "停用" };
	std::vector<std::string> headerEn = { "id", "degcode", "degname", "degdel" };

	std::vector<std::vector<std::string>> data;
	data.push_back(header);
	data.push_back(headerEn);

	for (const auto& item : list)
	{
		std::vector<std::string> row = {
			item.getId(),
			item.getDegCode(),
			item.getDegName(),
			item.getDegDel()
		};
		data.push_back(row);
	}

	// 生成 excel 内存 buffer 并直接返回
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff("企业等级", data);
	const char* tsData = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(tsData, buff.size());

	if (!fstring)
	{
		std::cerr << "Failed to build excel buffer: " << std::strerror(errno) << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	auto response = createResponse(Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=entleve.xlsx");

	return response;
}
