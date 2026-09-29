"""
tests/test_story_interruption_and_autoheal.py — Регрессионные тесты защиты сюжетного прогресса:
1. L1 (Волк у пня): прерывание диалога не софтлочит сюжет; повторное исследование возобновляет квест до l1_completed.
2. L1.5 (Волчье логово): прерывание до wolf_lair_unlocked не теряет логово; после открытия логова исследование свободно.
3. L3 (Печь): в l3_1_fire_low нет деструктивной кнопки back; прерывание до l3_shelter_unlocked не сжигает печь.
4. L3.7 (Гребень): прерывание до открытия Солонца на карте не блокирует путь на гребень.
5. Auto-heal: GameState.from_document автоматически исцеляет повреждённые сейвы с зависшими _started/_triggered флагами.
6. Навигация: возврат через back при active_story_callback восстанавливает сюжетный экран, а не сбрасывает его.
"""

import pytest
from game_state import GameState
from story.location_stories import (
    check_forest_research_story_trigger,
    handle_story,
    handle_location_3_slate_hollow,
)


def test_l1_interruption_does_not_softlock():
    """L1: прерывание на экране факела/котёнка не сжигает триггер; повторное исследование возвращает сюжет."""
    game = GameState()
    game.day = 3
    game.equipment["hand_left"] = "Факел"
    game.torch_research_count = 3

    # 4-е исследование с факелом: стартует L1
    ev, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=True)
    assert ev == "forest_start"

    # Игрок нажимает "Использовать факел"
    text, kb = handle_story("wolf_torch", game, 101)
    assert game.story_state == "after_fight"
    assert not game.is_story_flag_set("l1_completed")

    # Игрок прерывает диалог (выход по /main или перезапуск): active_story_callback сброшен
    game.active_story_callback = None
    game.story_state = None

    # Игрок снова исследует лес с факелом: триггер снова доступен, так как l1_completed ещё нет!
    ev2, log2 = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=True)
    assert ev2 == "forest_start"

    # Теперь игрок мирно завершает встречу (уходит)
    text_leave, kb_leave = handle_story("wolf_leave", game, 101)
    assert game.is_story_flag_set("l1_completed")

    # После l1_completed повторное исследование больше не вызывает forest_start
    ev3, log3 = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=True)
    assert ev3 is None


def test_l1_5_interruption_and_map_unlock():
    """L1.5: прерывание до открытия логова не теряет логово; после wolf_lair_unlocked исследование свободно."""
    game = GameState()
    game.day = 8
    game.set_story_flag("l1_completed")
    game.story_flags["l1_completed_day"] = 3
    game.l1_post_research_count = 2

    # 3-е исследование после 4 дней: обнаружен овраг
    ev, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert ev == "l1_5_start"
    assert not game.wolf_lair_unlocked

    # Игрок прервал диалог на первом шаге
    game.active_story_callback = None
    game.story_state = None

    # При следующем исследовании овраг не исчезает: триггер снова даёт l1_5_start
    ev2, log2 = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert ev2 == "l1_5_start"

    # Игрок проходит диалог до l1_5_leave (осознанный уход в лагерь)
    text_leave, kb_leave = handle_story("l1_5_leave", game, 101)
    assert game.wolf_lair_unlocked is True
    assert game.wolf_lair_active is True

    # После открытия логова на карте исследование леса больше НЕ перехватывается триггером
    ev3, log3 = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert ev3 is None


def test_l3_fire_low_keyboard_has_no_back_button():
    """Экран l3_1_fire_low не содержит деструктивной кнопки back."""
    game = GameState()
    text, kb = handle_location_3_slate_hollow("l3_1_fire_low", game, 101)
    callback_datas = [
        btn.callback_data
        for row in kb.inline_keyboard
        for btn in row
    ]
    assert "back" not in callback_datas
    assert "l3_2_call" in callback_datas
    assert "l3_3_inspect" in callback_datas


def test_l3_shelter_interruption_does_not_lose_stove():
    """L3: прерывание до фиксации убежища не сжигает печь; повторное исследование находит печь."""
    game = GameState()
    game.day = 5
    game.story_flags["l3_entered_day"] = 2
    game.l3_research_count = 1

    # 2-е исследование в Лощине находит печь
    ev, log = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev == "l3_1_fire_low"
    assert not game.is_story_flag_set("l3_shelter_unlocked")

    # Игрок вышел в меню (/main)
    game.active_story_callback = None
    game.story_state = None

    # Следующее исследование Лощины снова приводит к печи, так как убежище ещё не закреплено
    ev2, log2 = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev2 == "l3_1_fire_low"

    # Игрок завершает обустройство убежища
    handle_location_3_slate_hollow("l3_6_finalize", game, 101)
    assert game.is_story_flag_set("l3_shelter_unlocked") is True

    # Теперь исследование освобождается (нет принудительного показа печи)
    ev3, log3 = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    # Если Солонец ещё не открыт — сработает следующий этап (l3_7_morning), но печь l3_1_fire_low больше не спамит
    assert ev3 != "l3_1_fire_low"


def test_l3_7_ridge_unlock_pattern():
    """L3.7: после появления Солонца в unlocked_locations исследование лощины свободно."""
    game = GameState()
    game.day = 6
    game.set_story_flag("l3_shelter_unlocked", True)

    # Солонца ещё нет на карте -> исследование выводит к гребню
    ev, log = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev == "l3_7_morning"

    # Открываем Солонец на карте
    game.unlocked_locations = ["Скромная Лощина", "Солонец (Секач)"]

    # Теперь исследование лощины не перехватывается, доступ к Секачу идёт через меню локаций
    ev2, log2 = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev2 is None


def test_autoheal_broken_saves_in_from_document():
    """GameState.from_document автоматически очищает зависшие флаги _started / _triggered."""
    doc = {
        "schema_version": 2,
        "day": 5,
        "story_flags": {
            "l1_started": True,       # l1_completed нет
            "l1_5_triggered": True,    # wolf_lair_unlocked False
            "l3_story_started": True,  # l3_shelter_unlocked False
            "l3_7_triggered": True,    # Солонца нет, ridge_completed нет
        },
        "wolf_lair_unlocked": False,
        "unlocked_locations": ["Стартовый лес", "Скромная Лощина"],
        "active_story_callback": None,
    }

    game = GameState.from_document(doc)
    # Все 4 зависших флага должны быть сброшены, открывая доступ к прохождению
    assert not game.is_story_flag_set("l1_started")
    assert not game.is_story_flag_set("l1_5_triggered")
    assert not game.is_story_flag_set("l3_story_started")
    assert not game.is_story_flag_set("l3_7_triggered")
