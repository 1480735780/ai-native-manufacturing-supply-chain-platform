# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

p = "wms-cpp/wms-c7-reposity/zh-dict.yaml"
enc = detect(open(p, 'rb').read())
txt = open(p, 'rb').read().decode(enc)
NL = '\r\n'
def blk(lines): return ''.join(l + NL for l in lines)

# 在顶层 excel: 之前插入顶层 file: 组
anchor = blk(['excel:', ' content:', '  info: 内容', ' sheet:', '  s1: 数据表1'])
assert anchor in txt, "excel 段定位失败"
new = blk([
 'file:',
 ' upload:',
 '  summary: 上传文件',
 ' download:',
 '  summary: 下载文件',
 ' field:',
 '  filename: 下载文件名',
]) + anchor
txt = txt.replace(anchor, new, 1)
open(p, 'wb').write(txt.encode(enc))
print("顶层 file 组已补充")
