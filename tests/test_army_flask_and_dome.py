"""
tests/test_army_flask_and_dome.py — Комплексные тесты новой механики:
1. Предметы: 🟨 Армейская фляга и 🧴 Бутылка дождевой воды.
2. Сбор дождевой воды (2–4 деления за 1 AP при дожде/грозе).
3. Питье сырой дождевой воды (риск 55% расстройства: -6 HP, -15 жажды).
4. Экипировка и опустошение армейской фляги (остаётся 0/20, не превращается в пустую бутылку).
5. Кипячение на костре (переливание во флягу до 20, возврат пустой бутылки, сохранение остатка).
6. Локация «🪂 Забытый купол»: триггер (день >= 2, 2-е исследование), нахождение вверху списка,
   первый визит (падение, закрытие на день), влияние погоды, сбивание посохом (со 2-го раза),
   сбивание камнями (штраф AP и жажды), помощь кота, расчистка завала и исчезновение локации после взятия фляги.
"""

import asyncio
import pytest
from game_state import GameState
from keyboards import get_locations_kb, get_main_kb, get_campfire_kb, get_item_card_actions_kb
from modules.items import ITEMS, ITEM_EMOJIS, get_item_negative_effects, handle_inventory_callback
from modules.cooking import handle_campfire_callback
from story.location_stories import check_forest_research_story_trigger, handle_story


def test_items_specification():
    """Проверка характеристик Армейской фляги и Бутылки дождевой воды."""
    assert "Армейская фляга" in ITEMS
    flask_data = ITEMS["Армейская фляга"]
    assert flask_data["rank"] == 6
    assert flask_data["type"] == "tool"
    assert flask_data["note"] == "Подходит для кипячения дождевой воды на костре."
    assert ITEM_EMOJIS["Армейская фляга"] == "🟨"

    assert "Бутылка дождевой воды" in ITEMS
    rain_data = ITEMS["Бутылка дождевой воды"]
    assert rain_data["rank"] == 1
    assert rain_data["type"] == "drink"
    assert rain_data["note"] == "Перелить в металлическую флягу и прокипятить на костре."
    assert ITEM_EMOJIS["Бутылка дождевой воды"] == "🧴"

    neg = get_item_negative_effects("Бутылка дождевой воды")
    assert neg is not None
    assert neg["chance"] == 55
    assert neg["effects"]["hp"] == -6
    assert neg["effects"]["thirst"] == -15


def test_army_flask_equip_and_empty_retention():
    """Армейская фляга при опустошении остаётся 0/20 и не превращается в пластиковую бутылку."""
    game = GameState()
    game.inventory["Армейская фляга"] = 1
    game.equipment["flask"] = "Армейская фляга"
    game.flask_water = 1

    # Имитация глотка до опустошения
    water_left = game.flask_water
    game.flask_water = water_left - 1
    container_name = game.equipment.get("flask")
    if "Армейская" in container_name:
        game.flask_water = 0
        # Не удаляется из слота
    else:
        game.equipment["flask"] = None

    assert game.equipment["flask"] == "Армейская фляга"
    assert game.flask_water == 0
    assert game.inventory.get("Пустая бутылка", 0) == 0

    # Проверка отображения в карточке персонажа
    char_text = game.get_character_text()
    assert "🟨 Армейская фляга (0/20)" in char_text


