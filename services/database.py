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
# IN-MEMORY FALLBACK
# ──────────────────────────────────────────────────────────────────────────────
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
        current = self._store.setdefault(player_id, {})
        if "$set" in update:
            current.update(update["$set"])
            self._store[player_id] = current


# ──────────────────────────────────────────────────────────────────────────────
# MONGODB INIT
# ──────────────────────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI") or "mongodb://localhost:27017/test"

mongo_client = None
players_collection = None


def is_mongo_connected() -> bool:
    """Проверить, работает ли приложение с реальной MongoDB (не fallback)."""
    return players_collection is not None and not isinstance(players_collection, MemoryPlayersCollection)


def _init_mongo():
    global mongo_client, players_collection
    try:
        # Увеличенный таймаут 10000мс для стабильного DNS-резолвинга SRV и TLS handshake на Render
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client["forest_game"]
        coll = db["players"]
        coll.database.command("ping")
        mongo_client = client
        players_collection = coll
        logging.info("MongoDB подключена успешно к базе 'forest_game', коллекция 'players'")
    except Exception as exc:
        logging.critical(
            f"ВНИМАНИЕ! Не удалось подключиться к MongoDB ({exc}). "
            f"Используется in-memory fallback! Данные НЕ сохранятся при перезапуске контейнера на Render!"
        )
        players_collection = MemoryPlayersCollection()


_init_mongo()


def _ensure_mongo_connection():
    """Ленивая попытка восстановить подключение к MongoDB, если на старте был временный сбой сети."""
    global mongo_client, players_collection
    if is_mongo_connected():
        return
    if os.getenv("MONGO_URI"):
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db = client["forest_game"]
            coll = db["players"]
            coll.database.command("ping")
            mongo_client = client
            players_collection = coll
            logging.info("MongoDB: связь восстановлена, подключение успешно переключено с memory на MongoDB!")
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# КЭШ АКТИВНЫХ СЕССИЙ
# ──────────────────────────────────────────────────────────────────────────────
games: dict = {}  # {user_id: Game}


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
