import asyncio
import logging
import os
import time
import random
from collections import Counter
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Update, Message
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
import httpx
from pymongo import MongoClient

from keyboards import get_main_kb, inventory_inline_kb, character_inline_kb, wolf_kb, peek_kb, cat_kb, next_kb
from crafts import handle_craft
from stories import handle_story

# ──────────────────────────────────────────────────────────────────────────────
# НАСТРОЙКИ
# ──────────────────────────────────────────────────────────────────────────────
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден!")

BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI не найден!")

logging.basicConfig(level=logging.INFO)
logging.info(f"Бот запущен. TOKEN: {TOKEN[:10]}... BASE_URL: {BASE_URL}")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI(title="Forest Survival Bot")

last_request_time = {}
last_active_msg_id = {}
research_count_day2 = {}

# ──────────────────────────────────────────────────────────────────────────────
# MONGODB
# ──────────────────────────────────────────────────────────────────────────────
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['forest_game']
players_collection = db['players']
mongo_client.server_info()
logging.info("MongoDB подключён успешно")

# ──────────────────────────────────────────────────────────────────────────────
# КЛАСС ИГРЫ
# ──────────────────────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.hp = 100
        self.hunger = 20
        self.thirst = 60
        self.ap = 5
        self.karma = 0
        self.karma_goal = 100
        self.day = 1
        self.log = ["Ты проснулся в лесу. Что будешь делать?"]
        self.inventory = Counter({
            "Спички ": 1,
            "Вилка ": 1,
            "Кусок коры ": 1,
            "Сухпай": 3,
            "Бутылка воды": 10
        })
        self.weather = "clear"
        self.location = "лес"
        self.unlocked_locations = ["лес", "тёмный лес", "озеро", "заброшенный лагерь"]
        self.water_capacity = 10
        self.equipment = {
            "head": None,
            "torso": None,
            "back": None,
            "pants": None,
            "boots": None,
            "trinket": None,
            "pet": None,
            "hand": None
        }
        self.story_state = None
        self.found_branch_once = False
        self.nav_stack = ["main"]  # стек навигации

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
        weather_icon = {"clear": " ", "cloudy": " ", "rain": " "}.get(self.weather, " ")
        return (
            f" {self.hp}    {self.hunger}    {self.thirst}    {self.ap}    {weather_icon} {self.day}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(f"> {line}" for line in self.log) + "\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

    def get_inventory_text(self):
        lines = []
        equipped_hand = self.equipment.get("hand")
        for item, count in self.inventory.items():
            if count > 0:
                marker = " " if item == "Факел" else ""
                equipped_mark = " " if item == equipped_hand else ""
                line = f"• {item} x{count}{marker}{equipped_mark}" if count > 1 else f"• {item}{marker}{equipped_mark}"
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
            "hand": "Рука"
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
            game = Game()
            inv_dict = data["game_data"].pop("inventory", {})
            equip_dict = data["game_data"].pop("equipment", {})
            game.__dict__.update(data["game_data"])
            game.inventory = Counter(inv_dict)
            game.equipment = equip_dict
            if "nav_stack" not in game.__dict__:
                game.nav_stack = ["main"]
            return game
    except Exception as e:
        logging.error(f"Ошибка загрузки {uid}: {e}")
    return None

def save_game(uid: int, game: Game):
    try:
        data = game.__dict__.copy()
        data["inventory"] = dict(game.inventory)
        data["equipment"] = game.equipment
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
    "Краткий гайд\n"
    "100 - здоровье\n"
    "100 - сытость\n"
    "100 - жажда\n"
    "5 - действия на день\n"
    "100 - день\n\n"
    "Карма поможет выбраться.\n\n"
    "Попробуй выжить друг мой..."
)

