import asyncio
import logging
import os
import time
import random
from collections import Counter
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
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
# КЛАСС ИГГРЫ
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
            "head": None, "torso": None, "back": None, "pants": None,
            "boots": None, "trinket": None, "pet": None, "hand": None
        }
        self.story_state = None
        self.found_branch_once = False  # пока оставляем, но теперь не строго обязательно

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
        equipped_hand = self.equipment.get("hand")
        for item, count in self.inventory.items():
            if count > 0:
                marker = " ✦" if item == "Факел" else ""
                equipped_mark = " ✅" if item == equipped_hand else ""
                line = f"• {item} x{count}{marker}{equipped_mark}" if count > 1 else f"• {item}{marker}{equipped_mark}"
                lines.append(line)
        text = "🎒 Инвентарь:\n" + "\n".join(lines) if lines else "🎒 Инвентарь пуст"
        text += "\n━━━━━━━━━━━━━━━━━━━"
        return text

    def get_character_text(self):
        slots = {
            "head": "Голова", "torso": "Торс", "back": "Спина", "pants": "Штаны",
            "boots": "Ботинки", "trinket": "Безделушка", "pet": "Питомец", "hand": "Рука"
        }
        lines = [f"{name}: {self.equipment.get(slot) or 'Пусто'}" for slot, name in slots.items()]
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
# КРАФТ
# ──────────────────────────────────────────────────────────────────────────────
CRAFT_RECIPES = {
    "Факел": {
        "required": {"Спички 🔥": 1, "Ветка": 1},
        "result": {"Факел": 1},
        "craft_log": "Вы скрафтили факел.",
        "funny_log": "Для крафта факела вам пришлось использовать носок с левой ноги."
    }
}

def get_craft_kb(game: Game):
    buttons = []
    has_recipe = False
    for item, recipe in CRAFT_RECIPES.items():
        if all(game.inventory.get(k, 0) >= v for k, v in recipe["required"].items()):
            has_recipe = True
            buttons.append([InlineKeyboardButton(
                text=f"{item} 🔥 (Спички + Ветка)",
                callback_data=f"craft_{item}"
            )])
    if not has_recipe:
        buttons.append([InlineKeyboardButton(text="Пока ничего нельзя скрафтить", callback_data="dummy")])
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="inv_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_use_kb(game: Game):
    buttons = []
    if game.inventory.get("Факел", 0) > 0 and game.equipment["hand"] is None:
        buttons.append([InlineKeyboardButton(text="Факел 🔥", callback_data="use_item_Факел")])
    if not buttons:
        buttons.append([InlineKeyboardButton(text="Нечего использовать", callback_data="dummy")])
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="inv_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ──────────────────────────────────────────────────────────────────────────────
# КНОПКИ ОСНОВНЫЕ
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
        next_icon = loc_icons[current_idx+1]
        if next_loc in game.unlocked_locations:
            loc_row.append(InlineKeyboardButton(text=f"{next_icon} →", callback_data=f"loc_{next_loc}"))
        else:
            loc_row.append(InlineKeyboardButton(text=f"{next_icon} ×", callback_data="loc_locked"))
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
# ПРИВЕТСТВИЕ
# ──────────────────────────────────────────────────────────────────────────────
GUIDE_TEXT = (
    "🌲 Добро пожаловать в лес выживания!\n\n"
    "Краткий гайд\n"
    "❤️ 100 - здоровье\n"
    "🍖 100 - сытость\n"
    "💧 100 - жажда\n"
    "⚡ 5 - действия на день\n"
    "☀️ 100 - день\n\n"
    "⚖️ Карма поможет выбраться.\n\n"
    "Попробуй выжить друг мой..."
)

