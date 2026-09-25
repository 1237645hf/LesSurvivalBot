import asyncio
import logging
import os
import time
import random
from textwrap import wrap
from pathlib import Path
from aiohttp import web, ClientSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from pymongo import MongoClient

from game_math import (
    process_damage,
    get_resource_multiplier,
    get_base_resource_cost,
    get_thirst_base_cost,
    calculate_ap_by_hp,
)
from game_state import GameState, Game
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
from modules.cooking import COOKING_RECIPES, cook_item, list_recipes, format_recipe_card
from modules.items import (
    get_item_effects,
    get_item_negative_effects,
    is_item_consumable,
    format_item_card,
    get_item_rank_marker,
    get_item_display_name,
)

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


# Предметы, для которых при находке назначается случайное количество (1-3)
_STICK_ITEMS = {"Ветка", "Палка", "Палки"}


def _randomize_stick_count(found_list: list) -> list:
    """Увеличить количество веток/палок в результате roll_find до случайного 1-3.

    Остальные предметы остаются с количеством 1 (как всегда).
    Возвращает новый список с дублированными записями (каждая запись = 1 предмет).
    """
    result = []
    for item in found_list:
        if item in _STICK_ITEMS:
            count = random.randint(1, 3)
            result.extend([item] * count)
        else:
            result.append(item)
    return result




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
    get_use_item_kb,
    get_drop_item_kb,
    get_drop_quantity_kb,
    get_campfire_kb,
    get_campfire_fuel_kb,
    get_campfire_recipes_kb,
    get_campfire_recipe_kb,
    get_campfire_light_confirm_kb,
    get_bottle_actions_kb,
    get_inspect_menu_kb,
    get_item_card_actions_kb,
    get_campfire_recipe_view_kb,
    get_inventory_kb,
    inventory_inline_kb,
    character_inline_kb,
)
from crafts import (
    handle_craft,
    do_craft,
    can_craft,
    craft_mark,
    CRAFT_RECIPES,
    get_craft_menu_text,
    get_craft_menu_kb,
)
from story.location_stories import (
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
# БАЗА ДАННЫХ
# ──────────────────────────────────────────────────────────────────────────────
from services.database import (
    players_collection,
    load_game,
    save_game,
    games,
    MemoryPlayersCollection,
)


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

        # Проверка негативных эффектов (расстройство желудка, токсины, паразиты)
        neg = get_item_negative_effects(item)
        if neg:
            chance = int(neg.get("chance", 0))
            if random.randint(1, 100) <= chance:
                neg_effects = neg.get("effects", {})
                if "thirst" in neg_effects:
                    game.thirst = max(0, game.thirst + neg_effects["thirst"])
                if "hp" in neg_effects:
                    game.hp = max(1, game.hp + neg_effects["hp"])
                msg = neg.get("log_message") or neg.get("description")
                restore_parts.append(f"⚠️ {msg}")

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


def format_game_text(text: str, game=None) -> str:
    """Полный текст сообщения без обрезки и искажения строк."""
    return text


def get_settings_text(game=None):
    return (
        "⚙️ **Настройки**\n\n"
        "Интерфейс игры работает в стандартном полноразмерном режиме Telegram.\n"
        "Обрезка сообщений отключена для сохранения всех слотов и описаний."
    )


def get_campfire_text(game=None) -> str:
    """Формирует живое описание костра без бюрократических делений."""
    durability = int(getattr(game, "campfire_durability", 0) or 0)
    max_d = int(getattr(game, "campfire_max_durability", 10) or 10)
    ratio = durability / max_d if max_d > 0 else 0

    if ratio >= 0.8:
        narrative = "Костёр ярко пылает и озаряет лагерь. Жаркие угли согревают всё вокруг, треск сучьев отгоняет лесную тьму."
    elif ratio >= 0.5:
        narrative = "Костёр уверенно потрескивает, ровное пламя дарит тепло и уют. Огонь стабилен, но со временем потребует дров."
    elif ratio >= 0.3:
        narrative = "Пламя заметно ослабло, костёр начинает угасать. Дым стелется по земле, пора подбросить веток."
    elif durability > 0:
        narrative = "Костёр едва тлеет, остались лишь тусклые угли. Ещё немного — и лагерь погрузится в ледяной мрак."
    else:
        narrative = "Костёр потух. Вокруг лишь холодный пепел."

    return (
        f"🔥 КОСТЁР\n\n"
        f"{narrative}\n\n"
        f"Огонь: {durability}/{max_d}"
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
    # Нижняя Reply-клавиатура полностью отключена — сбрасываем кэш у клиента
    try:
        await message.answer("🌲 LesSurvivalBot", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await update_or_send_message(chat_id, uid, text, kb)


def _ensure_game(uid: int):
    """Достать игру из памяти или Mongo."""
    game = games.get(uid)
    if game is None:
        game = load_game(uid)
        if game is not None:
            games[uid] = game
    return game


@dp.message(Command("main", "menu", "home"))
async def cmd_main(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    try:
        await message.delete()
    except Exception:
        pass
    game = _ensure_game(uid)
    if not game:
        await message.answer("Сначала /start")
        return
    game.nav_stack = ["main"]
    await update_or_send_message(chat_id, uid, game.get_ui(), get_main_kb(game))
    save_game(uid, game)



@dp.message(Command("inventory", "inv"))
async def cmd_inventory(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    # P8: удаляем сообщение игрока с командой
    try:
        await message.delete()
    except Exception:
        pass
    game = _ensure_game(uid)
    if not game:
        await message.answer("Сначала /start")
        return
    game.push_screen("inventory")
    await update_or_send_message(chat_id, uid, game.get_inventory_text(), inventory_inline_kb)
    save_game(uid, game)



@dp.message(Command("character", "char", "hero"))
async def cmd_character(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    try:
        await message.delete()
    except Exception:
        pass
    game = _ensure_game(uid)
    if not game:
        await message.answer("Сначала /start")
        return
    game.push_screen("character")
    await update_or_send_message(chat_id, uid, game.get_character_text(), character_inline_kb)
    save_game(uid, game)


@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    try:
        await message.delete()
    except Exception:
        pass
    game = _ensure_game(uid)
    if not game:
        await message.answer("Сначала /start")
        return
    game.push_screen("settings")

    await update_or_send_message(chat_id, uid, get_settings_text(game), get_settings_kb(game))
    save_game(uid, game)

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    chat_id = callback.message.chat.id
    data = callback.data or ""
    try:
        now = time.time()
        last = last_request_time.get(uid, 0)
        if now - last < 0.35:
            await callback.answer()
            return
        last_request_time[uid] = now

        ans = get_callback_answer(callback)
        if ans and ans[0]:
            await callback.answer(str(ans[0]), show_alert=bool(ans[1]) if len(ans) > 1 else False)
        else:
            await callback.answer()

        logging.info(f"[CALLBACK] {data} от {uid}")
        game = games.get(uid)
        if game is None:
            game = load_game(uid)
            if game is not None:
                games[uid] = game
        if data in ("new_game", "start_new_game"):
            game = Game()
            games[uid] = game
            game.story_state = "WAITING_FOR_CHARACTER_NAME"
            save_game(uid, game)
            text = (
                "📛 Введи имя своего персонажа:\n"
                "• Только буквы, цифры, _\n"
                "• Пробелы запрещены (используй _ вместо пробела)\n"
                "• Эмодзи запрещены\n"
                "• Макс. 20 символов"
            )
            await update_or_send_message(chat_id, uid, text, None)
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
            game.story_state = "WAITING_FOR_CHARACTER_NAME"
            save_game(uid, game)
            text = (
                "📛 Введи имя своего персонажа:\n"
                "• Только буквы, цифры, _\n"
                "• Пробелы запрещены (используй _ вместо пробела)\n"
                "• Эмодзи запрещены\n"
                "• Макс. 20 символов"
            )
            await update_or_send_message(chat_id, uid, text, None)
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

        if game is None:
            await update_or_send_message(
                chat_id,
                uid,
                "Сессия не найдена. Нажми /start",
                types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="🚀 Начать выживание", callback_data="start_new_game")]
                ]),
            )
            return

        text = None
        kb = None

        if data == "locations_menu":
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
            kb = character_inline_kb

        elif data.startswith("cook_exec_") or (data.startswith("cook_") and not data.startswith("cook_recipe_view_")):
            # Непосредственное приготовление блюда на костре
            recipe_id = data.removeprefix("cook_exec_")
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
            if game.campfire_durability <= 0:
                game.campfire_active = False
                game.add_log("Костёр потух после готовки.")
            save_game(uid, game)
            while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("recipe_card", "campfire_recipes"):
                game.nav_stack.pop()
            text = f"{message}\n\n{get_campfire_text(game)}"
            kb = get_campfire_kb(game)
            await safe_edit_message(chat_id, callback.message.message_id, text, kb)
            await callback.answer()
            return
        elif data.startswith("cook_recipe_view_"):
            # Карточка рецепта костра перед готовкой
            recipe_id = data.removeprefix("cook_recipe_view_")
            game.push_screen("recipe_card")
            text = format_recipe_card(recipe_id)
            kb = get_campfire_recipe_view_kb(recipe_id)
            await safe_edit_message(chat_id, callback.message.message_id, text, kb)
            await callback.answer()
            return
        elif data == "inv_craft":
            game.push_screen("craft")
            text = get_craft_menu_text(game)
            kb = get_craft_menu_kb(game)

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
                    game.add_log("🔥 Костёр успешно разведён (10/10)! Кнопка костра теперь доступна на главном экране.")
                    text = game.get_ui()
                    kb = get_main_kb(game)

        elif data == "inv_recipes":
            game.push_screen("recipes")
            text = get_craft_menu_text(game)
            kb = get_craft_menu_kb(game)

        elif data in ("campfire_screen", "menu_campfire"):
            # Меню костра (основное)
            game.push_screen("campfire")
            text = get_campfire_text(game)
            kb = get_campfire_kb(game)
        elif data == "campfire_add_fuel_menu":
            # Подменю выбора топлива (Ветки, Палки, Кусок коры)
            inv = getattr(game, "inventory", {}) or {}
            has_branches = (inv.get("Ветка", 0) + inv.get("Палки", 0) + inv.get("Палка", 0)) > 0
            has_bark = inv.get("Кусок коры", 0) > 0
            if not has_branches and not has_bark:
                text = "❌ В инвентаре нет подходящего топлива!\nНужны ветки/палки или кусок коры."
                kb = types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="⬅️ Назад в костёр", callback_data="menu_campfire")]
                ])
            else:
                cur_d = getattr(game, "campfire_durability", 0)
                max_d = getattr(game, "campfire_max_durability", 10)
                text = f"🔥 КОСТЁР ({cur_d}/{max_d})\nВыберите топливо для поддержания огня:"
                kb = get_campfire_fuel_kb(game)

        elif data.startswith("feed_fuel:"):
            # feed_fuel:<item_name>:<1|max>
            parts = data.split(":", 2)
            if len(parts) >= 3:
                fuel_item = parts[1]
                feed_mode = parts[2]
                inv = getattr(game, "inventory", {}) or {}
                avail = inv.get(fuel_item, 0)
                needed = game.campfire_max_durability - game.campfire_durability

                if not game.campfire_active or game.campfire_durability <= 0:
                    await callback.answer("🔥 Костёр уже погас! Разведите его заново.", show_alert=True)
                    text = game.get_ui()
                    kb = get_main_kb(game)
                elif needed <= 0:
                    await callback.answer(f"🔥 Костёр уже разгорелся до максимума ({game.campfire_max_durability}/{game.campfire_max_durability})!", show_alert=True)
                    text = get_campfire_text(game)
                    kb = get_campfire_kb(game)
                elif avail <= 0:
                    await callback.answer(f"❌ «{fuel_item}» закончился в инвентаре!", show_alert=True)
                    text = get_campfire_text(game)
                    kb = get_campfire_kb(game)
                else:
                    to_use = 1 if feed_mode == "1" else min(avail, needed)
                    inv[fuel_item] -= to_use
                    if inv[fuel_item] <= 0:
                        del inv[fuel_item]
                    game.campfire_durability += to_use
                    game.add_log(f"🪵 Подкинуто: {fuel_item} ×{to_use}. Огонь: {game.campfire_durability}/{game.campfire_max_durability}.")
                    text = f"Подкинуто {fuel_item} ×{to_use}.\n\n{get_campfire_text(game)}"
                    kb = get_campfire_kb(game)

        elif data == "campfire_recipes":
            game.push_screen("campfire_recipes")
            from modules.cooking import COOKING_RECIPES, can_cook
            available_count = sum(1 for r_id in COOKING_RECIPES if can_cook(game, r_id))
            if available_count > 0:
                text = "📜 Рецепты костра\n\nВыберите блюдо, чтобы узнать ингредиенты и приготовить:"
            else:
                text = "📜 Рецепты костра\n\nСейчас у вас недостаточно ингредиентов ни для одного блюда.\nНайдите ягоды, грибы, мясо, воду или кусок коры."
            kb = get_campfire_recipes_kb(game)
        elif data == "inv_inspect":
            items_in_inv = [item for item, c in game.inventory.items() if c > 0]
            if not items_in_inv:
                await callback.answer("Инвентарь пуст!", show_alert=True)
                return
            game.push_screen("inspect")
            text = "🔍 Подробный осмотр предметов\n\nВыберите предмет из инвентаря, чтобы изучить его описание, эффекты и свойства:"
            kb = get_inspect_menu_kb(game)

        elif data.startswith("inspect_item_"):
            item = data.removeprefix("inspect_item_")
            game.push_screen("item_card")
            text = format_item_card(item)
            kb = get_item_card_actions_kb(item, game)

        elif data.startswith("use_preview_"):
            item = data.removeprefix("use_preview_")
            game.push_screen("item_card")
            text = format_item_card(item)
            kb = get_item_card_actions_kb(item, game)

        elif data == "inv_use":
            # Перенаправляем устаревший inv_use в подробный осмотр
            items_in_inv = [item for item, c in game.inventory.items() if c > 0]
            if not items_in_inv:
                await callback.answer("Инвентарь пуст!", show_alert=True)
                return
            game.push_screen("inspect")
            text = "🔍 Подробный осмотр предметов\n\nВыберите предмет из инвентаря, чтобы изучить его описание, эффекты и свойства:"
            kb = get_inspect_menu_kb(game)

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
                    has_torch = (
                        game.equipment.get("hand_left") == "Факел"
                        or game.equipment.get("hand") == "Факел"
                    )
                    has_matches = game.inventory.get("Спички", 0) > 0
                    min_ap = 1 if (has_torch or has_matches) else 2

                    if game.ap < min_ap:
                        game.add_log(f"Не хватает очков действий для розжига костра (требуется {min_ap} ⚡).")
                        text = game.get_ui()
                        kb = get_main_kb(game)
                    else:
                        if has_torch:
                            cost_text = "🔥 Источник огня: горящий факел в руке!\nЗатраты: 1 ⚡ AP. Спички, сытость и жажда НЕ тратятся."
                        elif has_matches:
                            cost_text = "🪵 Источник огня: спички из инвентаря.\nЗатраты: 1 спичка, 1 ⚡ AP. Сытость и жажда НЕ тратятся."
                        else:
                            cost_text = "⏳ Спичек и факела нет — розжиг трением вручную.\nЗатраты: 2 ⚡ AP, голод −7, жажда −18 (тяжёлые усилия)."

                        text = (
                            "Ты складываешь камни и ветки в аккуратную кладку.\n"
                            "В круге света теплее не только телу: даже лес будто отступает на шаг.\n\n"
                            f"{cost_text}\n\n"
                            "После розжига на главном экране появится костёр (10/10) и откроются рецепты готовки."
                        )
                        kb = get_campfire_light_confirm_kb()
            elif item == "Бутылка воды":
                text = (
                    "🧴 Бутылка чистой воды (20 глотков).\n\n"
                    "Ты можешь надеть её на пояс (в слот фляги), чтобы кнопка «💧 Пить» появилась на главном экране, либо сделать один глоток прямо сейчас."
                )
                kb = get_bottle_actions_kb()
            else:
                result = use_consumable(item, game)
                if result is not None:
                    text = result
                    kb = get_main_kb(game)

        elif data == "equip_bottle_flask":
            if game.inventory.get("Бутылка воды", 0) > 0:
                game.inventory["Бутылка воды"] -= 1
                if game.inventory["Бутылка воды"] <= 0:
                    del game.inventory["Бутылка воды"]
                game.equipment["flask"] = "Бутылка воды"
                game.flask_water = 20
                game.add_log("🧴 Бутылка воды экипирована в слот фляги (20/20). Теперь кнопка «Пить» доступна на главном экране!")
            else:
                game.add_log("В инвентаре нет бутылки воды.")
            text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "drink_bottle_single":
            if game.equipment.get("flask") and getattr(game, "flask_water", 0) > 0:
                game.flask_water -= 1
                game.thirst = min(100, game.thirst + 30)
                game.add_log(f"💧 Ты сделал глоток воды (+15 жажды). Во фляге: {game.flask_water}/20.")
                if game.flask_water <= 0:
                    container_name = game.equipment.get("flask") or "Бутылка воды"
                    game.equipment["flask"] = None
                    game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1
                    game.add_log(f"Ёмкость «{container_name}» опустошена! В инвентаре осталась пустая бутылка.")
            elif game.inventory.get("Бутылка воды", 0) > 0:
                game.inventory["Бутылка воды"] -= 1
                if game.inventory["Бутылка воды"] <= 0:
                    del game.inventory["Бутылка воды"]
                game.equipment["flask"] = "Бутылка воды"
                game.flask_water = 19
                game.thirst = min(100, game.thirst + 30)
                game.add_log("🧴 Ты экипировал бутылку на пояс и сделал глоток (+15 жажды). Во фляге: 19/20.")
            else:
                game.add_log("Нет доступной воды для питья.")
            text = game.get_ui()
            kb = get_main_kb(game)
        elif data.startswith("drop_item_"):
            item = data.removeprefix("drop_item_")
            if game.inventory.get(item, 0) > 0:
                game.push_screen("drop_qty")
                current_count = game.inventory[item]
                game.story_state = "WAITING_FOR_DROP_QUANTITY"
                game.story_flags["drop_item_name"] = item
                from modules.items import get_item_description
                desc = get_item_description(item)
                text = (
                    f"🗑 {item} (в наличии: {current_count} шт.)\n\n"
                    f"{desc}\n\n"
                    f"Введите свое число в чат чтобы выбросить или выберите вариант:"
                )
                kb = get_drop_quantity_kb(item)

        elif data.startswith("drop_qty:"):
            parts = data.split(":", 2)
            if len(parts) < 3:
                return
            qty_type = parts[1]
            item = parts[2]
            game.story_state = None
            game.story_flags.pop("drop_item_name", None)
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

                if drop_count > 0:
                    while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
                        game.nav_stack.pop()
                    game.inventory[item] -= drop_count
                    if game.inventory[item] <= 0:
                        del game.inventory[item]
                    game.add_log(f"Выкинуто: {item} ×{drop_count}")
                    text = f"Удалено: {item} ×{drop_count}.\n\n{game.get_inventory_text()}"
                    kb = get_inventory_kb(game, 0)

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
                    kb = get_inventory_kb(game, 0)
            elif prev == "inventory":
                text = game.get_inventory_text()
                kb = get_inventory_kb(game, 0)
            else:
                text = game.get_ui()
                kb = get_main_kb(game)

        elif data == "back":
            game.story_state = None
            if "drop_item_name" in game.story_flags:
                del game.story_flags["drop_item_name"]
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
            elif prev in ("craft", "recipes"):
                text = get_craft_menu_text(game)
                kb = get_craft_menu_kb(game)
            elif prev == "inspect":
                items_in_inv = [item for item, c in game.inventory.items() if c > 0]
                if items_in_inv:
                    text = "🔍 Подробный осмотр предметов\n\nВыберите предмет из инвентаря, чтобы изучить его описание, эффекты и свойства:"
                    kb = get_inspect_menu_kb(game)
                else:
                    text = game.get_inventory_text()
                    kb = inventory_inline_kb
            elif prev == "drop":
                if any(count > 0 for count in game.inventory.values()):
                    text = "Выберите предмет для удаления:"
                    kb = get_drop_item_kb(game)
                else:
                    text = game.get_inventory_text()
                    kb = inventory_inline_kb
            elif prev in ("drop_qty", "use"):
                text = game.get_inventory_text()
                kb = inventory_inline_kb
            elif prev == "campfire":
                text = get_campfire_text(game)
                kb = get_campfire_kb(game)
            elif prev == "campfire_recipes":
                from modules.cooking import COOKING_RECIPES, can_cook
                available_count = sum(1 for r_id in COOKING_RECIPES if can_cook(game, r_id))
                if available_count > 0:
                    text = "📜 Рецепты костра\n\nВыберите блюдо, чтобы узнать ингредиенты и приготовить:"
                else:
                    text = "📜 Рецепты костра\n\nСейчас у вас недостаточно ингредиентов ни для одного блюда.\nНайдите ягоды, грибы, мясо, воду или кусок коры."
                kb = get_campfire_recipes_kb(game)
            elif prev == "campfire_fuel":
                cur_d = getattr(game, "campfire_durability", 0)
                max_d = getattr(game, "campfire_max_durability", 10)
                text = f"🔥 КОСТЁР ({cur_d}/{max_d})\nВыберите топливо для поддержания огня:"
                kb = get_campfire_fuel_kb(game)
            elif prev == "locations":
                text = "Куда направиться?"
                kb = get_locations_kb(game)
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

            deltas = game.consume_action(action_type="search", base_hunger=2, base_thirst=1)
            res_log = format_resource_log_text(deltas)
            if res_log:
                game.add_log(res_log)

            # Счётчик исследований с факелом (факел только в левой руке)
            torch_equipped = (
                game.equipment.get("hand_left") == "Факел"
                or game.equipment.get("hand") == "Факел"
            )
            if torch_equipped:
                torch_research_count = getattr(game, "torch_research_count", 0) + 1
                game.torch_research_count = torch_research_count

                # На 4-м исследовании с факелом — запускаем сюжет L1
                if torch_research_count >= 4:
                    game.add_log(f"🔦 {torch_research_count}-е исследование с факелом! Что-то происходит...")
                    text, kb = handle_story(data, game, uid)
                else:
                    # С факелом лут идёт так же, как без него — обычный roll_find
                    loc_id = location_id_from_game(game)
                    found_list = roll_find(loc_id)
                    msg = apply_finds_to_inventory(game, found_list)
                    game.add_log(f"🔦 {msg}")
                    text = game.get_ui()
                    kb = get_main_kb(game)
            else:
                # Без факела — обычный roll_find по локации
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
                    game.add_log(msg)
                    trap_msgs.append(msg)
                elif animal:
                    msg = f"Ловушка на локации {loc_id}: {animal}"
                    game.add_log(msg)
                    trap_msgs.append(msg)
                trap = getattr(game, "traps", {}).get(loc_id)
                if trap:
                    trap["pending_animal"] = None
                    trap["pending_loot"] = None
            if trap_msgs:
                text = game.get_ui() + "\n" + "\n".join(trap_msgs)
            else:
                text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "action_3":
            # Пить из экипированной бутылки/фляги
            if game.equipment.get("flask"):
                water_left = int(getattr(game, "flask_water", 0) or 0)
                if water_left > 0:
                    game.flask_water = water_left - 1
                    game.thirst = min(100, game.thirst + 15)
                    game.add_log(f"💧 Ты сделал глоток воды из бутылки (+15 жажды). Во фляге: {game.flask_water}/20.")
                    if game.flask_water <= 0:
                        container_name = game.equipment.get("flask") or "Бутылка воды"
                        game.equipment["flask"] = None
                        game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1
                        game.add_log(f"Ёмкость «{container_name}» опустошена! В инвентаре осталась пустая бутылка.")
                else:
                    container_name = game.equipment.get("flask") or "Бутылка воды"
                    game.equipment["flask"] = None
                    game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1
                    game.add_log(f"Ёмкость «{container_name}» опустошена! В инвентаре осталась пустая бутылка.")
            elif game.inventory.get("Бутылка воды", 0) > 0:
                game.add_log("Бутылка в инвентаре не надета! Перейди в инвентарь и нажми «Бутылка воды» -> «Надеть на пояс».")
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
        try:
            await callback.answer("Ошибка обработки кнопки. Попробуй ещё раз или /start", show_alert=True)
        except Exception as e:
            pass

