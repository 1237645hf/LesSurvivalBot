import asyncio
import logging
import os
import time
import random
import gc
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
import httpx
from pymongo import MongoClient
from pymongo.errors import ConfigurationError, OperationFailure

# ──────────────────────────────────────────────────────────────────────────────
# НАСТРОЙКИ
# ──────────────────────────────────────────────────────────────────────────────

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден в Environment Variables Render!")

BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI не найден в Environment Variables Render!")

logging.basicConfig(level=logging.INFO)
logging.info(f"Бот запущен. TOKEN: {TOKEN[:10]}... BASE_URL: {BASE_URL}")
logging.info(f"MONGO_URI: {MONGO_URI[:30]}...")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI(title="Forest Survival Bot")

last_request_time = {}   # кулдаун
last_ui_msg_id = {}      # user_id → message_id главного UI
last_inv_msg_id = {}     # user_id → message_id инвентаря

# ──────────────────────────────────────────────────────────────────────────────
# ПОДКЛЮЧЕНИЕ К MONGODB
# ──────────────────────────────────────────────────────────────────────────────

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['forest_game']           # имя базы данных
    players_collection = db['players']         # коллекция игроков
    mongo_client.server_info()
    logging.info("MongoDB подключён успешно")
except (ConfigurationError, OperationFailure) as e:
    logging.error(f"Ошибка подключения к MongoDB: {e}")
    raise RuntimeError("Не удалось подключиться к MongoDB")

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
        self.search_progress = 0
        self.day = 1
        self.log = ["🌲 Ты проснулся в лесу. Что будешь делать?"]
        self.inventory = ["Спички 🔥", "Вилка 🍴", "Кусок коры 🪵", "Сухпай (3/3)"]
        self.weather = "clear"  # clear / cloudy / rain
        self.location = "лес"   # текущая локация
        self.unlocked_locations = ["лес", "тёмный лес", "река", "озеро", "заброшенный лагерь"]  # пока все открыты

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    def get_ui(self):
        weather_icon = {
            "clear": "☀️ Ясно",
            "cloudy": "☁️ Пасмурно",
            "rain": "🌧️ Дождь"
        }.get(self.weather, "☀️ Ясно")
        location_icon = {
            "лес": "🌲 Лес",
            "тёмный лес": "🌳 Тёмный лес",
            "река": "🌊 Река",
            "озеро": "💦 Озеро",
            "заброшенный лагерь": "🏕️ Заброшенный лагерь"
        }.get(self.location, "🌲 Лес")
        return (
            f"❤️ {self.hp}   🍖 {self.hunger}   💧 {self.thirst}  ⚡ {self.ap}   ☀️ {self.day}   {weather_icon}\n"
            f"Ты в {location_icon}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(f"> {line}" for line in self.log) + "\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

    def get_inventory_text(self):
        return "🎒 Инвентарь:\n" + "\n".join(f"• {item}" for item in self.inventory) if self.inventory else "🎒 Инвентарь пуст"

# ──────────────────────────────────────────────────────────────────────────────
# ФУНКЦИИ СОХРАНЕНИЯ / ЗАГРУЗКИ
# ──────────────────────────────────────────────────────────────────────────────

def load_game(uid: int) -> Game | None:
    try:
        data = players_collection.find_one({"_id": uid})
        if data and "game_data" in data:
            game = Game()
            game.__dict__.update(data["game_data"])
            return game
    except Exception as e:
        logging.error(f"Ошибка загрузки игрока {uid}: {e}")
    return None

def save_game(uid: int, game: Game):
    try:
        players_collection.update_one(
            {"_id": uid},
            {"$set": {"game_data": game.__dict__}},
            upsert=True
        )
    except Exception as e:
        logging.error(f"Ошибка сохранения игрока {uid}: {e}")

# ГЛОБАЛЬНЫЙ КЭШ ИГР
games = {}

# ──────────────────────────────────────────────────────────────────────────────
# КНОПКИ
# ──────────────────────────────────────────────────────────────────────────────

def get_main_kb(game: Game):
    locations = ["лес", "тёмный лес", "река", "озеро", "заброшенный лагерь"]
    loc_icons = ["🌲", "🌳", "🌊", "💦", "🏕️"]
    current_idx = locations.index(game.location)
    loc_row = []
    if current_idx > 0:
        prev_loc = locations[current_idx - 1]
        prev_icon = loc_icons[current_idx - 1]
        loc_row.append(InlineKeyboardButton(text=f"← {prev_icon}", callback_data=f"loc_{prev_loc}"))
    loc_row.append(InlineKeyboardButton(text=f"{loc_icons[current_idx]} {game.location.capitalize()}", callback_data="loc_current"))  # текущая, без действия
    if current_idx < len(locations) - 1:
        next_loc = locations[current_idx + 1]
        next_icon = loc_icons[current_idx + 1]
        if next_loc in game.unlocked_locations:
            loc_row.append(InlineKeyboardButton(text=f"{next_icon} →", callback_data=f"loc_{next_loc}"))
        else:
            loc_row.append(InlineKeyboardButton(text=f"{next_icon} Заблокировано", callback_data="loc_locked"))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        loc_row,  # ряд с локациями
        [InlineKeyboardButton(text="🌲 В чащу ", callback_data="action_1"),
         InlineKeyboardButton(text="🎒 Инвентарь ", callback_data="action_2")],
        [InlineKeyboardButton(text="💧 Пить воду ", callback_data="action_3"),
         InlineKeyboardButton(text="🌙 Спать ", callback_data="action_4")],
        [InlineKeyboardButton(text="🚁 Сбежать ", callback_data="action_6")],
    ])
    return kb

