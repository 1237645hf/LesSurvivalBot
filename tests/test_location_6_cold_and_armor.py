import pytest
from game_state import GameState
from modules.items import ITEMS
from crafts import do_craft, can_craft, CRAFT_RECIPES
from modules.finds import handle_explore_callback
from main import handle_sleep_action
from modules.traps import apply_trap_loot_to_inventory


@pytest.mark.l6
@pytest.mark.anyio
async def test_fur_items_registration_and_stats():
    """1. Регистрация предметов мехового сета, их характеристики и функционал футляра."""
    fur_pieces = [
        "Меховой капюшон",
        "Меховой плащ-нагрудник",
        "Меховые поножи",
        "Меховые сапоги",
    ]
    for piece in fur_pieces:
        assert piece in ITEMS
        assert ITEMS[piece]["rank"] == 3
        assert ITEMS[piece]["type"] == "armor"

    assert ITEMS["Меховой капюшон"]["effects"]["cold_protection"] == 15
    assert ITEMS["Меховой плащ-нагрудник"]["effects"]["cold_protection"] == 55
    assert ITEMS["Меховые поножи"]["effects"]["cold_protection"] == 15
    assert ITEMS["Меховые сапоги"]["effects"]["cold_protection"] == 15

    # Суммарный уворот
    total_dodge = sum(ITEMS[p]["effects"]["dodge"] for p in fur_pieces)
    assert total_dodge == 15

    # Экипировка и отображение в GameState
    game = GameState()
    game.equipment["head"] = "Меховой капюшон"
    game.equipment["torso"] = "Меховой плащ-нагрудник"
    game.equipment["pants"] = "Меховые поножи"
    game.equipment["boots"] = "Меховые сапоги"

    assert game.is_full_fur_set_equipped() is True
    assert game.cold_protection == 100
    assert game.dodge_chance == 15

    ui_text = game.get_character_text()
    assert "Теплоизоляция: 100%" in ui_text
    assert "КОМПЛЕКТ: 4 из 4 (Меховой)" in ui_text
    assert "Полная защита от холода (100%)" in ui_text

    # Функционал футляра на меховых поножах
    game.inventory["Янтарное зелье"] = 1
    from modules.items import handle_inventory_callback
    await handle_inventory_callback("pocket_insert_Янтарное зелье", game, 123)
    assert game.pants_pocket == "Янтарное зелье"
    assert "Футляр: Янтарное зелье" in game.get_character_text()


@pytest.mark.l6
def test_fur_crafting_from_inventory_and_equipped():
    """2. Проверка крафта: списание ресурсов, любой мох и улучшение прямо на персонаже."""
    game = GameState()
    game.inventory.clear()

    # Разблокируем рецепты
    game.set_story_flag("fur_recipes_unlocked", True)

    # Тест крафта в инвентаре с альтернативным мхом ("Сухой мох")
    game.inventory["Кожаный капюшон"] = 1
    game.inventory["Мех"] = 2
    game.inventory["Сухой мох"] = 1
    game.inventory["Кожа"] = 1
    game.inventory["Слизь"] = 1

    assert can_craft(game, "Меховой капюшон") is True
    ok, _ = do_craft(game, "Меховой капюшон")
    assert ok is True
    assert game.inventory.get("Меховой капюшон") == 1
    assert game.inventory.get("Кожаный капюшон", 0) == 0
    assert game.inventory.get("Сухой мох", 0) == 0
    assert game.inventory.get("Мех", 0) == 0

    # Тест крафта с надетого кожаного нагрудника прямо на персонаже
    game.equipment["torso"] = "Кожаный нагрудник"
    game.inventory["Мех"] = 10
    game.inventory["Пещерный мох"] = 4
    game.inventory["Кожа"] = 1
    game.inventory["Слизь"] = 5

    assert can_craft(game, "Меховой плащ-нагрудник") is True
    ok, _ = do_craft(game, "Меховой плащ-нагрудник")
    assert ok is True
    # Нагрудник должен быть заменён прямо на персонаже!
    assert game.equipment.get("torso") == "Меховой плащ-нагрудник"
    assert game.inventory.get("Меховой плащ-нагрудник", 0) == 0
    assert game.inventory.get("Мех", 0) == 0
    assert game.inventory.get("Пещерный мох", 0) == 0

    # Тест крафта поножей с сохранением кармана
    game.equipment["pants"] = "Кожаные поножи"
    game.pants_pocket = "Ягодный отвар"
    game.inventory["Мех"] = 5
    game.inventory["Мох"] = 3
    game.inventory["Кожа"] = 2
    game.inventory["Слизь"] = 1

    assert can_craft(game, "Меховые поножи") is True
    ok, _ = do_craft(game, "Меховые поножи")
    assert ok is True
    assert game.equipment.get("pants") == "Меховые поножи"
    assert game.pants_pocket == "Ягодный отвар"  # Карман сохранился


@pytest.mark.l6
def test_fur_hunter_unlock_trigger():
    """3. Открытие рецептов при первом получении меха."""
    game = GameState()
    game.inventory.clear()
    assert not game.is_story_flag_set("fur_recipes_unlocked")

    # Игрок получает добычу из ловушки
    apply_trap_loot_to_inventory(game, {"Мех": 2, "Сырое мясо": 3})

    assert game.inventory.get("Мех") == 2
    assert game.is_story_flag_set("fur_recipes_unlocked") is True
    assert "Меховой капюшон" in game.unlocked_crafts
    assert "Меховой плащ-нагрудник" in game.unlocked_crafts
    assert "Меховые поножи" in game.unlocked_crafts
    assert "Меховые сапоги" in game.unlocked_crafts

    # Проверка системного лога
    logs = [str(x) for x in game.event_log]
    assert any("прикидываешь выкройку" in log for log in logs)


@pytest.mark.l6
@pytest.mark.anyio
async def test_l6_exploration_cold_damage_and_full_set_immunity():
    """4. Урон от холода при исследовании L6 с math.floor, поглощение и иммунитет сета."""
    game = GameState()
    game.current_location = "Мохнатая пещера"
    game.location_index = 5
    game.ap = 10
    game.hp = 100
    game.hunger = 60
    game.thirst = 60

    # 1) Исследование без мехового сета (0% защиты, урон 10..15 HP)
    await handle_explore_callback("action_1", game, 1001)
    damage_taken = 100 - game.hp
    assert 10 <= damage_taken <= 15
    logs = [str(x) for x in game.event_log]
    assert any("Пронизывающий мороз пещеры" in log for log in logs)

    # 2) Прогрессивное снижение с math.floor: надеваем только Меховой плащ (55% защиты)
    # Незащищённость: (100 - 55) / 100 = 0.45
    # Фактический урон: math.floor(base_dmg * 0.45) -> для 10..15 даёт строго от 4 до 6 HP
    game.equipment["torso"] = "Меховой плащ-нагрудник"
    assert game.cold_protection == 55
    game.hp = 100
    game.event_log.clear()

    await handle_explore_callback("action_1", game, 1001)
    partial_dmg = 100 - game.hp
    assert 4 <= partial_dmg <= 6

    # 3) Надеваем полный меховой комплект (100% защиты)
    game.equipment["head"] = "Меховой капюшон"
    game.equipment["pants"] = "Меховые поножи"
    game.equipment["boots"] = "Меховые сапоги"
    assert game.cold_protection == 100

    hp_before = 80
    game.hp = hp_before
    game.event_log.clear()

    await handle_explore_callback("action_1", game, 1001)
    # Здоровье не уменьшилось от холода (голод/жажда сыты, урон 0)
    assert game.hp == hp_before
    new_logs = [str(x) for x in game.event_log]
    assert not any("мороз" in log.lower() for log in new_logs)
    assert not any("холод" in log.lower() for log in new_logs)

    # 4) Честная смерть от холода при исследовании на L6
    game.equipment.clear()  # Снимаем сет
    game.hp = 5
    game.ap = 5
    text, kb = await handle_explore_callback("action_1", game, 1001)
    assert game.hp == 0
    assert "ВЫ ПОГИБЛИ" in text
    assert "Смертельное переохлаждение" in text


