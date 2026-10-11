import pytest
import random
from game_state import GameState
from crafts import get_craft_menu_text, get_craft_menu_kb, can_craft, do_craft
from story.location_stories import handle_location_3_slate_hollow, handle_location_2_ruchey, check_forest_research_story_trigger
from keyboards import get_main_kb
from modules.items import use_consumable


@pytest.mark.mech
def test_slate_armor_uniqueness_and_expiry():
    """Пункт 2: Уникальность сланцевой брони и исчезновение на L3+."""
    game = GameState()
    game.inventory = {
        "Сланцевая пластина": 20,
        "Кусок коры": 20,
        "Мох": 20,
        "Ветка": 20,
    }
    game.location_index = 1
    game.set_story_flag("l2_thorns_seen", True)
    game.unlocked_crafts = ["Костёр", "Факел", "Сланцевая маска", "Сланцевый панцирь"]

    # 1. Сланцевая маска доступна до крафта
    assert can_craft(game, "Сланцевая маска") is True
    ok, msg = do_craft(game, "Сланцевая маска")
    assert ok is True
    assert game.inventory.get("Сланцевая маска") == 1

    # 2. Повторный крафт заблокирован и скрыт из меню
    assert can_craft(game, "Сланцевая маска") is False
    kb = get_craft_menu_kb(game)
    cb_datas = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "craft_Сланцевая маска" not in cb_datas

    # 3. Переход на L3 (или завершение гребня) скрывает сланцевые рецепты
    game.location_index = 2
    game.set_story_flag("l3_ridge_completed", True)
    assert can_craft(game, "Сланцевый панцирь") is False
    kb_l3 = get_craft_menu_kb(game)
    cb_datas_l3 = [b.callback_data for row in kb_l3.inline_keyboard for b in row]
    assert "craft_Сланцевый панцирь" not in cb_datas_l3


@pytest.mark.mech
def test_campfire_durability_ticks_globally():
    """Пункт 4: Огонь уменьшается на всех локациях при действиях и сне."""
    game = GameState()
    game.current_location = "Ручей со змеями"
    game.campfire_active = True
    game.campfire_durability = 8
    game.campfires = {
        "loc_1": {"active": True, "durability": 5, "max_durability": 10},
        "loc_2": {"active": True, "durability": 8, "max_durability": 10},
    }

    # Потребление AP уменьшает прочность на текущей и других локациях
    game.consume_action(1)
    assert game.campfire_durability == 7
    assert game.campfires["loc_1"]["durability"] == 4

    # Сон уменьшает прочность на 3 на всех локациях
    game.sleep_and_turn_day()
    assert game.campfire_durability == 4
    assert game.campfires["loc_1"]["durability"] == 1


@pytest.mark.mech
def test_mushroom_soup_caps_at_player_max_hp():
    """Пункт 5: Грибная похлёбка хилит до max_hp игрока (например, 125 от панциря), а не сбрасывает на 100."""
    game = GameState()
    game.equipment["torso"] = "Сланцевый панцирь"
    assert game.max_hp == 125
    game.hp = 110
    game.inventory["Грибная похлёбка"] = 1

    use_consumable("Грибная похлёбка", game)
    # Похлёбка восстанавливает 20 HP, при капе 125 должно стать 125 (а не сбрасываться до 100!)
    assert game.hp == 125


@pytest.mark.l2
def test_l2_puzzle_persistence_and_callback_safety():
    """Пункт 7: Сохранение номера попытки/шага загадки и защита active_story_callback."""
    game = GameState()
    game.l2_puzzle_attempt = 4
    game.l2_puzzle_step = 2

    # Проверка to_document / from_document
    doc = game.to_document()
    assert doc["l2_puzzle_attempt"] == 4
    assert doc["l2_puzzle_step"] == 2

    restored = GameState.from_document(doc)
    assert restored.l2_puzzle_attempt == 4
    assert restored.l2_puzzle_step == 2

    # Ответ на загадку не должен портить active_story_callback на l2_p_ans:...
    restored.hp = 50
    text, kb = handle_location_2_ruchey("l2_p_ans:4:1:0", restored, 101)
    assert not (restored.active_story_callback or "").startswith("l2_p_ans:")


