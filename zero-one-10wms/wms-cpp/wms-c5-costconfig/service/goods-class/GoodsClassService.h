#pragma once
/*
 Copyright Zero One Star. All rights reserved.
 
 @Author: Ann
 @Date: 2025/3/2 20:02
 
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
#ifndef _GOODSCLASS_SERVICE_
#define _GOODSCLASS_SERVICE_
#include <list>
#include <vector>
#include <string>
#include "domain/do/public-do/GoodsClassDO.h"
#include "domain/vo/goods-class/GoodsClassVO.h"
#include "domain/query/goods-class/GoodsClassQuery.h"
#include "domain/dto/goods-class/GoodsClassDTO.h"


/**
 * 操作计费商品类的增删改查
 */
class GoodsClassService
{
public:
	// 修改数据
	bool update(const GoodsClassModifyDTO::Wrapper& dto);
	// 保存数据
	string insert(const GoodsClassAddDTO::Wrapper& dto);
	// 分页查询所有数据
	GoodsClassNameListPageDTO::Wrapper listName(const GoodClassQuery::Wrapper& query);
	// 分页查询所有数据
	GoodsClassPageDTO::Wrapper listAll(const GoodClassQuery::Wrapper& query);

	// Batch delete by ids, returns affected rows
	int removeByIds(const std::vector<std::string>& ids);

	// List all rows for excel export
	std::list<GoodsClassDO> listForExport();

	// Import rows ([code, name]) and return inserted count
	int importRows(const std::vector<std::vector<std::string>>& rows,
		const std::string& createBy, const std::string& orgCode, const std::string& companyCode);

};

#endif // !_GOODSCLASS_SERVICE_

