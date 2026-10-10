"""
tests/test_location_4_story.py — Тесты сюжета локации 4 (Просека Охотников) и бонусного лута.
"""

import pytest
from game_state import GameState
from modules.finds import BONUS_FINDS, _roll_bonus, roll_find
from story.location_stories import handle_location_4_hunters_glade


@pytest.mark.l4
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


@pytest.mark.l4
@pytest.mark.nav
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


@pytest.mark.l4
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


@pytest.mark.l4
def test_location_4_trap_damage():
    """L4.2b наносит 5 урона и сохраняет коллбэк."""
    game = GameState()
    game.hp = 50
    text, kb = handle_location_4_hunters_glade("l4_2b_trap", game, 12345)
    assert game.hp == 45
    assert len(text) <= 500
    assert "Ты ушиб плечо: −5 ХП" in text
    assert game.active_story_callback == "l4_2b_trap"


@pytest.mark.l4
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


@pytest.mark.l4
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


@pytest.mark.l4
@pytest.mark.nav
def test_l3_unlocks_l4_navigation():
    """После завершения L3 (l3_13_boundary) Просека Охотников добавляется в unlocked_locations и видна в get_locations_kb."""
    from story.location_stories import handle_location_3_slate_hollow
    from keyboards import get_locations_kb

    game = GameState()
    game.unlocked_locations = ["Лесной старт", "Ручей", "Скромная Лощина"]

    # Игрок выходит на границу L3
    text, kb = handle_location_3_slate_hollow("l3_13_boundary", game, 101)
    assert "Просека охотников" in game.unlocked_locations

    # Проверяем меню локаций
    loc_kb = get_locations_kb(game)
    btn_texts = [b.text for row in loc_kb.inline_keyboard for b in row]
    btn_cbs = [b.callback_data for row in loc_kb.inline_keyboard for b in row]

    assert "4. 🏹 Просека охотников" in btn_texts
    assert "location_enter_4" in btn_cbs


@pytest.mark.l4
def test_location_4_observation_inspections():
    """Проверка трёх точек осмотра в L4 (узел, срез кожи, зола) на +2 Наблюдательности каждая и лимит <= 500 символов."""
    game = GameState()
    assert game.narrative_karma.get("observation", 0) == 0

    # 1. Осмотр узла в L4.3b
    text_3b, kb_3b = handle_location_4_hunters_glade("l4_3b_mount", game, 101)
    assert len(text_3b) <= 500
    cbs_3b = [b.callback_data for row in kb_3b.inline_keyboard for b in row]
    assert "l4_3b_inspect_knot" in cbs_3b
    btn_knot = next(b for row in kb_3b.inline_keyboard for b in row if b.callback_data == "l4_3b_inspect_knot")
    assert len(btn_knot.text) <= 30

    text_knot, kb_knot = handle_location_4_hunters_glade("l4_3b_inspect_knot", game, 101)
    assert len(text_knot) <= 500
    assert game.narrative_karma.get("observation") == 2
    assert game.is_story_flag_set("l4_knot_inspected")

    # Возврат к выбору — кнопка осмотра исчезла
    text_3b_back, kb_3b_back = handle_location_4_hunters_glade("l4_3b_mount_back", game, 101)
    assert len(text_3b_back) <= 500
    cbs_3b_back = [b.callback_data for row in kb_3b_back.inline_keyboard for b in row]
    assert "l4_3b_inspect_knot" not in cbs_3b_back
    assert "l4_3b1_plates" in cbs_3b_back

    # 2. Осмотр среза кожи в L4.5
    text_5, kb_5 = handle_location_4_hunters_glade("l4_5_firepit", game, 101)
    assert len(text_5) <= 500
    cbs_5 = [b.callback_data for row in kb_5.inline_keyboard for b in row]
    assert "l4_5_inspect_leather" in cbs_5
    btn_leather = next(b for row in kb_5.inline_keyboard for b in row if b.callback_data == "l4_5_inspect_leather")
    assert len(btn_leather.text) <= 30

    text_leather, kb_leather = handle_location_4_hunters_glade("l4_5_inspect_leather", game, 101)
    assert len(text_leather) <= 500
    assert game.narrative_karma.get("observation") == 4
    assert game.is_story_flag_set("l4_leather_inspected")

    # Возврат к кострищу — кнопка осмотра исчезла
    text_5_back, kb_5_back = handle_location_4_hunters_glade("l4_5_firepit_back", game, 101)
    assert len(text_5_back) <= 500
    cbs_5_back = [b.callback_data for row in kb_5_back.inline_keyboard for b in row]
    assert "l4_5_inspect_leather" not in cbs_5_back
    assert "l4_5a_loot_all" in cbs_5_back

    # 3. Осмотр золы в L4.7
    text_7, kb_7 = handle_location_4_hunters_glade("l4_7_hearth", game, 101)
    assert len(text_7) <= 500
    cbs_7 = [b.callback_data for row in kb_7.inline_keyboard for b in row]
    assert "l4_7_inspect_cinder" in cbs_7
    btn_cinder = next(b for row in kb_7.inline_keyboard for b in row if b.callback_data == "l4_7_inspect_cinder")
    assert len(btn_cinder.text) <= 30

    text_cinder, kb_cinder = handle_location_4_hunters_glade("l4_7_inspect_cinder", game, 101)
    assert len(text_cinder) <= 500
    assert game.narrative_karma.get("observation") == 6
    assert game.is_story_flag_set("l4_cinder_inspected")

    # Возврат к кострищу — кнопка осмотра исчезла
    text_7_back, kb_7_back = handle_location_4_hunters_glade("l4_7_hearth_back", game, 101)
    assert len(text_7_back) <= 500
    cbs_7_back = [b.callback_data for row in kb_7_back.inline_keyboard for b in row]
    assert "l4_7_inspect_cinder" not in cbs_7_back
    assert "l4_7a_fire" in cbs_7_back


