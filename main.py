import asyncio
import logging
import os
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
import httpx

# ──────────────────────────────────────────────────────────────────────────────
# НАСТРОЙКИ
# ──────────────────────────────────────────────────────────────────────────────

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден! Добавь в Environment Variables на Render")

BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

logging.basicConfig(level=logging.INFO)
logging.info(f"Бот стартует с TOKEN: {TOKEN[:10]}...")
logging.info(f"BASE_URL: {BASE_URL}")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI(title="Forest Survival Bot")

# ──────────────────────────────────────────────────────────────────────────────
# SELF-PING
# ──────────────────────────────────────────────────────────────────────────────

PING_INTERVAL_SECONDS = 300

async def self_ping_task():
    if not BASE_URL:
        logging.info("Self-ping НЕ запущен")
        return
    ping_url = f"{BASE_URL}/ping"
    logging.info(f"Self-ping каждые 5 мин → {ping_url}")
    while True:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(ping_url, timeout=10.0)
                if r.status_code == 200:
                    logging.info(f"[SELF-PING] OK → {time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            logging.error(f"[SELF-PING] ошибка: {e}")
        await asyncio.sleep(PING_INTERVAL_SECONDS)

# ──────────────────────────────────────────────────────────────────────────────
# Игра
# ──────────────────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        self.hp = 100
        self.hunger = 30
        self.thirst = 30
        self.ap = 5
        self.log = ["🌲 Ты проснулся в лесу. Что будешь делать?"]

    def get_ui(self):
        # ТОЛЬКО ОДИН блок состояния — без повторений!
        ui_text = (
            f"❤️ HP: {self.hp}   🍖 Голод: {self.hunger}   💧 Жажда: {self.thirst}\n"
            f"⚡ Очки действий: {self.ap}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(f"> {line}" for line in self.log[-5:]) + "\n"
            + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        return ui_text

games = {}
last_ui_msg_id = {}  # user_id → message_id последнего UI

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1 В чащу 🌲"), KeyboardButton(text="2 Инвентарь 🎒")],
        [KeyboardButton(text="3 Пить воду 💧"), KeyboardButton(text="4 Спать 🌙")],
        [KeyboardButton(text="5 Позвать мудреца 🧙"), KeyboardButton(text="6 Сбежать 🚁")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выбери действие..."
)

# ──────────────────────────────────────────────────────────────────────────────
# Хендлеры
# ──────────────────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    games[uid] = Game()

    await message.answer(
        "🌲 Добро пожаловать в лес выживания!\nВыбери действие ↓",
        reply_markup=main_keyboard
    )

    ui_msg = await message.answer(games[uid].get_ui(), reply_markup=main_keyboard)
    last_ui_msg_id[uid] = ui_msg.message_id

@dp.message()
async def any_message(message: Message):
    uid = message.from_user.id
    if uid not in games:
        await message.answer("Напиши /start")
        return

    game = games[uid]
    text = message.text.strip().lower()
    action_taken = False

    if "1" in text or "чащу" in text:
        if game.ap > 0:
            game.ap -= 1
            game.log.append("🔍 Ты пошёл в чащу... нашёл кору! (заглушка)")
            action_taken = True
        else:
            game.log.append("❌ Устал — нужно поспать")
            action_taken = True
    elif "3" in text or "пить" in text:
        game.log.append("💧 Напился из ручья... жажда -20")
        game.thirst = max(0, game.thirst - 20)
        action_taken = True
    elif "4" in text or "спать" in text:
        game.log.append("🌙 Поспал... восстановил действия, но голод +15")
        game.ap = 5
        game.hunger += 15
        action_taken = True
    elif "5" in text or "мудрец" in text:
        game.log.append("🧙 Мудрец молчит... нужно больше кармы (заглушка)")
        action_taken = True
    elif "6" in text or "сбежать" in text:
        game.log.append("🚁 Побег провалился... пока остаёмся в лесу")
        action_taken = True
    else:
        await message.answer("Нажми кнопку с номером действия!", reply_markup=main_keyboard)
        return

    if action_taken:
        # Удаляем старое сообщение с UI
        if uid in last_ui_msg_id:
            try:
                await bot.delete_message(message.chat.id, last_ui_msg_id[uid])
            except Exception:
                pass

        # Отправляем новое состояние
        new_msg = await message.answer(game.get_ui(), reply_markup=main_keyboard)
        last_ui_msg_id[uid] = new_msg.message_id

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI
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
