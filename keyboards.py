from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_kb(game):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Исследовать", callback_data="action_1"),
         InlineKeyboardButton(text="Инвентарь", callback_data="action_2")],
        [InlineKeyboardButton(text=f"Пить ({game.inventory.get('Вода', 0)}/{game.water_capacity})", callback_data="action_3") if game.inventory.get('Вода', 0) > 0 else InlineKeyboardButton(text="Пить (пусто)", callback_data="action_3"),
         InlineKeyboardButton(text="Спать", callback_data="action_4")]
    ])
    if game.weather == "rain":
        kb.inline_keyboard.append([InlineKeyboardButton(text="Собрать воду", callback_data="action_collect_water")])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="Локации", callback_data="locations_menu")
    ])
    return kb


def get_locations_kb(game):
    """Временная панель входа; условия доступности подключаются позже."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ручей", callback_data="location_enter_2")],
        [InlineKeyboardButton(text="Лощина", callback_data="location_enter_3")],
        [InlineKeyboardButton(text="Просека", callback_data="location_enter_4")],
        [InlineKeyboardButton(text="Яр", callback_data="location_enter_5")],
        [InlineKeyboardButton(text="Пещера", callback_data="location_enter_6")],
        [InlineKeyboardButton(text="Святилище", callback_data="location_enter_7")],
        [InlineKeyboardButton(text="Назад", callback_data="back")],
    ])

inventory_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Осмотреть", callback_data="inv_inspect"),
     InlineKeyboardButton(text="Использовать", callback_data="inv_use")],
    [InlineKeyboardButton(text="Выкинуть", callback_data="inv_drop"),
     InlineKeyboardButton(text="Крафт", callback_data="inv_craft")],
    [InlineKeyboardButton(text="Персонаж", callback_data="inv_character"),
     InlineKeyboardButton(text="Назад", callback_data="back")],
])

character_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Назад", callback_data="back")]
])

wolf_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Уйти тихо", callback_data="wolf_leave")],
    [InlineKeyboardButton(text="Использовать факел", callback_data="wolf_torch")]
])

peek_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Заглянуть внутрь", callback_data="peek_den")]
])

cat_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Оставить его здесь", callback_data="pet_leave")],
    [InlineKeyboardButton(text="Забрать с собой", callback_data="pet_take")]
])

next_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Дальше", callback_data="story_next")]
])

def get_location_kb(game, location_id: int):
    """Получить клавиатуру для конкретной локации."""
    # Для теперь просто возвращаем основную клавиатуру
    return get_main_kb(game)
