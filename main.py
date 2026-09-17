import asyncio
import logging
import os
import time
import random
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from pymongo import MongoClient


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

from keyboards import get_main_kb, get_locations_kb, inventory_inline_kb, character_inline_kb
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
from game_state import GameState

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
            "Спички 🔥": 1,
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
        weather_icon = {"clear": "☀️", "cloudy": "☁️", "rain": "🌧️"}.get(self.weather, "☀️")
        return (
            f"❤️ {self.hp} | 🍖 {self.hunger} | 💧 {self.thirst} | ⚡ {self.ap} | {weather_icon} День: {self.day}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(f"> {line}" for line in self.log) + "\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

    def get_inventory_text(self):
        lines = []
        equipped_hand = self.equipment.get("hand")
        for item, count in self.inventory.items():
            if count > 0:
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
            inventory = game_data.get("inventory", {})
            normalized_inventory = {}
            for key, value in inventory.items():
                canonical = key.replace("Спички ", "Спички 🔥").replace("Бутылка воды", "Вода")
                normalized_inventory[canonical] = value
            game_data["inventory"] = normalized_inventory
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
        text = "Есть сохранение. Что делаем?"
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Продолжить", callback_data="load_game")],
            [types.InlineKeyboardButton(text="Новая игра", callback_data="new_game")]
        ])
    else:
        text = GUIDE_TEXT
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Начать", callback_data="start_new_game")]
        ])
    await update_or_send_message(chat_id, uid, text, kb)

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    chat_id = callback.message.chat.id
    try:
        now = time.time()
        if uid in last_request_time and now - last_request_time[uid] < 1.0:
            await callback.answer("Подожди немного...")
            return
        last_request_time[uid] = now + 0.2
        data = callback.data
        logging.info(f"[CALLBACK] {data} от {uid}")
        game = games.get(uid)
        if data in ("new_game", "start_new_game"):
            game = Game()
            games[uid] = game
            save_game(uid, game)
            await update_or_send_message(chat_id, uid, game.get_ui(), get_main_kb(game))
            await callback.answer()
            return
        if data == "load_game":
            game = load_game(uid) or Game()
            games[uid] = game
            save_game(uid, game)
            await update_or_send_message(chat_id, uid, game.get_ui(), get_main_kb(game))
            await callback.answer()
            return
        if not game:
            await callback.answer("Сначала начни игру /start")
            return

        text = None
        kb = None

        if data == "locations_menu":
            game.push_screen("locations")
            text = "Куда направиться?"
            kb = get_locations_kb(game)
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
        elif data == "inv_craft":
            game.push_screen("craft")
            kb_c = types.InlineKeyboardMarkup(inline_keyboard=[])
            if game.inventory.get("Спички 🔥", 0) >= 1 and game.inventory.get("Ветка", 0) >= 1:
                kb_c.inline_keyboard.append([
                    types.InlineKeyboardButton(text="Факел (1 ветка + 1 спичка)", callback_data="craft_Факел")
                ])
                craft_text = "Доступный крафт:"
            else:
                craft_text = "Пока ничего нельзя скрафтить.\n(нужна Ветка и Спички 🔥)"
            kb_c.inline_keyboard.append([types.InlineKeyboardButton(text="Назад", callback_data="back")])
            text = craft_text
            kb = kb_c
        elif data == "inv_use":
            game.push_screen("use")
            kb_u = types.InlineKeyboardMarkup(inline_keyboard=[])
            if game.inventory.get("Факел", 0) > 0 and game.equipment.get("hand") is None:
                kb_u.inline_keyboard.append([types.InlineKeyboardButton(text="Факел ", callback_data="use_item_Факел")])
            if not kb_u.inline_keyboard:
                kb_u.inline_keyboard.append([types.InlineKeyboardButton(text="Нечего использовать", callback_data="dummy")])
            kb_u.inline_keyboard.append([types.InlineKeyboardButton(text="Назад", callback_data="back")])
            text = "Что использовать?"
            kb = kb_u

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
            elif prev == "craft":
                kb_c = types.InlineKeyboardMarkup(inline_keyboard=[])
                if game.inventory.get("Спички 🔥", 0) >= 1 and game.inventory.get("Ветка", 0) >= 1:
                    kb_c.inline_keyboard.append([
                        types.InlineKeyboardButton(text="Факел (1 ветка + 1 спичка)", callback_data="craft_Факел")
                    ])
                    craft_text = "Доступный крафт:"
                else:
                    craft_text = "Пока ничего нельзя скрафтить.\n(нужна Ветка и Спички 🔥)"
                kb_c.inline_keyboard.append([types.InlineKeyboardButton(text="Назад", callback_data="back")])
                text = craft_text
                kb = kb_c
            elif prev == "use":
                text = game.get_ui()
                kb = get_main_kb(game)
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
                game.add_log("Действия на сегодня закончились.")
                text = game.get_ui()
                kb = get_main_kb(game)
            else:
                game.ap -= 1
                possible = ["Ветка", "Камень", "Ягода", "Гриб"]
                found = random.choice(possible)
                game.inventory[found] = game.inventory.get(found, 0) + 1
                game.add_log(f"Нашёл: {found}")
                text = game.get_ui()
                kb = get_main_kb(game)

        elif data == "action_3":
            if game.ap <= 0:
                game.add_log("Действия на сегодня закончились.")
            elif game.inventory.get("Вода", 0) > 0:
                game.inventory["Вода"] -= 1
                game.thirst = min(100, game.thirst + 30)
                game.add_log("Ты сделал глоток воды. Жажда уменьшилась.")
            else:
                game.add_log("Воды больше нет.")
            text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "action_4":
            game.day += 1
            game.ap = 5
            game.inventory["Вода"] = min(10, game.inventory.get("Вода", 0) + 5)
            game.add_log(f"День {game.day} начался. Снова 5 действий в запасе.")
            game.add_log("Ночь закончилась. Ты отдохнул и пополнил запасы воды.")
            text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "action_collect_water":
            if game.weather == "rain" and game.inventory.get("Вода", 0) < game.water_capacity:
                add = min(5, game.water_capacity - game.inventory.get("Вода", 0))
                game.inventory["Вода"] += add
                game.add_log(f"Собрал {add} воды в бутылку.")
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
        await callback.answer()
    except Exception as exc:
        logging.exception(f"Ошибка callback {data if 'data' in locals() else 'unknown'} для {uid}: {exc}")
        try:
            await callback.answer("Произошла ошибка. Попробуйте ещё раз.")
        except Exception:
            pass

@dp.message(F.text & ~F.text.startswith("/"))
async def process_text_message(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    try:
        raw_text = message.text.strip() if message.text else ""
        text = raw_text[:80] if raw_text else ""
        game = games.get(uid) or load_game(uid)
        if not game:
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
                await safe_edit_message(chat_id, msg_id, final_text, kb)
            else:
                await update_or_send_message(chat_id, uid, final_text, kb)

            save_game(uid, game)
            return
    except Exception as exc:
        logging.exception(f"Ошибка process_text_message для {uid}: {exc}")
        try:
            await message.answer("Я не смог обработать это сообщение. Попробуйте ещё раз.")
        except Exception:
            pass

async def run_bot():
    """Запустить polling и гарантированно закрыть внешние ресурсы при остановке."""
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        if mongo_client is not None:
            mongo_client.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(run_bot())