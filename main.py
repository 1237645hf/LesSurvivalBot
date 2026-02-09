import asyncio
import logging
import os
import time
import random
from collections import Counter
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import CommandStart, Text
import httpx
from pymongo import MongoClient

# ──────────────────────────────────────────────────────────────────────────────
# НАСТРОЙКИ
# ──────────────────────────────────────────────────────────────────────────────
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден!")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI не найден!")

logging.basicConfig(level=logging.INFO)
logging.info(f"Бот запущен. TOKEN: {TOKEN[:10]}... BASE_URL: {BASE_URL}")

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI(title="Forest Survival Bot")

last_request_time = {}
last_ui_msg_id = {}
last_submenu_msg_id = {}

# ──────────────────────────────────────────────────────────────────────────────
# MONGODB
# ──────────────────────────────────────────────────────────────────────────────
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['forest_game']
players_collection = db['players']
mongo_client.server_info()
logging.info("MongoDB подключён успешно")

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
        self.karma_goal = 100
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
        self.equipment = {
            "head": None,
            "torso": None,
            "back": None,
            "pants": None,
            "boots": None,
            "trinket": None,
            "pet": None,
            "hand": None          # ← новый слот под факел и возможно оружие позже
        }
        self.story_state = None   # "wolf_scene", "cat_name_wait", None
        self.found_branch_once = False

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    def get_ui(self):
        weather_icon = {"clear": "☀️", "cloudy": "☁️", "rain": "🌧️"}.get(self.weather, "☀️")
        karma_str = f"🕊️ {self.karma}/{self.karma_goal}"
        return (
            f"❤️ {self.hp} 🍖 {self.hunger} 💧 {self.thirst} ⚡ {self.ap} {weather_icon} {self.day} {karma_str}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(f"> {line}" for line in self.log) + "\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

    def get_inventory_text(self):
        lines = []
        for item, count in self.inventory.items():
            if count > 0:
                marker = " ✦" if item in ("Факел",) else ""   # можно использовать
                lines.append(f"• {item} x{count}{marker}" if count > 1 else f"• {item}{marker}")
        return "🎒 Инвентарь:\n" + "\n".join(lines) if lines else "🎒 Инвентарь пуст"

    def get_character_text(self):
        lines = []
        slots = {
            "head": "Голова",
            "torso": "Торс",
            "back": "Спина",
            "pants": "Штаны",
            "boots": "Ботинки",
            "trinket": "Безделушка",
            "pet": "Питомец",
            "hand": "Рука"
        }
        for slot, name in slots.items():
            item = self.equipment.get(slot)
            lines.append(f"{name}: {item if item else 'Пусто'}")
        return "👤 Персонаж:\n\n" + "\n".join(lines)

# ──────────────────────────────────────────────────────────────────────────────
# СОХРАНЕНИЕ / ЗАГРУЗКА
# ──────────────────────────────────────────────────────────────────────────────
def load_game(uid: int) -> Game | None:
    try:
        data = players_collection.find_one({"_id": uid})
        if data and "game_data" in data:
            game = Game()
            inv_dict = data["game_data"].pop("inventory", {})
            equip_dict = data["game_data"].pop("equipment", {})
            game.__dict__.update(data["game_data"])
            game.inventory = Counter(inv_dict)
            game.equipment = equip_dict
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
        loc_row.append(InlineKeyboardButton(text=f"← {loc_icons[current_idx-1]}", callback_data=f"loc_{locations[current_idx-1]}"))
    loc_row.append(InlineKeyboardButton(text=f"{loc_icons[current_idx]} {game.location.capitalize()}", callback_data="loc_current"))
    if current_idx < len(locations)-1:
        next_loc = locations[current_idx+1]
        if next_loc in game.unlocked_locations:
            loc_row.append(InlineKeyboardButton(text=f"{loc_icons[current_idx+1]} →", callback_data=f"loc_{next_loc}"))
        else:
            loc_row.append(InlineKeyboardButton(text=f"{loc_icons[current_idx+1]} ×", callback_data="loc_locked"))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        loc_row,
        [InlineKeyboardButton(text="🔍 Исследовать", callback_data="action_1"),
         InlineKeyboardButton(text="🎒 Инвентарь", callback_data="action_2")],
        [InlineKeyboardButton(text=f"💧 Пить ({game.inventory['Бутылка воды']}/{game.water_capacity})", callback_data="action_3")
         if game.inventory['Бутылка воды'] > 0 else InlineKeyboardButton(text="💧 Пить (пусто)", callback_data="action_3"),
         InlineKeyboardButton(text="🌙 Спать", callback_data="action_4")]
    ])
    if game.weather == "rain":
        kb.inline_keyboard.append([InlineKeyboardButton(text="🌧️ Собрать воду", callback_data="action_collect_water")])
    return kb

