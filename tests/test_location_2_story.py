"""
tests/test_location_2_story.py — Комплексное тестирование механик и сюжета Локации 2 («Ручей»).
Проверяет:
1. Сланцевый крафт и экипировку 4 предметов брони.
2. Отображение защиты в карточке персонажа (/character).
3. Прорыв сквозь терновник, расчет урона (26/51/76/101 HP) и защиту от смерти.
4. Разрушение маски и трансформацию ботинок в отремонтированные.
5. Здание водосброса, взрыв шкафа и реакцию котёнка.
6. Установку коробочки (перчатка против удара током голыми руками с защитой от смерти).
7. Терминал плотины: банк 10 заходов (30 задач), отсутствие подсказок на кнопках,
   штраф при ошибке (−5 HP, 0 AP, сдвиг попытки (attempt + 1) % 10).
8. Активацию моста, удаление записки, открытие Скромной Лощины и возврат на локацию.
"""

import pytest
from game_state import GameState
from story.location_stories import (
    handle_location_2_ruchey,
    get_l2_slate_armor_count,
    get_l2_thorn_damage,
    L2_PUZZLE_BANK,
)
from crafts import can_craft, do_craft, handle_craft
from keyboards import get_item_card_actions_kb, get_locations_kb


def test_slate_craft_recipes_and_flexible_ingredients():
    """Тест 1: Рецепты сланцевой брони и гибкое списание ингредиентов (кора/мох/ветки)."""
    game = GameState()
    game.inventory = {
        "Сланцевая пластина": 20,
        "Кусок коры": 20,
        "Мох": 20,
        "Ветка": 10,
    }
    game.unlocked_crafts = ["Сланцевая маска", "Сланцевый панцирь", "Сланцевые поножи", "Сланцевые ботинки"]

    # Крафт маски: 2 пластины, 2 коры, 2 мха
    ok_mask, _ = do_craft(game, "Сланцевая маска")
    assert ok_mask is True
    assert game.inventory.get("Сланцевая маска") == 1
    assert game.inventory["Сланцевая пластина"] == 18
    assert game.inventory["Кусок коры"] == 18
    assert game.inventory["Мох"] == 18

    # Крафт ботинок: 2 пластины, 3 мха, 2 коры
    ok_boots, _ = do_craft(game, "Сланцевые ботинки")
    assert ok_boots is True
    assert game.inventory.get("Сланцевые ботинки") == 1
    assert game.inventory["Сланцевая пластина"] == 16

    # Крафт поножей: 6 пластин, 3 коры, 4 мха
    ok_legs, _ = do_craft(game, "Сланцевые поножи")
    assert ok_legs is True
    assert game.inventory.get("Сланцевые поножи") == 1
    assert game.inventory["Сланцевая пластина"] == 10

    # Крафт панциря: 8 пластин, 5 коры, 4 мха, 4 ветки
    ok_body, _ = do_craft(game, "Сланцевый панцирь")
    assert ok_body is True
    assert game.inventory.get("Сланцевый панцирь") == 1
    assert game.inventory["Сланцевая пластина"] == 2


def test_slate_armor_equipping_and_character_card():
    """Тест 2: Экипировка всех 4 сланцевых предметов и вывод • 🛡 Защита от шипов: X/4."""
    game = GameState()
    game.inventory = {
        "Сланцевая маска": 1,
        "Сланцевый панцирь": 1,
        "Сланцевые поножи": 1,
        "Сланцевые ботинки": 1,
    }

    # Исходно 0/4
    assert get_l2_slate_armor_count(game) == 0

    # Надеваем маску
    handle_craft("use_item_Сланцевая маска", game, 101)
    assert game.equipment["head"] == "Сланцевая маска"
    assert get_l2_slate_armor_count(game) == 1
    assert "• 🛡 Защита от шипов: 1/4" in game.get_character_text()

    # Надеваем панцирь
    handle_craft("use_item_Сланцевый панцирь", game, 101)
    assert game.equipment["torso"] == "Сланцевый панцирь"
    assert get_l2_slate_armor_count(game) == 2
    assert "• 🛡 Защита от шипов: 2/4" in game.get_character_text()

    # Надеваем поножи
    handle_craft("use_item_Сланцевые поножи", game, 101)
    assert game.equipment["pants"] == "Сланцевые поножи"
    assert get_l2_slate_armor_count(game) == 3
    assert "• 🛡 Защита от шипов: 3/4" in game.get_character_text()

    # Надеваем ботинки
    handle_craft("use_item_Сланцевые ботинки", game, 101)
    assert game.equipment["boots"] == "Сланцевые ботинки"
    assert get_l2_slate_armor_count(game) == 4
    assert "• 🛡 Защита от шипов: 4/4" in game.get_character_text()


