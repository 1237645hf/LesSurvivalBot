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
last_active_msg_id = {}
research_count_day2 = {} # {uid: сколько раз исследовал на 2-й день}
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
            "head": None, "torso": None, "back": None, "pants": None,
            "boots": None, "trinket": None, "pet": None, "hand": None
        }
        self.story_state = None
        self.found_branch_once = False
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
        pet_text = f"Питомец: {self.equipment['pet']}" if self.equipment.get("pet") else "Питомец: Пусто"
        slots = {
            "head": "Голова",
            "torso": "Торс",
            "back": "Спина",
            "pants": "Штаны",
            "boots": "Ботинки",
            "trinket": "Безделушка",
            "pet": pet_text,
            "hand": "Рука"
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
# КНОПКИ
# ──────────────────────────────────────────────────────────────────────────────
def get_main_kb(game: Game):
    kb = InlineKeyboardMarkup(inline_keyboard=[
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
wolf_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Уйти тихо", callback_data="wolf_flee")],
    [InlineKeyboardButton(text="Использовать факел", callback_data="wolf_fight")]
])
peek_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Заглянуть внутрь", callback_data="peek_den")]
])
cat_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Оставить его здесь", callback_data="cat_leave")],
    [InlineKeyboardButton(text="Забрать с собой", callback_data="cat_take")]
])
next_kb = InlineKeyboardMarkup(inline_keyboard=[
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
    logging.info(f"[START] Получен /start от пользователя {uid}")
    try:
        for i in range(1, 100):
            await bot.delete_message(message.chat.id, message.message_id - i)
    except:
        pass
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    loaded = load_game(uid)
    if loaded:
        msg = await bot.send_message(
            message.chat.id,
            "Есть сохранение. Что делаем?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Продолжить", callback_data="load_game")],
                [InlineKeyboardButton(text="Новая игра", callback_data="new_game")]
            ])
        )
        last_active_msg_id[uid] = msg.message_id
    else:
        msg = await bot.send_message(
            message.chat.id,
            GUIDE_TEXT,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Начать", callback_data="start_new_game")]
            ])
        )
        last_active_msg_id[uid] = msg.message_id
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
    try:
        await bot.delete_message(chat_id, callback.message.message_id)
    except:
        pass
    if data == "new_game":
        msg = await bot.send_message(
            chat_id,
            GUIDE_TEXT,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Начать", callback_data="start_new_game")]
            ])
        )
        last_active_msg_id[uid] = msg.message_id
        await callback.answer()
        return
    if data == "start_new_game":
        game = Game()
        games[uid] = game
        save_game(uid, game)
        msg = await bot.send_message(chat_id, game.get_ui(), reply_markup=get_main_kb(game))
        last_active_msg_id[uid] = msg.message_id
        await callback.answer()
        return
    if data == "load_game":
        game = load_game(uid) or Game()
        games[uid] = game
        save_game(uid, game)
        msg = await bot.send_message(chat_id, game.get_ui(), reply_markup=get_main_kb(game))
        last_active_msg_id[uid] = msg.message_id
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
                msg = await bot.send_message(
                    chat_id,
                    "Ты идёшь между стволов, и вдруг замираешь.\n"
                    "Где-то совсем рядом — хриплое рычание, звук рвущейся земли, тяжёлое дыхание.\n"
                    "Очень осторожно, почти не дыша, ты раздвигаешь ветки и смотришь.\n\n"
                    "Перед тобой — старый, истощённый волк. Шерсть свалялась, рёбра торчат, один глаз мутный.\n"
                    "Он яростно копает лапами под старым пнём.\n"
                    "Факел в твоей руке потрескивает, бросая дрожащие тени.\n\n"
                    "Твои действия:",
                    reply_markup=wolf_kb
                )
                last_active_msg_id[uid] = msg.message_id
            else:
                events = [
                    ("Нашёл ягоды! +10 сытости", lambda: setattr(game, 'hunger', min(100, game.hunger + 10))),
                    ("Нашёл мухоморы", lambda: game.inventory.update({"Мухоморы": game.inventory["Мухоморы"] + 1})),
                    ("Нашёл родник → +3 воды", lambda: game.inventory.update({"Бутылка воды": min(game.water_capacity, game.inventory["Бутылка воды"] + 3)})),
                    ("Укус насекомого –5 HP", lambda: setattr(game, 'hp', max(0, game.hp - 5))),
                    ("Нашёл кору", lambda: game.inventory.update({"Кусок коры 🪵": game.inventory["Кусок коры 🪵"] + 1})),
                    ("Нашёл нож", lambda: game.inventory.update({"Нож": game.inventory["Нож"] + 1}))
                ]
                text, effect = random.choice(events)
                effect()
                game.add_log(f"🔍 Исследовал... {text}")
        action_taken = True
    elif data == "wolf_flee":
        game.add_log(
            "Ты медленно пятишься назад, стараясь не хрустнуть ни одной веткой.\n"
            "Через несколько шагов рычание стихает за деревьями.\n"
            "Что бы там ни было под пнём — оно теперь не твоё дело.\n"
            "Сердце всё ещё колотится."
        )
        game.story_state = None
        msg = await bot.send_message(chat_id, game.get_ui(), reply_markup=get_main_kb(game))
        last_active_msg_id[uid] = msg.message_id
    elif data == "wolf_fight":
        fight_text = (
            "Ты поднимаешь факел повыше. Пламя трещит громче.\n"
            "Волк резко оборачивается, глаза вспыхивают жёлтым в свете огня.\n"
            "Секунду он смотрит на тебя — не нападает, но и не отступает.\n"
            "Тогда ты делаешь шаг вперёд и рычишь сам — низко, зло, по-человечески неумело.\n"
            "Факел вспыхивает ярче от рывка воздуха.\n"
            "Зверь подается назад и ты замахиваешься факелом.\n"
            "Ещё мгновение — и ты видишь как подпалённый волк убегает в темноту между деревьями, бросив свою яму.\n"
            "Остатки факела медленно догорают на земле возле тебя.\n\n"
            "Теперь перед тобой открытая яма под пнём."
        )
        game.equipment["hand"] = None
        game.inventory["Факел"] = max(0, game.inventory.get("Факел", 0) - 1)
        game.story_state = "after_fight"
        msg = await bot.send_message(chat_id, fight_text, reply_markup=peek_kb)
        last_active_msg_id[uid] = msg.message_id
    elif data == "peek_den":
        msg = await bot.send_message(
            chat_id,
            "Ты опускаешься на колени, наклоняешься ближе.\n"
            "В слабом отсвете угасающих угольков факела, почти на самом дне ямы, блестят два огромных влажных глаза.\n"
            "Они смотрят на тебя с ужасом и надеждой одновременно.\n"
            "Маленький, грязный, дрожащий котёнок.\n"
            "Шерсть слиплась от сырости, одно ухо надорвано.\n"
            "Ты тихо протягиваешь руку.\n"
            "Он долго не решается. Потом осторожно, очень медленно обнюхивает твои пальцы.\n"
            "Ты чувствуешь холодный нос и слабое, прерывистое дыхание.\n\n"
            "Твои действия:",
            reply_markup=cat_kb
        )
        last_active_msg_id[uid] = msg.message_id
        game.story_state = "cat_choice"
    elif data == "cat_leave":
        game.add_log(
            "Ты медленно убираешь руку.\n"
            "Котёнок смотрит тебе вслед, но не мяукает.\n"
            "Ты встаёшь, разворачиваешься и уходишь.\n"
            "За спиной остаётся только тишина леса и ощущение, что ты только что прошёл мимо чего-то важного."
        )
        game.karma -= 50
        game.story_state = None
        msg = await bot.send_message(chat_id, game.get_ui(), reply_markup=get_main_kb(game))
        last_active_msg_id[uid] = msg.message_id
    elif data == "cat_take":
        game.story_state = "cat_name_wait"
        msg = await bot.send_message(
            chat_id,
            "Ты осторожно опускаешь обе ладони в яму.\n"
            "Котёнок сначала отшатывается, потом сам делает маленький шаг навстречу.\n"
            "Через секунду он уже у тебя на руках — лёгкий, холодный, дрожащий всем телом.\n"
            "Ты прижимаешь его к груди, прикрывая полой куртки.\n\n"
            "Как ты его назовёшь?",
            reply_markup=None
        )
        last_active_msg_id[uid] = msg.message_id
    elif data == "story_next":
        game.story_state = None
        msg = await bot.send_message(chat_id, game.get_ui(), reply_markup=get_main_kb(game))
        last_active_msg_id[uid] = msg.message_id
    elif data == "action_2":
        msg = await bot.send_message(chat_id, game.get_inventory_text(), reply_markup=inventory_inline_kb)
        last_active_msg_id[uid] = msg.message_id
        await callback.answer()
    elif data == "inv_craft":
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        if game.inventory.get("Спички 🔥", 0) >= 1 and game.inventory.get("Ветка", 0) >= 1:
            kb.inline_keyboard.append([
                InlineKeyboardButton(text="Факел (1 ветка + 1 спичка)", callback_data="craft_Факел")
            ])
            text = "Доступный крафт:"
        else:
            text = "Пока ничего нельзя скрафтить.\n(нужна Ветка и Спички 🔥)"
        kb.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="inv_back")])
        msg = await bot.send_message(chat_id, text, reply_markup=kb)
        last_active_msg_id[uid] = msg.message_id
    elif data == "craft_Факел":
        if game.inventory.get("Спички 🔥", 0) < 1 or game.inventory.get("Ветка", 0) < 1:
            await callback.answer("Недостаточно материалов", show_alert=True)
            return
        game.inventory["Спички 🔥"] -= 1
        game.inventory["Ветка"] -= 1
        game.inventory["Факел"] += 1
        game.add_log("Вы скрафтили факел.")
        game.add_log("Для крафта факела вам пришлось использовать носок с левой ноги.")
        msg = await bot.send_message(chat_id, game.get_inventory_text(), reply_markup=inventory_inline_kb)
        last_active_msg_id[uid] = msg.message_id
        save_game(uid, game)
        await callback.answer()
    elif data == "inv_use":
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        if game.inventory.get("Факел", 0) > 0 and game.equipment["hand"] is None:
            kb.inline_keyboard.append([InlineKeyboardButton(text="Факел 🔥", callback_data="use_item_Факел")])
        if not kb.inline_keyboard:
            kb.inline_keyboard.append([InlineKeyboardButton(text="Нечего использовать", callback_data="dummy")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="inv_back")])
        msg = await bot.send_message(chat_id, "Что использовать?", reply_markup=kb)
        last_active_msg_id[uid] = msg.message_id
    elif data == "use_item_Факел":
        if game.inventory.get("Факел", 0) > 0 and game.equipment["hand"] is None:
            game.inventory["Факел"] -= 1
            game.equipment["hand"] = "Факел"
            game.add_log("Вы экипировали факел в руку.")
            msg = await bot.send_message(chat_id, game.get_ui(), reply_markup=get_main_kb(game))
            last_active_msg_id[uid] = msg.message_id
            save_game(uid, game)
        else:
            game.add_log("Нельзя экипировать факел сейчас.")
        action_taken = True
        await callback.answer()
    elif data == "inv_character":
        msg = await bot.send_message(chat_id, game.get_character_text(), reply_markup=character_inline_kb)
        last_active_msg_id[uid] = msg.message_id
    elif data in ("inv_back", "character_back"):
        msg = await bot.send_message(chat_id, game.get_ui(), reply_markup=get_main_kb(game))
        last_active_msg_id[uid] = msg.message_id
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
        msg = await bot.send_message(chat_id, game.get_ui(), reply_markup=get_main_kb(game))
        last_active_msg_id[uid] = msg.message_id
    await callback.answer()