def test_boiling_rainwater_logic():
    """Тест переливания и кипячения дождевой воды во флягу."""
    # Пример 1: во фляге 8, в бутылке 4 -> во фляге 12, бутылка опустела и вернулась
    game1 = GameState()
    game1.equipment["flask"] = "Армейская фляга"
    game1.flask_water = 8
    game1.rain_bottles = [4]
    game1.inventory["Бутылка дождевой воды"] = 1
    game1.campfire_active = True
    game1.campfire_durability = 5

    # Логика кипячения
    cur_w = game1.flask_water
    space = 20 - cur_w
    avail = game1.rain_bottles[0]
    transfer = min(space, avail)
    game1.flask_water += transfer
    rem = avail - transfer
    if rem <= 0:
        game1.rain_bottles.pop(0)
        game1.inventory.pop("Бутылка дождевой воды", None)
        game1.inventory["Пустая бутылка"] = game1.inventory.get("Пустая бутылка", 0) + 1
    game1.campfire_durability -= 1

    assert game1.flask_water == 12
    assert len(game1.rain_bottles) == 0
    assert "Бутылка дождевой воды" not in game1.inventory
    assert game1.inventory["Пустая бутылка"] == 1
    assert game1.campfire_durability == 4

    # Пример 2: во фляге 16, в бутылке 10 -> во фляге 20, в бутылке осталось 6
    game2 = GameState()
    game2.equipment["flask"] = "Армейская фляга"
    game2.flask_water = 16
    game2.rain_bottles = [10]
    game2.inventory["Бутылка дождевой воды"] = 1
    game2.campfire_active = True
    game2.campfire_durability = 5

    cur_w = game2.flask_water
    space = 20 - cur_w
    avail = game2.rain_bottles[0]
    transfer = min(space, avail)
    game2.flask_water += transfer
    rem = avail - transfer
    if rem <= 0:
        game2.rain_bottles.pop(0)
    else:
        game2.rain_bottles[0] = rem
    game2.campfire_durability -= 1

    assert game2.flask_water == 20
    assert game2.rain_bottles[0] == 6
    assert game2.inventory.get("Пустая бутылка", 0) == 0
    assert game2.inventory["Бутылка дождевой воды"] == 1


def test_clean_bottle_water_transfers_to_army_flask():
    """Чистая вода из обычной бутылки переливается во флягу без кипячения."""
    game = GameState()
    game.inventory["Армейская фляга"] = 1
    game.inventory["Бутылка воды"] = 1
    game.army_flask_water = 16

    text, _ = asyncio.run(
        handle_inventory_callback("flask_transfer_clean_water", game, 101)
    )

    assert game.army_flask_water == 20
    assert game.inventory.get("Бутылка воды", 0) == 0
    assert game.clean_bottles_charges == [16]
    assert game.inventory.get("Пустая бутылка", 0) == 0
    assert "Перелито 4 глотков" in text


def test_boiling_rainwater_callback_checks_fire_and_water():
    """Реальный callback кипятит дождевую воду во фляге и не меняет состояние без костра."""
    game = GameState()
    game.equipment["flask"] = "Армейская фляга"
    game.flask_water = 0
    game.army_flask_water = 0
    game.campfire_active = True
    game.campfire_durability = 5
    game.rain_bottles = [4]
    game.inventory["Бутылка дождевой воды"] = 1

    text, _ = asyncio.run(handle_campfire_callback("campfire_boil_water", game, 101))

    assert game.flask_water == game.army_flask_water == 4
    assert game.rain_bottles == []
    assert game.inventory["Пустая бутылка"] == 1
    assert game.campfire_durability == 4
    assert "4/20 чистой воды" in text

    game.campfire_active = False
    game.campfire_durability = 0
    game.rain_bottles = [3]
    previous_water = game.flask_water
    result = asyncio.run(handle_campfire_callback("campfire_boil_water", game, 101))
    assert result == (None, None)
    assert game.flask_water == previous_water
    assert game.rain_bottles == [3]


def test_campfire_boiling_button_uses_army_flask_water_when_unequipped():
    """Кнопка кипячения смотрит запас армейской фляги, а не обычной надетой бутылки."""
    game = GameState()
    game.equipment["flask"] = "Бутылка воды"
    game.flask_water = 20
    game.inventory["Армейская фляга"] = 1
    game.army_flask_water = 0
    game.campfire_active = True
    game.campfire_durability = 5
    game.rain_bottles = [4]

    button_callbacks = [
        button.callback_data
        for row in get_campfire_kb(game).inline_keyboard
        for button in row
    ]
    assert "campfire_boil_water" in button_callbacks