@pytest.mark.l6
def test_l6_sleep_guard_and_sleep_damage():
    """5. Динамический гвард сна на основе actual_sleep_dmg (math.floor) и безопасный сон."""
    game = GameState()
    game.current_location = "Мохнатая пещера"
    game.location_index = 5
    game.equipment.clear()
    game.day = 1
    game.hunger = 60
    game.thirst = 60

    # 1) Базовый холод без брони (0% защиты, незащищённость 1.0)
    # Без костра: actual_sleep_dmg = 50. Гвард при HP <= 50
    game.hp = 50
    handle_sleep_action(game)
    assert game.day == 1  # Сон заблокирован
    logs = [str(x) for x in game.event_log]
    assert any("Засыпать на такой холодриге без подготовки — верная смерть!" in log for log in logs)

    # Сон разрешён при HP > 50 (например, 51 -> выживает с 1 HP)
    game.hp = 51
    game.event_log.clear()
    handle_sleep_action(game)
    assert game.day == 2
    assert game.hp == 1
    logs = [str(x) for x in game.event_log]
    assert any("Заснув в ледяной пещере без огня" in log for log in logs)

    # С костром без брони: actual_sleep_dmg = 30. Гвард при HP <= 30
    game.campfire_active = True
    game.campfire_durability = 10
    game.hp = 30
    handle_sleep_action(game)
    assert game.day == 2  # Сон заблокирован
    game.hp = 31
    handle_sleep_action(game)
    assert game.day == 3  # Сон разрешен
    assert game.hp == 1

    # 2) Прогрессивное снижение урона во сне с math.floor:
    # Надеваем Меховой плащ (55% защиты, незащищённость 0.45)
    game.equipment["torso"] = "Меховой плащ-нагрудник"
    assert game.cold_protection == 55

    # Без костра: math.floor(50 * 0.45) = 22 урона.
    # Динамический гвард: при HP <= 22 блокируется, при HP = 23 разрешён!
    game.campfire_active = False
    game.hp = 22
    handle_sleep_action(game)
    assert game.day == 3  # Заблокирован при HP <= 22!

    game.hp = 23
    game.event_log.clear()
    handle_sleep_action(game)
    assert game.day == 4  # Разрешён при HP == 23!
    assert game.hp == 1  # 23 - 22 = 1 HP
    logs = [str(x) for x in game.event_log]
    assert any("-22 HP" in log for log in logs)

    # С костром: math.floor(30 * 0.45) = 13 урона.
    # Динамический гвард: при HP <= 13 блокируется, при HP = 14 разрешён!
    game.campfire_active = True
    game.campfire_durability = 10
    game.hp = 13
    handle_sleep_action(game)
    assert game.day == 4  # Заблокирован при HP <= 13!

    game.hp = 14
    game.event_log.clear()
    handle_sleep_action(game)
    assert game.day == 5  # Разрешён при HP == 14!
    assert game.hp == 1  # 14 - 13 = 1 HP
    logs = [str(x) for x in game.event_log]
    assert any("-13 HP" in log for log in logs)

    # 3) Сон в полном меховом сете (100% защиты) -> actual_sleep_dmg = 0, безопасный сон
    game.equipment["head"] = "Меховой капюшон"
    game.equipment["pants"] = "Меховые поножи"
    game.equipment["boots"] = "Меховые сапоги"
    game.hp = 80
    game.event_log.clear()
    handle_sleep_action(game)
    assert game.day == 6
    assert game.hp == 80
    logs = [str(x) for x in game.event_log]
    assert not any("обмороз" in log.lower() for log in logs)

    # 4) Флаг warm_cave_shelter -> actual_sleep_dmg = 0 даже без брони и с 1 HP
    game.equipment.clear()
    game.set_story_flag("warm_cave_shelter", True)
    game.hp = 1
    game.event_log.clear()
    handle_sleep_action(game)
    assert game.day == 7
    assert game.hp == 1


@pytest.mark.l6
def test_warm_cave_entry_and_free_wall_fur():
    """6. Вход в Тёплую пещеру, разблокировка рецептов и неисчерпаемый мех со стен."""
    from story.locations.loc6_furry_cave import handle_location_6_furry_cave
    from crafts import get_craft_menu_text

    game = GameState()
    game.current_location = "Мохнатая пещера"
    game.location_index = 5
    game.unlocked_crafts = ["Костёр", "Факел"]
    game.inventory.clear()

    # 1) Вход в Тёплую пещеру (активация шелтера через furry_cave_start)
    text, kb = handle_location_6_furry_cave("furry_cave_start", game, 1001)
    assert game.is_story_flag_set("warm_cave_shelter") is True
    assert game.is_story_flag_set("fur_recipes_unlocked") is True
    assert "Меховой капюшон" in game.unlocked_crafts
    assert "Меховой плащ-нагрудник" in game.unlocked_crafts
    assert "Меховые поножи" in game.unlocked_crafts
    assert "Меховые сапоги" in game.unlocked_crafts

    # 2) В свёртке лежат выкройки и мех
    text_bundle, _ = handle_location_6_furry_cave("furry_bundle", game, 1001)
    assert "выкройки" in text_bundle
    # Берём весь сюжетный мех (+3)
    handle_location_6_furry_cave("furry_take_all", game, 1001)
    assert game.inventory["Мех"] == 3

    # 3) Проверяем отображение в меню крафта: "Мех: со стен пещеры (в избытке)" и пояснение
    craft_menu = get_craft_menu_text(game)
    assert "Мех: со стен пещеры (в избытке)" in craft_menu
    assert "Мех взят из запасов пещеры — здесь его более чем в избытке" in craft_menu

    # 4) Крафтим "Меховой капюшон":
    # Требуется: Кожаный капюшон ×1 + Мех ×2 + Пещерный мох ×1 + Кожа ×1 + Слизь ×1
    game.inventory["Кожаный капюшон"] = 1
    game.inventory["Пещерный мох"] = 1
    game.inventory["Кожа"] = 1
    game.inventory["Слизь"] = 1

    ok, msg = do_craft(game, "Меховой капюшон")
    assert ok is True
    assert "Мех взят из запасов пещеры" in msg
    # Сюжетный мех в инвентаре остался НЕТРОНУТЫМ (3 шт.)!
    assert game.inventory["Мех"] == 3
    # Остальные компоненты списались:
    assert game.inventory.get("Кожаный капюшон", 0) == 0
    assert game.inventory.get("Пещерный мох", 0) == 0
    assert game.inventory.get("Кожа", 0) == 0
    assert game.inventory.get("Слизь", 0) == 0
    assert game.inventory.get("Меховой капюшон", 0) == 1

    # 5) Крафт при 0 Меха в инвентаре тоже работает благодаря запасам пещеры
    game.inventory["Мех"] = 0
    game.inventory["Кожаные сапоги"] = 1
    game.inventory["Пещерный мох"] = 2
    game.inventory["Кожа"] = 2
    game.inventory["Слизь"] = 2

    assert can_craft(game, "Меховые сапоги") is True
    ok, msg = do_craft(game, "Меховые сапоги")
    assert ok is True
    assert game.inventory.get("Мех", 0) == 0
    assert game.inventory.get("Меховые сапоги", 0) == 1


