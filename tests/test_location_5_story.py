"""
Unit-тесты для сюжета Локации 5 («Яр Слаймов»), предметов, крафтов и механик фонаря / амулета.
"""

import pytest
from game_state import GameState
from story.location_stories import handle_location_5_slug_pit
from crafts import can_craft, do_craft, handle_craft, CRAFT_RECIPES, CRAFT_YIELDS
from modules.items import is_item_consumable, format_item_card, ITEMS
from main import use_consumable
from keyboards import get_main_kb, get_item_card_actions_kb


@pytest.mark.l5
@pytest.mark.slow
def test_location_5_story_full_flow_wait_branch():
    """Прохождение сюжета Локации 5 через выжидание и использование гриба."""
    game = GameState()
    game.current_location = "Яр Слаймов"

    # Окно 1: Вход
    text, kb = handle_location_5_slug_pit("slug_pit_start", game, 101)
    assert game.story_state == "l5_1a"
    assert "зеленоватая взвесь" in text

    # Окно 2: Осмотр светящейся поросли
    text, kb = handle_location_5_slug_pit("l5_1b", game, 101)
    assert game.story_state == "l5_1b"

    # Окно 2.1: Сбор гриба
    text, kb = handle_location_5_slug_pit("l5_gather_mushroom", game, 101)
    assert game.inventory.get("Светящийся гриб", 0) == 1

    # Окно 3: Спуск на дно яра
    text, kb = handle_location_5_slug_pit("l5_1c", game, 101)
    assert game.story_state == "l5_1c"

    # Окно 4: Разведка вглубь яра
    text, kb = handle_location_5_slug_pit("l5_2a", game, 101)
    assert game.story_state == "l5_2a"

    # Окно 5: Осмотр кокона
    text, kb = handle_location_5_slug_pit("l5_2b_cocoon", game, 101)
    assert game.story_state == "l5_2b_cocoon"

    # Окно 7: Шаг к кокону
    text, kb = handle_location_5_slug_pit("l5_3_step", game, 101)
    assert game.story_state == "l5_3_step"

    # Окно 7.2: Приближение
    text, kb = handle_location_5_slug_pit("l5_3_approach", game, 101)
    assert game.story_state == "l5_3_approach"

    # Окно 7.3: Гигантский слизень
    text, kb = handle_location_5_slug_pit("l5_3_slug", game, 101)
    assert game.story_state == "l5_3_slug"

    # Окно 8: Выжидание и срезка гриба
    text, kb = handle_location_5_slug_pit("l5_3b_wait", game, 101)
    assert game.story_state == "l5_3b_wait"

    # Окно 9: Извлечение чистого фонаря
    text, kb = handle_location_5_slug_pit("l5_3b_extract", game, 101)
    assert game.story_state == "l5_3b_extract"
    assert game.inventory.get("Старый фонарь", 0) == 1
    assert game.lantern_durability == 20
    assert game.story_flags.get("lantern_taken") is True

    # Окно 10: Находка Костяного амулета охотника
    text, kb = handle_location_5_slug_pit("l5_4_amulet", game, 101)
    assert game.story_state == "l5_4_amulet"
    assert game.inventory.get("Костяной амулет охотника", 0) == 1
    assert game.story_flags.get("found_hunter_amulet") is True

    # Окно 11: Финал истории
    text, kb = handle_location_5_slug_pit("l5_5_lantern", game, 101)
    assert game.story_flags.get("l5_ch1_completed") is True
    assert not game.is_story_flag_set("l5_completed")
    assert "Мохнатая пещера" not in getattr(game, "unlocked_locations", [])
    assert "Зарядить фонарь" in game.unlocked_crafts
    assert "Пузырёк" in game.unlocked_crafts
    assert "Янтарное зелье" in game.unlocked_crafts
    assert "Приманка для слизней" in game.unlocked_crafts


@pytest.mark.l5
@pytest.mark.slow
def test_location_5_story_force_branch():
    """Прохождение сюжета Локации 5 через силовой разрыв кокона."""
    game = GameState()
    game.hp = 50

    text, kb = handle_location_5_slug_pit("l5_3a_force", game, 101)
    assert game.hp == 45
    assert game.inventory.get("Старый фонарь", 0) == 1
    assert game.lantern_durability == 20
    assert game.story_flags.get("lantern_taken") is True
    assert "Смола из карманов сейчас не поможет" in text
    assert "в спешке и суматохе некогда вскрывать ядра" in text