def test_thorn_damage_calculation_and_death_prevention():
    """Тест 3: Формула урона терновника и скрытие кнопки пролома при недостаточном HP."""
    game = GameState()

    # 0 предметов: урон 101
    assert get_l2_thorn_damage(0) == 101
    assert get_l2_thorn_damage(1) == 101
    assert get_l2_thorn_damage(2) == 76
    assert get_l2_thorn_damage(3) == 51
    assert get_l2_thorn_damage(4) == 26

    # При HP=100 и уроне 101 (0 защиты) кнопка Проломиться недоступна
    game.hp = 100
    text, kb = handle_location_2_ruchey("location_enter_2", game, 101)
    btn_texts = [b.text for row in kb.inline_keyboard for b in row]
    assert "🪨 Проломиться" not in btn_texts
    assert "⛔ Попытка проломиться сейчас будет смертельной!" in text

    # Надеваем полный комплект (4/4 -> урон 26)
    game.equipment = {
        "head": "Сланцевая маска",
        "torso": "Сланцевый панцирь",
        "pants": "Сланцевые поножи",
        "boots": "Сланцевые ботинки",
    }
    game.hp = 50
    text, kb = handle_location_2_ruchey("l2_thorns_approach", game, 101)
    btn_texts = [b.text for row in kb.inline_keyboard for b in row]
    assert "🪨 Проломиться" in btn_texts

    # Если HP упало до 20 (а урон 26), кнопка снова исчезает (защита от смерти)
    game.hp = 20
    text, kb = handle_location_2_ruchey("l2_thorns_approach", game, 101)
    btn_texts = [b.text for row in kb.inline_keyboard for b in row]
    assert "🪨 Проломиться" not in btn_texts


def test_thorn_breakthrough_gear_wear_and_trampled_path():
    """Тест 4: При прорыве маска ломается в прах, а ботинки становятся отремонтированными."""
    game = GameState()
    game.hp = 100
    game.equipment = {
        "head": "Сланцевая маска",
        "torso": "Сланцевый панцирь",
        "pants": "Сланцевые поножи",
        "boots": "Сланцевые ботинки",
    }

    text, kb = handle_location_2_ruchey("l2_thorns_break", game, 101)

    # Урон 26 при 4/4
    assert game.hp == 74
    # Маска сломалась
    assert game.equipment.get("head") in ("Пусто", None)
    # Панцирь и поножи целы
    assert game.equipment.get("torso") == "Сланцевый панцирь"
    assert game.equipment.get("pants") == "Сланцевые поножи"
    # Ботинки потеряли накладки и стали Отремонтированными
    assert game.equipment.get("boots") == "Отремонтированные ботинки"

    # Флаг пролома установлен
    assert game.is_story_flag_set("l2_thorns_cleared") is True
    assert "тропинка свободна" in text
    assert kb.inline_keyboard[0][0].callback_data == "l2_dam_entrance"


def test_dam_entrance_panel_explosion_and_kitten_reaction():
    """Тест 5: Вход в здание водосброса, взрыв шкафа и царапина испуганного котёнка."""
    game = GameState()
    game.hp = 50
    game.equipment["pet"] = "Котёнок"
    game.story_flags["has_pet"] = True
    game.inventory["Плоская металлическая коробочка"] = 1

    # Вход
    text_dam, kb_dam = handle_location_2_ruchey("l2_dam_entrance", game, 101)
    assert "«Откуда здесь ток?.. Наверное, я этого не узнаю никогда...»" in text_dam
    assert kb_dam.inline_keyboard[0][0].callback_data == "l2_panel_inspect"

    # Взрыв щитка
    text_blow, kb_blow = handle_location_2_ruchey("l2_panel_inspect", game, 101)
    assert "БА-БАХ!" in text_blow
    # Котёнок оцарапал (-2 HP)
    assert game.hp == 48
    assert "Плоская металлическая коробочка" in text_blow
    assert kb_blow.inline_keyboard[0][0].callback_data == "l2_fusebox_inspect"


def test_fusebox_insertion_safe_vs_shock():
    """Тест 6: Установка коробочки через перчатку котёнка или голыми руками (-10 HP)."""
    # Вариант А: С котёнком есть диэлектрическая перчатка
    game_safe = GameState()
    game_safe.hp = 50
    game_safe.equipment["pet"] = "Котёнок"
    game_safe.story_flags["has_pet"] = True
    game_safe.inventory["Плоская металлическая коробочка"] = 1

    text_fb, kb_fb = handle_location_2_ruchey("l2_fusebox_inspect", game_safe, 101)
    cb_fb = [b.callback_data for row in kb_fb.inline_keyboard for b in row]
    assert "l2_fuse_safe" in cb_fb
    assert "l2_fuse_shock" in cb_fb

    # Вставка через перчатку
    text_res, kb_res = handle_location_2_ruchey("l2_fuse_safe", game_safe, 101)
    assert game_safe.hp == 50  # Без урона
    assert "Плоская металлическая коробочка" not in game_safe.inventory  # Списана навсегда
    assert game_safe.is_story_flag_set("l2_fuse_inserted") is True
    assert kb_res.inline_keyboard[0][0].callback_data == "l2_puzzle_start"

    # Вариант Б: Без котёнка (или выбор голыми руками) -> удар током (−10 HP) с защитой от смерти
    game_shock = GameState()
    game_shock.hp = 8  # Меньше 10
    game_shock.inventory["Плоская металлическая коробочка"] = 1

    text_shock, kb_shock = handle_location_2_ruchey("l2_fuse_shock", game_shock, 101)
    # Защита от смерти: HP не упало ниже 1
    assert game_shock.hp == 1
    assert "Плоская металлическая коробочка" not in game_shock.inventory
    assert game_shock.is_story_flag_set("l2_fuse_inserted") is True


