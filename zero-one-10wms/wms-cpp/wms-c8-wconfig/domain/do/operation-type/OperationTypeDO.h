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
#ifndef _OPERATION_TYPE_DO_
#define _OPERATION_TYPE_DO_
#include "../DoInclude.h"

/**
 * 操作类型数据实体类
 */
class OperationTypeDO
{
	// 唯一标识
	CC_SYNTHESIZE(string, id, Id);
	// 操作类型代码
	CC_SYNTHESIZE(string, code, Code);
	// 操作类型名称
	CC_SYNTHESIZE(string, name, Name);

public:
	OperationTypeDO() {
		id = "";
		code = "";
		name = "";
	}
};

// 操作类型DO对象的指针类型设定
typedef std::shared_ptr<OperationTypeDO> PtrOperationTypeDO;

#endif // !_OPERATION_TYPE_DO_
