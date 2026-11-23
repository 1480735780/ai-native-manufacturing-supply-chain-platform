#pragma once
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
#ifndef _RECV_G_WAY_SERVICE_
#define _RECV_G_WAY_SERVICE_
#include <list>
#include <vector>
#include "domain/vo/recv-g-way/Recv-G-Way-FileVo.h"
#include "domain/query/recv-g-way/Recv-G-Way-FileQuery.h"
#include "domain/dto/recv-g-way/Recv-G-WayFileDto.h"
#include "domain/dto/recv-g-way/Recv-G-WayBatchDeleteDto.h"

/**
 * 接货方式服务实现
 */
class Recv_G_WayService
{
public:
	// 分页查询接货方式
	Recv_G_WayAllDto::Wrapper listAll(const Recv_G_WayQuery::Wrapper& query);

	// 新增接货方式
	int saveData(const Recv_G_WayAddDto::Wrapper& dto,string name, string realname, string orgcode, string companycode);
	// 修改接货方式
	bool updateData(const Recv_G_WayEditDto::Wrapper& dto);
	// 通过ID删除接货方式
	bool removeData(const string id);
	// 批量删除接货方式
	bool batchDeleteRecv_G_Way(const Recv_G_WayBatchDeleteDto::Wrapper& dto);
	// 导入接货方式（解析上传的Excel文件内容）
	int importRecv_G_Way(const char* data, size_t size, string name, string realname, string orgcode, string companycode);
	// 导出接货方式（返回Excel文件二进制内容）
	std::vector<unsigned char> exportRecv_G_Way();
};

#endif // !_RECV_G_WAY_SERVICE_