@pytest.mark.l6
def test_l6_ascent_progression_and_milestones():
    """7. Подъём на L6: 40 исследований, логи [Подъём: X/40] и утверждённые шаги 2, 4, 7, 8, 10."""
    from story.location_stories import check_forest_research_story_trigger
    from story.locations.loc6_furry_cave import handle_location_6_furry_cave

    game = GameState()
    game.current_location = "Мохнатая пещера"
    game.location_index = 5
    game.unlocked_crafts = ["Костёр", "Факел"]
    assert game.story_flags.get("l6_ascent_progress", 0) == 0

    # Шаг 1: обычный подъём
    ev, log = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    assert game.story_flags["l6_ascent_progress"] == 1
    logs = [str(x) for x in game.event_log]
    assert any("[Подъём: 1/40]" in l for l in logs)

    # Шаг 2: Веха 2 — Интерактивный хаб структуры пещеры
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step2_hub"
    assert game.story_flags["l6_ascent_progress"] == 2

    # Проверяем хаб: 3 кнопки осмотра + 1 кнопка подъёма
    text, kb = handle_location_6_furry_cave("l6_step2_hub", game, 1001)
    assert len(text) >= 380 and len(text) <= 580
    assert len(kb.inline_keyboard) == 4

    # Осмотр стока воды: экран 2.1
    text_w, kb_w = handle_location_6_furry_cave("l6_step2_water", game, 1001)
    assert len(text_w) >= 350 and len(text_w) <= 430
    assert game.is_story_flag_set("l6_step2_water_seen")

    # Возврат в хаб: кнопка стока скрылась, осталось 3 кнопки
    text_h2, kb_h2 = handle_location_6_furry_cave("l6_step2_hub", game, 1001)
    assert len(kb_h2.inline_keyboard) == 3

    # Осмотр людей (2.2) и разлома (2.3)
    text_p, _ = handle_location_6_furry_cave("l6_step2_people", game, 1001)
    assert len(text_p) >= 350 and len(text_p) <= 430
    text_c, _ = handle_location_6_furry_cave("l6_step2_chasm", game, 1001)
    assert len(text_c) >= 350 and len(text_c) <= 430

    # Завершение шага 2
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)
    assert game.story_state is None

    # Шаг 3: обычный подъём
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    assert game.story_flags["l6_ascent_progress"] == 3

    # Шаг 4: Веха 4 — Шатающийся уступ и схрон
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step4_main"
    assert game.story_flags["l6_ascent_progress"] == 4
    text4, kb4 = handle_location_6_furry_cave("l6_step4_main", game, 1001)
    assert len(text4) >= 380 and len(text4) <= 580
    assert len(kb4.inline_keyboard) == 3

    # Выбор 4.3: Вбить клин под плиту (+1 вмешательство)
    handle_location_6_furry_cave("l6_step4_wedge", game, 1001)
    assert game.narrative_karma["intervention"] == 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Тестируем схрон шага 4 на отдельном состоянии
    g4 = GameState()
    g4.inventory.clear()
    g4.inventory["Жареное мясо"] = 2
    text4_i, kb4_i = handle_location_6_furry_cave("l6_step4_inspect", g4, 1001)
    assert g4.inventory.get("Спички", 0) == 1
    assert g4.inventory.get("Пещерный мох", 0) == 1
    # Положить подарок взамен (+1 сострадание)
    handle_location_6_furry_cave("l6_step4_leave_gift", g4, 1001)
    assert g4.narrative_karma["compassion"] == 1
    assert g4.inventory.get("Жареное мясо") == 1

    # Шаги 5-6:
    for i in range(5, 7):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i

    # Шаг 7: Веха 7 — Окно в облака и непуганые бараны
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_ascent_step7"
    assert game.story_flags["l6_ascent_progress"] == 7
    text7, kb7 = handle_location_6_furry_cave("l6_ascent_step7", game, 1001)
    assert len(text7) >= 380 and len(text7) <= 580
    assert len(kb7.inline_keyboard) == 3

    # Наблюдать (+1 Наблюдение)
    handle_location_6_furry_cave("l6_step7_observe", game, 1001)
    assert game.narrative_karma["observation"] == 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаг 8: Веха 8 — Дыхание стужи и спутник (кот / без кота)
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step8_main"
    assert game.story_flags["l6_ascent_progress"] == 8

    # Без питомца
    text8_no_pet, _ = handle_location_6_furry_cave("l6_step8_main", game, 1001)
    assert len(text8_no_pet) >= 380 and len(text8_no_pet) <= 580
    assert "Котёнок" not in text8_no_pet

    # С питомцем
    game.set_story_flag("has_pet", True)
    text8_pet, _ = handle_location_6_furry_cave("l6_step8_main", game, 1001)
    assert len(text8_pet) >= 380 and len(text8_pet) <= 580
    assert "Котёнок забился глубоко под одежду за пазухой" in text8_pet
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаг 9:
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    assert game.story_flags["l6_ascent_progress"] == 9

    # Шаг 10: Веха 10 — Вмёрзшая стоянка у очага
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step10_main"
    assert game.story_flags["l6_ascent_progress"] == 10

    text10, kb10 = handle_location_6_furry_cave("l6_step10_main", game, 1001)
    assert len(text10) >= 380 and len(text10) <= 580
    assert len(kb10.inline_keyboard) == 3

    # Осмотреть за ларчиком (без начисления кармы, чистый осмотр)
    obs_b10 = game.narrative_karma["observation"]
    handle_location_6_furry_cave("l6_step10_behind", game, 1001)
    assert game.narrative_karma["observation"] == obs_b10

    # Забрать ларчик (+1 Древесный уголь, +1 Зелье здоровья)
    handle_location_6_furry_cave("l6_step10_box", game, 1001)
    assert game.inventory.get("Древесный уголь", 0) >= 1
    assert game.inventory.get("Зелье здоровья", 0) >= 1

    # Забрать всё / продолжить (без кармы за уход)
    handle_location_6_furry_cave("l6_step10_take_all", game, 1001)
    assert game.narrative_karma["pragmatism"] == 0

    # Шаги 11-12: обычный подъём
    for i in range(11, 13):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i

    # Шаг 13: Веха 13 — Расколотая арка и камнепад
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step13_main"
    assert game.story_flags["l6_ascent_progress"] == 13
    text13, kb13 = handle_location_6_furry_cave("l6_step13_main", game, 1001)
    assert len(text13) >= 380 and len(text13) <= 580
    assert len(kb13.inline_keyboard) == 3

    # Выбор 13.2а: Наблюдение (безопасный обход, снята карма)
    text13_obs, _ = handle_location_6_furry_cave("l6_step13_observe", game, 1001)
    assert len(text13_obs) >= 350 and len(text13_obs) <= 430
    assert game.narrative_karma["observation"] == 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Проверка урона -10 HP на шаге 13.2б
    g13 = GameState()
    g13.hp = 50
    handle_location_6_furry_cave("l6_step13_break", g13, 1001)
    assert g13.hp == 40
    assert g13.narrative_karma["intervention"] == 1

    # Шаг 14:
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    assert game.story_flags["l6_ascent_progress"] == 14

    # Шаг 15: Веха 15 — Заброшенный грузовой подъёмник
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step15_main"
    assert game.story_flags["l6_ascent_progress"] == 15
    text15, kb15 = handle_location_6_furry_cave("l6_step15_main", game, 1001)
    assert len(text15) >= 380 and len(text15) <= 580
    assert len(kb15.inline_keyboard) == 1

    # Экран 15.1б: Детали и развилка
    text15_b, kb15_b = handle_location_6_furry_cave("l6_step15_detail", game, 1001)
    assert len(text15_b) >= 380 and len(text15_b) <= 580
    assert len(kb15_b.inline_keyboard) == 3

    # Срезать кожу (+1 Кожа, +1 Прагматизм)
    text15_lea, _ = handle_location_6_furry_cave("l6_step15_leather", game, 1001)
    assert len(text15_lea) >= 350 and len(text15_lea) <= 430
    assert game.inventory.get("Кожа", 0) == 1
    assert game.narrative_karma["pragmatism"] == 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаг 16:
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    assert game.story_flags["l6_ascent_progress"] == 16

    # Шаг 17: Веха 17 — Скользкий карниз и переходящая сумка
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step17_main"
    assert game.story_flags["l6_ascent_progress"] == 17
    text17, kb17 = handle_location_6_furry_cave("l6_step17_main", game, 1001)
    assert len(text17) >= 380 and len(text17) <= 580
    assert len(kb17.inline_keyboard) == 3

    # Проверка сумки (прямое взятие припасов и выбор действий)
    text17_bag, kb17_bag = handle_location_6_furry_cave("l6_step17_bag", game, 1001)
    assert len(text17_bag) >= 380 and len(text17_bag) <= 580
    assert len(kb17_bag.inline_keyboard) == 3
    assert any(b.callback_data == "l6_step17_take_all" for row in kb17_bag.inline_keyboard for b in row)
    assert game.inventory.get("Мех", 0) >= 1
    assert game.inventory.get("Жареное мясо", 0) >= 1

    # Повторная проверка сумки (пустая сумка)
    text17_empty, kb17_empty = handle_location_6_furry_cave("l6_step17_bag", game, 1001)
    assert len(text17_empty) >= 380 and len(text17_empty) <= 580
    assert "пусто" in text17_empty.lower()

    # Оставить подарок (+1 Сострадание, списание еды без дублирования лута)
    g17 = GameState()
    g17.inventory["Жареное мясо"] = 2
    text17_gift, _ = handle_location_6_furry_cave("l6_step17_leave_gift", g17, 1001)
    assert len(text17_gift) >= 380 and len(text17_gift) <= 580
    assert g17.narrative_karma["compassion"] == 1
    assert g17.inventory.get("Жареное мясо", 0) == 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаги 18-19:
    for i in range(18, 20):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i

    # Шаг 20: Веха 20 — Извилистые штольни и морозный морок
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step20_main"
    assert game.story_flags["l6_ascent_progress"] == 20
    text20, kb20 = handle_location_6_furry_cave("l6_step20_main", game, 1001)
    assert len(text20) >= 380 and len(text20) <= 580
    assert len(kb20.inline_keyboard) == 3

    # 20.2а: Наблюдение (+1 Наблюдение)
    text20_obs, _ = handle_location_6_furry_cave("l6_step20_observe", game, 1001)
    assert len(text20_obs) >= 380 and len(text20_obs) <= 580
    assert game.narrative_karma["observation"] == 2

    # 20.2б: Сострадание с питомцем и без
    game.set_story_flag("has_pet", False)
    text20_no_pet, _ = handle_location_6_furry_cave("l6_step20_compassion", game, 1001)
    assert len(text20_no_pet) >= 380 and len(text20_no_pet) <= 580
    assert "Котёнок" not in text20_no_pet

    game.set_story_flag("has_pet", True)
    text20_pet, _ = handle_location_6_furry_cave("l6_step20_compassion", game, 1001)
    assert len(text20_pet) >= 380 and len(text20_pet) <= 580
    assert "Котёнок забился глубоко" in text20_pet

    # 20.2в: Прагматизм (+1 Прагматизм)
    text20_prag, _ = handle_location_6_furry_cave("l6_step20_pragmatism", game, 1001)
    assert len(text20_prag) >= 380 and len(text20_prag) <= 580
    assert game.narrative_karma["pragmatism"] == 2
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаги 21-22: обычный подъём
    for i in range(21, 23):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i

    # Шаг 23: Шёпот из толщи монолита
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step23_main"
    assert game.story_flags["l6_ascent_progress"] == 23

    text23, kb23 = handle_location_6_furry_cave("l6_step23_main", game, 1001)
    assert len(text23) >= 380 and len(text23) <= 580
    assert len(kb23.inline_keyboard) == 1

    text23_b, kb23_b = handle_location_6_furry_cave("l6_step23_detail", game, 1001)
    assert len(text23_b) >= 380 and len(text23_b) <= 580
    assert len(kb23_b.inline_keyboard) == 3

    # 23.2а: Вмешательство
    text23_int, _ = handle_location_6_furry_cave("l6_step23_intervene", game, 1001)
    assert len(text23_int) >= 380 and len(text23_int) <= 580
    assert game.narrative_karma["intervention"] == 2

    # 23.2б: Разум (соло и с питомцем)
    obs_before = game.narrative_karma["observation"]
    game.set_story_flag("has_pet", False)
    text23_solo, _ = handle_location_6_furry_cave("l6_step23_mind", game, 1001)
    assert len(text23_solo) >= 380 and len(text23_solo) <= 580
    assert "Котёнок" not in text23_solo

    game.set_story_flag("has_pet", True)
    text23_pet, _ = handle_location_6_furry_cave("l6_step23_mind", game, 1001)
    assert len(text23_pet) >= 380 and len(text23_pet) <= 580
    assert "Котёнок шевелится" in text23_pet
    assert game.narrative_karma["observation"] == obs_before + 2

    # 23.2в: Прагматизм
    prag_before = game.narrative_karma["pragmatism"]
    text23_prag, _ = handle_location_6_furry_cave("l6_step23_pragmatism", game, 1001)
    assert len(text23_prag) >= 380 and len(text23_prag) <= 580
    assert game.narrative_karma["pragmatism"] == prag_before + 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаг 24: обычный подъём
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    assert game.story_flags["l6_ascent_progress"] == 24

    # Шаг 25: Снежный баран в расщелине
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step25_main"
    assert game.story_flags["l6_ascent_progress"] == 25

    text25, kb25 = handle_location_6_furry_cave("l6_step25_main", game, 1001)
    assert len(text25) >= 380 and len(text25) <= 580
    assert len(kb25.inline_keyboard) == 1

    text25_b, kb25_b = handle_location_6_furry_cave("l6_step25_detail", game, 1001)
    assert len(text25_b) >= 380 and len(text25_b) <= 580
    assert len(kb25_b.inline_keyboard) == 3

    # 25.2а: Силовое спасение (+1 Вмешательство)
    int_before = game.narrative_karma["intervention"]
    text25_int, _ = handle_location_6_furry_cave("l6_step25_intervene", game, 1001)
    assert len(text25_int) >= 380 and len(text25_int) <= 580
    assert game.narrative_karma["intervention"] == int_before + 1

    # 25.2б: Забота (соло и с питомцем)
    comp_before = game.narrative_karma["compassion"]
    game.set_story_flag("has_pet", False)
    text25_solo, _ = handle_location_6_furry_cave("l6_step25_compassion", game, 1001)
    assert len(text25_solo) >= 380 and len(text25_solo) <= 580
    assert "Котёнок" not in text25_solo

    game.set_story_flag("has_pet", True)
    text25_pet, _ = handle_location_6_furry_cave("l6_step25_compassion", game, 1001)
    assert len(text25_pet) >= 380 and len(text25_pet) <= 580
    assert "котёнок под одеждой за пазухой" in text25_pet
    assert game.narrative_karma["compassion"] == comp_before + 2

    # 25.2в: Прагматизм
    prag_before25 = game.narrative_karma["pragmatism"]
    text25_prag, _ = handle_location_6_furry_cave("l6_step25_pragmatism", game, 1001)
    assert len(text25_prag) >= 380 and len(text25_prag) <= 580
    assert game.narrative_karma["pragmatism"] == prag_before25 + 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаг 26: обычный подъём
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    assert game.story_flags["l6_ascent_progress"] == 26

    # Шаг 27: Каменный завал в штольне
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step27_main"
    assert game.story_flags["l6_ascent_progress"] == 27
    text27, kb27 = handle_location_6_furry_cave("l6_step27_main", game, 1001)
    assert len(text27) >= 380 and len(text27) <= 580
    assert len(kb27.inline_keyboard) == 3

    # 27.2а: Лаз под завалом (+1 Прагматизм)
    prag_b27 = game.narrative_karma["pragmatism"]
    text27_cr, _ = handle_location_6_furry_cave("l6_step27_crawl", game, 1001)
    assert len(text27_cr) >= 380 and len(text27_cr) <= 580
    assert game.narrative_karma["pragmatism"] == prag_b27 + 1

    # 27.2б: Разборка вручную (+1 Вмешательство, -5 HP)
    g27 = GameState()
    g27.hp = 50
    text27_cl, _ = handle_location_6_furry_cave("l6_step27_clear", g27, 1001)
    assert len(text27_cl) >= 380 and len(text27_cl) <= 580
    assert g27.hp == 45
    assert g27.narrative_karma["intervention"] == 1

    # 27.2в: Обход по верху (+1 Наблюдение)
    obs_b27 = game.narrative_karma["observation"]
    text27_up, _ = handle_location_6_furry_cave("l6_step27_climb", game, 1001)
    assert len(text27_up) >= 380 and len(text27_up) <= 580
    assert game.narrative_karma["observation"] == obs_b27 + 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаги 28-29: обычный подъём
    for i in range(28, 30):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i

    # Шаг 30: Лик каменного исполина
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step30_main"
    assert game.story_flags["l6_ascent_progress"] == 30
    text30, kb30 = handle_location_6_furry_cave("l6_step30_main", game, 1001)
    assert len(text30) >= 380 and len(text30) <= 580
    assert len(kb30.inline_keyboard) == 3

    # 30.2а: Ответ камню (+1 Вмешательство, флаг l6_golem_greeted)
    int_b30 = game.narrative_karma["intervention"]
    text30_spk, _ = handle_location_6_furry_cave("l6_step30_speak", game, 1001)
    assert len(text30_spk) >= 380 and len(text30_spk) <= 580
    assert game.story_flags.get("l6_golem_greeted") is True
    assert game.narrative_karma["intervention"] == int_b30 + 1

    # 30.2б: Согревание у пара (соло и питомец, +1 Сострадание)
    comp_b30 = game.narrative_karma["compassion"]
    game.set_story_flag("has_pet", False)
    text30_solo, _ = handle_location_6_furry_cave("l6_step30_steam", game, 1001)
    assert len(text30_solo) >= 380 and len(text30_solo) <= 580
    assert "котёнок" not in text30_solo.lower()

    game.set_story_flag("has_pet", True)
    text30_pet, _ = handle_location_6_furry_cave("l6_step30_steam", game, 1001)
    assert len(text30_pet) >= 380 and len(text30_pet) <= 580
    assert "котёнк" in text30_pet.lower()
    assert game.narrative_karma["compassion"] == comp_b30 + 2

    # 30.2в: Проверка снаряжения (+1 Прагматизм)
    prag_b30 = game.narrative_karma["pragmatism"]
    text30_gr, _ = handle_location_6_furry_cave("l6_step30_gear", game, 1001)
    assert len(text30_gr) >= 380 and len(text30_gr) <= 580
    assert game.narrative_karma["pragmatism"] == prag_b30 + 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаги 31-32: обычный подъём
    for i in range(31, 33):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i

    # Шаг 33: Тектонический разлом и старая переправа
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step33_main"
    assert game.story_flags["l6_ascent_progress"] == 33
    text33, kb33 = handle_location_6_furry_cave("l6_step33_main", game, 1001)
    assert len(text33) >= 380 and len(text33) <= 580
    assert len(kb33.inline_keyboard) == 3

    # 33.2а: Переход по бревну (+1 Прагматизм)
    prag_b33 = game.narrative_karma["pragmatism"]
    text33_cr, _ = handle_location_6_furry_cave("l6_step33_cross", game, 1001)
    assert len(text33_cr) >= 380 and len(text33_cr) <= 580
    assert game.narrative_karma["pragmatism"] == prag_b33 + 1

    # 33.2б: Укрепление клиньями (+1 Вмешательство)
    int_b33 = game.narrative_karma["intervention"]
    text33_br, _ = handle_location_6_furry_cave("l6_step33_brace", game, 1001)
    assert len(text33_br) >= 380 and len(text33_br) <= 580
    assert game.narrative_karma["intervention"] == int_b33 + 1

    # 33.2в: Поиск в нише (+1 Наблюдение, +1 Спички)
    obs_b33 = game.narrative_karma["observation"]
    text33_sr, _ = handle_location_6_furry_cave("l6_step33_search", game, 1001)
    assert len(text33_sr) >= 380 and len(text33_sr) <= 580
    assert game.narrative_karma["observation"] == obs_b33 + 1
    assert game.inventory.get("Спички", 0) >= 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаги 34-35: обычный подъём
    for i in range(34, 36):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i

    # Шаг 36: Пик ледяного морока
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step36_main"
    assert game.story_flags["l6_ascent_progress"] == 36
    text36, kb36 = handle_location_6_furry_cave("l6_step36_main", game, 1001)
    assert len(text36) >= 380 and len(text36) <= 580
    assert len(kb36.inline_keyboard) == 3

    # 36.2а: Рассеять морок (+1 Прагматизм)
    prag_b36 = game.narrative_karma["pragmatism"]
    text36_fc, _ = handle_location_6_furry_cave("l6_step36_focus", game, 1001)
    assert len(text36_fc) >= 380 and len(text36_fc) <= 580
    assert game.narrative_karma["pragmatism"] == prag_b36 + 1

    # 36.2б: Проверить звук (+1 Вмешательство, +1 Пещерный мох)
    int_b36 = game.narrative_karma["intervention"]
    text36_inv, _ = handle_location_6_furry_cave("l6_step36_investigate", game, 1001)
    assert len(text36_inv) >= 380 and len(text36_inv) <= 580
    assert game.narrative_karma["intervention"] == int_b36 + 1
    assert game.inventory.get("Пещерный мох", 0) >= 1

    # 36.2в: Прислушаться к чутью (соло и питомец, +1 Сострадание)
    comp_b36 = game.narrative_karma["compassion"]
    game.set_story_flag("has_pet", False)
    text36_solo, _ = handle_location_6_furry_cave("l6_step36_instinct", game, 1001)
    assert len(text36_solo) >= 380 and len(text36_solo) <= 580
    assert "котёнок" not in text36_solo.lower()

    game.set_story_flag("has_pet", True)
    text36_pet, _ = handle_location_6_furry_cave("l6_step36_instinct", game, 1001)
    assert len(text36_pet) >= 380 and len(text36_pet) <= 580
    assert "котёнок" in text36_pet.lower()
    assert game.narrative_karma["compassion"] == comp_b36 + 2
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаг 37: обычный подъём
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    assert game.story_flags["l6_ascent_progress"] == 37

    # Шаг 38: Дыхание горы (геотермальное тепло)
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step38_main"
    assert game.story_flags["l6_ascent_progress"] == 38
    text38, kb38 = handle_location_6_furry_cave("l6_step38_main", game, 1001)
    assert len(text38) >= 380 and len(text38) <= 580
    assert len(kb38.inline_keyboard) == 3

    # 38.2а: Коснуться скалы (+1 Вмешательство)
    int_b38 = game.narrative_karma["intervention"]
    text38_tch, _ = handle_location_6_furry_cave("l6_step38_touch", game, 1001)
    assert len(text38_tch) >= 380 and len(text38_tch) <= 580
    assert game.narrative_karma["intervention"] == int_b38 + 1

    # 38.2б: Изучить русло пара (+1 Наблюдение)
    obs_b38 = game.narrative_karma["observation"]
    text38_obs, _ = handle_location_6_furry_cave("l6_step38_observe", game, 1001)
    assert len(text38_obs) >= 380 and len(text38_obs) <= 580
    assert game.narrative_karma["observation"] == obs_b38 + 1

    # 38.2в: Ускорить шаг (+1 Прагматизм)
    prag_b38 = game.narrative_karma["pragmatism"]
    text38_rsh, _ = handle_location_6_furry_cave("l6_step38_rush", game, 1001)
    assert len(text38_rsh) >= 380 and len(text38_rsh) <= 580
    assert game.narrative_karma["pragmatism"] == prag_b38 + 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаг 39: Порог Мохнатой пещеры
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step39_main"
    assert game.story_flags["l6_ascent_progress"] == 39
    text39, kb39 = handle_location_6_furry_cave("l6_step39_main", game, 1001)
    assert len(text39) >= 380 and len(text39) <= 580
    assert len(kb39.inline_keyboard) == 3

    # 39.2а: Собрать мягкий мох (соло и питомец, +1 Сострадание, +1 Пещерный мох)
    comp_b39 = game.narrative_karma["compassion"]
    game.set_story_flag("has_pet", False)
    text39_solo, _ = handle_location_6_furry_cave("l6_step39_moss", game, 1001)
    assert len(text39_solo) >= 380 and len(text39_solo) <= 580
    assert "котёнок" not in text39_solo.lower()

    game.set_story_flag("has_pet", True)
    text39_pet, _ = handle_location_6_furry_cave("l6_step39_moss", game, 1001)
    assert len(text39_pet) >= 380 and len(text39_pet) <= 580
    assert "котёнк" in text39_pet.lower()
    assert game.narrative_karma["compassion"] == comp_b39 + 2

    # 39.2б: Оглянуться на путь назад (+1 Наблюдение)
    obs_b39 = game.narrative_karma["observation"]
    text39_lb, _ = handle_location_6_furry_cave("l6_step39_lookback", game, 1001)
    assert len(text39_lb) >= 380 and len(text39_lb) <= 580
    assert game.narrative_karma["observation"] == obs_b39 + 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаг 40: Веха завершения подъёма — открытие Тёплой пещеры
    assert not game.is_story_flag_set("warm_cave_shelter")
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_ascent_step40"
    assert game.story_flags["l6_ascent_progress"] == 40

    # Обработка l6_ascent_step40
    text, kb = handle_location_6_furry_cave("l6_ascent_step40", game, 1001)
    assert len(text) >= 380 and len(text) <= 580
    assert "Тёплая пещера" in text
    assert game.is_story_flag_set("warm_cave_shelter") is True
    assert game.is_story_flag_set("fur_recipes_unlocked") is True
    assert "Меховой капюшон" in game.unlocked_crafts
    assert "Меховой плащ-нагрудник" in game.unlocked_crafts
    assert "Меховые поножи" in game.unlocked_crafts
    assert "Меховые сапоги" in game.unlocked_crafts



