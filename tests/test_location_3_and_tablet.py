"""
tests/test_location_3_and_tablet.py — Тесты механик Локации 3 (Скромная Лощина),
печи, сланцевой посуды, древесного угля и каменной плиты с записями.
"""

import pytest
from game_state import GameState
from crafts import do_craft
from modules.cooking import cook_item
from main import use_consumable, format_tablet_notes_text
from story.location_stories import (
    handle_location_2_ruchey,
    handle_location_3_slate_hollow,
    check_forest_research_story_trigger,
)
from services.database import (
    get_tablet_notes,
    save_tablet_note,
    DEFAULT_TABLET_NOTES,
)


@pytest.mark.l3
def test_stove_properties_and_rekindle():
    """Тест свойств печи: макс. прочность 30, розжиг при 0 за 2 AP."""
    game = GameState()
    game.current_location = "Скромная лощина"
    game.set_story_flag("l3_shelter_unlocked", True)
    assert game.is_stove is True

    # Прочность печи до 30
    game.campfire_durability = 0
    game.ap = 2
    game.hunger = 50
    game.thirst = 50

    ok, msg = game.rekindle_stove()
    assert ok is True
    assert game.campfire_durability == 1
    assert game.campfire_active is True
    assert game.ap == 0
    assert game.hunger == 43  # -7
    assert game.thirst == 32  # -18


@pytest.mark.l3
def test_charcoal_and_slate_crafts():
    """Тест крафтов L3: Древесный уголь (х3), Сланцевый слиток, Сланцевая тарелка (х2), Сланцевый пенал."""
    game = GameState()
    game.inventory = {
        "Ветка": 5,
        "Кусок коры": 2,
        "Сланцевая пластина": 2,
        "Глина": 2,
        "Мох": 2,
    }

    # 1. Крафт древесного угля: 5 веток + 2 коры -> 3 угля
    ok, res = do_craft(game, "Древесный уголь")
    assert ok is True
    assert game.inventory.get("Древесный уголь") == 3
    assert game.inventory.get("Ветка", 0) == 0
    assert game.inventory.get("Кусок коры", 0) == 0

    # 2. Крафт сланцевого слитка: 2 пластины + 2 глины -> 1 слиток
    ok, res = do_craft(game, "Сланцевый слиток")
    assert ok is True
    assert game.inventory.get("Сланцевый слиток") == 1
    assert game.inventory.get("Сланцевая пластина", 0) == 0
    assert game.inventory.get("Глина", 0) == 0

    # 3. Крафт сланцевой тарелки: 1 слиток -> 2 тарелки
    ok, res = do_craft(game, "Сланцевая тарелка")
    assert ok is True
    assert game.inventory.get("Сланцевая тарелка") == 2
    assert game.inventory.get("Сланцевый слиток", 0) == 0


@pytest.mark.l3
def test_reusable_slate_plate_cooking_and_eating():
    """Тест многоразовой сланцевой тарелки при готовке и поедании."""
    game = GameState()
    game.campfire_active = True
    game.campfire_durability = 10
    game.inventory = {
        "Сланцевая тарелка": 1,
        "Сырое мясо": 1,
    }
    # При готовке вместо коры используется тарелка
    ok, msg = cook_item(game, "cook_roast_meat")
    assert ok is True
    dish_name = "Мясо на коре (🍽️)"
    assert game.inventory.get(dish_name) == 1
    assert game.inventory.get("Сланцевая тарелка", 0) == 0

    # Поедание блюда с тарелкой возвращает Сланцевую тарелку в инвентарь
    game.hunger = 40
    use_consumable(dish_name, game)
    assert game.inventory.get("Сланцевая тарелка") == 1
    assert game.inventory.get(dish_name, 0) == 0
    assert any("тарелка снова свободна" in log_msg for log_msg in game.log)


