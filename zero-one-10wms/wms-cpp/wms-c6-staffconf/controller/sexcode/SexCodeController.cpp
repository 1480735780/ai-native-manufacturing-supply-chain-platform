#include "stdafx.h"
#include "SexCodeController.h"

#include <iostream>
#include "SqlSession.h"
#include "list"
#include "domain/do/sex/SexDO.h"
#include "dao/SexMapper.h"
#include "ExcelComponent.h"
#include "SimpleDateTimeFormat.h"


namespace fs = std::filesystem;

StuCodePageJsonVO::Wrapper SexCodeController::execQueryStucode(StuCodeQuery::Wrapper& stucodeQuery)
{
	StuCodeService service;
	auto result = service.listAll(stucodeQuery);
	auto jvo = StuCodePageJsonVO::createShared();
	jvo->success(result);
	return jvo;

}

StringJsonVO::Wrapper SexCodeController::execModifyStucode(const StuCodeDTO::Wrapper& stucodeDto, const PayloadDTO& payload)
{
	StuCodeService service;
	auto jvo = StringJsonVO::createShared();
	if (!stucodeDto->name || stucodeDto->name->empty() || !stucodeDto->code || stucodeDto->code->empty())
	{
		jvo->fail("");
		return jvo;
	}
	auto result = service.updateStuCode(stucodeDto, payload);

	if (result)
	{
		jvo->success("success");
	}
	else
	{
		jvo->fail("failed");
	}
	return jvo;
}

StringJsonVO::Wrapper SexCodeController::execSetStucode(const StuCodeDTO::Wrapper& stucodeDto, const PayloadDTO& payload)
{
	StuCodeService service;
	auto jvo = StringJsonVO::createShared();
	if (!stucodeDto->name || stucodeDto->name->empty() || !stucodeDto->code || stucodeDto->code->empty())
	{
		jvo->fail("");
		return jvo;
	}
	auto result = service.setStuCode(stucodeDto, payload);

	if (result)
	{
		jvo->success("success");
	}
	else
	{
		jvo->fail("failed");
	}
	return jvo;
}

StringJsonVO::Wrapper SexCodeController::execDelStucode(const StuCodeDelDTO::Wrapper& stucodeDto)
{
	StuCodeService service;
	auto jvo = StringJsonVO::createShared();
	if (!stucodeDto->delList || stucodeDto->delList->empty())
	{
		jvo->fail("");
		return jvo;
	}

	auto result = service.setDelCode(stucodeDto);

	if (result)
	{
		jvo->success("success");
	}
	else
	{
		jvo->fail("failed");
	}
	return jvo;
}

