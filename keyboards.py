from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_kb(game):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Исследовать", callback_data="action_1"),
         InlineKeyboardButton(text="🎒 Инвентарь", callback_data="action_2")],
        [InlineKeyboardButton(text=f"💧 Пить ({game.inventory['Бутылка воды']}/{game.water_capacity})", callback_data="action_3") if game.inventory['Бутылка воды'] > 0 else InlineKeyboardButton(text="💧 Пить (пусто)", callback_data="action_3"),
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
