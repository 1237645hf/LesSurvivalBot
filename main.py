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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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
last_request_time = {}  # Антифлуд

# ──────────────────────────────────────────────────────────────────────────────
# MONGODB
# ──────────────────────────────────────────────────────────────────────────────
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client['forest_game']
    players_collection = db['players']
    mongo_client.server_info()
    logging.info("MongoDB подключён успешно")
except Exception as e:
    logging.error(f"Ошибка MongoDB: {e}")
    raise

# ──────────────────────────────────────────────────────────────────────────────
# СОСТОЯНИЯ FSM
# ──────────────────────────────────────────────────────────────────────────────
class GameStates(StatesGroup):
    main = State()
    inventory = State()
    character = State()

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
        self.day = 1
        self.log = ["🌲 Ты проснулся в лесу. Что будешь делать?"]
        self.inventory = Counter({
            "Спички 🔥": 1,
            "Вилка 🍴": 1,
            "Кусок коры 🪵": 1,
            "Сухпай": 3,
            "Бутылка воды": 10
        })
        self.weather = "clear"
        self.location = "лес"
        self.unlocked_locations = ["лес", "тёмный лес", "озеро", "заброшенный лагерь"]
        self.water_capacity = 10
        # Снаряжение для персонажа (заглушки)
        self.equipment = {
            "голова": None,
            "торс": None,
            "спина": None,
            "правая рука": None,
            "левая рука": None,
            "ноги": None,
            "ботинки": None,
            "питомец": None
        }

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    def get_ui(self):
        weather_icon = {"clear": "☀️", "cloudy": "☁️", "rain": "🌧️"}.get(self.weather, "☀️")
        return (
            f"❤️ {self.hp} 🍖 {self.hunger} 💧 {self.thirst} ⚡ {self.ap} {weather_icon} {self.day}\n"
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

    def get_character_text(self):
        eq_text = "\n".join(f"{slot.capitalize()}: {item or 'Пусто'}" for slot, item in self.equipment.items())
        return f"👤 Персонаж:\nСнаряжение:\n{eq_text}"

# ──────────────────────────────────────────────────────────────────────────────
# СОХРАНЕНИЕ / ЗАГРУЗКА
# ──────────────────────────────────────────────────────────────────────────────
def load_game(uid: int) -> Game | None:
    try:
        data = players_collection.find_one({"_id": uid})
        if data and "game_data" in data:
            game = Game()
            inv_dict = data["game_data"].pop("inventory", {})
            eq_dict = data["game_data"].pop("equipment", {})
            game.__dict__.update(data["game_data"])
            game.inventory = Counter(inv_dict)
            game.equipment = eq_dict
            return game
    except Exception as e:
        logging.error(f"Ошибка загрузки {uid}: {e}")
    return None

def save_game(uid: int, game: Game):
    try:
        data = game.__dict__.copy()
        data["inventory"] = dict(game.inventory)
        data["equipment"] = game.equipment
        players_collection.update_one(
            {"_id": uid},
            {"$set": {"game_data": data}},
            upsert=True
        )
    except Exception as e:
        logging.error(f"Ошибка сохранения {uid}: {e}")

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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        loc_row,
        [InlineKeyboardButton(text="🔍 Исследовать ", callback_data="action_1"),
         InlineKeyboardButton(text="🎒 Инвентарь ", callback_data="action_2")],
        [InlineKeyboardButton(text=f"💧 Пить воду ({game.inventory['Бутылка воды']}/{game.water_capacity})", callback_data="action_3")
         if game.inventory['Бутылка воды'] > 0 else InlineKeyboardButton(text="💧 Пить воду (пусто)", callback_data="action_3"),
         InlineKeyboardButton(text="🌙 Спать ", callback_data="action_4")]
    ])
    if game.weather == "rain":
        kb.inline_keyboard.append([InlineKeyboardButton(text="🌧️ Собрать воду ", callback_data="action_collect_water")])
    return kb

inventory_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👁️ Осмотреть ", callback_data="inv_inspect"),
     InlineKeyboardButton(text="🛠️ Использовать ", callback_data="inv_use")],
    [InlineKeyboardButton(text="🗑️ Выкинуть ", callback_data="inv_drop"),
     InlineKeyboardButton(text="🛠️ Крафт ", callback_data="inv_craft")],
    [InlineKeyboardButton(text="👤 Персонаж ", callback_data="inv_character"),
     InlineKeyboardButton(text="← Назад ", callback_data="inv_back")],
])

character_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="← Назад ", callback_data="character_back")],
])  # Можно добавить кнопки для экипировки позже

