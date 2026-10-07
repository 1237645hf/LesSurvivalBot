# -*- coding: utf-8 -*-
"""
test_location_5_scout.py — Автотесты механики разведки логова Древнего/Мусорного слайма (L5).

Проверяет:
1. Окно 0: Первое прибытие при not intro_seen (текст, кнопки, переход в Окно 1).
2. Окно 1: Главный экран логова (динамический блок счётчиков, кнопки).
3. Окно 2 и 3: Ветка повадок (наблюдение, мысли охотника, инкремент счётчиков).
4. Окно 4 и 5: Ветка окрестностей (наблюдение, мысли охотника, инкремент счётчиков).
5. 5-дневный циклический шаблон RECON_LIMITS = [3, 2, 3, 2, 3].
6. Сохранение остатка визита при выходе в лагерь посреди дня (день не меняется).
7. Смена локального дня (recon_day += 1) строго при исчерпании лимита и выходе в лагерь.
8. Динамический остаток до капа 23 (не больше, чем осталось до 23).
9. Окно Финала при сумме 23 и три вариации (Вектор 1: повадки, Вектор 2: окрестности, Вектор 3: баланс).
10. Тестовые коллбэки финального окна.
11. Персистентность состояния в to_document / from_document.
"""
import pytest
from game_state import GameState
from story.locations.loc5_slug_pit import (
    handle_location_5_slug_pit,
    RECON_LIMITS,
    HABITS_EVENTS,
    SURROUNDINGS_EVENTS,
    get_recon_day,
    get_daily_scout_limit,
    is_scout_day_exhausted,
)


def test_scout_limits_and_events_structure():
    """Тест структур данных 5-дневного шаблона и 23 событий на ветку."""
    assert RECON_LIMITS == [3, 2, 3, 2, 3]

    assert len(HABITS_EVENTS) == 23
    assert len(SURROUNDINGS_EVENTS) == 23
    for entry in HABITS_EVENTS:
        assert "observation" in entry or "event" in entry
        assert "thought" in entry
    for entry in SURROUNDINGS_EVENTS:
        assert "observation" in entry or "event" in entry
        assert "thought" in entry


def test_scout_window_0_intro():
    """Тест Окна 0: первое прибытие."""
    game = GameState()
    uid = 101
    assert not game.intro_seen

    text, kb = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "Ты замираешь на сланцевом карнизе над тупиковой промоиной" in text
    assert len(text) <= 550
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "👁️ Начать наблюдения" in buttons
    assert "🏕️ Вернуться в лагерь" in buttons

    # Нажатие [🏕️ Вернуться в лагерь]
    t_camp, kb_camp = handle_location_5_slug_pit("l5_scout_leave_to_camp", game, uid)
    assert game.active_story_callback is None
    assert game.story_state is None

    # Повторный вход -> всё ещё Окно 0
    text_again, _ = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "Ты замираешь на сланцевом карнизе" in text_again

    # Нажатие [👁️ Начать наблюдения]
    text_hub, kb_hub = handle_location_5_slug_pit("l5_scout_start", game, uid)
    assert game.intro_seen is True
    # Попали в Окно 1
    assert "Ты осторожно наблюдаешь за дном яра из-за сланцевых выступов" in text_hub
    assert len(text_hub) <= 500


def test_scout_window_1_counters_display():
    """Тест динамического блока счётчиков в Окне 1."""
    game = GameState()
    uid = 102
    game.intro_seen = True

    # 1. Ничего не исследовано -> блок скрыт
    text0, _ = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "📊" not in text0

    # 2. Только повадки (habits > 0, surroundings == 0)
    game.habits_count = 5
    text_h, _ = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "📊 Повадки твари: 5/23" in text_h
    assert "📊 Окрестности" not in text_h

    # 3. Только окрестности (surroundings > 0, habits == 0)
    game.habits_count = 0
    game.surroundings_count = 4
    text_s, _ = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "📊 Окрестности: 4/23" in text_s
    assert "📊 Повадки твари" not in text_s

    # 4. Обе ветки начаты (habits > 0, surroundings > 0)
    game.habits_count = 3
    game.surroundings_count = 2
    text_both, _ = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "📊 Повадки твари: 3" in text_both
    assert "📊 Окрестности: 2" in text_both
    assert "Всего изучено: 5/23" in text_both


