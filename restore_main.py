#!/usr/bin/env python3
"""Восстановить main.py. Один раз: python restore_main.py"""
import zlib, base64, pathlib
root = pathlib.Path(__file__).resolve().parent
blob = (root / "main.blob").read_text().strip()
path = root / "main.py"
path.write_text(zlib.decompress(base64.b64decode(blob)).decode("utf-8"), encoding="utf-8")
print(f"OK: main.py restored ({path.stat().st_size} bytes)")
print("Проверка: python -m py_compile main.py")
