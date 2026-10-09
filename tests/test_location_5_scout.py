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
    assert "Крепкий посох" not in game.inventory
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

    # С оружием -> экран дебюта ловушки
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    t_intro, kb_intro = handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    assert "Ты спускаешься в чашу яра, прижимаясь к знакомым расщелинам" in t_intro
    assert "Пора пустить в ход знание местности!" in t_intro
    intro_btns = [btn.text for row in kb_intro.inline_keyboard for btn in row]
    assert "💥 Обрушить подготовленный уступ" in intro_btns
    assert "🏃 Отступить в лагерь" in intro_btns

    # Нажатие [💥 Обрушить подготовленный уступ] -> старт Фазы 1 со срезом HP
    t_fight, kb_fight = handle_location_5_slug_pit("l5_hybrid_trigger_trap", game, uid)
    battle = getattr(game, "wolf_battle", None)
    assert battle is not None
    assert battle["enemy_id"] == "trash_slime_hybrid"
    assert battle["max_hp"] == 2000
    assert 350 <= battle["start_damage"] <= 400
    assert battle["wolf_hp"] == 2000 - battle["start_damage"]
    assert 1600 <= battle["wolf_hp"] <= 1650
    assert f"Мусорный слайм: {battle['wolf_hp']}/2000 HP" in t_fight
    assert "Грохот лавины! Подрубленный сланцевый уступ срывается вниз" in t_fight
    assert f"[Слайм теряет {battle['start_damage']} HP!]" in t_fight
    fight_btns = [btn.text for row in kb_fight.inline_keyboard for btn in row]
    assert "🪝 Бросить крюк в Крупный мусор" in fight_btns
    assert "🪝 Бросить крюк в Мелкий мусор" in fight_btns
    assert "🧗 Спрятаться за каменный монолит" in fight_btns
    assert "🏃 Сбежать в лагерь" in fight_btns


