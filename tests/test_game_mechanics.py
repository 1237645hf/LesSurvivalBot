"""
tests/test_game_mechanics.py — Всестороннее тестирование игровых механик:
По 3 теста на каждый тип механики (всего 6 механик × 3 теста = 18 тестов):

1. Механика факела (3 теста)
2. Механика костра (3 теста)
3. Механика воды и бутылок/фляги (3 теста)
4. Механика кулинарии и готовки на костре (3 теста)
5. Механика расходников (3 теста)
6. Механика охотничьих ловушек (3 теста)
"""

import pytest
from game_state import GameState
from crafts import can_craft, do_craft, handle_craft, has_torch
from main import use_consumable
from modules.cooking import cook_item
from modules import traps, items


# ==============================================================================
# МЕХАНИКА 1: ФАКЕЛ (3 ТЕСТА)
# ==============================================================================

def test_1_1_torch_equip_gives_plus_one_ap_left_hand_only():
    """Тест 1.1: Факел экипируется строго в левую руку и даёт +1 AP пока в руке."""
    game = GameState()
    game.hp = 100
    base_ap = game.calculate_daily_ap()
    assert base_ap == 5  # Базовый AP при 100 HP без экипировки

    # В правую руку взять нельзя
    game.inventory["Факел"] = 1
    game.equipment["hand_left"] = None
    game.equipment["hand_right"] = None

    handle_craft("use_item_Факел", game, 1001)

    assert game.equipment.get("hand_left") == "Факел"
    assert game.equipment.get("hand_right") is None
    # Пока факел экипирован — AP увеличивается на 1
    assert game.calculate_daily_ap() == base_ap + 1
    assert game.inventory.get("Факел", 0) == 0


def test_1_2_torch_limit_one_per_character():
    """Тест 1.2: Лимит 1 факел на персонажа (нельзя скрафтить второй в инвентаре или в руке)."""
    game = GameState()
    game.inventory["Спички"] = 5
    game.inventory["Ветка"] = 5
    game.inventory.pop("Факел", None)
    game.equipment["hand_left"] = None

    # Крафтим 1-й факел — успешно
    assert can_craft(game, "Факел") is True
    ok, msg = do_craft(game, "Факел")
    assert ok is True
    assert has_torch(game) is True

    # Попытка скрафтить 2-й в инвентарь — запрет
    assert can_craft(game, "Факел") is False
    ok, msg = do_craft(game, "Факел")
    assert ok is False
    assert "уже есть факел" in msg.lower()

    # Экипируем факел в руку
    handle_craft("use_item_Факел", game, 1001)
    assert game.equipment["hand_left"] == "Факел"

    # Попытка скрафтить, пока факел в руке — тоже запрет
    assert can_craft(game, "Факел") is False
    ok, msg = do_craft(game, "Факел")
    assert ok is False


def test_1_3_torch_burns_at_night_without_extra_bonus():
    """Тест 1.3: Ночью факел сгорает, доп бонусов не даёт, а его +1 AP пропадает."""
    game = GameState()
    game.hp = 100
    game.campfire_active = True
    game.campfire_durability = 10
    game.equipment["hand_left"] = "Факел"
    game.equipment["hand"] = "Факел"
    game.ap = game.calculate_daily_ap()
    assert game.ap == 6  # 5 базовых + 1 от факела

    # Спим
    game.sleep_and_turn_day()

    # Факел сгорел и исчез
    assert game.equipment.get("hand_left") is None
    assert game.equipment.get("hand") is None
    assert "Факел" not in game.inventory

    # Утром AP рассчитывается БЕЗ факела (5 базовых)
    assert game.ap == 5


# ==============================================================================
# МЕХАНИКА 2: КОСТЁР (3 ТЕСТА)
# ==============================================================================

def test_2_1_campfire_light_costs_two_ap_hunger_thirst():
    """Тест 2.1: Розжиг костра тратит ровно 2 AP, 7 голода, 18 жажды и даёт 10/10 прочности."""
    game = GameState()
    game.ap = 5
    game.hunger = 50
    game.thirst = 50

    res = game.light_campfire()
    assert res["lit"] is True
    assert res["delta_ap"] == -2
    assert game.ap == 3
    assert game.hunger == 50 - 7
    assert game.thirst == 50 - 18
    assert game.campfire_active is True
    assert game.campfire_durability == 10
    assert game.campfire_max_durability == 10


def test_2_2_campfire_durability_loss_on_action_and_night():
    """Тест 2.2: Сгорание костра при действиях с AP (−1) и за ночь (−3)."""
    game = GameState()
    game.ap = 5
    game.light_campfire()
    assert game.campfire_durability == 10

    # Действие с ap_cost=1 снижает прочность на 1
    game.consume_action(action_type="search", ap_cost=1)
    assert game.campfire_durability == 9

    # Ночь снижает прочность на 3
    game.sleep_and_turn_day()
    assert game.campfire_durability == 6