@pytest.mark.slow
@pytest.mark.l4
def test_location_4_sequential_chapters_flow_and_sleeps():

    """Тестирование цепочки сюжеток L4 (Пролог -> 4 сна -> Глава 1 -> 4 сна -> Глава 2 -> 4 сна -> Глава 3)."""
    from story.location_stories import check_forest_research_story_trigger, handle_location_4_hunters_glade

    game = GameState()
    game.day = 5
    game.current_location = "Просека Охотников"

    # Завершаем пролог оленя
    game.set_story_flag("deer_freed", True)
    text_fin, kb_fin = handle_location_4_hunters_glade("l4_8_final", game, 101)
    assert game.is_story_flag_set("l4_completed")
    assert "l4_deer_sleeps" in game.story_flags
    base_sleeps = game.story_flags["l4_deer_sleeps"]

    # 1. До 4 снов Глава 1 не срабатывает
    game.story_flags["l4_sleep_count"] = base_sleeps + 3
    ev, log = check_forest_research_story_trigger(game, loc_id=4, torch_equipped=False)
    assert ev is None

    # После 4 снов — триггер Главы 1 («Преграда на обрыве»)
    game.story_flags["l4_sleep_count"] = base_sleeps + 4
    ev, log = check_forest_research_story_trigger(game, loc_id=4, torch_equipped=False)
    assert ev == "l4_ch1_1_cliff"

    # Прохождение Главы 1 и проверка длины текстов и кнопок
    ch1_screens = [
        "l4_ch1_1_cliff", "l4_ch1_2_trap", "l4_ch1_2_inspect", "l4_ch1_2_trap_back",
        "l4_ch1_3_growth", "l4_slug_battle_start", "l4_slug_battle_engine",
        "l4_ch1_4_stone_mark", "l4_ch1_5_doubt"
    ]
    for scr in ch1_screens:
        txt, kb = handle_location_4_hunters_glade(scr, game, 101)
        assert len(txt) <= 500, f"Экран {scr} превышает 500 символов ({len(txt)})"
        for row in kb.inline_keyboard:
            for b in row:
                assert len(b.text) <= 30, f"Кнопка {b.text} на экране {scr} превышает 30 символов"

    assert game.is_story_flag_set("l4_ch1_cliff_completed")
    assert "Яр Слаймов" not in getattr(game, "unlocked_locations", [])

    # 2. До 4 снов Глава 2 не срабатывает
    ch2_sleep_base = game.story_flags["l4_ch2_sleeps"]
    game.story_flags["l4_sleep_count"] = ch2_sleep_base + 2
    ev, log = check_forest_research_story_trigger(game, loc_id=4, torch_equipped=False)
    assert ev is None

    # После 4 снов — триггер Главы 2 («Серая стая»)
    game.story_flags["l4_sleep_count"] = ch2_sleep_base + 4
    ev, log = check_forest_research_story_trigger(game, loc_id=4, torch_equipped=False)
    assert ev == "l4_ch2_1_shadow"

    # Прохождение Главы 2 со спасённым оленем
    ch2_screens = ["l4_ch2_1_shadow", "l4_ch2_2_stone_shield", "l4_ch2_3_guard", "l4_ch2_3b_gaze", "l4_ch2_4_lesson"]
    for scr in ch2_screens:
        txt, kb = handle_location_4_hunters_glade(scr, game, 101)
        assert len(txt) <= 500, f"Экран {scr} превышает 500 символов ({len(txt)})"
        if scr == "l4_ch2_3_guard":
            assert "этот бой с волками стал бы для тебя последним в твоей жизни, и живым ты бы из него не вышел победителем" in txt.lower()
        if scr == "l4_ch2_3b_gaze":
            assert "они пришли спасти того, кто спас их сородича" in txt.lower()
        for row in kb.inline_keyboard:
            for b in row:
                assert len(b.text) <= 30, f"Кнопка {b.text} на экране {scr} превышает 30 символов"

    assert game.is_story_flag_set("l4_ch2_pack_completed")

    # Проверка альтернативной ветки Главы 2 (без оленя)
    game_no_deer = GameState()
    game_no_deer.story_flags["deer_freed"] = False
    txt_guard, kb_guard = handle_location_4_hunters_glade("l4_ch2_3_guard", game_no_deer, 101)
    assert "Помощи ждать неоткуда" in txt_guard
    assert len(txt_guard) <= 500
    txt_fight, kb_fight = handle_location_4_hunters_glade("l4_wolves_battle_start", game_no_deer, 101)
    assert len(txt_fight) <= 500

    # 3. До 4 снов Глава 3 не срабатывает
    ch3_sleep_base = game.story_flags["l4_ch3_sleeps"]
    game.story_flags["l4_sleep_count"] = ch3_sleep_base + 3
    ev, log = check_forest_research_story_trigger(game, loc_id=4, torch_equipped=False)
    assert ev is None

    # После 4 снов — триггер Главы 3 («Дозорный помост и решение по броне»)
    game.story_flags["l4_sleep_count"] = ch3_sleep_base + 4
    ev, log = check_forest_research_story_trigger(game, loc_id=4, torch_equipped=False)
    assert ev == "l4_ch3_1_shelter"

    # Прохождение Главы 3
    # Подъём брони люлькой (требуется Ветка x1, Кожа x1)
    game.inventory["Ветка"] = 2
    game.inventory["Кожа"] = 2
    ch3_screens = [
        "l4_ch3_1_shelter", "l4_ch3_2_fate", "l4_ch3_2a_lift",
        "l4_ch3_3_table", "l4_ch3_3_inspect", "l4_ch3_3_table_back",
        "l4_ch3_4_draft", "l4_ch3_4_upgrade",
        "l4_ch3_5_armor_final", "l4_ch3_5a_tree", "l4_ch3_5b_moss", "l4_ch3_6_epilogue"
    ]
    for scr in ch3_screens:
        txt, kb = handle_location_4_hunters_glade(scr, game, 101)
        assert len(txt) <= 500, f"Экран {scr} превышает 500 символов ({len(txt)})"
        for row in kb.inline_keyboard:
            for b in row:
                assert len(b.text) <= 30, f"Кнопка {b.text} на экране {scr} превышает 30 символов"

    assert game.is_story_flag_set("l4_fully_completed")
    assert game.inventory.get("Схема кожаной брони", 0) >= 1
    assert "Яр Слаймов" in game.unlocked_locations