@pytest.mark.l2
def test_l2_dam_puzzle_karma():
    """Тест кармы L2: решение за 1 или 2 попытки даёт +2 к наблюдательности."""
    game = GameState()
    game.l2_puzzle_attempt = 1  # 2-я попытка (<= 1 ошибок)
    handle_location_2_ruchey("l2_bridge_activated", game, 101)
    assert game.narrative_karma.get("observation", 0) == 2

    # Если решено за 3 попытки (2 ошибки), дополнительная наблюдательность не даётся
    game2 = GameState()
    game2.l2_puzzle_attempt = 2  # 3-я попытка
    handle_location_2_ruchey("l2_bridge_activated", game2, 102)
    assert game2.narrative_karma.get("observation", 0) == 0


@pytest.mark.l3
def test_l3_research_story_trigger():
    """Тест триггера L3: срабатывает со 2-го дня пребывания на 2-е исследование."""
    game = GameState()
    game.current_location = "Скромная Лощина"
    game.day = 1
    # Первый день на локации — триггер не должен сработать
    ev, log = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev is None

    # Переход на следующий день (день 2 > дня входа 1)
    game.day = 2
    # 1-е исследование дня 2
    ev1, _ = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev1 is None

    # 2-е исследование дня 2 -> запуск сюжета L3!
    ev2, log2 = check_forest_research_story_trigger(game, loc_id=3, torch_equipped=False)
    assert ev2 == "l3_1_fire_low"
    assert game.is_story_flag_set("l3_story_started") is True


@pytest.mark.l3
def test_l3_story_progression_and_stove_unlock():
    """Тест прохождения сюжета L3 от L3.1 до обустройства лагеря."""
    game = GameState()
    game.current_location = "Скромная Лощина"

    # L3.1: обнаружение
    t, kb = handle_location_3_slate_hollow("l3_1_fire_low", game, 101)
    assert "тлеют угли" in t

    # L3.2: зов
    t, kb = handle_location_3_slate_hollow("l3_2_call", game, 101)
    assert "Если пришёл — грейся" in t

    # L3.3: убежище
    t, kb = handle_location_3_slate_hollow("l3_3_inspect", game, 101)
    assert "Крыша течёт справа" in t

    # L3.4: надписи (+1 наблюдательность)
    t, kb = handle_location_3_slate_hollow("l3_4_writings", game, 101)
    assert game.narrative_karma.get("observation", 0) == 1

    # L3.5: обжиг заготовки
    t, kb = handle_location_3_slate_hollow("l3_5_finish_bake", game, 101)
    assert game.inventory.get("Сланцевый слиток") == 1

    # L3.6: остаёмся здесь и финализируем убежище
    t, kb = handle_location_3_slate_hollow("l3_6_finalize", game, 101)
    assert game.is_story_flag_set("l3_shelter_unlocked") is True
    assert game.is_stove is True
    assert game.campfire_active is True
    assert game.campfire_durability >= 15


@pytest.mark.l3
@pytest.mark.persist
def test_stone_tablet_pagination_and_storage():
    """Тест пагинации каменной плиты и сохранения записей."""
    notes = get_tablet_notes()
    assert len(notes) >= 4  # 4 каноничные надписи

    # Проверка текста пагинации
    text, total_pages = format_tablet_notes_text(notes, page=1, page_size=5)
    assert "КАМЕННАЯ ПЛИТА У ПЕЧИ" in text
    assert "Если пришёл — грейся" in text

    # Сохранение новой записи
    ok = save_tablet_note(uid=999, author="Бродяга Тестер", text="Новая метка на плите")
    assert ok is True

    updated_notes = get_tablet_notes()
    assert any(n.get("text") == "Новая метка на плите" for n in updated_notes)