def test_hybrid_trash_battle_full_flow():
    """Полный тест всех фаз гибридного боя (Мусорный слайм, 2000 HP -> 0 HP)."""
    game = GameState()
    uid = 106
    game.intro_seen = True
    game.hp = 100
    game.equipment["hand_right"] = "Охотничье сланцевое копьё"
    game.equipment["weapon"] = "Охотничье сланцевое копьё"
    game.equipment["pocket"] = "Костяной крюк на кожаной верёвке"
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    game.inventory["Светящийся гриб"] = 2

    # Экран дебюта ловушки
    game.equipment["hand_left"] = "Щит из бересты"
    game.inventory["Крепкий посох"] = 1  # Уже был в инвентаре, не должен дублироваться
    t_intro, kb_intro = handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    assert "💥 Обрушить подготовленный уступ" in [b.text for r in kb_intro.inline_keyboard for b in r]

    # Старт боя: обрушение уступа
    t1, kb1 = handle_location_5_slug_pit("l5_hybrid_trigger_trap", game, uid)
    assert "⚔️ Позиционный бой: Мусорный слайм" in t1
    assert "🏃 Уворот:" in t1
    assert game.wolf_battle["phase"] == "1"
    start_hp = game.wolf_battle["wolf_hp"]
    assert 1600 <= start_hp <= 1650

    # Фаза 1: прячемся за монолит (0 урона, слайм мажет, мусор перетасовывается)
    prev_large = game.wolf_battle["large_trash"]
    prev_small = game.wolf_battle["small_trash"]
    t_hide, _ = handle_location_5_slug_pit("l5_hybrid_hide_rock", game, uid)
    assert "Ты укрываешься за каменным монолитом" in t_hide
    assert game.wolf_battle["wolf_hp"] == start_hp
    assert game.hp == 100
    assert (game.wolf_battle["large_trash"] != prev_large) or (game.wolf_battle["small_trash"] != prev_small)

    # Фаза 1 -> Фаза 2А: бросаем крюк в крупный мусор
    t2a, kb2a = handle_location_5_slug_pit("l5_hybrid_hook_large", game, uid)
    assert game.wolf_battle["phase"] == "2A"
    assert "Крюк намертво сел в крупный узел!" in t2a
    btns2a = [btn.text for row in kb2a.inline_keyboard for btn in row]
    assert "💪 Выдрать узел изо всех сил" in btns2a

    # Фаза 2А -> Фаза 3А: силовой рывок
    t3a, kb3a = handle_location_5_slug_pit("l5_hybrid_pull_large", game, uid)
    assert game.wolf_battle["phase"] == "3A"
    assert "Чавкающий хлюп! Крупный мусор выдран наружу!" in t3a
    assert game.wolf_battle["wolf_hp"] <= 1900
    assert game.hp < 100
    assert game.wolf_battle["stun_turns"] in (2, 3)

    # Фаза 3А -> Фаза 3А-Гриб: бросить гриб в дыру
    t_shroom, kb_shroom = handle_location_5_slug_pit("l5_hybrid_shroom_hole", game, uid)
    assert game.wolf_battle["phase"] == "3A_shroom"
    assert game.inventory.get("Светящийся гриб") == 1
    assert "Гриб разорван в дыре!" in t_shroom
    btns_shroom = [btn.text for row in kb_shroom.inline_keyboard for btn in row]
    assert "🗡️ Всадить копьё в оголённое ядро" in btns_shroom

    # Фаза 3А-Гриб -> Крит в ядро (при stun_turns > 0 возвращает в обычную 3A)
    game.wolf_battle["stun_turns"] = 2
    hp_before = game.wolf_battle["wolf_hp"]
    t_crit, _ = handle_location_5_slug_pit("l5_hybrid_crit_core", game, uid)
    assert "КРИТ! Остриё бьёт прямо в сердцевину!" in t_crit
    assert game.wolf_battle["wolf_hp"] <= hp_before - 55
    assert game.wolf_battle["phase"] == "3A"
    assert game.wolf_battle["stun_turns"] == 1

    # Крит при stun_turns == 1 -> схлопывание бреши и возврат в Фазу 1
    t_crit_close, _ = handle_location_5_slug_pit("l5_hybrid_crit_core", game, uid)
    assert "Слайм стянул мусор и закрыл брешь!" in t_crit_close
    assert game.wolf_battle["phase"] == "1"

    # Фаза 2Б: срыв мелкого мусора
    t2b, kb2b = handle_location_5_slug_pit("l5_hybrid_hook_small", game, uid)
    assert game.wolf_battle["phase"] == "2B"
    assert "Ты выдёргиваешь мелкий мусор" in t2b
    btns2b = [btn.text for row in kb2b.inline_keyboard for btn in row]
    assert "🧗 Уйти перекатом за каменный монолит" in btns2b
    assert "🛡️ Сгруппироваться на глине" in btns2b

    # Уход перекатом за монолит
    t_roll, _ = handle_location_5_slug_pit("l5_hybrid_roll_rock", game, uid)
    assert "Ты уходишь перекатом за каменный монолит!" in t_roll
    assert game.wolf_battle["phase"] == "1"

    # Проверка перехода на Фазу 5 (Поломка крюка при HP <= 400)
    game.wolf_battle["wolf_hp"] = 400
    t5, kb5 = handle_location_5_slug_pit("l5_hybrid_hide_rock", game, uid)
    assert game.wolf_battle["phase"] == "5"
    assert "С сухим треском крюк разлетается в щепки!" in t5
    assert "Костяной крюк на кожаной верёвке" not in game.inventory
    assert "Костяной крюк на кожаной верёвке" not in game.equipment.values()
    btns5 = [btn.text for row in kb5.inline_keyboard for btn in row]
    assert "🗡️ Встать в боевую стойку со сланцевым копьём" in btns5

    # Фаза 5 -> Фаза 6: Боевая стойка
    t6, kb6 = handle_location_5_slug_pit("l5_hybrid_core_stance", game, uid)
    assert game.wolf_battle["phase"] == "6"
    assert "Слайм хлещет мусорным выростом" in t6
    btns6 = [btn.text for row in kb6.inline_keyboard for btn in row]
    assert "🗡️ Выпад в открытое ядро" in btns6
    assert "🗡️ Выпад в мусорный вырост" in btns6
    assert "🧗 Спрятаться за каменным монолитом" in btns6
    assert "🔙 Отступить в сухую промоину" in btns6

    # Маневры за камень и в промоину (0 урона)
    t_core_hide, _ = handle_location_5_slug_pit("l5_hybrid_core_hide", game, uid)
    assert "Ты спрятался за каменным монолитом!" in t_core_hide
    t_core_back, _ = handle_location_5_slug_pit("l5_hybrid_core_back", game, uid)
    assert "Ты отступил в сухую промоину" in t_core_back

    # Выпад в открытое ядро -> переход в Фазу 7 (Шок ядра)
    t7, kb7 = handle_location_5_slug_pit("l5_hybrid_hit_core", game, uid)
    assert game.wolf_battle["phase"] == "7"
    assert "ТОЧНО В ЦЕЛЬ! Копьё бьёт в ядро!" in t7
    assert "Тварь парализована шоком на 1 ход!" in t7
    btns7 = [btn.text for row in kb7.inline_keyboard for btn in row]
    assert "🗡️ Повторный выпад в ядро" in btns7
    assert "🍄 Бросить гриб на ядро" in btns7
    assert "🧪 Лечение" in btns7

    # Бросок гриба на ядро во время шока (60..70 HP)
    game.wolf_battle["wolf_hp"] = 50  # Достаточно для финального добивания грибом
    t_win, kb_win = handle_location_5_slug_pit("l5_hybrid_core_shroom", game, uid)

    # Проверка Фазы 8 (Финал)
    assert game.wolf_battle is None
    assert "Решающий удар раскалывает янтарное ядро пополам!" in t_win
    assert "В руках остаётся лишь гладкий Крепкий посох." in t_win
    assert "Открыта новая локация: Мохнатая пещера." in t_win
    assert "(L6)" not in t_win

    # Проверка предметов и экипировки: левая рука не тронута, посох не сдублирован!
    assert "Охотничье сланцевое копьё" not in game.inventory
    assert "Охотничье сланцевое копьё" not in game.equipment.values()
    assert game.equipment.get("hand_right") == "Крепкий посох"
    assert game.equipment.get("hand_left") == "Щит из бересты"
    assert game.inventory.get("Крепкий посох") == 1

    # Проверка сюжетных флагов
    assert game.is_story_flag_set("trash_slime_defeated")
    assert game.is_story_flag_set("boss_trash_slime_defeated")
    assert game.is_story_flag_set("l5_ancient_defeated")
    assert game.is_story_flag_set("l6_unlocked")
    assert "Мохнатая пещера" in game.unlocked_locations

    btns_win = [btn.text for row in kb_win.inline_keyboard for btn in row]
    assert "🏕️ Вернуться в лагерь" in btns_win

    # Возврат в лагерь и очистка логова
    handle_location_5_slug_pit("l5_scout_leave_to_camp", game, uid)
    assert game.active_story_callback is None

    t_cleared, _ = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "На дне котловины яра тихо" in t_cleared


