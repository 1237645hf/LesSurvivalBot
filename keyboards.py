from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

def get_main_kb(game):
    kb = [
        [KeyboardButton(text="Исследовать")],
        [KeyboardButton(text="Инвентарь"), KeyboardButton(text="Пить"), KeyboardButton(text="Спать")]
    ]
    # Conditional: if game.resource_counters['факел'] > 0: kb.append([KeyboardButton(text="Экипировать факел")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def inventory_inline_kb(game):
    buttons = []
    for item in game.inventory:
        buttons.append([InlineKeyboardButton(text=f"{item} ({game.inventory[item]})", callback_data=f"inv_inspect_{item}")])
    buttons.append([InlineKeyboardButton(text="Крафт", callback_data="inv_craft")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def wolf_kb(game):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Убежать", callback_data="wolf_flee")],
        [InlineKeyboardButton(text="Сразиться", callback_data="wolf_fight")]
    ])

# Аналогично для cat_kb, peek_den_kb, craft_kb (с рецептами из crafts: for r in RECIPES: add button callback_data=f"craft_{r}"), equip_kb и т.д.

def craft_kb(game):
    buttons = [[InlineKeyboardButton(text=recipe, callback_data=f"craft_{recipe}")] for recipe in RECIPES]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
