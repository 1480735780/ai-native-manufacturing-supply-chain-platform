#pragma once
#ifndef _ENTERPRISESTATUSDO_
#define _ENTERPRISESTATUSDO_
#include "../DoInclude.h"

class EnterpriseStatusDO
{
	// 唯一标识（ba_com_sta.id，前端修改/删除依赖它）
	CC_SYNTHESIZE(string, id, Id);
	// 编号（对应 com_sta_code）
	CC_SYNTHESIZE(string, enterpriseid, kehuzhuangtai_code);
	// 企业名（对应 com_sta_name）
	CC_SYNTHESIZE(string, enterprisename, kehuzhuangtai_name);
	// 状态（对应 com_sta_del）
	CC_SYNTHESIZE(string, status, cus_sta_del);
public:
	EnterpriseStatusDO() {
		id = "";
		enterpriseid = "C001";
		enterprisename = "客户1";
		status = "Y";
	}
};

class EnterpriseStatusListDO
{
	// 唯一编码
	CC_SYNTHESIZE(string, statusonlyid, id);
	// 编号
	CC_SYNTHESIZE(string, enterpriseid, kehuzhuangtai_code);
	// 企业名
	CC_SYNTHESIZE(string, enterprisename, kehuzhuangtai_name);
public:
	EnterpriseStatusListDO() {
		statusonlyid = " ";
		enterpriseid = "C001";
		enterprisename = "客户1";
	}
};

// 给DO智能指针设定一个别名方便使用
typedef std::shared_ptr<EnterpriseStatusDO> PtrEnterpriseStatusDO;
typedef std::shared_ptr<EnterpriseStatusListDO> PtrEnterpriseStatusListDO;
#endif // !_ENTERPRISESTATUSDO_
