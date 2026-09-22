import game_state

print("=== LIVE INVENTORY ===")
for item, count in game_state.game.inventory.items():
    if count > 0:
        print(f"{item}: count={count}")

print("\n=== TOTAL ITEMS ===")
print(f"Total items in inventory: {len([i for i, c in game_state.game.inventory.items() if c > 0])}")