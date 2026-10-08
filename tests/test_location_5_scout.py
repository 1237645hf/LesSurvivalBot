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
    has_slate_spear,
    has_bone_hook,
    has_glowing_shroom,
    count_berries,
    consume_berries,
    is_slate_spear_in_hand,
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
    assert "Исследования завершены. Ты знаешь эту гору жижи вдоль и поперёк" in text
    assert len(text) <= 500
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "⚔️ Начать тактический бой" in buttons
    assert "🏕️ Вернуться в лагерь" in buttons

    # Без оружия -> экран предупреждения о снаряжении
    t_warn, kb_warn = handle_location_5_slug_pit("l5_scout_final_attack_habits", game, uid)
    assert "необходимо специальное снаряжение" in t_warn
    assert game.story_state == "l5_scout_gear_warning"

    # С копьём и крюком -> старт боя
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    t_fight, kb_fight = handle_location_5_slug_pit("l5_scout_final_attack_habits", game, uid)
    assert getattr(game, "wolf_battle", None) is not None


def test_scout_final_screen_vector_2_surroundings():
    """Тест Окна Финала: Вектор 2 (surroundings >= 16) и полная спецоперация «Каменный пресс»."""
    game = GameState()
    uid = 105
    game.intro_seen = True
    game.habits_count = 6
    game.surroundings_count = 17  # Сумма 23
    game.hp = 100

    text, kb = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "Все приготовления завершены. Над дном котловины нависает тяжелейший каменный пресс" in text
    assert len(text) <= 500
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "💥 Запустить спецоперацию: Каменный пресс" in buttons
    assert "🏕️ Вернуться в лагерь" in buttons

    # 1. Проверка экрана нехватки (если ничего нет)
    t_missing, kb_m = handle_location_5_slug_pit("l5_scout_final_trap_surroundings", game, uid)
    assert "Для воплощения замысла тебе не хватает:" in t_missing
    assert "• Сланцевое копьё (должно быть экипировано в руках!)" in t_missing
    assert "• Костяной крюк на кожаной верёвке (в инвентаре)" in t_missing
    assert "• Спелые лесные ягоды: 0/5 шт. (для приманки)" in t_missing
    assert "• Светящиеся грибы: 0 шт. (необходимы для растворения кислоты)" in t_missing
    assert game.story_state == "l5_trap_op_missing_gear"
    btns_m = [b.text for row in kb_m.inline_keyboard for b in row]
    assert "🏕️ Вернуться в лагерь и подготовиться" in btns_m

    # 2. Выдаём всё необходимое
    game.equipment["hand_right"] = "Охотничье сланцевое копьё"
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    game.inventory["Лесная ягода"] = 6
    game.inventory["Светящийся гриб"] = 3

    # Экран 1: Шаг в бездну (списание 5 ягод)
    t1, kb1 = handle_location_5_slug_pit("l5_scout_final_trap_surroundings", game, uid)
    assert "Ты спускаешься по скользкому глиняному укосу на самое дно чаши" in t1
    assert game.inventory.get("Лесная ягода") == 1  # 6 - 5 = 1
    assert game.story_state == "l5_trap_op_step1"
    btns1 = [b.text for row in kb1.inline_keyboard for b in row]
    assert "🧗 Взбираться к спусковому узлу" in btns1

    # Экран 2: Роковая осечка
    t2, kb2 = handle_location_5_slug_pit("l5_trap_op_step2", game, uid)
    assert "Ты карабкаешься по мокрому сланцу наверх" in t2
    assert game.story_state == "l5_trap_op_step2"
    btns2 = [b.text for row in kb2.inline_keyboard for b in row]
    assert "⚠️ Прыгнуть на помост и выбить клин" in btns2

    # Экран 3: Срыв лавины в бездну (удаление костяного крюка)
    t3, kb3 = handle_location_5_slug_pit("l5_trap_op_step3", game, uid)
    assert "Страх отступает перед диким выбросом адреналина" in t3
    assert "Костяной крюк на кожаной верёвке" not in game.inventory
    assert game.story_state == "l5_trap_op_step3"
    btns3 = [b.text for row in kb3.inline_keyboard for b in row]
    assert "🛡️ Прижать голову и сгруппироваться" in btns3

    # Экран 4: Крушение и расплата (урон при surroundings_count=17: 80 HP)
    t4, kb4 = handle_location_5_slug_pit("l5_trap_op_step4", game, uid)
    assert "Глухой сокрушительный удар о дно котловины" in t4
    assert "Получено урона: 80 единиц." in t4
    assert "Удар камней и кислотные пары едва не сломали тебе хребет" in t4
    assert game.hp == 20  # 100 - 80 = 20
    assert game.story_state == "l5_trap_op_step4"
    btns4 = [b.text for row in kb4.inline_keyboard for b in row]
    assert "🩸 Пересилить контузию и встать" in btns4

    # Экран 5: Бунт придавленной массы
    t5, kb5 = handle_location_5_slug_pit("l5_trap_op_step5", game, uid)
    assert "Кашляя кровью и задыхаясь от дыма, ты встаешь на колени" in t5
    assert game.story_state == "l5_trap_op_step5"
    btns5 = [b.text for row in kb5.inline_keyboard for b in row]
    assert "🍄 Выхватить светящиеся грибы" in btns5

    # Экран 6: Химическое пекло (удаление ВСЕХ светящихся грибов)
    t6, kb6 = handle_location_5_slug_pit("l5_trap_op_step6", game, uid)
    assert "Ты срываешь с пояса сумку и достаешь все редкие светящиеся грибы" in t6
    assert "Светящийся гриб" not in game.inventory
    assert game.story_state == "l5_trap_op_step6"
    btns6 = [b.text for row in kb6.inline_keyboard for b in row]
    assert "⚡ Рвануть по качающимся камням" in btns6

    # Экран 7: Первый удар мимо
    t7, kb7 = handle_location_5_slug_pit("l5_trap_op_step7", game, uid)
    assert "Сланцевое копьё в дрожащих руках кажется неподъемным" in t7
    assert game.story_state == "l5_trap_op_step7"
    btns7 = [b.text for row in kb7.inline_keyboard for b in row]
    assert "🔥 Навалиться всем весом и добить" in btns7

    # Экран 8: Гибель сердцевины
    t8, kb8 = handle_location_5_slug_pit("l5_trap_op_step8", game, uid)
    assert "Зарычав от боли и отчаяния, ты не отпускаешь оружие" in t8
    assert game.story_state == "l5_trap_op_step8"
    btns8 = [b.text for row in kb8.inline_keyboard for b in row]
    assert "🍂 Выдернуть голое древко и отскочить" in btns8

    # Экран 9: Тишина над котловиной (снятие копья, выдача Крепкого посоха, флаги босса)
    t9, kb9 = handle_location_5_slug_pit("l5_trap_op_step9", game, uid)
    assert "Ты падаешь на спину на сухую породу" in t9
    assert game.equipment.get("hand_right") == "Крепкий посох"
    assert game.inventory.get("Крепкий посох") == 1
    assert "Охотничье сланцевое копьё" not in game.inventory
    assert "🔱 Охотничье сланцевое копьё" not in game.inventory
    assert game.is_story_flag_set("trash_slime_defeated")
    assert game.is_story_flag_set("boss_trash_slime_defeated")
    assert game.is_story_flag_set("l5_ancient_defeated")
    assert game.story_state == "l5_trap_op_step9"
    btns9 = [b.text for row in kb9.inline_keyboard for b in row]
    assert "➡️ Далее" in btns9

    # Экран 10: Путь во тьму (открытие L6 Мохнатая пещера)
    t10, kb10 = handle_location_5_slug_pit("l5_trap_op_step10", game, uid)
    assert "Пар рассеивается, открывая восточную стену котловины" in t10
    assert "Открыта новая локация: Мохнатая пещера." in t10
    assert "(L6)" not in t10
    assert "Мохнатая пещера" in game.unlocked_locations
    assert game.story_state == "l5_trap_op_step10"
    btns10 = [b.text for row in kb10.inline_keyboard for b in row]
    assert "🏕️ Вернуться в лагерь" in btns10

    # Возврат в лагерь
    handle_location_5_slug_pit("l5_scout_leave_to_camp", game, uid)
    assert game.active_story_callback is None

    # Повторный вход в логово -> чистое логово
    t_clear, _ = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "На дне котловины яра тихо" in t_clear
    assert game.story_state == "l5_ancient_cleared"