inventory_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👁️ Осмотреть", callback_data="inv_inspect"),
     InlineKeyboardButton(text="🛠️ Использовать", callback_data="inv_use")],
    [InlineKeyboardButton(text="🗑️ Выкинуть", callback_data="inv_drop"),
     InlineKeyboardButton(text="🛠️ Крафт", callback_data="inv_craft")],
    [InlineKeyboardButton(text="👤 Персонаж", callback_data="inv_character"),
     InlineKeyboardButton(text="← Назад", callback_data="inv_back")],
])

character_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="← Назад", callback_data="character_back")]
])

story_wolf_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Сбежать от волка", callback_data="story_wolf_flee")],
    [InlineKeyboardButton(text="Использовать факел", callback_data="story_wolf_fight")]
])

story_peek_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Заглянуть под пень", callback_data="story_peek")]
])

story_cat_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Оставить его здесь", callback_data="story_cat_leave")],
    [InlineKeyboardButton(text="Забрать с собой", callback_data="story_cat_take")]
])

story_next_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Дальше", callback_data="story_next")]
])

# ──────────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    # чистим старые сообщения (опционально)
    try:
        for i in range(1, 40):
            await bot.delete_message(message.chat.id, message.message_id - i)
    except:
        pass

    game = load_game(uid)
    if game:
        games[uid] = game
        await message.answer("Есть сохранение. Продолжить?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Продолжить", callback_data="load_game")],
            [InlineKeyboardButton(text="Новая игра", callback_data="new_game")]
        ]))
    else:
        await message.answer(
            "🌲 Ты открыл глаза. Вокруг лес. Холодно. Хочется есть.\n\n"
            "Выживи.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Начать", callback_data="new_game")]
            ])
        )

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    now = time.time()
    if uid in last_request_time and now - last_request_time[uid] < 0.8:
        await callback.answer("Подожди немного...")
        return
    last_request_time[uid] = now

    data = callback.data
    game = games.get(uid)
    if not game:
        await callback.answer("Сначала начни игру")
        return

    chat_id = callback.message.chat.id

    # Удаляем подменю при переходе
    if data in ("action_2", "inv_character", "inv_back", "character_back", "story_") and uid in last_submenu_msg_id:
        try:
            await bot.delete_message(chat_id, last_submenu_msg_id[uid])
            del last_submenu_msg_id[uid]
        except:
            pass

    # ─── НОВАЯ ИГРА ────────────────────────────────────────
    if data in ("new_game", "start_game"):
        game = Game()
        games[uid] = game
        save_game(uid, game)
        if uid in last_ui_msg_id:
            try:
                await bot.delete_message(chat_id, last_ui_msg_id[uid])
            except:
                pass
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id
        await callback.answer()
        return

    # ─── ЗАГРУЗКА ──────────────────────────────────────────
    if data == "load_game":
        game = load_game(uid) or Game()
        games[uid] = game
        save_game(uid, game)
        if uid in last_ui_msg_id:
            try:
                await bot.delete_message(chat_id, last_ui_msg_id[uid])
            except:
                pass
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id
        await callback.answer()
        return

    # ─── ДЕЙСТВИЯ НА ГЛАВНОМ ЭКРАНЕ ───────────────────────
    action_taken = False

    if data == "action_1":  # Исследовать
        if game.ap <= 0:
            game.add_log("Нет сил. Нужно поспать.")
        else:
            game.ap -= 1
            game.hunger = max(0, game.hunger - 7)
            game.thirst = max(0, game.thirst - 8)

            if game.equipment.get("hand") == "Факел" and game.story_state is None:
                # Запускаем сюжет
                game.story_state = "wolf_scene"
                if uid in last_ui_msg_id:
                    try:
                        await bot.delete_message(chat_id, last_ui_msg_id[uid])
                        del last_ui_msg_id[uid]
                    except:
                        pass
                msg = await callback.message.answer(
                    "Ты слышишь хриплое рычание и звук рвущейся земли.\n"
                    "Осторожно выглядываешь из-за дерева.\n\n"
                    "Старый, истощённый волк яростно копает под пнём.\n"
                    "Рёбра торчат, один глаз мутный.\n\n"
                    "Твои действия:",
                    reply_markup=story_wolf_kb
                )
                last_submenu_msg_id[uid] = msg.message_id
            else:
                # обычное исследование
                events = [
                    ("Нашёл ягоды! +10 сытости", lambda: setattr(game, 'hunger', min(100, game.hunger + 10))),
                    ("Нашёл мухоморы", lambda: game.inventory.update({"Мухоморы": game.inventory["Мухоморы"] + 1})),
                    ("Нашёл родник → +3 воды", lambda: game.inventory.update({"Бутылка воды": min(game.water_capacity, game.inventory["Бутылка воды"] + 3)})),
                    ("Укус насекомого –5 HP", lambda: setattr(game, 'hp', max(0, game.hp - 5))),
                    ("Нашёл кору", lambda: game.inventory.update({"Кусок коры 🪵": game.inventory["Кусок коры 🪵"] + 1})),
                    ("Нашёл ветку", lambda: game.inventory.update({"Ветка": game.inventory["Ветка"] + 1})),
                    ("Нашёл нож", lambda: game.inventory.update({"Нож": game.inventory["Нож"] + 1}))
                ]
                text, effect = random.choice(events)
                effect()
                game.add_log(f"🔍 Исследовал... {text}")

                # Первая ветка → мысль про факел (только один раз)
                if "Ветка" in text and not game.found_branch_once:
                    game.found_branch_once = True
                    game.add_log("А из этого можно сделать факел?")
        action_taken = True

    # ─── ИСТОРИЯ ───────────────────────────────────────────
    elif data == "story_wolf_flee":
        game.add_log("Ты тихо отступил. Что бы там ни было — не твоё дело.")
        game.story_state = None
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id
        await callback.answer("Ок")

    elif data == "story_wolf_fight":
        game.add_log("Ты размахнулся и ударил волка горящим факелом по морде.")
        game.add_log("Шерсть вспыхнула, зверь взвыл и бросился в чащу.")
        game.equipment["hand"] = None  # факел сломался
        game.inventory["Факел"] = game.inventory["Факел"] - 1 if game.inventory["Факел"] > 0 else 0
        msg = await callback.message.answer(
            "Факел догорел и рассыпался угольками.\n\n"
            "Теперь под пнём открыта яма...",
            reply_markup=story_peek_kb
        )
        last_submenu_msg_id[uid] = msg.message_id
        game.story_state = "after_fight"

    elif data == "story_peek":
        msg = await callback.message.answer(
            "Ты наклоняешься. В темноте ямы блестят два испуганных глаза.\n"
            "Маленький грязный котёнок дрожит и смотрит на тебя.\n\n"
            "Твои действия:",
            reply_markup=story_cat_kb
        )
        last_submenu_msg_id[uid] = msg.message_id
        game.story_state = "cat_choice"

    elif data == "story_cat_leave":
        game.add_log("Ты оставил котёнка и ушёл. Лес снова стал тихим.")
        game.story_state = None
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id
        await callback.answer("Ок")

    elif data == "story_cat_take":
        game.story_state = "cat_name_wait"
        msg = await callback.message.answer(
            "Ты осторожно берёшь дрожащего котёнка на руки.\n"
            "Он холодный и лёгкий.\n\n"
            "Как ты его назовёшь?",
            reply_markup=None
        )
        last_submenu_msg_id[uid] = msg.message_id
        await callback.answer()

    elif data == "story_next":
        game.story_state = None
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id
        await callback.answer()

    # ─── ИНВЕНТАРЬ ─────────────────────────────────────────
    elif data == "action_2":
        msg = await callback.message.answer(game.get_inventory_text(), reply_markup=inventory_inline_kb)
        last_submenu_msg_id[uid] = msg.message_id
        await callback.answer()

    # ─── ИСПОЛЬЗОВАТЬ ПРЕДМЕТ (факел) ─────────────────────
    elif data == "inv_use":
        # пока заглушка — в будущем выбор предмета
        # для простоты считаем, что используем факел, если он есть
        if game.inventory["Факел"] > 0 and game.equipment["hand"] is None:
            game.inventory["Факел"] -= 1
            game.equipment["hand"] = "Факел"
            game.add_log("Ты взял факел в руку.")
            action_taken = True
        else:
            game.add_log("Нечего использовать или рука занята.")

    # ─── ПЕРСОНАЖ ─────────────────────────────────────────
    elif data == "inv_character":
        msg = await callback.message.answer(game.get_character_text(), reply_markup=character_inline_kb)
        last_submenu_msg_id[uid] = msg.message_id
        await callback.answer()

    # ─── НАЗАД ИЗ ПОДМЕНЮ ─────────────────────────────────
    elif data in ("inv_back", "character_back"):
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id
        await callback.answer()

    # другие действия (пить, спать и т.д.) — оставляем как было
    elif data == "action_3":
        if game.inventory["Бутылка воды"] > 0:
            game.inventory["Бутылка воды"] -= 1
            game.thirst = min(100, game.thirst + 20)
            game.add_log(f"Напился. Жажда +20 (осталось {game.inventory['Бутылка воды']})")
        else:
            game.add_log("Бутылка пуста.")
        action_taken = True

    elif data == "action_4":
        game.day += 1
        game.ap = 5
        game.hunger = max(0, game.hunger - 15)
        game.weather = random.choices(["clear", "cloudy", "rain"], weights=[70, 20, 10])[0]
        w_name = {"clear": "ясно", "cloudy": "пасмурно", "rain": "дождь"}[game.weather]
        game.add_log(f"День {game.day}. Выспался. Голод -15. {w_name.capitalize()}.")
        action_taken = True

    if action_taken:
        save_game(uid, game)
        if uid in last_ui_msg_id:
            try:
                await bot.edit_message_text(
                    game.get_ui(),
                    chat_id=chat_id,
                    message_id=last_ui_msg_id[uid],
                    reply_markup=get_main_kb(game)
                )
            except:
                msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
                last_ui_msg_id[uid] = msg.message_id

    await callback.answer()

