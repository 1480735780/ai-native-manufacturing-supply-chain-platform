# -*- coding: utf-8 -*-
"""智能解码/编码助手：自动识别文件是 UTF-8 还是 GBK，写回时保持原编码。"""
import sys

def detect(raw: bytes) -> str:
    # 严格 utf-8 优先；失败则 gb18030（GBK 超集）
    try:
        raw.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        return 'gb18030'

def read(path: str) -> str:
    raw = open(path, 'rb').read()
    return raw.decode(detect(raw))

def write(path: str, text: str, enc: str = None) -> str:
    if enc is None:
        enc = detect(open(path, 'rb').read()) if __import__('os').path.exists(path) else 'utf-8'
    open(path, 'wb').write(text.encode(enc))
    return enc

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'r':
        for p in sys.argv[2:]:
            raw = open(p, 'rb').read()
            print('=' * 25, p, f'[detected={detect(raw)}]', '=' * 25)
            print(raw.decode(detect(raw)))
    elif mode == 'enc':
        for p in sys.argv[2:]:
            raw = open(p, 'rb').read()
            print(f'{p} -> {detect(raw)}')
