import re, sys, io

p = r'D:\Learning\code\AIWMSproject\zero-one-10wms\documents\02、项目需求\数据库\zowms.sql'
s = open(p, encoding='utf-8', errors='replace').read()

# find CREATE TABLE blocks
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
    cm = re.search(r'COMMENT\s*=\s*\'([^\']*)\'', tail)
    tables.append((name, cm.group(1) if cm else '', body))

print('TOTAL TABLES:', len(tables))
print()
by_prefix = {}
for name, cm, body in tables:
    pref = name.split('_')[0]
    by_prefix.setdefault(pref, []).append((name, cm))
for pref in sorted(by_prefix):
    print(f'== {pref}_ ({len(by_prefix[pref])}) ==')
    for name, cm in by_prefix[pref]:
        print(f'  {name}  |  {cm}')
    print()
