"""
tests/test_persistence.py — Автотесты персистентности и сериализации MongoDB.
"""

import pytest
from unittest.mock import patch, MagicMock
from game_state import GameState, Game
from services.database import (
    MemoryPlayersCollection,
    save_game,
    load_game,
    is_mongo_connected,
)


def test_persist_to_document_contains_name_fields():
    """Проверка наличия полей имени и флага в to_document."""
    game = GameState()
    game.player_name = "Следопыт_77"
    game.character_name = "Следопыт_77"
    game.is_name_set = True
    game.day = 3
    game.campfire_active = True
    game.inventory["Ветка"] = 5

    doc = game.to_document()
    assert "player_name" in doc
    assert doc["player_name"] == "Следопыт_77"
    assert "character_name" in doc
    assert doc["character_name"] == "Следопыт_77"
    assert "is_name_set" in doc
    assert doc["is_name_set"] is True
    assert doc["day"] == 3
    assert doc["campfire_active"] is True
    assert doc["inventory"].get("Ветка") == 5


def test_persist_to_document_no_set_types():
    """BSON-совместимость: to_document() не содержит типов set."""
    game = GameState()
    game.traps[1] = {"location_id": 1, "is_active": True}
    doc = game.to_document()

    def _assert_no_sets(obj, path=""):
        if isinstance(obj, set):
            raise AssertionError(f"Найден set в пути {path}: {obj}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                assert isinstance(k, str), f"Ключ словаря не является str в {path}: {k}"
                _assert_no_sets(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                _assert_no_sets(item, f"{path}[{idx}]")

    _assert_no_sets(doc, "doc")


def test_persist_save_and_load_round_trip():
    """Round-trip через MemoryPlayersCollection: сохранение и чтение идентичны."""
    mock_store = MemoryPlayersCollection()

    with patch("services.database.players_collection", mock_store):
        game = GameState()
        game.character_name = "Бродяга_Севера"
        game.player_name = "Бродяга_Севера"
        game.is_name_set = True
        game.day = 7
        game.hp = 92
        game.hunger = 45
        game.thirst = 80
        game.ap = 4
        game.campfire_active = True
        game.campfire_durability = 6
        game.inventory = {"Спички": 2, "Факел": 1, "Ветка": 4}
        game.traps[2] = {"location_id": 2, "is_active": True, "placed_day": 5}

        uid = 99887766
        ok = save_game(uid, game)
        assert ok is True

        # Проверяем, что в хранилище появился документ с _id и game_data
        stored_raw = mock_store.find_one({"_id": uid})
        assert stored_raw is not None
        assert "game_data" in stored_raw
        assert stored_raw["game_data"]["character_name"] == "Бродяга_Севера"
        assert stored_raw["game_data"]["is_name_set"] is True

        # Загружаем обратно через load_game
        loaded = load_game(uid)
        assert loaded is not None
        assert loaded.character_name == "Бродяга_Севера"
        assert loaded.player_name == "Бродяга_Севера"
        assert loaded.is_name_set is True
        assert loaded.day == 7
        assert loaded.hp == 92
        assert loaded.hunger == 45
        assert loaded.thirst == 80
        assert loaded.ap == 4
        assert loaded.campfire_active is True
        assert loaded.campfire_durability == 6
        assert loaded.inventory.get("Спички") == 2
        assert loaded.inventory.get("Факел") == 1
        assert 2 in loaded.traps
        assert loaded.traps[2]["is_active"] is True


@pytest.mark.anyio
async def test_persist_character_name_saves_immediately():
    """После успешного ввода имени в dialogs вызывается save_game и флаг is_name_set=True."""
    from services.dialogs import handle_waiting_for_character_name

    from unittest.mock import AsyncMock

    mock_store = MemoryPlayersCollection()

    with patch("services.database.players_collection", mock_store):
        uid = 55443322
        chat_id = 55443322
        game = GameState()
        game.story_state = "WAITING_FOR_CHARACTER_NAME"
        game.is_name_set = False

        fake_msg = MagicMock()
        fake_msg.message_id = 123

        bot_ctx = {
            "last_active_msg_id": {},
            "safe_delete_message": AsyncMock(),
            "safe_edit_message": AsyncMock(),
            "update_or_send_message": AsyncMock(),
            "format_game_text": lambda t, g: t,
        }

        # Эмулируем ввод имени персонажа
        handled = await handle_waiting_for_character_name(
            uid=uid,
            chat_id=chat_id,
            text="Таёжник",
            message=fake_msg,
            game=game,
            bot_ctx=bot_ctx,
        )

        assert handled is True
        assert game.character_name == "Таёжник"
        assert game.is_name_set is True
        assert game.story_state is None

        # Проверяем, что в БД сразу же лежит документ с именем и флагом
        saved_doc = mock_store.find_one({"_id": uid})
        assert saved_doc is not None
        assert "game_data" in saved_doc
        assert saved_doc["game_data"]["character_name"] == "Таёжник"
        assert saved_doc["game_data"]["is_name_set"] is True