@pytest.mark.l6
def test_l6_ascent_reset_on_leaving():
    """8. Сброс прогресса подъёма при отступлении из L6 до открытия Тёплой пещеры."""
    from story.location_stories import check_l6_ascent_leave

    game = GameState()
    game.current_location = "Мохнатая пещера"
    game.location_index = 5
    game.story_flags["l6_ascent_progress"] = 12
    assert not game.is_story_flag_set("warm_cave_shelter")

    # 1) Игрок уходит из Мохнатой пещеры в Стартовый лес
    check_l6_ascent_leave(game, "location_enter_1")
    assert game.story_flags.get("l6_ascent_progress") == 0
    logs = [str(x) for x in game.event_log]
    assert any("Ты отступил назад, спасаясь от стужи. Метель замела уступы" in l for l in logs)

    # 2) Если Тёплая пещера уже открыта — прогресс НЕ сбрасывается
    game.current_location = "Мохнатая пещера"
    game.story_flags["l6_ascent_progress"] = 30
    game.set_story_flag("warm_cave_shelter", True)
    game.event_log.clear()

    check_l6_ascent_leave(game, "location_enter_1")
    assert game.story_flags.get("l6_ascent_progress") == 30
    logs_after = [str(x) for x in game.event_log]
    assert not any("Ты отступил назад" in l for l in logs_after)


