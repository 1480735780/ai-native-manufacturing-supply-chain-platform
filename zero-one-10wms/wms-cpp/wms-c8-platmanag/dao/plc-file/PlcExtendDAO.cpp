/*
 Copyright Zero One Star. All rights reserved.

 @Author: dev-yuetaiguanli
 @Date: 2026/11/22

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
// 本文件为PLC指令模块补充实现：批量删除、导出查询、执行标记、批量导入
#include "stdafx.h"
#include "PlcDAO.h"
#include "PlcMapper.h"
#include "../../lib-common/include/id/UuidFacade.h"
#include <algorithm>

// 导出专用字段映射（全字段显式列序）
class PlcExportMapper : public Mapper<PlcDO>
{
public:
	PlcDO mapper(ResultSet* resultSet) const override
	{
		PlcDO data;
		data.setid(resultSet->getString(1));
		data.setplc_ip(resultSet->getString(2));
		data.setplc_port(resultSet->getString(3));
		data.setplc_type(resultSet->getString(4));
		data.setcom_remark(resultSet->getString(5));
		data.setcom_time(resultSet->getString(6));
		data.setcom_seq(resultSet->getString(7));
		data.setcom_cons(resultSet->getString(8));
		data.setremark1(resultSet->getString(9));
		data.setcom_no(resultSet->getString(10));
		data.setquery01(resultSet->getString(11));
		data.setquery02(resultSet->getString(12));
		data.setsetp_time(resultSet->getString(13));
		data.setsetp_num(resultSet->getString(14));
		return data;
	}
};

// 批量删除
uint64_t PlcDAO::deleteBatch(const std::list<string>& ids)
{
	if (ids.empty()) return 0;
	string sql = "DELETE FROM `wms_plc` WHERE `id` IN (";
	SqlParams params;
	int i = 0;
	for (const auto& id : ids) {
		if (i > 0) sql += ",";
		sql += "?";
		SQLPARAMS_PUSH(params, "s", std::string, id);
		i++;
	}
	sql += ")";
	return sqlSession->executeUpdate(sql, params);
}

// 按条件查询全部（导出用，显式列序）
std::list<PlcDO> PlcDAO::selectAllForExport(const PlcFileQuery::Wrapper& query)
{
	SqlParams params;
	string sql = "SELECT `id`,`plc_ip`,`plc_port`,`plc_type`,`com_remark`,`com_time`,`com_seq`,`com_cons`,`remark1`,`com_no`,`query01`,`query02`,`setp_time`,`setp_num` FROM `wms_plc` ";
	sql += queryConditionBuilder(query, params);
	sql += " ORDER BY `com_seq` ASC, `id` ASC";
	PlcExportMapper mapper;
	return sqlSession->executeQuery<PlcDO>(sql, mapper, params);
}

// 执行标记：更新执行时间与执行结果
int PlcDAO::markExecuted(const string& id, const string& execResult)
{
	string sql = "UPDATE `wms_plc` SET `com_time`=?, `remark1`=? WHERE `id`=?";
	return sqlSession->executeUpdate(sql, "%s%s%s", getCurrentDateTime(), execResult, id);
}

// 批量导入
bool PlcDAO::importAllData(const std::vector<std::vector<std::string>>& xdata, const string& create_name, const string& create_by, const string& orgcode, const string& companycode)
{
	// 列序：plc_ip,plc_port,plc_type,com_remark,com_time,com_seq,com_cons,remark1,com_no,query01,query02,setp_time,setp_num
	string sql = "INSERT INTO `wms_plc` (`id`, `create_name`, `create_by`, `create_date`, `sys_org_code`, `sys_company_code`, "
		"`plc_ip`, `plc_port`, `plc_type`, `com_remark`, `com_time`, `com_seq`, `com_cons`, `remark1`, `com_no`, `query01`, `query02`, `setp_time`, `setp_num`) "
		"VALUES (?, ?, ?, NOW(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
	try {
		auto conn = sqlSession->getConnection();
		if (conn == nullptr)return false;
		for (size_t i = 1; i < xdata.size(); i++) {
			const auto& row = xdata[i];
			if (row.size() < 13) continue; // 列不足跳过
			UuidFacade uuidObj;
			string uid = uuidObj.genUuid();
			uid.erase(std::remove(uid.begin(), uid.end(), '-'), uid.end());
			std::unique_ptr<sql::PreparedStatement> pstmt(conn->prepareStatement(sql));
			pstmt->setString(1, uid);
			pstmt->setString(2, create_name);
			pstmt->setString(3, create_by);
			pstmt->setString(4, orgcode);
			pstmt->setString(5, companycode);
			for (size_t col = 0; col < 13; col++) {
				pstmt->setString(6 + col, row[col]);
			}
			pstmt->executeUpdate();
		}
	}
	catch (sql::SQLException& ex) {
		cerr << ex.what() << endl;
		return false;
	}
	return true;
}

// 通过ID查询指令集（执行用，显式列序）
PtrPlcDO PlcDAO::selectConsById(string id)
{
	string sql = "SELECT `id`,`plc_ip`,`plc_port`,`plc_type`,`com_remark`,`com_time`,`com_seq`,`com_cons`,`remark1`,`com_no`,`query01`,`query02`,`setp_time`,`setp_num` FROM `wms_plc` WHERE `id`=?";
	// 复用 PtrPlcMapper （其列序与上述 SELECT 一致：1..14）
	PtrPlcMapper mapper;
	return sqlSession->executeQueryOne<PtrPlcDO>(sql, mapper, "%s", id);
}