@pytest.mark.l3
def test_l3_entry_stove_tablet_and_pacing():
    """Пункты 8, 10, 11: Вход в L3, доступность печи/плиты и тайминг Секача."""
    game = GameState()
    game.day = 3
    game.current_location = "Скромная лощина"

    # 1. Пункт 8: Стартовый вход в L3 возвращает сюжетное окно с кнопкой, а не главное меню
    text_entry, kb_entry = handle_location_3_slate_hollow("location_enter_3", game, 101)
    cb_entry = [b.callback_data for row in kb_entry.inline_keyboard for b in row]
    assert "l3_enter_camp" in cb_entry
    assert kb_entry != get_main_kb(game)

    # 2. Пункт 10: Печь и плита скрыты в лагере до сюжетного открытия
    handle_location_3_slate_hollow("l3_enter_camp", game, 101)
    main_kb = get_main_kb(game)
    main_cbs = [b.callback_data for row in main_kb.inline_keyboard for b in row]
    assert "tablet_notes_view" not in main_cbs
    assert not any("Печь" in (b.text or "") for row in main_kb.inline_keyboard for b in row)

    # Чтение надписей открывает каменную плиту
    handle_location_3_slate_hollow("l3_4_writings", game, 101)
    kb_with_tablet = get_main_kb(game)
    assert any(b.callback_data == "tablet_notes_view" for row in kb_with_tablet.inline_keyboard for b in row)

    # 3. Пункт 11: Кнопка «Уйти» из убежища ведёт в лагерь (l3_6_finalize), а не сразу к Секачу
    text_stay, kb_stay = handle_location_3_slate_hollow("l3_6_stay", game, 101)
    leave_btn = [b for row in kb_stay.inline_keyboard for b in row if "Уйти" in b.text][0]
    assert leave_btn.callback_data == "l3_6_finalize"

    # Завершаем обустройство убежища
    handle_location_3_slate_hollow("l3_6_finalize", game, 101)
    assert game.is_story_flag_set("l3_shelter_unlocked") is True
    assert game.is_stove is True

    # В этот же день Секач не прерывает исследование
    ev, log = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev != "l3_7_morning"

    # На следующий день (после сна) просыпается Секач
    game.day = 4
    ev2, log2 = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev2 == "l3_7_morning"


def test_rain_drinking_and_l6_blocking():
    """Тест лимита питья дождя (3 глотка, 7-15 жажды) и скрытия кнопок на L6."""
    import asyncio
    from modules.finds import handle_explore_callback

    game = GameState()
    game.weather = "rain"
    game.thirst = 50

    # 1. До 3 раз можно пить дождь без расхода AP
    initial_ap = game.ap
    for i in range(1, 4):
        prev_thirst = game.thirst
        asyncio.run(handle_explore_callback("action_collect_water", game, 101))
        assert game.ap == initial_ap
        assert game.story_flags.get("rain_sips_count") == i
        assert 7 <= (game.thirst - prev_thirst) <= 15

    # 2. 4-й раз срабатывает ограничение (не восстанавливает жажду)
    t_before = game.thirst
    asyncio.run(handle_explore_callback("action_collect_water", game, 101))
    assert game.thirst == t_before
    assert game.story_flags.get("rain_sips_count") == 3

    # 3. На следующий день счётчик сбрасывается
    game.sleep_and_turn_day()
    assert game.story_flags.get("rain_sips_count", 0) == 0

    # 4. На 6-й локации кнопки сбора и питья дождя скрыты
    game.location_index = 5
    game.current_location = "Снежный пик"
    kb = get_main_kb(game)
    cb_datas = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "action_collect_water" not in cb_datas
    assert "action_fill_rain_bottle" not in cb_datas


def test_l2_stream_water_refill_and_boiling_durability():
    """Тест 20% наполнения бутылки водой из ручья и сохранение прочности костра при кипячении."""
    import asyncio
    from modules.finds import handle_explore_callback
    from modules.cooking import handle_campfire_callback
    from unittest.mock import patch

    # 1. Пополнение начатой бутылки из ручья
    game = GameState()
    game.location_index = 1
    game.current_location = "Ручей со змеями"
    game.ap = 5
    game.inventory = {"Бутылка дождевой воды": 1}
    game.rain_bottles = [8]

    # Мокаем randint <= 20 для 20% шанса ручья
    orig_randint = random.randint
    def fake_randint(a, b):
        if a == 1 and b == 100:
            return 15
        return orig_randint(a, b)

    with patch("random.randint", side_effect=fake_randint):
        asyncio.run(handle_explore_callback("action_1", game, 101))
    assert game.rain_bottles == [20]

    # 2. Кипячение воды во фляге не тратит прочность костра
    game.campfire_active = True
    game.campfire_durability = 6
    game.equipment["flask"] = "Армейская фляга"
    game.flask_water = 0

    asyncio.run(handle_campfire_callback("campfire_boil_water", game, 101))
    assert game.campfire_durability == 6
    assert game.flask_water == 20
    assert game.inventory.get("Пустая бутылка") == 1
    assert "Бутылка дождевой воды" not in game.inventory


def test_bark_cap_and_rain_fill_divisions():
    """Тест капа коры (6, 15) и наполнения бутылки дождевой водой на 2-6 делений."""
    import asyncio
    from modules.finds import RESOURCE_SOFT_CAPS, handle_explore_callback
    from unittest.mock import patch

    # 1. Кап коры поднят: soft 6, hard 15
    assert RESOURCE_SOFT_CAPS["Кусок коры"] == (6, 15)
    assert RESOURCE_SOFT_CAPS["Кора"] == (6, 15)

    # 2. Наполнение бутылки дождем даёт 2..6 делений
    game = GameState()
    game.weather = "rain"
    game.ap = 2
    game.inventory = {"Пустая бутылка": 1}

    with patch("random.randint", return_value=5):
        asyncio.run(handle_explore_callback("action_fill_rain_bottle", game, 101))
    assert game.rain_bottles == [5]
    assert game.inventory.get("Бутылка дождевой воды") == 1
    assert game.inventory.get("Пустая бутылка", 0) == 0