# ─── ВВОД ИМЕНИ КОТЁНКА ────────────────────────────────────────
@dp.message()
async def handle_text_message(message: Message):
    uid = message.from_user.id
    game = games.get(uid)
    if not game or game.story_state != "cat_name_wait":
        return

    name = message.text.strip()
    if not name:
        await message.answer("Дай хоть какое-то имя…")
        return

    game.equipment["pet"] = name
    game.karma += 5
    game.add_log(f"У вас появился питомец: {name}")
    game.add_log(f"Карма +5 → {game.karma}/{game.karma_goal}")

    game.story_state = None
    save_game(uid, game)

    msg = await message.answer(
        f"«{name}» — произносишь ты вслух.\n"
        "Котёнок прижимается ближе и тихо мурчит.\n\n"
        "Впервые в этом лесу не так одиноко.",
        reply_markup=story_next_kb
    )
    if uid in last_submenu_msg_id:
        try:
            await bot.delete_message(message.chat.id, last_submenu_msg_id[uid])
        except:
            pass
    last_submenu_msg_id[uid] = msg.message_id

# ──────────────────────────────────────────────────────────────────────────────
# FASTAPI + WEBHOOK + PING
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/ping")
async def ping():
    return PlainTextResponse("OK")

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    try:
        body = await request.json()
        update = Update.model_validate(body, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        raise HTTPException(500)

@app.on_event("startup")
async def on_startup():
    if WEBHOOK_URL:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        logging.info(f"Webhook: {WEBHOOK_URL}")
    asyncio.create_task(self_ping_task())

async def self_ping_task():
    if not BASE_URL:
        return
    url = f"{BASE_URL}/ping"
    while True:
        try:
            async with httpx.AsyncClient() as c:
                await c.get(url, timeout=8)
        except:
            pass
        await asyncio.sleep(300)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
