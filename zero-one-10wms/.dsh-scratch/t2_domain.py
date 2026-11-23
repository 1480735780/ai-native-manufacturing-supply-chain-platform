# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect
R = "wms-cpp/wms-c8-wconfig/"

LICENSE = '''/*
 Copyright Zero One Star. All rights reserved.

 @Author: zero-one-star
 @Date: 2025/03/10 16:09:12

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

\t  https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*/
'''

files = {}

files["domain/do/operation-type/OperationTypeDO.h"] = LICENSE + '''#ifndef _OPERATION_TYPE_DO_
#define _OPERATION_TYPE_DO_
#include "../DoInclude.h"

/**
 * 操作类型数据实体类
 */
class OperationTypeDO
{
\t// 唯一标识
\tCC_SYNTHESIZE(string, id, Id);
\t// 操作类型代码
\tCC_SYNTHESIZE(string, code, Code);
\t// 操作类型名称
\tCC_SYNTHESIZE(string, name, Name);

public:
\tOperationTypeDO() {
\t\tid = "";
\t\tcode = "";
\t\tname = "";
\t}
};

// 操作类型DO对象的指针类型设定
typedef std::shared_ptr<OperationTypeDO> PtrOperationTypeDO;

#endif // !_OPERATION_TYPE_DO_
'''

files["domain/dto/operation-type/OperationTypeDTO.h"] = LICENSE + '''#ifndef _OPERATION_TYPE_DTO_
#define _OPERATION_TYPE_DTO_

#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 操作类型新增数据对象（不提供唯一标识，由后端生成）
 */
class OperationTypeAddDTO : public oatpp::DTO
{
\tDTO_INIT(OperationTypeAddDTO, oatpp::DTO);
\t// 操作类型代码
\tAPI_DTO_FIELD_DEFAULT(String, code, ZH_WORDS_GETTER("op.field.code"));
\t// 操作类型名称
\tAPI_DTO_FIELD_DEFAULT(String, name, ZH_WORDS_GETTER("op.field.name"));
};

/**
 * 操作类型数据对象（修改时需要唯一标识）
 */
class OperationTypeDTO : public OperationTypeAddDTO
{
\tDTO_INIT(OperationTypeDTO, OperationTypeAddDTO);
\t// 唯一标识
\tAPI_DTO_FIELD_DEFAULT(String, id, ZH_WORDS_GETTER("op.field.id"));
};

/**
 * 操作类型分页数据对象
 */
class OperationTypePageDTO : public PageDTO<OperationTypeDTO::Wrapper>
{
\tDTO_INIT(OperationTypePageDTO, PageDTO<OperationTypeDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_OPERATION_TYPE_DTO_
'''

files["domain/dto/operation-type/OperationTypeBatchDeleteDto.h"] = LICENSE + '''#ifndef _OPERATION_TYPE_BATCH_DELETE_DTO_
#define _OPERATION_TYPE_BATCH_DELETE_DTO_

#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 操作类型批量删除请求 dto
 */
class OperationTypeBatchDeleteDto : public oatpp::DTO {
\tDTO_INIT(OperationTypeBatchDeleteDto, DTO);
\t// 唯一标识列表
\tAPI_DTO_FIELD_DEFAULT(List<oatpp::String>, ids, ZH_WORDS_GETTER("op.field.ids"));
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_OPERATION_TYPE_BATCH_DELETE_DTO_
'''

files["domain/query/operation-type/OperationTypeQuery.h"] = LICENSE + '''#ifndef _OPERATION_TYPE_QUERY_
#define _OPERATION_TYPE_QUERY_

#include "../../GlobalInclude.h"
#include "domain/query/PageQuery.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 操作类型分页查询对象
 */
class OperationTypeQuery : public PageQuery
{
\tDTO_INIT(OperationTypeQuery, PageQuery);
\t// 操作类型代码
\tDTO_FIELD(String, code);
\tDTO_FIELD_INFO(code) {
\t\tinfo->description = ZH_WORDS_GETTER("op.field.code");
\t}
\t// 操作类型名称
\tDTO_FIELD(String, name);
\tDTO_FIELD_INFO(name) {
\t\tinfo->description = ZH_WORDS_GETTER("op.field.name");
\t}
};

#include OATPP_CODEGEN_END(DTO)
#endif // !_OPERATION_TYPE_QUERY_
'''

files["domain/vo/operation-type/OperationTypeVO.h"] = LICENSE + '''#ifndef _OPERATION_TYPE_VO_
#define _OPERATION_TYPE_VO_

#include "../../GlobalInclude.h"
#include "../../dto/operation-type/OperationTypeDTO.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 操作类型JsonVO，用于响应给客户端的Json对象
 */
class OperationTypeJsonVO : public JsonVO<OperationTypeDTO::Wrapper> {
\tDTO_INIT(OperationTypeJsonVO, JsonVO<OperationTypeDTO::Wrapper>);
};

/**
 * 操作类型分页列表JsonVO，用于响应给客户端的Json对象
 */
class OperationTypePageJsonVO : public JsonVO<OperationTypePageDTO::Wrapper> {
\tDTO_INIT(OperationTypePageJsonVO, JsonVO<OperationTypePageDTO::Wrapper>);
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_OPERATION_TYPE_VO_
'''

for path, content in files.items():
    full = R + path
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'wb').write(content.encode('utf-8'))
    print("新建", path)
