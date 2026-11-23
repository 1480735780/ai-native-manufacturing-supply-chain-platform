#include "stdafx.h"
#include "CdmDAO.h"
#include "../lib-common/include/id/SnowFlake.h"
#include "id/UuidFacade.h"
#include"CdmMapper.h"



 int  CdmDAO::update(const CdmDO& uObj)
 {
	 // 修改企业等级：只更新业务字段与更新审计字段。
	 // 注意：CdmDO 的字段语义由 CDMDTO 决定 —— cname=等级名称、cdn=等级编码、cdd=停用标记。
	 // 这里使用 COALESCE(NULLIF(?, ''), 原值) 保证前端未传的字段不会被空串覆盖。
	 string sql = "UPDATE `ba_com_deg` SET `com_deg_name`=COALESCE(NULLIF(?,''),`com_deg_name`), `com_deg_code`=COALESCE(NULLIF(?,''),`com_deg_code`), `com_deg_del`=COALESCE(NULLIF(?,''),`com_deg_del`), `update_name`=COALESCE(NULLIF(?,''),`update_name`), `update_by`=COALESCE(NULLIF(?,''),`update_by`), `update_date`=COALESCE(NULLIF(?,''),`update_date`) WHERE `id`=?";
	 return sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s", uObj.getCname(), uObj.getCdn(), uObj.getCdd(), uObj.getUname(), uObj.getUby(), uObj.getUdate(), uObj.getId());
 }

 int CdmDAO::deleteById(vector<string>& ids)
 {
	 string sql = "DELETE FROM `ba_com_deg` WHERE `id`=?";

	 for (auto id : ids)
	 {
		 int res = sqlSession->executeUpdate(sql, "%s", id);

		 if (res != 1) {
			 return res; 
		 }
	 }
	 return 1;
 }

 std::list<CdmDO> CdmDAO::getAllattri() {
	 string sql = "SELECT `id`,`create_name`,`create_by`,`create_date`,`sys_org_code`,`sys_company_code`,`com_type_code`,`com_type_name` from `ba_com_type`";
	 CdmMapper mapper;
	 return sqlSession->executeQuery<CdmDO>(sql, mapper);
 }
