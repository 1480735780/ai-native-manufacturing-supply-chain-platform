#pragma once
/*
 Copyright Zero One Star. All rights reserved.

 @Author: mao
 @Date: 2025/2/27 16:12:16

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

	  https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*/
#ifndef _DEFPLAT_DAO_
#define _DEFPLAT_DAO_
#include "BaseDAO.h"
#include "../../domain/do/def-plat/PlatDO.h"
#include "../../domain/query/def-file/DefPlatQuery.h"
//#include "../../domain/query/sample/SampleQuery.h"

/**
 * 示例表数据库操作实现
 */
class DefPlatDAO : public BaseDAO
{
private:
	//************************************
	// Method:      queryConditionBuilder
	// FullName:    SampleDAO::queryConditionBuilder
	// Access:      private 
	// Returns:     std::string 返回条件SQL语句，即WHERE部分的语句
	// Parameter:   const SampleQuery::Wrapper& query 查询数据对象
	// Parameter:   SqlParams& params 存放查询数据的参数对象
	// Description: 查询条件构建器，根据SampleQuery对象动态构建查询条件相关参数
	//************************************
	//inline std::string queryConditionBuilder(const SampleQuery::Wrapper& query, SqlParams& params);
public:
	// 通过ID删除数据
	uint64_t deleteById(string id);
	// 修改数据
	uint64_t update(string id,const PlatDO& uObj);
	// 查询所有数据
	std::list<PlatDO> queryAll();
	// 查询月台名称列表（未停用）
	std::list<PlatDO> queryNameList();
	// 条件查询计数
	uint64_t count(const DefPlatQuery::Wrapper& query);
	// 条件分页查询
	std::list<PlatDO> selectWithPage(const DefPlatQuery::Wrapper& query);
	// 新增数据
	int insert(const PlatDO& iObj);
	// 批量删除数据（逻辑删除，置停用）
	uint64_t deleteBatch(const std::list<string>& ids);
	// 检查月台代码是否已存在
	uint64_t countByCode(const string& platform_code);
	// 批量导入数据
	bool importAllData(const std::vector<std::vector<std::string>>& xdata, const string& create_name, const string& create_by, const string& orgcode, const string& companycode);
	
private:
	// 查询条件构造器
	inline std::string queryConditionBuilder(const DefPlatQuery::Wrapper& query, SqlParams& params);
	std::string getCurrentDateTime();
};
#endif // !_DEFPLAT_DAO_