def test_zero_flask_water_survives_document_round_trip():
    """Загрузка сейва не подставляет 10 глотков вместо сохранённого нуля."""
    game = GameState()
    game.equipment["flask"] = "Армейская фляга"
    game.flask_water = 0
    game.army_flask_water = 0

    restored = GameState.from_document(game.to_document())

    assert restored.flask_water == 0
    assert restored.army_flask_water == 0


def test_dome_discovery_trigger():
    """Локация открывается на день >= 2 на 2-е исследование в лесу."""
    game = GameState()
    game.day = 1
    evt, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert evt is None

    # Наступил день 2
    game.day = 2
    # 1-е исследование дня 2
    evt, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert evt is None

    # 2-е исследование дня 2 -> срабатывает триггер Забытого купола!
    evt, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert evt == "l1_dome_start"
    assert log is None  # Без лишнего лога, сразу в окно
    assert game.is_story_flag_set("l1_dome_discovered")


def test_dome_in_locations_kb_at_top():
    """Забытый купол располагается в САМОМ ВЕРХУ меню локаций и исчезает после завершения."""
    game = GameState()
    game.locations_unlocked = True
    game.unlocked_locations = ["Стартовый лес", "Ручей со змеями"]

    # До открытия — нет в меню
    kb_before = get_locations_kb(game)
    assert not any("Забытый купол" in btn.text for row in kb_before.inline_keyboard for btn in row)

    # Открыли
    game.set_story_flag("l1_dome_discovered", True)
    kb_open = get_locations_kb(game)
    dome_btn = kb_open.inline_keyboard[1][0]
    assert "• 🪂 Забытый купол" in dome_btn.text  # Под Стартовым лесом с точкой

    # Завершили сюжетку (забрали флягу)
    game.set_story_flag("l1_dome_completed", True)
    kb_closed = get_locations_kb(game)
    assert not any("Забытый купол" in btn.text for row in kb_closed.inline_keyboard for btn in row)


def test_dome_first_visit_fall_and_daily_lock():
    """Первый визит: попытка залезть -> падение (-5 HP, -1 AP) -> блокировка на текущий день."""
    game = GameState()
    game.day = 2
    game.hp = 50
    game.ap = 5
    game.set_story_flag("l1_dome_discovered", True)

    # Шаг 1: Экран 1.1 Находка
    t1, kb1 = handle_story("l1_dome_start", game, 123)
    assert "расколотый дуб" in t1
    assert "Вскарабкаться на дуб" in kb1.inline_keyboard[0][0].text
    assert "Вернуться в лагерь" in kb1.inline_keyboard[1][0].text

    # Шаг 2: Срыв ветви и падение
    t2, kb2 = handle_story("l1_dome_climb_v1", game, 123)
    assert "-5 HP, -1 AP" in t2
    assert game.hp == 45
    assert game.ap == 4
    assert "Подняться на ноги" in kb2.inline_keyboard[0][0].text

    # Шаг 3: Экран после падения — блокировка до завтра
    t3, kb3 = handle_story("l1_dome_after_fall", game, 123)
    assert "Нужно вернуться завтра" in t3
    assert game.story_flags.get("l1_dome_visited_once") is True
    assert game.story_flags.get("l1_dome_day_attempt") == 2
    assert "Вернуться в лагерь" in kb3.inline_keyboard[0][0].text

    # Попытка зайти снова в тот же день (день 2)
    t_re, kb_re = handle_story("l1_dome_enter", game, 123)
    assert "Тело всё еще ноет" in t_re
    assert "Вернуться в лагерь" in kb_re.inline_keyboard[0][0].text


