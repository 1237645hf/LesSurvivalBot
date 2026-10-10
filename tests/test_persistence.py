"""
tests/test_persistence.py — Автотесты персистентности и сериализации MongoDB.
"""

import pytest
from unittest.mock import patch, MagicMock
from game_state import GameState, Game
from services.database import (
    MemoryPlayersCollection,
    MemoryTabletNotesCollection,
    save_game,
    load_game,
    is_mongo_connected,
    _migrate_memory_to_mongo,
    _ensure_mongo_connection,
    save_tablet_note,
    games,
)


@pytest.mark.smoke
@pytest.mark.persist
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


@pytest.mark.persist
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


@pytest.mark.smoke
@pytest.mark.persist
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


@pytest.mark.persist
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


@pytest.mark.persist
def test_migrate_memory_to_mongo_migrates_players_and_notes():
    """Тест миграции данных из Memory-коллекций и games кэша в MongoDB коллекции."""
    old_players = MemoryPlayersCollection()
    old_players.update_one({"_id": 111}, {"$set": {"game_data": {"character_name": "Память_111"}}})

    old_notes = MemoryTabletNotesCollection()
    old_notes.update_one(
        {"user_id": 222},
        {"$set": {"user_id": 222, "author": "Автор_222", "text": "Текст_222"}},
        upsert=True,
    )

    active_game = GameState()
    active_game.character_name = "Активный_333"
    games[333] = active_game

    try:
        mock_coll = MagicMock()
        mock_notes_coll = MagicMock()
        mock_notes_coll.count_documents.return_value = 0

        p_count, n_count = _migrate_memory_to_mongo(
            coll=mock_coll,
            notes_coll=mock_notes_coll,
            old_players=old_players,
            old_notes=old_notes,
        )

        assert p_count == 2
        assert n_count == 1

        # Проверяем, что update_one вызывался для игрока 111 и игрока 333
        coll_calls = mock_coll.update_one.call_args_list
        uids_updated = [call[0][0]["_id"] for call in coll_calls]
        assert 111 in uids_updated
        assert 333 in uids_updated

        # Проверяем, что update_one вызывался для заметки 222
        notes_calls = mock_notes_coll.update_one.call_args_list
        note_uids = [call[0][0]["user_id"] for call in notes_calls]
        assert 222 in note_uids

        # Проверяем проверку каноничных записей
        mock_notes_coll.insert_many.assert_called_once()
    finally:
        games.pop(333, None)


@pytest.mark.persist
def test_ensure_mongo_connection_full_reconnect_and_migration():
    """Тест: при восстановлении сети _ensure_mongo_connection переносит данные и переключает коллекции."""
    import services.database as db_module

    mem_players = MemoryPlayersCollection()
    mem_notes = MemoryTabletNotesCollection()

    original_players = db_module.players_collection
    original_notes = db_module.tablet_notes_collection
    original_client = db_module.mongo_client

    db_module.players_collection = mem_players
    db_module.tablet_notes_collection = mem_notes

    try:
        # Игрок сохраняет прогресс во время fallback
        game = GameState()
        game.character_name = "Спасённый_Игрок"
        game.player_name = "Спасённый_Игрок"
        game.is_name_set = True
        save_game(555, game)

        # Игрок оставляет надпись на плите во время fallback
        save_tablet_note(555, "Спасённый_Игрок", "Мы выжили")

        # Мокируем MongoClient и его коллекции
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_mongo_players = MagicMock()
        mock_mongo_notes = MagicMock()

        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.side_effect = lambda name: {
            "players": mock_mongo_players,
            "stone_tablet_notes": mock_mongo_notes,
        }[name]
        mock_mongo_players.database.command.return_value = {"ok": 1}
        mock_mongo_notes.count_documents.return_value = 1

        with patch.dict("os.environ", {"MONGO_URI": "mongodb://mocked:27017"}), \
             patch("services.database.MongoClient", return_value=mock_client):

            # До вызова мы на Memory-коллекции
            assert not is_mongo_connected()

            _ensure_mongo_connection()

            # После вызова мы успешно переключились на MongoDB
            assert is_mongo_connected()
            assert db_module.players_collection is mock_mongo_players
            assert db_module.tablet_notes_collection is mock_mongo_notes

            # Проверяем, что данные игрока 555 перенесены в mock_mongo_players
            saved_calls = [call for call in mock_mongo_players.update_one.call_args_list if call[0][0].get("_id") == 555]
            assert len(saved_calls) >= 1
            assert saved_calls[0][0][1]["$set"]["game_data"]["character_name"] == "Спасённый_Игрок"

            # Проверяем, что заметка игрока 555 перенесена в mock_mongo_notes
            note_calls = [call for call in mock_mongo_notes.update_one.call_args_list if call[0][0].get("user_id") == 555]
            assert len(note_calls) >= 1
            assert note_calls[0][0][1]["$set"]["author"] == "Спасённый_Игрок"
    finally:
        db_module.players_collection = original_players
        db_module.tablet_notes_collection = original_notes
        db_module.mongo_client = original_client
        games.pop(555, None)


@pytest.mark.persist
def test_ensure_mongo_connection_failure_keeps_fallback_intact():
    """Тест: если при попытке переподключения Mongo падает, fallback и накопленные данные не повреждаются."""
    import services.database as db_module

    mem_players = MemoryPlayersCollection()
    mem_notes = MemoryTabletNotesCollection()

    original_players = db_module.players_collection
    original_notes = db_module.tablet_notes_collection
    original_client = db_module.mongo_client

    db_module.players_collection = mem_players
    db_module.tablet_notes_collection = mem_notes

    try:
        game = GameState()
        game.character_name = "Остался_В_Памяти"
        game.player_name = "Остался_В_Памяти"
        game.is_name_set = True
        save_game(666, game)

        mock_client = MagicMock()
        mock_client.__getitem__.side_effect = Exception("Connection refused")

        with patch.dict("os.environ", {"MONGO_URI": "mongodb://mocked:27017"}), \
             patch("services.database.MongoClient", return_value=mock_client):

            _ensure_mongo_connection()

            # Должны остаться на fallback
            assert not is_mongo_connected()
            assert db_module.players_collection is mem_players
            assert db_module.tablet_notes_collection is mem_notes

            # Данные в памяти не потеряны
            loaded = load_game(666)
            assert loaded is not None
            assert loaded.character_name == "Остался_В_Памяти"
    finally:
        db_module.players_collection = original_players
        db_module.tablet_notes_collection = original_notes
        db_module.mongo_client = original_client
        games.pop(666, None)