@pytest.mark.l5
def test_location_5_story_leave_without_lantern():
    """Проверка ухода без фонаря: крафт 'Зарядить фонарь' не разблокируется и не виден в меню."""
    from crafts import get_craft_menu_text, get_craft_menu_kb

    # 1. Уход через l5_5_left (после l5_3c_leave)
    game = GameState()
    game.current_location = "Яр Слаймов"
    text, kb = handle_location_5_slug_pit("l5_5_left", game, 101)
    assert game.story_flags.get("l5_ch1_completed") is True
    assert not game.is_story_flag_set("l5_completed")
    assert "Зарядить фонарь" not in game.unlocked_crafts
    assert "Пузырёк" in game.unlocked_crafts
    assert "Янтарное зелье" in game.unlocked_crafts
    assert "Приманка для слизней" in game.unlocked_crafts
    assert "Мохнатая пещера" not in getattr(game, "unlocked_locations", [])

    craft_text = get_craft_menu_text(game)
    assert "Зарядить фонарь" not in craft_text
    craft_kb = get_craft_menu_kb(game)
    assert not any("Зарядить фонарь" in b.text for r in craft_kb.inline_keyboard for b in r)

    # 2. Ранний уход через l5_leave_early
    game2 = GameState()
    game2.current_location = "Яр Слаймов"
    text2, kb2 = handle_location_5_slug_pit("l5_leave_early", game2, 101)
    assert not game2.is_story_flag_set("l5_completed")
    assert "Зарядить фонарь" not in game2.unlocked_crafts
    assert "Пузырёк" in game2.unlocked_crafts
    assert "Янтарное зелье" in game2.unlocked_crafts
    assert "Приманка для слизней" in game2.unlocked_crafts
    assert "Мохнатая пещера" not in game2.unlocked_locations
    assert game2.story_state is None
    assert game2.active_story_callback is None

    # 3. Даже если "Зарядить фонарь" принудительно добавить в unlocked_crafts, без фонаря он скрыт в меню
    game2.unlocked_crafts.append("Зарядить фонарь")
    assert "Зарядить фонарь" not in get_craft_menu_text(game2)
    assert not any("Зарядить фонарь" in b.text for r in get_craft_menu_kb(game2).inline_keyboard for b in r)


@pytest.mark.l5
def test_lantern_equip_and_durability_and_charging():
    """Экипировка старого фонаря, бонус AP, отображение на кнопке и крафт перезарядки."""
    game = GameState()
    game.inventory["Старый фонарь"] = 1
    game.lantern_durability = 20

    # Экипировка в левую руку
    handle_craft("use_item_Старый фонарь", game, 101)
    assert game.equipment.get("hand_left") == "Старый фонарь"
    assert game.calculate_daily_ap() >= 7  # 5 base + 2 lantern

    # Проверка текста кнопки в get_main_kb
    kb = get_main_kb(game)
    explore_btn = kb.inline_keyboard[0][0]
    assert "🔦 Исследовать (20/20)" in explore_btn.text

    # Симулируем исследование (трата 1 деления прочности)
    game.lantern_durability = 19
    kb = get_main_kb(game)
    assert "🔦 Исследовать (19/20)" in kb.inline_keyboard[0][0].text

    # Пробуем зарядить без ядер — нельзя
    assert not can_craft(game, "Зарядить фонарь")

    # Добавляем 2 Янтарных ядра
    game.inventory["Янтарное ядро"] = 2
    assert can_craft(game, "Зарядить фонарь")

    # Крафтим "Зарядить фонарь"
    ok, msg = do_craft(game, "Зарядить фонарь")
    assert ok is True
    assert game.lantern_durability == 20
    assert game.inventory.get("Янтарное ядро", 0) == 0


@pytest.mark.l5
def test_hunter_amulet_equip_and_dodge():
    """Экипировка амулета охотника и проверка бонуса уворота."""
    game = GameState()
    game.inventory["Костяной амулет охотника"] = 1
    initial_dodge = game.dodge_chance

    handle_craft("use_item_Костяной амулет охотника", game, 101)
    assert game.equipment.get("trinket") == "Костяной амулет охотника"
    assert game.dodge_chance == initial_dodge + 5


