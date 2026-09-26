"""
tests/test_story_triggers_l1.py — Тесты сюжетных триггеров L1 и L1.5.

Проверяет:
1. day=2, 10 исследований с факелом на loc 1 → L1 нет.
2. day=3, 3 исследования с факелом → L1 нет; 4-е → L1 есть.
3. 2 исследования → сон → ещё 2 с новым факелом (счётчик не сброшен) при day>=3 → L1 есть.
4. torch_research_count уже 10, l1_started нет, day>=3, исследование с факелом → L1 всё равно стартует (>=).
5. Без факела счётчик L1 не растёт / сюжет не стартует.
6. L1.5 без l1_completed → нет; с completed и day+4 и 3 поисками → есть.
"""

import pytest
from game_state import GameState
from story.location_stories import (
    check_forest_research_story_trigger,
    handle_story,
)


def test_trigger_l1_day_2_ten_researches_with_torch_no_trigger():
    """day=2, 10 исследований с факелом на loc 1 → L1 не запускается (нужен day >= 3)."""
    game = GameState()
    game.day = 2
    game.equipment["hand_left"] = "Факел"

    for _ in range(10):
        event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=True)
        assert event is None
        assert log is None

    assert game.torch_research_count == 10
    assert not game.is_story_flag_set("l1_started")


def test_trigger_l1_day_3_activates_on_fourth_torch_research():
    """day=3, 3 исследования с факелом → L1 нет; 4-е → L1 запускается."""
    game = GameState()
    game.day = 3
    game.equipment["hand_left"] = "Факел"

    # Исследования 1..3: L1 нет
    for i in range(1, 4):
        event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=True)
        assert event is None
        assert log is None
        assert game.torch_research_count == i

    # 4-е исследование: триггер срабатывает
    event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=True)
    assert event == "forest_start"
    assert log is not None
    assert game.torch_research_count == 4


def test_trigger_l1_sleep_preserves_counter_and_fires_at_day_3():
    """2 исследования → сон → ещё 2 с новым факелом (счётчик сохранён) при day>=3 → L1 есть."""
    game = GameState()
    game.day = 2
    game.equipment["hand_left"] = "Факел"

    # 2 исследования на 2-й день
    for _ in range(2):
        event, _ = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=True)
        assert event is None
    assert game.torch_research_count == 2

    # Сон: наступает день 3, факел сгорает, но torch_research_count сохраняется
    game.sleep_and_turn_day()
    assert game.day == 3
    assert game.torch_research_count == 2
    assert game.equipment.get("hand_left") is None

    # Надеваем новый факел
    game.equipment["hand_left"] = "Факел"

    # 3-е суммарное исследование: L1 ещё нет
    event, _ = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=True)
    assert event is None
    assert game.torch_research_count == 3

    # 4-е суммарное исследование: L1 срабатывает!
    event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=True)
    assert event == "forest_start"
    assert game.torch_research_count == 4


def test_trigger_l1_counter_already_ten_still_triggers_with_greater_equal():
    """torch_research_count уже 10, l1_started нет, day>=3, исследование с факелом → L1 всё равно стартует (>=)."""
    game = GameState()
    game.day = 4
    game.torch_research_count = 10
    game.equipment["hand_left"] = "Факел"

    event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=True)
    assert event == "forest_start"
    assert game.torch_research_count == 11
    assert log is not None


def test_trigger_l1_without_torch_counter_does_not_grow_and_no_trigger():
    """Без факела счётчик L1 не растёт, сюжет не запускается даже при day>=3 и count>=4."""
    game = GameState()
    game.day = 5
    game.torch_research_count = 3

    # 5 исследований без факела
    for _ in range(5):
        event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
        assert event is None
        assert log is None

    # Счётчик не изменился
    assert game.torch_research_count == 3

    # Даже если искусственно установить счётчик >= 4:
    game.torch_research_count = 10
    event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert event is None
    assert game.torch_research_count == 10


def test_trigger_l1_5_chain_prerequisites():
    """L1.5 без l1_completed не стартует; с completed, day >= completed_day + 4 и 3 поисками → стартует."""
    game = GameState()
    game.day = 10

    # 1. Без l1_completed: ничего не происходит
    for _ in range(5):
        event, _ = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
        assert event is None
    assert game.l1_post_research_count == 0

    # 2. Выставляем l1_completed на 3-й день
    game.set_story_flag("l1_completed")
    game.story_flags["l1_completed_day"] = 3

    # Проверяем на 6-й день (< 3 + 4 = 7): не стартует
    game.day = 6
    event, _ = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert event is None
    assert game.l1_post_research_count == 0

    # Наступил 7-й день (день 3 + 4):
    game.day = 7

    # Поиск 1
    event, _ = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert event is None
    assert game.l1_post_research_count == 1

    # Поиск 2
    event, _ = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert event is None
    assert game.l1_post_research_count == 2

    # Поиск 3: срабатывает триггер l1_5_start
    event, _ = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert event == "l1_5_start"
    assert game.is_story_flag_set("l1_5_triggered")
