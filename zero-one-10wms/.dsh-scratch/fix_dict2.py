# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

p = "wms-cpp/wms-c7-reposity/zh-dict.yaml"
enc = detect(open(p, 'rb').read())
txt = open(p, 'rb').read().decode(enc)
NL = '\r\n'
def blk(lines): return ''.join(l + NL for l in lines)

old = blk([
 '  file:',
 '    data:',
 '      summary: 导入的文件数据',
 '    impath:',
 '      summary: 导入文件',
 '    expath:',
 '      summary: 导出文件',
 '    sheet:',
 '      summary: 订单类型',
])
new = blk([
 '  file:',
 '    data:',
 '      summary: 导入的文件数据',
 '    impath:',
 '      summary: 导入文件',
 '    expath:',
 '      summary: 导出文件',
 '    sheet:',
 '      summary: 订单类型',
 '    field:',
 '      filename: 下载文件名',
 '    upload:',
 '      summary: 上传文件',
 '    download:',
 '      summary: 下载文件',
])
assert old in txt, "dictionary.file 段未匹配"
txt = txt.replace(old, new, 1)

old2 = blk([
 'excel:',
 ' sheet:',
 '  s1: 数据表1',
 '  s2: 数据表2',
])
new2 = blk([
 'excel:',
 ' content:',
 '  info: 内容',
 ' sheet:',
 '  s1: 数据表1',
 '  s2: 数据表2',
])
assert old2 in txt, "excel 段未匹配"
txt = txt.replace(old2, new2, 1)

open(p, 'wb').write(txt.encode(enc))
print("zh-dict.yaml 补充完成")
