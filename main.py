import asyncio
import logging
import os
import time
import random
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
    raise ValueError("TOKEN не найден в переменных окружения Render!")

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
# SELF-PING каждые 5 минут
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
            logging.error(f"[SELF-PING] ошибка: {str(e)}")
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
        if not self.inventory:
            return "🎒 Инвентарь пуст"
        return "🎒 Инвентарь:\n" + "\n".join(f"• {item}" for item in self.inventory)

games = {}
last_ui_msg_id = {}  # user_id → message_id последнего состояния

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
        "🌲 Добро пожаловать в лес выживания!\nВыбери действие кнопками ниже ↓",
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
            game.add_log("🔍 Ты пошёл в чащу... нашёл кору!")
            action_taken = True
        else:
            game.add_log("❌ Ты слишком устал!")
            action_taken = True
    elif "2" in text or "инвентарь" in text:
        await message.answer(game.get_inventory_text(), reply_markup=main_keyboard)
        return  # не трогаем основное состояние
    elif "3" in text or "пить" in text:
        game.add_log("💧 Напился из ручья... жажда -20")
        game.thirst = max(0, game.thirst - 20)
        action_taken = True
    elif "4" in text or "спать" in text:
        game.add_log("🌙 Поспал... восстановил действия, но голод +15")
        game.ap = 5
        game.hunger += 15
        action_taken = True
    elif "5" in text or "мудрец" in text:
        game.add_log("🧙 Мудрец дал тебе совет... +5 кармы")
        game.karma += 5
        action_taken = True
    elif "6" in text or "сбежать" in text:
        chance = 10 + (game.karma // 10)  # шанс 10% + бонус от кармы
        if random.randint(1, 100) <= chance:
            await message.answer(
                "🚁 ПОБЕДА! Ты успешно сбежал из леса!\n\n"
                "Игра окончена. Напиши /start, чтобы начать заново.",
                reply_markup=main_keyboard
            )
            if uid in games:
                del games[uid]
            if uid in last_ui_msg_id:
                try:
                    await bot.delete_message(message.chat.id, last_ui_msg_id[uid])
                except:
                    pass
            return
        else:
            game.add_log("Побег не удался... остаёмся в лесу")
            action_taken = True
    else:
        await message.answer("Выбери действие кнопкой!", reply_markup=main_keyboard)
        return

    if action_taken:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_ui_msg_id[uid],
                text=game.get_ui(),
                reply_markup=main_keyboard
            )
        except Exception as e:
            logging.warning(f"edit_message_text не удалось: {e}")
            # если редактирование провалилось — отправляем новое
            new_msg = await message.answer(game.get_ui(), reply_markup=main_keyboard)
            last_ui_msg_id[uid] = new_msg.message_id

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
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except:
            pass
        try:
            await bot.set_webhook(WEBHOOK_URL)
            logging.info(f"Webhook установлен: {WEBHOOK_URL}")
        except Exception as e:
            logging.error(f"Ошибка установки webhook: {e}")
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