@dp.message(F.text & ~F.text.startswith("/"))
async def process_text_message(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    try:
        raw_text = message.text.strip() if message.text else ""
        text = raw_text[:80] if raw_text else ""
        # Если пришло сообщение от старой кэшированной Reply-панели — принудительно удаляем её у клиента
        old_reply_buttons = (
            "🚀 Начать / Старт", "🏠 Главное меню / Перезапуск", "🏠 Главное меню",
            "📊 Статус", "🏠 Главный экран", "🎒 Инвентарь", "👤 Персонаж", "⚙️ Настройки"
        )
        if text in old_reply_buttons:
            try:
                await message.answer("Нижняя панель отключена. Управление ведётся через кнопки сообщений.", reply_markup=ReplyKeyboardRemove())
            except Exception:
                pass
            if text in ("🚀 Начать / Старт", "🏠 Главное меню / Перезапуск", "🏠 Главное меню"):
                await cmd_start(message)
                return
            if text in ("📊 Статус", "🏠 Главный экран"):
                await cmd_main(message)
                return
            if text in ("🎒 Инвентарь",):
                await cmd_inventory(message)
                return
            if text in ("👤 Персонаж",):
                await cmd_character(message)
                return
            if text in ("⚙️ Настройки",):
                await cmd_settings(message)
                return

        game = _ensure_game(uid)
        if not game:
            return

        # Делегируем диалоговые FSM-состояния в services/dialogs.py
        from services.dialogs import process_text_input
        bot_ctx = {
            "last_active_msg_id": last_active_msg_id,
            "safe_edit_message": safe_edit_message,
            "safe_delete_message": safe_delete_message,
            "update_or_send_message": update_or_send_message,
            "format_game_text": format_game_text,
            "inventory_inline_kb": inventory_inline_kb,
            "get_campfire_kb": get_campfire_kb,
        }
        await process_text_input(uid, chat_id, text, message, game, bot_ctx)

    except Exception as exc:
        logging.exception(f"Ошибка process_text_message для {uid}: {exc}")
        try:
            await message.answer("Я не смог обработать это сообщение. Попробуйте ещё раз.")
        except Exception as e:
            pass



# ──────────────────────────────────────────────────────────────────────────────
# РЎР•Р Р’Р•Р  Р РџРРќР“
# ──────────────────────────────────────────────────────────────────────────────
from services.server import keep_alive_pinger, start_health_check_server, PING_URLS


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
                types.BotCommand(command="main", description="Главный экран"),
                types.BotCommand(command="inventory", description="Инвентарь"),
                types.BotCommand(command="character", description="Персонаж"),
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
        from services.database import mongo_client
        if mongo_client is not None:
            mongo_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_bot())