def test_trap_op_damage_scaling():
    """Тест шкалы урона на шаге 4 в зависимости от surroundings_count."""
    game = GameState()
    uid = 108

    # 1. surroundings == 21 -> урон 60
    game.surroundings_count = 21
    game.hp = 100
    t4_21, _ = handle_location_5_slug_pit("l5_trap_op_step4", game, uid)
    assert "Получено урона: 60 единиц." in t4_21
    assert "Благодаря изученным циклам выброса пара" in t4_21
    assert game.hp == 40

    # 2. surroundings == 22 -> урон 40
    game.surroundings_count = 22
    game.hp = 100
    t4_22, _ = handle_location_5_slug_pit("l5_trap_op_step4", game, uid)
    assert "Получено урона: 40 единиц." in t4_22
    assert "Идеально выверенная траектория прыжка" in t4_22
    assert game.hp == 60

    # 3. surroundings >= 23 -> урон 15
    game.surroundings_count = 23
    game.hp = 100
    t4_23, _ = handle_location_5_slug_pit("l5_trap_op_step4", game, uid)
    assert "Получено урона: 15 единиц." in t4_23
    assert "Безупречная предварительная подготовка" in t4_23
    assert game.hp == 85


def test_scout_final_screen_vector_3_balanced():
    """Тест Окна Финала: Вектор 3 (гибрид, habits < 16 and surroundings < 16)."""
    game = GameState()
    uid = 106
    game.intro_seen = True
    game.habits_count = 12
    game.surroundings_count = 11  # Сумма 23

    text, kb = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "Времени на дальнейшие наблюдения не осталось. Капитальный помост достроить не удалось" in text
    assert len(text) <= 500
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "⚔️ Начать позиционный бой" in buttons
    assert "🏕️ Вернуться в лагерь" in buttons

    # Без оружия -> предупреждение
    t_warn, _ = handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    assert "необходимо специальное снаряжение" in t_warn

    # С оружием -> старт боя
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    t_fight, _ = handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    assert getattr(game, "wolf_battle", None) is not None


