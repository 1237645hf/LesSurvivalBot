import asyncio
import logging
import os
import time
import random
from textwrap import wrap
from pathlib import Path
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from pymongo import MongoClient

from game_math import (
    process_damage,
    get_resource_multiplier,
    get_base_resource_cost,
    get_thirst_base_cost,
    calculate_ap_by_hp,
)
from game_state import GameState
from modules.hints import get_active_hints
from modules.traps import (
    HUNTABLE_ANIMALS,
    TRAP_CHANCE_BY_LOCATION,
    place_trap,
    remove_trap,
    activate_trap,
    get_trap_for_location,
    get_trap_description,
    get_trap_loot,
    get_active_traps,
    roll_trap_roll,
    process_trap_rollover,
)

# ──────────────────────────────────────────────────────────────────────────────
# РЕЦЕПТЫ КОСТРА
# ──────────────────────────────────────────────────────────────────────────────
CAMPFIRE_RECIPES = {
    "Жареное мясо": {"ingredients": {"Сырое мясо": 1}, "output": "Жареное мясо"},
    "Жареная рыба": {"ingredients": {"Сырая рыба": 1}, "output": "Жареная рыба"},
    "Жареные грибы": {"ingredients": {"Грибы": 1}, "output": "Жареные грибы"},
    "Травяной отвар": {"ingredients": {"Лекарственные травы": 1, "Чистая вода": 1}, "output": "Травяной отвар"},
}


