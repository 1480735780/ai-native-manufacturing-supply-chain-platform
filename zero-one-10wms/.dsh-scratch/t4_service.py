# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

R = "wms-cpp/wms-c8-wconfig/"

# ================= Service.h =================
p = R + "service/recv-g-way/Recv-G-WayService.h"
enc = detect(open(p, 'rb').read())
new_h = '''#pragma once
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
\t// 分页查询接货方式
\tRecv_G_WayAllDto::Wrapper listAll(const Recv_G_WayQuery::Wrapper& query);

\t// 新增接货方式
\tint saveData(const Recv_G_WayAddDto::Wrapper& dto,string name, string realname, string orgcode, string companycode);
\t// 修改接货方式
\tbool updateData(const Recv_G_WayEditDto::Wrapper& dto);
\t// 通过ID删除接货方式
\tbool removeData(const string id);
\t// 批量删除接货方式
\tbool batchDeleteRecv_G_Way(const Recv_G_WayBatchDeleteDto::Wrapper& dto);
\t// 导入接货方式（解析上传的Excel文件内容）
\tint importRecv_G_Way(const char* data, size_t size, string name, string realname, string orgcode, string companycode);
\t// 导出接货方式（返回Excel文件二进制内容）
\tstd::vector<unsigned char> exportRecv_G_Way();
\t//默认值处理
\tstd::string DefPutData(const PayloadDTO& payload);
};

#endif // !_RECV_G_WAY_SERVICE_
'''
open(p, 'wb').write(new_h.encode(enc))
print("Recv-G-WayService.h ->", enc)

# ================= Service.cpp =================
p = R + "service/recv-g-way/Recv-G-WayService.cpp"
enc = detect(open(p, 'rb').read())
new_cpp = '''/*
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
#include "stdafx.h"
#include "Recv-G-WayService.h"
#include "../../dao/recv-g-way/Recv-G-WayFileDao.h"
#include "ExcelComponent.h"

Recv_G_WayAllDto::Wrapper Recv_G_WayService::listAll(const Recv_G_WayQuery::Wrapper& query)
{
\t// 定义分页对象
\tauto pages = Recv_G_WayAllDto::createShared();
\tpages->pageIndex = query->pageIndex;
\tpages->pageSize = query->pageSize;

\t// 查询数据总数
\tRecv_G_WayDAO dao;
\tuint64_t count = dao.count(query);
\tif (count <= 0)
\t{
\t\treturn pages;
\t}

\t// 分页查询数据
\tpages->total = count;
\tpages->calcPages();
\tlist<Recv_G_WayDO> result = dao.selectWithPage(query);
\t// 将DO转换成DTO
\tfor (Recv_G_WayDO sub : result)
\t{
\t\tauto dto = Recv_G_WayEditDto::createShared();
\t\tZO_STAR_DOMAIN_DO_TO_DTO(dto, sub, del_mode_code, Del_mode_code, del_mode_name, Del_mode_name,id,Id);
\t\tpages->addData(dto);
\t}
\treturn pages;
}

int Recv_G_WayService::saveData(const Recv_G_WayAddDto::Wrapper& dto, string name, string realname, string orgcode, string companycode)
{
\t// 组装DO数据
\tRecv_G_WayDO data;
\tZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Del_mode_code, del_mode_code, Del_mode_name, del_mode_name);
\t// 执行数据插入
\tRecv_G_WayDAO dao;
\treturn dao.insert(data, name, realname, orgcode, companycode);
}

bool Recv_G_WayService::updateData(const Recv_G_WayEditDto::Wrapper& dto)
{
\t// 组装DO数据

\tRecv_G_WayDO data;
\tZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Del_mode_code, del_mode_code, Del_mode_name, del_mode_name,Id,id);
\t// 执行数据修改
\tRecv_G_WayDAO dao;
\treturn dao.update(data);
}

bool Recv_G_WayService::removeData(const string id)
{
\tRecv_G_WayDAO dao;
\treturn dao.deleteById(id);
}

bool Recv_G_WayService::batchDeleteRecv_G_Way(const Recv_G_WayBatchDeleteDto::Wrapper& dto)
{
\tif (!dto->ids || dto->ids->empty())
\t{
\t\treturn false;
\t}
\tRecv_G_WayDAO dao;
\treturn dao.batchDelete(dto) > 0;
}

int Recv_G_WayService::importRecv_G_Way(const char* data, size_t size, string name, string realname, string orgcode, string companycode)
{
\tif (data == nullptr || size == 0)
\t{
\t\treturn -1;
\t}
\t// 页签名称（xlnx只能存储utf8，读取中文内容时需要转换）
\tstd::string sheetName = ZH_WORDS_GETTER("recv-g-way-file.excel.name");
\t// 读取文件内容
\tauto readData = ExcelComponent::readIntoVector(data, size, sheetName);
\tif (readData.empty())
\t{
\t\treturn -1;
\t}

\tlist<Recv_G_WayDO> datas;
\tint i = 1;
\tint result = -1;
\tfor (auto row : readData)
\t{
\t\t// 第一行为表头，需要校验
\t\tif (i == 1)
\t\t{
\t\t\tif (row.size() != 2 || row[0] != ZH_WORDS_GETTER("recv-g-way-file.excel.col.first") || row[1] != ZH_WORDS_GETTER("recv-g-way-file.excel.col.second"))
\t\t\t{
\t\t\t\treturn -1;
\t\t\t}
\t\t\tresult = 0;
\t\t\t++i;
\t\t\tcontinue;
\t\t}
\t\t// 跳过空行
\t\tif (row.size() < 2 || row[0].empty() && row[1].empty())
\t\t{
\t\t\tcontinue;
\t\t}
\t\tRecv_G_WayDO temp;
\t\ttemp.setDel_mode_code(row[0]);
\t\ttemp.setDel_mode_name(row[1]);
\t\tdatas.push_back(temp);
\t}

\tif (datas.empty())
\t{
\t\treturn result == 0 ? 0 : -1;
\t}

\tRecv_G_WayDAO dao;
\tdao.insert(datas, name, realname, orgcode, companycode);
\treturn result;
}

std::vector<unsigned char> Recv_G_WayService::exportRecv_G_Way()
{
\tRecv_G_WayDAO dao;
\tlist<Recv_G_WayDO> result = dao.selectAll();

\tstd::vector<std::vector<std::string>> data;
\t// 写入表头
\tstd::vector<std::string> first;
\tfirst.push_back(ZH_WORDS_GETTER("recv-g-way-file.excel.col.first"));
\tfirst.push_back(ZH_WORDS_GETTER("recv-g-way-file.excel.col.second"));
\tdata.push_back(first);

\tfor (auto it = result.begin(); it != result.end(); ++it)
\t{
\t\tstd::vector<std::string> row;
\t\trow.push_back(it->getDel_mode_code());
\t\trow.push_back(it->getDel_mode_name());
\t\tdata.push_back(row);
\t}

\t// 页签名称（xlnx只能存储utf8，读取中文内容时需要转换）
\tstd::string sheetName = ZH_WORDS_GETTER("recv-g-way-file.excel.name");
\t// 将数据以excel格式写入buff中
\tExcelComponent excel;
\treturn excel.writeVectorToBuff(sheetName, data);
}
'''
open(p, 'wb').write(new_cpp.encode(enc))
print("Recv-G-WayService.cpp ->", enc)
