from aiogram import types
from game import Game
from utils import get_pogoda, clear_chat
from aiogram.filters import CommandStart

games = {}
last_ui_msg_id = {}

# Основные inline-кнопки (без цифр)
main_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="В чащу 🌲", callback_data="action_1"),
        InlineKeyboardButton(text="Инвентарь 🎒", callback_data="action_2"),
    ],
    [
        InlineKeyboardButton(text="Пить воду 💧", callback_data="action_3"),
        InlineKeyboardButton(text="Спать 🌙", callback_data="action_4"),
    ],
    [
        InlineKeyboardButton(text="📱ловить сигнал📱", callback_data="action_5"),
        InlineKeyboardButton(text="Сбежать 🚁", callback_data="action_6"),
    ],
])

# Кнопки для старта игры
start_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🫡 Я готов 🫡", callback_data="start_game")],
])

# ──────────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    await clear_chat(message.chat.id)

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
        reply_markup=start_inline_kb
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
        await callback.message.edit_text(
            "Игра началась!\n\nВыбери действие ниже ↓"
        )

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
            game.add_log("🔍 Ты пошёл в чащу... нашёл кору!")
            action_taken = True
        else:
            game.add_log("🏕 У тебя нет сил и нужно отдохнуть")
            action_taken = True
    elif data == "action_2":
        await callback.message.answer(game.get_inventory_text(), reply_markup=inventory_inline_kb)
        await callback.answer()
        return
    elif data == "action_3":
        game.add_log("💧 Напился... жажда -20")
        game.thirst = max(0, game.thirst - 20)
        action_taken = True
    elif data == "action_4":
        game.day += 1
        game.ap = 5
        game.hunger = max(0, game.hunger -15)
        game.add_log(f"🌙 День {game.day}. Выспался, голод -15")
        action_taken = True
    elif data == "action_5":
        game.add_log("🧙 Мудрец дал совет... +5 кармы")
        game.karma += 5
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
    elif data == "inv_back":
        await callback.message.edit_text(game.get_ui(), reply_markup=main_inline_kb)
        await callback.answer()
        return

    if action_taken:
        await callback.message.edit_text(
            game.get_ui(),
            reply_markup=main_inline_kb
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