@pytest.mark.l4
def test_leather_armor_schema_craft_and_equipment():
    """Тест использования схемы кожаной брони, открытия крафта и экипировки комплекта."""
    from crafts import handle_craft, do_craft

    game = GameState()
    game.inventory["Схема кожаной брони"] = 1

    # 1. Использование схемы
    text, kb = handle_craft("use_item_Схема кожаной брони", game, 101)
    assert game.inventory.get("Схема кожаной брони", 0) == 0
    assert game.is_story_flag_set("leather_armor_unlocked")
    for piece in ("Кожаный капюшон", "Кожаный нагрудник", "Кожаные поножи", "Кожаные сапоги"):
        assert piece in game.unlocked_crafts

    # 2. Крафт всех 4 предметов
    game.inventory["Кожа"] = 20
    game.inventory["Кусок коры"] = 10
    game.inventory["Сланцевый слиток"] = 2
    game.inventory["Ветка"] = 5

    for piece in ("Кожаный капюшон", "Кожаный нагрудник", "Кожаные поножи", "Кожаные сапоги"):
        ok, msg = do_craft(game, piece)
        assert ok, f"Не удалось скрафтить {piece}: {msg}"
        assert game.inventory.get(piece, 0) == 1

    # 3. Экипировка всех 4 предметов
    handle_craft("use_item_Кожаный капюшон", game, 101)
    handle_craft("use_item_Кожаный нагрудник", game, 101)
    handle_craft("use_item_Кожаные поножи", game, 101)
    handle_craft("use_item_Кожаные сапоги", game, 101)

    assert game.equipment.get("head") == "Кожаный капюшон"
    assert game.equipment.get("torso") == "Кожаный нагрудник"
    assert game.equipment.get("pants") == "Кожаные поножи"
    assert game.equipment.get("boots") == "Кожаные сапоги"


