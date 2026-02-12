import asyncio
import logging
import os
from collections import Counter
from datetime import datetime
from random import choice, randint

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from fastapi import FastAPI
from pymongo import MongoClient

from crafts import RECIPES, check_craft, use_item
from keyboards import (cat_kb, craft_kb, equip_kb, get_inventory_actions_kb,
                       get_main_kb, inventory_inline_kb, main_menu_kb,
                       peek_den_kb, wolf_kb)
from stories import EVENTS, get_thought, trigger_event

# Config from env
TOKEN = os.getenv("TOKEN")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
MONGO_URI = os.getenv("MONGO_URI")
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

# MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['forest_game']
players_collection = db['players']

# Logging
logging.basicConfig(level=logging.INFO)

# Bot setup
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

app = FastAPI()

class Form(StatesGroup):
    name = State()

class Game:
    def __init__(self):
        self.hp = 100
        self.hunger = 0
        self.thirst = 0
        self.ap = 5
        self.karma = 0
        self.day = 1
        self.log = []
        self.inventory = Counter()
        self.equipment = {}
        self.story_state = None
        self.nav_stack = []
        self.weather = choice(['солнечно', 'дождливо', 'пасмурно'])
        self.last_request_time = 0
        self.research_count_day2 = 0
        self.found_branch_once = False
        self.resource_counters = Counter()  # Для триггеров/счётчиков ресурсов

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    def get_ui(self):
        status_bar = (
            f"❤️ HP: {self.hp} | 🍲 Сытость: {self.hunger} | 💧 Жажда: {self.thirst} | "
            f"⚡ ОД: {self.ap} | ☀️ Погода: {self.weather} | 📅 День: {self.day}"
        )
        log_text = "\n".join(self.log[-5:]) if self.log else "Ничего не произошло."
        return f"{status_bar}\n\n{log_text}"

    def get_inventory_text(self):
        if not self.inventory:
            return "Инвентарь пуст."
        return "\n".join(f"{item}: {count}" for item, count in self.inventory.items())

    def push_screen(self, screen_name):
        self.nav_stack.append(screen_name)

    def pop_screen(self):
        if self.nav_stack:
            return self.nav_stack.pop()
        return None

    def update_weather(self):
        self.weather = choice(['солнечно', 'дождливо', 'пасмурно'])

    def update_stats(self):
        self.hunger = min(100, self.hunger + 10)
        self.thirst = min(100, self.thirst + 10)
        if self.hunger >= 100 or self.thirst >= 100:
            self.hp = max(0, self.hp - 10)
        if self.hp <= 0:
            self.add_log("Вы погибли...")

async def load_game(user_id: int) -> Game:
    data = players_collection.find_one({"_id": user_id})
    if data:
        game = Game()
        for key, value in data.items():
            if key != "_id":
                setattr(game, key, value)
        return game
    return Game()

async def save_game(user_id: int, game: Game):
    data = vars(game)
    data["_id"] = user_id
    players_collection.replace_one({"_id": user_id}, data, upsert=True)

async def update_or_send_message(message: Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except:
        await message.answer(text, reply_markup=reply_markup)

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    game = await load_game(message.from_user.id)
    await message.answer(game.get_ui(), reply_markup=get_main_kb(game))
    await save_game(message.from_user.id, game)

@dp.message()
async def process_message(message: Message, state: FSMContext):
    game = await load_game(message.from_user.id)
    text = message.text.lower()

    if text == 'исследовать' and game.ap > 0:
        game.ap -= 1
        items = ['ягоды', 'ветка', 'камень', 'грибы']
        item = choice(items)
        
        # Forced палка/ветка на day 2, second explore (ap==4 after dec)
        if game.day == 2 and game.research_count_day2 == 1 and not game.found_branch_once:
            item = 'ветка'
            game.found_branch_once = True
            game.add_log(get_thought('branch_found'))  # Мысль из stories

        game.inventory[item] += 1
        game.resource_counters[item] += 1  # Инкремент счётчика
        game.add_log(f"Вы нашли: {item}")
        game.research_count_day2 += 1 if game.day == 2 else 0

        # Check триггер события
        event_name = trigger_event(game)  # Из stories, на основе counters/day/ap
        if event_name:
            game.story_state = event_name
            game.add_log(EVENTS[event_name]['text'])
            await message.answer(game.get_ui(), reply_markup=EVENTS[event_name]['kb'](game))

    elif text == 'пить' and game.ap > 0:
        game.ap -= 1
        game.thirst = max(0, game.thirst - 20)
        game.add_log("Вы попили воду.")

    elif text == 'спать':
        game.ap = 5
        game.day += 1
        game.update_weather()
        game.update_stats()
        game.research_count_day2 = 0  # Reset счётчика
        game.add_log("Вы поспали. Новый день начался.")

    elif text == 'инвентарь':
        await message.answer(game.get_inventory_text(), reply_markup=inventory_inline_kb(game))

    # ... (остальные message handlers как в твоём коде: персонаж, карта, крафт — но крафт перенаправь в crafts)

    await update_or_send_message(message, game.get_ui(), get_main_kb(game))
    await save_game(message.from_user.id, game)

@dp.callback_query()
async def process_callback(callback: CallbackQuery):
    game = await load_game(callback.from_user.id)
    data = callback.data

    if data.startswith('inv_'):
        action, item = data.split('_', 1)[1], data.split('_', 2)[2] if '_' in data else None
        if action == 'craft':
            await callback.message.edit_text("Крафт:", reply_markup=craft_kb(game))
        elif action == 'use' and item:
            result = use_item(game, item)  # Из crafts
            game.add_log(result)
        # ... (остальные inv_ как inspect, drop, equip — адаптируй с counters)

    elif data in ['wolf_flee', 'wolf_fight']:
        # Вызов из stories
        effects = EVENTS['wolf']['effects'][data]
        for key, val in effects.items():
            setattr(game, key, getattr(game, key) + val)
        game.add_log(EVENTS['wolf']['outcomes'][data])
        game.story_state = None

    # Аналогично для cat, peek_den и т.д.

    await callback.message.edit_text(game.get_ui(), reply_markup=get_main_kb(game))
    await save_game(callback.from_user.id, game)

async def main():
    if WEBHOOK_URL:
        await bot.delete_webhook()
        await bot.set_webhook(WEBHOOK_URL)
    else:
        await dp.start_polling(bot)

@app.post(WEBHOOK_PATH)
async def webhook(update: dict):
    telegram_update = aiogram.types.Update(**update)
    await dp.feed_update(bot=bot, update=telegram_update)

if __name__ == "__main__":
    import uvicorn
    asyncio.run(main())  # Или uvicorn.run для Render