# ─── ВВОД ИМЕНИ КОТЁНКА ───────────────────────────────────────────────────────
@dp.message(F.text)
async def handle_name_input(message: Message):
    uid = message.from_user.id
    game = games.get(uid)
    if not game or game.story_state != "cat_name_wait":
        return
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    name = message.text.strip()[:32]
    if not name:
        msg = await bot.send_message(message.chat.id, "Дай хоть какое-то имя…")
        last_active_msg_id[uid] = msg.message_id
        return
    game.equipment["pet"] = name
    game.karma += 5
    game.story_state = None
    save_game(uid, game)
    if uid in last_active_msg_id:
        try:
            await bot.delete_message(message.chat.id, last_active_msg_id[uid])
            del last_active_msg_id[uid]
        except:
            pass
    msg = await bot.send_message(
        message.chat.id,
        f"Ты смотришь на маленькое существо у себя на руках.\n"
        f"«{name}», — произносишь ты вслух, и понимаешь что нашел себе нового друга.\n"
        f"Котёнок поднимает голову, будто услышал и запомнил.\n"
        f"Уходя от пня, ты чувствуешь, как он начинает тихо, почти неслышно мурчать.\n"
        f"Вибрация проходит сквозь твою грудь — слабая, но живая.\n"
        f"Впервые за долгое время в этом лесу становится чуть теплее.",
        reply_markup=next_kb
    )
    last_active_msg_id[uid] = msg.message_id
    game.add_log(f"У вас появился питомец: {name}")
    game.add_log(f"+5 кармы")
