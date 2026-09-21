#!/usr/bin/env python3
"""Восстановить исправленный main.py. Запуск: python restore_main.py"""
import zlib, base64, pathlib
root = pathlib.Path(__file__).resolve().parent
blob = "".join((root / f"main.blob.{i}").read_text() for i in range(3))
path = root / "main.py"
path.write_text(zlib.decompress(base64.b64decode(blob)).decode(), encoding="utf-8")
print(f"OK: main.py restored ({path.stat().st_size} bytes)")
print("Теперь можно запускать: python main.py")
