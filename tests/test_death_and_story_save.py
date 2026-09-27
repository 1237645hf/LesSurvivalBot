"""
test_death_and_story_save.py — Тесты сохранения активного сюжетного окна, честной смерти (без пола 1) и удаления перенапряжения.
"""

import pytest
from game_state import GameState, get_death_text
from game_math import (
    process_damage,
    get_resource_multiplier,
    calculate_ap_by_hp,
)
from keyboards import get_death_kb
from story.location_stories import (
    handle_story,
    handle_location_2_ruchey,
    get_l2_thorn_damage,
)
from modules.combat import start_battle, apply_action


def test_story_callback_persistence():
    """Тест 1: active_story_callback сохраняется в to_document и восстанавливается в from_document."""
    game = GameState()
    assert game.active_story_callback is None

    game.active_story_callback = "l1_5_behind"
    doc = game.to_document()
    assert doc["active_story_callback"] == "l1_5_behind"

    restored = GameState.from_document(doc)
    assert restored.active_story_callback == "l1_5_behind"


def test_story_callback_set_and_clear_lifecycle():
    """Тест 2: При показе сюжетного экрана active_story_callback выставляется, а при выходе в лагерь очищается."""
    game = GameState()
    
    # 1. Показ экрана L1.5
    text, kb = handle_story("l1_5_start", game, 101)
    assert "каменистый овраг" in text
    assert game.active_story_callback == "l1_5_start"

    # 2. Переход к следующему экрану
    text2, kb2 = handle_story("l1_5_wolf", game, 101)
    assert "Из темноты пещеры поднимается волк" in text2
    assert game.active_story_callback == "l1_5_wolf"

    # 3. Выход из сюжета в лагерь
    text_leave, kb_leave = handle_story("l1_5_leave", game, 101)
    assert "Ты вернулся в лагерь" in text_leave or "❤️" in text_leave
    assert game.active_story_callback is None


def test_story_callback_resumes_exact_screen():
    """Тест 3: Восстановление сюжетного экрана через handle_story по active_story_callback."""
    game = GameState()
    game.active_story_callback = "l1_5_thought"

    # Вызываем handle_story с сохранённым коллбэком
    text, kb = handle_story(game.active_story_callback, game, 101)
    assert "С голыми руками на него лезть" in text
    assert any(b.callback_data == "l1_5_leave" for row in kb.inline_keyboard for b in row)


def test_process_damage_honest_death_and_no_overexertion():
    """Тест 4: process_damage списывает урон честно до 0, не держит пол 1 и не конвертирует урон в ресурсы."""
    game = GameState()
    game.hp = 15
    game.hunger = 80
    game.thirst = 90

    # Наносим смертельный урон 20 при HP=15
    new_hp, log_msg = process_damage(game, 20)
    assert new_hp == 0
    assert game.hp == 0
    assert "Здоровье упало до 0" in log_msg
    # Ресурсы не тронуты! Перенапряжение вырезано
    assert game.hunger == 80
    assert game.thirst == 90


def test_resource_multipliers_and_ap_by_hp_remain():
    """Тест 5: Множители ресурсов и расчет AP от HP работают по канону."""
    game = GameState()

    # HP 100: множители 1.0, AP 5
    game.hp = 100
    assert get_resource_multiplier(game, "hunger") == 1.0
    assert get_resource_multiplier(game, "thirst") == 1.0
    assert calculate_ap_by_hp(game) == 5

    # HP 35: множители 1.15 / 1.5, AP 3
    game.hp = 35
    assert get_resource_multiplier(game, "hunger") == 1.15
    assert get_resource_multiplier(game, "thirst") == 1.5
    assert calculate_ap_by_hp(game) == 3

    # HP 10: множители 1.3 / 2.0, AP 2
    game.hp = 10
    assert get_resource_multiplier(game, "hunger") == 1.3
    assert get_resource_multiplier(game, "thirst") == 2.0
    assert calculate_ap_by_hp(game) == 2


def test_combat_wolf_fatal_blow():
    """Тест 6: Удар волка при низком HP честно опускает здоровье до 0 и выдаёт экран гибели."""
    game = GameState()
    game.hp = 2
    game.equipment["hand_right"] = "Крепкий посох"
    start_battle(game, "old_wolf")

    # Волк наносит минимум 5 урона при атаке игрока
    text, kb = apply_action("attack", game, "old_wolf")
    assert game.hp == 0
    assert game.wolf_battle is None
    assert "Ты погиб" in text
    assert kb.inline_keyboard[0][0].callback_data == "start_new_game_confirmed"


def test_thorns_gate_blocks_deadly_entry():
    """Тест 7: Ворота терновника блокируют прорыв при недостаточном HP."""
    game = GameState()
    game.hp = 20  # Меньше минимального урона шипов (26 при 4/4 защите)
    game.equipment = {
        "head": "Сланцевая маска",
        "torso": "Сланцевый панцирь",
        "pants": "Сланцевые поножи",
        "boots": "Сланцевые ботинки",
    }
    dmg = get_l2_thorn_damage(4)
    assert dmg == 26
    assert game.hp <= dmg

    text, kb = handle_location_2_ruchey("location_enter_2", game, 101)
    btn_cbs = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "l2_thorns_break" not in btn_cbs
    assert "Попытка проломиться сейчас будет смертельной" in text


def test_death_text_and_kb_format():
    """Тест 8: Форматирование текста смерти и клавиатуры рестарта."""
    game = GameState()
    game.character_name = "Следопыт"
    game.day = 7
    death_text = get_death_text(game, "🐺 Волк оказался быстрее.")
    assert "💀 **Ты погиб.**" in death_text
    assert "🐺 Волк оказался быстрее." in death_text
    assert "Выживание Следопыт подошло к концу на 7-й день." in death_text

    kb = get_death_kb()
    assert kb.inline_keyboard[0][0].text == "🔄 Начать заново"
    assert kb.inline_keyboard[0][0].callback_data == "start_new_game_confirmed"