@pytest.mark.l5
def test_vial_craft_and_potion_consumption():
    """Крафт 5 пузырьков из 1 сланцевого слитка, крафт зелья и его применение с возвратом пузырька."""
    game = GameState()
    game.inventory["Сланцевый слиток"] = 1

    # 1. Крафт пузырьков (из 1 слитка получается ровно 5 пузырьков)
    ok, msg = do_craft(game, "Пузырёк")
    assert ok is True
    assert game.inventory.get("Пузырёк", 0) == 5

    # 2. Крафт Янтарного зелья (3 пузырька + 1 янтарное ядро + 1 ягода -> 3 зелья)
    game.inventory["Янтарное ядро"] = 1
    game.inventory["Болотная ягода"] = 1
    assert can_craft(game, "Янтарное зелье")

    ok, msg = do_craft(game, "Янтарное зелье")
    assert ok is True
    assert game.inventory.get("Янтарное зелье", 0) == 3
    assert game.inventory.get("Пузырёк", 0) == 2

    # 3. Применение Янтарного зелья (+70 HP и возврат пузырька)
    game.hp = 20
    use_consumable("Янтарное зелье", game)
    assert game.hp == 90
    assert game.inventory.get("Янтарное зелье", 0) == 2
    assert game.inventory.get("Пузырёк", 0) == 3


@pytest.mark.l5
def test_slug_bait_mechanics():
    """Тест крафта приманки (только на L5, 10 любых ягод), установки, меню засады и ночного распада."""
    game = GameState()
    game.current_location = "Стартовый лес"
    game.inventory["Лесная ягода"] = 6
    game.inventory["Красная ягода"] = 4

    # 1. Попытка скрафтить не на L5 -> нельзя
    assert not can_craft(game, "Приманка для слизней")
    ok, err = do_craft(game, "Приманка для слизней")
    assert ok is False
    assert "Яру Слаймов" in err

    # 2. Перемещаемся в Яр Слаймов -> теперь можно
    game.current_location = "Яр Слаймов"
    assert can_craft(game, "Приманка для слизней")
    ok, msg = do_craft(game, "Приманка для слизней")
    assert ok is True
    assert game.inventory.get("Приманка для слизней", 0) == 1
    assert game.inventory.get("Лесная ягода", 0) == 0
    assert game.inventory.get("Красная ягода", 0) == 0

    # 3. Установка приманки в Яру Слаймов
    handle_craft("use_item_Приманка для слизней", game, 101)
    assert game.slug_bait_active is True
    assert game.inventory.get("Приманка для слизней", 0) == 0

    # 4. Проверка меню приманки на L5
    text, kb = handle_location_5_slug_pit("l5_bait_menu", game, 101)
    assert "ПРИМАНКА ДЛЯ СЛИЗНЕЙ" in text
    callbacks = [b.callback_data for r in kb.inline_keyboard for b in r]
    assert "l5_slug_ambush" in callbacks
    assert "l5_bait_remove" in callbacks

    # 5. Ночной распад: сон уничтожает приманку
    game.sleep_and_turn_day()
    assert game.slug_bait_active is False
    assert any("сожрали приманку" in log for log in game.event_log)


@pytest.mark.l5
def test_pants_pocket_and_button_exact_text():
    """Тест футляра на кожаных поножах и точного текста кнопки без искажения рода и скобок HP."""
    game = GameState()
    game.equipment["pants"] = "Кожаные поножи"
    game.inventory["Янтарное зелье"] = 1
    game.inventory["Ягодный отвар"] = 1

    # Вкладываем Янтарное зелье в футляр
    # Симулируем pocket_insert_
    game.inventory["Янтарное зелье"] -= 1
    game.pants_pocket = "Янтарное зелье"
    assert game.pants_pocket == "Янтарное зелье"

    # Экран персонажа отображает футляр
    char_screen = game.get_character_text()
    assert "Кожаные поножи" in char_screen
    assert "Футляр: Янтарное зелье" in char_screen

    # Проверяем генерацию кнопок в бою: кнопка должна называться строго 'Принять Янтарное зелье'
    from story.location_stories import _render_slug_pack_battle, start_slug_pack_battle
    start_slug_pack_battle(game, count=2)
    text, kb = _render_slug_pack_battle(game)

    pocket_btn = next((b for r in kb.inline_keyboard for b in r if "Принять" in b.text), None)
    assert pocket_btn is not None
    # Строгое требование пользователя: никаких '+70 HP' в скобках, точное название предмета
    assert pocket_btn.text == "Принять Янтарное зелье"
    assert "+70" not in pocket_btn.text

    # Проверяем использование в бою
    game.hp = 50
    text_after, kb_after = handle_location_5_slug_pit("l5_slug_use_pocket", game, 101)
    assert game.pants_pocket is None
    assert game.inventory.get("Пузырёк", 0) == 1
    assert "Ты принимаешь Янтарное зелье" in text_after


