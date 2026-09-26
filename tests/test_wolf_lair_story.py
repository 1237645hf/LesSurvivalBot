"""
Тесты для сюжетной цепочки L1.5–L1.7 (Волчье логово, битва, пощада/добивание, переход к Ручью).
Проверяют каждый этап (Stage 1..20), контакты/стыки всех кнопок (contacts) и 4 обязательных правила.
"""

import pytest
from game_state import GameState
from crafts import do_craft, CRAFT_RECIPES, handle_craft
from keyboards import get_main_kb, get_locations_kb, get_wolf_battle_kb
from story.location_stories import (
    handle_story,
    handle_l1_wolf_lair,
    check_forest_research_story_trigger,
    is_story_callback,
)
from modules.combat import (
    start_battle,
    apply_action,
    get_battle_text,
    get_wolf_battle_text,
    ENEMIES,
    get_enemy,
)
from main import PARENT_SCREEN, CANONICAL_STACKS


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 1: ТРИГГЕР ИССЛЕДОВАНИЯ В МОДУЛЕ STORY (АЛГОРИТМ НЕ В MAIN.PY)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_01_research_trigger_algorithm_in_story_module():
    """Этап 1: Алгоритм проверки триггера L1.5 живёт в location_stories и активируется на 3-е исследование."""
    game = GameState()
    game.set_story_flag("l1_completed")
    game.story_flags["l1_completed_day"] = 2
    game.day = 5  # Прошло только 3 дня (< 4)

    # Исследование до 4-х дней: не триггерится
    event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert event is None

    # Наступил 6-й день (день 2 + 4 = 6)
    game.day = 6

    # 1-е исследование
    event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert event is None
    assert game.l1_post_research_count == 1

    # 2-е исследование
    event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert event is None
    assert game.l1_post_research_count == 2

    # 3-е исследование: срабатывает триггер l1_5_start
    event, log = check_forest_research_story_trigger(game, loc_id=1, torch_equipped=False)
    assert event == "l1_5_start"
    assert game.is_story_flag_set("l1_5_triggered")


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 2: ОКНО 1 — НАХОДКА ОВРАГА И ПЕЩЕРЫ (l1_5_start)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_02_l1_5_start_screen_and_contact():
    """Этап 2: Экран l1_5_start и контактная кнопка перехода на l1_5_wolf."""
    game = GameState()
    assert is_story_callback("l1_5_start")

    text, kb = handle_story("l1_5_start", game, 101)
    assert "каменистый овраг со входом в неглубокую пещеру" in text
    assert "Только эта расщелина" in text
    assert game.story_state == "l1_5"

    # Проверка контакта: ровно 1 кнопка, ведущая на l1_5_wolf
    assert len(kb.inline_keyboard) == 1
    assert kb.inline_keyboard[0][0].callback_data == "l1_5_wolf"
    assert "Далее" in kb.inline_keyboard[0][0].text


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 3: ОКНО 2 — СТАРЫЙ ВОЛК С ОЖОГОМ (l1_5_wolf)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_03_l1_5_wolf_screen_and_contact():
    """Этап 3: Экран l1_5_wolf с описанием ожога морды и контактная кнопка на l1_5_behind."""
    game = GameState()
    assert is_story_callback("l1_5_wolf")

    text, kb = handle_story("l1_5_wolf", game, 101)
    assert "свежая тёмная корка от ожога твоим факелом на морде" in text
    assert "обломанными клыками" in text

    # Проверка контакта: кнопка на l1_5_behind
    assert kb.inline_keyboard[0][0].callback_data == "l1_5_behind"


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 4: ОКНО 3 — РАСЩЕЛИНА И ШУМ ВОДЫ (l1_5_behind)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_04_l1_5_behind_screen_and_contact():
    """Этап 4: Экран l1_5_behind с намёком на ручей и контактная кнопка на l1_5_thought."""
    game = GameState()
    assert is_story_callback("l1_5_behind")

    text, kb = handle_story("l1_5_behind", game, 101)
    assert "тянет прохладой и влагой, доносится шум далёкой воды" in text

    # Проверка контакта: кнопка на l1_5_thought
    assert kb.inline_keyboard[0][0].callback_data == "l1_5_thought"


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 5: ОКНО 4 — ОСОЗНАНИЕ НЕОБХОДИМОСТИ ОРУЖИЯ (l1_5_thought)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_05_l1_5_thought_screen_and_contact():
    """Этап 5: Экран l1_5_thought (самоубийство с голыми руками) и контакт на l1_5_leave."""
    game = GameState()
    assert is_story_callback("l1_5_thought")

    text, kb = handle_story("l1_5_thought", game, 101)
    assert "С голыми руками на него лезть — самоубийство" in text

    # Проверка контакта: кнопка на l1_5_leave
    assert kb.inline_keyboard[0][0].callback_data == "l1_5_leave"
    assert "Тихо уйти в лагерь" in kb.inline_keyboard[0][0].text


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 6: ОТСТУПЛЕНИЕ В ЛАГЕРЬ И ОТКРЫТИЕ КРАФТА (l1_5_leave)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_06_l1_5_leave_and_camp_return_and_craft_unlock():
    """Этап 6: Отступление в лагерь, открытие крафта посоха и временного меню Волчьего логова."""
    game = GameState()
    assert is_story_callback("l1_5_leave")

    text, kb = handle_story("l1_5_leave", game, 101)
    assert "Крепкий посох" in game.unlocked_crafts
    assert game.locations_unlocked is True
    assert game.wolf_lair_active is True
    assert any("Открыт крафт: 🪵 Крепкий посох" in line for line in game.log)

    # Контакт с главным экраном: возвращает клавиатуру лагеря с кнопкой «Локации»
    assert any(btn.callback_data == "locations_menu" for row in kb.inline_keyboard for btn in row)


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 7: КРАФТ И ЭКИПИРОВКА ПОСОХА (В ПРАВУЮ РУКУ, НЕ СНИМАЯ ФАКЕЛ)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_07_staff_craft_and_dual_wield_torch():
    """Этап 7: Крафт 'Крепкий посох' из 8 веток, надевание в hand_right, факел в hand_left цел."""
    game = GameState()
    assert CRAFT_RECIPES["Крепкий посох"] == [("Ветка", 8)]

    # Крафт
    game.inventory["Ветка"] = 8
    success, msg = do_craft(game, "Крепкий посох")
    assert success is True
    assert game.inventory.get("Ветка", 0) == 0
    assert game.inventory.get("Крепкий посох") == 1

    # Надеваем факел в левую руку
    game.equipment["hand_left"] = "Факел"

    # Надеваем посох в правую руку
    handle_craft("use_item_Крепкий посох", game, 101)
    assert game.equipment.get("hand_right") == "Крепкий посох"
    assert game.equipment.get("hand_left") == "Факел"  # Оба предмета надеты!


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 8: МЕНЮ ЛОКАЦИЙ И ВХОД В ЛОГОВО (БЕЗ ОРУЖИЯ vs С ПОСОХОМ)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_08_wolf_lair_entry_screen_unarmed_vs_armed():
    """Этап 8: Проверка входа в логово: без посоха вход закрыт, с посохом открыт бой."""
    game = GameState()
    game.wolf_lair_active = True

    # 1. Без посоха в руке
    loc_kb = get_locations_kb(game)
    assert "🐾 Волчье логово (Опасно)" in loc_kb.inline_keyboard[0][0].text

    text_unarmed, kb_unarmed = handle_story("wolf_lair_enter", game, 101)
    assert "Без надёжного оружия соваться в логово самоубийственно" in text_unarmed
    assert kb_unarmed.inline_keyboard[0][0].callback_data == "back"

    # 2. С посохом в правой руке
    game.equipment["hand_right"] = "Крепкий посох"
    loc_kb_armed = get_locations_kb(game)
    assert loc_kb_armed.inline_keyboard[0][0].text == "🐾 Волчье логово"

    text_armed, kb_armed = handle_story("wolf_lair_enter", game, 101)
    assert "Сжимая в руке тяжёлый посох" in text_armed
    cb_datas = [btn.callback_data for row in kb_armed.inline_keyboard for btn in row]
    assert "wolf_battle_start" in cb_datas
    assert "back" in cb_datas


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 9: ИНИЦИАЛИЗАЦИЯ БОЯ (wolf_battle_start)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_09_wolf_battle_initialization():
    """Этап 9: Старт боя: инициализация 50 HP волка, боевой клавиатуры и экрана."""
    game = GameState()
    game.equipment["hand_right"] = "Крепкий посох"
    game.hp = 100

    text, kb = handle_story("wolf_battle_start", game, 101)
    assert game.story_state == "wolf_battle"
    assert game.wolf_battle is not None
    assert game.wolf_battle["wolf_hp"] == 50
    assert "ЛОГОВО СТАРОГО ВОЛКА" in text
    assert "100/100 HP" in text
    assert "50/50 HP" in text

    # Контакты боевого меню
    btn_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "wolf_battle_attack" in btn_callbacks
    assert "wolf_battle_defend" in btn_callbacks
    assert "wolf_battle_flee" in btn_callbacks


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 10: РАУНД АТАКИ ПОСОХОМ (wolf_battle_attack)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_10_wolf_battle_attack_round():
    """Этап 10: Атака посохом наносит 4–6 урона (+1 от факела), волк получает урон."""
    game = GameState()
    game.equipment["hand_right"] = "Крепкий посох"
    game.equipment["hand_left"] = "Факел"
    handle_story("wolf_battle_start", game, 101)

    text, kb = handle_story("wolf_battle_attack", game, 101)
    # Игрок нанёс 4-6 базовых + 1 от факела = 5-7 урона
    assert game.wolf_battle["player_dmg_dealt"] in (5, 6, 7)
    assert game.wolf_battle["wolf_hp"] < 50


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 11: РАУНД ЗАЩИТЫ (wolf_battle_defend) И СНИЖЕНИЕ УРОНА НА 50%
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_11_wolf_battle_defend_round_damage_mitigation():
    """Этап 11: Защита снижает входящий урон волка на 50% (2–4 ед. вместо 5–7)."""
    game = GameState()
    game.equipment["hand_right"] = "Крепкий посох"
    game.hp = 100
    handle_story("wolf_battle_start", game, 101)

    initial_hp = game.hp
    text, kb = handle_story("wolf_battle_defend", game, 101)
    dmg = initial_hp - game.hp
    assert dmg in (0, 2, 3, 4)  # 0 при испуге факелом, 2-4 при ударе
    assert "снижено на 50%" in game.wolf_battle["last_log"] or "Ты уходишь в глухую защиту" in game.wolf_battle["last_log"]


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 12: БЕГСТВО ИЗ БОЯ (wolf_battle_flee)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_12_wolf_battle_flee_contact():
    """Этап 12: Бегство из боя безопасно выводит игрока и даёт контактную кнопку в меню локаций."""
    game = GameState()
    game.equipment["hand_right"] = "Крепкий посох"
    handle_story("wolf_battle_start", game, 101)

    text, kb = handle_story("wolf_battle_flee", game, 101)
    assert game.wolf_battle is None
    assert "сломя голову выбегаешь из пещеры" in text
    assert kb.inline_keyboard[0][0].callback_data == "locations_menu"


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 13: ПОБЕДА НАД ВОЛКОМ И РАЗВЕТВЛЕНИЕ (ПИТОМЕЦ vs БЕЗ ПИТОМЦА)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_13_wolf_battle_defeat_transitions():
    """Этап 13: Победа над волком: с котёнком ведёт на мольбу котёнка, без котёнка — на выбор пощады/добивания."""
    # Вариант А: Есть котёнок
    game_pet = GameState()
    game_pet.equipment["pet"] = "Барсик"
    text_pet, kb_pet = handle_story("l1_5_aftermath", game_pet, 101)
    assert kb_pet.inline_keyboard[0][0].callback_data == "l1_5_kitten_plea"

    # Вариант Б: Нет котёнка
    game_no_pet = GameState()
    text_no_pet, kb_no_pet = handle_story("l1_5_aftermath", game_no_pet, 101)
    cb_datas = [btn.callback_data for row in kb_no_pet.inline_keyboard for btn in row]
    assert "l1_5_spare" in cb_datas
    assert "l1_5_kill" in cb_datas


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 14: ПРОСЬБА КОТЁНКА (l1_5_kitten_plea)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_14_l1_5_kitten_plea_screen_and_contacts():
    """Этап 14: Экран просьбы котёнка с контактами на l1_5_spare и l1_5_kill."""
    game = GameState()
    game.equipment["pet"] = "Пушок"

    text, kb = handle_story("l1_5_kitten_plea", game, 101)
    assert "Котёнок замирает, глядя на лежащего волка" in text
    assert "Словно просит не убивать побеждённого" in text

    cb_datas = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "l1_5_spare" in cb_datas
    assert "l1_5_kill" in cb_datas


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 15: ПОЩАДА С ЕДОЙ (СПИСАНИЕ НИЗШЕГО РАНГА)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_15_spare_branch_with_food_consumption():
    """Этап 15: Пощада с едой списывает ровно 1 шт. низшего ранга ⚪ и ведёт в расщелину l1_6_passage."""
    game = GameState()
    game.inventory["Жареное мясо"] = 1   # Ранг 2 (🟢)
    game.inventory["Сырое мясо"] = 1     # Ранг 1 (⚪)

    text, kb = handle_story("l1_5_spare", game, 101)
    assert game.is_story_flag_set("spared_wolf")
    assert "Отдано: Сырое мясо ×1" in text
    assert game.inventory.get("Сырое мясо", 0) == 0
    assert game.inventory.get("Жареное мясо") == 1  # Высший ранг сохранён

    # Контакт на расщелину
    assert kb.inline_keyboard[0][0].callback_data == "l1_6_passage"


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 16: ПОЩАДА БЕЗ ЕДЫ (БЕЗОПАСНЫЙ ФОЛЛБЭК)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_16_spare_branch_without_food_fallback():
    """Этап 16: Пощада без еды не падает с ошибкой, волк отползает, переход на l1_6_passage."""
    game = GameState()
    game.inventory = {"Ветка": 5}

    text, kb = handle_story("l1_5_spare", game, 101)
    assert game.is_story_flag_set("spared_wolf")
    assert "У тебя нет с собой еды, но зверь видит" in text
    assert kb.inline_keyboard[0][0].callback_data == "l1_6_passage"


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 17: ДОБИВАНИЕ ВОЛКА (L1.5b — ТОЧНАЯ КАНОНИЧЕСКАЯ ФРАЗА)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_17_kill_branch_exact_canonical_phrase():
    """Этап 17: Добивание волка выводит точный канонический текст L1.5b и контакт на l1_6_passage."""
    game = GameState()
    text, kb = handle_story("l1_5_kill", game, 101)

    assert text == "Ты покидаешь пещеру с уверенностью, что на тебя этой ночью никто не нападёт."
    assert game.is_story_flag_set("killed_wolf")
    assert kb.inline_keyboard[0][0].callback_data == "l1_6_passage"


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 18: ПРОХОД СКВОЗЬ РАСЩЕЛИНУ (l1_6_passage)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_18_l1_6_fissure_passage():
    """Этап 18: Протискивание сквозь узкую расщелину и контактная кнопка на l1_6_exit."""
    game = GameState()
    text, kb = handle_story("l1_6_passage", game, 101)

    assert "Ты протискиваешься в узкую щель за логовом" in text
    assert kb.inline_keyboard[0][0].callback_data == "l1_6_exit"


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 19: ВЫХОД К ВОДЕ (l1_6_exit)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_19_l1_6_exit_to_stream_water():
    """Этап 19: Выход на свежий речной воздух и контактная кнопка на l1_7_finish."""
    game = GameState()
    text, kb = handle_story("l1_6_exit", game, 101)

    assert "Каменный коридор обрывается, и яркий свет ослепляет тебя" in text
    assert kb.inline_keyboard[0][0].callback_data == "l1_7_finish"