def test_hybrid_trash_battle_extra_branches():
    """Тест дополнительных веток: уколы копьём, лечение, увороты и побег."""
    game = GameState()
    uid = 106
    game.intro_seen = True
    game.hp = 50
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    game.inventory["Янтарное зелье"] = 1

    # Инициализация боя: экран дебюта и спуск ловушки
    t_intro, kb_intro = handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    assert "подтесанный сланцевый уступ" in t_intro
    handle_location_5_slug_pit("l5_hybrid_trigger_trap", game, uid)
    assert game.wolf_battle is not None

    # Фаза 2А -> 3А
    handle_location_5_slug_pit("l5_hybrid_hook_large", game, uid)
    handle_location_5_slug_pit("l5_hybrid_pull_large", game, uid)

    # Выпад копьём в дыру
    game.wolf_battle["stun_turns"] = 2
    t_spear, _ = handle_location_5_slug_pit("l5_hybrid_spear_hole", game, uid)
    assert "Ты наносишь выпад копьём в дыру!" in t_spear
    assert game.wolf_battle["stun_turns"] == 1
    assert game.wolf_battle["phase"] == "3A"

    # Лечение во время 3А
    t_heal, _ = handle_location_5_slug_pit("l5_hybrid_heal", game, uid)
    assert "Янтарное зелье" in t_heal
    assert game.hp > 50
    assert game.wolf_battle["stun_turns"] == 0
    assert game.wolf_battle["phase"] == "1"

    # Фаза 2Б: сгруппироваться на глине
    handle_location_5_slug_pit("l5_hybrid_hook_small", game, uid)
    assert game.wolf_battle["phase"] == "2B"
    t_brace, _ = handle_location_5_slug_pit("l5_hybrid_brace", game, uid)
    assert ("Ты успел увернуться от навала!" in t_brace) or ("Навал сбивает тебя с ног!" in t_brace)
    assert game.wolf_battle["phase"] == "1"

    # Фаза 6: удар по выросту
    game.wolf_battle["phase"] = "6"
    t_trash, _ = handle_location_5_slug_pit("l5_hybrid_hit_trash", game, uid)
    assert ("Ты увернулся от встречного удара хлама!" in t_trash) or ("Удар мусором сбивает выпад!" in t_trash)

    # Фаза 7: повторный выпад и лечение
    game.wolf_battle["phase"] = "7"
    t_repeat, _ = handle_location_5_slug_pit("l5_hybrid_core_repeat", game, uid)
    assert "Повторный выпад сотрясает ядро!" in t_repeat
    assert game.wolf_battle["phase"] == "6"

    game.wolf_battle["phase"] = "7"
    t_core_heal, _ = handle_location_5_slug_pit("l5_hybrid_core_heal", game, uid)
    assert "Тварь в шоке, ты спокойно перевязываешь раны." in t_core_heal
    assert game.wolf_battle["phase"] == "6"

    # Сбежать в лагерь
    t_escape, kb_esc = handle_location_5_slug_pit("l5_ancient_escape", game, uid)
    assert "Задыхаясь от едких испарений" in t_escape
    assert game.wolf_battle is None
    btns_esc = [b.text for r in kb_esc.inline_keyboard for b in r]
    assert "🏕️ Вернуться в лагерь" in btns_esc


def test_hybrid_trash_battle_player_death_handling():
    """Тест обработки гибели персонажа на опасных фазах боя (сброс сессии и экран смерти)."""
    game = GameState()
    uid = 106
    game.intro_seen = True
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1

    # 1. Смерть при вырывании узла (Фаза 2А -> 3А)
    handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    handle_location_5_slug_pit("l5_hybrid_trigger_trap", game, uid)
    game.hp = 1
    handle_location_5_slug_pit("l5_hybrid_hook_large", game, uid)
    t_death, kb_death = handle_location_5_slug_pit("l5_hybrid_pull_large", game, uid)
    assert game.hp == 0
    assert game.wolf_battle is None
    assert game.story_state is None
    assert "Тварь погребла тебя под тоннами едкой жижи" in t_death
    death_cbs = [b.callback_data for r in kb_death.inline_keyboard for b in r]
    assert "start_new_game_confirmed" in death_cbs

    # 2. Смерть при неудачном сгруппировании на глине (Фаза 2Б)
    game.hp = 2
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    handle_location_5_slug_pit("l5_hybrid_trigger_trap", game, uid)
    game.hp = 2
    handle_location_5_slug_pit("l5_hybrid_hook_small", game, uid)
    # Намеренно ставим уворот 0, чтобы гарантировать навал
    game.equipment = {}
    t_death2, _ = handle_location_5_slug_pit("l5_hybrid_brace", game, uid)
    assert game.hp == 0
    assert game.wolf_battle is None
    assert "Тварь погребла тебя под тоннами едкой жижи" in t_death2