def test_scout_partial_visit_and_local_day_rollover():
    """Тест частичного визита (сохранение остатка) и смены локального дня только при полном расходе."""
    game = GameState()
    uid = 103
    game.intro_seen = True
    game.recon_day = 1
    game.day_researches_done = 0

    assert get_daily_scout_limit(game) == 3

    # Делаем 1 исследование повадок
    handle_location_5_slug_pit("l5_scout_habits_observe", game, uid)
    handle_location_5_slug_pit("l5_scout_habits_think", game, uid)
    assert game.habits_count == 1
    assert game.day_researches_done == 1

    # Уходим в лагерь посреди визита (сделано 1 из 3)
    handle_location_5_slug_pit("l5_scout_leave_to_camp", game, uid)
    # День цикла НЕ должен смениться!
    assert game.recon_day == 1
    assert game.day_researches_done == 1

    # Спим в лагере: цикл не зависит от календаря сна
    game.sleep_and_turn_day()
    assert game.recon_day == 1
    assert game.day_researches_done == 1

    # Возвращаемся в логово: хаб открыт, доделываем попытки
    _, kb_ret = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    btns_ret = [btn.text for row in kb_ret.inline_keyboard for btn in row]
    assert "👁️ Изучать повадки слайма" in btns_ret

    # Делаем 2-е исследование (окрестности)
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert game.surroundings_count == 1
    assert game.day_researches_done == 2

    # Делаем 3-е исследование (повадки) -> лимит дня 1 исчерпан (3/3)
    handle_location_5_slug_pit("l5_scout_habits_observe", game, uid)
    _, kb_done = handle_location_5_slug_pit("l5_scout_habits_think", game, uid)
    assert game.habits_count == 2
    assert game.day_researches_done == 3
    btns_done = [btn.text for row in kb_done.inline_keyboard for btn in row]
    assert "🏕️ Вернуться в лагерь" in btns_done
    assert "🔍 Продолжить наблюдать" not in btns_done

    # Возвращаемся в лагерь после полного исчерпания лимита -> смена дня цикла!
    handle_location_5_slug_pit("l5_scout_leave_to_camp", game, uid)
    assert game.recon_day == 2
    assert game.day_researches_done == 0

    # На день 2 лимит равен RECON_LIMITS[(2-1)%5] = 2
    assert get_daily_scout_limit(game) == 2


def test_scout_dynamic_remaining_to_cap():
    """Тест: лимит не может превышать остаток до 23."""
    game = GameState()
    game.intro_seen = True
    game.recon_day = 1  # Базовый лимит 3
    game.habits_count = 15
    game.surroundings_count = 7  # Сумма 22 (осталось ровно 1)
    game.day_researches_done = 0

    # До капа в 23 осталось ровно 1, поэтому доступно 1, а не 3
    assert get_daily_scout_limit(game) == 1


def test_scout_final_screen_vector_1_habits():
    """Тест Окна Финала: Вектор 1 (habits >= 16)."""
    game = GameState()
    uid = 104
    game.intro_seen = True
    game.habits_count = 16
    game.surroundings_count = 7  # Сумма 23

    text, kb = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "Ты досконально изучил каждую судорогу желе и круговорот мусора" in text
    assert len(text) <= 500
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "⚔️ Напасть на уязвимые зоны" in buttons
    assert "🏕️ Вернуться в лагерь" in buttons

    # Тестовый коллбэк
    t_act, kb_act = handle_location_5_slug_pit("l5_scout_final_attack_habits", game, uid)
    assert "уязвимые зоны Мусорного слайма" in t_act


def test_scout_final_screen_vector_2_surroundings():
    """Тест Окна Финала: Вектор 2 (surroundings >= 16)."""
    game = GameState()
    uid = 105
    game.intro_seen = True
    game.habits_count = 6
    game.surroundings_count = 17  # Сумма 23

    text, kb = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "Ты изучил каждый выступ яра, шаткие сланцевые пласты" in text
    assert len(text) <= 500
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "⚙️ Активировать ловушку окружения" in buttons
    assert "🏕️ Вернуться в лагерь" in buttons

    # Тестовый коллбэк
    t_act, kb_act = handle_location_5_slug_pit("l5_scout_final_trap_surroundings", game, uid)
    assert "ловушку окружения" in t_act