@pytest.mark.l4
@pytest.mark.nav
def test_location_5_entry_requirement():
    """Вход на локацию 5 открывает сюжет «То, что лес не отпустил» без искусственных блокировок."""
    from story.location_stories import handle_location_5_slug_pit

    game = GameState()
    game.current_location = "Яр Слаймов"

    # Вход в локацию 5
    text, kb = handle_location_5_slug_pit("slug_pit_start", game, 101)
    assert "Яр Слаймов" in text or "зеленоватая взвесь" in text or "туман" in text
    assert game.story_state == "l5_1a"
    assert kb is not None


@pytest.mark.l4
def test_l4_slug_battle_full_cycle_and_mushroom_consumption():
    """Тест полного интерактивного цикла боя со слизнем и удаление гриба из инвентаря."""
    from story.location_stories import handle_location_4_hunters_glade, SLUG_ACTIONS

    game = GameState()
    game.hp = 150

    # 1. Старт боя со слизнем
    txt, kb = handle_location_4_hunters_glade("l4_slug_battle_start", game, 101)
    assert game.story_state == "l4_slug_battle"
    assert "БОЛОТНЫЙ СЛИЗЕНЬ" in txt
    assert game.inventory.get("Светящийся гриб") == 1
    assert "🦯 Ударить посохом" in [b.text for r in kb.inline_keyboard for b in r]

    # 2. Первые 2 удара — гриб ещё нельзя осмотреть
    for _ in range(2):
        txt, kb = handle_location_4_hunters_glade("l4_slug_strike", game, 101)
        btns = [b.callback_data for r in kb.inline_keyboard for b in r]
        assert "l4_slug_inspect" not in btns

    # 3-й удар — появляется [🔍 Осмотреть гриб]
    txt, kb = handle_location_4_hunters_glade("l4_slug_strike", game, 101)
    btns = [b.callback_data for r in kb.inline_keyboard for b in r]
    assert "l4_slug_inspect" in btns

    # 3. Осмотр гриба
    txt, kb = handle_location_4_hunters_glade("l4_slug_inspect", game, 101)
    assert "Тебе показалось, что слизень отшатнулся" in txt

    # 4. Прокликиваем все 10 действий
    for act_key, _ in SLUG_ACTIONS:
        txt, kb = handle_location_4_hunters_glade(f"l4_slug_act_{act_key}", game, 101)

    btns = [b.callback_data for r in kb.inline_keyboard for b in r]
    assert "l4_slug_coat" in btns

    # 5. Растираем по посоху — гриб должен исчезнуть из инвентаря!
    txt, kb = handle_location_4_hunters_glade("l4_slug_coat", game, 101)
    assert "Светящийся гриб" not in game.inventory
    btn_texts = [b.text for r in kb.inline_keyboard for b in r]
    assert "💥 Ударить посохом" in btn_texts

    # 6. Удары смазанным посохом до победы
    while game.slug_battle.get("slug_hp", 0) > 0:
        txt, kb = handle_location_4_hunters_glade("l4_slug_strike", game, 101)
        if game.is_story_flag_set("l4_slug_defeated"):
            break

    assert game.is_story_flag_set("l4_slug_defeated")
    assert "l4_ch1_4_stone_mark" in [b.callback_data for r in kb.inline_keyboard for b in r]