inventory_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👁️ Осмотреть ", callback_data="inv_inspect"),
     InlineKeyboardButton(text="🛠️ Использовать ", callback_data="inv_use")],
    [InlineKeyboardButton(text="🗑️ Выкинуть ", callback_data="inv_drop"),
     InlineKeyboardButton(text="🛠️ Крафт ", callback_data="inv_craft")],
    [InlineKeyboardButton(text="👤 Персонаж ", callback_data="inv_character"),
     InlineKeyboardButton(text="← Назад ", callback_data="inv_back")],
])

start_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🫡 Я готов ", callback_data="start_game")],
])

# ──────────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id

    await message.answer(
        "🌲 Добро пожаловать в лес выживания!\n\n"
        "Краткий гайд\n"
        "❤️ 100 - твое здоровье\n"
        "🍖 100 - твоя сытость\n"
        "💧 100 - твоя жажда\n"
        "⚡ 5 - очки действий на день\n"
        "☀️ 100 - игровой день\n\n"
        "⚖️ Карма - единственный параметр способный тебе помочь выбраться из леса.\n\n"
        "Попробуй выжить, друг....",
        reply_markup=start_kb
    )

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    now = time.time()

    if uid in last_request_time and now - last_request_time[uid] < 1.0:
        await callback.answer("Подожди секунду!")
        return
    last_request_time[uid] = now

    data = callback.data

    if data == "start_game":
        games[uid] = Game()
        save_game(uid, games[uid])

        await callback.message.edit_text("Игра началась!\n\nВыбери действие ниже ↓")

        ui_msg = await callback.message.answer(games[uid].get_ui(), reply_markup=get_main_kb(games[uid]))
        last_ui_msg_id[uid] = ui_msg.message_id
        await callback.answer()
        return

    if uid not in games:
        loaded = load_game(uid)
        if loaded:
            games[uid] = loaded
        else:
            await callback.message.answer("Сначала /start")
            await callback.answer()
            return

    game = games[uid]
    action_taken = False

    if data.startswith("loc_"):
        if data == "loc_locked":
            game.add_log("Эта локация заблокирована...")
            action_taken = True
        elif data == "loc_current":
            game.add_log("Ты уже здесь.")
            action_taken = True
        else:
            new_loc = data.replace("loc_", "")
            if new_loc in game.unlocked_locations:
                game.location = new_loc
                game.add_log(f"Перешёл в {new_loc}.")
                action_taken = True
            else:
                game.add_log("Локация не открыта.")
                action_taken = True

    elif data == "action_1":
        if game.weather == "rain":
            game.add_log("🌧️ Дождь льёт стеной, в чащу не сунешься...")
            action_taken = True
        elif game.ap > 0:
            game.ap -= 1
            game.hunger = max(0, game.hunger - 7)
            game.thirst = max(0, game.thirst - 8)
            # События в чаще (базовые, зависят от локации)
            events = [
                ("Нашёл ягоды! +10 сытости", lambda: setattr(game, 'hunger', min(100, game.hunger + 10))),
                ("Нашёл мухоморы... рискнул съесть? -5 HP", lambda: setattr(game, 'hp', max(0, game.hp - 5))),
                ("Нашёл родник! +20 жажды", lambda: setattr(game, 'thirst', min(100, game.thirst + 20))),
                ("Укус змеи! -10 HP", lambda: setattr(game, 'hp', max(0, game.hp - 10))),
                ("Нашёл кору", lambda: game.inventory.append("Кусок коры 🪵"))
            ]
            # Модификаторы по локации
            if game.location in ["река", "озеро"]:
                events.append(("Напился из реки/озера! +30 жажды", lambda: setattr(game, 'thirst', min(100, game.thirst + 30))))  # больше шанса на воду
            event_text, event_effect = random.choice(events)
            event_effect()
            game.add_log(f"🔍 Ты пошёл в чащу... {event_text}")
            action_taken = True
        else:
            game.add_log("🏕 У тебя нет сил и нужно отдохнуть")
            action_taken = True

    elif data == "action_2":
        if uid in last_ui_msg_id:
            try:
                await bot.delete_message(callback.message.chat.id, last_ui_msg_id[uid])
                del last_ui_msg_id[uid]
            except:
                pass

        inv_msg = await callback.message.answer(game.get_inventory_text(), reply_markup=inventory_inline_kb)
        last_inv_msg_id[uid] = inv_msg.message_id
        await callback.answer()
        return

    elif data == "action_3":
        game.thirst = min(100, game.thirst + 20)
        game.add_log("💧 Напился... жажда +20")
        action_taken = True

    elif data == "action_4":
        game.day += 1
        game.ap = 5
        game.hunger = max(0, game.hunger - 15)

        weather_choices = ["clear", "cloudy", "rain"]
        weights = [70, 20, 10]
        game.weather = random.choices(weather_choices, weights=weights, k=1)[0]

        weather_name = {"clear": "ясно", "cloudy": "пасмурно", "rain": "дождь"}[game.weather]
        game.add_log(f"🌙 День {game.day}. Выспался, голод -15. На улице {weather_name}.")
        action_taken = True

    elif data == "action_6":
        chance = 10 + (game.karma // 10)
        if random.randint(1, 100) <= chance:
            await callback.message.answer("🚁 ПОБЕДА! Ты сбежал!\n\n/start — новая игра")
            games.pop(uid, None)
            last_ui_msg_id.pop(uid, None)
            players_collection.delete_one({"_id": uid})
            await callback.answer("Победа!")
            return
        else:
            game.add_log("Побег не удался...")
            action_taken = True

    elif data == "inv_inspect":
        game.add_log("👁️ Осмотрел инвентарь... (заглушка)")
        action_taken = True

    elif data == "inv_use":
        game.add_log("🛠️ Использовал предмет... (заглушка)")
        action_taken = True

    elif data == "inv_drop":
        game.add_log("🗑️ Выкинул предмет... (заглушка)")
        action_taken = True

    elif data == "inv_craft":
        game.add_log("🛠️ Крафт... (заглушка)")
        action_taken = True

    elif data == "inv_character":
        game.add_log("👤 Персонаж... (заглушка)")
        action_taken = True

    elif data == "inv_back":
        if uid in last_inv_msg_id:
            try:
                await bot.delete_message(callback.message.chat.id, last_inv_msg_id[uid])
                del last_inv_msg_id[uid]
            except:
                pass

        ui_msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = ui_msg.message_id
        await callback.answer()
        return

    if action_taken:
        save_game(uid, game)
        await callback.message.edit_text(
            game.get_ui(),
            reply_markup=get_main_kb(game)
        )
        await callback.answer()

# ──────────────────────────────────────────────────────────────────────────────
# SELF-PING + АВТО-ПЕРЕУСТАНОВКА WEBHOOK
# ──────────────────────────────────────────────────────────────────────────────

PING_INTERVAL_SECONDS = 300

async def self_ping_task():
    if not BASE_URL:
        logging.info("Self-ping отключён")
        return
    ping_url = f"{BASE_URL}/ping"
    logging.info(f"Self-ping запущен (каждые {PING_INTERVAL_SECONDS} сек → {ping_url})")
    while True:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(ping_url, timeout=10)
                if r.status_code == 200:
                    logging.info(f"[SELF-PING] OK → {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    try:
                        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
                        logging.info(f"Webhook переустановлен: {WEBHOOK_URL}")
                    except Exception as e:
                        logging.warning(f"Авто-переустановка webhook: {e}")
        except Exception as e:
            logging.error(f"[SELF-PING] ошибка: {e}")
        await asyncio.sleep(PING_INTERVAL_SECONDS)

# ──────────────────────────────────────────────────────────────────────────────
# FASTAPI МАРШРУТЫ И ЖИЗНЕННЫЙ ЦИКЛ
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/ping")
@app.get("/health")
async def health_check():
    return PlainTextResponse("OK", status_code=200)

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        body = await request.json()
        update = Update.model_validate(body, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500)

@app.on_event("startup")
async def on_startup():
    if WEBHOOK_URL:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except:
            pass
        try:
            await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
            logging.info(f"Webhook установлен: {WEBHOOK_URL}")
        except Exception as e:
            logging.error(f"set_webhook failed: {e}")
    asyncio.create_task(self_ping_task())

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)