"""
tests/test_location_2_prologue_and_thorns_trigger.py — Тесты нового порядка сюжета L2:
1. При первом переходе на Ручей запускается пролог «Стук у воды» (L2.1).
2. Выборы в прологе: срезание ремня с получением рюкзака, коробочки и записки.
3. Пролог завершается с фиксацией дня (l2_prologue_completed_day).
4. Обычные исследования ручья дают ресурсы и не триггерят терновник сразу.
5. На 5-й день после завершения пролога на 3-е исследование ручья запускается Стена терновника.
"""

import pytest
from game_state import GameState
from story.location_stories import (
    handle_location_2_ruchey,
    check_forest_research_story_trigger,
)


def test_l2_prologue_starts_on_first_entrance():
    """При первом входе на Ручей открывается пролог 'Стук у воды' (а не терновник)."""
    game = GameState()
    game.current_location = "Ручей"

    text, kb = handle_location_2_ruchey("location_enter_2", game, 101)
    assert "🌊 СТУК У ВОДЫ" in text
    cb_datas = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "l2_1a" in cb_datas
    assert "l2_2" in cb_datas
    assert "l2_1b" in cb_datas


def test_l2_prologue_path_to_backpack_and_items():
    """Прохождение пролога: прислушаться -> осмотреть рюкзак -> срезать -> осмотр -> коробочка и записка."""
    game = GameState()
    game.day = 5

    # 1. Прислушаться
    text_1a, kb_1a = handle_location_2_ruchey("l2_1a", game, 101)
    assert game.is_story_flag_set("noticed_snakes_leaving")
    assert "Все до одной" in text_1a

    # 2. Подойти к кустам
    text_2, kb_2 = handle_location_2_ruchey("l2_2", game, 101)
    assert "красная заплатка" in text_2

    # 3. Сначала проверить (без питомца)
    text_3a, kb_3a = handle_location_2_ruchey("l2_3a", game, 101)
    assert "Останки лежат под подмытым берегом" in text_3a

    # 4. Вода прибывает
    text_4, kb_4 = handle_location_2_ruchey("l2_4", game, 101)
    assert "Теперь понятно, почему змеи так торопились на берег" in text_4

    # 5. Срезать ремень
    text_5a, kb_5a = handle_location_2_ruchey("l2_5a", game, 101)
    assert game.inventory.get("Рюкзак с красной заплаткой") == 1
    assert game.is_story_flag_set("bag_obtained")

    # 6. Хозяин ручья
    text_6, kb_6 = handle_location_2_ruchey("l2_6", game, 101)
    assert "ХОЗЯИН РУЧЬЯ" in text_6
    assert kb_6.inline_keyboard[0][0].callback_data == "l2_7"

    # 7. Осмотр рюкзака: получение коробочки и записки
    text_7, kb_7 = handle_location_2_ruchey("l2_7", game, 101)
    assert game.inventory.get("Плоская металлическая коробочка") == 1
    assert game.inventory.get("Записка с наброском местности") == 1

    # 8. Финал пролога
    text_7a, kb_7a = handle_location_2_ruchey("l2_7a", game, 101)
    assert game.is_story_flag_set("l2_prologue_completed")
    assert game.story_flags["l2_prologue_completed_day"] == 5


def test_l2_thorns_trigger_after_5_days_and_3_researches():
    """Стена терновника триггерится только через 5 дней на 3-е исследование ручья."""
    game = GameState()
    game.set_story_flag("l2_prologue_completed")
    game.story_flags["l2_prologue_completed_day"] = 5
    game.day = 8  # Прошло только 3 дня (< 5)

    # Исследования на 8 день не триггерят
    for _ in range(5):
        event, _ = check_forest_research_story_trigger(game, loc_id=2, torch_equipped=False)
        assert event is None

    # Наступает 10-й день (5 + 5)
    game.day = 10

    # 1-е исследование
    ev1, _ = check_forest_research_story_trigger(game, loc_id=2, torch_equipped=False)
    assert ev1 is None
    assert game.story_flags["l2_research_count"] == 1

    # 2-е исследование
    ev2, _ = check_forest_research_story_trigger(game, loc_id=2, torch_equipped=False)
    assert ev2 is None
    assert game.story_flags["l2_research_count"] == 2

    # 3-е исследование: запуск Стены терновника!
    ev3, log3 = check_forest_research_story_trigger(game, loc_id=2, torch_equipped=False)
    assert ev3 == "l2_thorns_approach"
    assert "терновника" in log3
    assert game.is_story_flag_set("l2_thorns_discovered")