@pytest.mark.l4
def test_l4_wolf_pack_battle_full_cycle():
    """Тест боя со стаей волков: динамическая плашка, разброс урона, оборона и победа."""
    from story.location_stories import handle_location_4_hunters_glade

    game = GameState()
    game.hp = 500
    game.equipment["weapon"] = "Крепкий посох"

    # 1. Старт боя
    txt, kb = handle_location_4_hunters_glade("l4_wolves_battle_start", game, 101)
    assert "[ 🐺 🐺 🐺 ]" in txt
    assert "🐺 Серый:  41/41 HP" in txt
    assert "🐺 Бурый:  44/44 HP" in txt
    assert "🐺 Вожак:  51/51 HP" in txt

    # 2. Проверка глухой обороны
    hp_before = game.hp
    txt_def, kb_def = handle_location_4_hunters_glade("l4_pack_defend", game, 101)
    assert game.hp < hp_before
    assert "Глухая оборона" in txt_def

    # 3. Фокус Серого до гибели
    while game.wolf_pack_battle.get("grey_hp", 0) > 0:
        txt, kb = handle_location_4_hunters_glade("l4_pack_attack_grey", game, 101)

    assert "[ 💀 🐺 🐺 ]" in txt
    assert "l4_pack_attack_grey" not in [b.callback_data for r in kb.inline_keyboard for b in r]

    # 4. Фокус Бурого до гибели
    while game.wolf_pack_battle.get("brown_hp", 0) > 0:
        txt, kb = handle_location_4_hunters_glade("l4_pack_attack_brown", game, 101)

    assert "[ 💀 💀 🐺 ]" in txt
    assert "l4_pack_attack_brown" not in [b.callback_data for r in kb.inline_keyboard for b in r]

    # 5. Фокус Вожака до победы
    while game.wolf_pack_battle.get("leader_hp", 0) > 0:
        txt, kb = handle_location_4_hunters_glade("l4_pack_attack_leader", game, 101)

    assert game.is_story_flag_set("l4_wolves_defeated")
    assert "[ 💀 💀 💀 ]" in txt
    assert "l4_ch2_4_lesson" in [b.callback_data for r in kb.inline_keyboard for b in r]
    assert game.hp > 0


@pytest.mark.l4
def test_l4_no_premature_l5_unlock_in_ch1():
    """L5 («Яр Слаймов») не должна открываться в конце Главы 1 (l4_ch1_5_doubt), а только в Главе 3."""
    game = GameState()
    game.unlocked_locations = ["Стартовый лес", "Ручей со змеями", "Скромная лощина", "Просека охотников"]

    # Проходим финал Главы 1
    text, kb = handle_location_4_hunters_glade("l4_ch1_5_doubt", game, 101)
    assert game.is_story_flag_set("l4_ch1_cliff_completed")
    assert "Яр Слаймов" not in game.unlocked_locations

    # Проходим финал Главы 3 (эпилог)
    text_ep, kb_ep = handle_location_4_hunters_glade("l4_ch3_6_epilogue", game, 101)
    assert game.is_story_flag_set("l4_fully_completed")
    assert "Яр Слаймов" in game.unlocked_locations