@pytest.mark.l3
def test_slate_armor_hp_defense_and_full_set():
    """Тест параметров сланцевого сета: +50 HP суммарно, 12 брони, распознавание полного сета."""
    game = GameState()
    assert game.max_hp == 100
    assert game.armor_defense == 0
    assert game.is_full_slate_set_equipped() is False

    # Надеваем части сета
    game.equipment["head"] = "Сланцевая маска"
    assert game.max_hp == 108
    assert game.armor_defense == 2
    assert game.is_full_slate_set_equipped() is False

    game.equipment["torso"] = "Сланцевый панцирь"
    assert game.max_hp == 133
    assert game.armor_defense == 7
    assert game.is_full_slate_set_equipped() is False

    game.equipment["pants"] = "Сланцевые поножи"
    assert game.max_hp == 145
    assert game.armor_defense == 10
    assert game.is_full_slate_set_equipped() is False

    game.equipment["boots"] = "Сланцевые ботинки"
    assert game.max_hp == 150
    assert game.armor_defense == 12
    assert game.is_full_slate_set_equipped() is True


@pytest.mark.l3
def test_ridge_without_armor_damage_and_retreat():
    """Тест попытки пройти гребень без сланцевой брони: получение урона и отступление в лагерь."""
    game = GameState()
    game.hp = 100

    # L3.7: отдых у печи перед подъёмом
    text, kb = handle_location_3_slate_hollow("l3_7_morning", game, 101)
    assert "Перед подъёмом" in text

    # L3.8: без сета брони доступны атака (срыв), обход и возврат в лагерь
    text, kb = handle_location_3_slate_hollow("l3_8_ridge", game, 101)
    cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "l3_9a_charge" in cbs
    assert "l3_9b_ridge" in cbs
    assert "back" in cbs
    assert "l3_10_armored" not in cbs

    # Таран секача без брони наносит 30 урона
    handle_location_3_slate_hollow("l3_9a_charge", game, 101)
    assert game.hp == 70

    # Падение с карниза наносит 25 урона
    handle_location_3_slate_hollow("l3_9b_ridge", game, 101)
    assert game.hp == 45

    # Возврат в лагерь открывает крафты сланцевого сета, окованного посоха и локацию Солонец (Секач)
    text, kb = handle_location_3_slate_hollow("l3_9_camp", game, 101)
    assert "Сланцевый панцирь" in game.unlocked_crafts
    assert "Окованный посох" in game.unlocked_crafts
    assert "Солонец (Секач)" in game.unlocked_locations


@pytest.mark.l3
def test_ridge_with_armor_and_peaceful_cache():
    """Тест прохождения гребня в сланцевой броне мирным путём (карниз / схрон) с паритетом лута."""
    game = GameState()
    game.equipment = {
        "head": "Сланцевая маска",
        "torso": "Сланцевый панцирь",
        "pants": "Сланцевые поножи",
        "boots": "Сланцевые ботинки",
    }
    assert game.is_full_slate_set_equipped() is True

    # На гребне в полной броне открывается доступ к прямому столкновению
    text, kb = handle_location_3_slate_hollow("l3_8_ridge", game, 101)
    cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "l3_10_armored" in cbs

    # Экран l3_10_armored
    text, kb = handle_location_3_slate_hollow("l3_10_armored", game, 101)
    cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "l3_11a_start" in cbs
    assert "l3_11b_cliff" in cbs

    # Обход по карнизу в броне -> урон -5 HP, переход в схрон
    hp_before = game.hp
    text, kb = handle_location_3_slate_hollow("l3_11b_cliff", game, 101)
    assert game.is_story_flag_set("boar_bypassed") is True
    assert game.hp == hp_before - 5

    # Схрон l3_12_cache: ещё -5 HP при срыве и одна кнопка взять припасы
    text, kb = handle_location_3_slate_hollow("l3_12_cache", game, 101)
    assert "тайная ниша" in text
    assert [btn.callback_data for row in kb.inline_keyboard for btn in row] == ["l3_12_taken"]
    assert game.hp == hp_before - 10

    # Забираем припасы и оставляем взамен ягоды (l3_12_taken -> l3_13_kind)
    handle_location_3_slate_hollow("l3_12_taken", game, 101)
    game.inventory["Ягоды"] = 2
    text, kb = handle_location_3_slate_hollow("l3_13_kind", game, 101)
    assert game.inventory["Мясо"] == 4
    assert game.inventory["Кожа"] == 2
    assert game.inventory["Кость"] == 2
    assert game.inventory["Ягоды"] == 1  # оставил ягоды взамен
    assert game.is_story_flag_set("l3_ridge_completed") is True
    assert game.narrative_karma.get("compassion", 0) == 2