# ══════════════════════════════════════════════════════════════════════════════
# ЭТАП 20: ФИНАЛ L1.7, ЗАКРЫТИЕ ЛОГОВА И ОТКРЫТИЕ РУЧЬЯ (l1_7_finish & inspect)
# ══════════════════════════════════════════════════════════════════════════════

def test_stage_20_l1_7_finish_and_inspect_open_stream():
    """Этап 20: Завершение арки L1.7, логово закрыто навсегда, открыт Ручей."""
    game = GameState()
    game.wolf_lair_active = True

    # 1. Завершаем сюжет
    text_finish, kb_finish = handle_story("l1_7_finish", game, 101)
    assert game.wolf_lair_active is False
    assert game.wolf_lair_defeated is True
    assert "Лесной старт" in game.unlocked_locations
    assert "Ручей" in game.unlocked_locations
    assert kb_finish.inline_keyboard[0][0].callback_data == "l1_7_inspect"

    # Меню локаций теперь содержит только Стартовый лес и Ручей (логова нет)
    loc_kb = get_locations_kb(game)
    cb_datas = [btn.callback_data for row in loc_kb.inline_keyboard for btn in row]
    assert "location_enter_1" in cb_datas
    assert "location_enter_2" in cb_datas
    assert "wolf_lair_enter" not in cb_datas

    # 2. Осмотр нового места (l1_7_inspect) переводит на сюжет Ручья
    text_inspect, kb_inspect = handle_story("l1_7_inspect", game, 101)
    assert game.current_location == "Ручей"
    assert "Ручей бурлит" in text_inspect


