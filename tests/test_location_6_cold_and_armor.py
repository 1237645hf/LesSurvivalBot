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
    game.hunger = 100
    game.thirst = 100

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
    game.hunger = 100
    game.thirst = 100

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
    """7. Подъём на L6: 30 исследований, логи [Подъём: X/30] и 4 ключевых вехи."""
    from story.location_stories import check_forest_research_story_trigger, handle_story
    from story.locations.loc6_furry_cave import handle_location_6_furry_cave

    game = GameState()
    game.current_location = "Мохнатая пещера"
    game.location_index = 5
    game.unlocked_crafts = ["Костёр", "Факел"]
    assert game.story_flags.get("l6_ascent_progress", 0) == 0

    # Шаги 1-6: обычный подъём
    for i in range(1, 7):
        ev, log = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i
        logs = [str(x) for x in game.event_log]
        assert any(f"[Подъём: {i}/30]" in l for l in logs)

    # Шаг 7: Веха 1 — «Окно в облака и непуганые бараны»
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_ascent_step7"
    assert game.story_flags["l6_ascent_progress"] == 7

    # Выбор 1: Наблюдать (+Observation)
    text, kb = handle_location_6_furry_cave("l6_step7_observe", game, 1001)
    assert game.narrative_karma["observation"] == 1
    # Возврат в игровой процесс
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)
    assert game.story_state is None

    # Шаги 8-14:
    for i in range(8, 15):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i

    # Шаг 15: Веха 2 — «Вмёрзший привал и знак охотников»
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_ascent_step15"
    assert game.story_flags["l6_ascent_progress"] == 15

    # Выбор: Разгрести лёд (+Observation, +1 Древесный уголь)
    obs_before = game.narrative_karma["observation"]
    handle_location_6_furry_cave("l6_step15_observe", game, 1001)
    assert game.narrative_karma["observation"] == obs_before + 1
    assert game.inventory.get("Древесный уголь", 0) >= 1
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаги 16-21:
    for i in range(16, 22):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i

    # Шаг 22: Веха 3 — «Морозный морок (Шёпот из глубин)»
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_ascent_step22"
    assert game.story_flags["l6_ascent_progress"] == 22

    # Тестируем выбор Сострадания (+2 Compassion)
    handle_location_6_furry_cave("l6_whisper_compassion", game, 1001)
    assert game.narrative_karma["compassion"] == 2
    assert game.story_flags.get("l6_whisper_choice") == "compassion"
    handle_location_6_furry_cave("l6_ascent_continue", game, 1001)

    # Шаги 23-29:
    for i in range(23, 30):
        ev, _ = check_forest_research_story_trigger(game, 6, False)
        assert ev is None
        assert game.story_flags["l6_ascent_progress"] == i

    # Шаг 30: Веха 4 — «Тёплый оазис» (активация шелтера и рецептов)
    assert not game.is_story_flag_set("warm_cave_shelter")
    ev, _ = check_forest_research_story_trigger(game, 6, False)
    assert ev == "l6_ascent_step30"
    assert game.story_flags["l6_ascent_progress"] == 30

    # Обработка l6_ascent_step30
    text, kb = handle_location_6_furry_cave("l6_ascent_step30", game, 1001)
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


