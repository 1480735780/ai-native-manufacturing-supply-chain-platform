/*
 Copyright Zero One Star. All rights reserved.

 @Author: awei
 @Date: 2022/10/25 11:13:11

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
#include "WorkStateService.h"
#include "../../dao/workstate/WorkStateDAO.h"


bool WorkStateService::removeData(string id)
{
	WorkStateDAO dao;
	return dao.deleteById(id) == 1;
}

bool WorkStateService::uploadData(const std::vector<std::vector<std::string>>& data, const PayloadDTO& payload)
{
	// ��������Ƿ�Ϊ��
	if (data.empty()) {
		OATPP_LOGE("GoodsService", "No data found in Excel file");
		return false;
	}

	// ���� Excel ����
	// fix: track success/failed rows and always return a value (old code had no return)
	size_t okCount = 0;
	size_t failCount = 0;
	for (size_t i = 1; i < data.size(); i++) { // skip header row
		const auto& row = data[i];
		// skip empty or short rows
		if (row.size() < 2 || row[0].empty() || row[1].empty()) {
			failCount++;
			continue;
		}
		// �� Excel ����ת��Ϊ DO ����
		WorkStateDO doo;
		
		try {
			UuidFacade uuid(1);
			doo.setId(uuid.genUuid());
			doo.setCreate_name(payload.getUsername());
			doo.setCreate_by(payload.getId());
			doo.setSys_org_code(payload.getOrgcode());
			doo.setSys_company_code(payload.getCompanycode());
			doo.setWork_sta_code(row[0]);
			doo.setWork_sta_name(row[1]);
			
		}
		catch (const std::exception& e) {
			OATPP_LOGE("WorkStateService", "Failed to parse data in row %zu: %s", i, e.what());
			failCount++;
			continue;
		}
		// ���� DAO ���������
		// call DAO to insert data
		WorkStateDAO dao;
		if (dao.insert(doo) > 0) {
			okCount++;
		}
		else {
			failCount++;
		}
	}

	OATPP_LOGI("WorkStateService", "import finished, success=%zu failed=%zu", okCount, failCount);
	return okCount > 0;
}

std::vector<std::vector<std::string>> WorkStateService::getVectorData()
{
	WorkStateDAO dao;
	auto res = dao.selectWork();
	std::vector<std::vector<string>> vec;
	for (auto& i : res) {
		vec.emplace_back(std::vector<std::string>{i.getWork_sta_code(),i.getWork_sta_name()});
	}
	return vec;
}