# ──────────────────────────────────────────────────────────────────────────────
# FASTAPI + WEBHOOK + PING
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
        logging.info(f"Webhook получил обновление: {update.update_id if update else 'нет id'}")
        return {"ok": True}
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500)
@app.on_event("startup")
async def on_startup():
    if WEBHOOK_URL:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logging.info("Старый webhook удалён")
        except Exception as e:
            logging.warning(f"Не удалось удалить старый webhook: {e}")
        try:
            await bot.set_webhook(
                url=WEBHOOK_URL,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"]
            )
            logging.info(f"Webhook успешно установлен: {WEBHOOK_URL}")
        except Exception as e:
            logging.error(f"Ошибка установки webhook: {e}")
    else:
        logging.warning("BASE_URL не задан → webhook не установлен!")
    asyncio.create_task(self_ping_task())
async def self_ping_task():
    if not BASE_URL:
        logging.info("Self-ping отключён (нет BASE_URL)")
        return
    url = f"{BASE_URL}/ping"
    while True:
        try:
            async with httpx.AsyncClient() as c:
                await c.get(url, timeout=10)
            logging.info("[SELF-PING] OK")
        except Exception as e:
            logging.warning(f"[SELF-PING] ошибка: {e}")
        await asyncio.sleep(300)
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logging.info(f"Запуск uvicorn на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
