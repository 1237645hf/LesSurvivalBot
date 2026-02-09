import asyncio
import logging
import os
import time
import random
from collections import Counter
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

last_request_time = {}
last_ui_msg_id = {}
last_inv_msg_id = {}

# ──────────────────────────────────────────────────────────────────────────────
# ПОДКЛЮЧЕНИЕ К MONGODB
# ──────────────────────────────────────────────────────────────────────────────

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['forest_game']
    players_collection = db['players']
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
        self.inventory = Counter({
            "Спички 🔥": 1,
            "Вилка 🍴": 1,
            "Кусок коры 🪵": 1,
            "Сухпай": 3,           # порции
            "Бутылка воды": 10     # глотки
        })
        self.weather = "clear"
        self.location = "лес"
        self.unlocked_locations = ["лес", "тёмный лес", "озеро", "заброшенный лагерь"]

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    def get_ui(self):
        weather_icon = {"clear": "☀️ Ясно", "cloudy": "☁️ Пасмурно", "rain": "🌧️ Дождь"}.get(self.weather, "☀️ Ясно")
        location_icon = {
            "лес": "🌲 Лес",
            "тёмный лес": "🌳 Тёмный лес",
            "озеро": "🏝 Озеро",
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
        lines = []
        for item, count in self.inventory.items():
            if count > 0:
                lines.append(f"• {item} x{count}" if count > 1 else f"• {item}")
        return "🎒 Инвентарь:\n" + "\n".join(lines) if lines else "🎒 Инвентарь пуст"

# ──────────────────────────────────────────────────────────────────────────────
# ФУНКЦИИ СОХРАНЕНИЯ / ЗАГРУЗКИ
# ──────────────────────────────────────────────────────────────────────────────

def load_game(uid: int) -> Game | None:
    try:
        data = players_collection.find_one({"_id": uid})
        if data and "game_data" in data:
            game = Game()
            # Восстанавливаем Counter
            inv_dict = data["game_data"].pop("inventory", {})
            game.__dict__.update(data["game_data"])
            game.inventory = Counter(inv_dict)
            return game
    except Exception as e:
        logging.error(f"Ошибка загрузки игрока {uid}: {e}")
    return None

def save_game(uid: int, game: Game):
    try:
        data = game.__dict__.copy()
        data["inventory"] = dict(game.inventory)  # Counter → dict для Mongo
        players_collection.update_one(
            {"_id": uid},
            {"$set": {"game_data": data}},
            upsert=True
        )
    except Exception as e:
        logging.error(f"Ошибка сохранения игрока {uid}: {e}")

games = {}

# ──────────────────────────────────────────────────────────────────────────────
# КНОПКИ
# ──────────────────────────────────────────────────────────────────────────────

def get_main_kb(game: Game):
    locations = ["лес", "тёмный лес", "озеро", "заброшенный лагерь"]
    loc_icons = ["🌲", "🌳", "🏝", "🏕️"]
    current_idx = locations.index(game.location)

    loc_row = []
    if current_idx > 0:
        prev_loc = locations[current_idx - 1]
        prev_icon = loc_icons[current_idx - 1]
        loc_row.append(InlineKeyboardButton(text=f"← {prev_icon}", callback_data=f"loc_{prev_loc}"))

    loc_row.append(InlineKeyboardButton(text=f"{loc_icons[current_idx]} {game.location.capitalize()}", callback_data="loc_current"))

    if current_idx < len(locations) - 1:
        next_loc = locations[current_idx + 1]
        next_icon = loc_icons[current_idx + 1]
        if next_loc in game.unlocked_locations:
            loc_row.append(InlineKeyboardButton(text=f"{next_icon} →", callback_data=f"loc_{next_loc}"))
        else:
            loc_row.append(InlineKeyboardButton(text=f"{next_icon} Заблокировано", callback_data="loc_locked"))

    kb = [
        loc_row,
        [
            InlineKeyboardButton(text="🌲 В чащу ", callback_data="action_1"),
            InlineKeyboardButton(text="🎒 Инвентарь ", callback_data="action_2")
        ],
        [
            InlineKeyboardButton(text=f"💧 Пить воду ({game.inventory['Бутылка воды']}/10)", callback_data="action_3")
            if game.inventory['Бутылка воды'] > 0 else InlineKeyboardButton(text="💧 Пить воду (пусто)", callback_data="action_3_disabled"),
            InlineKeyboardButton(text="🌙 Спать ", callback_data="action_4")
        ]
    ]

    if game.weather == "rain":
        kb.append([InlineKeyboardButton(text="🌧️ Собрать воду ", callback_data="action_collect_water")])

    return InlineKeyboardMarkup(inline_keyboard=kb)

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
        "❤️ 100 - здоровье\n"
        "🍖 100 - сытость\n"
        "💧 100 - жажда\n"
        "⚡ 5 - действия на день\n"
        "☀️ 100 - день\n\n"
        "⚖️ Карма помогает выбраться.\n\n"
        "Попробуй выжить...",
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
    game = games.get(uid)

    if data == "start_game":
        game = Game()
        games[uid] = game
        save_game(uid, game)
        await callback.message.edit_text("Игра началась!\n\nВыбери действие ↓")
        ui_msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = ui_msg.message_id
        await callback.answer()
        return

    if not game:
        loaded = load_game(uid)
        if loaded:
            games[uid] = loaded
            game = loaded
        else:
            await callback.message.answer("Сначала /start")
            await callback.answer()
            return

    action_taken = False

    if data.startswith("loc_"):
        if data == "loc_locked":
            game.add_log("Эта локация заблокирована...")
        elif data == "loc_current":
            game.add_log("Ты уже здесь.")
        else:
            new_loc = data.replace("loc_", "")
            if new_loc in game.unlocked_locations:
                game.location = new_loc
                game.add_log(f"Перешёл в {new_loc}.")
            else:
                game.add_log("Локация не открыта.")
        action_taken = True

    elif data == "action_1":
        if game.weather == "rain":
            game.add_log("🌧️ Дождь льёт стеной, в чащу не сунешься...")
        elif game.ap > 0:
            game.ap -= 1
            game.hunger = max(0, game.hunger - 7)
            game.thirst = max(0, game.thirst - 8)

            events = [
                ("Нашёл ягоды! +15 сытости", lambda: setattr(game, 'hunger', min(100, game.hunger + 15))),
                ("Нашёл мухоморы (предмет)", lambda: game.inventory.update({"Мухоморы": game.inventory["Мухоморы"] + 1})),
                ("Нашёл родник! Наполнил бутылку +30", lambda: game.inventory.update({"Бутылка воды": min(10, game.inventory["Бутылка воды"] + 30)})),
                ("Укус змеи! -10 HP", lambda: setattr(game, 'hp', max(0, game.hp - 10))),
                ("Нашёл кору", lambda: game.inventory.update({"Кусок коры 🪵": game.inventory["Кусок коры 🪵"] + 1})),
                ("Нашёл ветку", lambda: game.inventory.update({"Ветка": game.inventory["Ветка"] + 1})),
                ("Нашёл нож", lambda: game.inventory.update({"Нож": game.inventory["Нож"] + 1}))
            ]
            text, effect = random.choice(events)
            effect()
            game.add_log(f"🔍 Ты пошёл в чащу... {text}")
        else:
            game.add_log("🏕 У тебя нет сил и нужно отдохнуть")
        action_taken = True

    elif data == "action_3":
        if game.inventory["Бутылка воды"] > 0:
            game.inventory["Бутылка воды"] -= 1
            game.thirst = min(100, game.thirst + 20)
            game.add_log(f"💧 Глоток из бутылки... жажда +20 (осталось {game.inventory['Бутылка воды']}/10)")
        else:
            game.add_log("💧 Бутылка пуста, найди источник!")
        action_taken = True

    elif data == "action_collect_water":
        if game.weather == "rain":
            added = 40
            game.inventory["Бутылка воды"] = min(10, game.inventory["Бутылка воды"] + added)
            game.add_log(f"🌧️ Собрал дождевую воду... +{added} в бутылку (теперь {game.inventory['Бутылка воды']}/10)")
            action_taken = True
        else:
            game.add_log("Сейчас не идёт дождь...")
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

    elif data in ("inv_inspect", "inv_use", "inv_drop", "inv_craft", "inv_character"):
        game.add_log(f"{data.replace('inv_', '').capitalize()}... (заглушка)")
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
# SELF-PING + WEBHOOK
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
# FASTAPI
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
