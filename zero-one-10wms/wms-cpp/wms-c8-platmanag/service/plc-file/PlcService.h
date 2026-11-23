#pragma once
/*
 @Author: tutu
*/
#ifndef _PLC_SERVICE_
#define _PLC_SERVICE_
#include <list>
#include <vector>
#include "domain/vo/plc-file/PlcFileVO.h"
#include "domain/query/plc-file/PlcFileQuery.h"
#include "domain/dto/plc-file/PlcFileDto.h"
#include "../../domain/do/plc-file/PlcFileDO.h"

class PlcService
{
public:
	// 分页查询所有数据
	PlcListPageDTO::Wrapper listAll(const PlcFileQuery::Wrapper& query);
	// 通过ID查询单个数据
	PlcdetailDTO::Wrapper getById(string id);
	// 保存数据
	bool saveData(const PlcAddDTO::Wrapper& dto, string name, string realname, string orgcode, string companycode);
	// 修改数据
	bool updateData(const PlcdetailDTO::Wrapper& dto);
	// 通过ID删除数据
	bool removeData(string id);
	// 批量删除
	uint64_t removeBatch(const std::list<string>& ids);
	// 导出查询（全字段）
	std::list<PlcDO> listAllForExport(const PlcFileQuery::Wrapper& query);
	// 执行指令（单条）返回是否成功
	bool executeOne(const string& id);
	// 批量执行指令（返回成功条数）
	uint64_t executeBatch(const std::list<string>& ids);
	// 导入PLC指令
	bool importData(const std::vector<std::vector<std::string>>& xdata, const string& name, const string& realname, const string& orgcode, const string& companycode);
};

#endif

