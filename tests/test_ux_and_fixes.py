import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from game_state import GameState
from services.dialogs import handle_waiting_for_pet_name
from modules.traps import process_trap_rollover, place_trap, roll_trap_roll
from main import process_callback, games, last_request_time, get_user_lock


@pytest.mark.anyio
async def test_pet_name_validation():
    """Тест валидации клички питомца (regex, длина, эмодзи, переносы строк)."""
    uid = 88801
    chat_id = 88801

    game = GameState()
    game.story_state = "WAITING_FOR_PET_NAME"
    games[uid] = game

    mock_msg = AsyncMock()
    mock_msg.message_id = 123
    mock_edit = AsyncMock()
    mock_send = AsyncMock()

    bot_ctx = {
        "last_active_msg_id": {uid: 100},
        "safe_delete_message": AsyncMock(),
        "safe_edit_message": mock_edit,
        "update_or_send_message": mock_send,
        "format_game_text": lambda text, g: text,
    }

    # 1. Пустая строка
    mock_edit.reset_mock()
    res = await handle_waiting_for_pet_name(uid, chat_id, "", mock_msg, game, bot_ctx)
    assert res is True
    assert game.story_state == "WAITING_FOR_PET_NAME"
    assert "не может быть пустой" in mock_edit.call_args[0][2]

    # 2. Перенос строки
    mock_edit.reset_mock()
    res = await handle_waiting_for_pet_name(uid, chat_id, "Котик\nВторой", mock_msg, game, bot_ctx)
    assert res is True
    assert game.story_state == "WAITING_FOR_PET_NAME"
    assert "Переносы строк запрещены" in mock_edit.call_args[0][2]

    # 3. Пробелы
    mock_edit.reset_mock()
    res = await handle_waiting_for_pet_name(uid, chat_id, "Рыжий Кот", mock_msg, game, bot_ctx)
    assert res is True
    assert game.story_state == "WAITING_FOR_PET_NAME"
    assert "Пробелы запрещены" in mock_edit.call_args[0][2]

    # 4. Эмодзи
    mock_edit.reset_mock()
    res = await handle_waiting_for_pet_name(uid, chat_id, "Барсик🐱", mock_msg, game, bot_ctx)
    assert res is True
    assert game.story_state == "WAITING_FOR_PET_NAME"
    assert "Эмодзи" in mock_edit.call_args[0][2]

    # 5. Длина > 20 символов
    mock_edit.reset_mock()
    long_name = "ОченьДлиннаяКличкаДляПитомцаБольше20"
    res = await handle_waiting_for_pet_name(uid, chat_id, long_name, mock_msg, game, bot_ctx)
    assert res is True
    assert game.story_state == "WAITING_FOR_PET_NAME"
    assert "Слишком длинная" in mock_edit.call_args[0][2]

    # 6. Спецсимволы
    mock_edit.reset_mock()
    res = await handle_waiting_for_pet_name(uid, chat_id, "Кот@#$!", mock_msg, game, bot_ctx)
    assert res is True
    assert game.story_state == "WAITING_FOR_PET_NAME"
    assert "Разрешены только буквы" in mock_edit.call_args[0][2]

    # 7. Корректное имя
    mock_edit.reset_mock()
    res = await handle_waiting_for_pet_name(uid, chat_id, "Рыжик_1", mock_msg, game, bot_ctx)
    assert res is True
    assert game.story_state is None
    assert game.companion_name == "Рыжик_1"
    assert game.equipment.get("pet") == "Рыжик_1"
    assert game.is_story_flag_set("has_pet") is True
    assert game.is_story_flag_set("saved_kitten") is True


def test_traps_probabilities_and_empty_reporting():
    """Тест соотношения 40% пуста / 20% ломается / 40% добыча и события empty."""
    import random
    game = GameState()
    game.story_flags["traps_unlocked"] = True
    place_trap(game, 1)

    # 1. 40% (roll 1..40) -> пуста
    orig_randint = random.randint
    try:
        random.randint = lambda a, b: 30
        res = roll_trap_roll(game, 1)
        assert res["is_broken"] is False
        assert res["pending_animal"] is None

        events = process_trap_rollover(game)
        assert len(events) == 1
        assert events[0]["empty"] is True
        assert events[0]["broken"] is False
        assert events[0]["animal"] is None

        # 2. 20% (roll 41..60) -> ломается
        game.traps[1]["is_active"] = True
        game.traps[1]["is_broken"] = False
        random.randint = lambda a, b: 50
        events = process_trap_rollover(game)
        assert len(events) == 1
        assert events[0]["broken"] is True
        assert events[0]["empty"] is False

        # 3. 40% (roll 61..100) -> добыча
        game.traps[1]["is_active"] = True
        game.traps[1]["is_broken"] = False
        random.randint = lambda a, b: 80
        events = process_trap_rollover(game)
        assert len(events) == 1
        assert events[0]["broken"] is False
        assert events[0]["empty"] is False
        assert events[0]["animal"] == "Заяц"
        assert events[0]["loot"] == {"Сырое мясо": 1}
    finally:
        random.randint = orig_randint


@pytest.mark.anyio
async def test_race_condition_double_tap_prevention():
    """Тест защиты от Race Condition при двойном клике через per-user asyncio.Lock."""
    uid = 999123
    chat_id = 999123

    game = GameState()
    game.is_name_set = True
    game.character_name = "Герой"
    game.ap = 5
    game.inventory.clear()
    game.inventory["Вода"] = 5
    games[uid] = game
    last_request_time[uid] = 0

    executed_count = 0

    # Создаём два mock callback с действием питья (action_3)
    def make_query():
        q = AsyncMock()
        q.from_user.id = uid
        q.message.chat.id = chat_id
        q.data = "action_3"
        return q

    q1 = make_query()
    q2 = make_query()

    with patch("main.update_or_send_message", new_callable=AsyncMock), \
         patch("main.save_game"):
        # Запускаем два одновременных вызова
        await asyncio.gather(
            process_callback(q1),
            process_callback(q2),
        )

    # Должен сработать только ОДИН запрос: выпито ровно 1 раз, потрачено 1 порция воды
    assert game.inventory["Вода"] == 4
