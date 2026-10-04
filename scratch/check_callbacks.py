import re
from pathlib import Path

files = [
    Path("story/location_stories.py"),
    Path("keyboards.py"),
    Path("main.py"),
    Path("modules/finds.py"),
    Path("game_state.py"),
]

all_callbacks = {}
for file in files:
    if not file.exists():
        continue
    content = file.read_text(encoding="utf-8")
    cbs = re.findall(r'callback_data=[\'"]([^\'"]+)[\'"]', content)
    all_callbacks[str(file)] = sorted(set(cbs))
    print(f"{file}: {len(set(cbs))} unique callbacks found")

for file, cbs in all_callbacks.items():
    print(f"\n--- {file} ({len(cbs)}) ---")
    for cb in cbs[:20]:
        print(" ", cb)
    if len(cbs) > 20:
        print(f"  ... and {len(cbs) - 20} more")
