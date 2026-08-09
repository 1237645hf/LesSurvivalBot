"""
Test script to verify GameState structure without external dependencies.
"""
from game_state import GameState

# Create a fresh game state
game = GameState()

print("=" * 50)
print("GAME STATE VERIFICATION")
print("=" * 50)
print(f"\nCurrent Location: {game.current_location}")
print(f"Story State: {game.story_state}")
print(f"\nKarma Dict:")
for karma_type, value in game.karma.items():
    print(f"  {karma_type.capitalize()}: {value}")
print(f"\nEquipment Slots:")
for slot, item in game.equipment.items():
    print(f"  {slot}: {item}")

print("\n" + "=" * 50)
print("TESTING METHODS")
print("=" * 50)

# Test karma adjustment
game.adjust_karma("heroic", 10)
print(f"\nAfter adding +10 heroic karma:")
print(f"  Heroic karma: {game.karma['heroic']}")

# Test karma title
karma_title = game.get_karma_title()
print(f"\nKarma title: {karma_title}")

print("\n" + "=" * 50)
print("VERIFICATION COMPLETE")
print("=" * 50)
