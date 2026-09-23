import asyncio
import logging
import os
import time
import random
from textwrap import wrap
from pathlib import Path
from aiohttp import web, ClientSession
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
    apply_trap_loot_to_inventory,
    traps_unlocked,
)
from modules.finds import roll_find, apply_finds_to_inventory, location_id_from_game
from modules.cooking import COOKING_RECIPES, cook_item, list_recipes
from modules.items import get_item_effects, is_item_consumable

# Готовка: единый источник — modules/cooking.py (еда.txt). CAMPFIRE_RECIPES удалён.


def format_resource_log_text(deltas: dict) -> str:
    """Собрать строку лога строго по ФАКТИЧЕСКИМ дельтам из consume_action/light_campfire.

    Пример вывода: «Голод -2, Жажда -1» или «Голод -1, HP -3 (голодание)».
    """
    parts = []
    if deltas.get("delta_hunger"):
        parts.append(f"Голод {deltas['delta_hunger']:+d}")
    if deltas.get("delta_thirst"):
        parts.append(f"Жажда {deltas['delta_thirst']:+d}")
    hp_delta = deltas.get("delta_hp", 0)
    if hp_delta:
        hp_reasons = []
        if deltas.get("hunger_damage_to_hp"):
            hp_reasons.append("голодание")
        if deltas.get("thirst_damage_to_hp"):
            hp_reasons.append("обезвоживание")
        reason = f" ({', '.join(hp_reasons)})" if hp_reasons else ""
        parts.append(f"HP {hp_delta:+d}{reason}")
    return ", ".join(parts)


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
    get_drop_quantity_kb,
    get_campfire_kb,
    get_campfire_fuel_kb,
    get_campfire_recipes_kb,
    get_campfire_recipe_kb,
    get_campfire_light_confirm_kb,
    inventory_inline_kb,
    character_inline_kb,
)
from crafts import handle_craft, do_craft, can_craft, craft_mark, CRAFT_RECIPES
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

