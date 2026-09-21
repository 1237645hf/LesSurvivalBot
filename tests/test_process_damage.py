"""Тест для проверки process_damage в game_math.py."""
from game_math import process_damage
from game_state import GameState

# Тест 1: HP=10, урон 15 (должен упасть до 1 — максимальный урон)
print("=== Тест 1: HP=10, урон 15 ===")
g = GameState()
g.hp = 10
g.ap = 5
print(f"До: HP={g.hp}, AP={g.ap}")
new_hp, log = process_damage(g, 15)
print(f"После: New HP={new_hp}, Log='{log}', Actual HP={g.hp}")
assert new_hp == 1, f"New HP должен быть 1, а не {new_hp}"
assert g.hp == 1, f"g.hp должен быть 1, а не {g.hp}"
print("✅ Тест 1 пройден!\n")

# Тест 2: HP=5, урон 10 (должен упасть до 1 — кап)
print("=== Тест 2: HP=5, урон 10 ===")
g2 = GameState()
g2.hp = 5
g2.ap = 5
print(f"До: HP={g2.hp}, AP={g2.ap}")
new_hp2, log2 = process_damage(g2, 10)
print(f"После: New HP={new_hp2}, Log='{log2}', Actual HP={g2.hp}")
assert new_hp2 == 1, f"New HP должен быть 1, а не {new_hp2}"
assert g2.hp == 1, f"g2.hp должен быть 1, а не {g2.hp}"
print("✅ Тест 2 пройден!\n")

# Тест 3: HP=50, урон 20 (должен упасть до 30)
print("=== Тест 3: HP=50, урон 20 ===")
g3 = GameState()
g3.hp = 50
g3.ap = 5
print(f"До: HP={g3.hp}, AP={g3.ap}")
new_hp3, log3 = process_damage(g3, 20)
print(f"После: New HP={new_hp3}, Log='{log3}', Actual HP={g3.hp}")
assert new_hp3 == 30, f"New HP должен быть 30, а не {new_hp3}"
assert g3.hp == 30, f"g3.hp должен быть 30, а не {g3.hp}"
print("✅ Тест 3 пройден!\n")

print("🎉 Все тесты process_damage пройдены!")