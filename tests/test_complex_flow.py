"""Комплексный тест для проверки всей логики AP и ресурсов."""
from game_state import GameState
from game_math import process_damage

print("=== Комплексный тест: Смена дня + Действие + Урон ===\n")

# Создаём персонажа
game = GameState()
game.hp = 45
game.hunger = 20
game.thirst = 25
game.ap = 5
game.day = 1
game.weather = "clear"

print(f"1. Начальное состояние (День 1):")
print(f"   HP: {game.hp}, AP: {game.ap}, Hunger: {game.hunger}, Thirst: {game.thirst}")
print(f"   Статус-бар: {game.get_status_bar()}")

# Смена дня — reset_daily_ap
print(f"\n2. Смена дня (reset_daily_ap):")
daily_ap = game.reset_daily_ap()
print(f"   Новый AP: {daily_ap}")
print(f"   Статус-бар: {game.get_status_bar()}")

# Действие — consume_action
print(f"\n3. Действие 'walk' (consume_action):")
result = game.consume_action("walk")
print(f"   Результат: {result}")
print(f"   AP: {game.ap}, Hunger: {game.hunger}, Thirst: {game.thirst}")
print(f"   Статус-бар: {game.get_status_bar()}")

# Урон — process_damage
print(f"\n4. Урон 10 (process_damage):")
new_hp, log = process_damage(game, 10)
print(f"   Новый HP: {new_hp}, Лог: '{log}'")
print(f"   AP: {game.ap}, HP: {game.hp}")
print(f"   Статус-бар: {game.get_status_bar()}")

# Проверка, что HP не ушёл ниже 1
assert game.hp >= 1, f"HP должен быть >= 1, а не {game.hp}"
# Проверка, что AP не ушёл ниже 0
assert game.ap >= 0, f"AP должен быть >= 0, а не {game.ap}"
# Проверка, что hunger не ушёл ниже 1
assert game.hunger >= 1, f"Hunger должен быть >= 1, а не {game.hunger}"
# Проверка, что thirst не ушёл ниже 1
assert game.thirst >= 1, f"Thirst должен быть >= 1, а не {game.thirst}"

print(f"\n✅ Все проверки пройдены!")
print(f"\n📊 Итоговое состояние:")
print(f"   HP: {game.hp}, AP: {game.ap}, Hunger: {game.hunger}, Thirst: {game.thirst}")