# -*- coding: utf-8 -*-
"""
test_location_5_ch2_story.py — Комплексные тесты Главы 2 Локации 5 («Заводь Исполина»).

Проверяет:
1. Триггер запуска на 3-й день на 3-е исследование Яра Слизней.
2. Возможность заходить в костер/лагерь между исследованиями.
3. Полный нарративный переход l5_2_1 -> l5_2_6.
4. Разблокировку подлокации [☣️ Заводь Исполина] в get_locations_kb.
5. Вход на арену l5_arena_start и пошаговый бой со слаймом (атака, уворот, крит по ядру).
6. Победу над боссом l5_2_7 с поломкой экипированного посоха и удалением арены из меню.
7. Переходы l5_2_8 -> l5_2_9 -> l5_2_10.
8. Разблокировку подлокации [🕳️ Логово Древнего] в get_locations_kb.
9. Проверку длины всех текстов экранов (строго <= 500 символов).
"""
import pytest
from game_state import GameState
from keyboards import get_locations_kb, get_slime_battle_kb
from story.location_stories import (
    check_forest_research_story_trigger,
    handle_story,
    handle_location_5_slug_pit,
)
from modules.combat.engine import start_battle, apply_action


def test_l5_ch2_research_trigger_conditions():
    """Тест условий срабатывания триггера Главы 2 Локации 5."""
    game = GameState()
    game.day = 1
    
    # 1. Если первая глава не пройдена — триггер не срабатывает
    evt, log = check_forest_research_story_trigger(game, loc_id=5, torch_equipped=False)
    assert evt is None
    
    # Завершаем первую главу L5
    game.set_story_flag("l5_completed", True)
    game.story_flags["l5_completed_day"] = 1
    
    # 2. В день 1 или день 2 триггер не должен срабатывать
    game.day = 1
    for _ in range(5):
        evt, _ = check_forest_research_story_trigger(game, loc_id=5, torch_equipped=False)
        assert evt is None
        
    game.day = 2
    for _ in range(5):
        evt, _ = check_forest_research_story_trigger(game, loc_id=5, torch_equipped=False)
        assert evt is None
        
    # 3. Наступает 3-й день (day == 3)
    game.day = 3
    # 1-е исследование
    evt1, _ = check_forest_research_story_trigger(game, loc_id=5, torch_equipped=False)
    assert evt1 is None
    assert game.story_flags.get("l5_day3_research_count") == 1
    
    # Игрок делает что-то другое: костер, крафт, готовка
    game.campfire_active = True
    
    # 2-е исследование
    evt2, _ = check_forest_research_story_trigger(game, loc_id=5, torch_equipped=False)
    assert evt2 is None
    assert game.story_flags.get("l5_day3_research_count") == 2
    
    # 3-е исследование — срабатывание триггера!
    evt3, log3 = check_forest_research_story_trigger(game, loc_id=5, torch_equipped=False)
    assert evt3 == "l5_2_1"
    assert "следы" in log3.lower() or "уступ" in log3.lower()
    assert game.is_story_flag_set("l5_ch2_started")


def test_l5_ch2_scouting_story_flow():
    """Тест прохождения разведки от l5_2_1 до l5_2_6."""
    game = GameState()
    uid = 12345
    
    # Экран 1
    text1, kb1 = handle_location_5_slug_pit("l5_2_1", game, uid)
    assert "прочёсываешь сырой лабиринт яра" in text1
    assert len(text1) <= 500
    buttons1 = [btn.text for row in kb1.inline_keyboard for btn in row]
    assert "👣 Выйти на разведку" in buttons1
    
    # Экран 2
    text2, kb2 = handle_location_5_slug_pit("l5_2_2", game, uid)
    assert "тянется широкая примятая полоса" in text2
    assert "отпечатки копыт молодого оленя" in text2
    assert len(text2) <= 500
    buttons2 = [btn.text for row in kb2.inline_keyboard for btn in row]
    assert "🐾 Идти по следу" in buttons2
    
    # Экран 3
    text3, kb3 = handle_location_5_slug_pit("l5_2_3", game, uid)
    assert "Борозда огибает острый сланцевый гребень" in text3
    assert len(text3) <= 500
    buttons3 = [btn.text for row in kb3.inline_keyboard for btn in row]
    assert "🤫 Прокрасться в заводь" in buttons3
    
    # Экран 4
    text4, kb4 = handle_location_5_slug_pit("l5_2_4", game, uid)
    assert "Исполинский слайм размером с человека" in text4
    assert len(text4) <= 500
    buttons4 = [btn.text for row in kb4.inline_keyboard for btn in row]
    assert "👀 Следить за тварью" in buttons4
    
    # Экран 5
    text5, kb5 = handle_location_5_slug_pit("l5_2_5", game, uid)
    assert "выбрасывает всю массу вперёд" in text5
    assert len(text5) <= 500
    buttons5 = [btn.text for row in kb5.inline_keyboard for btn in row]
    assert "💡 Оценить слабость" in buttons5
    
    # Экран 6
    text6, kb6 = handle_location_5_slug_pit("l5_2_6", game, uid)
    assert "Всё встало на свои места" in text6
    assert len(text6) <= 500
    assert game.is_story_flag_set("l5_arena_unlocked")
    buttons6 = [btn.text for row in kb6.inline_keyboard for btn in row]
    assert "🏕️ Отступить в лагерь" in buttons6