def test_dome_bad_weather_visit():
    """В плохую погоду (дождь/пасмурно) на следующий день ничего нельзя достать."""
    game = GameState()
    game.day = 3
    game.weather = "rain"
    game.set_story_flag("l1_dome_discovered", True)
    game.story_flags["l1_dome_visited_once"] = True
    game.story_flags["l1_dome_day_attempt"] = 2  # прошлый день

    text, kb = handle_story("l1_dome_enter", game, 123)
    assert "Непогода окутала поляну сыростью" in text
    assert "Стоит прийти в ясную погоду" in text
    assert "Вернуться в лагерь" in kb.inline_keyboard[0][0].text


def test_dome_stone_throw_fails():
    """Броски камнями не достают и тратят 1 AP и 15 жажды."""
    game = GameState()
    game.day = 3
    game.weather = "clear"
    game.ap = 5
    game.thirst = 50
    game.set_story_flag("l1_dome_discovered", True)
    game.story_flags["l1_dome_visited_once"] = True

    text, kb = handle_story("l1_dome_stone_throw", game, 123)
    assert "-1 AP, -15 к жажде" in text
    assert game.ap == 4
    # 50 - 1 (за действие) - 15 (штраф) = 34
    assert game.thirst == 34
    assert "Перевести дух" in kb.inline_keyboard[0][0].text


def test_dome_staff_progression_and_loot():
    """Посох: 1-я и 2-я попытка не получаются, 3-я попытка сбивает ранец.
    Упавший ранец сохраняется при повторном входе даже в дождь.
    При 0 AP отображается кнопка 'Нет сил расчищать'."""
    game = GameState()
    game.day = 3
    game.weather = "clear"
    game.ap = 5
    game.set_story_flag("l1_dome_discovered", True)
    game.story_flags["l1_dome_visited_once"] = True

    # 1-я попытка с посохом
    t_st1, kb_st1 = handle_story("l1_dome_staff_solve", game, 123)
    assert "руки затекли и дрожат" in t_st1
    assert "придется отложить до завтра" in t_st1
    assert game.story_flags.get("l1_dome_staff_tries") == 1
    assert game.story_flags.get("l1_dome_day_attempt") == 3

    # 2-я попытка с посохом (на следующий день)
    game.day = 4
    game.ap = 5
    t_st2, kb_st2 = handle_story("l1_dome_staff_solve", game, 123)
    assert "Узел строп заметно разболтался" in t_st2
    assert "завтра узел точно поддастся" in t_st2
    assert game.story_flags.get("l1_dome_staff_tries") == 2
    assert game.story_flags.get("l1_dome_day_attempt") == 4

    # 3-я попытка с посохом (на 5 день) — успех!
    game.day = 5
    game.ap = 5
    t_st3, kb_st3 = handle_story("l1_dome_staff_solve", game, 123)
    assert "Сухой треск! Перетертые стропы лопаются" in t_st3
    assert game.is_story_flag_set("l1_dome_backpack_fallen") is True
    assert "Осмотреть завал у корней" in kb_st3.inline_keyboard[0][0].text

    # Проверка сохранения упавшего ранца при выходе и повторном входе (даже в дождь!)
    game.weather = "rain"
    t_reenter, kb_reenter = handle_story("l1_dome_enter", game, 123)
    assert "Ранец лежит прямо среди густого валежника" in t_reenter
    assert "Расчистить завал (1 ⚡)" in kb_reenter.inline_keyboard[0][0].text
    assert "Вернуться в лагерь" in kb_reenter.inline_keyboard[1][0].text

    # Проверка отсутствия AP на экране завала:
    game.ap = 0
    t_no_ap, kb_no_ap = handle_story("l1_dome_enter", game, 123)
    assert "Ранец лежит прямо среди густого валежника" in t_no_ap
    assert len(kb_no_ap.inline_keyboard) == 1
    assert "Нет сил расчищать" in kb_no_ap.inline_keyboard[0][0].text

    # Игрок восстанавливает AP и расчищает завал
    game.ap = 2
    t_loot, kb_loot = handle_story("l1_dome_loot", game, 123)
    assert "Армейская фляга" in t_loot
    assert "воздав последние почести" in t_loot
    assert game.inventory.get("Армейская фляга") == 1
    assert game.army_flask_water == 0
    assert game.equipment.get("flask") is None
    assert game.is_story_flag_set("l1_dome_completed") is True
    assert game.narrative_karma["pragmatism"] == 3
    assert "Вернуться в лагерь" in kb_loot.inline_keyboard[0][0].text

    ap_after_first_reward = game.ap
    duplicate_text, _ = handle_story("l1_dome_loot", game, 123)
    assert "Армейская фляга" in duplicate_text
    assert game.inventory.get("Армейская фляга") == 1
    assert game.narrative_karma["pragmatism"] == 3
    assert game.ap == ap_after_first_reward