# Регистрация системных команд Telegram для синей кнопки Menu
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
        self.event_log = ["Ты проснулся в лесу. Что будешь делать?"]
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

    def add_log(self, text, source: str = "game"):
        """Добавить запись в лог событий."""
        self.event_log.append(text)
        # Ограничение длины: 50 записей
        if len(self.event_log) > 50:
            self.event_log = self.event_log[-50:]
        if len(self.event_log) > 50:
            self.event_log = self.event_log[-50:]

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
        pet_name = self.equipment.get("pet") or getattr(self, "companion_name", None) or "Пусто"
        slots = {
            "head": "Голова",
            "torso": "Торс",
            "back": "Спина",
            "pants": "Штаны",
            "boots": "Ботинки",
            "trinket": "Безделушка",
            "pet": "Питомец",
            "hand": "Рука",
        }
        lines = []
        for slot, label in slots.items():
            if slot == "pet":
                lines.append(f"{label}: {pet_name}")
            else:
                lines.append(f"{label}: {self.equipment.get(slot) or 'Пусто'}")
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
        if count > 0 and is_item_consumable(item)
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
    """Использовать предмет с учётом динамических коэффициентов.

    Источник правды по эффектам — modules/items.py (get_item_effects).
    """
    if item == "Вода":
        hunger_mult = get_resource_multiplier(game, "hunger")
        water_cost = 1 + max(0, (30 - game.hunger) // 10)
        if game.inventory.get("Вода", 0) < water_cost:
            return f"Нужно воды: {water_cost}. В инвентаре недостаточно воды."
        game.inventory["Вода"] -= water_cost
        if game.inventory["Вода"] <= 0:
            del game.inventory["Вода"]
        thirst_restore = 10 * get_resource_multiplier(game, "thirst")
        game.thirst = min(100, game.thirst + thirst_restore)
        result = f"Жажда восстановлена на {int(thirst_restore)}. Потрачено воды: {water_cost}."
    else:
        effects = get_item_effects(item)

        if not effects and "зель" in item.lower():
            effects = {"hp": 25}
        if not effects and item == "Еда":
            effects = {"hunger": 30}

        if not effects:
            return None

        restore_parts = []

        if "hunger" in effects:
            hunger_mult = get_resource_multiplier(game, "hunger")
            hunger_val = int(effects["hunger"] * hunger_mult)
            game.hunger = min(100, game.hunger + hunger_val)
            restore_parts.append(f"Голод утолен ({hunger_val} ед.)")

        if "thirst" in effects:
            thirst_mult = get_resource_multiplier(game, "thirst")
            thirst_val = int(effects["thirst"] * thirst_mult)
            game.thirst = min(100, game.thirst + thirst_val)
            restore_parts.append(f"Жажда восстановлена ({thirst_val} ед.)")

        if "hp" in effects:
            hp_val = effects["hp"]
            game.hp = min(100, game.hp + hp_val)
            if hp_val >= 0:
                restore_parts.append(f"Здоровье восстановлено ({hp_val} ед.)")
            else:
                restore_parts.append(f"Получен урон ({abs(hp_val)} ед.)")

        if "poison" in effects and effects["poison"]:
            poison_val = effects["poison"]
            game.hp = max(0, game.hp - poison_val)
            restore_parts.append(f"Отравление ({poison_val} урона)")

        if not restore_parts:
            return None

        result = " ".join(restore_parts)

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
        elif data.startswith("cook_"):
            # Готовка через modules/cooking.py (еда.txt)
            recipe_id = data  # cook_roast_berries и т.п.
            if not game.campfire_active or game.campfire_durability <= 0:
                await callback.answer("🔥 Костёр погас! Разведите его снова.", show_alert=True)
                return
            ok, message = cook_item(game, recipe_id)
            if not ok:
                await callback.answer(message, show_alert=True)
                return
            deltas = game.consume_action(action_type="cook", base_hunger=2, base_thirst=1)
            res_log = format_resource_log_text(deltas)
            if res_log:
                game.add_log(res_log)
            game.campfire_durability = max(0, game.campfire_durability - 1)
            save_game(uid, game)
            text = f"{message}\n(Остаток огня: {game.campfire_durability}/{game.campfire_max_durability})"
            kb = get_campfire_kb(game)
            await safe_edit_message(chat_id, callback.message.message_id, text, kb)
            await callback.answer()
            return
        elif data == "inv_craft":
            game.push_screen("craft")
            unlocked = list(getattr(game, "unlocked_crafts", ["Костёр", "Факел"]) or ["Костёр", "Факел"])
            kb_c = types.InlineKeyboardMarkup(inline_keyboard=[])
            lines = ["🔨 Крафт (только открытые рецепты):", ""]
            for name in unlocked:
                if name not in CRAFT_RECIPES:
                    continue
                mark = craft_mark(game, name)
                ings = ", ".join(f"{n}×{q}" for n, q in CRAFT_RECIPES[name])
                lines.append(f"{name} {mark} — {ings}")
                kb_c.inline_keyboard.append([
                    types.InlineKeyboardButton(
                        text=f"🔨 {name} {mark}",
                        callback_data=f"craft_{name}",
                    )
                ])
            if not kb_c.inline_keyboard:
                lines.append("Пока нечего крафтить.")
            kb_c.inline_keyboard.append([types.InlineKeyboardButton(text="↩️ Назад", callback_data="action_2")])
            text = "\n".join(lines)
            kb = kb_c

        elif data == "campfire_confirm_light":
            if game.inventory.get("Костёр", 0) < 1:
                game.add_log("Нет костра в инвентаре.")
                text = game.get_ui()
                kb = get_main_kb(game)
            elif game.ap < 1:
                game.add_log("Не хватает очков действий, чтобы развести костёр.")
                text = game.get_ui()
                kb = get_main_kb(game)
            else:
                campfire_result = game.light_campfire()
                if not campfire_result.get("lit"):
                    game.add_log("Не удалось развести костёр (не хватает сил).")
                    text = game.get_ui()
                    kb = get_main_kb(game)
                else:
                    game.inventory["Костёр"] -= 1
                    if game.inventory["Костёр"] <= 0:
                        del game.inventory["Костёр"]
                    text = game.get_ui()
                    kb = get_main_kb(game)

        elif data == "inv_recipes":
            unlocked = list(getattr(game, "unlocked_crafts", ["Костёр", "Факел"]) or ["Костёр", "Факел"])
            lines = ["📜 Рецепты:", ""]
            for name in unlocked:
                if name not in CRAFT_RECIPES:
                    lines.append(f"• {name}")
                    continue
                mark = craft_mark(game, name)
                ings = ", ".join(f"{n}×{q}" for n, q in CRAFT_RECIPES[name])
                lines.append(f"• {name} {mark}")
                lines.append(f"  ({ings})")
            text = "\n".join(lines)
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="↩️ Назад", callback_data="action_2")]
            ])

        elif data == "campfire_screen":
            # Экран костра
            max_durability = game.campfire_max_durability
            durability = game.campfire_durability
            text = f"🔥 КОСТЁР\nПрочность пламени: {durability}/{max_durability} делений."
            kb = get_campfire_kb(game)
        elif data == "menu_campfire":
            # Меню костра (основное)
            text = f"🔥 КОСТЁР\nПрочность пламени: {game.campfire_durability}/{game.campfire_max_durability} делений."
            kb = get_campfire_kb(game)
        elif data == "campfire_add_fuel_menu":
            # Подменю выбора дров
            text = "Выберите, сколько дров подкинуть:"
            kb = get_campfire_fuel_kb(game)
        elif data == "campfire_fuel_max":
            # До максимума
            if "Ветка" in game.inventory:
                needed = game.campfire_max_durability - game.campfire_durability
                branches = game.inventory["Ветка"]
                if branches == 0 or needed == 0:
                    text = "Костёр почти полон или веток нет!"
                    kb = types.InlineKeyboardMarkup(inline_keyboard=[
                        [types.InlineKeyboardButton(text="[ ⬅️ Назад в костёр ]", callback_data="menu_campfire")]
                    ])
                else:
                    to_use = min(branches, needed)
                    game.inventory["Ветка"] -= to_use
                    if game.inventory["Ветка"] <= 0:
                        del game.inventory["Ветка"]
                    game.campfire_durability += to_use
                    text = f"🪵 Добавлено веток: {to_use}. Прочность костра: {game.campfire_durability}/{game.campfire_max_durability}."
                    kb = get_campfire_kb(game)
            else:
                text = "Нет веток в инвентаре!"
                kb = types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="[ ⬅️ Назад в костёр ]", callback_data="menu_campfire")]
                ])
        elif data == "campfire_fuel_custom":
            # Своё количество — ждём ввода от пользователя
            text = "Сколько веток подкинуть?"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="[ ⬅️ Назад в костёр ]", callback_data="menu_campfire")]
            ])
        elif data == "campfire_cook_single":
            # Пожарить один предмет — выбираем из инвентаря
            text = "🥩 Что пожарить?"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🍖 Мясо", callback_data="campfire_cook_meat")],
                [types.InlineKeyboardButton(text="🍄 Грибы", callback_data="campfire_cook_mushroom")],
                [types.InlineKeyboardButton(text="🥕 Овощи", callback_data="campfire_cook_veg")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_campfire")],
            ])
        elif data == "campfire_recipes":
            # Список рецептов из modules/cooking.py (еда.txt)
            text = "📜 РЕЦЕПТЫ КОСТРА (кора + теги ягоды/грибы, вода 0–3)"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[])
            for recipe_id, label in list_recipes():
                kb.inline_keyboard.append([
                    types.InlineKeyboardButton(text=label, callback_data=recipe_id)
                ])
            kb.inline_keyboard.append([
                types.InlineKeyboardButton(text="⬅️ Назад в костёр", callback_data="menu_campfire")
            ])
            text += f"\n{len(COOKING_RECIPES)} рецептов."
        elif data.startswith("campfire_recipe_"):
            # Старый callback — перенаправляем на список
            text = "Выберите рецепт из списка."
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="📜 Рецепты", callback_data="campfire_recipes")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_campfire")],
            ])
        elif data.startswith("campfire_ingredient_"):
            # Выбор ингредиента для рецепта
            recipe = data.removeprefix("campfire_ingredient_")
            ingredient = data.removeprefix("campfire_ingredient_").split("_")[-1]
            text = f"Выбираем {ingredient}..."
            kb = get_campfire_recipe_kb(game, recipe)
        elif data == "inv_inspect":
            items = get_inspectable_items(game)
            if not items:
                return
            text = "Подробный осмотр:\n" + "\n".join(
                f"• {item}: {ITEM_DESCRIPTIONS[item]}" for item in items
            )
            kb = inventory_inline_kb

        elif data == "inv_use":
            usable = get_usable_items(game)
            if not usable:
                return
            game.push_screen("use")
            text = "Выберите предмет для использования:"
            kb = get_use_item_kb(game)

        elif data == "inv_drop":
            if not any(count > 0 for count in game.inventory.values()):
                return
            game.push_screen("drop")
            text = "Выберите предмет для удаления:"
            kb = get_drop_item_kb(game)

        elif data.startswith("use_consumable_"):
            item = data.removeprefix("use_consumable_")
            if item == "Костёр":
                if game.inventory.get("Костёр", 0) < 1:
                    game.add_log("Нет костра в инвентаре.")
                    text = game.get_ui()
                    kb = get_main_kb(game)
                else:
                    text = (
                        "Ты складываешь камни и ветки в аккуратную кладку. "
                        "Искра цепляется за мох — и огонь готов родиться. "
                        "В круге света теплее не только телу: даже лес будто "
                        "отступает на шаг. Некоторые звери обойдут стоянку стороной."
                        + "\n\n"
                        + "Затраты: 1 ⚡, голод −7 (с модификаторами), жажда −15 (с модификаторами)."
                        + "\n"
                        + "После розжига откроются рецепты готовки у костра."
                    )
                    kb = get_campfire_light_confirm_kb()
            else:
                result = use_consumable(item, game)
                if result is not None:
                    text = result
                    kb = get_main_kb(game)
        elif data.startswith("drop_item_"):
            item = data.removeprefix("drop_item_")
            if game.inventory.get(item, 0) > 0:
                game.push_screen("drop_qty")
                current_count = game.inventory[item]
                text = f"Сколько выкинуть «{item}»?\nВ инвентаре: {current_count} шт."
                kb = get_drop_quantity_kb(item)

        elif data.startswith("drop_qty:"):
            parts = data.split(":", 2)
            if len(parts) < 3:
                return
            qty_type = parts[1]
            item = parts[2]
            current_count = game.inventory.get(item, 0)
            if current_count <= 0:
                while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
                    game.nav_stack.pop()
                text = f"Предмета «{item}» нет в инвентаре.\n\n{game.get_inventory_text()}"
                kb = inventory_inline_kb
            else:
                drop_count = 0
                if qty_type == "1":
                    drop_count = 1
                elif qty_type == "all":
                    drop_count = current_count
                elif qty_type == "custom":
                    game.story_state = "WAITING_FOR_DROP_QUANTITY"
                    game.story_flags["drop_item_name"] = item
                    text = f"Введите количество «{item}» для выброса:\n(Доступно: {current_count} шт.)"
                    kb = types.InlineKeyboardMarkup(inline_keyboard=[
                        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="drop_qty_cancel")]
                    ])
                    if text is not None:
                        game.record_route(data)
                        await update_or_send_message(chat_id, uid, text, kb)
                        save_game(uid, game)
                    return

                if drop_count > 0:
                    while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
                        game.nav_stack.pop()
                    game.inventory[item] -= drop_count
                    if game.inventory[item] <= 0:
                        del game.inventory[item]
                    game.add_log(f"Выкинуто: {item} ×{drop_count}")
                    text = f"Удалено: {item} ×{drop_count}.\n\n{game.get_inventory_text()}"
                    kb = inventory_inline_kb

        elif data == "drop_qty_cancel":
            game.story_state = None
            if "drop_item_name" in game.story_flags:
                del game.story_flags["drop_item_name"]
            prev = game.pop_screen()
            if prev == "drop_qty":
                prev = game.pop_screen()
            if prev == "drop":
                if any(count > 0 for count in game.inventory.values()):
                    text = "Выберите предмет для удаления:"
                    kb = get_drop_item_kb(game)
                else:
                    text = game.get_inventory_text()
                    kb = inventory_inline_kb
            elif prev == "inventory":
                text = game.get_inventory_text()
                kb = inventory_inline_kb
            else:
                text = game.get_ui()
                kb = get_main_kb(game)

        elif data == "back":
            prev = game.pop_screen()
            if prev == "main":
                text = game.get_ui()
                kb = get_main_kb(game)
            elif prev == "inventory":
                text = game.get_inventory_text()
                kb = inventory_inline_kb
            elif prev == "character":
                text = game.get_character_text()
                kb = character_inline_kb
            elif prev == "drop":
                text = game.get_inventory_text()
                kb = inventory_inline_kb
            elif prev == "drop_qty":
                if any(count > 0 for count in game.inventory.values()):
                    text = "Выберите предмет для удаления:"
                    kb = get_drop_item_kb(game)
                else:
                    text = game.get_inventory_text()
                    kb = inventory_inline_kb
            elif prev == "craft":
                unlocked = list(getattr(game, "unlocked_crafts", ["Костёр", "Факел"]) or ["Костёр", "Факел"])
                kb_c = types.InlineKeyboardMarkup(inline_keyboard=[])
                lines = ["🔨 Крафт:", ""]
                for name in unlocked:
                    if name not in CRAFT_RECIPES:
                        continue
                    mark = craft_mark(game, name)
                    ings = ", ".join(f"{n}×{q}" for n, q in CRAFT_RECIPES[name])
                    lines.append(f"{name} {mark} — {ings}")
                    kb_c.inline_keyboard.append([
                        types.InlineKeyboardButton(
                            text=f"🔨 {name} {mark}",
                            callback_data=f"craft_{name}",
                        )
                    ])
                if not kb_c.inline_keyboard:
                    lines.append("Пока нечего крафтить.")
                kb_c.inline_keyboard.append([
                    types.InlineKeyboardButton(text="↩️ Назад", callback_data="action_2")
                ])
                text = chr(10).join(lines)
                kb = kb_c
            elif prev == "use":
                text = game.get_ui()
                kb = get_main_kb(game)
            elif prev == "settings":
                text = get_settings_text(game)
                kb = get_settings_kb(game)
            else:
                text = game.get_ui()
                kb = get_main_kb(game)

        elif data.startswith("craft_") or data.startswith("use_item_"):
            text, kb = handle_craft(data, game, uid)
            if text is None:
                text = game.get_inventory_text()
                kb = inventory_inline_kb

        elif data.startswith("river_") or data.startswith("snake_") or data.startswith("story_"):
            text, kb = handle_location_2_ruchey(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data.startswith("slate_") or data.startswith("rest_") or data.startswith("examine"):
            text, kb = handle_location_3_slate_hollow(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data.startswith("hunters_") or data.startswith("glade_"):
            text, kb = handle_location_4_hunters_glade(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data.startswith("slug_") or data.startswith("pit_"):
            text, kb = handle_location_5_slug_pit(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data.startswith("furry_") or data.startswith("warm_") or data.startswith("sleep") or data.startswith("cave_"):
            text, kb = handle_location_6_furry_cave(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data.startswith("sanctuary_") and data != "sanctuary_resolve":
            text, kb = handle_location_7_sanctuary_peak(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)

        elif data in ("wolf_leave", "wolf_torch", "peek_den", "pet_leave", "pet_take", "story_next"):
            if game.ap <= 0:
                text = "Нет сил. Нужно поспать."
                kb = get_main_kb(game)
            else:
                text, kb = handle_story(data, game, uid)

        elif data == "action_1":
            if game.ap <= 0:
                ap_warning = "Не хватает очков действий! Нужно поспать (Отдых)."
                game.add_log(ap_warning)
                await callback.answer(ap_warning, show_alert=True)
                text = game.get_ui()
                kb = get_main_kb(game)
                if text is not None:
                    await update_or_send_message(chat_id, uid, text, kb)
                    save_game(uid, game)
                return

            # Центральное списание AP и ресурсов — сначала математика, потом лог по факту
            deltas = game.consume_action(action_type="search", base_hunger=2, base_thirst=1)
            res_log = format_resource_log_text(deltas)
            if res_log:
                game.add_log(res_log)

            # Счётчик исследований с факелом (для Главной Сюжетной Истории)
            torch_research_count = getattr(game, "torch_research_count", 0)

            # Увеличиваем счётчик ТОЛЬКО если факел экипирован
            if game.equipment.get("hand") == "Факел":
                torch_research_count += 1
                game.torch_research_count = torch_research_count

            # На 4-м исследовании с факелом — гарантированно 1-я Сюжетная История
            if torch_research_count >= 4:
                game.add_log(f"{torch_research_count}-е исследование с факелом! Запускаем Главную Сюжетную Историю.")
                text, kb = handle_story(data, game, uid)
            else:
                # Лут по локации (еда.txt → modules/finds.py)
                loc_id = location_id_from_game(game)
                found_list = roll_find(loc_id)
                msg = apply_finds_to_inventory(game, found_list)
                game.add_log(msg)
                text = game.get_ui()
                kb = get_main_kb(game)

        elif data in ("action_sleep", "action_4"):
            game.sleep_and_turn_day()
            trap_msgs = []
            # Утро: 40% ломка / 60% успех + лут по таблице локации (еда.txt)
            for event in process_trap_rollover(game):
                loc_id = event.get("location_id")
                if event.get("broken"):
                    msg = f"Ловушка на локации {loc_id}: сломалась, добычи нет."
                    game.add_log(msg)
                    trap_msgs.append(msg)
                    continue
                animal = event.get("animal")
                loot = event.get("loot") or {}
                if loot:
                    apply_trap_loot_to_inventory(game, loot)
                    loot_txt = ", ".join(f"{k}×{v}" for k, v in loot.items())
                    msg = f"Ловушка на локации {loc_id}: {animal} (+{loot_txt})"
                else:
                    msg = f"Ловушка на локации {loc_id}: {animal}"
                # сброс pending
                trap = getattr(game, "traps", {}).get(loc_id)
                if trap:
                    trap["pending_animal"] = None
                    trap["pending_loot"] = None
                game.add_log(msg)
                trap_msgs.append(msg)
            if trap_msgs:
                text = game.get_ui() + "\n" + "\n".join(trap_msgs)
            else:
                text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "action_3":
            if game.ap <= 0:
                game.add_log("Действия на сегодня закончились.")
            elif game.inventory.get("Вода", 0) > 0:
                game.inventory["Вода"] -= 1
                if game.inventory["Вода"] <= 0:
                    del game.inventory["Вода"]
                game.thirst = min(100, game.thirst + 30)
                game.add_log("Ты сделал глоток воды. Жажда уменьшилась.")
            else:
                game.add_log("Воды больше нет.")
            text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "action_light_campfire":
            campfire_result = game.light_campfire()
            if campfire_result.get("lit"):
                res_log = format_resource_log_text(campfire_result)
                if res_log:
                    game.add_log(res_log)
                text = f"🔥 Вы развели костёр! (Прочность: {game.campfire_durability}/{game.campfire_max_durability})"
                kb = get_campfire_kb(game)
            else:
                text = "Не хватает AP для костра!"
                kb = get_main_kb(game)

        elif data == "action_collect_water":
            if game.weather in {"rain", "storm"} and game.ap > 0:
                game.ap -= 1
                game.inventory["Вода"] = game.inventory.get("Вода", 0) + 1
                game.add_log("Ты набрал дождевой воды!")
                text = "Ты набрал дождевой воды!"
                kb = get_main_kb(game)
            else:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data == "menu_main":
            text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "karma_escape":
            karma_ok = all(v > 0 for v in game.karma.values())
            if karma_ok:
                game.add_log("Карма идеальна — ты сбежал из леса!")
                game.story_state = "karma_escape"
            else:
                game.add_log("Карма не идеальна — остаёшься в лесу.")
                game.story_state = "karma_stuck"
            text = game.get_ui()
            kb = get_main_kb(game)

        if text is not None:
            game.record_route(data)
            await update_or_send_message(chat_id, uid, text, kb)
            save_game(uid, game)
    except Exception as exc:
        logging.exception(f"Ошибка callback {data if 'data' in locals() else 'unknown'} для {uid}: {exc}")

@dp.message(F.text & ~F.text.startswith("/"))
async def process_text_message(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    try:
        raw_text = message.text.strip() if message.text else ""
        text = raw_text[:80] if raw_text else ""
        if text == "🚀 Начать / Старт":
            await cmd_start(message)
            return
        game = games.get(uid) or load_game(uid)
        if not game:
            return

        if text == "📊 Статус":
            games[uid] = game
            await update_or_send_message(chat_id, uid, game.get_ui(), get_main_kb(game))
            return
        if text == "🎒 Инвентарь":
            games[uid] = game
            await update_or_send_message(chat_id, uid, game.get_inventory_text(), inventory_inline_kb)
            return
        if text == "⚙️ Настройки":
            games[uid] = game
            game.push_screen("settings")
            await update_or_send_message(chat_id, uid, get_settings_text(game), get_settings_kb(game))
            save_game(uid, game)
            return

        if game.story_state == "WAITING_FOR_PET_NAME":
            if not text:
                return

            # Удаляем входное сообщение пользователя
            await safe_delete_message(chat_id, message.message_id)

            # Сохраняем имя питомца в форму игры
            game.companion_name = text
            game.equipment["pet"] = text
            game.set_story_flag("saved_kitten")
            game.set_story_flag("has_pet")
            game.karma["gentle"] = game.karma.get("gentle", 0) + 5
            game.adjust_narrative_karma("compassion", 2)
            game.story_state = None
            game.add_log(f"У вас появился питомец: {text} (+5 кармы)")

            # Финальный текст истории
            final_text = (
                "Ты смотришь на маленькое существо у себя на руках.\n"
                f"«{text}», — произносишь ты вслух, и понимаешь что нашёл себе нового друга.\n"
                "Котёнок поднимает голову, будто услышал и запомнил.\n"
                "Уходя от пня, ты чувствуешь, как он начинает тихо, почти не слышно мурчать...\n\n"
                "Вибрация проходит сквозь твою грудь — слабая, но живая.\n"
                "Впервые за долгое время в этом лесу становится чуть теплее."
            )
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="Дальше", callback_data="story_next")]
            ])

            # Правильный путь: редактируем активное сообщение, а не создаём новое
            msg_id = last_active_msg_id.get(uid)
            if msg_id:
                await safe_edit_message(chat_id, msg_id, format_game_text(final_text, game), kb)
            else:
                await update_or_send_message(chat_id, uid, final_text, kb)

            save_game(uid, game)
            return

        if game.story_state == "WAITING_FOR_FUEL_COUNT":
            if not text:
                return

            # Удаляем входное сообщение пользователя
            await safe_delete_message(chat_id, message.message_id)

            # Проверяем, что введён именно положительный int
            try:
                fuel_amount = int(text)
                if fuel_amount <= 0:
                    text = "❌ Введите число больше нуля!"
                    kb = get_campfire_kb(game)
                    msg_id = last_active_msg_id.get(uid)
                    if msg_id:
                        await safe_edit_message(chat_id, msg_id, text, kb)
                    else:
                        await update_or_send_message(chat_id, uid, text, kb)
                    save_game(uid, game)
                    return
            except ValueError:
                # Если текст вместо цифры — возвращаем игрока в костёр
                text = "❌ Введите корректное положительное число!"
                kb = get_campfire_kb(game)
                msg_id = last_active_msg_id.get(uid)
                if msg_id:
                    await safe_edit_message(chat_id, msg_id, text, kb)
                else:
                    await update_or_send_message(chat_id, uid, text, kb)
                save_game(uid, game)
                return

            # Проверяем, есть ли столько веток в инвентаре
            branches = game.inventory.get("Ветка", 0)
            if branches <= 0:
                text = "❌ У вас нет столько веток! Доступно: 0"
                kb = get_campfire_kb(game)
                msg_id = last_active_msg_id.get(uid)
                if msg_id:
                    await safe_edit_message(chat_id, msg_id, text, kb)
                else:
                    await update_or_send_message(chat_id, uid, text, kb)
                save_game(uid, game)
                return

            # Проверяем, не превысил ли пользователь максимум
            needed = game.campfire_max_durability - game.campfire_durability
            if fuel_amount > needed:
                fuel_amount = needed

            # Спиши ветки и пополни прочность
            game.inventory["Ветка"] -= fuel_amount
            if game.inventory["Ветка"] <= 0:
                del game.inventory["Ветка"]
            game.campfire_durability += fuel_amount

            # Сбрасываем состояние ожидания
            game.story_state = None

            # Финальный текст
            text = f"🪵 Добавлено {fuel_amount} ветки. Прочность: {game.campfire_durability}/{game.campfire_max_durability}."
            kb = get_campfire_kb(game)

            # Правильный путь: редактируем активное сообщение, а не создаём новое
            msg_id = last_active_msg_id.get(uid)
            if msg_id:
                await safe_edit_message(chat_id, msg_id, text, kb)
            else:
                await update_or_send_message(chat_id, uid, text, kb)

            save_game(uid, game)
            return

        if game.story_state == "WAITING_FOR_DROP_QUANTITY":
            if not text:
                return

            await safe_delete_message(chat_id, message.message_id)

            item_name = game.story_flags.get("drop_item_name")
            if not item_name:
                game.story_state = None
                while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
                    game.nav_stack.pop()
                text = game.get_inventory_text()
                kb = inventory_inline_kb
                msg_id = last_active_msg_id.get(uid)
                if msg_id:
                    await safe_edit_message(chat_id, msg_id, text, kb)
                else:
                    await update_or_send_message(chat_id, uid, text, kb)
                save_game(uid, game)
                return

            try:
                drop_amount = int(text)
                if drop_amount <= 0:
                    error_text = "❌ Введите число больше нуля!"
                    kb = types.InlineKeyboardMarkup(inline_keyboard=[
                        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="drop_qty_cancel")]
                    ])
                    msg_id = last_active_msg_id.get(uid)
                    current_count = game.inventory.get(item_name, 0)
                    prompt = f"Введите количество «{item_name}» для выброса:\n(Доступно: {current_count} шт.)\n\n{error_text}"
                    if msg_id:
                        await safe_edit_message(chat_id, msg_id, prompt, kb)
                    else:
                        await update_or_send_message(chat_id, uid, prompt, kb)
                    save_game(uid, game)
                    return
            except ValueError:
                error_text = "❌ Введите корректное положительное число!"
                kb = types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="drop_qty_cancel")]
                ])
                msg_id = last_active_msg_id.get(uid)
                current_count = game.inventory.get(item_name, 0)
                prompt = f"Введите количество «{item_name}» для выброса:\n(Доступно: {current_count} шт.)\n\n{error_text}"
                if msg_id:
                    await safe_edit_message(chat_id, msg_id, prompt, kb)
                else:
                    await update_or_send_message(chat_id, uid, prompt, kb)
                save_game(uid, game)
                return

            current_count = game.inventory.get(item_name, 0)
            if current_count <= 0:
                game.story_state = None
                if "drop_item_name" in game.story_flags:
                    del game.story_flags["drop_item_name"]
                while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
                    game.nav_stack.pop()
                result_text = f"❌ У вас нет «{item_name}» в инвентаре!\n\n{game.get_inventory_text()}"
                kb = inventory_inline_kb
                msg_id = last_active_msg_id.get(uid)
                if msg_id:
                    await safe_edit_message(chat_id, msg_id, result_text, kb)
                else:
                    await update_or_send_message(chat_id, uid, result_text, kb)
                save_game(uid, game)
                return

            if drop_amount > current_count:
                drop_amount = current_count

            while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
                game.nav_stack.pop()
            game.inventory[item_name] -= drop_amount
            if game.inventory[item_name] <= 0:
                del game.inventory[item_name]
            game.add_log(f"Выкинуто: {item_name} ×{drop_amount}")

            game.story_state = None
            if "drop_item_name" in game.story_flags:
                del game.story_flags["drop_item_name"]

            result_text = f"Удалено: {item_name} ×{drop_amount}.\n\n{game.get_inventory_text()}"
            kb = inventory_inline_kb

            msg_id = last_active_msg_id.get(uid)
            if msg_id:
                await safe_edit_message(chat_id, msg_id, result_text, kb)
            else:
                await update_or_send_message(chat_id, uid, result_text, kb)

            save_game(uid, game)
            return
    except Exception as exc:
        logging.exception(f"Ошибка process_text_message для {uid}: {exc}")
        try:
            await message.answer("Я не смог обработать это сообщение. Попробуйте ещё раз.")
        except Exception as e:
            pass

