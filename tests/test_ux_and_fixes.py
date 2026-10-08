import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from game_state import GameState
from services.dialogs import handle_waiting_for_pet_name
from modules.traps import process_trap_rollover, place_trap, roll_trap_roll
from modules.items import (
    get_drop_menu_items,
    get_inspect_menu_items,
    handle_inventory_callback,
)
from keyboards import get_drop_item_kb, get_inspect_menu_kb
from main import process_callback, process_text_message, games, last_request_time, get_user_lock


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


@pytest.mark.anyio
async def test_process_text_message_immediate_delete_and_timeout():
    """Тест: входящий текст удаляется сразу до взятия лока, а при занятом локе срабатывает таймаут 3.0с."""
    uid = 999333
    chat_id = 999333

    fake_msg = AsyncMock()
    fake_msg.from_user.id = uid
    fake_msg.chat.id = chat_id
    fake_msg.message_id = 7777
    fake_msg.text = "Тестовый текст"

    lock = get_user_lock(uid)
    await lock.acquire()  # Искусственно занимаем лок

    deleted_msgs = []

    async def fake_del(cid, mid):
        deleted_msgs.append((cid, mid))

    async def fake_wait_for(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError()

    with patch("main.safe_delete_message", side_effect=fake_del), \
         patch("asyncio.wait_for", side_effect=fake_wait_for):

        await process_text_message(fake_msg)

        # Сообщение должно быть удалено СРАЗУ, даже если лок занят и случился таймаут
        assert (chat_id, 7777) in deleted_msgs

    lock.release()


def test_inventory_inspect_and_drop_use_short_callbacks_and_return_screens():
    """Длинные имена предметов не ломают callback; осмотр и сброс возвращают экраны."""
    item_name = "Редкий предмет " + "из длинного названия " * 5
    game = GameState()
    game.inventory[item_name] = 2

    inspect_kb = get_inspect_menu_kb(game)
    inspect_callbacks = [
        button.callback_data
        for row in inspect_kb.inline_keyboard
        for button in row
    ]
    assert all(len(callback.encode("utf-8")) <= 64 for callback in inspect_callbacks)
    inspect_index = get_inspect_menu_items(game).index(item_name)
    inspect_callback = f"inspect_item_{inspect_index}"
    assert inspect_callback in inspect_callbacks

    inspect_text, inspect_result_kb = asyncio.run(
        handle_inventory_callback(inspect_callback, game, 101)
    )
    assert item_name in inspect_text
    assert inspect_result_kb is not None

    drop_game = GameState()
    drop_game.inventory[item_name] = 2
    drop_kb = get_drop_item_kb(drop_game)
    drop_callbacks = [
        button.callback_data
        for row in drop_kb.inline_keyboard
        for button in row
    ]
    assert all(len(callback.encode("utf-8")) <= 64 for callback in drop_callbacks)
    drop_index = get_drop_menu_items(drop_game).index(item_name)
    drop_callback = f"drop_item_{drop_index}"
    assert drop_callback in drop_callbacks

    confirm_text, confirm_kb = asyncio.run(
        handle_inventory_callback(drop_callback, drop_game, 101)
    )
    assert item_name in confirm_text
    confirm_callbacks = [
        button.callback_data
        for row in confirm_kb.inline_keyboard
        for button in row
    ]
    assert "drop_qty:1" in confirm_callbacks
    assert "drop_qty:all" in confirm_callbacks

    result_text, _ = asyncio.run(
        handle_inventory_callback("drop_qty:1", drop_game, 101)
    )
    assert drop_game.inventory[item_name] == 1
    assert f"Удалено: {item_name} ×1." in result_text
