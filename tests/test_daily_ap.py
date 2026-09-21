"""Тест для проверки calculate_daily_ap."""
from game_state import GameState

for hp in [55, 45, 35, 15, 5]:
    g = GameState()
    g.hp = hp
    g.ap = 5
    print(f"HP={hp} -> Daily AP: {g.calculate_daily_ap()}")