@pytest.mark.l3
def test_boar_combat_tactics_and_victory_loot(monkeypatch):
    """Тест боевой системы с Секачом: паттерн уворотов (1-нет, 2-да, 3-да, 4-нет, 5-да), крит x2 и добыча."""
    def mock_randint(a, b):
        if (a, b) == (1, 100):
            return 99  # Шанс стана не срабатывает случайно
        return b
    monkeypatch.setattr("random.randint", mock_randint)
    game = GameState()
    game.equipment = {
        "head": "Сланцевая маска",
        "torso": "Сланцевый панцирь",
        "pants": "Сланцевые поножи",
        "boots": "Сланцевые ботинки",
        "hand_right": "Окованный посох",
        "trinket": "Клык волка",
    }
    game.hp = 150

    # Начало боя: Секач 350 HP, Герой 150 HP, статус '⚡ Мчится на таран!'
    text, kb = handle_location_3_slate_hollow("l3_start_boar_battle", game, 101)
    assert game.wolf_battle is not None
    assert game.wolf_battle["wolf_hp"] == 350
    assert game.hp == 150
    assert game.wolf_battle["is_charging"] is True
    assert game.wolf_battle["boar_status"] == "⚡ Мчится на таран!"

    # 1. Первый ход: таран врасплох (-44 HP Герою, -18 HP Секачу) -> статус '💢 В ярости'
    text, kb = handle_location_3_slate_hollow("boar_battle_dodge", game, 101)
    assert game.hp == 106
    assert game.wolf_battle["wolf_hp"] == 332
    assert game.wolf_battle["boar_status"] == "💢 В ярости"

    # 1. Удар, пока он в ярости -> Секач отвечает и переходит в '⏳ Разгоняется'
    text, kb = handle_location_3_slate_hollow("boar_battle_attack", game, 101)
    assert game.wolf_battle["boar_status"] == "⏳ Разгоняется"
    assert game.wolf_battle["is_charging"] is False

    # 2. Удар, пока он разгоняется -> Секач отвечает и переходит в '⚡ Мчится на таран!'
    text, kb = handle_location_3_slate_hollow("boar_battle_attack", game, 101)
    assert game.wolf_battle["boar_status"] == "⚡ Мчится на таран!"
    assert game.wolf_battle["is_charging"] is True

    # 3. Уворот от тарана -> Секач всегда врезается в стену и оглушён
    text, kb = handle_location_3_slate_hollow("boar_battle_dodge", game, 101)
    assert game.wolf_battle["is_stunned"] is True
    assert game.wolf_battle["boar_status"] == "💫 Оглушён (1 ход)"

    # 4. Крит-удар посохом по оглушённому (×2) -> Секач очухался и снова '💢 В ярости'
    hp_boar_before = game.wolf_battle["wolf_hp"]
    text, kb = handle_location_3_slate_hollow("boar_battle_attack", game, 101)
    dmg_done = hp_boar_before - game.wolf_battle["wolf_hp"]
    assert dmg_done >= 20
    assert game.wolf_battle["boar_status"] == "💢 В ярости"

    # 5. Если игрок не увернулся, а атаковал на таране -> Секач сносит тараном
    game.wolf_battle["is_charging"] = True
    hp_before = game.hp
    text, kb = handle_location_3_slate_hollow("boar_battle_attack", game, 101)
    assert game.hp < hp_before
    assert game.wolf_battle["boar_status"] == "💢 В ярости"

    # 7. Победа над Секачом и разделка туши
    handle_location_3_slate_hollow("l3_11a_win", game, 101)
    assert game.is_story_flag_set("boar_killed") is True

    text, kb = handle_location_3_slate_hollow("l3_12a_loot", game, 101)
    assert game.is_story_flag_set("l3_ridge_completed") is True
    assert game.inventory["Мясо"] == 4
    assert game.inventory["Кожа"] == 2
    assert game.inventory["Кость"] == 2


