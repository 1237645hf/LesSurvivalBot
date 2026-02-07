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

# ──────────────────────────────────────────────────────────────────────────────
# НАСТРОЙКИ
# ──────────────────────────────────────────────────────────────────────────────

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден в Environment Variables Render!")

BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

logging.basicConfig(level=logging.INFO)
logging.info(f"Бот запущен. TOKEN: {TOKEN[:10]}... BASE_URL: {BASE_URL}")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI(title="Forest Survival Bot")

last_request_time = {}  # кулдаун
last_ui_msg_id = {}  # user_id → message_id главного UI
last_inv_msg_id = {}  # user_id → message_id инвентаря

# ──────────────────────────────────────────────────────────────────────────────
# SELF-PING + АВТО-ПЕРЕУСТАНОВКА WEBHOOK
# ──────────────────────────────────────────────────────────────────────────────

PING_INTERVAL_SECONDS = 300

async def self_ping_task():
    if not BASE_URL:
        logging.info("Self-ping отключён")
        return
    ping_url = f"{BASE_URL}/ping"
    logging.info(f"Self-ping запущен (каждые 5 мин → {ping_url})")
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
        self.inventory = ["Спички 🔥", "Вилка 🍴", "Кусок коры 🪵"]

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    def get_ui(self):
        return (
            f"❤️ {self.hp}   🍖 {self.hunger}   💧 {self.thirst}  ⚡ {self.ap}   ☀️ {self.day}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(f"> {line}" for line in self.log) + "\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

    def get_inventory_text(self):
        return "🎒 Инвентарь:\n" + "\n".join(f"• {item}" for item in self.inventory) if self.inventory else "🎒 Инвентарь пуст"

games = {}

# ──────────────────────────────────────────────────────────────────────────────
# КНОПКИ
# ──────────────────────────────────────────────────────────────────────────────

main_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="В чащу 🌲", callback_data="action_1")],
    [InlineKeyboardButton(text="Инвентарь 🎒", callback_data="action_2")],
    [InlineKeyboardButton(text="Пить воду 💧", callback_data="action_3")],
    [InlineKeyboardButton(text="Спать 🌙", callback_data="action_4")],
    [InlineKeyboardButton(text="📱ловить сигнал📱", callback_data="action_5")],
    [InlineKeyboardButton(text="Сбежать 🚁", callback_data="action_6")],
])

inventory_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Осмотреть 👁️", callback_data="inv_inspect")],
    [InlineKeyboardButton(text="Использовать 🛠️", callback_data="inv_use")],
    [InlineKeyboardButton(text="Выкинуть 🗑️", callback_data="inv_drop")],
    [InlineKeyboardButton(text="Крафт 🛠️", callback_data="inv_craft")],
    [InlineKeyboardButton(text="Персонаж 👤", callback_data="inv_character")],
    [InlineKeyboardButton(text="Назад ←", callback_data="inv_back")],
])

start_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🫡 Я готов 🫡", callback_data="start_game")],
])

# ──────────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id

    # Очистка чата
    try:
        history = await bot.get_chat_history(message.chat.id, limit=30)
        for msg in history:
            if msg.from_user and msg.from_user.id == (await bot.get_me()).id:
                if msg.message_id != message.message_id:
                    await bot.delete_message(message.chat.id, msg.message_id)
    except Exception as e:
        logging.warning(f"Очистка чата не удалась: {e}")

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
        await callback.message.edit_text("Игра началась!\n\nВыбери действие ниже ↓")

        ui_msg = await callback.message.answer(games[uid].get_ui(), reply_markup=main_inline_kb)
        last_ui_msg_id[uid] = ui_msg.message_id
        await callback.answer()
        return

    if uid not in games:
        await callback.message.answer("Сначала /start")
        await callback.answer()
        return

    game = games[uid]
    action_taken = False

    if data == "action_1":
        if game.ap > 0:
            game.ap -= 1
            game.hunger = max(0, game.hunger - 7)
            game.thirst = max(0, game.thirst - 8)
            game.add_log("🔍 Ты пошёл в чащу... нашёл кору!")
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
        game.add_log(f"🌙 День {game.day}. Выспался, голод -15")
        action_taken = True
    elif data == "action_5":
        if game.ap > 0:
            game.ap -= 1
            if random.randint(1, 2) == 1:
                game.search_progress += 5
                game.add_log("📱 Поймал сигнал... +5 к поиску маршрута")
            else:
                game.add_log("📱 Сигнал не пойман...")
            action_taken = True
        else:
            game.add_log("🏕 У тебя нет сил и нужно отдохнуть")
            action_taken = True
    elif data == "action_6":
        chance = 10 + (game.karma // 10)
        if random.randint(1, 100) <= chance:
            await callback.message.answer("🚁 ПОБЕДА! Ты сбежал!\n\n/start — новая игра")
            games.pop(uid, None)
            last_ui_msg_id.pop(uid, None)
            await callback.answer("Победа!")
            return
        else:
            game.add_log("Побег не удался...")
            action_taken = True
    elif data == "inv_inspect":
        game.add_log("Осмотрел инвентарь... (заглушка)")
        action_taken = True
    elif data == "inv_use":
        game.add_log("Использовал предмет... (заглушка)")
        action_taken = True
    elif data == "inv_drop":
        game.add_log("Выкинул предмет... (заглушка)")
        action_taken = True
    elif data == "inv_craft":
        game.add_log("Крафт... (заглушка)")
        action_taken = True
    elif data == "inv_character":
        game.add_log("Персонаж... (заглушка)")
        action_taken = True
    elif data == "inv_back":
        if uid in last_inv_msg_id:
            try:
                await bot.delete_message(callback.message.chat.id, last_inv_msg_id[uid])
                del last_inv_msg_id[uid]
            except:
                pass

        ui_msg = await callback.message.answer(game.get_ui(), reply_markup=main_inline_kb)
        last_ui_msg_id[uid] = ui_msg.message_id
        await callback.answer()
        return

    if action_taken:
        await callback.message.edit_text(
            game.get_ui(),
            reply_markup=main_inline_kb
        )
        await callback.answer()

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
    import gc
    uvicorn.run(app, host="0.0.0.0", port=8000)