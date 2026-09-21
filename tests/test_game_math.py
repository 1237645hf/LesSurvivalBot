"""
test_game_math.py — Тесты для game_math.py.
Проверяет процесс урона при низком HP и конвертации в ресурсы.
"""

from game_math import process_damage, get_resource_multiplier


def test_process_damage_at_low_hp():
    """Тест: HP = 15, raw_damage = 50, hunger = 40, thirst = 30."""
    # Создаём mock-объект GameState
    class MockGame:
        def __init__(self):
            self.hp = 15
            self.hunger = 40
            self.thirst = 30
    
    game = MockGame()
    
    print("=" * 60)
    print("Тест: process_damage при HP = 15, raw_damage = 50")
    print("=" * 60)
    print(f"Исходное состояние:")
    print(f"  HP: {game.hp}")
    print(f"  Голод: {game.hunger}")
    print(f"  Жажда: {game.thirst}")
    print()
    
    # Применяем урон
    new_hp, damage_log = process_damage(game, raw_damage=50)
    
    print(f"Результат после урона:")
    print(f"  Новый HP: {new_hp}")
    print(f"  Лог: {damage_log}")
    print()
    
    # Проверяем коэффициенты
    hunger_mult = get_resource_multiplier(game, "hunger")
    thirst_mult = get_resource_multiplier(game, "thirst")
    
    print(f"Коэффициенты при HP={game.hp}:")
    print(f"  Голод: x{hunger_mult}")
    print(f"  Жажда: x{thirst_mult}")
    print()
    
    # Выводим итоговое состояние
    print(f"Итоговое состояние:")
    print(f"  HP: {new_hp}")
    print(f"  Голод: {game.hunger}")
    print(f"  Жажда: {game.thirst}")
    print("=" * 60)


if __name__ == "__main__":
    test_process_damage_at_low_hp()