start_continue_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔑 Загрузить игру", callback_data="load_game")],
    [InlineKeyboardButton(text="🎭 Начать новую", callback_data="new_game")],
])

start_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🫡 Я готов ", callback_data="start_game")]
])

# ──────────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    uid = message.from_user.id
    chat_id = message.chat.id
    message_id = message.message_id
    # Удаляем только свои сообщения выше (до 50)
    for i in range(1, 51):
        try:
            await bot.delete_message(chat_id, message_id - i)
        except Exception:
            pass  # Если не наше или не существует — пропускаем
    # Проверяем сохранение
    loaded = load_game(uid)
    if loaded:
        await state.set_state(GameStates.main)
        await state.update_data(game=loaded.__dict__)  # Временно в FSM, но сохраним в Mongo
        await message.answer(
            "У тебя есть сохранённая игра. Что хочешь?",
            reply_markup=start_continue_kb
        )
    else:
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
async def process_callback(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    chat_id = callback.message.chat.id
    now = time.time()
    if uid in last_request_time and now - last_request_time[uid] < 1.0:
        await callback.answer("Подожди секунду!")
        return
    last_request_time[uid] = now
    data = callback.data
    current_state = await state.get_state()
    state_data = await state.get_data()
    game_dict = state_data.get('game')
    if not game_dict:
        game = load_game(uid)
        if not game:
            await callback.message.answer("Сначала начни игру /start")
            await callback.answer()
            return
        game_dict = game.__dict__.copy()
        game_dict['inventory'] = dict(game.inventory)
        game_dict['equipment'] = game.equipment
        await state.update_data(game=game_dict)
    else:
        # Восстанавливаем game из state_data
        game = Game()
        game.__dict__.update(game_dict)
        game.inventory = Counter(game_dict['inventory'])
        game.equipment = game_dict['equipment']
    current_msg_id = state_data.get('current_msg_id')

    action_taken = False
    edit_current = False

    if data in ("start_game", "new_game"):
        game = Game()
        await state.set_state(GameStates.main)
        await state.update_data(game=game.__dict__.copy(), current_msg_id=None)
        state_data['game']['inventory'] = dict(game.inventory)
        state_data['game']['equipment'] = game.equipment
        save_game(uid, game)
        try:
            if current_msg_id:
                await bot.delete_message(chat_id, current_msg_id)
        except:
            pass
        ui_msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        await state.update_data(current_msg_id=ui_msg.message_id)
        await callback.answer()
        return

    if data == "load_game":
        game = load_game(uid)
        if not game:
            game = Game()
            save_game(uid, game)
        await state.set_state(GameStates.main)
        await state.update_data(game=game.__dict__.copy(), current_msg_id=None)
        state_data['game']['inventory'] = dict(game.inventory)
        state_data['game']['equipment'] = game.equipment
        try:
            if current_msg_id:
                await bot.delete_message(chat_id, current_msg_id)
        except:
            pass
        ui_msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        await state.update_data(current_msg_id=ui_msg.message_id)
        await callback.answer()
        return

    if not game:
        await callback.answer()
        return

    # Обработка в зависимости от состояния
    if current_state == GameStates.main:
        if data.startswith("loc_") or data in ("action_1", "action_3", "action_4", "action_collect_water"):
            # Действия в главном окне - edit
            edit_current = True
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
                    game.add_log("🌧️ Дождь льёт стеной, исследовать нельзя...")
                elif game.ap > 0:
                    game.ap -= 1
                    game.hunger = max(0, game.hunger - 7)
                    game.thirst = max(0, game.thirst - 8)
                    events = [
                        ("Нашёл ягоды! +10 сытости", lambda: setattr(game, 'hunger', min(100, game.hunger + 10))),
                        ("Нашёл мухоморы (предмет)", lambda: game.inventory.update({"Мухоморы": game.inventory["Мухоморы"] + 1})),
                        ("Нашёл родник! Наполнил бутылку +3 глотка", lambda: game.inventory.update({"Бутылка воды": min(game.water_capacity, game.inventory["Бутылка воды"] + 3)})),
                        ("Укус змеи! -5 HP", lambda: setattr(game, 'hp', max(0, game.hp - 5))),
                        ("Нашёл кору", lambda: game.inventory.update({"Кусок коры 🪵": game.inventory["Кусок коры 🪵"] + 1})),
                        ("Нашёл ветку", lambda: game.inventory.update({"Ветка": game.inventory["Ветка"] + 1})),
                        ("Нашёл нож", lambda: game.inventory.update({"Нож": game.inventory["Нож"] + 1}))
                    ]
                    event_text, event_effect = random.choice(events)
                    event_effect()
                    game.add_log(f"🔍 Ты пошёл исследовать... {event_text}")
                else:
                    game.add_log("🏕 У тебя нет сил и нужно отдохнуть")
                action_taken = True
            elif data == "action_3":
                if game.inventory["Бутылка воды"] > 0:
                    game.inventory["Бутылка воды"] -= 1
                    game.thirst = min(100, game.thirst + 20)
                    game.add_log(f"💧 Напился... жажда +20 (осталось {game.inventory['Бутылка воды']}/{game.water_capacity})")
                else:
                    game.add_log("💧 Бутылка пуста, найди источник!")
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
            elif data == "action_collect_water":
                if game.weather == "rain":
                    added = 40
                    game.inventory["Бутылка воды"] = min(game.water_capacity, game.inventory["Бутылка воды"] + added)
                    game.add_log(f"🌧️ Собрал дождевую воду... +{added} (теперь {game.inventory['Бутылка воды']}/{game.water_capacity})")
                else:
                    game.add_log("Сейчас не идёт дождь...")
                action_taken = True
        elif data == "action_2":
            # Переход в инвентарь: delete main, send inventory
            try:
                await bot.delete_message(chat_id, current_msg_id)
            except:
                pass
            submenu_msg = await callback.message.answer(game.get_inventory_text(), reply_markup=inventory_inline_kb)
            await state.set_state(GameStates.inventory)
            await state.update_data(current_msg_id=submenu_msg.message_id)
            await callback.answer()
            return

    elif current_state == GameStates.inventory:
        if data in ("inv_inspect", "inv_use", "inv_drop", "inv_craft"):
            # Действия в инвентаре - edit (заглушки)
            edit_current = True
            game.add_log(f"{data.replace('inv_', '').capitalize()}... (заглушка)")
            action_taken = True
        elif data == "inv_character":
            # Переход в персонаж: delete inventory, send character
            try:
                await bot.delete_message(chat_id, current_msg_id)
            except:
                pass
            char_msg = await callback.message.answer(game.get_character_text(), reply_markup=character_inline_kb)
            await state.set_state(GameStates.character)
            await state.update_data(current_msg_id=char_msg.message_id)
            await callback.answer()
            return
        elif data == "inv_back":
            # Назад в main: delete inventory, send main
            try:
                await bot.delete_message(chat_id, current_msg_id)
            except:
                pass
            ui_msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
            await state.set_state(GameStates.main)
            await state.update_data(current_msg_id=ui_msg.message_id)
            await callback.answer()
            return

    elif current_state == GameStates.character:
        if data == "character_back":
            # Назад в inventory: delete character, send inventory
            try:
                await bot.delete_message(chat_id, current_msg_id)
            except:
                pass
            submenu_msg = await callback.message.answer(game.get_inventory_text(), reply_markup=inventory_inline_kb)
            await state.set_state(GameStates.inventory)
            await state.update_data(current_msg_id=submenu_msg.message_id)
            await callback.answer()
            return

    if action_taken:
        # Сохраняем game в Mongo после действия
        save_game(uid, game)
        # Обновляем state_data
        await state.update_data(game=game.__dict__.copy())
        state_data['game']['inventory'] = dict(game.inventory)
        state_data['game']['equipment'] = game.equipment

    if edit_current and action_taken:
        try:
            if current_state == GameStates.main:
                await bot.edit_message_text(
                    game.get_ui(),
                    chat_id,
                    current_msg_id,
                    reply_markup=get_main_kb(game)
                )
            elif current_state == GameStates.inventory:
                await bot.edit_message_text(
                    game.get_inventory_text(),
                    chat_id,
                    current_msg_id,
                    reply_markup=inventory_inline_kb
                )
            # Для character пока нет edit, только назад
        except Exception as e:
            logging.warning(f"Edit failed: {e}")
            # Если edit не удался, отправляем новое и обновляем ID
            try:
                await bot.delete_message(chat_id, current_msg_id)
            except:
                pass
            if current_state == GameStates.main:
                new_msg = await bot.send_message(chat_id, game.get_ui(), reply_markup=get_main_kb(game))
            elif current_state == GameStates.inventory:
                new_msg = await bot.send_message(chat_id, game.get_inventory_text(), reply_markup=inventory_inline_kb)
            await state.update_data(current_msg_id=new_msg.message_id)

    await callback.answer()

# ──────────────────────────────────────────────────────────────────────────────
# SELF-PING + WEBHOOK
# ──────────────────────────────────────────────────────────────────────────────
PING_INTERVAL_SECONDS = 300  # 5 минут, как просил
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