def test_2_3_campfire_morning_cold_penalty_when_extinguished():
    """Тест 2.3: Штраф −1 AP утром от холода, если костёр потух к утру."""
    game = GameState()
    game.hp = 100
    game.campfire_active = False
    game.campfire_durability = 0

    # Спим без костра
    game.sleep_and_turn_day()

    # Базовое AP = 5, но из-за холода без костра: 5 - 1 = 4 AP
    assert game.ap == 4


# ==============================================================================
# МЕХАНИКА 3: ВОДА, БУТЫЛКИ И СЛОТ ФЛЯГИ (3 ТЕСТА)
# ==============================================================================

def test_3_1_bottle_equip_flask_slot():
    """Тест 3.1: Экипировка «Бутылка воды» в слот flask на 20 глотков."""
    game = GameState()
    assert game.inventory.get("Бутылка воды") == 2
    assert game.equipment.get("flask") is None

    # Экипируем одну бутылку
    game.inventory["Бутылка воды"] -= 1
    game.equipment["flask"] = "Бутылка воды"
    game.flask_water = 20

    assert game.equipment["flask"] == "Бутылка воды"
    assert game.flask_water == 20
    assert game.inventory["Бутылка воды"] == 1


def test_3_2_drink_from_flask_restores_thirst():
    """Тест 3.2: Питье из фляги восстанавливает жажду и тратит глоток."""
    game = GameState()
    game.equipment["flask"] = "Бутылка воды"
    game.flask_water = 20
    game.thirst = 30

    # Делаем 1 глоток
    game.flask_water -= 1
    game.thirst = min(100, game.thirst + 15)

    assert game.flask_water == 19
    assert game.thirst == 45


def test_3_3_bottle_empty_leaves_empty_bottle_and_logs_name():
    """Тест 3.3: Опустошение бутылки в 0: слот освобождается, даётся пустая бутылка, лог содержит имя ёмкости."""
    game = GameState()
    game.equipment["flask"] = "Бутылка воды"
    game.flask_water = 1

    # Последний глоток
    game.flask_water -= 1
    container_name = game.equipment.get("flask") or "Бутылка воды"
    game.equipment["flask"] = None
    game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1
    game.add_log(f"Ёмкость «{container_name}» опустошена! В инвентаре осталась пустая бутылка.")

    assert game.equipment.get("flask") is None
    assert game.inventory.get("Пустая бутылка") == 1
    assert any("Ёмкость «Бутылка воды» опустошена!" in log for log in game.event_log)


# ==============================================================================
# МЕХАНИКА 4: КУЛИНАРИЯ И ГОТОВКА НА КОСТРЕ (3 ТЕСТА)
# ==============================================================================

def test_4_1_cooking_without_water_requires_bark():
    """Тест 4.1: Сухая обжарка на коре (Печёные ягоды): расход коры и ягоды, без воды."""
    game = GameState()
    game.inventory = {
        "Кусок коры": 1,
        "Лесная ягода": 1,
    }
    game.flask_water = 0

    ok, msg = cook_item(game, "cook_roast_berries")
    assert ok is True
    assert "Печёные ягоды готово" in msg
    assert game.inventory.get("Печёные ягоды") == 1
    assert "Кусок коры" not in game.inventory
    assert "Лесная ягода" not in game.inventory


def test_4_2_cooking_with_single_flask_water():
    """Тест 4.2: Готовка с водой (Грибная похлёбка — 2 воды): списание из надетой фляги."""
    game = GameState()
    game.equipment["flask"] = "Бутылка воды"
    game.flask_water = 10
    game.inventory = {
        "Кусок коры": 1,
        "Лесной гриб": 1,
    }

    ok, msg = cook_item(game, "cook_mushroom_soup")
    assert ok is True
    assert "Грибная похлёбка готово" in msg
    assert game.flask_water == 8
    assert game.inventory.get("Грибная похлёбка") == 1


def test_4_3_cooking_multi_container_water_consumption():
    """Тест 4.3: Забор воды из нескольких ёмкостей (во фляге 1 вода, рецепт требует 3: фляга опустошается, остаток берётся из инвентаря)."""
    game = GameState()
    game.equipment["flask"] = "Бутылка воды"
    game.flask_water = 1  # Только 1 деление во фляге
    game.inventory = {
        "Кусок коры": 1,
        "Сырое мясо": 1,
        "Лесная ягода": 1,
        "Бутылка воды": 1,  # Вторая полная бутылка в инвентаре (20 делений)
    }

    # Рецепт "cook_hunter_soup" требует 3 деления воды
    ok, msg = cook_item(game, "cook_hunter_soup")
    assert ok is True
    assert "Охотничья похлёбка готово" in msg

    # 1 деление взято из фляги (она опустошилась -> дала пустую бутылку)
    # 2 оставшихся взяты из инвентарной бутылки -> она надета в слот flask с остатком 18/20
    assert game.inventory.get("Пустая бутылка") == 1
    assert "Бутылка воды" not in game.inventory  # была 1, теперь она надета на пояс
    assert game.equipment.get("flask") == "Бутылка воды"
    assert game.flask_water == 18
    assert game.inventory.get("Охотничья похлёбка") == 1