@pytest.mark.l6
def test_l6_ascent_leave_and_reenter_no_duplicate_stories():
    """Проверка правила: при уходе из L6 прогресс сбрасывается в 0, но пройденные сюжетные окна не повторяются."""
    from story.location_stories import check_forest_research_story_trigger
    from story.locations.loc6_furry_cave import handle_location_6_furry_cave

    game = GameState()
    game.current_location = "Мохнатая пещера"
    game.location_index = 5
    assert game.story_flags.get("l6_ascent_progress", 0) == 0

    # Шаг 1: обычный шаг
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    assert game.story_flags["l6_ascent_progress"] == 1

    # Шаг 2: срабатывает хаб l6_step2_hub
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step2_hub"
    assert game.story_flags["l6_ascent_progress"] == 2
    assert game.is_story_flag_set("l6_step2_seen")
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаг 3: обычный
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None

    # Шаг 4: срабатывает l6_step4_main
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step4_main"
    assert game.story_flags["l6_ascent_progress"] == 4
    assert game.is_story_flag_set("l6_step4_seen")
    # Берём лут
    m_before = game.inventory.get("Спички", 0)
    handle_location_6_furry_cave("l6_step4_inspect", game, 1001)
    assert game.inventory.get("Спички") == m_before + 1
    handle_location_6_furry_cave("l6_step4_take_all", game, 1001)

    # Доходим до шага 8
    for i in range(5, 7):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
    # Шаг 7
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_ascent_step7"
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)
    # Шаг 8
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_step8_main"
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    assert game.story_flags["l6_ascent_progress"] == 8

    # Игрок решает уйти в другую локацию (например, Стартовый лес)
    game.current_location = "Стартовый лес"
    # Прогресс сбросился в 0
    assert game.story_flags.get("l6_ascent_progress") == 0
    assert any("Ты отступил назад, спасаясь от стужи" in str(x) for x in game.event_log)

    # Игрок возвращается в Мохнатую пещеру
    game.current_location = "Мохнатая пещера"
    assert game.story_flags.get("l6_ascent_progress") == 0

    # Начинает подъём заново:
    # Шаг 1: обычный
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    assert game.story_flags["l6_ascent_progress"] == 1

    # Шаг 2: РАНЕЕ ПРОЙДЕН! Не должен вызываться повторно!
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None  # Никакого повторного сюжета!
    assert game.story_flags["l6_ascent_progress"] == 2

    # Шаг 3: обычный
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None

    # Шаг 4: РАНЕЕ ПРОЙДЕН! Не должен вызываться повторно и дублировать лут!
    matches_count = game.inventory.get("Спички", 0)
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None  # Не вызывается!
    assert game.story_flags["l6_ascent_progress"] == 4
    assert game.inventory.get("Спички", 0) == matches_count  # Лут не удвоился!

    # Шаги 5, 6:
    for i in range(5, 7):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None

    # Шаги 7 и 8: РАНЕЕ ПРОЙДЕНЫ!
    ev7, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev7 is None
    assert game.story_flags["l6_ascent_progress"] == 7

    ev8, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev8 is None
    assert game.story_flags["l6_ascent_progress"] == 8

    # Шаг 9: обычный
    ev9, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev9 is None
    assert game.story_flags["l6_ascent_progress"] == 9

    # Шаг 10: РАНЕЕ НЕ БЫЛ ПРОЙДЕН (игрок ушёл на 8-м)! Должен сработать!
    ev10, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev10 == "l6_step10_main"
    assert game.story_flags["l6_ascent_progress"] == 10
    assert game.is_story_flag_set("l6_step10_seen")


