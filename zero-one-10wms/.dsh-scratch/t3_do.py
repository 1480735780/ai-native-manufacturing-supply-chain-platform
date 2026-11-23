# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

p = "wms-cpp/wms-c7-reposity/domain/do/library/LibraryDO.h"
raw = open(p, 'rb').read()
enc = detect(raw)
print("原编码:", enc)

new = '''#pragma once
/*
 @Author: nanbowan
*/
#include "../DoInclude.h"

/**
 * 库位类型数据实体类
 */
class LibraryDO
{
\tusing datetime = string;
\t// 唯一id
\tCC_SYNTHESIZE(string, id, Id);
\t// 创建人名称
\tCC_SYNTHESIZE(string, create_name, CreateName);
\t// 创建人登录名称
\tCC_SYNTHESIZE(string, create_by, CreateBy);
\t// 创建日期
\tCC_SYNTHESIZE(datetime, create_date, CreateDate);
\t// 更新人名称
\tCC_SYNTHESIZE(string, update_name, UpdateName);
\t// 更新人登录名称
\tCC_SYNTHESIZE(string, update_by, UpdateBy);
\t// 更新日期
\tCC_SYNTHESIZE(datetime, update_date, UpdateDate);
\t// 所属部门
\tCC_SYNTHESIZE(string, sys_org_code, SysOrgCode);
\t// 所属公司
\tCC_SYNTHESIZE(string, sys_company_code, SysCompanyCode);
\t// 库位类型代码
\tCC_SYNTHESIZE(string, bin_type_code, Code);
\t// 库位类型名称
\tCC_SYNTHESIZE(string, bin_type_name, Name);

public:
\tLibraryDO() {
\t\tid = "0";
\t\tcreate_name = "";
\t\tcreate_by = "";
\t\tcreate_date = "";
\t\tupdate_name = "";
\t\tupdate_by = "";
\t\tupdate_date = "";
\t\tsys_org_code = "";
\t\tsys_company_code = "";
\t\tbin_type_code = "";
\t\tbin_type_name = "";
\t}
};

// 库位类型DO对象的指针类型设定，通常由智能指针使用
typedef std::shared_ptr<LibraryDO> PtrLibraryDO;

/*
* 库位类型表-库位类型名称（唯一标识 + 代码 + 名称）
*/
class LibraryNameDO
{
\t// 唯一id
\tCC_SYNTHESIZE(string, id, Id);
\t// 库位类型代码
\tCC_SYNTHESIZE(string, bin_type_code, Code);
\t// 库位类型名称
\tCC_SYNTHESIZE(string, bin_type_name, Name);

public:
\tLibraryNameDO() {
\t\tid = "";
\t\tbin_type_code = "";
\t\tbin_type_name = "";
\t}
};

// 库位类型名称DO对象的指针类型设定
typedef std::shared_ptr<LibraryNameDO> PtrLibraryNameDO;


'''

open(p, 'wb').write(new.encode(enc))
print("已写入, 编码:", enc)
