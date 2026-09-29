"""
tests/test_location_4_story.py — Тесты сюжета локации 4 (Просека Охотников) и бонусного лута.
"""

import pytest
from game_state import GameState
from modules.finds import BONUS_FINDS, _roll_bonus, roll_find
from story.location_stories import handle_location_4_hunters_glade


def test_location_4_bonus_find_sticks():
    """В таблице бонусов L4 присутствует ветка с шансом 30% и количеством 1-2 шт."""
    table = BONUS_FINDS[4]
    stick_entry = next((e for e in table if e["item"] == "Ветка"), None)
    assert stick_entry is not None, "Ветка отсутствует в BONUS_FINDS[4]"
    assert stick_entry["chance"] == 30
    assert stick_entry.get("count_range") == (1, 2)

    # Проверка работы _roll_bonus с count_range
    rolled_counts = set()
    single_stick_table = [stick_entry]
    for _ in range(100):
        res = _roll_bonus(single_stick_table)
        if res:
            rolled_counts.add(len(res))
            assert all(x == "Ветка" for x in res)
    # За 100 итераций при 30% шансе должны выпасть и 1, и 2 шт.
    assert 1 in rolled_counts
    assert 2 in rolled_counts
    assert not any(c > 2 or c < 1 for c in rolled_counts)


def test_location_4_window_1_only_two_buttons():
    """Окно 1 (Вход) должно содержать ровно 2 кнопки: 'Идти по верёвке' и 'Прямо на звук'."""
    game = GameState()
    text, kb = handle_location_4_hunters_glade("l4_1_entry", game, 12345)

    assert "Ты осторожно раздвигаешь колючие лапы елей" in text
    assert len(text) <= 500, f"Текст окна превышает лимит: {len(text)}"
    assert game.active_story_callback == "l4_1_entry"
    assert game.story_state == "l4_1_entry"

    buttons = kb.inline_keyboard
    all_btns = [b for row in buttons for b in row]
    assert len(all_btns) == 2, f"Ожидалось ровно 2 кнопки, получено {len(all_btns)}"
    btn_texts = [b.text for b in all_btns]
    btn_cbs = [b.callback_data for b in all_btns]

    assert "Идти по верёвке" in btn_texts
    assert "Прямо на звук" in btn_texts
    assert "l4_2_rope" in btn_cbs
    assert "l4_3_deer" in btn_cbs
    # Все кнопки <= 30 символов
    assert all(len(t) <= 30 for t in btn_texts)


def test_location_4_rope_and_bushes_kitten():
    """Окно L4.2 (Верёвка) переходит в L4.2a (За кустами) с проверкой питомца."""
    game = GameState()
    text, kb = handle_location_4_hunters_glade("l4_2_rope", game, 12345)
    assert len(text) <= 500
    assert game.active_story_callback == "l4_2_rope"

    # Без питомца
    text_no_pet, kb_no_pet = handle_location_4_hunters_glade("l4_2a_bushes", game, 12345)
    assert "котёнок" not in text_no_pet.lower()
    assert len(text_no_pet) <= 500

    # С питомцем
    game.equipment["pet"] = "Барсик"
    text_pet, kb_pet = handle_location_4_hunters_glade("l4_2a_bushes", game, 12345)
    assert "котёнок" in text_pet.lower()
    assert len(text_pet) <= 500

    # Кнопки L4.2a
    btns = [b.callback_data for row in kb_pet.inline_keyboard for b in row]
    assert "l4_3_deer" in btns
    assert "l4_2b_trap" in btns


def test_location_4_trap_damage():
    """L4.2b наносит 5 урона и сохраняет коллбэк."""
    game = GameState()
    game.hp = 50
    text, kb = handle_location_4_hunters_glade("l4_2b_trap", game, 12345)
    assert game.hp == 45
    assert len(text) <= 500
    assert "Ты ушиб плечо: −5 ХП" in text
    assert game.active_story_callback == "l4_2b_trap"