# ЖЁСТКО ЗАФИКСИРОВАННЫЕ ССЫЛКИ ДЛЯ ПИНГА (НЕ УДАЛЯТЬ И НЕ СОКРАЩАТЬ)
PING_URLS = [
    "https://lessurvivalbot-5u4p.onrender.com",
    "https://lessurvivalbot.onrender.com"
]

async def keep_alive_pinger(interval_seconds: int = 300):
    """
    КРИТИЧЕСКАЯ ФУНКЦИЯ: Отправляет HTTP GET запросы каждые 5 минут на оба сервиса Render,
    чтобы предотвратить их уход в спящий режим.
    """
    await asyncio.sleep(15)  # Пауза перед первым запуском после старта бота
    async with ClientSession() as session:
        while True:
            for url in PING_URLS:
                try:
                    async with session.get(url, timeout=10) as response:
                        logging.info(f"[Keep-Alive] Пинг {url} -> Статус: {response.status}")
                except Exception as e:
                    logging.warning(f"[Keep-Alive] Ошибка при пинге {url}: {e}")
            await asyncio.sleep(interval_seconds)

async def handle_health_check(request):
    return web.Response(text="OK")

async def start_health_check_server():
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def run_bot():
    """Запустить polling и гарантированно закрыть внешние ресурсы при остановке."""
    await start_health_check_server()
    
    # Запуск пинга в отдельном task — чтобы не мешал запуску бота
    pinger_task = asyncio.create_task(keep_alive_pinger(300))
    
    try:
        # Даем серверу "отдохнуть" перед установкой команд
        logging.info("Сервер запущен — даем ему 10 секунд на 'разогрев'...")
        await asyncio.sleep(10)
        logging.info("Запускаем команды бота...")
        # Обертываем команды в try/except — aiogram может ронять Unauthorized на уже запущонном боте
        try:
            await bot.set_my_commands([
                types.BotCommand(command="start", description="Начать выживание"),
                types.BotCommand(command="inventory", description="Инвентарь"),
                types.BotCommand(command="status", description="Статус"),
                types.BotCommand(command="settings", description="Настройки"),
            ])
            await bot.delete_webhook(drop_pending_updates=False)
            logging.info("Команды установлены — запускаем polling...")
            await dp.start_polling(bot)
        except Exception as cmd_err:
            logging.error(f"Ошибка при настройке команд: {cmd_err}")
            # Продолжаем polling — он сам обработает команды
            await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка в основном потоке бота: {e}")
        # Перезапускаем пинг, если бот упал
        if pinger_task.done() and not pinger_task.cancelled():
            logging.warning("Пингер завершил работу — перезапускаем его...")
            pinger_task = asyncio.create_task(keep_alive_pinger(300))
    finally:
        if mongo_client is not None:
            mongo_client.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(run_bot())