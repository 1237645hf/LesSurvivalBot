# ГРУППА: Импорты библиотек и модулей
# Описание: Здесь импортируются все необходимые внешние библиотеки и внутренние модули. Это нужно для доступа к функциям (async, logging, Counter и т.д.) и твоим файлам (crafts, keyboards, stories). Без этого код не запустится.

# БЛОК 1.1: Стандартные импорты (библиотеки Python)
# Описание: Импорт базовых инструментов для асинхронности, логирования, работы с ОС, коллекциями, датами и рандомом. Нужно для обработки событий, логов, случайных предметов/погоды.
import asyncio
import logging
import os
from collections import Counter
from datetime import datetime
from random import choice, randint

# БЛОК 1.2: Импорты aiogram и связанных (для Telegram бота)
# Описание: Импорт для бота, диспетчера, ошибок, фильтров, состояний, типов сообщений. Нужно для обработки команд, callback'ов, клавиатур и FSM.
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramRetryAfter
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

# БЛОК 1.3: Импорты FastAPI и MongoDB (для webhook и БД)
# Описание: Для вебхука на Render и хранения данных в MongoDB. Нужно для онлайн-работы бота и сохранения состояний игроков.
from fastapi import FastAPI
from pymongo import MongoClient

# БЛОК 1.4: Импорты из твоих модулей (crafts, keyboards, stories)
# Описание: Доступ к рецептам, клавиатурам, событиям. Нужно для интеграции сюжета, крафта и UI.
from crafts import RECIPES, check_craft, use_item
from keyboards import (
    get_main_kb, inventory_inline_kb, craft_kb, wolf_kb,
    cat_kb, peek_den_kb, equip_kb, get_inventory_actions_kb, main_menu_kb  # Добавлены недостающие
)
from stories import EVENTS, get_thought, trigger_event

# ГРУППА: Конфигурация (токены, URL, БД)
# Описание: Здесь загружаются переменные из env (токен, URL, URI). Это нужно для безопасности (не хранить secrets в коде) и настройки webhook/БД.

# БЛОК 2.1: Загрузка переменных из окружения
# Описание: Получение токена бота, базового URL Render, URI MongoDB. Нужно для подключения к Telegram и БД.
TOKEN = os.getenv("TOKEN")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")
MONGO_URI = os.getenv("MONGO_URI")

# БЛОК 2.2: Настройка webhook
# Описание: Формирование пути и URL для webhook. Нужно для онлайн-режима на Render (бот получает обновления через веб).
WEBHOOK_PATH = f"/bot/{TOKEN}"
WEBHOOK_URL = f"{BASE_URL}{WEBHOOK_PATH}" if BASE_URL else None

# БЛОК 2.3: Подключение к MongoDB
# Описание: Создание клиента, БД и коллекции. Нужно для хранения/загрузки данных игроков.
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['forest_game']
players_collection = db['players']

# ГРУППА: Настройка логирования и бота
# Описание: Инициализация логов, бота, диспетчера, хранилища, FastAPI. Это базовая настройка для запуска бота.

# БЛОК 3.1: Логирование
# Описание: Установка уровня логирования. Нужно для отладки ошибок в консоли/логах Render.
logging.basicConfig(level=logging.INFO)

# БЛОК 3.2: Инициализация бота и диспетчера
# Описание: Создание бота с парсингом HTML, хранилища в памяти, диспетчера. Нужно для обработки сообщений/callback'ов.
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# БЛОК 3.3: FastAPI приложение
# Описание: Создание веб-сервера для webhook. Нужно для приема обновлений от Telegram на Render.
app = FastAPI()

# ГРУППА: Классы состояний (FSM)
# Описание: Определение состояний для FSM (finite state machine). Нужно для многошаговых взаимодействий (например, ввод имени).

# БЛОК 4.1: Класс Form
# Описание: Состояние для имени (если используешь). Нужно для диалогов с пользователем.
class Form(StatesGroup):
    name = State()

