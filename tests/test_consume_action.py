"""Тест для проверки consume_action и ресурсов."""
from game_state import GameState

g = GameState()
g.hp = 45
g.ap = 5
g.hunger = 20
g.thirst = 25

print("--- До действия ---")
print(f"HP: {g.hp}, AP: {g.ap}, Hunger: {g.hunger}, Thirst: {g.thirst}")

result = g.consume_action("test")

print("--- После действия ---")
print(f"AP: {g.ap}, Hunger: {g.hunger}, Thirst: {g.thirst}")

# Проверка, что AP упал на 1
assert g.ap == 4, f"AP должен быть 4, а не {g.ap}"
# Проверка, что hunger не ушёл ниже 1
assert g.hunger >= 1, f"Hunger должен быть >= 1, а не {g.hunger}"
# Проверка, что thirst не ушёл ниже 1
assert g.thirst >= 1, f"Thirst должен быть >= 1, а не {g.thirst}"

print("\n✅ Все проверки пройдены!")