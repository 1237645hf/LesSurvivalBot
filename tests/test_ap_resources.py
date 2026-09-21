"""Короткий тест для проверки AP и ресурсов."""
from game_state import GameState
from game_math import process_damage

print("=" * 60)
print("🧪 КОМПЛЕКСНЫЙ ТЕСТ: AP и Ресурсы")
print("=" * 60)

# 1. Расчет AP для разных уровней HP
print("\n📊 1. Расчет AP для HP = 55, 45, 35, 15, 5:")
print("-" * 50)
for hp in [55, 45, 35, 15, 5]:
    g = GameState()
    g.hp = hp
    g.ap = 5
    daily_ap = g.calculate_daily_ap()
    print(f"   HP={hp:2} → Daily AP: {daily_ap}")

# 2. Попытка опустить ресурсы ниже 1
print("\n📊 2. Попытка опустить ресурсы ниже 1 (должна остаться ровно 1):")
print("-" * 50)

# Тест для hunger (base_hunger=2)
g_hunger = GameState()
g_hunger.hunger = 3
g_hunger.ap = 5
print(f"   Hunger=3, AP=5 → После действия: Hunger={g_hunger.hunger}")
g_hunger.consume_action('test')
print(f"   После consume_action: Hunger={g_hunger.hunger}")
assert g_hunger.hunger == 1, f"Ошибка: Hunger должен быть 1, а не {g_hunger.hunger}"

# Тест для thirst (base_thirst=1)
g_thirst = GameState()
g_thirst.thirst = 3
g_thirst.ap = 5
print(f"   Thirst=3, AP=5 → После действия: Thirst={g_thirst.thirst}")
g_thirst.consume_action('test')
print(f"   После consume_action: Thirst={g_thirst.thirst}")
assert g_thirst.thirst == 2, f"Ошибка: Thirst должен быть 2, а не {g_thirst.thirst}"

# Тест для hp через process_damage
g_hp = GameState()
g_hp.hp = 3
g_hp.ap = 5
new_hp, log = process_damage(g_hp, 2)
print(f"   HP=3, Урон=2 → Новый HP: {new_hp}, Лог: '{log}'")
assert new_hp == 1, f"Ошибка: HP должен быть 1, а не {new_hp}"

# 3. Финальный комплексный тест
print("\n📊 3. Финальный комплексный тест (Смена дня + Действие + Урон):")
print("-" * 50)
game = GameState()
game.hp = 45
game.hunger = 20
game.thirst = 25
game.ap = 5
game.day = 1

print(f"   Начальное: HP={game.hp}, AP={game.ap}, Hunger={game.hunger}, Thirst={game.thirst}")

# Смена дня
game.reset_daily_ap()
print(f"   После смена дня: AP={game.ap}")

# Действие
game.consume_action("walk")
print(f"   После действия: AP={game.ap}, Hunger={game.hunger}, Thirst={game.thirst}")

# Урон
new_hp, log = process_damage(game, 10)
print(f"   После урона 10: HP={game.hp}, Лог='{log}'")

# Проверки
assert game.hp >= 1, f"HP должен быть >= 1"
assert game.ap >= 0, f"AP должен быть >= 0"
assert game.hunger >= 1, f"Hunger должен быть >= 1"
assert game.thirst >= 1, f"Thirst должен быть >= 1"

print("\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
print("=" * 60)