# ══════════════════════════════════════════════════════════════════════════════
# ПРОВЕРКА АРХИТЕКТУРНЫХ ПРАВИЛ: MONGODB И СТЕК НАВИГАЦИИ PARENT_SCREEN
# ══════════════════════════════════════════════════════════════════════════════

def test_architectural_rule_1_mongodb_persistence():
    """Правило 1: Состояние боя wolf_battle полностью персистится в MongoDB."""
    game = GameState()
    game.equipment["hand_right"] = "Крепкий посох"
    handle_story("wolf_battle_start", game, 101)
    handle_story("wolf_battle_defend", game, 101)

    doc = game.to_document()
    assert "wolf_battle" in doc
    assert doc["wolf_battle"] is not None

    restored = GameState.from_document(doc)
    assert restored.wolf_battle is not None
    assert restored.wolf_battle["wolf_hp"] == doc["wolf_battle"]["wolf_hp"]
    assert restored.wolf_battle["wolf_dmg_dealt"] == doc["wolf_battle"]["wolf_dmg_dealt"]


def test_architectural_rule_4_canonical_navigation_stack():
    """Правило 4: Стек навигации экрана wolf_lair и wolf_battle каноничен и защищён от циклов."""
    assert PARENT_SCREEN["wolf_lair"] == "locations"
    assert PARENT_SCREEN["locations"] == "main"
    assert CANONICAL_STACKS["wolf_lair"] == ["main", "locations", "wolf_lair"]
    assert PARENT_SCREEN["wolf_battle"] == "wolf_lair"
    assert CANONICAL_STACKS["wolf_battle"] == ["main", "locations", "wolf_lair", "wolf_battle"]
    assert PARENT_SCREEN["combat"] == "wolf_lair"
    assert CANONICAL_STACKS["combat"] == ["main", "locations", "wolf_lair", "combat"]


