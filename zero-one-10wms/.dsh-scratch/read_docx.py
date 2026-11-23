import docx, os, io

files = [
    r'D:\Learning\code\AIWMSproject\zero-one-10wms\documents\02、项目需求\业务流程文档\细化业务流程\c2\企业配置\企业配置.docx',
    r'D:\Learning\code\AIWMSproject\zero-one-10wms\documents\02、项目需求\业务流程文档\细化业务流程\c7\仓库配置\库位类型\库位类型.docx',
]

out = io.StringIO()
for f in files:
    out.write(f'\n\n===== {os.path.basename(f)} =====\n')
    d = docx.Document(f)
    for p in d.paragraphs:
        t = p.text.strip()
        if t:
            out.write(t + '\n')
    for ti, tbl in enumerate(d.tables):
        out.write(f'\n[表 {ti+1}]\n')
        for row in tbl.rows:
            cells = [c.text.strip().replace('\n', ' ') for c in row.cells]
            out.write(' | '.join(cells) + '\n')

open(r'D:\Learning\code\AIWMSproject\zero-one-10wms\.dsh-scratch\docx-text.txt', 'w', encoding='utf-8').write(out.getvalue())
print('done', sum(len(open(f,'rb').read()) for f in files))
