import game_state
import modules.items

print("=== INVENTORY vs ITEMS ===")
items = [item for item, count in game_state.game.inventory.items() if count > 0]
print(f"Inventory items: {items}")
print("")
print("In ITEMS dict:")
for item in items:
    item_data = modules.items.ITEMS.get(item, "MISSING")
    if item_data:
        print(f"  {item}: {item_data}")
    else:
        print(f"  {item}: MISSING")

print("\n=== ITEMS dict keys only ===")
for key in sorted(modules.items.ITEMS.keys()):
    print(f"  {key}")
