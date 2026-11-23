# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

def patch(path, old, new):
    enc = detect(open(path, 'rb').read())
    txt = open(path, 'rb').read().decode(enc)
    assert old in txt, "未找到待替换片段: " + path
    txt = txt.replace(old, new, 1)
    open(path, 'wb').write(txt.encode(enc))
    print("OK", path, "[", enc, "]")

# ---- 修正 T1 引入的 BusinessLinkDAO::insert（UUID主键不能用 executeInsert 取 LAST_INSERT_ID）----
patch(
    "wms-cpp/wms-c7-reposity/dao/business-link/BusinessLinkDAO.cpp",
    'return sqlSession->executeInsert(sql, "%s%s%s%s%s%s%s", iObj.getId(), iObj.getCreateName(), iObj.getCreateBy(), iObj.getSysOrgCode(), iObj.getSysCompanyCode(), iObj.getOperStepCode(), iObj.getOperStepName());',
    'return sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s", iObj.getId(), iObj.getCreateName(), iObj.getCreateBy(), iObj.getSysOrgCode(), iObj.getSysCompanyCode(), iObj.getOperStepCode(), iObj.getOperStepName());'
)

# ---- 修正 LibraryDAO::insert ----
patch(
    "wms-cpp/wms-c7-reposity/dao/library/LibraryDAO.cpp",
    '''string sql = "INSERT INTO `ba_bin_type` (`id`, `create_name`, `create_by`, `create_date`, `update_name`, `update_by`, `update_date`, `sys_org_code`, `sys_company_code`, `bin_type_code`, `bin_type_name`) VALUES (?,?,?,NOW(),?,?,NOW(),?,?,?,?)";
\treturn sqlSession->executeInsert(sql, "%s%s%s%s%s%s%s%s", iObj.getId(), iObj.getCreateName(), iObj.getCreateBy(),
\t\tiObj.getUpdateName(), iObj.getUpdateBy(), iObj.getSysOrgCode(), iObj.getSysCompanyCode(),
\t\tiObj.getCode(), iObj.getName());''',
    '''string sql = "INSERT INTO `ba_bin_type` (`id`, `create_name`, `create_by`, `create_date`, `sys_org_code`, `sys_company_code`, `bin_type_code`, `bin_type_name`) VALUES (?,?,?,NOW(),?,?,?,?)";
\treturn sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s", iObj.getId(), iObj.getCreateName(), iObj.getCreateBy(),
\t\tiObj.getSysOrgCode(), iObj.getSysCompanyCode(), iObj.getCode(), iObj.getName());'''
)
