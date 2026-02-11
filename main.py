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
from aiogram.exceptions import TelegramBadRequest
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
research_count_day2 = {}

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
        self.nav_stack = ["main"]  # ← СТЕК НАВИГАЦИИ

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    def push_screen(self, screen: str):
        """Добавить экран в стек"""
        self.nav_stack.append(screen)

    def pop_screen(self):
        """Вернуться на предыдущий экран, вернуть его идентификатор"""
        if len(self.nav_stack) > 1:
            self.nav_stack.pop()
        return self.nav_stack[-1]

    def reset_nav(self):
        """Сбросить стек до главного экрана"""
        self.nav_stack = ["main"]

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
            # Если стек не был сохранён — инициализируем
            if "nav_stack" not in game.__dict__:
                game.nav_stack = ["main"]
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
# КНОПКИ (без изменений)
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
     InlineKeyboardButton(text="← Назад", callback_data="back")],
])

character_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="← Назад", callback_data="back")]
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
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# ──────────────────────────────────────────────────────────────────────────────
async def update_or_send_message(chat_id: int, uid: int, text: str, reply_markup=None):
    msg_id = last_active_msg_id.get(uid)
    if msg_id:
        try:
            await bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=msg_id,
                reply_markup=reply_markup
            )
            return msg_id
        except TelegramBadRequest as e:
            logging.warning(f"Не удалось отредактировать {msg_id} для {uid}: {e}")
            try:
                await bot.delete_message(chat_id, msg_id)
            except:
                pass
            last_active_msg_id.pop(uid, None)

    msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    last_active_msg_id[uid] = msg.message_id
    return msg.message_id

