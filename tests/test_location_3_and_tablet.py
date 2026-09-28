"""
tests/test_location_3_and_tablet.py — Тесты механик Локации 3 (Скромная Лощина),
печи, сланцевой посуды, древесного угля и каменной плиты с записями.
"""

import pytest
from game_state import GameState
from crafts import do_craft
from modules.cooking import cook_item
from main import use_consumable, format_tablet_notes_text
from story.location_stories import (
    handle_location_2_ruchey,
    handle_location_3_slate_hollow,
    check_forest_research_story_trigger,
)
from services.database import (
    get_tablet_notes,
    save_tablet_note,
    DEFAULT_TABLET_NOTES,
)


def test_stove_properties_and_rekindle():
    """Тест свойств печи: макс. прочность 30, розжиг при 0 за 2 AP."""
    game = GameState()
    game.set_story_flag("l3_shelter_unlocked", True)
    assert game.is_stove is True

    # Прочность печи до 30
    game.campfire_durability = 0
    game.ap = 2
    game.hunger = 50
    game.thirst = 50

    ok, msg = game.rekindle_stove()
    assert ok is True
    assert game.campfire_durability == 1
    assert game.campfire_active is True
    assert game.ap == 0
    assert game.hunger == 43  # -7
    assert game.thirst == 32  # -18


def test_charcoal_and_slate_crafts():
    """Тест крафтов L3: Древесный уголь (х3), Сланцевый слиток, Сланцевая тарелка (х2), Сланцевый пенал."""
    game = GameState()
    game.inventory = {
        "Ветка": 5,
        "Кусок коры": 2,
        "Сланцевая пластина": 2,
        "Глина": 2,
        "Мох": 2,
    }

    # 1. Крафт древесного угля: 5 веток + 2 коры -> 3 угля
    ok, res = do_craft(game, "Древесный уголь")
    assert ok is True
    assert game.inventory.get("Древесный уголь") == 3
    assert game.inventory.get("Ветка", 0) == 0
    assert game.inventory.get("Кусок коры", 0) == 0

    # 2. Крафт сланцевого слитка: 2 пластины + 2 глины -> 1 слиток
    ok, res = do_craft(game, "Сланцевый слиток")
    assert ok is True
    assert game.inventory.get("Сланцевый слиток") == 1
    assert game.inventory.get("Сланцевая пластина", 0) == 0
    assert game.inventory.get("Глина", 0) == 0

    # 3. Крафт сланцевой тарелки: 1 слиток -> 2 тарелки
    ok, res = do_craft(game, "Сланцевая тарелка")
    assert ok is True
    assert game.inventory.get("Сланцевая тарелка") == 2
    assert game.inventory.get("Сланцевый слиток", 0) == 0


def test_reusable_slate_plate_cooking_and_eating():
    """Тест многоразовой сланцевой тарелки при готовке и поедании."""
    game = GameState()
    game.campfire_active = True
    game.campfire_durability = 10
    game.inventory = {
        "Сланцевая тарелка": 1,
        "Сырое мясо": 1,
    }
    # При готовке вместо коры используется тарелка
    ok, msg = cook_item(game, "cook_roast_meat")
    assert ok is True
    dish_name = "Мясо на коре (🍽️)"
    assert game.inventory.get(dish_name) == 1
    assert game.inventory.get("Сланцевая тарелка", 0) == 0

    # Поедание блюда с тарелкой возвращает Сланцевую тарелку в инвентарь
    game.hunger = 40
    use_consumable(dish_name, game)
    assert game.inventory.get("Сланцевая тарелка") == 1
    assert game.inventory.get(dish_name, 0) == 0
    assert any("тарелка снова свободна" in log_msg for log_msg in game.log)


def test_l2_dam_puzzle_karma():
    """Тест кармы L2: решение за 1 или 2 попытки даёт +2 к наблюдательности."""
    game = GameState()
    game.l2_puzzle_attempt = 1  # 2-я попытка (<= 1 ошибок)
    handle_location_2_ruchey("l2_bridge_activated", game, 101)
    assert game.narrative_karma.get("observation", 0) == 2

    # Если решено за 3 попытки (2 ошибки), дополнительная наблюдательность не даётся
    game2 = GameState()
    game2.l2_puzzle_attempt = 2  # 3-я попытка
    handle_location_2_ruchey("l2_bridge_activated", game2, 102)
    assert game2.narrative_karma.get("observation", 0) == 0


def test_l3_research_story_trigger():
    """Тест триггера L3: срабатывает со 2-го дня пребывания на 2-е исследование."""
    game = GameState()
    game.current_location = "Скромная Лощина"
    game.day = 1
    # Первый день на локации — триггер не должен сработать
    ev, log = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev is None

    # Переход на следующий день (день 2 > дня входа 1)
    game.day = 2
    # 1-е исследование дня 2
    ev1, _ = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev1 is None

    # 2-е исследование дня 2 -> запуск сюжета L3!
    ev2, log2 = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev2 == "l3_1_fire_low"
    assert game.is_story_flag_set("l3_story_started") is True


def test_l3_story_progression_and_stove_unlock():
    """Тест прохождения сюжета L3 от L3.1 до обустройства лагеря."""
    game = GameState()
    game.current_location = "Скромная Лощина"

    # L3.1: обнаружение
    t, kb = handle_location_3_slate_hollow("l3_1_fire_low", game, 101)
    assert "тлеют угли" in t

    # L3.2: зов
    t, kb = handle_location_3_slate_hollow("l3_2_call", game, 101)
    assert "Если пришёл — грейся" in t

    # L3.3: убежище
    t, kb = handle_location_3_slate_hollow("l3_3_inspect", game, 101)
    assert "Крыша течёт справа" in t

    # L3.4: надписи (+1 наблюдательность)
    t, kb = handle_location_3_slate_hollow("l3_4_writings", game, 101)
    assert game.narrative_karma.get("observation", 0) == 1

    # L3.5: обжиг заготовки
    t, kb = handle_location_3_slate_hollow("l3_5_finish_bake", game, 101)
    assert game.inventory.get("Сланцевый слиток") == 1

    # L3.6: остаёмся здесь и финализируем убежище
    t, kb = handle_location_3_slate_hollow("l3_6_finalize", game, 101)
    assert game.is_story_flag_set("l3_shelter_unlocked") is True
    assert game.is_stove is True
    assert game.campfire_active is True
    assert game.campfire_durability >= 15


def test_stone_tablet_pagination_and_storage():
    """Тест пагинации каменной плиты и сохранения записей."""
    notes = get_tablet_notes()
    assert len(notes) >= 4  # 4 каноничные надписи

    # Проверка текста пагинации
    text, total_pages = format_tablet_notes_text(notes, page=1, page_size=5)
    assert "КАМЕННАЯ ПЛИТА У ПЕЧИ" in text
    assert "Если пришёл — грейся" in text

    # Сохранение новой записи
    ok = save_tablet_note(uid=999, author="Бродяга Тестер", text="Новая метка на плите")
    assert ok is True

    updated_notes = get_tablet_notes()
    assert any(n.get("text") == "Новая метка на плите" for n in updated_notes)