def test_habits_trash_battle_full_flow():
    """Полный тест Вектора 1: Тактический бой по повадкам (2000 HP -> 0 HP)."""
    game = GameState()
    uid = 108
    game.intro_seen = True
    game.hp = 100
    game.habits_count = 16
    game.equipment["hand_right"] = "Охотничье сланцевое копьё"
    game.equipment["hand_left"] = "Щит из бересты"
    game.equipment["pocket"] = "Костяной крюк на кожаной верёвке"
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    game.inventory["Светящийся гриб"] = 2
    game.inventory["Крепкий посох"] = 1

    # 1. Старт боя
    t1, kb1 = handle_location_5_slug_pit("l5_scout_final_attack_habits", game, uid)
    assert game.wolf_battle is not None
    assert game.wolf_battle["enemy_id"] == "trash_slime_habits"
    assert game.wolf_battle["wolf_hp"] == 2000
    assert game.wolf_battle["max_hp"] == 2000
    assert "⚔️ Тактический бой: Мусорный слайм" in t1
    assert "2000/2000 HP" in t1

    # 2. Фаза 1: кнопки краткие и ёмкие
    btns1 = [b.text for r in kb1.inline_keyboard for b in r]
    assert "🪝 Бросить крюк" in btns1
    assert "🛡️ Выждать момент" in btns1
    assert "🏃 Сбежать в лагерь" in btns1

    # 3. Выждать момент (0 урона, смена узла)
    t_wait, _ = handle_location_5_slug_pit("l5_habits_wait", game, uid)
    assert "Ты выжидаешь такт пульсации" in t_wait
    assert game.wolf_battle["wolf_hp"] == 2000
    assert game.hp == 100

    # 4. Фаза 1 -> Фаза 2 (Бросить крюк)
    t2, kb2 = handle_location_5_slug_pit("l5_habits_hook", game, uid)
    assert game.wolf_battle["phase"] == "2"
    btns2 = [b.text for r in kb2.inline_keyboard for b in r]
    assert "💪 Выдрать" in btns2

    # 5. Фаза 2 -> Фаза 3 (Выдрать узел: 80..100 урон слайму, 1..3 игроку)
    t3, kb3 = handle_location_5_slug_pit("l5_habits_pull", game, uid)
    assert game.wolf_battle["phase"] == "3"
    assert 1900 <= game.wolf_battle["wolf_hp"] <= 1920
    assert 97 <= game.hp <= 99
    assert game.wolf_battle["stun_turns"] in (2, 3)
    btns3 = [b.text for r in kb3.inline_keyboard for b in r]
    assert "🗡️ Ударить копьём" in btns3
    assert "🍄 Бросить гриб" in btns3
    assert "🧪 Лечение" in btns3

    # 6. Фаза 3 -> 3-Гриб (Бросить гриб)
    t_shroom, kb_shroom = handle_location_5_slug_pit("l5_habits_shroom", game, uid)
    assert game.wolf_battle["phase"] == "3_shroom"
    assert game.inventory.get("Светящийся гриб") == 1
    assert "Гриб разорван в ране!" in t_shroom
    btns_shroom = [b.text for r in kb_shroom.inline_keyboard for b in r]
    assert "🗡️ Ударить копьём" in btns_shroom

    # 7. Крит копьём в Фазе 3-Гриб (85..105 урон слайму, 2 игроку)
    game.wolf_battle["stun_turns"] = 2
    hp_b = game.wolf_battle["wolf_hp"]
    player_b = game.hp
    t_crit, _ = handle_location_5_slug_pit("l5_habits_crit_spear", game, uid)
    assert "КРИТ! Знание анатомии направляет удар точно в сердцевину!" in t_crit
    assert game.wolf_battle["wolf_hp"] <= hp_b - 85
    assert game.hp == player_b - 2
    assert game.wolf_battle["phase"] == "3"
    assert game.wolf_battle["stun_turns"] == 1

    # 8. Обычный укол копьём при stun_turns == 1 -> закрытие бреши и возврат в Фазу 1
    t_close, _ = handle_location_5_slug_pit("l5_habits_spear", game, uid)
    assert "Слайм стянул жижу и закрыл дыру!" in t_close
    assert game.wolf_battle["phase"] == "1"

    # 9. Рубеж HP <= 400: поломка крюка при попытке броска
    game.wolf_battle["wolf_hp"] = 400
    t5, kb5 = handle_location_5_slug_pit("l5_habits_hook", game, uid)
    assert game.wolf_battle["phase"] == "5"
    assert "Крюк разлетается в щепки!" in t5
    assert "Костяной крюк на кожаной верёвке" not in game.inventory
    assert "Костяной крюк на кожаной верёвке" not in game.equipment.values()
    btns5 = [b.text for r in kb5.inline_keyboard for b in r]
    assert "🗡️ Встать в стойку" in btns5

    # 10. Фаза 5 -> Фаза 6: Атака ядра
    t6, kb6 = handle_location_5_slug_pit("l5_habits_stance", game, uid)
    assert game.wolf_battle["phase"] == "6"
    assert "Слайм вздувается и хлещет массой" in t6
    btns6 = [b.text for r in kb6.inline_keyboard for b in r]
    assert "🗡️ Ударить в ядро" in btns6
    assert "🗡️ Ударить в накат" in btns6
    assert "🛡️ Увернуться" in btns6

    # 11. Уворот в Фазе 6 (0 урона)
    t_dodge, _ = handle_location_5_slug_pit("l5_habits_dodge", game, uid)
    assert "Ты уходишь из-под удара по знанию ритма" in t_dodge

    # 12. Ударить в открытое ядро -> Фаза 7 (Шок ядра)
    t7, kb7 = handle_location_5_slug_pit("l5_habits_hit_core", game, uid)
    assert game.wolf_battle["phase"] == "7"
    assert "ТОЧНО В ЦЕЛЬ! Остриё вонзается в ядро!" in t7
    assert "Тварь ошеломлена на 1 ход!" in t7
    btns7 = [b.text for r in kb7.inline_keyboard for b in r]
    assert "🗡️ Ударить копьём" in btns7
    assert "🍄 Бросить гриб" in btns7
    assert "🧪 Лечение" in btns7

    # 13. Бросок гриба в ядро во время шока (80..95 урона)
    game.wolf_battle["wolf_hp"] = 70  # Для финального добивания
    t_win, kb_win = handle_location_5_slug_pit("l5_habits_core_shroom", game, uid)

    # 14. Проверка победы (Фаза 8)
    assert game.wolf_battle is None
    assert "Точный укол раскалывает янтарное ядро пополам!" in t_win
    assert "В руках остаётся лишь гладкое Крепкое древко (Крепкий посох)." in t_win
    assert "Открыта новая локация: Мохнатая пещера." in t_win

    # Проверка экипировки: левая рука не тронута, в правой Крепкий посох, копья нет
    assert "Охотничье сланцевое копьё" not in game.inventory
    assert "Охотничье сланцевое копьё" not in game.equipment.values()
    assert game.equipment.get("hand_right") == "Крепкий посох"
    assert game.equipment.get("hand_left") == "Щит из бересты"
    assert game.inventory.get("Крепкий посох") == 1

    # Проверка флагов
    assert game.is_story_flag_set("trash_slime_defeated")
    assert game.is_story_flag_set("boss_trash_slime_defeated")
    assert game.is_story_flag_set("l5_ancient_defeated")
    assert game.is_story_flag_set("l6_unlocked")
    assert "Мохнатая пещера" in game.unlocked_locations


def test_habits_trash_battle_player_death():
    """Тест гибели игрока в тактическом бою по повадкам (Вектор 1)."""
    game = GameState()
    uid = 109
    game.intro_seen = True
    game.habits_count = 16
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1

    # 1. Гибель при силовом рывке
    handle_location_5_slug_pit("l5_scout_final_attack_habits", game, uid)
    handle_location_5_slug_pit("l5_habits_hook", game, uid)
    game.hp = 1
    t_death, kb_death = handle_location_5_slug_pit("l5_habits_pull", game, uid)
    assert game.hp == 0
    assert game.wolf_battle is None
    assert "Тварь погребла тебя под тоннами едкой жижи" in t_death
    death_cbs = [b.callback_data for r in kb_death.inline_keyboard for b in r]
    assert "start_new_game_confirmed" in death_cbs