# ──────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ С RETRY ПРИ FLOOD
# ──────────────────────────────────────────────────────────────────────────────
async def update_or_send_message(chat_id: int, uid: int, text: str, reply_markup=None):
    msg_id = last_active_msg_id.get(uid)
    if msg_id:
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=msg_id, reply_markup=reply_markup
            )
            return msg_id
        except TelegramRetryAfter as e:
            logging.warning(f"Flood control: ждём {e.retry_after} сек перед повтором edit")
            await asyncio.sleep(e.retry_after + 0.5)
            try:
                await bot.edit_message_text(
                    text, chat_id=chat_id, message_id=msg_id, reply_markup=reply_markup
                )
                return msg_id
            except Exception as ex:
                logging.error(f"Повторная ошибка при edit после retry: {ex}")
        except TelegramBadRequest as e:
            logging.warning(f"Не удалось отредактировать {msg_id} для {uid}: {e}")
            try:
                await bot.delete_message(chat_id, msg_id)
            except:
                pass
            last_active_msg_id.pop(uid, None)
    msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    last_active_msg_id[uid] = msg.message_id
    return msg.message_id

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
    action_taken = False

    if data == "action_2":
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
        if game.inventory.get("Спички ", 0) >= 1 and game.inventory.get("Ветка", 0) >= 1:
            kb_c.inline_keyboard.append([
                types.InlineKeyboardButton(text="Факел (1 ветка + 1 спичка)", callback_data="craft_Факел")
            ])
            craft_text = "Доступный крафт:"
        else:
            craft_text = "Пока ничего нельзя скрафтить.\n(нужна Ветка и Спички )"
        kb_c.inline_keyboard.append([types.InlineKeyboardButton(text="Назад", callback_data="back")])
        text = craft_text
        kb = kb_c
    elif data == "inv_use":
        game.push_screen("use")
        kb_u = types.InlineKeyboardMarkup(inline_keyboard=[])
        if game.inventory.get("Факел", 0) > 0 and game.equipment["hand"] is None:
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
            if game.inventory.get("Спички ", 0) >= 1 and game.inventory.get("Ветка", 0) >= 1:
                kb_c.inline_keyboard.append([
                    types.InlineKeyboardButton(text="Факел (1 ветка + 1 спичка)", callback_data="craft_Факел")
                ])
                craft_text = "Доступный крафт:"
            else:
                craft_text = "Пока ничего нельзя скрафтить.\n(нужна Ветка и Спички )"
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

    elif data in ("wolf_flee", "wolf_fight", "peek_den", "cat_leave", "cat_take", "story_next"):
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
            game.inventory[found] += 1
            game.add_log(f"Нашёл: {found}")
            text = game.get_ui()
            kb = get_main_kb(game)
            action_taken = True

    elif data == "action_3":
        if game.ap <= 0:
            game.add_log("Действия на сегодня закончились.")
        elif game.inventory["Бутылка воды"] > 0:
            game.inventory["Бутылка воды"] -= 1
            game.thirst = min(100, game.thirst + 30)
            game.add_log("Ты сделал глоток воды. Жажда уменьшилась.")
            action_taken = True
        else:
            game.add_log("Воды больше нет.")
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "action_4":
        if game.ap <= 0:
            game.add_log("Действия на сегодня закончились.")
        else:
            game.hp = min(100, game.hp + 40)
            game.hunger = max(0, game.hunger - 20)
            game.thirst = max(0, game.thirst - 15)
            game.day += 1
            game.ap = 5
            game.add_log("Ты уснул. Новый день начался.")
            action_taken = True
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "action_collect_water":
        if game.weather == "rain" and game.inventory["Бутылка воды"] < game.water_capacity:
            add = min(5, game.water_capacity - game.inventory["Бутылка воды"])
            game.inventory["Бутылка воды"] += add
            game.add_log(f"Собрал {add} воды в бутылку.")
        text = game.get_ui()
        kb = get_main_kb(game)

    if text is not None:
        await update_or_send_message(chat_id, uid, text, kb)
        save_game(uid, game)
    await callback.answer()

# ──────────────────────────────────────────────────────────────────────────────
# WEBHOOK
# ──────────────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook установлен: {WEBHOOK_URL}")
    else:
        logging.warning("BASE_URL не задан — webhook не установлен")

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != TOKEN:
        raise HTTPException(status_code=403)
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return PlainTextResponse("OK")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
