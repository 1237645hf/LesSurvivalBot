"""
services/database.py — Слой работы с базой данных (MongoDB / in-memory fallback).

Экспортирует:
    players_collection  — объект коллекции (MongoCollection или MemoryPlayersCollection)
    load_game(uid)      — загрузить сохранение игрока
    save_game(uid, game)— сохранить состояние игрока
    is_mongo_connected()— проверка реального подключения к MongoDB
    games               — кэш активных сессий {user_id: GameState}
"""

import logging
import os
from pymongo import MongoClient

from game_state import Game


# ──────────────────────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────────
# IN-MEMORY FALLBACK
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_TABLET_NOTES = [
    {
        "user_id": 0,
        "author": "Бродяга (неизвестен)",
        "text": "Если пришёл — грейся, если взял — оставь для следующего.",
        "created_at": 1,
    },
    {
        "user_id": 0,
        "author": "Бродяга (неизвестен)",
        "text": "Крыша течёт справа. — Уже нет.",
        "created_at": 2,
    },
    {
        "user_id": 0,
        "author": "Бродяга (неизвестен)",
        "text": "В печи тяга плохая. Заднюю щель не закрывать.",
        "created_at": 3,
    },
    {
        "user_id": 0,
        "author": "Бродяга (неизвестен)",
        "text": "Я думал, здесь никого больше нет. — Я тоже.",
        "created_at": 4,
    },
]


class MemoryPlayersCollection:
    """Простое in-memory хранилище — используется ТОЛЬКО когда MongoDB недоступна."""

    def __init__(self):
        self._store = {}

    def find_one(self, query):
        player_id = query.get("_id") if isinstance(query, dict) else None
        return self._store.get(player_id)

    def update_one(self, query, update, upsert=False):
        player_id = query.get("_id") if isinstance(query, dict) else None
        if player_id is None:
            return
        current = self._store.setdefault(player_id, {"_id": player_id})
        if "$set" in update:
            current.update(update["$set"])
            self._store[player_id] = current


class MemoryTabletNotesCollection:
    """In-memory хранилище надписей на каменной плите."""

    def __init__(self):
        self._notes = [dict(n) for n in DEFAULT_TABLET_NOTES]

    def find(self, query=None):
        class _Cursor:
            def __init__(self, notes):
                self._n = list(notes)

            def sort(self, field, direction=1):
                self._n.sort(key=lambda x: x.get(field, 0), reverse=(direction < 0))
                return self

            def __iter__(self):
                return iter(self._n)

        return _Cursor(self._notes)

    def update_one(self, query, update, upsert=False):
        uid = query.get("user_id") if isinstance(query, dict) else None
        set_data = update.get("$set", {})
        for note in self._notes:
            if note.get("user_id") == uid and uid != 0:
                note.update(set_data)
                return
        if upsert:
            new_note = dict(set_data)
            new_note["user_id"] = uid
            self._notes.append(new_note)


# ──────────────────────────────────────────────────────────────────────────────
# MONGODB INIT
# ──────────────────────────────────────────────────────────────────────────────
def is_testing_mode() -> bool:
    """Проверка, запущен ли код в тестовом режиме (pytest / локальные тесты)."""
    return os.getenv("LES_TESTING") == "1" or os.getenv("FORCE_MEMORY_DB") == "1"


MONGO_URI = os.getenv("MONGO_URI") or ("" if is_testing_mode() else "mongodb://localhost:27017/test")

mongo_client = None
players_collection = None
tablet_notes_collection = None


def is_mongo_connected() -> bool:
    """Проверить, работает ли приложение с реальной MongoDB (не fallback)."""
    return players_collection is not None and not isinstance(players_collection, MemoryPlayersCollection)


def _init_mongo():
    global mongo_client, players_collection, tablet_notes_collection
    if is_testing_mode():
        players_collection = MemoryPlayersCollection()
        tablet_notes_collection = MemoryTabletNotesCollection()
        return

    try:
        # Увеличенный таймаут 10000мс для стабильного DNS-резолвинга SRV и TLS handshake на Render
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client["forest_game"]
        coll = db["players"]
        notes_coll = db["stone_tablet_notes"]
        coll.database.command("ping")
        mongo_client = client
        players_collection = coll
        tablet_notes_collection = notes_coll
        # Инициализация каноничных надписей в пустой коллекции
        if notes_coll.count_documents({"user_id": 0}) == 0:
            notes_coll.insert_many([dict(n) for n in DEFAULT_TABLET_NOTES])
        logging.info("MongoDB подключена успешно к базе 'forest_game'")
    except Exception as exc:
        logging.critical(
            f"ВНИМАНИЕ! Не удалось подключиться к MongoDB ({exc}). "
            f"Используется in-memory fallback! Данные НЕ сохранятся при перезапуске контейнера на Render!"
        )
        players_collection = MemoryPlayersCollection()
        tablet_notes_collection = MemoryTabletNotesCollection()


_init_mongo()



# ──────────────────────────────────────────────────────────────────────────────
# КЭШ АКТИВНЫХ СЕССИЙ
# ──────────────────────────────────────────────────────────────────────────────
games: dict = {}  # {user_id: Game}


