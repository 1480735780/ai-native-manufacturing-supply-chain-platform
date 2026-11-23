import os, re, io

root = r'D:\Learning\code\AIWMSproject\zero-one-10wms\documents\02、项目需求\业务流程文档'
rows = []
for dirpath, dirnames, filenames in os.walk(root):
    for fn in filenames:
        low = fn.lower()
        if not (low.endswith('.pdf') or low.endswith('.png') or low.endswith('.jpg') or low.endswith('.jpeg')):
            continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, root)
        pages = ''
        if low.endswith('.pdf'):
            data = open(full, 'rb').read()
            m = re.findall(rb'/Type\s*/Page[^s]', data)
            pages = str(len(m))
        rows.append((rel, os.path.getsize(full), pages))

rows.sort()
out = io.StringIO()
out.write(f'共 {len(rows)} 个图形文件\n\n')
out.write('| 文件 | 大小KB | 页数 |\n|---|---|---|\n')
for rel, size, pages in rows:
    out.write(f'| {rel} | {size//1024} | {pages} |\n')
open(r'D:\Learning\code\AIWMSproject\zero-one-10wms\.dsh-scratch\file-inventory.md', 'w', encoding='utf-8').write(out.getvalue())
print('files:', len(rows))
