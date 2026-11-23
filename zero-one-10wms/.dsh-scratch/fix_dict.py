# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

def patch(path, old, new, count=1):
    enc = detect(open(path, 'rb').read())
    txt = open(path, 'rb').read().decode(enc)
    assert old in txt, "未找到: %s -> %s" % (path, old)
    txt = txt.replace(old, new, count)
    open(path, 'wb').write(txt.encode(enc))
    print("OK", path)

R = "wms-cpp/wms-c7-reposity/"

# 1. dictionary.order.name.summary -> dictionary.order.type.summary
patch(R+"controller/file/FileController.cpp", '"dictionary.order.name.summary"', '"dictionary.order.type.summary"')
patch(R+"controller/temperature/TemperatureController.cpp", '"dictionary.order.name.summary"', '"dictionary.order.type.summary"')

# 2. dictionary.library.name.summary -> dictionary.library.type.summary
patch(R+"controller/libraryfile/LibraryFileController.cpp", '"dictionary.library.name.summary"', '"dictionary.library.type.summary"')

# 3. 温度属性端点标题：repository.* -> reposity.*（yaml 中根键为 reposity）
patch(R+"controller/temperature/TemperatureController.h", '"repository.temperature.queryall.summary"', '"reposity.temperature.queryall.summary"')
patch(R+"controller/temperature/TemperatureController.h", '"repository.temperature.add.summary"', '"reposity.temperature.add.summary"')
