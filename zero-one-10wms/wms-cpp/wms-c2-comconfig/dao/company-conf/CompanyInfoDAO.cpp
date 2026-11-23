/*
 Copyright Zero One Star. All rights reserved.

 @Author: blue
 @Date: 2025/03/13 14:26:52

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
#include "stdafx.h"
#include "CompanyInfoDAO.h"
#include "CompanyInfoMapper.h"
#include <sstream>

std::string CompanyInfoDAO::queryComdegBuilder(const CompanyInfoQuery::Wrapper& query, SqlParams& params) {
	stringstream sqlCondition;
	sqlCondition << " WHERE 1=1";
	if (query->code && !query->code->empty()) {

		sqlCondition << " AND com_code=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->code.getValue(""));
	}
	if (query->ChineseSampleName && !query->ChineseSampleName->empty()) {

		sqlCondition << " AND com_zh_name=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->ChineseSampleName.getValue(""));
	}
	if (query->ChineseFullName && !query->ChineseFullName->empty()) {

		sqlCondition << " AND com_zh_aname=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->ChineseFullName.getValue(""));
	}
	if (query->ChineseAddr && !query->ChineseAddr->empty()) {

		sqlCondition << " AND com_zh_addr=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->ChineseAddr.getValue(""));
	}
	if (query->EnglishSampleName && !query->EnglishSampleName->empty()) {

		sqlCondition << " AND com_en_name=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->EnglishSampleName.getValue(""));
	}
	if (query->EnglishFullName && !query->EnglishFullName->empty()) {

		sqlCondition << " AND com_en_aname=?";
		SQLPARAMS_PUSH(params, "s", std::string, query->EnglishFullName.getValue(""));

	}
	return sqlCondition.str();
}

uint64_t CompanyInfoDAO::count(const CompanyInfoQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT COUNT(*) FROM ba_comp ";
	// 构建查询条件
	sql += queryComdegBuilder(query, params);
	// 执行查询
	return sqlSession->executeQueryNumerical(sql, params);
}

std::list<CompanyInfoDO> CompanyInfoDAO::selectWithPage(const CompanyInfoQuery::Wrapper& query) {
	SqlParams params;
	string sql = "SELECT com_code,com_zh_name,com_zh_aname,com_zh_addr,com_en_name,com_en_aname,id FROM ba_comp ";
	// 构建查询条件
	sql += queryComdegBuilder(query, params);
	// 构建分页条件
	sql += " LIMIT " + std::to_string(((query->pageIndex - 1) * query->pageSize)) + "," + std::to_string(query->pageSize);

	//执行查询
	CompanyInfoMapper mapper;
	return sqlSession->executeQuery<CompanyInfoDO>(sql, mapper, params);

}


PtrCompanyInfoDO CompanyInfoDAO::selectDetail(const std::string& id)
{
	// 列顺序需与 CompanyInfoMapper 保持一致（第 7 列为 id）
	string sql = "SELECT com_code,com_zh_name,com_zh_aname,com_zh_addr,com_en_name,com_en_aname,id FROM ba_comp WHERE `id`=?";
	PtrCompanyInfoMapper mapper;
	// ba_comp.id 是 varchar(36) 字符串主键，按字符串绑定参数
	return sqlSession->executeQueryOne<PtrCompanyInfoDO>(sql, mapper, "%s", id);
}