# ==============================================================================
# МЕХАНИКА 5: РАСХОДНИКИ (3 ТЕСТА)
# ==============================================================================

def test_5_1_consumables_food_restores_hunger():
    """Тест 5.1: Использование Сухпая восстанавливает голод и списывает предмет."""
    game = GameState()
    game.hunger = 20
    game.inventory = {"Сухпай": 2}

    res = use_consumable("Сухпай", game)
    assert res is not None
    assert game.hunger > 20
    assert game.inventory.get("Сухпай") == 1


def test_5_2_consumables_potions_restores_hp():
    """Тест 5.2: Зелье здоровья восстанавливает HP."""
    game = GameState()
    game.hp = 60
    game.inventory = {"Зелье здоровья": 1}

    res = use_consumable("Зелье здоровья", game)
    assert res is not None
    assert game.hp == 85  # +25 HP
    assert "Зелье здоровья" not in game.inventory


def test_5_3_consumables_berries_and_mushrooms():
    """Тест 5.3: Региональные ягоды и грибы восстанавливают голод."""
    game = GameState()
    game.hunger = 10
    game.inventory = {"Красная ягода": 1, "Пещерный гриб": 1}

    use_consumable("Красная ягода", game)
    assert game.hunger > 10
    assert "Красная ягода" not in game.inventory

    h_after_berry = game.hunger
    use_consumable("Пещерный гриб", game)
    assert game.hunger > h_after_berry
    assert "Пещерный гриб" not in game.inventory


# ==============================================================================
# МЕХАНИКА 6: ОХОТНИЧЬИ ЛОВУШКИ (3 ТЕСТА)
# ==============================================================================

def test_6_1_traps_placement_limit_one_per_location():
    """Тест 6.1: Установка ловушек — не более одной активной на локацию."""
    game = GameState()
    game.story_flags["traps_unlocked"] = True

    # Первая установка на L2
    trap1 = traps.place_trap(game, 2)
    assert trap1 is not None
    assert trap1["is_active"] is True

    # Повторная попытка на ту же L2 — отказ
    trap2 = traps.place_trap(game, 2)
    assert trap2 is None


def test_6_2_traps_probabilities_empty_broken_loot():
    """Тест 6.2: Проверка трёх исходов ловушки: 40% пусто, 20% сломалась, 40% добыча."""
    import random
    game = GameState()
    game.story_flags["traps_unlocked"] = True
    traps.place_trap(game, 1)

    # 1. Ролл <= 40 -> пустая (цела, но без добычи)
    orig_randint = random.randint
    random.randint = lambda a, b: 25
    res = traps.roll_trap_roll(game, 1)
    assert res["is_broken"] is False
    assert res["is_active"] is True
    assert res["pending_animal"] is None

    # 2. Ролл 41-60 -> ломается
    random.randint = lambda a, b: 50
    res = traps.roll_trap_roll(game, 1)
    assert res["is_broken"] is True
    assert res["is_active"] is False

    # 3. Ролл > 60 -> успех (добыча поймана)
    game.traps[1]["is_active"] = True
    game.traps[1]["is_broken"] = False
    random.randint = lambda a, b: 85
    res = traps.roll_trap_roll(game, 1)
    assert res["is_broken"] is False
    assert res["pending_animal"] == "Заяц"
    assert res["pending_loot"] == {"Сырое мясо": 1}

    random.randint = orig_randint


def test_6_3_traps_rollover_loot_added_to_inventory():
    """Тест 6.3: Утренний ролловер ловушек передаёт добычу в инвентарь."""
    game = GameState()
    game.story_flags["traps_unlocked"] = True
    traps.place_trap(game, 1)
    game.traps[1]["is_active"] = True
    game.traps[1]["pending_animal"] = "Заяц"
    game.traps[1]["pending_loot"] = {"Сырое мясо": 1}

    loot = traps.get_trap_loot(game, 1)
    assert loot is not None
    assert loot["animal"] == "Заяц"
    assert loot["loot"] == {"Сырое мясо": 1}

    traps.apply_trap_loot_to_inventory(game, loot["loot"])
    assert game.inventory.get("Сырое мясо") == 1