@pytest.mark.l5
@pytest.mark.slow
def test_multi_slime_pack_combat_simulation():
    """Тест экрана боя со скоплением слизней: заголовок, HP 15-25, полный блок по 1 HP, победа и трофеи."""
    game = GameState()
    # Надеваем полный кожаный комплект + амулет охотника
    game.equipment = {
        "head": "Кожаный капюшон",
        "torso": "Кожаный нагрудник",
        "pants": "Кожаные поножи",
        "boots": "Кожаные сапоги",
        "trinket": "Костяной амулет охотника",
        "hand_right": "Окованный посох",
        "hand_left": "Старый фонарь",
    }
    assert game.max_hp == 133
    assert game.armor_defense == 7
    assert game.dodge_chance == 40  # 35% сет + 5% амулет

    from story.location_stories import start_slug_pack_battle
    text, kb = start_slug_pack_battle(game, count=6)

    # 1. Заголовок битвы: опция 7 (скрещенные клинки)
    assert "⚔️ СКОПЛЕНИЕ СЛИЗНЕЙ" in text
    assert "[ 🟢 🟢 🟢 🟢 🟢 🟢 ]" in text
    b = game.slug_pack_battle
    assert len(b["slimes"]) == 6
    for s in b["slimes"]:
        assert 15 <= s["hp"] <= 25

    # 2. Полный блок: каждый живой слизень наносит ровно 1 урон (6 слизней -> 6 урона)
    hp_before = game.hp
    text_def, kb_def = handle_location_5_slug_pit("l5_slug_defend", game, 101)
    assert game.hp == hp_before - 6
    assert "Получено в блок: 6 урона" in text_def

    # 3. Атака посохом
    first_slime_hp = b["slimes"][0]["hp"]
    text_atk, kb_atk = handle_location_5_slug_pit("l5_slug_attack", game, 101)
    assert b["slimes"][0]["hp"] < first_slime_hp

    # 4. Победа при гибели всех слизней
    for s in b["slimes"]:
        s["alive"] = False
        s["hp"] = 0
    text_fin, kb_fin = handle_location_5_slug_pit("l5_slug_attack", game, 101)
    assert "ВСЕ СЛИЗНИ ПОВЕРЖЕНЫ" in text_fin
    assert "Янтарное ядро" in text_fin
    assert "l5_slug_battle_finish" in [b.callback_data for r in kb_fin.inline_keyboard for b in r]


@pytest.mark.l5
def test_vial_and_amber_potion_card_metadata():
    """Тест карточек предметов: отсутствие ранга, эмодзи 🍹, описание пузырька и зелья."""
    from modules.items import ITEM_EMOJIS, ITEMS

    # 1. Эмодзи
    assert ITEM_EMOJIS["Янтарное зелье"] == "🍹"
    assert ITEM_EMOJIS["Приманка для слизней"] == "🍯"

    # 2. Ранг отсутствует
    assert "rank" not in ITEMS["Пузырёк"]
    assert "rank" not in ITEMS["Янтарное зелье"]

    # 3. Описания
    assert "выплавленный из сланцевого слитка" in ITEMS["Пузырёк"]["description"]
    assert "+70 HP" not in ITEMS["Янтарное зелье"]["description"]
    assert "+70 HP" in ITEMS["Янтарное зелье"]["note"]


