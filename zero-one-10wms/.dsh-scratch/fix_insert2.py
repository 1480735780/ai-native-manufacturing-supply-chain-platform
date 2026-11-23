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

# DAO：create_date 改为由应用层写入（与 OrderType 一致）
patch(
    "wms-cpp/wms-c7-reposity/dao/library/LibraryDAO.cpp",
    '''string sql = "INSERT INTO `ba_bin_type` (`id`, `create_name`, `create_by`, `create_date`, `sys_org_code`, `sys_company_code`, `bin_type_code`, `bin_type_name`) VALUES (?,?,?,NOW(),?,?,?,?)";
\treturn sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s", iObj.getId(), iObj.getCreateName(), iObj.getCreateBy(),
\t\tiObj.getSysOrgCode(), iObj.getSysCompanyCode(), iObj.getCode(), iObj.getName());''',
    '''string sql = "INSERT INTO `ba_bin_type` (`id`, `create_name`, `create_by`, `create_date`, `sys_org_code`, `sys_company_code`, `bin_type_code`, `bin_type_name`) VALUES (?,?,?,?,?,?,?,?)";
\treturn sqlSession->executeUpdate(sql, "%s%s%s%s%s%s%s%s", iObj.getId(), iObj.getCreateName(), iObj.getCreateBy(),
\t\tiObj.getCreateDate(), iObj.getSysOrgCode(), iObj.getSysCompanyCode(), iObj.getCode(), iObj.getName());'''
)

# Service：DTO→DO 映射补上 create_date
patch(
    "wms-cpp/wms-c7-reposity/service/library/LibraryService.cpp",
    '''\tZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Id, id,
\t\tCreateName, create_name, CreateBy, create_by, CreateDate, create_date,
\t\tUpdateName, update_name, UpdateBy, update_by, UpdateDate, update_date,
\t\tSysOrgCode, sys_org_code, SysCompanyCode, sys_company_code,
\t\tCode, bin_type_code, Name, bin_type_name);''',
    '''\tZO_STAR_DOMAIN_DTO_TO_DO(data, dto, Id, id,
\t\tCreateName, create_name, CreateBy, create_by, CreateDate, create_date,
\t\tSysOrgCode, sys_org_code, SysCompanyCode, sys_company_code,
\t\tCode, bin_type_code, Name, bin_type_name);'''
)