def test_combat_module_engine_and_enemies():
    """Проверка независимой работы модуля modules.combat."""
    assert "old_wolf" in ENEMIES
    cfg = get_enemy("old_wolf")
    assert cfg["name"] == "Старый волк"
    assert cfg["max_hp"] == 50

    game = GameState()
    game.equipment["hand_right"] = "Крепкий посох"
    game.equipment["hand_left"] = "Факел"

    # 1. start_battle
    text, kb = start_battle(game, "old_wolf")
    assert game.wolf_battle is not None
    assert game.wolf_battle["wolf_hp"] == 50
    assert "ЛОГОВО СТАРОГО ВОЛКА" in text

    # 2. apply_action attack
    text_atk, kb_atk = apply_action("attack", game, "old_wolf")
    assert game.wolf_battle["wolf_hp"] < 50

    # 3. apply_action defend
    text_def, kb_def = apply_action("defend", game, "old_wolf")
    assert any(
        phrase in game.wolf_battle["last_log"]
        for phrase in ("снижено на 50%", "Ты уходишь в глухую защиту", "Волк пугается огня", "закрываешься посохом")
    )

    # 4. apply_action flee
    text_flee, kb_flee = apply_action("flee", game, "old_wolf")
    assert game.wolf_battle is None
    assert "сломя голову выбегаешь" in text_flee