def test_puzzle_bank_integrity_and_no_hints_in_buttons():
    """Тест 7: Банк загадок содержит 10 заходов по 3 вопроса, и на кнопках НЕТ подсказок."""
    assert len(L2_PUZZLE_BANK) == 10
    for attempt_idx, attempt_questions in enumerate(L2_PUZZLE_BANK):
        assert len(attempt_questions) == 3, f"В заходе {attempt_idx} должно быть ровно 3 вопроса."
        for q_idx, q in enumerate(attempt_questions):
            assert "num_str" in q
            assert "text" in q
            assert "options" in q
            assert len(q["options"]) >= 2
            # Проверка отсутствия слова "верно" в тексте кнопок
            for opt_text, is_corr in q["options"]:
                assert "верно" not in opt_text.lower(), f"Текст кнопки '{opt_text}' не должен содержать подсказок!"


def test_puzzle_error_penalty_and_attempt_cycling():
    """Тест 8: При ошибке — струя воды, -5 HP, AP=0, и номер захода сдвигается на (attempt+1)%10."""
    game = GameState()
    game.hp = 40
    game.ap = 4
    game.l2_puzzle_attempt = 2
    game.l2_puzzle_step = 2

    # Находим неверный ответ для захода 2, вопроса 2
    q_data = L2_PUZZLE_BANK[2][1]
    wrong_idx = [i for i, (txt, corr) in enumerate(q_data["options"]) if not corr][0]

    text_err, kb_err = handle_location_2_ruchey(f"l2_p_ans:2:2:{wrong_idx}", game, 101)

    assert game.hp == 35  # -5 HP
    assert game.ap == 0  # Выбило AP до 0
    assert game.l2_puzzle_attempt == 3  # Сдвиг на следующий заход
    assert game.l2_puzzle_step == 1  # Сброс шага
    assert "⚠️ ОШИБКА АВТОМАТИКИ!" in text_err
    assert "Ледяная струя" in text_err
    assert kb_err.inline_keyboard[0][0].callback_data == "back"


def test_puzzle_success_bridge_activation_and_note_removal():
    """Тест 9: Три верных ответа подряд опускают мост, удаляют записку и открывают Скромную Лощину."""
    game = GameState()
    game.inventory["Записка с наброском местности"] = 1
    game.l2_puzzle_attempt = 0
    game.l2_puzzle_step = 1

    # Шаг 1: верный ответ
    correct_idx_1 = [i for i, (txt, corr) in enumerate(L2_PUZZLE_BANK[0][0]["options"]) if corr][0]
    handle_location_2_ruchey(f"l2_p_ans:0:1:{correct_idx_1}", game, 101)
    assert game.l2_puzzle_step == 2

    # Шаг 2: верный ответ
    correct_idx_2 = [i for i, (txt, corr) in enumerate(L2_PUZZLE_BANK[0][1]["options"]) if corr][0]
    handle_location_2_ruchey(f"l2_p_ans:0:2:{correct_idx_2}", game, 101)
    assert game.l2_puzzle_step == 3

    # Шаг 3: верный ответ -> финал переправы
    correct_idx_3 = [i for i, (txt, corr) in enumerate(L2_PUZZLE_BANK[0][2]["options"]) if corr][0]
    text_bridge, kb_bridge = handle_location_2_ruchey(f"l2_p_ans:0:3:{correct_idx_3}", game, 101)

    assert "Записка с наброском местности" not in game.inventory
    assert "Скромная Лощина" in game.unlocked_locations
    assert game.is_story_flag_set("l2_completed") is True
    assert kb_bridge.inline_keyboard[0][0].callback_data == "location_enter_3"
    assert kb_bridge.inline_keyboard[0][0].text == "⛰️ Шагнуть в Скромную Лощину"


def test_return_to_location_2_after_completion():
    """Тест 10: Повторный вход на Ручей после завершения сюжета показывает опущенный мост."""
    game = GameState()
    game.set_story_flag("l2_completed", True)
    game.unlocked_locations = ["Лесной старт", "Ручей", "Скромная Лощина"]

    text, kb = handle_location_2_ruchey("location_enter_2", game, 101)
    assert "Массивный мост надёжно опущен" in text
    cb_datas = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "location_enter_3" in cb_datas
    assert "location_enter_1" in cb_datas
