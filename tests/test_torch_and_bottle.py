"""
tests/test_torch_and_bottle.py — Тесты механики факела, сна и бутылки воды.
"""

from game_state import GameState
from crafts import can_craft, do_craft, handle_craft


def test_torch_limit_and_equip_left_hand_only():
    game = GameState()
    # Очищаем инвентарь от факелов
    game.inventory.pop("Факел", None)
    game.equipment["hand_left"] = None
    game.equipment["hand_right"] = None

    # Добавляем ингредиенты для факела
    game.inventory["Спички"] = 2
    game.inventory["Ветка"] = 2

    # Крафтим 1-й факел
    assert can_craft(game, "Факел") is True
    ok, msg = do_craft(game, "Факел")
    assert ok is True
    assert game.inventory.get("Факел") == 1

    # Пытаемся скрафтить 2-й факел — должно быть запрещено!
    assert can_craft(game, "Факел") is False
    ok, msg = do_craft(game, "Факел")
    assert ok is False
    assert "уже есть факел" in msg.lower()

    # Экипируем факел — должен встать строго в левую руку
    handle_craft("use_item_Факел", game, 123)
    assert game.equipment.get("hand_left") == "Факел"
    assert game.equipment.get("hand_right") is None
    assert game.inventory.get("Факел", 0) == 0

    # Проверяем, что даже когда факел в руке, скрафтить второй нельзя
    assert can_craft(game, "Факел") is False


def test_torch_sleep_ap_bonus_and_burn_out():
    game = GameState()
    game.hp = 100
    game.campfire_active = True
    game.campfire_durability = 10
    game.equipment["hand_left"] = "Факел"
    game.equipment["hand"] = "Факел"

    # Спим
    game.sleep_and_turn_day()

    # Факел сгорел
    assert game.equipment.get("hand_left") is None
    assert game.equipment.get("hand") is None
    assert "Факел" not in game.inventory

    # Утром факел сгорел, поэтому его +1 AP пропадает: базовое AP = 5
    assert game.ap == 5


def test_campfire_lighting_cost():
    game = GameState()
    game.ap = 5
    game.hunger = 50
    game.thirst = 50

    res = game.light_campfire()
    assert res["lit"] is True
    assert res["delta_ap"] == -2
    assert game.ap == 3
    assert game.campfire_active is True
    assert game.campfire_durability == 10


def test_water_bottle_and_flask_mechanics():
    game = GameState()
    # Стартовый инвентарь нового игрока
    assert game.inventory.get("Бутылка воды") == 2
    assert game.equipment.get("flask") is None

    # Экипируем бутылку
    game.inventory["Бутылка воды"] -= 1
    game.equipment["flask"] = "Бутылка воды"
    game.flask_water = 20

    assert game.inventory.get("Бутылка воды") == 1
    assert game.equipment.get("flask") == "Бутылка воды"
    assert game.flask_water == 20

    # Делаем 20 глотков
    game.thirst = 50
    for _ in range(20):
        game.flask_water -= 1

    assert game.flask_water == 0
    # Когда опустела: слот освобождается, появляется пустая бутылка
    game.equipment["flask"] = None
    game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1

    assert game.equipment.get("flask") is None
    assert game.inventory.get("Пустая бутылка") == 1
