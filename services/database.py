"""
services/database.py — Слой работы с базой данных (MongoDB / in-memory fallback).

Экспортирует:
    players_collection  — объект коллекции (MongoCollection или MemoryPlayersCollection)
    load_game(uid)      — загрузить сохранение игрока
    save_game(uid, game)— сохранить состояние игрока
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
    """Простое in-memory хранилище — используется когда MongoDB недоступна."""

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
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = mongo_client["forest_game"]
    players_collection = db["players"]
    players_collection.database.command("ping")
    logging.info("MongoDB подключена успешно")
except Exception as exc:
    logging.warning(f"Mongo недоступен, используется in-memory fallback: {exc}")
    players_collection = MemoryPlayersCollection()


# ──────────────────────────────────────────────────────────────────────────────
# КЭШ АКТИВНЫХ СЕССИЙ
# ──────────────────────────────────────────────────────────────────────────────
games: dict = {}  # {user_id: Game}


# ──────────────────────────────────────────────────────────────────────────────
# СОХРАНЕНИЕ / ЗАГРУЗКА
# ──────────────────────────────────────────────────────────────────────────────
def load_game(uid: int) -> Game | None:
    """Загрузить сохранение игрока из БД. Возвращает None если не найдено."""
    try:
        data = players_collection.find_one({"_id": uid})
        if data and "game_data" in data:
            game_data = dict(data["game_data"])
            return Game.from_document(game_data)
    except Exception as e:
        logging.error(f"Ошибка загрузки {uid}: {e}")
    return None


def save_game(uid: int, game: Game) -> None:
    """Сохранить текущее состояние игрока в БД."""
    try:
        data = game.to_document()
        players_collection.update_one(
            {"_id": uid},
            {"$set": {"game_data": data}},
            upsert=True,
        )
    except Exception as e:
        logging.error(f"Ошибка сохранения {uid}: {e}")
