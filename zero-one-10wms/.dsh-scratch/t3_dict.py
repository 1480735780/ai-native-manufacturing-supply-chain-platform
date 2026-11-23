# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

p = "wms-cpp/wms-c7-reposity/zh-dict.yaml"
enc = detect(open(p, 'rb').read())
txt = open(p, 'rb').read().decode(enc)
assert '\r\n' in txt
NL = '\r\n'

def blk(lines):
    return ''.join(l + NL for l in lines)

old_bin = blk([
 'ba_bin_type:',
 '  excelout:',
 '    summary: 库位类型导出excel',
 '  modify:',
 '    summary: 修改库位类型信息',
 '  excelin:',
 '    summary: 库位类型excel导入',
 '  remove:',
 '    summary: 删除库位类型',
 '  field:',
 '    bin_type_code: 库位类型代码',
 '    act_type_name: 库位类型名称',
 '    create_name: 创建人名称',
 '    create_by: 创建人登录名称',
 '    create_date: 创建日期',
 '    update_name: 更新人名称',
 '    update_by: 更新人登录名称',
 '    update_date: 更新日期',
 '    sys_org_code: 所属部门',
 '    sys_company_code: 所属公司',
 '    id: 唯一id',
 'ba_bin_type:',
 '  query-all:',
 '    summary: 查询所有库位类型',
 '  modify:',
 '    summary: 修改库位类型信息',
 '  add:',
 '    summary: 录入新的库位类型',
 '  delete:',
 '    summary: 删除库位类型',
 '  field:',
 '    bin_type_code: 库位类型代码',
 '    bin_type_name: 库位类型名称',
 '    oper_step_code: 业务环节',
 '    create_name: 创建人名称',
 '    create_by: 创建人登录名称',
 '    create_date: 创建日期',
 '    update_name: 更新人名称',
 '    update_by: 更新人登录名称',
 '    update_date: 更新日期',
 '    sys_org_code: 所属部门',
 '    sys_company_code: 所属公司 ',
])
new_bin = blk([
 'ba_bin_type:',
 '  excelout:',
 '    summary: 库位类型导出excel',
 '  excelin:',
 '    summary: 库位类型excel导入',
 '  query-all:',
 '    summary: 查询所有库位类型',
 '  modify:',
 '    summary: 修改库位类型信息',
 '  add:',
 '    summary: 录入新的库位类型',
 '  delete:',
 '    summary: 删除库位类型',
 '  remove:',
 '    summary: 删除库位类型',
 '  field:',
 '    bin_type_code: 库位类型代码',
 '    bin_type_name: 库位类型名称',
 '    oper_step_code: 业务环节',
 '    create_name: 创建人名称',
 '    create_by: 创建人登录名称',
 '    create_date: 创建日期',
 '    update_name: 更新人名称',
 '    update_by: 更新人登录名称',
 '    update_date: 更新日期',
 '    sys_org_code: 所属部门',
 '    sys_company_code: 所属公司',
 '    id: 唯一id',
])
assert old_bin in txt, "ba_bin_type 段未匹配"
txt = txt.replace(old_bin, new_bin, 1)

old_ope = blk([
 '  libraryope:',
 '    modify:',
 '      summary: 修改库位类型',
 '    delete:',
 '      summary: 删除库位类型',
 '    delete-all:',
 '      summary: 删除所有库位类型',
 '    import:',
 '      summary: 导入库位类型',
 '    export:',
 '      summary: 导出库位类型',
])
new_ope = blk([
 '  libraryope:',
 '    modify:',
 '      summary: 修改库位类型',
 '    delete:',
 '      summary: 删除库位类型',
 '    delete-all:',
 '      summary: 删除所有库位类型',
 '    import:',
 '      summary: 导入库位类型',
 '    export:',
 '      summary: 导出库位类型',
 '    query-all:',
 '      summary: 查询全部库位类型',
 '    query-name:',
 '      summary: 查询库位类型名称列表',
 '    add:',
 '      summary: 新增库位类型',
])
assert old_ope in txt, "dictionary.libraryope 段未匹配"
txt = txt.replace(old_ope, new_ope, 1)

old_lib = blk([
 '  library:',
 '    id:',
 '      summary: 库位类型id',
 '    code:',
 '      summary: 库位类型代码',
 '    type:',
 '      summary: 库位类型名称',
])
new_lib = blk([
 '  library:',
 '    id:',
 '      summary: 库位类型id',
 '    code:',
 '      summary: 库位类型代码',
 '    type:',
 '      summary: 库位类型名称',
 '    field:',
 '      id: 唯一标识',
 '      create_name: 创建人名称',
 '      create_by: 创建人登录名称',
 '      create_date: 创建日期',
 '      update_name: 更新人名称',
 '      update_by: 更新人登录名称',
 '      update_date: 更新日期',
 '      sys_org_code: 所属部门',
 '      sys_company_code: 所属公司',
 '      bin_type_code: 库位类型代码',
 '      bin_type_name: 库位类型名称',
])
assert old_lib in txt, "dictionary.library 段未匹配"
txt = txt.replace(old_lib, new_lib, 1)

open(p, 'wb').write(txt.encode(enc))
print("zh-dict.yaml 已更新, 编码:", enc)
