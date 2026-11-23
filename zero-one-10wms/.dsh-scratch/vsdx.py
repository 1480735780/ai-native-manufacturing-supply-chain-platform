import zipfile, re, os, io, sys

root = r'D:\Learning\code\AIWMSproject\zero-one-10wms\documents\02、项目需求\业务流程文档'

out = io.StringIO()
count = 0
for dirpath, dirnames, filenames in os.walk(root):
    for fn in filenames:
        if not fn.lower().endswith('.vsdx'):
            continue
        full = os.path.join(dirpath, fn)
        try:
            z = zipfile.ZipFile(full)
        except Exception as e:
            out.write(f'\n### {fn}\n[无法打开: {e}]\n')
            continue
        texts = []
        for n in z.namelist():
            if not re.match(r'visio/pages/page\d+\.xml$', n):
                continue
            xml = z.read(n).decode('utf-8', 'replace')
            # <Text>...</Text> elements, strip inner tags
            for m in re.finditer(r'<Text[^>]*>(.*?)</Text>', xml, re.S):
                t = re.sub(r'<[^>]+>', '', m.group(1))
                t = t.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
                t = re.sub(r'\s+', ' ', t).strip()
                if t:
                    texts.append(t)
        rel = os.path.relpath(full, root)
        out.write(f'\n### {rel}\n')
        if texts:
            out.write(' | '.join(dict.fromkeys(texts)) + '\n')
        else:
            out.write('[无文本]\n')
        count += 1

open(r'D:\Learning\code\AIWMSproject\zero-one-10wms\.dsh-scratch\vsdx-text.txt', 'w', encoding='utf-8').write(out.getvalue())
print('vsdx files:', count)
