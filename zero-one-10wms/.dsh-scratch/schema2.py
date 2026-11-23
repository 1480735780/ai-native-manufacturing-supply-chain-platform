import re, io

p = r'D:\Learning\code\AIWMSproject\zero-one-10wms\documents\02、项目需求\数据库\zowms.sql'
s = open(p, encoding='utf-8').read()

tables = []
for m in re.finditer(r'CREATE TABLE\s+`([^`]+)`\s*\(', s):
    name = m.group(1)
    start = m.end()
    depth = 1
    i = start
    while i < len(s) and depth > 0:
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
        i += 1
    body = s[start:i-1]
    tail = s[i:i+400]
    cm = re.search(r"COMMENT\s*=\s*'([^']*)'", tail)
    tables.append((name, cm.group(1) if cm else '', body))

out = io.StringIO()
out.write(f'# 数据库表清单（zowms.sql，共 {len(tables)} 张表）\n\n')
by_prefix = {}
for name, cm, body in tables:
    pref = name.split('_')[0]
    by_prefix.setdefault(pref, []).append((name, cm, body))

for pref in sorted(by_prefix):
    out.write(f'\n## `{pref}_` 前缀（{len(by_prefix[pref])} 张）\n\n')
    out.write('| 表名 | 注释 |\n|---|---|\n')
    for name, cm, body in by_prefix[pref]:
        out.write(f'| `{name}` | {cm} |\n')

open(r'D:\Learning\code\AIWMSproject\zero-one-10wms\.dsh-scratch\table-list.md', 'w', encoding='utf-8').write(out.getvalue())
print('written')