@pytest.mark.l3
def test_l3_honest_damage_and_mortality():
    """Тест честного урона и гибели персонажа (README §1.8) во всех опасных сценах L3."""
    # 1. Смерть от тарана секача без брони (l3_9a_charge, урон 30)
    g1 = GameState()
    g1.hp = 25
    text, kb = handle_location_3_slate_hollow("l3_9a_charge", g1, 101)
    assert g1.hp == 0
    assert "ВЫ ПОГИБЛИ" in text
    assert "Секач" in text

    # 2. Смерть от срыва с узкого хребта (l3_9b_ridge, урон 25)
    g2 = GameState()
    g2.hp = 20
    text, kb = handle_location_3_slate_hollow("l3_9b_ridge", g2, 101)
    assert g2.hp == 0
    assert "ВЫ ПОГИБЛИ" in text
    assert "Срыв с узкой тропы" in text

    # 3. Смерть от сланцевой крошки на обрыве (l3_11b_cliff, урон 5)
    g3 = GameState()
    g3.hp = 5
    text, kb = handle_location_3_slate_hollow("l3_11b_cliff", g3, 101)
    assert g3.hp == 0
    assert "ВЫ ПОГИБЛИ" in text
    assert "Острые сланцевые осколки" in text

    # 4. Смерть от обвала скального уступа (l3_12_cache, урон 5)
    g4 = GameState()
    g4.hp = 4
    text, kb = handle_location_3_slate_hollow("l3_12_cache", g4, 101)
    assert g4.hp == 0
    assert "ВЫ ПОГИБЛИ" in text
    assert "Обвал скального уступа" in text

    # 5. Смерть от внезапного тарана кабана на 0-м ходу боя (урон 44)
    g5 = GameState()
    g5.hp = 30
    handle_location_3_slate_hollow("l3_start_boar_battle", g5, 101)
    text, kb = handle_location_3_slate_hollow("boar_battle_dodge", g5, 101)
    assert g5.hp == 0
    assert "ВЫ ПОГИБЛИ" in text
    assert "Секач насмерть сбил тебя внезапным тараном" in text