def test_scout_cross_launch_protection():
    """Тест защиты от перекрестного запуска веток и повторного боя после победы."""
    game = GameState()
    uid = 110
    game.intro_seen = True
    game.equipment["hand_right"] = "Охотничье сланцевое копьё"
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    game.inventory["Спелые лесные ягоды"] = 5
    game.inventory["Светящийся гриб"] = 2

    # 1. Вектор 1 (habits = 17, surroundings = 6): нельзя запустить Вектор 2 или Вектор 3
    game.habits_count = 17
    game.surroundings_count = 6
    t_v2_fail, _ = handle_location_5_slug_pit("l5_scout_final_trap_surroundings", game, uid)
    assert "Исследования завершены. Ты знаешь эту гору жижи вдоль и поперёк" in t_v2_fail
    t_v3_fail, _ = handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    assert "Исследования завершены. Ты знаешь эту гору жижи вдоль и поперёк" in t_v3_fail
    t_v1_ok, _ = handle_location_5_slug_pit("l5_scout_final_attack_habits", game, uid)
    assert game.wolf_battle is not None
    assert game.wolf_battle["enemy_id"] == "trash_slime_habits"
    game.wolf_battle = None

    # 2. Вектор 2 (surroundings = 17, habits = 6): нельзя запустить Вектор 1 или Вектор 3
    game.habits_count = 6
    game.surroundings_count = 17
    t_v1_fail, _ = handle_location_5_slug_pit("l5_scout_final_attack_habits", game, uid)
    assert "Все приготовления завершены. Над дном котловины нависает тяжелейший каменный пресс" in t_v1_fail
    t_v3_fail2, _ = handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    assert "Все приготовления завершены. Над дном котловины нависает тяжелейший каменный пресс" in t_v3_fail2
    t_v2_ok, _ = handle_location_5_slug_pit("l5_scout_final_trap_surroundings", game, uid)
    assert game.story_state == "l5_trap_op_step1"

    # 3. Вектор 3 (habits = 12, surroundings = 11): нельзя запустить Вектор 1 или Вектор 2
    game.habits_count = 12
    game.surroundings_count = 11
    t_v1_fail3, _ = handle_location_5_slug_pit("l5_scout_final_attack_habits", game, uid)
    assert "Времени на дальнейшие наблюдения не осталось." in t_v1_fail3
    t_v2_fail3, _ = handle_location_5_slug_pit("l5_scout_final_trap_surroundings", game, uid)
    assert "Времени на дальнейшие наблюдения не осталось." in t_v2_fail3
    t_v3_ok, kb_v3_ok = handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    assert "💥 Обрушить подготовленный уступ" in [b.text for r in kb_v3_ok.inline_keyboard for b in r]

    # 4. После победы над боссом: все три точки входа блокируются и выводят зачищенное логово
    game.set_story_flag("trash_slime_defeated", True)
    game.set_story_flag("l5_ancient_defeated", True)
    for cb in ("l5_scout_final_attack_habits", "l5_scout_final_trap_surroundings", "l5_scout_final_attack_balanced"):
        t_cleared, _ = handle_location_5_slug_pit(cb, game, uid)
        assert "На дне котловины яра тихо. Останки Древнего слайма рассосались в грязи" in t_cleared
        assert "(L6)" not in t_cleared
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


def test_post_boss_flow_and_locations_kb_pin():
    """Тест флоу победы над Мусорным слаймом, возврата в лагерь и пина в get_locations_kb."""
    from keyboards import get_locations_kb
    from story.location_stories import handle_story
    from story.locations.loc5_slug_pit import _render_habits_win, _render_hybrid_win

    # 1. Проверка строго 1 кнопки на всех трёх экранах победы
    game = GameState()
    game.unlocked_locations = ["Стартовый лес", "Ручей со змеями", "Скромная лощина", "Просека охотников", "Яр Слаймов"]
    uid = 999

    # Вектор 1 (Повадки)
    text_v1, kb_v1 = _render_habits_win(game)
    btns_v1 = [b.text for row in kb_v1.inline_keyboard for b in row]
    cbs_v1 = [b.callback_data for row in kb_v1.inline_keyboard for b in row]
    assert btns_v1 == ["🏕️ Вернуться в лагерь"]
    assert cbs_v1 == ["l5_scout_leave_to_camp"]

    # Вектор 2 Шаг 10
    text_v2, kb_v2 = handle_location_5_slug_pit("l5_trap_op_step10", game, uid)
    btns_v2 = [b.text for row in kb_v2.inline_keyboard for b in row]
    cbs_v2 = [b.callback_data for row in kb_v2.inline_keyboard for b in row]
    assert btns_v2 == ["🏕️ Вернуться в лагерь"]
    assert cbs_v2 == ["l5_scout_leave_to_camp"]

    # Вектор 3 (Гибрид)
    text_v3, kb_v3 = _render_hybrid_win(game)
    btns_v3 = [b.text for row in kb_v3.inline_keyboard for b in row]
    cbs_v3 = [b.callback_data for row in kb_v3.inline_keyboard for b in row]
    assert btns_v3 == ["🏕️ Вернуться в лагерь"]
    assert cbs_v3 == ["l5_scout_leave_to_camp"]

    # 2. Возврат в лагерь через l5_scout_leave_to_camp:
    # Приветственное системное уведомление об открытии Мохнатой пещеры
    text_camp, kb_camp = handle_location_5_slug_pit("l5_scout_leave_to_camp", game, uid)
    assert text_camp.startswith("🎉 Открыта новая локация: Мохнатая пещера")
    assert game.current_location == "Стартовый лес"
    assert not any("яр" in loc.lower() or "слизн" in loc.lower() or "слайм" in loc.lower() for loc in game.unlocked_locations)
    assert "Мохнатая пещера" in game.unlocked_locations

    # 3. Повторная попытка войти в L5 блокируется
    game.event_log = []
    text_blocked, _ = handle_location_5_slug_pit("slug_pit_start", game, uid)
    assert any("Яр Слаймов опустел и больше недоступен" in l for l in game.event_log)

    # 4. Проверка меню локаций (get_locations_kb):
    # - Яр Слаймов отсутствует
    # - Номера последовательные (1, 2, 3, 4, 5)
    # - Стартовый лес имеет маркер « 📍» и callback="already_here"
    loc_kb = get_locations_kb(game)
    btn_texts = [b.text for row in loc_kb.inline_keyboard for b in row]
    btn_cbs = [b.callback_data for row in loc_kb.inline_keyboard for b in row]

    assert "1. 🌲 Стартовый лес 📍" in btn_texts
    assert "2. 🏞️ Ручей со змеями" in btn_texts
    assert "3. ⛰️ Скромная лощина" in btn_texts
    assert "4. 🏹 Просека охотников" in btn_texts
    assert "5. 🦇 Мохнатая пещера" in btn_texts
    assert not any("яр" in t.lower() or "слизн" in t.lower() or "слайм" in t.lower() for t in btn_texts)
    assert "already_here" in btn_cbs

    # 5. При перемещении в Мохнатую пещеру пин перемещается на нее
    game.current_location = "Мохнатая пещера"
    loc_kb2 = get_locations_kb(game)
    btn_texts2 = [b.text for row in loc_kb2.inline_keyboard for b in row]
    assert "1. 🌲 Стартовый лес" in btn_texts2
    assert "5. 🦇 Мохнатая пещера 📍" in btn_texts2

    # 6. Клик по already_here возвращает уведомление и не ломает экран
    t_ah, _ = handle_story("already_here", game, uid)
    assert any("Ты уже находишься в этой локации" in l for l in game.event_log)


