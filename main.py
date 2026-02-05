import asyncio
import logging
import os
import time
import random
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
import httpx

# ──────────────────────────────────────────────────────────────────────────────
# 1. ИМПОРТЫ И НАСТРОЙКИ
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

last_request_time = {}  # для кулдауна

# ──────────────────────────────────────────────────────────────────────────────
# 2. SELF-PING
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
        except Exception as e:
            logging.error(f"[SELF-PING] ошибка: {e}")
        await asyncio.sleep(PING_INTERVAL_SECONDS)

# ──────────────────────────────────────────────────────────────────────────────
# 3. КЛАСС ИГРЫ
# ──────────────────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        self.hp = 100
        self.hunger = 30
        self.thirst = 30
        self.ap = 5
        self.karma = 0
        self.log = ["🌲 Ты проснулся в лесу. Что будешь делать?"]
        self.inventory = ["Спички 🔥", "Вилка 🍴", "Кусок коры 🪵"]

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 15:
            self.log = self.log[-15:]

    def get_ui(self):
        return (
            f"❤️ HP: {self.hp}   🍖 Голод: {self.hunger}   💧 Жажда: {self.thirst}\n"
            f"⚡ Очки действий: {self.ap}   ⚖️ Карма: {self.karma}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(f"> {line}" for line in self.log) + "\n"
            + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    def get_inventory_text(self):
        return "🎒 Инвентарь:\n" + "\n".join(f"• {item}" for item in self.inventory) if self.inventory else "🎒 Инвентарь пуст"

games = {}
last_ui_msg_id = {}  # user_id → message_id состояния

# Inline-клавиатура (одна для всех состояний игры)
inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="1 В чащу 🌲", callback_data="action_1"),
        InlineKeyboardButton(text="2 Инвентарь 🎒", callback_data="action_2"),
    ],
    [
        InlineKeyboardButton(text="3 Пить воду 💧", callback_data="action_3"),
        InlineKeyboardButton(text="4 Спать 🌙", callback_data="action_4"),
    ],
    [
        InlineKeyboardButton(text="5 Позвать мудреца 🧙", callback_data="action_5"),
        InlineKeyboardButton(text="6 Сбежать 🚁", callback_data="action_6"),
    ],
])

# ──────────────────────────────────────────────────────────────────────────────
# 4. ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id

    # Очистка чата (удаляем предыдущие сообщения бота)
    try:
        history = await bot.get_chat_history(message.chat.id, limit=30)
        for msg in history:
            if msg.from_user and msg.from_user.id == (await bot.get_me()).id:
                if msg.message_id != message.message_id:
                    await bot.delete_message(message.chat.id, msg.message_id)
    except Exception as e:
        logging.warning(f"Очистка чата не удалась: {e}")

    games[uid] = Game()

    await message.answer(
        "🌲 Добро пожаловать в лес выживания!\n\nВыбери действие ниже ↓",
        reply_markup=inline_kb
    )

    ui_msg = await message.answer(games[uid].get_ui(), reply_markup=inline_kb)
    last_ui_msg_id[uid] = ui_msg.message_id

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    now = time.time()

    # Кулдаун 1 секунда
    if uid in last_request_time and now - last_request_time[uid] < 1.0:
        await callback.answer("Подожди секунду!")
        return
    last_request_time[uid] = now

    if uid not in games:
        await callback.message.answer("Сначала /start")
        await callback.answer()
        return

    game = games[uid]
    data = callback.data
    action_taken = False

    if data == "action_1":
        if game.ap > 0:
            game.ap -= 1
            game.add_log("🔍 Ты пошёл в чащу... нашёл кору!")
            action_taken = True
        else:
            game.add_log("❌ Ты слишком устал!")
            action_taken = True
    elif data == "action_2":
        await callback.message.answer(game.get_inventory_text())
        await callback.answer()
        return
    elif data == "action_3":
        game.add_log("💧 Напился... жажда -20")
        game.thirst = max(0, game.thirst - 20)
        action_taken = True
    elif data == "action_4":
        game.add_log("🌙 Поспал... восстановил действия, голод +15")
        game.ap = 5
        game.hunger += 15
        action_taken = True
    elif data == "action_5":
        game.add_log("🧙 Мудрец дал совет... +5 кармы")
        game.karma += 5
        action_taken = True
    elif data == "action_6":
        chance = 10 + (game.karma // 10)
        if random.randint(1, 100) <= chance:
            await callback.message.answer(
                "🚁 ПОБЕДА! Ты сбежал из леса!\n\nНапиши /start для новой игры."
            )
            games.pop(uid, None)
            last_ui_msg_id.pop(uid, None)
            await callback.answer("Победа!")
            return
        else:
            game.add_log("Побег не удался... остаёмся в лесу")
            action_taken = True

    if action_taken:
        await callback.message.edit_text(
            game.get_ui(),
            reply_markup=inline_kb
        )
        await callback.answer()

# ──────────────────────────────────────────────────────────────────────────────
# 5. FASTAPI МАРШРУТЫ И ЖИЗНЕННЫЙ ЦИКЛ
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
            await bot.set_webhook(WEBHOOK_URL)
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