def test_location_4_deer_branching_and_rescue():
    """Полное прохождение ветки спасения оленя с вяленым мясом, кожей и питьём из фляги."""
    game = GameState()
    game.inventory = {
        "Спички": 2,
    }
    game.equipment["flask"] = "Бутылка воды"
    game.flask_water = 5
    game.thirst = 40

    # L4.3
    text, kb = handle_location_4_hunters_glade("l4_3_deer", game, 12345)
    assert len(text) <= 500
    deer_btn_texts = [b.text for row in kb.inline_keyboard for b in row]
    assert "Оставить его" in deer_btn_texts

    # L4.3a - попытка подойти напрямую
    game.hp = 40
    text, kb = handle_location_4_hunters_glade("l4_3a_approach", game, 12345)
    assert game.hp == 37
    assert len(text) <= 500
    assert "Ты ушиб кисть: −3 ХП" in text
    approach_btn_texts = [b.text for row in kb.inline_keyboard for b in row]
    assert "Оставить его" in approach_btn_texts  # Переименованная кнопка!

    # L4.3b -> L4.3b1 (отвязать пластинки)
    text, kb = handle_location_4_hunters_glade("l4_3b_mount", game, 12345)
    assert len(text) <= 500
    text, kb = handle_location_4_hunters_glade("l4_3b1_plates", game, 12345)
    assert len(text) <= 500
    assert game.is_story_flag_set("signal_disabled")

    # L4.4 (освобождение)
    text, kb = handle_location_4_hunters_glade("l4_4_freed", game, 12345)
    assert len(text) <= 500
    assert game.is_story_flag_set("deer_freed")

    # L4.5a (забрать свёрток: Мясо на коре ×2, Кожа ×1)
    game.inventory["Ветка"] = 5
    text, kb = handle_location_4_hunters_glade("l4_5a_loot_all", game, 12345)
    assert len(text) <= 500
    assert game.inventory.get("Мясо на коре") == 2
    assert game.inventory.get("Кожа") == 1
    loot_btns = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "l4_5_put_select" in loot_btns
    assert "l4_6_aftermath" in loot_btns

    # Тест оставления предмета взамен (Ветка)
    text_sel, kb_sel = handle_location_4_hunters_glade("l4_5_put_select", game, 12345)
    sel_btns = [b.callback_data for row in kb_sel.inline_keyboard for b in row]
    assert "l4_put_Ветка" in sel_btns

    text_put, kb_put = handle_location_4_hunters_glade("l4_put_Ветка", game, 12345)
    assert game.inventory["Ветка"] == 4
    assert game.is_story_flag_set("l4_cache_shared")
    assert "Ветка" in text_put

    # L4.6a (обезвредить: +1 Кожа, жажда -5)
    thirst_before = game.thirst
    text, kb = handle_location_4_hunters_glade("l4_6a_disarm", game, 12345)
    assert len(text) <= 500
    assert game.inventory.get("Кожа") == 2
    assert game.thirst == thirst_before - 5
    assert "Жажда: −5" in text

    # L4.7a (разжечь огонь: огонь неохотно, без траты спичек)
    matches_before = game.inventory.get("Спички", 0)
    text, kb = handle_location_4_hunters_glade("l4_7a_fire", game, 12345)
    assert len(text) <= 500
    assert game.inventory.get("Спички", 0) == matches_before  # Спички не тратятся!
    assert "неохотно" in text
    assert "Потрачено: Спичка" not in text

    fire_btns = [b.text for row in kb.inline_keyboard for b in row]
    assert "Попить воды" in fire_btns

    # L4.7a1 (попить воды: 3 глотка из бутылки, +20 к жажде)
    thirst_before_drink = game.thirst
    text, kb = handle_location_4_hunters_glade("l4_7a1_drink", game, 12345)
    assert len(text) <= 500
    assert game.flask_water == 2  # 5 - 3 глотка = 2
    assert game.thirst == thirst_before_drink + 20
    assert "Утоление жажды: +20" in text

    # L4.8 (финал)
    text, kb = handle_location_4_hunters_glade("l4_8_final", game, 12345)
    assert len(text) <= 500
    assert game.is_story_flag_set("l4_completed")
    assert game.active_story_callback is None
    final_btns = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "back" in final_btns


def test_location_4_settlement_and_trigger():
    """Просека Охотников: первые 2 ночи - спокойное обживание, на 3-й день при исследовании стартует квест."""
    from story.location_stories import check_forest_research_story_trigger
    from keyboards import get_main_kb

    game = GameState()
    game.day = 5
    game.current_location = "Просека Охотников"

    # 1. Первый вход на Просеку: мирный экран стоянки
    text_entry, kb_entry = handle_location_4_hunters_glade("location_enter_4", game, 101)
    assert "обустроить лагерь" in text_entry
    assert not game.is_story_flag_set("l4_started")
    assert game.story_flags.get("l4_entered_day") == 5

    # 2. Исследование в 1-й день нахождения (ночей сна = 0): квест не стартует
    ev1, log1 = check_forest_research_story_trigger(game, loc_id=4, torch_equipped=False)
    assert ev1 is None

    # 3. Проживание 1-й ночи (ночей сна = 1): квест ещё не стартует
    game.story_flags["l4_sleep_count"] = 1
    ev2, log2 = check_forest_research_story_trigger(game, loc_id=4, torch_equipped=False)
    assert ev2 is None

    # 4. Проживание 2-й ночи (ночей сна = 2, день 7): при исследовании стартует квест!
    game.story_flags["l4_sleep_count"] = 2
    game.day = 7
    ev3, log3 = check_forest_research_story_trigger(game, loc_id=4, torch_equipped=False)
    assert ev3 == "l4_1_entry"
    assert game.is_story_flag_set("l4_started")

    # 5. Завершение квеста
    game.set_story_flag("l4_completed", True)

    # 6. После завершения: исследование больше никогда не возвращает квест
    ev4, log4 = check_forest_research_story_trigger(game, loc_id=4, torch_equipped=False)
    assert ev4 is None

    # 7. После завершения: вход через меню выдаёт спокойную стоянку
    text_peace, kb_peace = handle_location_4_hunters_glade("location_enter_4", game, 101)
    assert "тропа свободна" in text_peace
    assert not game.active_story_callback


def test_l3_unlocks_l4_navigation():
    """После завершения L3 (l3_13_boundary) Просека Охотников добавляется в unlocked_locations и видна в get_locations_kb."""
    from story.location_stories import handle_location_3_slate_hollow
    from keyboards import get_locations_kb

    game = GameState()
    game.unlocked_locations = ["Лесной старт", "Ручей", "Скромная Лощина"]

    # Игрок выходит на границу L3
    text, kb = handle_location_3_slate_hollow("l3_13_boundary", game, 101)
    assert "Просека Охотников" in game.unlocked_locations

    # Проверяем меню локаций
    loc_kb = get_locations_kb(game)
    btn_texts = [b.text for row in loc_kb.inline_keyboard for b in row]
    btn_cbs = [b.callback_data for row in loc_kb.inline_keyboard for b in row]

    assert "🏹 Просека охотников" in btn_texts
    assert "location_enter_4" in btn_cbs

