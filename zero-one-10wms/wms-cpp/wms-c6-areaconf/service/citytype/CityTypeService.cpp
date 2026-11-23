#include "stdafx.h"
#include "CityTypeService.h"
#include "dao/citytype/CityTypeDAO.h"
#include <gtest/internal/gtest-string.h>
#include "Macros.h"
#include "ExcelComponent.h"
#include "FastDfsClient.h"
#include "id/SnowFlake.h"
#include "SimpleDateTimeFormat.h"

#define SET(v1, v2) obj.set##v1(v2)
std::string CityTypeService::Add(const CitytypeBaseDTO::Wrapper& dto, const PayloadDTO& payload)
{
    CityTypeAddDO obj;
    std::string id = "";
    SnowFlake sf(0,0);
    while (id == "") id = std::to_string(sf.nextId());
    SET(Id, id);
    SET(Cname, payload.getUsername());
    SET(Cby, payload.getRealname());
    SET(Cdate, SimpleDateTimeFormat::format());
    SET(Uname, obj.getCname());
    SET(Uby, obj.getCby());
    SET(Udate, obj.getCdate());
    SET(Orgcode, payload.getOrgcode());
    SET(Companycode, payload.getCompanycode());
    SET(Code, dto->code);
    SET(Name, dto->name);
    CityTypeDAO dao;
    if (dao.add(obj))
    {
        return id;
    }
    return "";
}
#undef SET

#define SET(v1, v2) obj.set##v1(v2)
bool CityTypeService::Udp(const CityTypeDTO::Wrapper& dto, const PayloadDTO& payload)
{
    CityTypeUpdDO obj;
    SET(Id, dto->id);
    SET(Uname, payload.getUsername());
    SET(Uby, payload.getRealname());
    SET(Udate, SimpleDateTimeFormat::format());
    SET(Orgcode, payload.getOrgcode());
    SET(Companycode, payload.getCompanycode());
    SET(Code, dto->code);
    SET(Name, dto->name);
    CityTypeDAO dao;
    return dao.upd(obj);
}
#undef SET

CityTypePageDTO::Wrapper  CityTypeService::listAll(const CityTypeQuery::Wrapper& query)
{
    // create page result
    auto pages = CityTypePageDTO::createShared();
    pages->pageIndex = query->pageIndex;
    pages->pageSize = query->pageSize;

    // count total rows with same conditions
    CityTypeDAO dao;
    uint64_t total = dao.count(query);
    pages->total = total;
    if (total <= 0)
    {
        return pages;
    }
    pages->calcPages();

    auto obj = dao.selectWithPage(query);
    for (auto sub : obj)
    {
        auto dto = CityTypeDTO::createShared();
        dto->id = sub.getId();
        dto->name = sub.getName();
        dto->code = sub.getCode();
        pages->addData(dto);
    }
    return pages;
}

oatpp::List<CityTypeNameDTO::Wrapper> CityTypeService::nameList()
{
    CityTypeDAO dao;
    auto obj = dao.getDistinctCityTypes();
    auto ans = oatpp::List<CityTypeNameDTO::Wrapper>::createShared();
    for (auto name : obj)
    {
        auto i = CityTypeNameDTO::createShared();
        i->id = name.getId();
        i->name = name.getName();
        ans->push_back(i);
    }
    return ans;
}

bool CityTypeService::removeData(std::string id)
{
	CityTypeDAO dao;
	return dao.deleteById(id) == 1;
}

int CityTypeService::import(const std::vector<std::vector<std::string>>& vec, const PayloadDTO& payload)
{
    int ok = 0;
    std::string name = payload.getUsername();
    std::string by = payload.getRealname();
    std::string date = SimpleDateTimeFormat::format();
    std::string org = payload.getOrgcode();
    std::string company = payload.getCompanycode();
    SnowFlake sf(1, 0);
    CityTypeDAO dao;
    for (auto line : vec)
    {
        if (line.size() < 2 || line[0] == "" || line[1] == "") continue;
        CityTypeAddDO obj;
        obj.setCby(by);
        obj.setCdate(date);
        obj.setCname(name);
        obj.setCode(line[0]);
        obj.setCompanycode(company);
        obj.setId(std::to_string(sf.nextId()));
        obj.setName(line[1]);
        obj.setOrgcode(org);
        obj.setUby(by);
        obj.setUdate(date);
        obj.setUname(name);
        if (dao.add(obj)) ok++;
    }
    return ok;
}

std::vector<std::vector<std::string>> CityTypeService::listAll()
{
    CityTypeDAO dao;
    auto datas = dao.listAll();
    std::vector<std::vector<std::string>> vec;
    std::vector<std::string> head(2, "");
    head[0] = ZH_WORDS_GETTER("citytype.code");
    head[1] = ZH_WORDS_GETTER("citytype.name");
    vec.push_back(head);
    for (auto sub : datas)
    {
        std::vector<std::string> line(2, "");
        line[0] = sub.getCode();
        line[1] = sub.getName();
        vec.push_back(line);
    }
    return vec;
}

int CityTypeService::removeDataBatch(const std::vector<std::string>& ids)
{
	CityTypeDAO dao;
	return dao.deleteByIds(ids);
}

std::vector<std::string> CityTypeService::listReferencedNames(const std::vector<std::string>& ids)
{
	// resolve ids to codes first
	std::vector<std::string> codes;
	CityTypeDAO dao;
	for (const auto& id : ids)
	{
		auto code = dao.getCodeById(id);
		if (!code.empty()) codes.push_back(code);
	}
	return dao.listReferencedCodes(codes);
}
