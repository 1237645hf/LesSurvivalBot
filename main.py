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

# ──────────────────────────────────────────────────────────────────────────────
# 2. SELF-PING (защита от засыпания на Render)
# ──────────────────────────────────────────────────────────────────────────────

PING_INTERVAL_SECONDS = 300

async def self_ping_task():
    if not BASE_URL:
        logging.info("Self-ping отключён (локальный запуск)")
        return
    ping_url = f"{BASE_URL}/ping"
    logging.info(f"Self-ping запущен (каждые 5 мин → {ping_url})")
    while True:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(ping_url, timeout=10)
                if r.status_code == 200:
                    logging.info(f"[SELF-PING] OK → {time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    logging.warning(f"[SELF-PING] статус {r.status_code}")
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

# ──────────────────────────────────────────────────────────────────────────────
# 4. ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ──────────────────────────────────────────────────────────────────────────────

games = {}
last_ui_msg_id = {}   # user_id → message_id последнего сообщения с состоянием

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
# 5. ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id

    # Удаляем все предыдущие сообщения бота в чате (кроме самой команды /start)
    try:
        chat_history = await bot.get_chat_history(message.chat.id, limit=30)
        for msg in chat_history:
            if msg.from_user and msg.from_user.id == (await bot.get_me()).id:
                if msg.message_id != message.message_id:  # не удаляем саму команду /start
                    await bot.delete_message(message.chat.id, msg.message_id)
    except Exception as e:
        logging.warning(f"Очистка чата не удалась: {e}")

    # Создаём новую игру
    games[uid] = Game()

    # Приветствие
    await message.answer(
        "🌲 Добро пожаловать в лес выживания!\n\nВыбери действие кнопками ниже ↓",
        reply_markup=main_keyboard
    )

    # Отправляем состояние
    ui_msg = await message.answer(games[uid].get_ui(), reply_markup=main_keyboard)
    last_ui_msg_id[uid] = ui_msg.message_id

@dp.message()
async def any_message(message: Message):
    uid = message.from_user.id
    if uid not in games:
        await message.answer("Напиши /start чтобы начать игру")
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
        return
    elif "3" in text or "пить" in text:
        game.add_log("💧 Напился... жажда -20")
        game.thirst = max(0, game.thirst - 20)
        action_taken = True
    elif "4" in text or "спать" in text:
        game.add_log("🌙 Поспал... восстановил действия, голод +15")
        game.ap = 5
        game.hunger += 15
        action_taken = True
    elif "5" in text or "мудрец" in text:
        game.add_log("🧙 Мудрец дал совет... +5 кармы")
        game.karma += 5
        action_taken = True
    elif "6" in text or "сбежать" in text:
        chance = 10 + (game.karma // 10)
        if random.randint(1, 100) <= chance:
            await message.answer(
                "🚁 ПОБЕДА! Ты сбежал из леса!\n\nНапиши /start для новой игры.",
                reply_markup=main_keyboard
            )
            games.pop(uid, None)
            last_ui_msg_id.pop(uid, None)
            return
        else:
            game.add_log("Побег не удался... остаёмся в лесу")
            action_taken = True
    else:
        await message.answer("Нажми кнопку с номером!", reply_markup=main_keyboard)
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
            logging.warning(f"edit_message_text failed: {e}")
            new_msg = await message.answer(game.get_ui(), reply_markup=main_keyboard)
            last_ui_msg_id[uid] = new_msg.message_id

# ──────────────────────────────────────────────────────────────────────────────
# 6. FASTAPI МАРШРУТЫ
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

# ──────────────────────────────────────────────────────────────────────────────
# 7. STARTUP И SHUTDOWN
# ──────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    if WEBHOOK_URL:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logging.info("Старый webhook удалён")
        except Exception as e:
            logging.warning(f"delete_webhook: {e}")

        try:
            await bot.set_webhook(WEBHOOK_URL)
            logging.info(f"Webhook успешно установлен: {WEBHOOK_URL}")
        except Exception as e:
            logging.error(f"Ошибка установки webhook: {e}")
    else:
        logging.error("BASE_URL не найден → webhook не установлен!")

    asyncio.create_task(self_ping_task())

@app.on_event("shutdown")
async def on_shutdown():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Webhook удалён")
    except Exception as e:
        logging.warning(f"shutdown delete_webhook: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# 8. ЗАПУСК
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)