def test_scout_attack_button_unlock_and_gear_checks():
    """Тест динамики кнопки атаки до 23 исследований и проверок снаряжения."""
    game = GameState()
    uid = 107
    game.intro_seen = True

    # 1. Шаги от 1 до 8: кнопки атаки НЕТ
    game.habits_count = 4
    game.surroundings_count = 4  # Всего 8
    _, kb8 = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    btns8 = [btn.text for row in kb8.inline_keyboard for btn in row]
    assert "⚔️ Атаковать слизня" not in btns8

    # 2. Шаг 9 (habits >= 9): кнопка появляется
    game.habits_count = 9
    game.surroundings_count = 0
    _, kb9 = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    btns9 = [btn.text for row in kb9.inline_keyboard for btn in row]
    assert "⚔️ Атаковать слизня" in btns9

    # 3. Нажатие без снаряжения -> предупреждение
    t_warn, kb_warn = handle_location_5_slug_pit("l5_scout_attack", game, uid)
    assert "необходимо специальное снаряжение" in t_warn
    assert game.story_state == "l5_scout_gear_warning"

    # 4. Нажатие со снаряжением (копьё + крюк) -> начало боя
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    t_fight, _ = handle_location_5_slug_pit("l5_scout_attack", game, uid)
    assert getattr(game, "wolf_battle", None) is not None


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