def load_env_file(path: str = ".env"):
    """Загрузить переменные из .env, если они ещё не заданы в окружении."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file()

from keyboards import (
    get_main_kb,
    get_locations_kb,
    get_settings_kb,
    get_bottom_menu,
    get_use_item_kb,
    get_drop_item_kb,
    get_campfire_kb,
    get_campfire_fuel_kb,
    get_campfire_recipes_kb,
    get_campfire_recipe_kb,
    inventory_inline_kb,
    character_inline_kb,
)
from crafts import handle_craft
from location_stories import (
    handle_story,
    handle_location_2_ruchey,
    handle_location_3_slate_hollow,
    handle_location_4_hunters_glade,
    handle_location_5_slug_pit,
    handle_location_6_furry_cave,
    handle_location_7_sanctuary_peak,
    ending_text,
    resolve_ending,
    ENDING_TITLES,
)
# ──────────────────────────────────────────────────────────────────────────────
# НАСТРОЙКИ
# ──────────────────────────────────────────────────────────────────────────────
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден!")

MONGO_URI = os.getenv("MONGO_URI") or "mongodb://localhost:27017/test"

logging.basicConfig(level=logging.INFO)
logging.info("Бот запускается в режиме Telegram polling")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальные словари для трекинга состояний (запросы, сообщения)
last_request_time = {}
last_active_msg_id = {}

# set_my_commands вызывается в run_bot() с await

# ──────────────────────────────────────────────────────────────────────────────
# MONGODB
# ──────────────────────────────────────────────────────────────────────────────
class MemoryPlayersCollection:
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


mongo_client = None
players_collection = None
try:
    mongo_client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=3000
    )
    db = mongo_client['forest_game']
    players_collection = db['players']
    players_collection.database.command('ping')
except Exception as exc:
    logging.warning(f"Mongo недоступен, используется in-memory fallback: {exc}")
    players_collection = MemoryPlayersCollection()

# ──────────────────────────────────────────────────────────────────────────────
# КЛАСС ИГРЫ
# ──────────────────────────────────────────────────────────────────────────────
class Game(GameState):
    def __init__(self):
        super().__init__()
        self.hp = 100
        self.hunger = 20
        self.thirst = 60
        self.ap = 5
        self.karma = {"heroic": 20, "brutal": 5, "gentle": 10, "clever": 15, "reckless": 8, "mysterious": 12}
        self.karma_goal = 100
        self.day = 1
        self.log = ["Ты проснулся в лесу. Что будешь делать?"]
        self.inventory = {
            "Спички": 1,
            "Вилка": 1,
            "Кусок коры": 1,
            "Сухпай": 3,
            "Вода": 10,
        }
        self.weather = "clear"
        self.location = "Лесной старт"
        self.unlocked_locations = ["Лесной старт", "Ручей с Змеями", "Скромоная Лощина", "Просека Охотников", "Яр Слизней", "Мохнатая Пещера", "Вершина Святилища"]
        self.current_location_state = "forest_start"
        self.water_capacity = 10
        self.equipment = {
            "head": None,
            "torso": None,
            "back": None,
            "pants": None,
            "boots": None,
            "trinket": None,
            "pet": None,
            "hand": None,
        }
        self.story_state = None
        self.found_branch_once = False
        self.nav_stack = ["main"]

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    def push_screen(self, screen: str):
        self.nav_stack.append(screen)

    def pop_screen(self):
        if len(self.nav_stack) > 1:
            self.nav_stack.pop()
        return self.nav_stack[-1]

    def reset_nav(self):
        self.nav_stack = ["main"]

    def get_ui(self):
        max_width = self.max_line_length if self.display_mode == "phone" else None
        return (
            f"{self.get_status_bar(max_width)}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(f"> {line}" for line in self.log) + "\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

    def get_inventory_text(self):
        lines = []
        equipped_hand = self.equipment.get("hand")
        for item, count in self.inventory.items():
            if count > 0:
                item = item.replace(" 🔥", "").replace("🔥", "")
                equipped_mark = " (в руке)" if item == equipped_hand else ""
                line = f"• {item} x{count}{equipped_mark}" if count > 1 else f"• {item}{equipped_mark}"
                lines.append(line)
        text = "Инвентарь:\n" + "\n".join(lines) if lines else "Инвентарь пуст"
        text += "\n━━━━━━━━━━━━━━━━━━━"
        return text

    def get_character_text(self):
        pet_text = f"Питомец: {self.equipment['pet']}" if self.equipment.get("pet") else "Питомец: Пусто"
        slots = {
            "head": "Голова",
            "torso": "Торс",
            "back": "Спина",
            "pants": "Штаны",
            "boots": "Ботинки",
            "trinket": "Безделушка",
            "pet": pet_text,
            "hand": "Рука",
        }
        lines = [f"{name}: {self.equipment.get(slot) or 'Пусто'}" for slot, name in slots.items()]
        return "Персонаж:\n\n" + "\n".join(lines)

# ──────────────────────────────────────────────────────────────────────────────
# СОХРАНЕНИЕ / ЗАГРУЗКА
# ──────────────────────────────────────────────────────────────────────────────
def load_game(uid: int) -> Game | None:
    try:
        data = players_collection.find_one({"_id": uid})
        if data and "game_data" in data:
            game_data = dict(data["game_data"])
            return Game.from_document(game_data)
    except Exception as e:
        logging.error(f"Ошибка загрузки {uid}: {e}")
    return None

def save_game(uid: int, game: Game):
    try:
        data = game.to_document()
        players_collection.update_one(
            {"_id": uid},
            {"$set": {"game_data": data}},
            upsert=True
        )
    except Exception as e:
        logging.error(f"Ошибка сохранения {uid}: {e}")

games = {}

ITEM_DESCRIPTIONS = {
    "Спички": "Нужны для розжига и создания факела.",
    "Ветка": "Подходит для крафта простых предметов.",
    "Факел": "Освещает путь и помогает пережить опасные встречи.",
    "Сланцевая пластина": "Ключевой материал для снаряжения у ручья.",
    "Сланевый шлем": "Защищает голову от опасностей локации.",
    "Сланевая броня": "Защищает грудь в путешествии.",
}


def get_inspectable_items(game):
    return [
        item for item, count in game.inventory.items()
        if count > 0 and item in ITEM_DESCRIPTIONS
    ]


def get_usable_items(game):
    return [
        item for item, count in game.inventory.items()
        if count > 0 and (item in ("Еда", "Вода") or "зель" in item.lower())
    ]


def get_callback_answer(callback):
    data = callback.data or ""
    game = games.get(callback.from_user.id)
    if data == "inv_inspect" and (not game or not get_inspectable_items(game)):
        return "У вас нет ключевых предметов для подробного осмотра", True
    if data in ("inv_use", "inv_drop") and (
        not game or not any(count > 0 for count in game.inventory.values())
    ):
        return ("Нечего использовать" if data == "inv_use" else "Нечего выкидывать"), True
    if data == "inv_use" and not get_usable_items(game):
        return "Нечего использовать", True
    return None, False


def use_consumable(item, game):
    """Использовать предмет с учётом динамических коэффициентов."""
    if item == "Вода":
        # Базовая стоимость воды: 1 + запас от голода
        hunger_mult = get_resource_multiplier(game, "hunger")
        water_cost = 1 + max(0, (30 - game.hunger) // 10)
        if game.inventory.get("Вода", 0) < water_cost:
            return f"Нужно воды: {water_cost}. В инвентаре недостаточно воды."
        game.inventory["Вода"] -= water_cost
        if game.inventory["Вода"] <= 0:
            del game.inventory["Вода"]
        # Восстанавливаем жажду с учётом коэффициента голода
        thirst_restore = 10 * get_resource_multiplier(game, "thirst")
        game.thirst = min(100, game.thirst + thirst_restore)
        result = f"Жажда восстановлена на {int(thirst_restore)}. Потрачено воды: {water_cost}."
    elif item == "Еда":
        # Еда восстанавливает голод с учётом коэффициента
        hunger_mult = get_resource_multiplier(game, "hunger")
        game.hunger = min(100, game.hunger + 30 * hunger_mult)
        result = f"Голод утолен ({int(30 * hunger_mult)} ед.)."
    elif "зель" in item.lower():
        game.hp = min(100, game.hp + 25)
        result = "Здоровье восстановлено."
    else:
        return None

    if item != "Вода":
        game.inventory[item] -= 1
        if game.inventory[item] <= 0:
            del game.inventory[item]
    game.add_log(f"Использовано: {item}. {result}")
    return f"Использовано: {item}. {result}\n\n{game.get_ui()}"

# ──────────────────────────────────────────────────────────────────────────────
# ПРИВЕТСТВИЕ
# ──────────────────────────────────────────────────────────────────────────────
GUIDE_TEXT = (
    "Добро пожаловать в лес выживания!\n\n"
    "Краткий гайд:\n"
    "❤️ Здоровье\n"
    "🍖 Сытость\n"
    "💧 Жажда\n"
    "⚡ Действия на день\n\n"
    "Карма поможет выбраться.\n\n"
    "Попробуй выжить, друг мой..."
)

# ──────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ С RETRY ПРИ FLOOD
# ──────────────────────────────────────────────────────────────────────────────
async def safe_delete_message(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest as exc:
        logging.warning(f"Не удалось удалить {message_id}: {exc}")
    except Exception as exc:
        logging.exception(f"Ошибка удаления сообщения {message_id}: {exc}")


async def safe_edit_message(chat_id: int, msg_id: int, text: str, reply_markup=None):
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=reply_markup)
        return True
    except TelegramRetryAfter as exc:
        logging.warning(f"Flood control: ждём {exc.retry_after} сек перед повтором edit")
        try:
            await asyncio.sleep(exc.retry_after + 0.5)
            await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=reply_markup)
            return True
        except TelegramBadRequest as exc2:
            logging.warning(f"Не удалось отредактировать после retry {msg_id}: {exc2}")
            await safe_delete_message(chat_id, msg_id)
            return False
        except Exception as exc2:
            logging.exception(f"Ошибка повторного edit {msg_id}: {exc2}")
            return False
    except TelegramBadRequest as exc:
        logging.warning(f"Не удалось отредактировать {msg_id}: {exc}")
        await safe_delete_message(chat_id, msg_id)
        return False
    except Exception as exc:
        logging.exception(f"Неожиданная ошибка edit {msg_id}: {exc}")
        return False


async def update_or_send_message(chat_id: int, uid: int, text: str, reply_markup=None):
    game = games.get(uid)
    text = format_game_text(text, game)
    msg_id = last_active_msg_id.get(uid)
    if msg_id:
        edited = await safe_edit_message(chat_id, msg_id, text, reply_markup)
        if edited:
            return msg_id
        last_active_msg_id.pop(uid, None)

    try:
        msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
        last_active_msg_id[uid] = msg.message_id
        return msg.message_id
    except TelegramRetryAfter as exc:
        logging.warning(f"Flood control send_message: ждём {exc.retry_after} сек")
        try:
            await asyncio.sleep(exc.retry_after + 0.5)
            msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
            last_active_msg_id[uid] = msg.message_id
            return msg.message_id
        except Exception as exc2:
            logging.exception(f"Ошибка send_message после retry: {exc2}")
            return None
    except TelegramBadRequest as exc:
        logging.warning(f"Не удалось отправить сообщение: {exc}")
        return None
    except Exception as exc:
        logging.exception(f"Неожиданная ошибка send_message: {exc}")
        return None


def format_game_text(text: str, game) -> str:
    """Отформатировать сообщение под выбранный режим экрана игрока."""
    if not game:
        return text

    line_length = game.max_line_length if game.display_mode == "phone" else None
    lines = []
    for line in text.splitlines() or [""]:
        if line_length:
            lines.extend(wrap(line, width=line_length, replace_whitespace=False) or [""])
        else:
            lines.append(line)

    max_lines = game.max_lines_per_msg
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = f"{lines[-1]}\n…"
    return "\n".join(lines)


def get_settings_text(game):
    mode = "📱 Телефон" if game.display_mode == "phone" else "💻 Компьютер"
    return (
        "⚙️ Настройки отображения\n\n"
        f"Режим: {mode}\n"
        f"Длина строки: {game.max_line_length}\n"
        f"Строк на сообщение: {game.max_lines_per_msg}"
    )

# ──────────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    logging.info(f"[START] Получен /start от {uid}")
    try:
        for i in range(1, 50):
            await bot.delete_message(chat_id, message.message_id - i)
    except:
        pass
    loaded = load_game(uid)
    if loaded:
        text = "Вы пришли в себя посреди леса. Вы ничего не помните... В памяти лишь обрывки прошлого."
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Продолжить", callback_data="load_game")],
            [types.InlineKeyboardButton(text="⚠️ Начать сначала", callback_data="confirm_new_game")]
        ])
    else:
        text = GUIDE_TEXT
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🚀 Начать выживание", callback_data="start_new_game")]
        ])
    await message.answer("Нижнее меню включено.", reply_markup=get_bottom_menu())
    await update_or_send_message(chat_id, uid, text, kb)

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    await callback.answer(*get_callback_answer(callback))
    uid = callback.from_user.id
    chat_id = callback.message.chat.id
    try:
        now = time.time()
        if uid in last_request_time and now - last_request_time[uid] < 1.0:
            return
        last_request_time[uid] = now + 0.2
        data = callback.data
        logging.info(f"[CALLBACK] {data} от {uid}")
        game = games.get(uid)
        if data in ("new_game", "start_new_game"):
            game = Game()
            games[uid] = game
            save_game(uid, game)
            text = game.get_ui()
            kb = get_main_kb(game)
            await update_or_send_message(chat_id, uid, text, kb)
            return
        if data == "load_game":
            game = load_game(uid) or Game()
            games[uid] = game
            save_game(uid, game)
            text = game.get_ui()
            kb = get_main_kb(game)
            await update_or_send_message(chat_id, uid, text, kb)
            return
        if data == "confirm_new_game":
            text = "Удалить текущего персонажа и начать новую историю?"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="✅ Да, начать заново", callback_data="start_new_game_confirmed")],
                [types.InlineKeyboardButton(text="❌ Оставить персонажа", callback_data="cancel_new_game")]
            ])
            await update_or_send_message(chat_id, uid, text, kb)
            return
        if data == "start_new_game_confirmed":
            game = Game()
            games[uid] = game
            save_game(uid, game)
            text = game.get_ui()
            kb = get_main_kb(game)
            await update_or_send_message(chat_id, uid, text, kb)
            return
        if data == "cancel_new_game":
            # Возвращаем игрока в главное меню старта
            text = "Вы отменили перезапуск. Что делаем?"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔄 Продолжить", callback_data="load_game")],
                [types.InlineKeyboardButton(text="⚠️ Начать сначала", callback_data="confirm_new_game")]
            ])
            await update_or_send_message(chat_id, uid, text, kb)
            return
        if not game:
            return

        text = None
        kb = None

        if data == "settings_mode_phone":
            game.display_mode = "phone"
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_mode_pc":
            game.display_mode = "pc"
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_length_minus":
            game.max_line_length = max(10, game.max_line_length - 5)
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_length_plus":
            game.max_line_length = min(100, game.max_line_length + 5)
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_height_minus":
            game.max_lines_per_msg = max(3, game.max_lines_per_msg - 1)
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_height_plus":
            game.max_lines_per_msg = min(30, game.max_lines_per_msg + 1)
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_noop":
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "locations_menu":
            game.push_screen("locations")
            text = "Куда направиться?"
            kb = get_locations_kb(game)
        elif data.startswith("trap_place_"):
            location_id = int(data.replace("trap_place_", ""))
            game.traps[location_id] = {
                "location_id": location_id,
                "is_active": True,
                "is_broken": False,
                "placed_day": game.day,
            }
            game.add_log(f"Ловушка установлена в {location_id}-й локации!")
            text = f"Ловушка установлена в {location_id}-й локации!"
            kb = get_main_kb(game)
        elif data.startswith("trap_replace_"):
            location_id = int(data.replace("trap_replace_", ""))
            game.traps[location_id] = {
                "location_id": location_id,
                "is_active": True,
                "is_broken": False,
                "placed_day": game.day,
            }
            game.add_log(f"Новая ловушка установлена в {location_id}-й локации (старая сломана)!")
            text = f"Новая ловушка в {location_id}-й локации!"
            kb = get_main_kb(game)
        elif data == "location_enter_2":
            game.current_location = "Ручей с Змеями"
            text, kb = handle_location_2_ruchey("river_ferocious", game, uid)
        elif data == "location_enter_3":
            game.current_location = "Скромная Лощина"
            text, kb = handle_location_3_slate_hollow("slate_hollow_start", game, uid)
        elif data == "location_enter_4":
            game.current_location = "Просека Охотников"
            text, kb = handle_location_4_hunters_glade("hunters_glade_start", game, uid)
        elif data == "location_enter_5":
            game.current_location = "Яр Слизней"
            text, kb = handle_location_5_slug_pit("slug_pit_start", game, uid)
        elif data == "location_enter_6":
            game.current_location = "Мохнатая Пещера"
            text, kb = handle_location_6_furry_cave("furry_cave_start", game, uid)
        elif data == "location_enter_7":
            game.current_location = "Вершина Святилища"
            text, kb = handle_location_7_sanctuary_peak("sanctuary_peak_start", game, uid)
        elif data == "sanctuary_resolve":
            text, kb = handle_location_7_sanctuary_peak(data, game, uid)
        elif data == "action_2":
            game.push_screen("inventory")
            text = game.get_inventory_text()
            kb = inventory_inline_kb
        elif data == "inv_character":
            game.push_screen("character")
            text = game.get_character_text()
