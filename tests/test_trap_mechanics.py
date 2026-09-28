import pytest
from game_state import GameState
from crafts import do_craft, can_craft, CRAFT_RECIPES
from keyboards import get_trap_buttons_kb
from unittest.mock import AsyncMock, patch
from main import process_callback, games, last_request_time


def test_trap_craft_and_consumption():
    game = GameState()
    game.inventory.clear()

    # Проверка рецепта
    assert "Охотничья ловушка" in CRAFT_RECIPES
    assert can_craft(game, "Охотничья ловушка") is False

    # Добавляем неполные ресурсы
    game.inventory["Ветка"] = 4
    game.inventory["Кусок коры"] = 2
    assert can_craft(game, "Охотничья ловушка") is False

    # Добавляем кожу и кость
    game.inventory["Кожа"] = 1
    game.inventory["Кость"] = 1
    assert can_craft(game, "Охотничья ловушка") is True

    ok, msg = do_craft(game, "Охотничья ловушка")
    assert ok is True
    assert game.inventory.get("Охотничья ловушка") == 1
    assert game.inventory.get("Ветка", 0) == 0
    assert game.inventory.get("Кусок коры", 0) == 0
    assert game.inventory.get("Кожа", 0) == 0
    assert game.inventory.get("Кость", 0) == 0


@pytest.mark.anyio
async def test_trap_placement_requires_item():
    uid = 99991
    last_request_time[uid] = 0
    game = GameState()
    game.is_name_set = True
    game.character_name = "Выживший"
    game.inventory.clear()
    game.traps.clear()
    games[uid] = game

    mock_query = AsyncMock()
    mock_query.from_user.id = uid
    mock_query.message.chat.id = uid
    mock_query.data = "trap_place_2"

    with patch("main.update_or_send_message", new_callable=AsyncMock) as mock_send, \
         patch("main.save_game"):
        # Попытка поставить без ловушки
        await process_callback(mock_query)
        assert 2 not in game.traps
        sent_text = mock_send.call_args[0][2]
        assert "У тебя нет охотничьей ловушки" in sent_text

        # Добавляем 1 ловушку
        last_request_time[uid] = 0
        game.inventory["Охотничья ловушка"] = 1
        await process_callback(mock_query)
        assert 2 in game.traps
        assert game.traps[2]["is_active"] is True
        assert game.inventory.get("Охотничья ловушка", 0) == 0

        # Повторная попытка на ту же локацию (уже активна)
        last_request_time[uid] = 0
        await process_callback(mock_query)
        sent_text = mock_send.call_args[0][2]
        assert "уже взведена ловушка" in sent_text


@pytest.mark.anyio
async def test_trap_replace_broken():
    uid = 99992
    last_request_time[uid] = 0
    game = GameState()
    game.is_name_set = True
    game.character_name = "Выживший"
    game.inventory.clear()
    game.traps[3] = {
        "location_id": 3,
        "is_active": False,
        "is_broken": True,
        "placed_day": 1,
    }
    games[uid] = game

    mock_query = AsyncMock()
    mock_query.from_user.id = uid
    mock_query.message.chat.id = uid
    mock_query.data = "trap_replace_3"

    with patch("main.update_or_send_message", new_callable=AsyncMock) as mock_send, \
         patch("main.save_game"):
        # Без ловушки в инвентаре
        await process_callback(mock_query)
        assert game.traps[3]["is_broken"] is True
        sent_text = mock_send.call_args[0][2]
        assert "нет новой охотничьей ловушки" in sent_text

        # Дали ловушку
        last_request_time[uid] = 0
        game.inventory["Охотничья ловушка"] = 1
        await process_callback(mock_query)
        assert game.traps[3]["is_broken"] is False
        assert game.traps[3]["is_active"] is True
        assert game.inventory.get("Охотничья ловушка", 0) == 0


def test_trap_buttons_keyboard():
    game = GameState()
    game.traps.clear()
    game.traps[2] = {"is_active": True, "is_broken": False}
    game.traps[3] = {"is_active": False, "is_broken": True}

    kb = get_trap_buttons_kb(game)
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("✅ Ручей (взведена)" in t for t in texts)
    assert any("🔨 Лощина (сломана — заменить)" in t for t in texts)
    assert any("🪤 Лес (поставить)" in t for t in texts)