def test_l5_arena_menu_unlock_and_start():
    """Тест отображения подлокации в меню локаций и экрана входа."""
    game = GameState()
    game.unlocked_locations = ["Яр Слизней"]
    
    # До l5_2_6 арены нет в меню
    locs_kb = get_locations_kb(game)
    buttons = [btn.text for row in locs_kb.inline_keyboard for btn in row]
    assert "• ☣️ Заводь Исполина" not in buttons
    
    # Разблокируем
    game.set_story_flag("l5_arena_unlocked", True)
    locs_kb = get_locations_kb(game)
    buttons = [btn.text for row in locs_kb.inline_keyboard for btn in row]
    assert "• ☣️ Заводь Исполина" in buttons
    
    # Вход на арену
    text, kb = handle_location_5_slug_pit("l5_arena_start", game, 123)
    assert "Ты стоишь на входе в каменистую заводь" in text
    assert len(text) <= 500
    buttons_arena = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "⚔️ Напасть на слайма" in buttons_arena
    assert "🏕️ Вернуться в лагерь" in buttons_arena


def test_l5_boss_combat_and_weapon_break():
    """Тест пошагового боя с Исполинским слаймом (555 HP), поломки посоха и победы."""
    game = GameState()
    uid = 999
    game.equipment["hand_right"] = "Крепкий посох"
    game.inventory["Крепкий посох"] = 1
    game.hp = 100

    # Запуск боя
    text, kb = handle_location_5_slug_pit("l5_boss_fight", game, uid)
    assert "Исполинский слайм" in text
    assert game.wolf_battle is not None
    assert game.wolf_battle["enemy_id"] == "giant_slime"
    assert game.wolf_battle["wolf_hp"] == 555
    assert game.wolf_battle["phase"] == "1"

    # Проверяем Ветку А: правильный шаг в сторону ядра
    game.wolf_battle["core_side"] = "right"
    text, kb = apply_action("slime_battle_step_right", game, "giant_slime")
    assert game.wolf_battle["phase"] == "2A"
    assert "Самое время бить" in text

    # Фаза 2А: Крит атака по ядру (35-40 урона)
    prev_hp = game.wolf_battle["wolf_hp"]
    text, kb = apply_action("slime_battle_attack", game, "giant_slime")
    assert game.wolf_battle["phase"] == "3A"
    dmg_dealt = prev_hp - game.wolf_battle["wolf_hp"]
    assert 35 <= dmg_dealt <= 40
    assert "Кислотный фонтан" in text or "хлещет пена" in text

    # Фаза 3А: Уворот от кислотного фонтана (0 урона, переход в 4А)
    hp_before = game.hp
    text, kb = apply_action("slime_battle_dodge_left", game, "giant_slime")
    assert game.hp == hp_before
    assert game.wolf_battle["phase"] == "4A"
    assert game.wolf_battle["stun_turns"] >= 1

    # Фаза 4А: Атака по оглушенному (12 HP)
    game.wolf_battle["stun_turns"] = 1
    prev_hp = game.wolf_battle["wolf_hp"]
    text, kb = apply_action("slime_battle_attack", game, "giant_slime")
    assert prev_hp - game.wolf_battle["wolf_hp"] == 12
    # После 1 удара stun_turns стал 0 -> переход в 5А
    assert game.wolf_battle["phase"] == "5A"

    # Фаза 5А: Следить за ядром -> переход обратно в Фазу 1
    text, kb = apply_action("slime_battle_watch", game, "giant_slime")
    assert game.wolf_battle["phase"] == "1"

    # Добиваем слайма
    game.wolf_battle["phase"] = "2A"
    game.wolf_battle["wolf_hp"] = 10
    text, kb = apply_action("slime_battle_attack", game, "giant_slime")
    assert "ПОБЕДА НАД ИСПОЛИНОМ" in text

    # Убеждаемся, что другая экипировка и инвентарь не затронуты
    game.equipment["hand_left"] = "Старый фонарь"
    game.equipment["pants"] = "Кожаные поножи"
    game.inventory["Вяленое мясо"] = 3

    # Переход на экран финала l5_2_7
    text_win, kb_win = handle_location_5_slug_pit("l5_2_7", game, uid)
    assert "Улучив момент, ты со всей силы вбиваешь посох прямо в обнажившееся ядро" in text_win
    assert len(text_win) <= 500

    # Проверка поломки ТОЛЬКО посоха:
    assert game.equipment.get("hand_right") is None
    assert game.inventory.get("Крепкий посох", 0) == 0
    # Вся остальная экипировка и инвентарь на месте:
    assert game.equipment.get("hand_left") == "Старый фонарь"
    assert game.equipment.get("pants") == "Кожаные поножи"
    assert game.inventory.get("Вяленое мясо") == 3

    assert game.is_story_flag_set("l5_boss_defeated")
    assert not game.is_story_flag_set("l5_arena_unlocked")

    # Проверка: Заводь Исполина исчезла из меню локаций
    locs_kb = get_locations_kb(game)
    buttons = [btn.text for row in locs_kb.inline_keyboard for btn in row]
    assert "☣️ Заводь Исполина" not in buttons


