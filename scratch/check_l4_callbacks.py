import ast
import re

with open("story/locations/loc4_hunters.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Найти все callback_data в кнопках
button_cbs = set(re.findall(r'callback_data="([^"]+)"', content))
# также динамические f-строки
f_cbs = re.findall(r'callback_data=f"([^"]+)"', content)

# 2. Найти все проверяемые data == "..." или data in (...)
handled_cbs = set(re.findall(r'data == "([^"]+)"', content))
for tuple_match in re.findall(r'data in \(([^)]+)\)', content):
    for item in re.findall(r'"([^"]+)"', tuple_match):
        handled_cbs.add(item)
for tuple_match in re.findall(r'data in \[([^\]]+)\]', content):
    for item in re.findall(r'"([^"]+)"', tuple_match):
        handled_cbs.add(item)
startswith_checks = re.findall(r'data\.startswith\("([^"]+)"\)', content)

print(f"Total literal button callbacks: {len(button_cbs)}")
print(f"Total handled exact callbacks: {len(handled_cbs)}")
print(f"Starts with checks: {startswith_checks}")
print(f"Dynamic f-string callbacks: {f_cbs}")

# Ищем колбэки из кнопок, которых нет среди handled_cbs и не покрываются startswith и не "back"
missing = []
for cb in sorted(button_cbs):
    if cb == "back":
        continue
    if cb in handled_cbs:
        continue
    if any(cb.startswith(sw) for sw in startswith_checks):
        continue
    missing.append(cb)

print("MISSING / UNHANDLED callbacks from buttons:")
for m in missing:
    print(f"  - {m}")