# ──────────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    logging.info(f"[START] /start от {uid}")
    try:
        for i in range(1, 100):
            await bot.delete_message(message.chat.id, message.message_id - i)
    except:
        pass
    loaded = load_game(uid)
    if loaded:
        await message.answer(
            "Есть сохранение. Что делаем?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Продолжить", callback_data="load_game")],
                [InlineKeyboardButton(text="Новая игра", callback_data="new_game")]
            ])
        )
    else:
        await message.answer(
            GUIDE_TEXT,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Начать", callback_data="start_new_game")]
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
    logging.info(f"[CALLBACK] {data} от {uid}")
    chat_id = callback.message.chat.id

    if data.startswith(("action_", "inv_", "story_")) and uid in last_submenu_msg_id:
        try:
            await bot.delete_message(chat_id, last_submenu_msg_id[uid])
            del last_submenu_msg_id[uid]
        except:
            pass

    if data in ("new_game", "start_new_game"):
        game = Game()
        games[uid] = game
        save_game(uid, game)
        if uid in last_ui_msg_id:
            try: await bot.delete_message(chat_id, last_ui_msg_id[uid])
            except: pass
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id
        await callback.answer()
        return

    if data == "load_game":
        game = load_game(uid) or Game()
        games[uid] = game
        save_game(uid, game)
        if uid in last_ui_msg_id:
            try: await bot.delete_message(chat_id, last_ui_msg_id[uid])
            except: pass
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id
        await callback.answer()
        return

    if data == "new_game":
        await callback.message.answer(
            GUIDE_TEXT,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Начать", callback_data="start_new_game")]
            ])
        )
        await callback.answer()
        return

    game = games.get(uid)
    if not game:
        await callback.answer("Сначала начни игру /start")
        return

    action_taken = False

    if data == "action_1":
        if game.ap <= 0:
            game.add_log("Нет сил. Нужно поспать.")
        else:
            game.ap -= 1
            game.hunger = max(0, game.hunger - 7)
            game.thirst = max(0, game.thirst - 8)
            if game.equipment.get("hand") == "Факел" and game.story_state is None:
                game.story_state = "wolf_scene"
                if uid in last_ui_msg_id:
                    try: await bot.delete_message(chat_id, last_ui_msg_id[uid]); del last_ui_msg_id[uid]
                    except: pass
                msg = await callback.message.answer(
                    "Ты слышишь хриплое рычание...\nСтарый волк копает под пнём...\nТвои действия:",
                    reply_markup=story_wolf_kb
                )
                last_submenu_msg_id[uid] = msg.message_id
            else:
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
                if "ветка" in text.lower():
                    game.add_log("А из этого можно сделать факел?")
        action_taken = True

    # ─── СЮЖЕТ С ВОЛКОМ И КОТЁНКОМ (без изменений) ───
    elif data == "story_wolf_flee":
        game.add_log("Ты тихо отступил.")
        game.story_state = None
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id

    elif data == "story_wolf_fight":
        game.add_log("Ты ударил волка факелом. Он убежал.")
        game.equipment["hand"] = None
        game.inventory["Факел"] -= 1 if game.inventory.get("Факел", 0) > 0 else 0
        msg = await callback.message.answer(
            "Факел догорел.\n\nТеперь под пнём открыта яма...",
            reply_markup=story_peek_kb
        )
        last_submenu_msg_id[uid] = msg.message_id
        game.story_state = "after_fight"

    elif data == "story_peek":
        msg = await callback.message.answer(
            "В яме маленький грязный котёнок...\nТвои действия:",
            reply_markup=story_cat_kb
        )
        last_submenu_msg_id[uid] = msg.message_id
        game.story_state = "cat_choice"

    elif data == "story_cat_leave":
        game.add_log("Ты оставил котёнка.")
        game.story_state = None
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id

    elif data == "story_cat_take":
        game.story_state = "cat_name_wait"
        msg = await callback.message.answer(
            "Ты берёшь котёнка.\nКак ты его назовёшь?",
            reply_markup=None
        )
        last_submenu_msg_id[uid] = msg.message_id

    elif data == "story_next":
        game.story_state = None
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id

    # ─── ИНВЕНТАРЬ ───
    elif data == "action_2":
        msg = await callback.message.answer(game.get_inventory_text(), reply_markup=inventory_inline_kb)
        last_submenu_msg_id[uid] = msg.message_id

    elif data == "inv_craft":
        craft_text = "Что можно скрафтить:\n"
        msg = await callback.message.answer(
            craft_text,
            reply_markup=get_craft_kb(game)
        )
        last_submenu_msg_id[uid] = msg.message_id

    elif data.startswith("craft_"):
        item = data.split("_", 1)[1]
        if item not in CRAFT_RECIPES:
            await callback.answer("Неизвестный рецепт")
            return
        recipe = CRAFT_RECIPES[item]
        if not all(game.inventory.get(k, 0) >= v for k, v in recipe["required"].items()):
            await callback.answer("Недостаточно материалов!", show_alert=True)
            return
        # Крафт
        for k, v in recipe["required"].items():
            game.inventory[k] -= v
        for k, v in recipe["result"].items():
            game.inventory[k] += v
        game.add_log(recipe["craft_log"])
        game.add_log(recipe["funny_log"])
        await callback.message.answer(f"{recipe['craft_log']}\n{recipe['funny_log']}")
        # Возврат в инвентарь
        msg = await callback.message.answer(game.get_inventory_text(), reply_markup=inventory_inline_kb)
        last_submenu_msg_id[uid] = msg.message_id
        save_game(uid, game)

    elif data == "inv_use":
        msg = await callback.message.answer(
            "Что использовать?",
            reply_markup=get_use_kb(game)
        )
        last_submenu_msg_id[uid] = msg.message_id

    elif data.startswith("use_item_"):
        item = data.split("_", 2)[2]
        if item == "Факел":
            if game.inventory.get("Факел", 0) > 0 and game.equipment["hand"] is None:
                game.inventory["Факел"] -= 1
                game.equipment["hand"] = "Факел"
                game.add_log("Вы экипировали факел в руку.")
                msg = await callback.message.answer(game.get_inventory_text(), reply_markup=inventory_inline_kb)
                last_submenu_msg_id[uid] = msg.message_id
                save_game(uid, game)
            else:
                game.add_log("Нельзя экипировать факел сейчас.")
        await callback.answer()

    elif data == "inv_character":
        msg = await callback.message.answer(game.get_character_text(), reply_markup=character_inline_kb)
        last_submenu_msg_id[uid] = msg.message_id

    elif data in ("inv_back", "character_back"):
        msg = await callback.message.answer(game.get_ui(), reply_markup=get_main_kb(game))
        last_ui_msg_id[uid] = msg.message_id

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