def test_l5_boss_branch_b_and_damage_penalties():
    """Тест Ветки Б (ошибка выбора стороны) и штрафов за жадность/ошибку."""
    game = GameState()
    uid = 777
    game.hp = 100
    start_battle(game, "giant_slime")

    # Ошибка: ядро справа, а игрок шагает влево
    game.wolf_battle["core_side"] = "right"
    text, kb = apply_action("slime_battle_step_left", game, "giant_slime")
    assert game.wolf_battle["phase"] == "2B"
    assert "Ошибся с направлением" in text

    # Фаза 2Б: Только подготовка
    text, kb = apply_action("slime_battle_prepare", game, "giant_slime")
    assert game.wolf_battle["phase"] == "3B"

    # Фаза 3Б: Атака в лоб на волну -> жадность: -50 HP
    text, kb = apply_action("slime_battle_attack", game, "giant_slime")
    assert game.hp == 50
    assert game.wolf_battle["phase"] == "4B"

    # Фаза 4Б: Тычок по жиже (8 HP) -> переход в 5Б
    prev_hp = game.wolf_battle["wolf_hp"]
    text, kb = apply_action("slime_battle_attack", game, "giant_slime")
    assert prev_hp - game.wolf_battle["wolf_hp"] == 8
    assert game.wolf_battle["phase"] == "5B"

    # Фаза 5Б: Следить за ядром -> возврат в Фазу 1
    text, kb = apply_action("slime_battle_watch", game, "giant_slime")
    assert game.wolf_battle["phase"] == "1"


def test_l5_boss_escape_burns_ap():
    """Тест побега из боя: сгорание всех AP до 0 и переход на l5_arena_escape."""
    game = GameState()
    uid = 888
    game.ap = 5
    game.max_ap = 5
    start_battle(game, "giant_slime")

    # Нажимаем [🏃 Сбежать]
    text, kb = apply_action("slime_battle_flee", game, "giant_slime")
    assert game.ap == 0
    assert game.wolf_battle is None
    assert game.story_state == "l5_arena_escape"
    assert "Лёгкие горят огнём" in text
    assert len(text) <= 500
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "🏕️ Вернуться в лагерь" in buttons