@pytest.mark.l4
def test_l4_karma_abuse_protection():
    """Повторные вызовы сюжетных экранов L4 не должны повторно начислять карму."""
    game = GameState()
    initial_karma = dict(game.narrative_karma)

    # 1. l4_3b1_plates (+2 observation)
    handle_location_4_hunters_glade("l4_3b1_plates", game, 101)
    assert game.narrative_karma.get("observation", 0) == 2
    handle_location_4_hunters_glade("l4_3b1_plates", game, 101)
    assert game.narrative_karma.get("observation", 0) == 2

    # 2. l4_3b2_shake (+1 pragmatism)
    game2 = GameState()
    handle_location_4_hunters_glade("l4_3b2_shake", game2, 101)
    assert game2.narrative_karma.get("pragmatism", 0) == 1
    handle_location_4_hunters_glade("l4_3b2_shake", game2, 101)
    assert game2.narrative_karma.get("pragmatism", 0) == 1

    # 3. l4_4_freed (+3 compassion)
    game3 = GameState()
    handle_location_4_hunters_glade("l4_4_freed", game3, 101)
    assert game3.narrative_karma.get("compassion", 0) == 3
    handle_location_4_hunters_glade("l4_4_freed", game3, 101)
    assert game3.narrative_karma.get("compassion", 0) == 3

    # 4. l4_3c_ignore (+2 pragmatism)
    game4 = GameState()
    handle_location_4_hunters_glade("l4_3c_ignore", game4, 101)
    assert game4.narrative_karma.get("pragmatism", 0) == 2
    handle_location_4_hunters_glade("l4_3c_ignore", game4, 101)
    assert game4.narrative_karma.get("pragmatism", 0) == 2

    # 5. l4_6b_warn (+2 compassion)
    game5 = GameState()
    handle_location_4_hunters_glade("l4_6b_warn", game5, 101)
    assert game5.narrative_karma.get("compassion", 0) == 2
    handle_location_4_hunters_glade("l4_6b_warn", game5, 101)
    assert game5.narrative_karma.get("compassion", 0) == 2

    # 6. l4_ch3_2a_lift (+2 intervention)
    game6 = GameState()
    game6.inventory["Ветка"] = 5
    game6.inventory["Кожа"] = 5
    handle_location_4_hunters_glade("l4_ch3_2a_lift", game6, 101)
    assert game6.narrative_karma.get("intervention", 0) == 2
    handle_location_4_hunters_glade("l4_ch3_2a_lift", game6, 101)
    assert game6.narrative_karma.get("intervention", 0) == 2

    # 7. l4_ch3_4_upgrade (+2 intervention)
    game7 = GameState()
    handle_location_4_hunters_glade("l4_ch3_4_upgrade", game7, 101)
    assert game7.narrative_karma.get("intervention", 0) == 2
    handle_location_4_hunters_glade("l4_ch3_4_upgrade", game7, 101)
    assert game7.narrative_karma.get("intervention", 0) == 2

    # 8. l4_ch3_5a_tree (+1 pragmatism)
    game8 = GameState()
    handle_location_4_hunters_glade("l4_ch3_5a_tree", game8, 101)
    assert game8.narrative_karma.get("pragmatism", 0) == 1
    handle_location_4_hunters_glade("l4_ch3_5a_tree", game8, 101)
    assert game8.narrative_karma.get("pragmatism", 0) == 1