def test_l5_blocked_entry_clears_fsm_story_triggers():
    """Тест: при попытке входа на пройденную L5 FSM-состояния гарантированно сбрасываются."""
    from main import is_in_active_story
    from story.location_stories import handle_story

    game = GameState()
    uid = 99999
    game.set_story_flag("boss_trash_slime_defeated", True)

    # Имитируем зависшие сюжетные и боевые состояния
    game.active_story_callback = "l5_1a"
    game.story_state = "l5_1a"
    game.wolf_battle = {"enemy_id": "trash_slime", "hp": 50}
    assert is_in_active_story(game) is True

    # 1. Вызов через handle_location_5_slug_pit
    text, kb = handle_location_5_slug_pit("slug_pit_start", game, uid)
    assert any("Яр Слаймов опустел и больше недоступен" in l for l in game.event_log)
    assert game.active_story_callback is None
    assert game.story_state is None
    assert game.wolf_battle is None
    assert is_in_active_story(game) is False

    # 2. Вызов через handle_story("location_enter_5")
    game.active_story_callback = "slug_pit_start"
    game.story_state = "slug_pit_start"
    game.wolf_battle = {"enemy_id": "trash_slime", "hp": 50}
    assert is_in_active_story(game) is True

    text2, kb2 = handle_story("location_enter_5", game, uid)
    assert game.active_story_callback is None
    assert game.story_state is None
    assert game.wolf_battle is None
    assert is_in_active_story(game) is False


def _assert_valid_screen(text, kb, expected_next_cb=None):
    """Вспомогательная проверка валидности текста, клавиатуры и отсутствия битых коллбэков."""
    assert isinstance(text, str) and len(text.strip()) > 0
    assert kb is not None
    all_cbs = []
    for row in kb.inline_keyboard:
        for btn in row:
            assert isinstance(btn.text, str) and len(btn.text.strip()) > 0
            assert isinstance(btn.callback_data, str) and len(btn.callback_data.strip()) > 0
            assert not any(err in btn.callback_data for err in ["None", "undefined", "{", "}"])
            all_cbs.append(btn.callback_data)
    if expected_next_cb:
        assert expected_next_cb in all_cbs, f"Ожидался callback '{expected_next_cb}' среди {all_cbs}"
    return all_cbs


def test_l5_vector_2_trap_operation_e2e_happy_path():
    """Сквозной интеграционный тест спецоперации Вектора 2 (Окрестности): от l5_trap_op_start до лагеря."""
    game = GameState()
    uid = 7001
    game.intro_seen = True
    game.surroundings_count = 23
    game.habits_count = 0
    game.hp = 100
    game.equipment["hand_right"] = "Охотничье сланцевое копьё"
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    game.inventory["Лесная ягода"] = 7
    game.inventory["Светящийся гриб"] = 4
    game.unlocked_locations = ["Стартовый лес", "Ручей со змеями", "Скромная лощина", "Просека охотников", "Яр Слаймов"]

    # Шаг 0 -> Шаг 1: списание 5 ягод
    t1, kb1 = handle_location_5_slug_pit("l5_trap_op_start", game, uid)
    _assert_valid_screen(t1, kb1, "l5_trap_op_step2")
    assert game.story_state == "l5_trap_op_step1"
    assert game.inventory.get("Лесная ягода") == 2
    assert game.inventory.get("Костяной крюк на кожаной верёвке") == 1
    assert game.inventory.get("Светящийся гриб") == 4

    # Шаг 1 -> Шаг 2: подъем к узлу
    t2, kb2 = handle_location_5_slug_pit("l5_trap_op_step2", game, uid)
    _assert_valid_screen(t2, kb2, "l5_trap_op_step3")
    assert game.story_state == "l5_trap_op_step2"

    # Шаг 2 -> Шаг 3: поломка и удаление костяного крюка
    t3, kb3 = handle_location_5_slug_pit("l5_trap_op_step3", game, uid)
    _assert_valid_screen(t3, kb3, "l5_trap_op_step4")
    assert game.story_state == "l5_trap_op_step3"
    assert "Костяной крюк на кожаной верёвке" not in game.inventory
    assert "Костяной крюк на кожаной верёвке" not in game.equipment.values()

    # Шаг 3 -> Шаг 4: обвал и получение урона (при капе 23 урон минимален: 15 HP)
    t4, kb4 = handle_location_5_slug_pit("l5_trap_op_step4", game, uid)
    _assert_valid_screen(t4, kb4, "l5_trap_op_step5")
    assert game.story_state == "l5_trap_op_step4"
    assert game.hp == 85

    # Шаг 4 -> Шаг 5: подъем на ноги
    t5, kb5 = handle_location_5_slug_pit("l5_trap_op_step5", game, uid)
    _assert_valid_screen(t5, kb5, "l5_trap_op_step6")
    assert game.story_state == "l5_trap_op_step5"

    # Шаг 5 -> Шаг 6: списание ВСЕХ светящихся грибов
    t6, kb6 = handle_location_5_slug_pit("l5_trap_op_step6", game, uid)
    _assert_valid_screen(t6, kb6, "l5_trap_op_step7")
    assert game.story_state == "l5_trap_op_step6"
    assert "Светящийся гриб" not in game.inventory

    # Шаг 6 -> Шаг 7: первый удар
    t7, kb7 = handle_location_5_slug_pit("l5_trap_op_step7", game, uid)
    _assert_valid_screen(t7, kb7, "l5_trap_op_step8")
    assert game.story_state == "l5_trap_op_step7"

    # Шаг 7 -> Шаг 8: сокрушение ядра
    t8, kb8 = handle_location_5_slug_pit("l5_trap_op_step8", game, uid)
    _assert_valid_screen(t8, kb8, "l5_trap_op_step9")
    assert game.story_state == "l5_trap_op_step8"

    # Шаг 8 -> Шаг 9: растворение копья, выдача и экипировка «Крепкий посох», флаги победы
    t9, kb9 = handle_location_5_slug_pit("l5_trap_op_step9", game, uid)
    _assert_valid_screen(t9, kb9, "l5_trap_op_step10")
    assert game.story_state == "l5_trap_op_step9"
    assert "Охотничье сланцевое копьё" not in game.inventory
    assert "Охотничье сланцевое копьё" not in game.equipment.values()
    assert game.equipment.get("hand_right") == "Крепкий посох"
    assert "Крепкий посох" not in game.inventory
    assert game.is_story_flag_set("trash_slime_defeated")
    assert game.is_story_flag_set("boss_trash_slime_defeated")
    assert game.is_story_flag_set("l5_ancient_defeated")
    assert not any("яр" in l.lower() or "слайм" in l.lower() for l in game.unlocked_locations)

    # Шаг 9 -> Шаг 10: разблокировка локации L6 «Мохнатая пещера»
    t10, kb10 = handle_location_5_slug_pit("l5_trap_op_step10", game, uid)
    _assert_valid_screen(t10, kb10, "l5_scout_leave_to_camp")
    assert game.story_state == "l5_trap_op_step10"
    assert game.is_story_flag_set("l6_unlocked")
    assert "Мохнатая пещера" in game.unlocked_locations

    # Финал спецоперации: возврат в лагерь
    t_camp, kb_camp = handle_location_5_slug_pit("l5_scout_leave_to_camp", game, uid)
    _assert_valid_screen(t_camp, kb_camp)
    assert game.current_location == "Стартовый лес"
    assert game.active_story_callback is None
    assert game.story_state is None
    assert game.wolf_battle is None