def test_l5_boss_pocket_item_mechanic():
    """Тест использования кармана поножей во время боя с боссом."""
    game = GameState()
    uid = 333
    game.equipment["pants"] = "Кожаные поножи"
    game.pants_pocket = "Янтарное зелье"
    game.hp = 20
    start_battle(game, "giant_slime")

    # Клавиатура должна содержать кнопку кармана
    kb = get_slime_battle_kb(phase="1", core_side="right", pocket_item="Янтарное зелье")
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "🍽️ Принять Янтарное зелье" in buttons

    # Принимаем зелье
    text, kb = apply_action("slime_battle_pocket", game, "giant_slime")
    assert game.hp == 90
    assert game.pants_pocket is None
    assert game.inventory.get("Пузырёк", 0) == 1


def test_l5_ch2_aftermath_and_ancient_lair_unlock():
    """Тест экранов l5_2_8 -> l5_2_9 -> l5_2_10 и открытия Логова Древнего."""
    game = GameState()
    game.unlocked_locations = ["Яр слизней"]
    uid = 555

    # Экран 8: l5_2_8
    text8, kb8 = handle_location_5_slug_pit("l5_2_8", game, uid)
    assert "Опираясь о мокрые камни, ты выходишь из лощины" in text8
    assert len(text8) <= 500
    buttons8 = [btn.text for row in kb8.inline_keyboard for btn in row]
    assert "👀 Заглянуть в промоину" in buttons8

    # Экран 9: l5_2_9
    text9, kb9 = handle_location_5_slug_pit("l5_2_9", game, uid)
    assert "На дне промоины залёг Древний слайм невероятных размеров" in text9
    assert len(text9) <= 500
    buttons9 = [btn.text for row in kb9.inline_keyboard for btn in row]
    assert "🔍 Приглядеться к твари" in buttons9

    # Экран 10: l5_2_10
    text10, kb10 = handle_location_5_slug_pit("l5_2_10", game, uid)
    assert "Как это чудовище здесь выживает и чем кормится в каменном мешке" in text10
    assert len(text10) <= 500
    assert game.is_story_flag_set("l5_ch2_completed")
    assert game.is_story_flag_set("l5_ancient_unlocked")
    buttons10 = [btn.text for row in kb10.inline_keyboard for btn in row]
    assert "🏕️ Вернуться в лагерь" in buttons10

    # Проверка разблокировки [🕳️ Логово Древнего] в меню локаций
    locs_kb = get_locations_kb(game)
    buttons = [btn.text for row in locs_kb.inline_keyboard for btn in row]
    assert "• 🕳️ Логово Древнего" in buttons

    # Проверка окна осмотра Логова Древнего (Окно 0: Первое прибытие)
    text_lair, kb_lair = handle_location_5_slug_pit("l5_ancient_lair", game, uid)
    assert "Ты замираешь на сланцевом карнизе над тупиковой промоиной" in text_lair
    assert len(text_lair) <= 550
    buttons_lair = [btn.text for row in kb_lair.inline_keyboard for btn in row]
    assert "👁️ Начать наблюдения" in buttons_lair
    assert "🏕️ Вернуться в лагерь" in buttons_lair

    # Проверка: после победы над Древним подлокация тоже исчезает из меню
    game.set_story_flag("l5_ancient_defeated", True)
    locs_kb_after = get_locations_kb(game)
    buttons_after = [btn.text for row in locs_kb_after.inline_keyboard for btn in row]
    assert "• 🕳️ Логово Древнего" not in buttons_after


