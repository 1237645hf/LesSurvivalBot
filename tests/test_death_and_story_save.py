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


def test_l2_mid_screen_resume():
    """Тест 9: Промежуточный экран L2 сохраняет active_story_callback, а выход очищает его."""
    game = GameState()
    game.hp = 100
    text, kb = handle_story("l2_dam_entrance", game, 101)
    assert text is not None
    assert game.active_story_callback == "l2_dam_entrance"

    # Восстановление того же экрана
    res_text, res_kb = handle_story(game.active_story_callback, game, 101)
    assert res_text == text

    # Выход в лагерь очищает active_story_callback
    out_text, out_kb = handle_story("ruchey_leave", game, 101)
    assert game.active_story_callback is None


def test_l3_to_l7_active_story_callback_lifecycle():
    """Тест 10: Локации L3-L7 корректно устанавливают и сбрасывают active_story_callback."""
    game = GameState()
    game.hp = 100

    # L3: Скромная Лощина по умолчанию возвращает main_kb -> callback сброшен
    handle_story("slate_hollow_start", game, 101)
    assert game.active_story_callback is None

    # L7: Вершина Святилища
    # Штатный конец (sanctuary_resolve) завершает арку и сбрасывает callback
    text7, kb7 = handle_story("sanctuary_resolve", game, 101)
    assert game.active_story_callback is None
    assert game.story_state == "completed"

    # Эмуляция сюжетного экрана с кнопками выбора в L3:
    # если kb != get_main_kb(game), active_story_callback фиксирует data экрана
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from keyboards import get_main_kb
    from unittest.mock import patch

    real_main_kb = get_main_kb(game)
    story_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Осмотреть", callback_data="slate_examine")]])
    with patch("story.location_stories.get_main_kb", side_effect=[story_kb, real_main_kb]):
        text3, kb3 = handle_story("slate_hollow_start", game, 101)
        assert game.active_story_callback == "slate_hollow_start"


def test_kitten_naming_resume_no_duplicate_karma():
    """Тест 11: pet_take выставляет waiting_pet_name, а continue/повтор не дублирует карму."""
    game = GameState()
    game.narrative_karma["compassion"] = 0
    assert not game.is_story_flag_set("saved_kitten")

    # 1. Первый показ экрана котёнка (pet_take)
    text, kb = handle_story("pet_take", game, 101)
    assert game.story_state == "WAITING_FOR_PET_NAME"
    assert game.active_story_callback == "waiting_pet_name"
    assert game.narrative_karma.get("compassion", 0) == 2
    assert game.is_story_flag_set("saved_kitten")
    assert "Как ты его назовёшь?" in text
    assert kb is None

    # 2. Симуляция continue / рендера экрана по сохранённому callback "waiting_pet_name"
    text2, kb2 = handle_story("waiting_pet_name", game, 101)
    assert "Как ты его назовёшь?" in text2
    assert kb2 is None
    assert game.active_story_callback == "waiting_pet_name"
    # Карма не должна увеличиться второй раз!
    assert game.narrative_karma.get("compassion", 0) == 2


@pytest.mark.anyio
async def test_kitten_naming_submit_and_idempotency():
    """Тест 13: Ввод имени очищает callback и state, а повторный вход при наличии питомца уходит в main."""
    from services.dialogs import handle_waiting_for_pet_name
    from unittest.mock import AsyncMock, MagicMock
    from keyboards import get_main_kb

    game = GameState()
    game.story_state = "WAITING_FOR_PET_NAME"
    game.active_story_callback = "waiting_pet_name"
    game.set_story_flag("saved_kitten")
    game.set_story_flag("has_pet")

    fake_msg = MagicMock()
    fake_msg.message_id = 999

    bot_ctx = {
        "last_active_msg_id": {},
        "safe_delete_message": AsyncMock(),
        "safe_edit_message": AsyncMock(),
        "update_or_send_message": AsyncMock(),
        "format_game_text": lambda t, g: t,
    }

    # 1. Ввод валидного имени котёнка
    handled = await handle_waiting_for_pet_name(
        uid=101,
        chat_id=101,
        text="Барсик",
        message=fake_msg,
        game=game,
        bot_ctx=bot_ctx,
    )
    assert handled is True
    assert game.companion_name == "Барсик"
    assert game.equipment.get("pet") == "Барсик"
    assert game.story_state is None
    assert game.active_story_callback is None

    # 2. Повторная попытка pet_take / resume при уже существующем питомце с именем
    text_repeat, kb_repeat = handle_story("pet_take", game, 101)
    assert kb_repeat == get_main_kb(game)
    assert game.companion_name == "Барсик"
    assert game.active_story_callback is None
    assert game.story_state is None

    # 3. Повторный вызов waiting_pet_name при уже существующем питомце
    text_resume, kb_resume = handle_story("waiting_pet_name", game, 101)
    assert kb_resume == get_main_kb(game)
    assert game.companion_name == "Барсик"
    assert game.active_story_callback is None


def test_wolf_battle_screen_no_restart_after_defeat():
    """Тест 12: wolf_battle_screen не перезапускает бой, если волк уже повержен."""
    game = GameState()
    game.hp = 80
    game.set_story_flag("wolf_lair_defeated")
    game.wolf_battle = None

    # Вызываем wolf_battle_screen после завершения боя
    text, kb = handle_story("wolf_battle_screen", game, 101)
    # Бой не должен перезапуститься
    assert game.wolf_battle is None
    # Должен перенаправить на l1_5_aftermath
    assert "Тяжёлый удар посоха окончательно сбивает старого волка" in text

