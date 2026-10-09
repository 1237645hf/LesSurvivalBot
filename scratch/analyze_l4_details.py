import re

with open("story/locations/loc4_hunters.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("=== KARMA ADJUSTMENTS ===")
for i, line in enumerate(lines, 1):
    if "adjust_narrative_karma" in line or "karma" in line.lower():
        print(f"Line {i}: {line.strip()}")

print("\n=== UNLOCKED LOCATIONS MODIFICATIONS ===")
for i, line in enumerate(lines, 1):
    if "unlocked_locations" in line or "unlocked.append" in line:
        print(f"Line {i}: {line.strip()}")

print("\n=== PRE_STORY_LOCATION / CURRENT_LOCATION ===")
for i, line in enumerate(lines, 1):
    if "pre_story_location" in line or "current_location" in line or "location_index" in line:
        print(f"Line {i}: {line.strip()}")

print("\n=== BATTLES / COMBAT CONTEXT ===")
for i, line in enumerate(lines, 1):
    if "wolf_battle" in line or "slug_battle" in line or "wolf_pack_battle" in line:
        print(f"Line {i}: {line.strip()}")

print("\n=== INVENTORY MODIFICATIONS ===")
for i, line in enumerate(lines, 1):
    if "game.inventory[" in line or "game.inventory.pop" in line or "del game.inventory" in line:
        print(f"Line {i}: {line.strip()}")