@pytest.mark.l6
def test_bundle_and_cache_duplication_prevented():
    """Проверка устранения бесконечного дюпа и дублирования лута в furry_bundle, step 17, step 4, step 10."""
    game = GameState()
    game.inventory.clear()

    # 1. Свёрток в Тёплой пещере (furry_bundle)
    from story.locations.loc6_furry_cave import handle_location_6_furry_cave, unlock_warm_cave_shelter
    unlock_warm_cave_shelter(game)

    # Первый осмотр свёртка
    text_b1, kb_b1 = handle_location_6_furry_cave("furry_bundle", game, 1001)
    assert len(text_b1) >= 380 and len(text_b1) <= 580
    btn_callbacks_1 = [b.callback_data for row in kb_b1.inline_keyboard for b in row]
    assert "furry_take_all" in btn_callbacks_1
    assert "furry_take_part" in btn_callbacks_1

    # Забираем весь мех (+3 Мех)
    text_ta, _ = handle_location_6_furry_cave("furry_take_all", game, 1001)
    assert len(text_ta) >= 380 and len(text_ta) <= 580
    assert game.inventory.get("Мех", 0) == 3
    assert game.is_story_flag_set("furry_bundle_taken")

    # Повторный вызов furry_take_all НЕ увеличивает мех и не ломает игру
    handle_location_6_furry_cave("furry_take_all", game, 1001)
    assert game.inventory.get("Мех", 0) == 3

    # Возврат в furry_bundle: кнопки взятия меха исчезли! Текст описывает пустой свёрток
    text_b2, kb_b2 = handle_location_6_furry_cave("furry_bundle", game, 1001)
    assert len(text_b2) >= 380 and len(text_b2) <= 580
    assert "пуст" in text_b2.lower()
    btn_callbacks_2 = [b.callback_data for row in kb_b2.inline_keyboard for b in row]
    assert "furry_take_all" not in btn_callbacks_2
    assert "furry_take_part" not in btn_callbacks_2
    assert "furry_take_remainder" not in btn_callbacks_2

    # Первый осмотр пещеры начисляет карму наблюдения (+1)
    obs_before = game.narrative_karma["observation"]
    handle_location_6_furry_cave("furry_examine", game, 1001)
    assert game.narrative_karma["observation"] == obs_before + 1
    # Повторный осмотр пещеры НЕ начисляет карму повторно
    handle_location_6_furry_cave("furry_examine", game, 1001)
    assert game.narrative_karma["observation"] == obs_before + 1

    # 2. Сумка у обрыва (l6_step17_bag)
    game.inventory.clear()
    text_bag1, kb_bag1 = handle_location_6_furry_cave("l6_step17_bag", game, 1001)
    assert len(text_bag1) >= 380 and len(text_bag1) <= 580
    assert game.inventory.get("Мех", 0) == 1
    assert game.inventory.get("Жареное мясо", 0) == 1
    assert game.is_story_flag_set("l6_step17_loot_taken")

    # Повторный осмотр сумки: предметы НЕ дублируются, текст сообщает о пустоте
    text_bag2, kb_bag2 = handle_location_6_furry_cave("l6_step17_bag", game, 1001)
    assert len(text_bag2) >= 380 and len(text_bag2) <= 580
    assert "пуст" in text_bag2.lower()
    assert game.inventory.get("Мех", 0) == 1
    assert game.inventory.get("Жареное мясо", 0) == 1

    # Ветка l6_step17_leave_gift не дублирует мех и мясо, а списывает еду и дает карму
    comp_before = game.narrative_karma["compassion"]
    text_gift1, _ = handle_location_6_furry_cave("l6_step17_leave_gift", game, 1001)
    assert len(text_gift1) >= 380 and len(text_gift1) <= 580
    assert game.inventory.get("Мех", 0) == 1
    assert game.inventory.get("Жареное мясо", 0) == 0  # Списано взамен
    assert game.narrative_karma["compassion"] == comp_before + 1
    assert game.is_story_flag_set("l6_step17_gift_left")

    # Повторный клик l6_step17_leave_gift не спамит карму
    handle_location_6_furry_cave("l6_step17_leave_gift", game, 1001)
    assert game.narrative_karma["compassion"] == comp_before + 1

    # 3. Тайник на шаге 4 (l6_step4_inspect)
    game.inventory.clear()
    text_s4_1, _ = handle_location_6_furry_cave("l6_step4_inspect", game, 1001)
    assert len(text_s4_1) >= 380 and len(text_s4_1) <= 580
    assert game.inventory.get("Спички", 0) == 1

    text_s4_2, _ = handle_location_6_furry_cave("l6_step4_inspect", game, 1001)
    assert len(text_s4_2) >= 380 and len(text_s4_2) <= 580
    assert "пуст" in text_s4_2.lower()
    assert game.inventory.get("Спички", 0) == 1  # Не за дюпался

    # 4. Ларчик на шаге 10 (l6_step10_box)
    game.inventory.clear()
    text_s10_1, _ = handle_location_6_furry_cave("l6_step10_box", game, 1001)
    assert len(text_s10_1) >= 380 and len(text_s10_1) <= 580
    assert game.inventory.get("Древесный уголь", 0) == 1
    assert game.inventory.get("Зелье здоровья", 0) == 1

    text_s10_2, _ = handle_location_6_furry_cave("l6_step10_box", game, 1001)
    assert len(text_s10_2) >= 380 and len(text_s10_2) <= 580
    assert "пуст" in text_s10_2.lower()
    assert game.inventory.get("Древесный уголь", 0) == 1
    assert game.inventory.get("Зелье здоровья", 0) == 1  # Не за дюпался

    # 5. Проверка кнопок и экранов take_all (шаги 4, 10, 17)
    # Шаг 4: take_all отдаёт нарративный экран и кнопку l6_ascent_continue
    text_s4_ta, kb_s4_ta = handle_location_6_furry_cave("l6_step4_take_all", game, 1001)
    assert len(text_s4_ta) >= 380 and len(text_s4_ta) <= 580
    assert any(b.callback_data == "l6_ascent_continue" for row in kb_s4_ta.inline_keyboard for b in row)

    # Шаг 10: box содержит кнопки перехода на l6_step10_leave_gift и l6_step10_take_all
    _, kb_s10_btns = handle_location_6_furry_cave("l6_step10_box", game, 1001)
    callbacks_10 = [b.callback_data for row in kb_s10_btns.inline_keyboard for b in row]
    assert "l6_step10_leave_gift" in callbacks_10
    assert "l6_step10_take_all" in callbacks_10
    text_s10_ta, kb_s10_ta = handle_location_6_furry_cave("l6_step10_take_all", game, 1001)
    assert len(text_s10_ta) >= 380 and len(text_s10_ta) <= 580
    assert any(b.callback_data == "l6_ascent_continue" for row in kb_s10_ta.inline_keyboard for b in row)

    # Шаг 17: bag содержит кнопки l6_step17_leave_gift и l6_step17_take_all
    g_fresh = GameState()
    _, kb_s17_btns = handle_location_6_furry_cave("l6_step17_bag", g_fresh, 1001)
    callbacks_17 = [b.callback_data for row in kb_s17_btns.inline_keyboard for b in row]
    assert "l6_step17_leave_gift" in callbacks_17
    assert "l6_step17_take_all" in callbacks_17
    text_s17_ta, kb_s17_ta = handle_location_6_furry_cave("l6_step17_take_all", game, 1001)
    assert len(text_s17_ta) >= 380 and len(text_s17_ta) <= 580
    assert any(b.callback_data == "l6_ascent_continue" for row in kb_s17_ta.inline_keyboard for b in row)