StringJsonVO::Wrapper SexCodeController::execUploadOne(std::shared_ptr<IncomingRequest> request, const PayloadDTO& payload)
{
	auto jvo = StringJsonVO::createShared();

	// 1 read multipart file field
	API_MULTIPART_INIT(container, reader);
	API_MULTIPART_CONFIG_MEMO_DEFAULT(reader, -1);
	request->transferBody(&reader);
	API_MULTIPART_PARSE_FILE_FIELD(container, "file", file);

	if (!file)
	{
		jvo->fail("Not Found File");
		return jvo;
	}

	// 2 parse excel from memory, sheet name unified as Sheet1
	// fix: old code treated header row as data and had no row size check
	auto readData = ExcelComponent::readIntoVector(file->data(), file->size(), "Sheet1");
	if (readData.size() <= 1)
	{
		jvo->fail("Empty File");
		return jvo;
	}

	// 3 skip header row, validate each row, insert valid rows only
	SqlSession sqlsession;
	uint64_t okCount = 0;
	uint64_t skipCount = 0;
	uint64_t failCount = 0;
	for (size_t i = 1; i < readData.size(); i++)
	{
		auto& row = readData[i];
		// fix: row size check to avoid out-of-range access (old code assumed 3 cells)
		if (row.size() < 2 || row[0].empty() || row[1].empty())
		{
			failCount++;
			continue;
		}
		// fix: exported file has 3 columns (id, code, name); 2-column files use (code, name)
		const std::string& sexCode = row.size() >= 3 ? row[1] : row[0];
		const std::string& sexName = row.size() >= 3 ? row[2] : row[1];
		auto time = SimpleDateTimeFormat::format();
		auto name = payload.getUsername();
		auto by = payload.getRealname();
		auto org = payload.getOrgcode();
		auto company = payload.getCompanycode();
		// debug: dump parsed row values
		// fix: no unique index on sex_sta_code, check duplicates before insert
		string chkSql = "SELECT COUNT(*) FROM ba_sex_sta WHERE sex_sta_code = ?";
		// fix: pass by value, va_arg(std::string) cannot take a reference (UB)
		uint64_t exists = sqlsession.executeQueryNumerical(chkSql, "%s", std::string(sexCode));
		if (exists > 0)
		{
			skipCount++;
			continue;
		}
		SnowFlake sf(0, 7);
		std::string id = std::to_string(sf.nextId());
		string sql = "INSERT INTO `ba_sex_sta` (`id`, `create_name`,`create_by`,`create_date`,`update_name`,`update_by`,`update_date`,`sys_org_code`,`sys_company_code`,`sex_sta_code`, `sex_sta_name`) VALUES(?, ?, ?,?,?,?,?,?,?,?,?)";
		// fix: pass std::string by value (va_arg(args, std::string) cannot safely take references)
		auto ch = sqlsession.executeUpdate(sql, "%s%s%s%s%s%s%s%s%s%s%s",
			id, std::string(name), std::string(by), std::string(time),
			std::string(name), std::string(by), std::string(time),
			std::string(org), std::string(company), sexCode, sexName);
		if (ch > 0)
		{
			okCount++;
		}
		else
		{
			failCount++;
		}
	}

	if (okCount == 0 && skipCount == 0)
	{
		jvo->fail("all rows failed");
		return jvo;
	}
	if (okCount == 0 && skipCount > 0)
	{
		// all rows are duplicates, report as success with 0 imported
		jvo->success(String("imported 0 rows, skipped " + std::to_string(skipCount) + ", failed " + std::to_string(failCount)));
		return jvo;
	}
	jvo->success(String("imported " + std::to_string(okCount) + " rows, skipped " + std::to_string(skipCount) + ", failed " + std::to_string(failCount)));
	return jvo;
}

std::shared_ptr<oatpp::web::server::api::ApiController::OutgoingResponse> SexCodeController::execDownloadFile()
{
	// query all rows from database
	SqlSession sqlsession;
	string sql = "SELECT id,sex_sta_code,sex_sta_name FROM ba_sex_sta ";
	SexMapper mapper;
	list<SexDO> lres = sqlsession.executeQuery<SexDO>(sql, mapper);

	// build excel data with header row
	// fix: old export had no header row, so exported file could not be re-imported as template
	std::vector<std::vector<std::string>> chvec;
	std::vector<std::string> head;
	head.push_back("id");
	head.push_back(ZH_WORDS_GETTER("sex.filed.sexcode"));
	head.push_back(ZH_WORDS_GETTER("sex.filed.sexname"));
	chvec.push_back(head);
	for (auto chl : lres)
	{
		std::vector<string> vec;
		vec.push_back(chl.getId());
		vec.push_back(chl.getSexCode());
		vec.push_back(chl.getSexName());
		chvec.push_back(vec);
	}

	// build excel buffer in memory, sheet name unified as Sheet1
	ExcelComponent excel;
	auto buff = excel.writeVectorToBuff("Sheet1", chvec);
	const char* data = reinterpret_cast<const char*>(buff.data());
	auto fstring = String(data, buff.size());

	if (!fstring)
	{
		std::cerr << "Failed to build excel buffer" << std::endl;
		return createResponse(Status::CODE_404, "File Not Found");
	}

	auto response = createResponse(Status::CODE_200, fstring);
	response->putHeader("Content-Disposition", "attachment; filename=sex.xlsx");

	return response;
}