def _migrate_memory_to_mongo(
    coll,
    notes_coll,
    old_players=None,
    old_notes=None,
) -> tuple[int, int]:
    """Миграция данных, накопленных в in-memory fallback, в реальную MongoDB.

    Возвращает кортеж (migrated_players_count, migrated_notes_count).
    """
    migrated_players = 0
    migrated_notes = 0

    # 1. Миграция сохранённых состояний игроков из MemoryPlayersCollection
    if isinstance(old_players, MemoryPlayersCollection):
        for uid, doc in list(old_players._store.items()):
            try:
                set_data = {k: v for k, v in doc.items() if k != "_id"}
                if set_data:
                    coll.update_one({"_id": uid}, {"$set": set_data}, upsert=True)
                    migrated_players += 1
            except Exception as exc:
                logging.error(f"Ошибка миграции игрока {uid} из памяти в MongoDB: {exc}", exc_info=True)

    # 2. Миграция активных игровых сессий из кэша games
    for uid, game in list(games.items()):
        try:
            data = game.to_document()
            coll.update_one({"_id": uid}, {"$set": {"game_data": data}}, upsert=True)
            if not isinstance(old_players, MemoryPlayersCollection) or uid not in getattr(old_players, "_store", {}):
                migrated_players += 1
        except Exception as exc:
            logging.error(f"Ошибка миграции активной игры {uid} из кэша games в MongoDB: {exc}", exc_info=True)

    # 3. Миграция записей каменной плиты из MemoryTabletNotesCollection
    if isinstance(old_notes, MemoryTabletNotesCollection):
        for note in getattr(old_notes, "_notes", []):
            uid = note.get("user_id")
            if uid and uid != 0:
                try:
                    note_data = {k: v for k, v in note.items() if k != "_id"}
                    notes_coll.update_one(
                        {"user_id": uid},
                        {"$set": note_data},
                        upsert=True,
                    )
                    migrated_notes += 1
                except Exception as exc:
                    logging.error(f"Ошибка миграции заметки плиты {uid} в MongoDB: {exc}", exc_info=True)

    # 4. Проверка и заполнение каноничных надписей в пустой коллекции плиты
    try:
        if notes_coll.count_documents({"user_id": 0}) == 0:
            notes_coll.insert_many([dict(n) for n in DEFAULT_TABLET_NOTES])
    except Exception as exc:
        logging.error(f"Ошибка проверки каноничных надписей плиты при миграции: {exc}", exc_info=True)

    return migrated_players, migrated_notes


def _ensure_mongo_connection():
    """Ленивая попытка восстановить подключение к MongoDB, если на старте был временный сбой сети."""
    global mongo_client, players_collection, tablet_notes_collection
    if is_mongo_connected():
        return
    uri = os.getenv("MONGO_URI") or MONGO_URI
    # В тестовом режиме не пытаемся подключаться к реальной Mongo, кроме тестов с моками (когда задан MONGO_URI)
    if is_testing_mode() and not os.getenv("MONGO_URI"):
        return
    if uri:
        try:
            timeout_ms = 100 if is_testing_mode() else 5000
            client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
            db = client["forest_game"]
            coll = db["players"]
            notes_coll = db["stone_tablet_notes"]
            coll.database.command("ping")

            # Переносим накопленные данные из памяти в базу ДО переключения ссылок
            old_players = players_collection
            old_notes = tablet_notes_collection
            migrated_players, migrated_notes = _migrate_memory_to_mongo(
                coll=coll,
                notes_coll=notes_coll,
                old_players=old_players,
                old_notes=old_notes,
            )

            # Переключаем глобальные переменные на реальную MongoDB только после успешной миграции
            mongo_client = client
            players_collection = coll
            tablet_notes_collection = notes_coll

            logging.info(
                f"MongoDB: связь восстановлена, подключение успешно переключено с memory на MongoDB! "
                f"Мигрировано игроков: {migrated_players}, заметок каменной плиты: {migrated_notes}."
            )
        except Exception as exc:
            if not is_testing_mode():
                logging.warning(f"MongoDB: попытка восстановления подключения не удалась ({exc}). Продолжаем fallback.")



# ──────────────────────────────────────────────────────────────────────────────
# СОХРАНЕНИЕ / ЗАГРУЗКА
# ──────────────────────────────────────────────────────────────────────────────
def load_game(uid: int) -> Game | None:
    """Загрузить сохранение игрока из БД. Возвращает None если не найдено."""
    _ensure_mongo_connection()
    try:
        data = players_collection.find_one({"_id": uid})
        if data and "game_data" in data:
            game_data = dict(data["game_data"])
            return Game.from_document(game_data)
    except Exception as e:
        logging.error(f"Ошибка загрузки сохранения {uid}: {e}", exc_info=True)
    return None


def save_game(uid: int, game: Game) -> bool:
    """Сохранить текущее состояние игрока в БД. Возвращает True при успехе."""
    _ensure_mongo_connection()
    try:
        data = game.to_document()
        players_collection.update_one(
            {"_id": uid},
            {"$set": {"game_data": data}},
            upsert=True,
        )
        return True
    except Exception as e:
        logging.error(f"Ошибка сохранения {uid}: {e}", exc_info=True)
        return False


def get_tablet_notes() -> list[dict]:
    """Получить список всех записей на каменной плите."""
    _ensure_mongo_connection()
    try:
        if tablet_notes_collection is not None:
            return list(tablet_notes_collection.find().sort("created_at", 1))
    except Exception as e:
        logging.error(f"Ошибка чтения записей каменной плиты: {e}", exc_info=True)
    return list(DEFAULT_TABLET_NOTES)


def save_tablet_note(uid: int, author: str, text: str) -> bool:
    """Сохранить или обновить запись игрока на каменной плите."""
    _ensure_mongo_connection()
    import time
    data = {
        "user_id": uid,
        "author": author,
        "text": text,
        "created_at": time.time(),
    }
    try:
        if tablet_notes_collection is not None:
            tablet_notes_collection.update_one(
                {"user_id": uid},
                {"$set": data},
                upsert=True,
            )
            return True
    except Exception as e:
        logging.error(f"Ошибка сохранения надписи на плите {uid}: {e}", exc_info=True)
    return False