@pytest.mark.l6
def test_l6_gift_deduction_validation_and_death_resets():
    """Тест проверки наличия припасов при подарке (шаги 4, 10, 17) и сброса состояния при гибели."""
    game = GameState()
    from story.locations.loc6_furry_cave import handle_location_6_furry_cave

    # 1. Шаг 4: попытка оставить подарок с пустым инвентарём
    game.inventory.clear()
    comp_before = game.narrative_karma["compassion"]
    text_s4_fail, kb_s4_fail = handle_location_6_furry_cave("l6_step4_leave_gift", game, 1001)
    assert 380 <= len(text_s4_fail) <= 580
    assert game.narrative_karma["compassion"] == comp_before  # карма НЕ начислена
    assert not game.is_story_flag_set("l6_step4_gift_left")   # флаг НЕ установлен
    cb_s4_fail = [b.callback_data for row in kb_s4_fail.inline_keyboard for b in row]
    assert "l6_step4_take_all" in cb_s4_fail
    assert "l6_ascent_continue" in cb_s4_fail

    # Шаг 4: успешный подарок при наличии еды
    game.inventory["Жареное мясо"] = 1
    text_s4_ok, kb_s4_ok = handle_location_6_furry_cave("l6_step4_leave_gift", game, 1001)
    assert 380 <= len(text_s4_ok) <= 580
    assert game.narrative_karma["compassion"] == comp_before + 1
    assert game.is_story_flag_set("l6_step4_gift_left")
    assert game.inventory.get("Жареное мясо", 0) == 0

    # 2. Шаг 10: попытка оставить подарок без еды
    g10 = GameState()
    g10.inventory.clear()
    comp10_before = g10.narrative_karma["compassion"]
    text_s10_fail, kb_s10_fail = handle_location_6_furry_cave("l6_step10_leave_gift", g10, 1001)
    assert 380 <= len(text_s10_fail) <= 580
    assert g10.narrative_karma["compassion"] == comp10_before
    assert not g10.is_story_flag_set("l6_step10_gift_left")
    cb_s10_fail = [b.callback_data for row in kb_s10_fail.inline_keyboard for b in row]
    assert "l6_step10_take_all" in cb_s10_fail
    assert "l6_ascent_continue" in cb_s10_fail

    # Шаг 10: успешный подарок
    g10.inventory["Сухпай"] = 1
    text_s10_ok, _ = handle_location_6_furry_cave("l6_step10_leave_gift", g10, 1001)
    assert 380 <= len(text_s10_ok) <= 580
    assert g10.narrative_karma["compassion"] == comp10_before + 1
    assert g10.is_story_flag_set("l6_step10_gift_left")
    assert g10.inventory.get("Сухпай", 0) == 0

    # 3. Шаг 17: попытка оставить подарок без еды
    g17 = GameState()
    g17.inventory.clear()
    comp17_before = g17.narrative_karma["compassion"]
    text_s17_fail, kb_s17_fail = handle_location_6_furry_cave("l6_step17_leave_gift", g17, 1001)
    assert 380 <= len(text_s17_fail) <= 580
    assert g17.narrative_karma["compassion"] == comp17_before
    assert not g17.is_story_flag_set("l6_step17_gift_left")
    cb_s17_fail = [b.callback_data for row in kb_s17_fail.inline_keyboard for b in row]
    assert "l6_step17_take_all" in cb_s17_fail
    assert "l6_ascent_continue" in cb_s17_fail

    # Шаг 17: успешный подарок
    g17.inventory["Жареное мясо"] = 1
    text_s17_ok, _ = handle_location_6_furry_cave("l6_step17_leave_gift", g17, 1001)
    assert 380 <= len(text_s17_ok) <= 580
    assert g17.narrative_karma["compassion"] == comp17_before + 1
    assert g17.is_story_flag_set("l6_step17_gift_left")
    assert g17.inventory.get("Жареное мясо", 0) == 0

    # 4. Проверка сброса состояния при гибели на шаге 13
    g_d13 = GameState()
    g_d13.hp = 5
    g_d13.story_state = "some_state"
    g_d13.active_story_callback = "some_callback"
    text_d13, _ = handle_location_6_furry_cave("l6_step13_break", g_d13, 1001)
    assert g_d13.hp == 0
    assert g_d13.story_state is None
    assert g_d13.active_story_callback is None
    assert "Смертельный обвал" in text_d13

    # 5. Проверка сброса состояния при гибели на шаге 27
    g_d27 = GameState()
    g_d27.hp = 3
    g_d27.story_state = "some_state"
    g_d27.active_story_callback = "some_callback"
    text_d27, _ = handle_location_6_furry_cave("l6_step27_clear", g_d27, 1001)
    assert g_d27.hp == 0
    assert g_d27.story_state is None
    assert g_d27.active_story_callback is None
    assert "Обвал каменной осыпи" in text_d27

    # 6. Проверка furry_bundle при наличии left_something_in_bundle: только кнопка отхода
    g_b = GameState()
    g_b.set_story_flag("left_something_in_bundle", True)
    text_gb, kb_gb = handle_location_6_furry_cave("furry_bundle", g_b, 1001)
    assert 380 <= len(text_gb) <= 580
    cb_gb = [b.callback_data for row in kb_gb.inline_keyboard for b in row]
    assert "furry_take_all" not in cb_gb
    assert "furry_take_part" not in cb_gb
    assert "furry_bundle_leave" in cb_gb