# ──────────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    logging.info(f"[START] Получен /start от {uid}")

    try:
        for i in range(1, 50):
            await bot.delete_message(chat_id, message.message_id - i)
    except:
        pass

    loaded = load_game(uid)
    if loaded:
        text = "Есть сохранение. Что делаем?"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Продолжить", callback_data="load_game")],
            [InlineKeyboardButton(text="Новая игра", callback_data="new_game")]
        ])
    else:
        text = GUIDE_TEXT
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Начать", callback_data="start_new_game")]
        ])

    await update_or_send_message(chat_id, uid, text, kb)

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    chat_id = callback.message.chat.id
    now = time.time()

    if uid in last_request_time and now - last_request_time[uid] < 0.8:
        await callback.answer("Подожди немного...")
        return
    last_request_time[uid] = now

    data = callback.data
    logging.info(f"[CALLBACK] {data} от {uid}")

    game = games.get(uid)

    if data in ("new_game", "start_new_game"):
        game = Game()
        games[uid] = game
        save_game(uid, game)
        await update_or_send_message(chat_id, uid, game.get_ui(), get_main_kb(game))
        await callback.answer()
        return

    if data == "load_game":
        game = load_game(uid) or Game()
        games[uid] = game
        save_game(uid, game)
        await update_or_send_message(chat_id, uid, game.get_ui(), get_main_kb(game))
        await callback.answer()
        return

    if not game:
        await callback.answer("Сначала начни игру /start")
        return

    text = None
    kb = None
    action_taken = False

    # ─── Переходы в подменю ───
    if data == "action_2":
        game.push_screen("inventory")
        text = game.get_inventory_text()
        kb = inventory_inline_kb

    elif data == "inv_character":
        game.push_screen("character")
        text = game.get_character_text()
        kb = character_inline_kb

    elif data == "inv_craft":
        game.push_screen("craft")
        kb_c = InlineKeyboardMarkup(inline_keyboard=[])
        if game.inventory.get("Спички 🔥", 0) >= 1 and game.inventory.get("Ветка", 0) >= 1:
            kb_c.inline_keyboard.append([
                InlineKeyboardButton(text="Факел (1 ветка + 1 спичка)", callback_data="craft_Факел")
            ])
            craft_text = "Доступный крафт:"
        else:
            craft_text = "Пока ничего нельзя скрафтить.\n(нужна Ветка и Спички 🔥)"
        kb_c.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="back")])
        text = craft_text
        kb = kb_c

    elif data == "inv_use":
        game.push_screen("use")
        kb_u = InlineKeyboardMarkup(inline_keyboard=[])
        if game.inventory.get("Факел", 0) > 0 and game.equipment["hand"] is None:
            kb_u.inline_keyboard.append([InlineKeyboardButton(text="Факел 🔥", callback_data="use_item_Факел")])
        if not kb_u.inline_keyboard:
            kb_u.inline_keyboard.append([InlineKeyboardButton(text="Нечего использовать", callback_data="dummy")])
        kb_u.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="back")])
        text = "Что использовать?"
        kb = kb_u

    # ─── Умная кнопка НАЗАД ───
    elif data == "back":
        prev = game.pop_screen()
        if prev == "main":
            text = game.get_ui()
            kb = get_main_kb(game)
        elif prev == "inventory":
            text = game.get_inventory_text()
            kb = inventory_inline_kb
        elif prev == "character":
            text = game.get_character_text()
            kb = character_inline_kb
        elif prev == "craft":
            kb_c = InlineKeyboardMarkup(inline_keyboard=[])
            if game.inventory.get("Спички 🔥", 0) >= 1 and game.inventory.get("Ветка", 0) >= 1:
                kb_c.inline_keyboard.append([
                    InlineKeyboardButton(text="Факел (1 ветка + 1 спичка)", callback_data="craft_Факел")
                ])
                craft_text = "Доступный крафт:"
            else:
                craft_text = "Пока ничего нельзя скрафтить.\n(нужна Ветка и Спички 🔥)"
            kb_c.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="back")])
            text = craft_text
            kb = kb_c
        elif prev == "use":
            kb_u = InlineKeyboardMarkup(inline_keyboard=[])
            if game.inventory.get("Факел", 0) > 0 and game.equipment["hand"] is None:
                kb_u.inline_keyboard.append([InlineKeyboardButton(text="Факел 🔥", callback_data="use_item_Факел")])
            if not kb_u.inline_keyboard:
                kb_u.inline_keyboard.append([InlineKeyboardButton(text="Нечего использовать", callback_data="dummy")])
            kb_u.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="back")])
            text = "Что использовать?"
            kb = kb_u

    # ─── Сюжетные возвраты на главный + сброс стека ───
    elif data in ("wolf_flee", "cat_leave", "story_next"):
        game.reset_nav()
        if data == "wolf_flee":
            game.add_log(
                "Ты медленно пятишься назад, стараясь не хрустнуть ни одной веткой.\n"
                "Через несколько шагов рычание стихает за деревьями.\n"
                "Что бы там ни было под пнём — оно теперь не твоё дело.\n"
                "Сердце всё ещё колотится."
            )
        elif data == "cat_leave":
            game.add_log(
                "Ты медленно убираешь руку.\n"
                "Котёнок смотрит тебе вслед, но не мяукает.\n"
                "Ты встаёшь, разворачиваешься и уходишь.\n"
                "За спиной остаётся только тишина леса и ощущение, что ты только что прошёл мимо чего-то важного."
            )
            game.karma -= 50
        text = game.get_ui()
        kb = get_main_kb(game)

    # ─── Остальные действия ───
    elif data == "action_1":
        # ... (твой код без изменений)
        action_taken = True

    elif data == "action_3":
        # ... (твой код без изменений)
        action_taken = True
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "action_4":
        # ... (твой код без изменений)
        action_taken = True
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "craft_Факел":
        # ... (твой код без изменений)
        text = game.get_inventory_text()
        kb = inventory_inline_kb
        save_game(uid, game)

    elif data == "use_item_Факел":
        # ... (твой код без изменений)
        text = game.get_ui()
        kb = get_main_kb(game)
        save_game(uid, game)

    # ─── Обновление экрана ───
    if text is not None:
        await update_or_send_message(chat_id, uid, text, kb)

    if action_taken:
        save_game(uid, game)
        # Если действие не привело к смене экрана — обновляем текущее
        if text is None:
            current = game.nav_stack[-1]
            if current == "main":
                await update_or_send_message(chat_id, uid, game.get_ui(), get_main_kb(game))
            # можно добавить для других экранов, если нужно автообновление

    await callback.answer()

# ─── ВВОД ИМЕНИ КОТЁНКА ───────────────────────────────────────────────────────
@dp.message(F.text)
async def handle_name_input(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    game = games.get(uid)
    if not game or game.story_state != "cat_name_wait":
        return

    try:
        await bot.delete_message(chat_id, message.message_id)
    except:
        pass

    name = message.text.strip()[:32]
    if not name:
        await update_or_send_message(chat_id, uid, "Дай хоть какое-то имя…")
        return

    game.equipment["pet"] = name
    game.karma += 5
    game.story_state = None
    save_game(uid, game)

    success_text = (
        f"Ты смотришь на маленькое существо у себя на руках.\n"
        f"«{name}», — произносишь ты вслух, и понимаешь что нашел себе нового друга.\n"
        f"Котёнок поднимает голову, будто услышал и запомнил.\n"
        f"Уходя от пня, ты чувствуешь, как он начинает тихо, почти неслышно мурчать.\n"
        f"Вибрация проходит сквозь твою грудь — слабая, но живая.\n"
        f"Впервые за долгое время в этом лесу становится чуть теплее."
    )

    # После выбора котёнка — на главный экран и сброс стека
    game.reset_nav()
    await update_or_send_message(chat_id, uid, success_text, next_kb)

    game.add_log(f"У вас появился питомец: {name}")
    game.add_log(f"+5 кармы")

# ──────────────────────────────────────────────────────────────────────────────
# FASTAPI + WEBHOOK + PING (без изменений)
# ──────────────────────────────────────────────────────────────────────────────
# ... (оставляем как было)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logging.info(f"Запуск uvicorn на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