def test_scout_final_screen_vector_3_balanced():
    """Тест Окна Финала: Вектор 3 (сбалансированный путь, habits >= 9 and surroundings >= 9)."""
    game = GameState()
    uid = 106
    game.intro_seen = True
    game.habits_count = 12
    game.surroundings_count = 11  # Сумма 23

    text, kb = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "Ты собрал по крупицам и повадки чудовища, и особенности котловины яра" in text
    assert len(text) <= 500
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "⚔️ Атаковать с опорой на местность" in buttons
    assert "🪨 Заманить в каменный карман" in buttons
    assert "🏕️ Вернуться в лагерь" in buttons

    # Тестовые коллбэки
    t_act1, _ = handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    assert "с опорой на изученный рельеф местности" in t_act1

    t_act2, _ = handle_location_5_slug_pit("l5_scout_final_trap_pocket", game, uid)
    assert "каменный карман" in t_act2


def test_scout_persistence_to_from_document():
    """Тест персистентности полей разведки."""
    game = GameState()
    game.intro_seen = True
    game.habits_count = 12
    game.surroundings_count = 11
    game.recon_day = 8
    game.day_researches_done = 2

    doc = game.to_document()
    assert doc["intro_seen"] is True
    assert doc["habits_count"] == 12
    assert doc["surroundings_count"] == 11
    assert doc["current_day"] == 8
    assert doc["day_researches_done"] == 2

    loaded = GameState.from_document(doc)
    assert loaded.intro_seen is True
    assert loaded.habits_count == 12
    assert loaded.surroundings_count == 11
    assert loaded.recon_day == 8
    assert loaded.current_day == 8
    assert loaded.day_researches_done == 2


def test_habits_23_events_content_and_triggers():
    """Тест 23 событий повадок, мыслей, бонусов и триггера разблокировки крюка на 9-м шаге."""
    import crafts
    from modules.items import ITEMS

    assert len(HABITS_EVENTS) == 23
    assert "Костяной крюк на кожаной верёвке" in crafts.CRAFT_RECIPES
    assert "Костяной крюк на кожаной верёвке" in ITEMS

    # 1. Проверка первого шага (без бонуса) без окрестностей: 1 строка прогресса
    game = GameState()
    uid = 201
    game.intro_seen = True
    game.habits_count = 0
    game.surroundings_count = 0

    text_obs, _ = handle_location_5_slug_pit("l5_scout_habits_observe", game, uid)
    assert "Слайм лениво подминает под себя слой мокрой глины" in text_obs
    assert len(text_obs) <= 500

    text_think, _ = handle_location_5_slug_pit("l5_scout_habits_think", game, uid)
    assert "Вслепую ядро не достать" in text_think
    assert "📊 Понимание повадок: 1/23" in text_think
    assert "Всего изучено" not in text_think
    assert len(text_think) <= 500

    # 2. Проверка шага с окрестностями: 2 строки прогресса
    game.surroundings_count = 3
    # Шаг 2 (idx 1)
    handle_location_5_slug_pit("l5_scout_habits_observe", game, uid)
    text_think2, _ = handle_location_5_slug_pit("l5_scout_habits_think", game, uid)
    assert "📊 Понимание повадок: 2/23" in text_think2
    assert "Всего изучено: 5/23" in text_think2

    # 3. Шаг 3 (idx 2): наличие бонуса урона копьём
    handle_location_5_slug_pit("l5_scout_habits_observe", game, uid)
    text_think3, _ = handle_location_5_slug_pit("l5_scout_habits_think", game, uid)
    assert "+5% урона копьём по ядру" in text_think3

    # 4. Шаг 9 (idx 8): разблокировка крюка
    game.habits_count = 8
    assert not game.craft_bone_hook_unlocked
    assert "bone_hook_rope" not in game.unlocked_recipes

    handle_location_5_slug_pit("l5_scout_habits_observe", game, uid)
    text_think9, _ = handle_location_5_slug_pit("l5_scout_habits_think", game, uid)
    assert game.habits_count == 9
    assert game.craft_bone_hook_unlocked is True
    assert "bone_hook_rope" in game.unlocked_recipes
    assert "Костяной крюк на кожаной верёвке" in game.unlocked_crafts
    assert game.is_story_flag_set("craft_bone_hook_unlocked")
    assert "💡 Открыт рецепт: Костяной крюк на кожаной верёвке" in text_think9
    assert "📊 Понимание повадок: 9/23" in text_think9

    # 5. Персистентность рецептов и крюка
    doc = game.to_document()
    assert doc["craft_bone_hook_unlocked"] is True
    assert "bone_hook_rope" in doc["unlocked_recipes"]

    restored = GameState.from_document(doc)
    assert restored.craft_bone_hook_unlocked is True
    assert "bone_hook_rope" in restored.unlocked_recipes

