#pragma once
/*
 @Author: nanbowan
*/

#ifndef _LIBRARY_DAO_
#define _LIBRARY_DAO_
#include "BaseDAO.h"
#include "domain/do/library/LibraryDO.h"
#include "domain/dto/library/LibraryDTO.h"
#include "domain/query/library/LibraryQuery.h"
#include "LibraryMapper.h"

/**
 * 库位类型数据操作实现
 */
class LibraryDAO : public BaseDAO
{
private:
	//************************************
	// Method:      queryConditionBuilder
	// FullName:    LibraryDAO::queryConditionBuilder
	// Access:      private
	// Returns:     std::string 返回条件SQL语句，即WHERE部分的语句
	// Parameter:   const LibraryQuery::Wrapper& query 查询数据对象
	// Parameter:   SqlParams& params 存放查询数据的参数对象
	// Description: 查询条件构建器，根据LibraryQuery对象动态构建查询条件相关参数
	//************************************
	inline std::string queryConditionBuilder(const LibraryQuery::Wrapper& query, SqlParams& params);
public:
	// 修改数据
	int update(const LibraryDO& uObj);
	// 通过ID删除数据
	int deleteById(string id);

	// 统计数据条数
	uint64_t count(const LibraryQuery::Wrapper& query);
	// 分页查询数据
	std::list<LibraryDO> selectWithPage(const LibraryQuery::Wrapper& query);
	// 查询库位类型名称列表
	std::list<LibraryNameDO> selectLibraryNameList();
	// 插入数据
	uint64_t insert(const LibraryDO& iObj);
};
#endif // !_LIBRARY_DAO_

