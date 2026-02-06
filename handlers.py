from aiogram import types
from aiogram.filters import CommandStart
from game import Game
from utils import clear_chat
from state import games, last_ui_msg_id, last_inv_msg_id, last_request_time

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

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
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