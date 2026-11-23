# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

p = "wms-cpp/wms-c8-wconfig/zh-dict.yaml"
enc = detect(open(p, 'rb').read())
txt = open(p, 'rb').read().decode(enc)
NL = '\r\n'
def blk(lines): return ''.join(l + NL for l in lines)

def rep(old_lines, new_lines, label):
    global txt
    old, new = blk(old_lines), blk(new_lines)
    assert old in txt, "未匹配: " + label
    txt = txt.replace(old, new, 1)
    print("OK", label)

# ---- 1. lad 段补齐缺失词条 ----
rep([' add:', '  summary: 录入提货方式', ' field:'],
    [' add:', '  summary: 录入提货方式',
     ' delete:', '  summary: 删除提货方式',
     ' batchDelete:', '  summary: 批量删除提货方式',
     ' import:', '  summary: 导入提货方式',
     ' export:', '  summary: 导出提货方式',
     ' excel:', '  name: 提货方式', '  col:',
     '   first: 提货方式代码', '   second: 提货方式名称',
     ' field:'], 'lad 段补词条')

# ---- 2. recv-g-way 段：补 field.ids / batchDelete / 修正 query-all.description ----
rep([' query-all:', '  description:', '  summary: 使用声明式服务查询多条数据', ' file:'],
    [' query-all:', '  description: 查询接货方式（分页+条件）', '  summary: 查询接货方式（分页+条件）',
     ' batchDelete:', '  summary: 批量删除接货方式',
     ' file:', '  ids: 唯一标识列表'], 'recv-g-way 段补词条')

# ---- 3. recv-g-way-file 段：修正导入导出标反 + 补 excel 段 ----
rep([' upload_f: ', '  description: ', '  summary: 接货文件导出',
     ' download_f:', '  description:', '  summary: 接货文件导入',
     ' filed:'],
    [' upload_f:', '  description: 导入接货方式（Excel上传）', '  summary: 导入接货方式',
     ' download_f:', '  description: 导出接货方式（Excel下载）', '  summary: 导出接货方式',
     ' excel:', '  name: 接货方式', '  col:',
     '   first: 接货方式代码', '   second: 接货方式名称',
     ' filed:'], 'recv-g-way-file 段修正')

open(p, 'wb').write(txt.encode(enc))
print("c8 zh-dict.yaml 已更新, 编码:", enc)
