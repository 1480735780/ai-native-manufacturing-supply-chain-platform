/*
 Copyright Zero One Star. All rights reserved.

 @Author: zero-one-star
 @Date: 2025/03/10 16:09:12

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
#ifndef _OPERATION_TYPE_SERVICE_
#define _OPERATION_TYPE_SERVICE_
#include <list>
#include <vector>
#include "domain/vo/operation-type/OperationTypeVO.h"
#include "domain/query/operation-type/OperationTypeQuery.h"
#include "domain/dto/operation-type/OperationTypeDTO.h"
#include "domain/dto/operation-type/OperationTypeBatchDeleteDto.h"

/**
 * 操作类型服务实现
 */
class OperationTypeService
{
public:
	// 分页查询操作类型
	OperationTypePageDTO::Wrapper listAll(const OperationTypeQuery::Wrapper& query);
	// 新增操作类型
	int saveData(const OperationTypeAddDTO::Wrapper& dto, string name, string realname, string orgcode, string companycode);
	// 修改操作类型
	bool updateData(const OperationTypeDTO::Wrapper& dto);
	// 通过ID删除操作类型
	bool removeData(const string id);
	// 批量删除操作类型
	bool batchDeleteOperationType(const OperationTypeBatchDeleteDto::Wrapper& dto);
	// 导入操作类型（解析上传的Excel文件内容）
	int importOperationType(const char* data, size_t size, string name, string realname, string orgcode, string companycode);
	// 导出操作类型（返回Excel文件二进制内容）
	std::vector<unsigned char> exportOperationType();
};

#endif // !_OPERATION_TYPE_SERVICE_
