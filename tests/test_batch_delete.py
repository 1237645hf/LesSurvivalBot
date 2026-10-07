import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

import main
from main import (
    safe_delete_messages,
    track_message_to_delete,
    clear_tracked_messages,
    cmd_start,
)


@pytest.mark.anyio
async def test_safe_delete_messages_empty():
    with patch.object(main.bot, "delete_messages", new_callable=AsyncMock) as mock_delete:
        await safe_delete_messages(chat_id=123, message_ids=[])
        mock_delete.assert_not_called()


@pytest.mark.anyio
async def test_safe_delete_messages_single_batch():
    with patch.object(main.bot, "delete_messages", new_callable=AsyncMock) as mock_delete:
        await safe_delete_messages(chat_id=123, message_ids=[10, 20, 30])
        mock_delete.assert_called_once()
        args, kwargs = mock_delete.call_args
        assert kwargs["chat_id"] == 123
        assert set(kwargs["message_ids"]) == {10, 20, 30}


@pytest.mark.anyio
async def test_safe_delete_messages_chunking_over_100():
    with patch.object(main.bot, "delete_messages", new_callable=AsyncMock) as mock_delete:
        ids = list(range(1, 151))  # 150 IDs -> should be 2 chunks (100 and 50)
        await safe_delete_messages(chat_id=123, message_ids=ids)
        assert mock_delete.call_count == 2
        chunk1 = mock_delete.call_args_list[0][1]["message_ids"]
        chunk2 = mock_delete.call_args_list[1][1]["message_ids"]
        assert len(chunk1) == 100
        assert len(chunk2) == 50


@pytest.mark.anyio
async def test_safe_delete_messages_handles_bad_request():
    with patch.object(
        main.bot,
        "delete_messages",
        new_callable=AsyncMock,
        side_effect=TelegramBadRequest(method=MagicMock(), message="message to delete not found"),
    ) as mock_delete:
        # Should not raise exception
        await safe_delete_messages(chat_id=123, message_ids=[999])
        mock_delete.assert_called_once()


@pytest.mark.anyio
async def test_fsm_track_and_clear_messages():
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=123, user_id=456)
    state = FSMContext(storage=storage, key=key)

    await track_message_to_delete(state, 101)
    await track_message_to_delete(state, 102)

    data = await state.get_data()
    assert data.get("messages_to_delete") == [101, 102]

    with patch.object(main.bot, "delete_messages", new_callable=AsyncMock) as mock_delete:
        await clear_tracked_messages(chat_id=123, state=state, extra_ids=[103])
        mock_delete.assert_called_once()
        kwargs = mock_delete.call_args[1]
        assert kwargs["chat_id"] == 123
        assert set(kwargs["message_ids"]) == {101, 102, 103}

        # Check state cleared
        data_after = await state.get_data()
        assert data_after.get("messages_to_delete") == []


@pytest.mark.anyio
async def test_cmd_start_no_blind_deletion_loop():
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=123, user_id=456)
    state = FSMContext(storage=storage, key=key)
    await state.update_data(messages_to_delete=[555])

    fake_message = MagicMock()
    fake_message.from_user.id = 456
    fake_message.chat.id = 123
    fake_message.message_id = 999
    fake_message.answer = AsyncMock()

    main.last_active_msg_id[456] = 888

    with patch.object(main.bot, "delete_messages", new_callable=AsyncMock) as mock_delete_batch, \
         patch.object(main.bot, "delete_message", new_callable=AsyncMock) as mock_delete_single, \
         patch("main.update_or_send_message", new_callable=AsyncMock):

        await cmd_start(fake_message, state=state)

        # Batch delete should be called exactly once with real IDs (555, 999, 888)
        mock_delete_batch.assert_called_once()
        called_ids = set(mock_delete_batch.call_args[1]["message_ids"])
        assert called_ids == {555, 888, 999}

        # Verify no blind loop range(1, 50) was run on delete_message
        for call in mock_delete_single.call_args_list:
            if call[0] and len(call[0]) > 1:
                assert call[0][1] not in [999 - i for i in range(1, 50)]


@pytest.mark.anyio
async def test_update_or_send_message_batch_delete_success():
    """При need_recreate сначала отправляется один пакетный запрос delete_messages (до 100 ID), включающий гарантированные ID."""
    uid = 777
    chat_id = 123
    game = MagicMock()
    game.last_message_id = 500
    game.header_message_id = 490
    game.last_action_time = 0  # Принудительно time_expired -> need_recreate = True
    main.games[uid] = game
    main.last_active_msg_id[uid] = 505

    sent_msg = MagicMock()
    sent_msg.message_id = 600

    try:
        with patch.object(main.bot, "delete_messages", new_callable=AsyncMock) as mock_delete_batch, \
             patch.object(main.bot, "delete_message", new_callable=AsyncMock) as mock_delete_single, \
             patch.object(main.bot, "send_message", new_callable=AsyncMock, return_value=sent_msg), \
             patch("main.save_game"):

            await main.update_or_send_message(chat_id, uid, "Привет", current_msg_id=506)

            # Пакетный запрос должен быть вызван ровно 1 раз
            mock_delete_batch.assert_called_once()
            batch_ids = mock_delete_batch.call_args[1]["message_ids"]
            # Гарантированные ID должны присутствовать в пачке
            assert 500 in batch_ids
            assert 490 in batch_ids
            assert 505 in batch_ids
            assert 506 in batch_ids
            assert len(batch_ids) <= 100
            # Одиночные вызовы delete_message НЕ должны вызываться при успешном пакете
            mock_delete_single.assert_not_called()
    finally:
        main.games.pop(uid, None)
        main.last_active_msg_id.pop(uid, None)


@pytest.mark.anyio
async def test_update_or_send_message_batch_delete_fallback():
    """Если пакетный запрос упал с ошибкой, fallback сначала точечно удаляет гарантированные ID."""
    uid = 888
    chat_id = 123
    game = MagicMock()
    game.last_message_id = 500
    game.header_message_id = 490
    game.last_action_time = 0
    main.games[uid] = game
    main.last_active_msg_id[uid] = 505

    sent_msg = MagicMock()
    sent_msg.message_id = 600

    deleted_order = []

    async def fake_delete_message(chat_id, message_id):
        deleted_order.append(message_id)

    try:
        with patch.object(main.bot, "delete_messages", new_callable=AsyncMock, side_effect=TelegramBadRequest(method=MagicMock(), message="message to delete not found")), \
             patch.object(main.bot, "delete_message", side_effect=fake_delete_message), \
             patch.object(main.bot, "send_message", new_callable=AsyncMock, return_value=sent_msg), \
             patch("main.save_game"):

            await main.update_or_send_message(chat_id, uid, "Привет", current_msg_id=506)

            # Гарантированные ID должны быть удалены первыми
            guaranteed = {500, 490, 505, 506}
            first_calls = set(deleted_order[:len(guaranteed)])
            assert first_calls == guaranteed
    finally:
        main.games.pop(uid, None)
        main.last_active_msg_id.pop(uid, None)