@pytest.mark.l3
def test_l3_anti_dupe_and_karma_guards():
    """Тест защиты от дюпов предметов, расхода бутылки воды и абуза кармы."""
    game = GameState()

    # 1. l3_4_writings: карма observation начисляется только 1 раз
    handle_location_3_slate_hollow("l3_4_writings", game, 101)
    assert game.narrative_karma.get("observation", 0) == 1
    handle_location_3_slate_hollow("l3_4_writings", game, 101)
    assert game.narrative_karma.get("observation", 0) == 1

    # 2. l3_5_finish_bake: сланцевый слиток и +2 pragmatism выдаются только 1 раз
    handle_location_3_slate_hollow("l3_5_finish_bake", game, 101)
    assert game.inventory.get("Сланцевый слиток", 0) == 1
    assert game.narrative_karma.get("pragmatism", 0) == 2
    handle_location_3_slate_hollow("l3_5_finish_bake", game, 101)
    assert game.inventory.get("Сланцевый слиток", 0) == 1
    assert game.narrative_karma.get("pragmatism", 0) == 2

    # 3. l3_5_take_clay: расход "Бутылка воды" возвращает "Пустая бутылка"
    game_clay = GameState()
    game_clay.flask_water = 0
    game_clay.inventory = {"Бутылка воды": 1}
    handle_location_3_slate_hollow("l3_5_take_clay", game_clay, 101)
    assert game_clay.inventory.get("Глина", 0) == 1
    assert game_clay.inventory.get("Бутылка воды", 0) == 0
    assert game_clay.inventory.get("Пустая бутылка", 0) == 1
    assert game_clay.narrative_karma.get("compassion", 0) == 1
    # Повторный вызов не дюпает глину и карму
    handle_location_3_slate_hollow("l3_5_take_clay", game_clay, 101)
    assert game_clay.inventory.get("Глина", 0) == 1
    assert game_clay.narrative_karma.get("compassion", 0) == 1

    # 4. l3_6_leave_clay и l3_6_warning однократность кармы
    game_clay.inventory["Глина"] = 5
    handle_location_3_slate_hollow("l3_6_leave_clay", game_clay, 101)
    assert game_clay.inventory.get("Глина", 0) == 4
    assert game_clay.narrative_karma.get("compassion", 0) == 3
    handle_location_3_slate_hollow("l3_6_leave_clay", game_clay, 101)
    assert game_clay.inventory.get("Глина", 0) == 4  # глина не списывается повторно
    assert game_clay.narrative_karma.get("compassion", 0) == 3  # карма не начисляется повторно

    handle_location_3_slate_hollow("l3_6_warning", game_clay, 101)
    assert game_clay.narrative_karma.get("compassion", 0) == 4
    handle_location_3_slate_hollow("l3_6_warning", game_clay, 101)
    assert game_clay.narrative_karma.get("compassion", 0) == 4

    # 5. l3_12a_loot: повторный вызов не дублирует ресурсы
    game_loot = GameState()
    handle_location_3_slate_hollow("l3_12a_loot", game_loot, 101)
    assert game_loot.inventory.get("Мясо") == 4
    assert game_loot.inventory.get("Кожа") == 2
    assert game_loot.inventory.get("Кость") == 2
    handle_location_3_slate_hollow("l3_12a_loot", game_loot, 101)
    assert game_loot.inventory.get("Мясо") == 4
    assert game_loot.inventory.get("Кожа") == 2
    assert game_loot.inventory.get("Кость") == 2

    # 6. l3_12_taken: повторный вызов не дублирует схрон
    game_cache = GameState()
    handle_location_3_slate_hollow("l3_12_taken", game_cache, 101)
    assert game_cache.inventory.get("Мясо") == 4
    assert game_cache.inventory.get("Кожа") == 2
    assert game_cache.inventory.get("Кость") == 2
    handle_location_3_slate_hollow("l3_12_taken", game_cache, 101)
    assert game_cache.inventory.get("Мясо") == 4
    assert game_cache.inventory.get("Кожа") == 2
    assert game_cache.inventory.get("Кость") == 2


@pytest.mark.l3
def test_l3_fsm_stabilization_and_stove_sync():
    """Тест сброса active_story_callback в лагере и синхронизации печи на 30 HP."""
    game = GameState()
    game.campfire_max_durability = 10
    game.campfire_durability = 5

    # 1. Финализация убежища l3_6_finalize
    handle_location_3_slate_hollow("l3_6_finalize", game, 101)
    assert game.is_story_flag_set("l3_shelter_unlocked") is True
    assert game.campfire_max_durability == 30
    assert game.campfire_durability >= 15
    assert game.campfires.get("loc_3", {}).get("max_durability") == 30
    assert game.active_story_callback is None
    assert game.story_state is None

    # 2. Вход в локацию при открытом убежище и завершённом сюжете
    game.set_story_flag("l3_ridge_completed", True)
    handle_location_3_slate_hollow("location_enter_3", game, 101)
    assert game.active_story_callback is None
    assert game.story_state is None
    assert game.current_location == "Скромная лощина"
    assert game.location_index == 2
    assert game.campfire_max_durability == 30
