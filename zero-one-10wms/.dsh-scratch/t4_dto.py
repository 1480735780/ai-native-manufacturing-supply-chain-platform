# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

p = "wms-cpp/wms-c8-wconfig/domain/dto/recv-g-way/Recv-G-WayBatchDeleteDto.h"
new = '''#pragma once
/*
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
#ifndef _RECV_G_WAY_BATCH_DELETE_DTO_
#define _RECV_G_WAY_BATCH_DELETE_DTO_

#include "../../GlobalInclude.h"

#include OATPP_CODEGEN_BEGIN(DTO)

/**
 * 接货方式批量删除请求 dto
 */
class Recv_G_WayBatchDeleteDto : public oatpp::DTO {
\tDTO_INIT(Recv_G_WayBatchDeleteDto, DTO);
\t// 唯一标识列表
\tAPI_DTO_FIELD_DEFAULT(List<oatpp::String>, ids, ZH_WORDS_GETTER("recv-g-way.field.ids"));
};

#include OATPP_CODEGEN_END(DTO)

#endif // !_RECV_G_WAY_BATCH_DELETE_DTO_
'''
open(p, 'wb').write(new.encode('gb18030'))
print("新建", p, "[gb18030]")
