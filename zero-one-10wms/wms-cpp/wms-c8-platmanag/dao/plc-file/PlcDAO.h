#pragma once
/*
 @Author: tutu
 @Date: 2025/03/05 14:23:49
*/
#ifndef _PLC_DAO_
#define _PLC_DAO_
#include "BaseDAO.h"
#include "../../domain/do/plc-file/PlcFileDO.h"
#include "../../domain/query/plc-file/PlcFileQuery.h"

class PlcDAO : public BaseDAO
{
private:
	//************************************
	// Method:      queryConditionBuilder
	// FullName:    PlcDAO::queryConditionBuilder
	// Access:      private 
	// Returns:     std::string 返回条件SQL语句，即WHERE部分的语句
	// Parameter:   const PlcFileQuery::Wrapper& query 查询数据对象
	// Parameter:   SqlParams& params 存放查询数据的参数对象
	// Description: 查询条件构建器，根据PlcFileQuery对象动态构建查询条件相关参数
	//************************************
	inline std::string queryConditionBuilder(const PlcFileQuery::Wrapper& query, SqlParams& params);
	std::string getCurrentDateTime();
public:
	// 统计数据条数
	uint64_t count(const PlcFileQuery::Wrapper& query);
	//分页查询数据
	std::list<PlcBaseDO> selectWithPage(const PlcFileQuery::Wrapper& query);
	// 通过姓名查询数据
	//std::list<PlcDO> selectByName(const string& name);
	// 通过ID查询数据
	PtrPlcDO selectById(string id);
	// 通过ID查询指令集（执行用）
	PtrPlcDO selectConsById(string id);
	// 插入数据
	int insert(const PlcDO& iObj, string name, string realname, string orgcode, string companycode);
	// 修改数据
	int update(const PlcDO& uObj);
	// 通过ID删除数据
	int deleteById(string id);
	// 批量删除数据（物理删除）
	uint64_t deleteBatch(const std::list<string>& ids);
	// 按条件查询全部字段（导出用）
	std::list<PlcDO> selectAllForExport(const PlcFileQuery::Wrapper& query);
	// 执行指令：更新执行时间并记录执行结果（remark1）
	int markExecuted(const string& id, const string& execResult);
	// 批量导入数据
	bool importAllData(const std::vector<std::vector<std::string>>& xdata, const string& create_name, const string& create_by, const string& orgcode, const string& companycode);
};
#endif
