# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect
R = "wms-cpp/wms-c8-wconfig/"

def patch(path, old, new, count=1):
    enc = detect(open(path, 'rb').read())
    txt = open(path, 'rb').read().decode(enc)
    assert old in txt, "未找到: %s -> %r" % (path, old)
    txt = txt.replace(old, new, count)
    open(path, 'wb').write(txt.encode(enc))
    print("OK", path)

# 1. 移除未实现的死声明 DefPutData
patch(R+"service/recv-g-way/Recv-G-WayService.h",
      "\t//默认值处理\n\tstd::string DefPutData(const PayloadDTO& payload);\n", "")

# 2. 修正 DTO 中错误的词条键名（recv_g_way -> recv-g-way）
patch(R+"domain/dto/recv-g-way/Recv-G-WayFileDto.h",
      '"recv_g_way.file.del_mode_name"', '"recv-g-way.file.del_mode_name"')
patch(R+"domain/dto/recv-g-way/Recv-G-WayFileDto.h",
      '"recv_g_way.file.del_mode_code"', '"recv-g-way.file.del_mode_code"')
patch(R+"domain/dto/recv-g-way/Recv-G-WayFileDto.h",
      '"recv_g_way.file.id"', '"recv-g-way.file.id"')

# 3. 修正 EditorImageDTO 词条键名（field -> filed）
patch(R+"domain/dto/recv-g-way/Recv-G-WayFileDto.h",
      '"recv-g-way-file.field.img-url"', '"recv-g-way-file.filed.img-url"')
patch(R+"domain/dto/recv-g-way/Recv-G-WayFileDto.h",
      '"recv-g-way-file.field.img-alt"', '"recv-g-way-file.filed.img-alt"')
patch(R+"domain/dto/recv-g-way/Recv-G-WayFileDto.h",
      '"recv-g-way-file.field.img-href"', '"recv-g-way-file.filed.img-href"')