# ГРУППА: Класс Game (логика игры)
# Описание: Основной класс с состоянием игрока (hp, inventory и т.д.). Здесь вся механика выживания, логов, UI.

# БЛОК 5.1: Инициализация (конструктор)
# Описание: Начальные значения переменных. Нужно для старта новой игры.
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
        self.resource_counters = Counter()  # Добавлено для счётчиков ресурсов/триггеров

# БЛОК 5.2: Методы для логов и UI
# Описание: Добавление записей в лог, формирование статус-бара и лога. Нужно для отображения интерфейса.
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

# БЛОК 5.3: Методы для инвентаря и навигации
# Описание: Текст инвентаря, стек экранов. Нужно для просмотра предметов и переключения меню.
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

# БЛОК 5.4: Обновление погоды и статов
# Описание: Смена погоды, обновление голода/жажды/hp. Нужно для симуляции выживания и проверки смерти.
    def update_weather(self):
        self.weather = choice(['солнечно', 'дождливо', 'пасмурно'])

    def update_stats(self):
        self.hunger = min(100, self.hunger + 10)
        self.thirst = min(100, self.thirst + 10)
        if self.hunger >= 100 or self.thirst >= 100:
            self.hp = max(0, self.hp - 10)
        if self.hp <= 0:
            self.add_log("Вы погибли... Игра окончена.")  # Добавлено обработка смерти

# ГРУППА: Функции загрузки/сохранения игры
# Описание: Загрузка/сохранение состояния из БД. Нужно для персистентности между сессиями.

# БЛОК 6.1: Загрузка игры
# Описание: Получение данных из MongoDB, создание Game. Нужно для продолжения игры.
async def load_game(user_id: int) -> Game:
    data = players_collection.find_one({"_id": user_id})
    if data:
        game = Game()
        for key, value in data.items():
            if key != "_id":
                setattr(game, key, value)
        return game
    return Game()

# БЛОК 6.2: Сохранение игры
# Описание: Сохранение в MongoDB с upsert. Нужно для обновления БД.
async def save_game(user_id: int, game: Game):
    data = vars(game)
    data["_id"] = user_id
    players_collection.replace_one({"_id": user_id}, data, upsert=True)

# ГРУППА: Вспомогательные функции
# Описание: Обновление сообщений, обработка flood. Нужно для UI и избежания банов от Telegram.