def test_l5_vector_1_habits_battle_e2e_happy_path():
    """Сквозной интеграционный тест тактического боя Вектора 1 (Повадки) от старта до победы и выхода в лагерь."""
    game = GameState()
    uid = 7002
    game.intro_seen = True
    game.habits_count = 23
    game.surroundings_count = 0
    game.hp = 100
    game.equipment["hand_right"] = "Охотничье сланцевое копьё"
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    game.inventory["Светящийся гриб"] = 2
    game.unlocked_locations = ["Стартовый лес", "Ручей со змеями", "Скромная лощина", "Просека охотников", "Яр Слаймов"]

    # 1. Старт боя
    t1, kb1 = handle_location_5_slug_pit("l5_scout_final_attack_habits", game, uid)
    _assert_valid_screen(t1, kb1, "l5_habits_hook")
    assert game.wolf_battle is not None
    assert game.wolf_battle["enemy_id"] == "trash_slime_habits"
    assert game.wolf_battle["wolf_hp"] == 2000
    assert game.wolf_battle["phase"] == "1"

    # 2. Фаза 1: Бросить крюк
    t2, kb2 = handle_location_5_slug_pit("l5_habits_hook", game, uid)
    _assert_valid_screen(t2, kb2, "l5_habits_pull")
    assert game.wolf_battle["phase"] == "2"

    # 3. Фаза 2: Выдрать узел -> Фаза 3 (ошеломление)
    t3, kb3 = handle_location_5_slug_pit("l5_habits_pull", game, uid)
    _assert_valid_screen(t3, kb3, "l5_habits_spear")
    assert game.wolf_battle["phase"] == "3"
    assert game.wolf_battle["wolf_hp"] < 2000

    # 4. Фаза 3: Ударить копьем
    t3b, kb3b = handle_location_5_slug_pit("l5_habits_spear", game, uid)
    _assert_valid_screen(t3b, kb3b)

    # 5. Переход в Фазу 5 при здоровье босса <= 400
    game.wolf_battle["wolf_hp"] = 350
    game.wolf_battle["phase"] = "1"
    t5, kb5 = handle_location_5_slug_pit("l5_habits_hook", game, uid)
    _assert_valid_screen(t5, kb5, "l5_habits_stance")
    assert game.wolf_battle["phase"] == "5"
    # Крюк ломается и удаляется
    assert "Костяной крюк на кожаной верёвке" not in game.inventory
    assert "Костяной крюк на кожаной верёвке" not in game.equipment.values()

    # 6. Фаза 5 -> Фаза 6: Встать в стойку
    t6, kb6 = handle_location_5_slug_pit("l5_habits_stance", game, uid)
    _assert_valid_screen(t6, kb6, "l5_habits_hit_core")
    assert game.wolf_battle["phase"] == "6"

    # 7. Фаза 6: Победный удар в ядро
    game.wolf_battle["wolf_hp"] = 15
    t_win, kb_win = handle_location_5_slug_pit("l5_habits_hit_core", game, uid)
    _assert_valid_screen(t_win, kb_win, "l5_scout_leave_to_camp")
    assert game.wolf_battle is None
    assert "Охотничье сланцевое копьё" not in game.inventory
    assert "Охотничье сланцевое копьё" not in game.equipment.values()
    assert game.equipment.get("hand_right") == "Крепкий посох"
    assert "Крепкий посох" not in game.inventory
    assert game.is_story_flag_set("trash_slime_defeated")
    assert game.is_story_flag_set("boss_trash_slime_defeated")
    assert game.is_story_flag_set("l5_ancient_defeated")
    assert game.is_story_flag_set("l6_unlocked")
    assert "Мохнатая пещера" in game.unlocked_locations
    assert not any("яр" in l.lower() or "слайм" in l.lower() for l in game.unlocked_locations)

    # 8. Выход в лагерь
    t_camp, kb_camp = handle_location_5_slug_pit("l5_scout_leave_to_camp", game, uid)
    _assert_valid_screen(t_camp, kb_camp)
    assert game.current_location == "Стартовый лес"
    assert game.active_story_callback is None
    assert game.story_state is None
    assert game.wolf_battle is None