def test_l5_post_boss_unarmed_camp_and_spear_craft():
    """Тест реакции экрана лагеря на безоружность и скрытия рецепта после крафта копья."""
    from keyboards import get_main_kb, get_inventory_kb, get_item_card_actions_kb
    from crafts import handle_craft, can_craft, do_craft, get_craft_menu_text, get_craft_menu_kb
    from modules.combat.engine import _calc_player_damage

    game = GameState()
    uid = 444
    game.set_story_flag("l5_boss_defeated", True)
    game.equipment["hand_right"] = None

    # 1. Проверяем лог в лагере: фраза «Посох сломан...»
    ui_text = game.get_ui()
    assert "Посох сломан, ты безоружен! В голове зреет мысль: пора скрафтить копьё." in ui_text

    # На основном экране лагеря НЕТ динамической кнопки верстака
    main_kb = get_main_kb(game)
    main_btns = [btn.text for row in main_kb.inline_keyboard for btn in row]
    assert "🔨 Верстак (Новое!)" not in main_btns
    assert "🎒 Инвентарь" in main_btns

    # В инвентаре обычная кнопка [🔨 Крафт]
    inv_kb = get_inventory_kb(game)
    inv_btns = [btn.text for row in inv_kb.inline_keyboard for btn in row]
    assert "🔨 Крафт" in inv_btns
    assert "🔨 Верстак (Новое!)" not in inv_btns

    # 2. В меню крафта рецепт копья доступен до изготовления
    menu_text = get_craft_menu_text(game)
    assert "Охотничье сланцевое копьё" in menu_text

    menu_kb = get_craft_menu_kb(game)
    menu_btns = [btn.text for row in menu_kb.inline_keyboard for btn in row]
    assert any("Охотничье сланцевое копьё" in b for b in menu_btns)

    # 3. Проверяем превью крафта копья
    text_preview, kb_preview = handle_craft("craft_Охотничье сланцевое копьё", game, uid)
    assert "🔱 Охотничье сланцевое копьё" in text_preview
    assert "клиновидным наконечником из сланца" in text_preview
    assert "19–24" in text_preview
    assert "Ветка (0/15)" in text_preview
    assert "Кожа (0/2)" in text_preview
    assert "Сланцевый слиток (0/2)" in text_preview
    assert "Светящийся гриб (0/3)" in text_preview

    # 4. Без ресурсов крафт невозможен
    assert can_craft(game, "Охотничье сланцевое копьё") is False
    ok, msg = do_craft(game, "Охотничье сланцевое копьё")
    assert ok is False

    # 5. Выдаём необходимые ресурсы (ветки, кожу, слитки, светящиеся грибы)
    game.inventory["Ветка"] = 15
    game.inventory["Кожа"] = 2
    game.inventory["Сланцевый слиток"] = 2
    game.inventory["Светящийся гриб"] = 3

    assert can_craft(game, "Охотничье сланцевое копьё") is True

    # 6. Крафтим копьё
    ok, msg = do_craft(game, "Охотничье сланцевое копьё")
    assert ok is True
    assert game.inventory.get("Охотничье сланцевое копьё") == 1
    assert game.inventory.get("Ветка", 0) == 0
    assert game.inventory.get("Кожа", 0) == 0
    assert game.inventory.get("Сланцевый слиток", 0) == 0
    assert game.inventory.get("Светящийся гриб", 0) == 0
    assert game.is_story_flag_set("crafted_hunting_spear")

    # 7. После получения копья рецепт скрывается из меню крафта!
    menu_text_after = get_craft_menu_text(game)
    assert "Охотничье сланцевое копьё" not in menu_text_after

    menu_kb_after = get_craft_menu_kb(game)
    menu_btns_after = [btn.text for row in menu_kb_after.inline_keyboard for btn in row]
    assert not any("копьё" in b.lower() for b in menu_btns_after)

    # Нельзя скрафтить второе копьё
    assert can_craft(game, "Охотничье сланцевое копьё") is False
    ok_second, _ = do_craft(game, "Охотничье сланцевое копьё")
    assert ok_second is False

    # 8. Проверяем экипировку копья через меню предметов
    item_kb = get_item_card_actions_kb("Охотничье сланцевое копьё", game)
    item_btns = [btn.text for row in item_kb.inline_keyboard for btn in row]
    assert "🔱 Взять в правую руку" in item_btns

    handle_craft("use_item_Охотничье сланцевое копьё", game, uid)
    assert game.equipment.get("hand_right") == "Охотничье сланцевое копьё"

    # И когда копьё в руке, рецепт тоже скрыт
    assert "Охотничье сланцевое копьё" not in get_craft_menu_text(game)

    # 9. Проверяем карточку персонажа и боевой урон (19–24)
    char_text = game.get_character_text()
    assert "🫱 ПРАВАЯ РУКА: 🔱 Охотничье сланцевое копьё" in char_text
    assert "19–24" in char_text

    dmg = _calc_player_damage(game)
    assert 19 <= dmg <= 24