@pytest.mark.l6
def test_l6_upper_ridge_and_stone_giant_obstacle():
    """Тест второй фазы L6: Верхний перевал, Каменный Исполин и разблокировка Святилища."""
    from story.locations.loc6_furry_cave import handle_location_6_furry_cave
    from story.location_stories import check_forest_research_story_trigger

    game = GameState()
    game.current_location = "Мохнатая пещера"
    game.location_index = 5
    game.set_story_flag("warm_cave_shelter", True)
    game.set_story_flag("visited_furry_cave", True)

    # 1. Проверка цепочки исследований перевала через триггер
    t1, _ = check_forest_research_story_trigger(game, 6, False)
    assert t1 == "l6_ridge_step1"
    assert game.story_flags["l6_ridge_progress"] == 1

    t2, _ = check_forest_research_story_trigger(game, 6, False)
    assert t2 == "l6_ridge_step2"
    assert game.story_flags["l6_ridge_progress"] == 2

    t3, _ = check_forest_research_story_trigger(game, 6, False)
    assert t3 == "l6_ridge_step3"
    assert game.story_flags["l6_ridge_progress"] == 3

    t4, _ = check_forest_research_story_trigger(game, 6, False)
    assert t4 == "l6_ridge_step4"
    assert game.story_flags["l6_ridge_progress"] == 4

    # 2. Проверка текстов и кнопок шагов перевала
    text1, kb1 = handle_location_6_furry_cave("l6_ridge_step1", game, 1001)
    assert 380 <= len(text1) <= 580
    assert all(len(b.text) <= 28 for row in kb1.inline_keyboard for b in row)

    text2, kb2 = handle_location_6_furry_cave("l6_ridge_step2", game, 1001)
    assert 380 <= len(text2) <= 580
    assert all(len(b.text) <= 28 for row in kb2.inline_keyboard for b in row)

    text3, kb3 = handle_location_6_furry_cave("l6_ridge_step3", game, 1001)
    assert 380 <= len(text3) <= 580
    assert all(len(b.text) <= 28 for row in kb3.inline_keyboard for b in row)

    text4, kb4 = handle_location_6_furry_cave("l6_ridge_step4", game, 1001)
    assert 380 <= len(text4) <= 580
    assert all(len(b.text) <= 28 for row in kb4.inline_keyboard for b in row)
    cb4 = [b.callback_data for row in kb4.inline_keyboard for b in row]
    assert "l6_giant_fight" in cb4
    assert "l6_giant_gift" in cb4
    assert "l6_giant_edge" in cb4

    # 3. Ветка боя (l6_giant_fight)
    g_fight = GameState()
    g_fight.hp = 50
    inter_before = g_fight.narrative_karma["intervention"]
    prag_before = g_fight.narrative_karma["pragmatism"]
    text_f, kb_f = handle_location_6_furry_cave("l6_giant_fight", g_fight, 1001)
    assert 380 <= len(text_f) <= 580
    assert g_fight.hp == 32  # 50 - 18
    assert g_fight.narrative_karma["intervention"] == inter_before + 2
    assert g_fight.narrative_karma["pragmatism"] == prag_before + 1
    assert all(len(b.text) <= 28 for row in kb_f.inline_keyboard for b in row)

    # 4. Ветка дара с едой (l6_giant_gift)
    g_gift = GameState()
    g_gift.inventory["Жареное мясо"] = 1
    comp_before = g_gift.narrative_karma["compassion"]
    obs_before = g_gift.narrative_karma["observation"]
    text_g, kb_g = handle_location_6_furry_cave("l6_giant_gift", g_gift, 1001)
    assert 380 <= len(text_g) <= 580
    assert g_gift.inventory.get("Жареное мясо", 0) == 0
    assert g_gift.narrative_karma["compassion"] == comp_before + 2
    assert g_gift.narrative_karma["observation"] == obs_before + 1
    assert all(len(b.text) <= 28 for row in kb_g.inline_keyboard for b in row)

    # Ветка дара без еды (жертва HP)
    g_gift_empty = GameState()
    g_gift_empty.hp = 40
    g_gift_empty.inventory.clear()
    text_ge, _ = handle_location_6_furry_cave("l6_giant_gift", g_gift_empty, 1001)
    assert 380 <= len(text_ge) <= 580
    assert g_gift_empty.hp == 30  # 40 - 10

    # 5. Ветка обхода по кромке (l6_giant_edge)
    g_edge = GameState()
    g_edge.hp = 50
    text_e, kb_e = handle_location_6_furry_cave("l6_giant_edge", g_edge, 1001)
    assert 380 <= len(text_e) <= 580
    assert g_edge.hp == 35  # 50 - 15
    assert all(len(b.text) <= 28 for row in kb_e.inline_keyboard for b in row)

    # 6. Финал победы и разблокировка Святилища (l6_giant_victory)
    g_vic = GameState()
    text_v, kb_v = handle_location_6_furry_cave("l6_giant_victory", g_vic, 1001)
    assert 380 <= len(text_v) <= 580
    assert all(len(b.text) <= 28 for row in kb_v.inline_keyboard for b in row)
    assert g_vic.is_story_flag_set("l6_giant_defeated") is True
    assert g_vic.is_story_flag_set("l6_completed") is True
    assert "Святилище" in g_vic.unlocked_locations
    cb_v = [b.callback_data for row in kb_v.inline_keyboard for b in row]
    assert "location_enter_7" in cb_v
    assert "l6_ascent_continue" in cb_v

    # 7. Честная смерть при бое и обходе
    g_dead_f = GameState()
    g_dead_f.hp = 10
    g_dead_f.story_state = "fight"
    g_dead_f.active_story_callback = "fight"
    t_df, _ = handle_location_6_furry_cave("l6_giant_fight", g_dead_f, 1001)
    assert g_dead_f.hp == 0
    assert g_dead_f.story_state is None
    assert g_dead_f.active_story_callback is None
    assert "Смертельный удар" in t_df

    g_dead_e = GameState()
    g_dead_e.hp = 10
    g_dead_e.story_state = "edge"
    g_dead_e.active_story_callback = "edge"
    t_de, _ = handle_location_6_furry_cave("l6_giant_edge", g_dead_e, 1001)
    assert g_dead_e.hp == 0
    assert g_dead_e.story_state is None
    assert g_dead_e.active_story_callback is None
    assert "Падение с ледяного карниза" in t_de


@pytest.mark.l6
def test_warm_cave_hub_extinguishing_and_ridge_delay():
    """Проверка логики Тёплой пещеры:
    1. При входе на локацию 6 не открывается сюжетный экран.
    2. Внутри пещеры кнопки гаснут по мере прохождения, остаётся только [В лагерь].
    3. Верхний хребет запускается на 5-й день после открытия пещеры на 2-е исследование.
    """
    from story.locations.loc6_furry_cave import handle_location_6_furry_cave
    from story.location_stories import check_forest_research_story_trigger

    game = GameState()
    game.day = 10
    game.current_location = "Мохнатая пещера"
    game.location_index = 5
    game.set_story_flag("warm_cave_shelter", True)

    # 1. Вход на локацию 6 НЕ открывает сюжетный экран
    ui_text, _ = handle_location_6_furry_cave("location_enter_6", game, 1001)
    assert game.story_state is None

    # 2. Хаб Тёплой пещеры (Экран 2.0)
    t0, kb0 = handle_location_6_furry_cave("furry_cave_start", game, 1001)
    assert 380 <= len(t0) <= 580
    cbs0 = [b.callback_data for row in kb0.inline_keyboard for b in row]
    assert "furry_examine" in cbs0
    assert "furry_warm" in cbs0
    assert "furry_sleep" in cbs0
    assert "furry_leave" in cbs0

    # Проходим осмотр и свёрток
    t_ex, kb_ex = handle_location_6_furry_cave("furry_examine", game, 1001)
    assert 380 <= len(t_ex) <= 580
    assert any(b.text == "↩️ Назад" and b.callback_data == "furry_cave_start" for row in kb_ex.inline_keyboard for b in row)
    handle_location_6_furry_cave("furry_take_all", game, 1001)

    # Проверяем, что на Экране 2.0 кнопка осмотра погасла
    _, kb_after_ex = handle_location_6_furry_cave("furry_cave_start", game, 1001)
    cbs_after_ex = [b.callback_data for row in kb_after_ex.inline_keyboard for b in row]
    assert "furry_examine" not in cbs_after_ex
    assert "furry_warm" in cbs_after_ex
    assert "furry_sleep" in cbs_after_ex

    # Проходим очаг
    t_w, kb_w = handle_location_6_furry_cave("furry_warm", game, 1001)
    assert 380 <= len(t_w) <= 580
    assert any(b.text == "↩️ Назад" and b.callback_data == "furry_cave_start" for row in kb_w.inline_keyboard for b in row)
    t_fr, kb_fr = handle_location_6_furry_cave("furry_fire_rest", game, 1001)
    assert 380 <= len(t_fr) <= 580

    # Проверяем, что кнопка очага погасла
    _, kb_after_w = handle_location_6_furry_cave("furry_cave_start", game, 1001)
    cbs_after_w = [b.callback_data for row in kb_after_w.inline_keyboard for b in row]
    assert "furry_examine" not in cbs_after_w
    assert "furry_warm" not in cbs_after_w
    assert "furry_sleep" in cbs_after_w

    # Проходим сон
    t_sl, kb_sl = handle_location_6_furry_cave("furry_sleep", game, 1001)
    assert 380 <= len(t_sl) <= 580
    t_loss, kb_loss = handle_location_6_furry_cave("furry_loss", game, 1001)
    assert 380 <= len(t_loss) <= 580
    assert any(b.text == "↩️ Назад" and b.callback_data == "furry_cave_start" for row in kb_loss.inline_keyboard for b in row)

    # Все три действия сделаны — осталась только кнопка [⛺ В лагерь]
    _, kb_final = handle_location_6_furry_cave("furry_cave_start", game, 1001)
    cbs_final = [b.callback_data for row in kb_final.inline_keyboard for b in row]
    assert "furry_examine" not in cbs_final
    assert "furry_warm" not in cbs_final
    assert "furry_sleep" not in cbs_final
    assert cbs_final == ["furry_leave"]

    # Нажатие [⛺ В лагерь] фиксирует день и возвращает в лагерь
    handle_location_6_furry_cave("furry_leave", game, 1001)
    assert game.story_flags["warm_cave_reached_day"] == 10
    assert game.is_story_flag_set("visited_furry_cave")

    # 3. Проверка запуска Верхнего хребта:
    # День 10..13 (до 5-го дня): сюжетка перевала НЕ стартует
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None
    game.day = 13
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev is None

    # День 14 (5-й день со дня 10):
    game.day = 14
    # 1-е исследование на 5-й день: ещё не запускается
    ev1, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev1 is None
    # 2-е исследование на 5-й день: запускает l6_ridge_step1!
    ev2, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev2 == "l6_ridge_step1"