def test_l5_vector_3_hybrid_battle_e2e_happy_path():
    """Сквозной интеграционный тест позиционного боя Вектора 3 (Гибрид) от старта до победы и выхода в лагерь."""
    game = GameState()
    uid = 7003
    game.intro_seen = True
    game.habits_count = 11
    game.surroundings_count = 12
    game.hp = 100
    game.equipment["hand_right"] = "Охотничье сланцевое копьё"
    game.inventory["Охотничье сланцевое копьё"] = 1
    game.inventory["Костяной крюк на кожаной верёвке"] = 1
    game.inventory["Светящийся гриб"] = 2
    game.unlocked_locations = ["Стартовый лес", "Ручей со змеями", "Скромная лощина", "Просека охотников", "Яр Слаймов"]

    # 1. Экран дебюта ловушки
    t_intro, kb_intro = handle_location_5_slug_pit("l5_scout_final_attack_balanced", game, uid)
    _assert_valid_screen(t_intro, kb_intro, "l5_hybrid_trigger_trap")
    assert game.story_state == "l5_hybrid_intro_trap"

    # 2. Обрушение уступа (старт боя с начальным уроном)
    t1, kb1 = handle_location_5_slug_pit("l5_hybrid_trigger_trap", game, uid)
    _assert_valid_screen(t1, kb1, "l5_hybrid_hook_large")
    assert game.wolf_battle is not None
    assert game.wolf_battle["enemy_id"] == "trash_slime_hybrid"
    assert game.wolf_battle["phase"] == "1"
    assert 1600 <= game.wolf_battle["wolf_hp"] <= 1650

    # 3. Фаза 1: Бросить крюк в крупный мусор -> Фаза 2A
    t2a, kb2a = handle_location_5_slug_pit("l5_hybrid_hook_large", game, uid)
    _assert_valid_screen(t2a, kb2a, "l5_hybrid_pull_large")
    assert game.wolf_battle["phase"] == "2A"

    # 4. Фаза 2A: Выдрать крупный узел -> Фаза 3A
    t3a, kb3a = handle_location_5_slug_pit("l5_hybrid_pull_large", game, uid)
    _assert_valid_screen(t3a, kb3a, "l5_hybrid_shroom_hole")
    assert game.wolf_battle["phase"] == "3A"
    assert game.wolf_battle["stun_turns"] in (2, 3)

    # 5. Фаза 3A: Бросить светящийся гриб в рану -> Фаза 3A_shroom (списание 1 гриба)
    t_sh, kb_sh = handle_location_5_slug_pit("l5_hybrid_shroom_hole", game, uid)
    _assert_valid_screen(t_sh, kb_sh, "l5_hybrid_crit_core")
    assert game.wolf_battle["phase"] == "3A_shroom"
    assert game.inventory.get("Светящийся гриб") == 1

    # 6. Фаза 3A_shroom: Решающий удар по ядру -> Победа
    game.wolf_battle["wolf_hp"] = 30
    t_win, kb_win = handle_location_5_slug_pit("l5_hybrid_crit_core", game, uid)
    _assert_valid_screen(t_win, kb_win, "l5_scout_leave_to_camp")
    assert game.wolf_battle is None
    assert "Охотничье сланцевое копьё" not in game.inventory
    assert "Охотничье сланцевое копьё" not in game.equipment.values()
    assert game.equipment.get("hand_right") == "Крепкий посох"
    assert "Крепкий посох" not in game.inventory
    assert game.is_story_flag_set("trash_slime_defeated")
    assert game.is_story_flag_set("boss_trash_slime_defeated")
    assert game.is_story_flag_set("l5_ancient_defeated")
    assert game.is_story_flag_set("l6_unlocked")
    assert "Мохнатая пещера" in game.unlocked_locations
    assert not any("яр" in l.lower() or "слайм" in l.lower() for l in game.unlocked_locations)

    # 7. Выход в лагерь
    t_camp, kb_camp = handle_location_5_slug_pit("l5_scout_leave_to_camp", game, uid)
    _assert_valid_screen(t_camp, kb_camp)
    assert game.current_location == "Стартовый лес"
    assert game.active_story_callback is None
    assert game.story_state is None
    assert game.wolf_battle is None


def test_l5_scout_reconnaissance_e2e_happy_path():
    """Сквозной тест разведки: прибытие, наблюдение повадок и окрестностей, лимиты дня и возврат в лагерь."""
    game = GameState()
    uid = 7004
    assert not game.intro_seen

    # 1. Прибытие в логово (Окно 0)
    t0, kb0 = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    _assert_valid_screen(t0, kb0, "l5_scout_start")

    # 2. Начало наблюдений -> Окно 1 (Хаб разведки)
    t1, kb1 = handle_location_5_slug_pit("l5_scout_start", game, uid)
    _assert_valid_screen(t1, kb1, "l5_scout_habits_observe")
    _assert_valid_screen(t1, kb1, "l5_scout_surroundings_observe")
    assert game.intro_seen is True

    # 3. Наблюдение повадок (Окно 2 -> Окно 3)
    t_h_obs, kb_h_obs = handle_location_5_slug_pit("l5_scout_habits_observe", game, uid)
    _assert_valid_screen(t_h_obs, kb_h_obs, "l5_scout_habits_think")

    t_h_th, kb_h_th = handle_location_5_slug_pit("l5_scout_habits_think", game, uid)
    _assert_valid_screen(t_h_th, kb_h_th, "l5_ancient_lair")
    assert game.habits_count == 1
    assert game.day_researches_done == 1

    # 4. Наблюдение окрестностей (Окно 4 -> Окно 5)
    t_s_obs, kb_s_obs = handle_location_5_slug_pit("l5_scout_surroundings_observe", game, uid)
    _assert_valid_screen(t_s_obs, kb_s_obs, "l5_scout_surroundings_think")

    t_s_th, kb_s_th = handle_location_5_slug_pit("l5_scout_surroundings_think", game, uid)
    _assert_valid_screen(t_s_th, kb_s_th, "l5_ancient_lair")
    assert game.surroundings_count == 1
    assert game.day_researches_done == 2

    # 5. Выход в лагерь посреди дня (лимит дня 1 равен 3, сделано 2)
    # День не должен смениться, остаток сохраняется
    t_camp, kb_camp = handle_location_5_slug_pit("l5_scout_leave_to_camp", game, uid)
    _assert_valid_screen(t_camp, kb_camp)
    assert game.current_location == "Стартовый лес"
    assert game.recon_day == 1
    assert game.day_researches_done == 2
    assert game.active_story_callback is None
    assert game.story_state is None
    assert game.wolf_battle is None