@pytest.mark.l4
def test_l4_mortality_and_death_screens():
    """Смерть на L4: при падении HP <= 0 вызывается некролог и экран гибели."""
    # 1. Ловушка (l4_2b_trap)
    game_trap = GameState()
    game_trap.hp = 3
    txt, kb = handle_location_4_hunters_glade("l4_2b_trap", game_trap, 101)
    assert game_trap.hp == 0
    assert "НЕКРОЛОГ" in txt or "погиб" in txt.lower() or "смертоносной ловушки" in txt.lower()
    cbs_trap = [b.callback_data for r in kb.inline_keyboard for b in r]
    assert "start_new_game_confirmed" in cbs_trap

    # 2. Удар оленя (l4_3a_approach)
    game_deer = GameState()
    game_deer.hp = 2
    txt, kb = handle_location_4_hunters_glade("l4_3a_approach", game_deer, 101)
    assert game_deer.hp == 0
    assert "НЕКРОЛОГ" in txt or "погиб" in txt.lower() or "копыта" in txt.lower()

    # 3. Бой со слизнем (l4_slug_strike)
    game_slug = GameState()
    game_slug.hp = 4
    handle_location_4_hunters_glade("l4_slug_battle_start", game_slug, 101)
    txt, kb = handle_location_4_hunters_glade("l4_slug_strike", game_slug, 101)
    assert game_slug.hp == 0
    assert game_slug.slug_battle is None
    assert "НЕКРОЛОГ" in txt or "погиб" in txt.lower() or "слизь" in txt.lower()

    # 4. Бой с волками (l4_pack_attack_grey)
    game_wolf = GameState()
    game_wolf.hp = 2
    handle_location_4_hunters_glade("l4_wolves_battle_start", game_wolf, 101)
    txt, kb = handle_location_4_hunters_glade("l4_pack_attack_grey", game_wolf, 101)
    assert game_wolf.hp == 0
    assert game_wolf.wolf_pack_battle is None
    assert "НЕКРОЛОГ" in txt or "погиб" in txt.lower() or "волк" in txt.lower()


@pytest.mark.l4
def test_l4_ch3_shelter_resource_requirement_and_deduction():
    """Подъём брони в укрытие требует 1 ветку и 1 кожу; без них действие блокируется."""
    # 1. Без ресурсов: кнопка заблокирована
    game = GameState()
    game.inventory = {}
    txt, kb = handle_location_4_hunters_glade("l4_ch3_2_fate", game, 101)
    cbs = [b.callback_data for r in kb.inline_keyboard for b in r]
    assert "l4_ch3_2_fate_no_res" in cbs
    assert "l4_ch3_2a_lift" not in cbs

    # Попытка прямого вызова l4_ch3_2a_lift без ресурсов
    txt_lift, kb_lift = handle_location_4_hunters_glade("l4_ch3_2a_lift", game, 101)
    assert not game.is_story_flag_set("l4_armor_lifted")
    assert "Не хватает материалов" in txt_lift

    # 2. С ресурсами: ветка и кожа списываются, броня поднимается
    game.inventory = {"Ветка": 2, "Кожа": 1}
    txt_fate_ok, kb_fate_ok = handle_location_4_hunters_glade("l4_ch3_2_fate", game, 101)
    cbs_ok = [b.callback_data for r in kb_fate_ok.inline_keyboard for b in r]
    assert "l4_ch3_2a_lift" in cbs_ok

    txt_lift_ok, kb_lift_ok = handle_location_4_hunters_glade("l4_ch3_2a_lift", game, 101)
    assert game.is_story_flag_set("l4_armor_lifted")
    assert game.inventory.get("Ветка") == 1
    assert "Кожа" not in game.inventory


@pytest.mark.l4
def test_l4_battle_cleanup_and_peaceful_camp():
    """При завершении боёв и на мирной стоянке боевые контексты и FSM очищаются."""
    game = GameState()
    game.set_story_flag("l4_fully_completed", True)
    game.slug_battle = {"slug_hp": 10}
    game.wolf_pack_battle = {"grey_hp": 20}
    game.active_story_callback = "l4_slug_battle"

    text, kb = handle_location_4_hunters_glade("location_enter_4", game, 101)
    assert game.active_story_callback is None
    assert game.slug_battle is None
    assert game.wolf_pack_battle is None
    assert "Впереди ждёт спуск к Яру Слаймов" in text