# БЛОК 7.1: Обновление или отправка сообщения
# Описание: Edit или answer сообщения. Нужно для динамического UI.
async def update_or_send_message(message: Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except:
        await message.answer(text, reply_markup=reply_markup)

# ГРУППА: Хендлеры сообщений (@dp.message)
# Описание: Обработка команд и текстовых сообщений (start, исследовать, пить и т.д.). Это основная логика взаимодействия.

# БЛОК 8.1: Команда /start
# Описание: Старт игры, загрузка, UI. Нужно для инициации.
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    game = await load_game(message.from_user.id)
    await message.answer(game.get_ui(), reply_markup=get_main_kb(game))
    await save_game(message.from_user.id, game)

# БЛОК 8.2: Обработка текстовых сообщений (process_message)
# Описание: Реакция на кнопки (исследовать, пить, спать, инвентарь). Включает рандом предметов, forced палку, триггеры.
@dp.message()
async def process_message(message: Message, state: FSMContext):
    game = await load_game(message.from_user.id)
    text = message.text.lower()

    if text == 'исследовать' and game.ap > 0:
        game.ap -= 1
        items = ['ягоды', 'ветка', 'камень', 'грибы']
        item = choice(items)
        
        # Подгруппа: Forced палка на день 2
        # Описание: Форсирование ветки на день 2, второй исслед, с мыслью. Нужно для триггера сюжета.
        if game.day == 2 and game.research_count_day2 == 1 and not game.found_branch_once:
            item = 'ветка'
            game.found_branch_once = True
            game.add_log(get_thought('branch_found'))  # Мысль из stories

        game.inventory[item] += 1
        game.resource_counters[item] += 1  # Инкремент счётчика
        game.add_log(f"Вы нашли: {item}")
        game.research_count_day2 += 1 if game.day == 2 else 0

        # Подгруппа: Проверка триггера события
        # Описание: Вызов события на основе counters/day/ap. Нужно для запуска сюжета.
        event_name = trigger_event(game)
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

    # Подгруппа: Другие действия (персонаж, карта и т.д.)
    # Описание: Если есть дополнительные меню — добавь здесь. Нужно для расширения.
    # (Твой старый код для персонажа/карты — вставь если нужно)

    await update_or_send_message(message, game.get_ui(), get_main_kb(game))
    await save_game(message.from_user.id, game)

# ГРУППА: Хендлеры callback'ов (@dp.callback_query)
# Описание: Обработка нажатий inline-кнопок (инвентарь, события, крафт).

# БЛОК 9.1: Основной процессор callback
# Описание: Разбор data, вызов use/craft, применение эффектов событий. Нужно для interactive UI.
@dp.callback_query()
async def process_callback(callback: CallbackQuery):
    game = await load_game(callback.from_user.id)
    data = callback.data

    if data.startswith('inv_'):
        parts = data.split('_')
        action = parts[1]
        item = '_'.join(parts[2:]) if len(parts) > 2 else None

        if action == 'craft':
            await callback.message.edit_text("Крафт:", reply_markup=craft_kb(game))
        elif action == 'use' and item:
            result = use_item(game, item)  # Из crafts
            game.add_log(result)
        # Подгруппа: Другие inv_ действия (inspect, drop, equip)
        # Описание: Осмотр, выкидывание, экипировка. Добавь логику из старого кода.
        elif action == 'inspect' and item:
            game.add_log(f"Осмотр: {item} — описание.")  # Пример
        elif action == 'drop' and item:
            game.inventory[item] -= 1
            game.add_log(f"Выкинули: {item}")
        elif action == 'equip' and item:
            game.equipment[item] = True
            game.add_log(f"Экипировано: {item}")

    elif data in ['wolf_flee', 'wolf_fight']:
        effects = EVENTS['wolf']['effects'].get(data, {})
        for key, val in effects.items():
            setattr(game, key, getattr(game, key) + val)
        outcome = EVENTS['wolf']['outcomes'].get(data, "")
        game.add_log(outcome)
        game.story_state = None

    # Подгруппа: Обработка других событий (cat, peek_den)
    # Описание: Аналогично wolf — эффекты и исходы. Нужно для завершения сюжета.
    elif data in ['cat_take', 'cat_leave']:
        # Аналогично, из EVENTS['cat']
        pass  # Добавь логику
    elif data.startswith('peek_'):
        # Аналогично
        pass

    elif data.startswith('craft_'):
        recipe_name = data.split('_')[1]
        result = check_craft(game, recipe_name)
        game.add_log(result)

    await callback.message.edit_text(game.get_ui(), reply_markup=get_main_kb(game))
    await save_game(callback.from_user.id, game)

# ГРУППА: Запуск бота
# Описание: Основная функция запуска (polling или webhook). Нужно для старта приложения.

# БЛОК 10.1: Асинхронный main
# Описание: Установка webhook или polling. Нужно для онлайн/локального режима.
async def main():
    if WEBHOOK_URL:
        await bot.delete_webhook()
        await bot.set_webhook(WEBHOOK_URL)
    else:
        await dp.start_polling(bot)

# БЛОК 10.2: Webhook обработчик
# Описание: Прием обновлений от Telegram. Нужно для FastAPI на Render.
@app.post(WEBHOOK_PATH)
async def webhook(update: dict):
    telegram_update = aiogram.types.Update(**update)
    await dp.feed_update(bot=bot, update=telegram_update)

# БЛОК 10.3: Запуск скрипта
# Описание: Входная точка. Нужно для выполнения кода.
if __name__ == "__main__":
    import uvicorn
    asyncio.run(main())  # Или uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