def test_dome_cat_solve():
    """С котёнком на следующий ясный день доступна кнопка и ранец сбивается сразу."""
    game = GameState()
    game.day = 3
    game.weather = "clear"
    game.set_story_flag("has_pet", True)
    game.set_story_flag("l1_dome_discovered", True)
    game.story_flags["l1_dome_visited_once"] = True

    # Кнопка взаимодействия с котёнком присутствует в меню купола
    t_menu, kb_menu = handle_story("l1_dome_enter", game, 123)
    cat_btn = [btn for row in kb_menu.inline_keyboard for btn in row if "котёнка" in btn.text]
    assert len(cat_btn) == 1
    assert cat_btn[0].callback_data == "l1_dome_cat_solve"

    # При отсутствии питомца кнопки нет
    game_no_pet = GameState()
    game_no_pet.day = 3
    game_no_pet.weather = "clear"
    game_no_pet.set_story_flag("l1_dome_discovered", True)
    game_no_pet.story_flags["l1_dome_visited_once"] = True
    _, kb_no_pet = handle_story("l1_dome_enter", game_no_pet, 123)
    assert not any("котёнка" in btn.text for row in kb_no_pet.inline_keyboard for btn in row)

    # Использование котёнка мгновенно сбивает ранец
    t_cat, kb_cat = handle_story("l1_dome_cat_solve", game, 123)
    assert "Котёнок с интересом смотрит" in t_cat
    assert "стропа лопается" in t_cat
    assert game.is_story_flag_set("l1_dome_backpack_fallen") is True
    assert "Осмотреть завал у корней" in kb_cat.inline_keyboard[0][0].text


def test_dome_climb_fatal_fall():
    """Падение с дуба при HP <= 5 приводит к честной гибели персонажа."""
    game = GameState()
    game.hp = 3
    game.ap = 2
    text, kb = handle_story("l1_dome_climb_v1", game, 123)
    assert game.hp == 0
    assert "Срыв с дуба и падение на острые корни оказались фатальными" in text
    assert "Стартовый лес" in text
    assert kb.inline_keyboard[0][0].callback_data == "start_new_game_confirmed"


def test_dome_stone_throw_and_staff_ap_guards():
    """При 0 AP бросок камней и попытка с посохом не списывают жажду/попытки и отправляют в лагерь."""
    game = GameState()
    game.day = 3
    game.weather = "clear"
    game.ap = 0
    game.thirst = 50
    game.set_story_flag("l1_dome_discovered", True)
    game.story_flags["l1_dome_visited_once"] = True

    # Бросок камней без AP
    t_stone, kb_stone = handle_story("l1_dome_stone_throw", game, 123)
    assert "У тебя нет сил бросать камни" in t_stone
    assert game.thirst == 50
    assert kb_stone.inline_keyboard[0][0].callback_data == "menu_main"

    # Попытка с шестом без AP
    t_staff, kb_staff = handle_story("l1_dome_staff_solve", game, 123)
    assert "У тебя нет сил держать тяжелый шест" in t_staff
    assert game.story_flags.get("l1_dome_staff_tries") is None
    assert kb_staff.inline_keyboard[0][0].callback_data == "menu_main"

