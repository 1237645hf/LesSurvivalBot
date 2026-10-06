import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram import types

from game_state import GameState
from keyboards import get_locations_kb, get_trap_buttons_kb
import main


def test_canonical_location_names():
    """Проверка, что меню локаций и ловушек выводит все 7 канонических названий."""
    game = GameState()
    # Открываем все локации
    game.unlocked_locations = [
        "Стартовый лес", "Ручей со змеями", "Скромная лощина",
        "Просека охотников", "Яр слизней", "Мохнатая пещера", "Святилище",
    ]

    loc_kb = get_locations_kb(game)
    texts = [btn.text for row in loc_kb.inline_keyboard for btn in row]
    cbs = [btn.callback_data for row in loc_kb.inline_keyboard for btn in row]

    expected = [
        "1. 🌲 Стартовый лес",
        "2. 🏞️ Ручей со змеями",
        "3. ⛰️ Скромная лощина",
        "4. 🏹 Просека охотников",
        "5. 🐌 Яр слизней",
        "6. 🦇 Мохнатая пещера",
        "7. 🏛️ Святилище",
        "↩️ Назад",
    ]
    assert texts == expected
    assert "location_enter_1" in cbs
    assert "location_enter_2" in cbs
    assert "location_enter_3" in cbs
    assert "location_enter_4" in cbs
    assert "location_enter_5" in cbs
    assert "location_enter_6" in cbs
    assert "location_enter_7" in cbs

    # Проверка ловушек
    trap_kb = get_trap_buttons_kb(game)
    trap_texts = [btn.text for row in trap_kb.inline_keyboard for btn in row]
    assert any("Стартовый лес" in t for t in trap_texts)
    assert any("Ручей со змеями" in t for t in trap_texts)
    assert any("Скромная лощина" in t for t in trap_texts)
    assert any("Просека охотников" in t for t in trap_texts)
    assert any("Яр слизней" in t for t in trap_texts)
    assert any("Мохнатая пещера" in t for t in trap_texts)
    assert any("Святилище" in t for t in trap_texts)


def test_is_in_active_story_detection():
    """Функция is_in_active_story корректно определяет нахождение игрока в сюжете или бою."""
    game = GameState()
    assert not main.is_in_active_story(game)

    # В активном сюжетном экране
    game.active_story_callback = "l4_1_entry"
    assert main.is_in_active_story(game)

    # При смерти сюжет не считается активным
    game.hp = 0
    assert not main.is_in_active_story(game)

    # В ожидании имени питомца
    game.hp = 100
    game.active_story_callback = None
    game.story_state = "WAITING_FOR_PET_NAME"
    assert main.is_in_active_story(game)

    # В бою с волком
    game.story_state = "wolf_battle"
    assert main.is_in_active_story(game)


@pytest.mark.anyio
async def test_commands_blocked_during_story():
    """Слеш-команды (/main, /inv, /start) во время сюжета удаляются, не сбивая сюжет."""
    uid = 999111
    chat_id = 999111
    game = GameState()
    game.is_name_set = True
    game.character_name = "Выживший"
    game.active_story_callback = "l4_2_tracks"
    main.games[uid] = game

    message = MagicMock()
    message.from_user = MagicMock()
    message.from_user.id = uid
    message.chat = MagicMock()
    message.chat.id = chat_id
    message.message_id = 5555
    message.delete = AsyncMock()

    with patch("main.safe_delete_message", new_callable=AsyncMock) as mock_del, \
         patch("main.restore_active_story_screen", new_callable=AsyncMock) as mock_restore:

        # 1. Попытка /main
        await main.cmd_main(message)
        mock_del.assert_called_with(chat_id, 5555)
        mock_restore.assert_called_with(chat_id, uid, game)
        # Сюжет НЕ стерт!
        assert game.active_story_callback == "l4_2_tracks"

        # 2. Попытка /inventory
        mock_del.reset_mock()
        mock_restore.reset_mock()
        await main.cmd_inventory(message)
        mock_del.assert_called_with(chat_id, 5555)
        mock_restore.assert_called_with(chat_id, uid, game)
        assert game.active_story_callback == "l4_2_tracks"

        # 3. Попытка /start
        mock_del.reset_mock()
        mock_restore.reset_mock()
        await main.cmd_start(message)
        mock_del.assert_called_with(chat_id, 5555)
        mock_restore.assert_called_with(chat_id, uid, game)
        assert game.active_story_callback == "l4_2_tracks"


@pytest.mark.anyio
async def test_callback_captures_active_message_id():
    """Любой callback мгновенно сохраняет message_id в last_active_msg_id и game.last_message_id."""
    uid = 888222
    chat_id = 888222
    game = GameState()
    game.is_name_set = True
    main.games[uid] = game
    main.last_active_msg_id.pop(uid, None)

    cb = MagicMock()
    cb.from_user = MagicMock()
    cb.from_user.id = uid
    cb.data = "noop"
    cb.message = MagicMock()
    cb.message.chat = MagicMock()
    cb.message.chat.id = chat_id
    cb.message.message_id = 77777
    cb.answer = AsyncMock()

    with patch("main.safe_edit_message", new_callable=AsyncMock) as mock_edit:
        mock_edit.return_value = True
        await main.process_callback(cb)

    assert main.last_active_msg_id.get(uid) == 77777
    assert getattr(game, "last_message_id", None) == 77777