@pytest.mark.l5
def test_l5_leave_early_karma_exploit_prevention():
    """Многократный вызов l5_leave_early начисляет карму строго один раз."""
    game = GameState()
    initial_pragmatism = game.narrative_karma.get("pragmatism", 0)
    initial_compassion = game.narrative_karma.get("compassion", 0)
    initial_intervention = game.narrative_karma.get("intervention", 0)
    initial_observation = game.narrative_karma.get("observation", 0)

    # 1-й выход
    handle_location_5_slug_pit("l5_leave_early", game, 101)
    assert game.narrative_karma.get("pragmatism", 0) == initial_pragmatism + 2
    assert game.narrative_karma.get("compassion", 0) == initial_compassion + 1
    assert game.narrative_karma.get("intervention", 0) == initial_intervention - 2
    assert game.narrative_karma.get("observation", 0) == initial_observation + 1
    assert game.is_story_flag_set("l5_leave_early_karma_applied")

    # 2-й и 3-й выходы (повторные)
    handle_location_5_slug_pit("l5_leave_early", game, 101)
    handle_location_5_slug_pit("l5_leave_early", game, 101)
    assert game.narrative_karma.get("pragmatism", 0) == initial_pragmatism + 2
    assert game.narrative_karma.get("compassion", 0) == initial_compassion + 1
    assert game.narrative_karma.get("intervention", 0) == initial_intervention - 2
    assert game.narrative_karma.get("observation", 0) == initial_observation + 1


@pytest.mark.l5
def test_l5_reentry_after_chapter1():
    """После финала Главы 1 игрок не видит заглушку 'Яр спокоен' и не начинает Главу 1 заново."""
    game = GameState()
    game.set_story_flag("l5_ch1_completed", True)

    text, kb = handle_location_5_slug_pit("slug_pit_start", game, 101)
    assert "Ты спускаешься на дно Яра Слаймов" in text
    assert "Яр теперь спокоен" not in text
    buttons = [b.callback_data for r in kb.inline_keyboard for b in r]
    assert "l5_2_1" in buttons
    assert "back" in buttons


@pytest.mark.l5
def test_l5_sturdy_staff_no_duplication_on_boss_win():
    """Проверка отсутствия дюпа Крепкого посоха во всех 3 векторах финала босса."""
    # 1. Вектор 3 (Гибрид)
    g3 = GameState()
    g3.equipment["hand_right"] = "Охотничье сланцевое копьё"
    g3.inventory["Охотничье сланцевое копьё"] = 1
    g3.wolf_battle = {"enemy_id": "trash_slime_hybrid"}
    from story.locations.loc5_slug_pit import _render_hybrid_win
    text3, kb3 = _render_hybrid_win(g3)
    assert g3.equipment.get("hand_right") == "Крепкий посох"
    assert g3.inventory.get("Крепкий посох", 0) == 0  # Не дублируется в инвентаре!
    assert "Охотничье сланцевое копьё" not in g3.inventory
    assert g3.is_story_flag_set("l5_completed")

    # 2. Вектор 1 (Повадки)
    g1 = GameState()
    g1.equipment["hand_right"] = "Охотничье сланцевое копьё"
    g1.inventory["Охотничье сланцевое копьё"] = 1
    g1.wolf_battle = {"enemy_id": "trash_slime_habits"}
    from story.locations.loc5_slug_pit import _render_habits_win
    text1, kb1 = _render_habits_win(g1)
    assert g1.equipment.get("hand_right") == "Крепкий посох"
    assert g1.inventory.get("Крепкий посох", 0) == 0  # Не дублируется в инвентаре!
    assert "Охотничье сланцевое копьё" not in g1.inventory
    assert g1.is_story_flag_set("l5_completed")

    # 3. Вектор 2 (Спецоперация)
    g2 = GameState()
    g2.equipment["hand_right"] = "Охотничье сланцевое копьё"
    g2.inventory["Охотничье сланцевое копьё"] = 1
    text2, kb2 = handle_location_5_slug_pit("l5_trap_op_step9", g2, 101)
    assert g2.equipment.get("hand_right") == "Крепкий посох"
    assert g2.inventory.get("Крепкий посох", 0) == 0  # Не дублируется в инвентаре!
    assert "Охотничье сланцевое копьё" not in g2.inventory
    assert g2.is_story_flag_set("l5_completed")


@pytest.mark.l5
@pytest.mark.nav
def test_l5_scout_leave_to_camp_clears_wolf_battle():
    """Возврат в лагерь через l5_scout_leave_to_camp зануляет wolf_battle."""
    game = GameState()
    game.wolf_battle = {"phase": "scout", "hp": 100}
    handle_location_5_slug_pit("l5_scout_leave_to_camp", game, 101)
    assert game.wolf_battle is None
    assert game.story_state is None
    assert game.active_story_callback is None
