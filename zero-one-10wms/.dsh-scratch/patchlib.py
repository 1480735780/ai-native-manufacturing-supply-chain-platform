# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.dsh-scratch')
from enc import detect

def patch(path, old, new, count=1):
    enc = detect(open(path, 'rb').read())
    raw = open(path, 'rb').read()
    nl = '\r\n' if raw.count(b'\r\n') > raw.count(b'\n') / 2 else '\n'
    txt = raw.decode(enc)
    o = old.replace('\n', nl)
    n = new.replace('\n', nl)
    assert o in txt, "未找到 @ %s : %r" % (path, old[:70])
    txt = txt.replace(o, n, count)
    open(path, 'wb').write(txt.encode(enc))
    print("OK", path, "[%s][%s]" % (enc, repr(nl)))
