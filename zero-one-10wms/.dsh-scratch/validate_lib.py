# -*- coding: utf-8 -*-
import re, os, sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

ROOT = "wms-cpp/wms-c7-reposity/"

def rd(p):
    raw = open(ROOT + p, 'rb').read()
    try: return raw.decode('utf-8')
    except UnicodeDecodeError: return raw.decode('gb18030')

def decls(txt, cls):
    """提取类体内声明的成员函数（含返回类型）"""
    m = re.search(r'class\s+' + cls + r'\b.*?\n\};', txt, re.S)
    if not m: return None, None
    body = m.group(0)
    decls_, defs_ = [], []
    # 声明：形如  返回类型 名字(参数);
    for mm in re.finditer(r'([\w:<>,\s\*&]+?)\s+(\w+)\s*\(([^;{)]*)\)\s*(?:const\s*)?;', body):
        decls_.append((mm.group(2), mm.group(3).strip()))
    # 定义：形如  返回类型 Class::名字(参数) {
    for mm in re.finditer(r'([\w:<>,\s\*&]+?)\s+' + cls + r'::(\w+)\s*\(([^)]*)\)\s*(?:const\s*)?\{', txt):
        defs_.append((mm.group(2), mm.group(3).strip()))
    return decls_, defs_

def report(name, cls, hdr, src):
    d, f = decls(rd(hdr), cls)
    if d is None:
        print(f"  [{name}] 未找到类 {cls}"); return False
    ok = True
    dn = {x[0] for x in d}; fn = {x[0] for x in f}
    miss = dn - fn
    if miss:
        print(f"  [{name}] 声明未定义: {sorted(miss)}"); ok = False
    # 参数个数比对
    dm = {x[0]: len([p for p in x[1].split(',') if p.strip()]) for x in d}
    fm = {x[0]: len([p for p in x[1].split(',') if p.strip()]) for x in f}
    for k in dn & fn:
        if dm[k] != fm[k]:
            print(f"  [{name}] {k} 参数个数不一致 声明={dm[k]} 定义={fm[k]}"); ok = False
    print(f"  [{name}] 声明{len(dn)}/定义{len(fn)} {'OK' if ok else 'FAIL'}")
    return ok

print("=== 类成员声明/定义一致性 ===")
allok = True
allok &= report("LibraryService", "LibraryService", "service/library/LibraryService.h", "service/library/LibraryService.cpp")
allok &= report("LibraryDAO", "LibraryDAO", "dao/library/LibraryDAO.h", "dao/library/LibraryDAO.cpp")
allok &= report("LibraryController", "LibraryController", "controller/library/LibraryController.h", "controller/library/LibraryController.cpp")

print("\n=== DO getter/setter 与 DTO 字段映射校验 ===")
do = rd("domain/do/library/LibraryDO.h")
do_get = set(re.findall(r'CC_SYNTHESIZE\([^,]+,\s*(\w+),\s*(\w+)\)', do))
do_map = {}
for var, fn in do_get:
    do_map[fn] = var          # getter 名 -> 字段名
print("  LibraryDO getters:", sorted(set(do_map)))

dto = rd("domain/dto/library/LibraryDTO.h")
dto_fields = set(re.findall(r'API_DTO_FIELD_DEFAULT\(\s*\w+,\s*(\w+)\s*,', dto))
print("  LibraryDTO fields:", sorted(dto_fields))

svc = rd("service/library/LibraryService.cpp")
for mm in re.finditer(r'ZO_STAR_DOMAIN_DO_TO_DTO\((\w+),\s*(\w+),([^)]*)\)', svc):
    tgt, src, fields = mm.group(1), mm.group(2), mm.group(3)
    pairs = [x.strip() for x in fields.split(',') if x.strip()]
    for i in range(0, len(pairs), 2):
        df, gf = pairs[i], pairs[i+1]
        if gf not in do_map:
            print(f"  FAIL DO→DTO: getter get{gf} 不存在于 DO"); allok = False
        elif do_map[gf] != df:
            print(f"  FAIL DO→DTO: 字段名不匹配 dto {df} vs do {do_map[gf]}"); allok = False
        if df not in dto_fields:
            print(f"  FAIL DO→DTO: DTO 无字段 {df}"); allok = False
    print(f"  DO→DTO {tgt} <- {src}: {len(pairs)//2} 项 OK")

for mm in re.finditer(r'ZO_STAR_DOMAIN_DTO_TO_DO\((\w+),\s*(\w+),([^)]*)\)', svc):
    tgt, src, fields = mm.group(1), mm.group(2), mm.group(3)
    pairs = [x.strip() for x in fields.split(',') if x.strip()]
    for i in range(0, len(pairs), 2):
        setter, df = pairs[i], pairs[i+1]
        if setter not in do_map:
            print(f"  FAIL DTO→DO: setter set{setter} 不存在于 DO"); allok = False
        if df not in dto_fields:
            print(f"  FAIL DTO→DO: DTO 无字段 {df}"); allok = False
    print(f"  DTO→DO {tgt} <- {src}: {len(pairs)//2} 项 OK")

print("\n=== 端点路径唯一性 & 前导斜杠 ===")
paths = []
for f in ["controller/library/LibraryController.h", "controller/libraryfile/LibraryFileController.h",
          "controller/business-link/BusinessLinkController.h", "controller/temperature/TemperatureController.h"]:
    t = rd(f)
    for mm in re.finditer(r'ENDPOINT\(\s*API_M_\w+,\s*"([^"]+)"', t):
        paths.append((f, mm.group(1)))
seen = {}
for f, p in paths:
    if not p.startswith('/'):
        print(f"  FAIL 路径缺少前导斜杠: {f} -> {p}"); allok = False
    if p in seen:
        print(f"  FAIL 路径重复: {p} ({seen[p]} vs {f})"); allok = False
    seen[p] = f
print(f"  共 {len(paths)} 个端点, 唯一 {len(seen)} 个")

print("\n总校验:", "PASS" if allok else "FAIL")