def test_surroundings_23_events_content_and_mechanics():
    """Тест 23 исследований окрестностей: тексты, проверки инвентаря, списание ресурсов, бонусы."""
    assert len(SURROUNDINGS_EVENTS) == 23

    game = GameState()
    uid = 301
    game.intro_seen = True

    # 1. Шаг 1: осмотр и мысли
    text_obs, _ = handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    assert "Ты часами изучаешь рельеф огромного провала" in text_obs
    assert len(text_obs) <= 500

    text_th, _ = handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert "Глубокая сухая заводь с отвесными краями" in text_th
    assert "📊 Знание местности: 1/23" in text_th
    assert "Всего изучено" not in text_th

    # Прогресс со второй строкой при habits > 0
    game.habits_count = 2
    game.surroundings_count = 1
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    text_th2, _ = handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert "📊 Знание местности: 2/23" in text_th2
    assert "Всего изучено: 4/23" in text_th2

    # 2. Шаг 4 (idx 3): внимательность +1
    game.surroundings_count = 3
    init_obs = game.narrative_karma.get("observation", 0)
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    text_th4, _ = handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert game.narrative_karma.get("observation", 0) == init_obs + 1
    assert "💡 +1 к характеристике «Внимательность»" in text_th4

    # 3. Шаг 9 (idx 8): Крюк (Вариант А — впервые)
    game.surroundings_count = 8
    game.craft_bone_hook_unlocked = False
    game.unlocked_recipes.discard("bone_hook_rope")
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    text_th9, _ = handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert game.craft_bone_hook_unlocked is True
    assert "bone_hook_rope" in game.unlocked_recipes
    assert "необходим костяной крюк на длинной и крепкой кожаной верёвке" in text_th9
    assert "💡 Открыт рецепт: Костяной крюк на кожаной верёвке" in text_th9

    # Шаг 9 (Вариант Б — уже открыт ранее)
    game.surroundings_count = 8
    game.craft_bone_hook_unlocked = True
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    text_th9b, _ = handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert "Тот самый костяной крюк на кожаной верёвке здесь тоже идеально подойдёт" in text_th9b

    # 4. Шаг 11 (idx 10): Блокировка при < 20 веток
    game.surroundings_count = 10
    game.inventory["Ветка"] = 12
    researches_before = game.day_researches_done
    text_block11, kb_block11 = handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    assert "не менее 20 веток" in text_block11
    assert "12/20 шт." in text_block11
    assert game.day_researches_done == researches_before
    btns11 = [b.text for row in kb_block11.inline_keyboard for b in row]
    assert "🔙 Назад к выбору" in btns11

    # Шаг 11: Успешный вход при 25 ветках -> списание ровно 20 веток (осталось 5)
    game.inventory["Ветка"] = 25
    text_obs11, _ = handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    assert "Сгущаются сумерки" in text_obs11
    text_th11, _ = handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert game.inventory["Ветка"] == 5
    assert "Двадцать толстых веток ушли на опоры" in text_th11

    # 5. Шаг 13 (idx 12): Блокировка при < 10 коры
    game.surroundings_count = 12
    game.inventory["Кусок коры"] = 5
    text_block13, _ = handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    assert "не менее 10 кусков коры" in text_block13
    assert "5/10 шт." in text_block13

    # Шаг 13: Успешный вход при 15 коры -> списание ровно 10 кусков коры (осталось 5)
    game.inventory["Кусок коры"] = 15
    text_obs13, _ = handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    assert "На рассвете яр затягивает плотный молочный туман" in text_obs13
    text_th13, _ = handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert game.inventory["Кусок коры"] == 5
    assert "Десять широких пластов коры намертво легли" in text_th13

    # 6. Шаг 16 (idx 15): списание всех сланцевых пластин
    game.surroundings_count = 15
    game.inventory["Сланцевая пластина"] = 7
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert game.inventory["Сланцевая пластина"] == 0

    # 7. Шаг 17 (idx 16): списание всех камней
    game.surroundings_count = 16
    game.inventory["Камень"] = 15
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert game.inventory["Камень"] == 0

    # 8. Шаг 20 (idx 19): флаг готовности пресса
    game.surroundings_count = 19
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    text_th20, _ = handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert game.is_story_flag_set("l5_trap_press_ready")
    assert "💡 Каменный пресс готов к бою" in text_th20

    # 9. Шаги 21-23: модификаторы урона
    game.surroundings_count = 20
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert getattr(game, "l5_trap_damage", None) == 60

    game.surroundings_count = 21
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert getattr(game, "l5_trap_damage", None) == 40

    game.surroundings_count = 22
    handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    text_th23, _ = handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    assert getattr(game, "l5_trap_damage", None) == 15
    assert "💡 Кап ветки — урон при прорыве снижен до 10–15 HP" in text_th23


