import re

with open('story/locations/loc3_hollow.py', 'r', encoding='utf-8') as f:
    content = f.read()

btn_callbacks = set(re.findall(r'callback_data=[\'"]([^\'"]+)[\'"]', content))

handled = set()
for match in re.finditer(r'(?:data\s*==\s*[\'"]([^\'"]+)[\'"]|data\s*in\s*\(([^)]+)\))', content):
    if match.group(1):
        handled.add(match.group(1))
    if match.group(2):
        for item in re.findall(r'[\'"]([^\'"]+)[\'"]', match.group(2)):
            handled.add(item)

startswith_prefixes = re.findall(r'data\.startswith\([\'"]([^\'"]+)[\'"]\)', content)

unhandled = set()
for cb in btn_callbacks:
    if cb in handled:
        continue
    if any(cb.startswith(p) for p in startswith_prefixes):
        continue
    unhandled.add(cb)

print(f"Total button callbacks: {len(btn_callbacks)}")
print(f"Handled exact callbacks: {len(handled)}")
print(f"Startswith prefixes: {startswith_prefixes}")
print(f"Unhandled button callbacks: {unhandled}")

# Also check karma adjustments
karma_calls = []
for i, line in enumerate(content.splitlines(), 1):
    if "adjust_narrative_karma" in line:
        karma_calls.append((i, line.strip()))
print(f"\nKarma calls ({len(karma_calls)}):")
for ln, text in karma_calls:
    print(f"  Line {ln}: {text}")

# Check HP modifications
hp_lines = []
for i, line in enumerate(content.splitlines(), 1):
    if re.search(r'(\bhp\b|\bhealth\b)', line):
        hp_lines.append((i, line.strip()))
print(f"\nHP lines ({len(hp_lines)}):")
for ln, text in hp_lines:
    print(f"  Line {ln}: {text}")

# Check stove and campfire usages
stove_lines = []
for i, line in enumerate(content.splitlines(), 1):
    if re.search(r'(\bstove\b|\bhearth\b|\bcampfire\b)', line):
        stove_lines.append((i, line.strip()))
print(f"\nStove/Hearth lines ({len(stove_lines)}):")
for ln, text in stove_lines:
    print(f"  Line {ln}: {text}")

# Check location strings
loc_strings = []
for i, line in enumerate(content.splitlines(), 1):
    if re.search(r'(лощин|hollow|просек|ручей|лес|bright|яр|слайм)', line, re.IGNORECASE):
        loc_strings.append((i, line.strip()))
print(f"\nLocation string lines count: {len(loc_strings)}")
for ln, text in loc_strings[:20]:
    print(f"  Line {ln}: {text}")
