# ГРУППА: Импорты
# Описание: Импорт для создания клавиатур. Нужно для кнопок в Telegram.

# БЛОК 1.1: Импорты aiogram types
# Описание: Классы для inline и reply клавиатур. Нужно для построения markup.
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# ГРУППА: Основные клавиатуры (reply и inline)
# Описание: Функции возвращающие клавиатуры на основе состояния game. Это UI для меню, событий.

# БЛОК 2.1: Главная клавиатура (get_main_kb)
# Описание: Основные кнопки (исследовать, инвентарь и т.д.). Conditional на counters. Нужно для главного экрана.
def get_main_kb(game):
    kb = [
        [KeyboardButton(text="Исследовать")],
        [KeyboardButton(text="Инвентарь"), KeyboardButton(text="Пить"), KeyboardButton(text="Спать")]
    ]
    # Conditional: если есть факел по счётчику
    if game.resource_counters.get('факел', 0) > 0:
        kb.append([KeyboardButton(text="Экипировать факел")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# БЛОК 2.2: Инвентарь inline (inventory_inline_kb)
# Описание: Кнопки для предметов + крафт. Нужно для просмотра инвентаря.
def inventory_inline_kb(game):
    buttons = []
    for item in game.inventory:
        buttons.append([InlineKeyboardButton(text=f"{item} ({game.inventory[item]})", callback_data=f"inv_inspect_{item}")])
    buttons.append([InlineKeyboardButton(text="Крафт", callback_data="inv_craft")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# БЛОК 2.3: Клавиатуры для событий (wolf_kb, cat_kb, peek_den_kb)
# Описание: Inline для выборов в сюжете. Нужно для interactive событий.
def wolf_kb(game):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Убежать", callback_data="wolf_flee")],
        [InlineKeyboardButton(text="Сразиться", callback_data="wolf_fight")]
    ])

def cat_kb(game):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оставить его здесь", callback_data="cat_leave")],
        [InlineKeyboardButton(text="Забрать с собой", callback_data="cat_take")]
    ])

def peek_den_kb(game):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Заглянуть внутрь", callback_data="peek_den")],
        [InlineKeyboardButton(text="Уйти", callback_data="peek_leave")]  # Пример, адаптируй
    ])

# БЛОК 2.4: Клавиатуры для инвентаря/крафта (craft_kb, equip_kb, get_inventory_actions_kb)
# Описание: Кнопки для действий над предметами, крафта, экипировки. Нужно для подменю.
def craft_kb(game):
    buttons = [[InlineKeyboardButton(text=recipe, callback_data=f"craft_{recipe}")] for recipe in RECIPES]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def equip_kb(game):
    buttons = []
    if "факел" in game.inventory:  # Адаптируй под твои предметы
        buttons.append([InlineKeyboardButton(text="Экипировать факел", callback_data="equip_torch")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_inventory_actions_kb(game):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Использовать", callback_data="inv_use")],
        [InlineKeyboardButton(text="Осмотреть", callback_data="inv_inspect")],
        [InlineKeyboardButton(text="Выкинуть", callback_data="inv_drop")],
        [InlineKeyboardButton(text="Экипировать", callback_data="inv_equip")]
    ])

# БЛОК 2.5: Другие клавиатуры (main_menu_kb)
# Описание: Альтернативная основная клавиатура, если нужно. Можно расширять.
def main_menu_kb(game):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Инвентарь"), KeyboardButton(text="Персонаж")],
        [KeyboardButton(text="Карта"), KeyboardButton(text="Спать")]
    ], resize_keyboard=True)
