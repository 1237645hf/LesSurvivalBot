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

# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
TOKEN = "123456:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"          # ← ИЗМЕНИ ЭТУ СТРОКУ!
# ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑

BASE_URL = os.getenv("RENDER_EXTERNAL_URL")                     # Render сам подставит
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI(title="Forest Survival Telegram Bot")

# ──────────────────────────────────────────────────────────────────────────────
# SELF-PING каждые 5 минут (попытка удерживать Render free от засыпания)
# ──────────────────────────────────────────────────────────────────────────────

PING_INTERVAL_SECONDS = 300   # 5 минут

async def self_ping_task():
    if not BASE_URL:
        logging.info("Self-ping НЕ запущен — нет переменной RENDER_EXTERNAL_URL (локальный запуск?)")
        return

    ping_url = f"{BASE_URL}/ping"
    logging.info(f"Self-ping запущен: каждые {PING_INTERVAL_SECONDS//60} мин → {ping_url}")

    while True:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(ping_url, timeout=10.0)
                if r.status_code == 200:
                    logging.info(f"[SELF-PING] OK → {time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    logging.warning(f"[SELF-PING] статус {r.status_code}")
        except Exception as e:
            logging.error(f"[SELF-PING] ошибка: {str(e)}")

        await asyncio.sleep(PING_INTERVAL_SECONDS)

# ──────────────────────────────────────────────────────────────────────────────
# Простая игровая логика (можно сильно расширить)
# ──────────────────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        self.hp = 100
        self.hunger = 30
        self.thirst = 30
        self.ap = 5
        self.log = ["🌲 Ты проснулся в лесу. Что будешь делать?"]

    def get_ui(self):
        return (
            f"❤️ HP: {self.hp}   🍖 Голод: {self.hunger}   💧 Жажда: {self.thirst}\n"
            f"⚡ Очки действий: {self.ap}\n"
            "━" * 36 + "\n" +
            "\n".join(f"> {line}" for line in self.log[-4:]) + "\n" +
            "━" * 36
        )

games = {}  # user_id → Game

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="1 В чащу 🌲"),
            KeyboardButton(text="2 Инвентарь 🎒")
        ],
        [
            KeyboardButton(text="3 Пить воду 💧"),
            KeyboardButton(text="4 Спать 🌙")
        ],
        [
            KeyboardButton(text="5 Позвать мудреца 🧙"),
            KeyboardButton(text="6 Сбежать 🚁")
        ],
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
        "🌲 Добро пожаловать в лес выживания!\n\nВыбери действие кнопками ниже ↓",
        reply_markup=main_keyboard
    )
    await message.answer(games[uid].get_ui(), reply_markup=main_keyboard)

@dp.message()
async def any_message(message: Message):
    uid = message.from_user.id
    if uid not in games:
        await message.answer("Напиши /start чтобы начать игру")
        return

    game = games[uid]
    text = message.text.strip().lower()

    if "1" in text or "чащу" in text:
        if game.ap > 0:
            game.ap -= 1
            game.log.append("🔍 Ты пошёл в чащу... нашёл что-то полезное? (пока заглушка)")
        else:
            game.log.append("❌ Ты слишком устал!")
    elif "3" in text or "пить" in text:
        game.log.append("💧 Ты напился из ручья... жажда уменьшилась на 20")
        game.thirst = max(0, game.thirst - 20)
    elif "4" in text or "спать" in text:
        game.log.append("🌙 Ты поспал... восстановил силы, но проголодался")
        game.ap = 5
        game.hunger += 15
    else:
        game.log.append(f"Не понял команду: {message.text}")

    await message.answer(game.get_ui(), reply_markup=main_keyboard)

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI маршруты
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
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook установлен → {WEBHOOK_URL}")
    asyncio.create_task(self_ping_task())

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Webhook удалён")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
