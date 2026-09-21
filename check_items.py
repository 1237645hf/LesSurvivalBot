"""Quick verification of the ITEMS dict structure."""
from modules.items import ITEMS

print(f"Number of items: {len(ITEMS)}")
print("First item:", list(ITEMS.keys())[:3])
print("Last item:", list(ITEMS.keys())[-3:])
print("Sample item:", ITEMS["Печёные ягоды"])
