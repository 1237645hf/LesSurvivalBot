"""Test script to verify items.py structure"""

from modules import items

print(f"Items dict has {len(items.ITEMS)} items")
print(f"Sample items: {list(items.ITEMS.keys())[:5]}")

# Check if dict is properly closed
print(f"First item: {list(items.ITEMS.keys())[0]}")
print(f"Last item: {list(items.ITEMS.keys())[-1]}")
