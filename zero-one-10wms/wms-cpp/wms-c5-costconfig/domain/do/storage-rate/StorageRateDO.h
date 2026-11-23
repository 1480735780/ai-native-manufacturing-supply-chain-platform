/*
 Copyright Zero One Star. All rights reserved.

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

#ifndef _STORAGERATE_DO_
#define _STORAGERATE_DO_
#include "../DoInclude.h"

/**
 * Entity of table wm_cost_conf
 */
class StorageRateDO
{
	// primary key
	CC_SYNTHESIZE(string, id, Id);
	CC_SYNTHESIZE(string, cost_code, CostCode);
	CC_SYNTHESIZE(string, cost_yj, CostYj);
	CC_SYNTHESIZE(string, cost_zk, CostZk);
	CC_SYNTHESIZE(string, cost_sl, CostSl);
	CC_SYNTHESIZE(string, cost_bhs, CostBhs);
	CC_SYNTHESIZE(string, cost_hsj, CostHsj);
	CC_SYNTHESIZE(string, create_name, CreateName);
	CC_SYNTHESIZE(string, create_by, CreateBy);
	CC_SYNTHESIZE(string, create_date, CreateDate);
	CC_SYNTHESIZE(string, update_name, UpdateName);
	CC_SYNTHESIZE(string, update_by, UpdateBy);
	CC_SYNTHESIZE(string, update_date, UpdateDate);
	CC_SYNTHESIZE(string, sys_org_code, SysOrgCode);
	CC_SYNTHESIZE(string, sys_company_code, SysCompanyCode);
};
typedef std::shared_ptr<StorageRateDO> PtrStorageRateDO;
#endif // !_STORAGERATE_DO_