# ─── ИМЯ КОТЁНКА ───
@dp.message(F.text)
async def handle_name_input(message: Message):
    uid = message.from_user.id
    game = games.get(uid)
    if not game or game.story_state != "cat_name_wait":
        return
    name = message.text.strip()[:30]
    if not name:
        await message.answer("Дай хоть какое-то имя…")
        return
    game.equipment["pet"] = name
    game.karma += 5
    game.add_log(f"Питомец: {name}")
    game.add_log(f"Карма +5 → {game.karma}/{game.karma_goal}")
    game.story_state = None
    save_game(uid, game)
    if uid in last_submenu_msg_id:
        try:
            await bot.delete_message(message.chat.id, last_submenu_msg_id[uid])
            del last_submenu_msg_id[uid]
        except:
            pass
    await message.answer(
        f"«{name}» — теперь у тебя есть друг.\nОн тихо мурчит.",
        reply_markup=story_next_kb
    )

# ──────────────────────────────────────────────────────────────────────────────
# FASTAPI + WEBHOOK
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/ping")
@app.get("/health")
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
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True, allowed_updates=["message", "callback_query"])
            logging.info(f"Webhook set: {WEBHOOK_URL}")
        except Exception as e:
            logging.error(f"Webhook setup error: {e}")
    asyncio.create_task(self_ping_task())

async def self_ping_task():
    if not BASE_URL:
        return
    url = f"{BASE_URL}/ping"
    while True:
        try:
            async with httpx.AsyncClient() as c:
                await c.get(url, timeout=10)
        except:
            pass
        await asyncio.sleep(300)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
