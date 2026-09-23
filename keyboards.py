from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from modules.items import is_item_consumable


def get_bottom_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главное меню / Перезапуск")],
            [
                KeyboardButton(text="📊 Статус"),
                KeyboardButton(text="🎒 Инвентарь"),
                KeyboardButton(text="⚙️ Настройки"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_settings_kb(game):
    mode_text = "📱 Телефон" if game.display_mode == "phone" else "💻 Компьютер"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Телефон", callback_data="settings_mode_phone"),
            InlineKeyboardButton(text="💻 Компьютер", callback_data="settings_mode_pc"),
        ],
        [
            InlineKeyboardButton(text="Длина -", callback_data="settings_length_minus"),
            InlineKeyboardButton(text=f"{game.max_line_length} ({mode_text})", callback_data="settings_noop"),
            InlineKeyboardButton(text="Длина +", callback_data="settings_length_plus"),
        ],
        [
            InlineKeyboardButton(text="Высота -", callback_data="settings_height_minus"),
            InlineKeyboardButton(text=f"{game.max_lines_per_msg} строк", callback_data="settings_noop"),
            InlineKeyboardButton(text="Высота +", callback_data="settings_height_plus"),
        ],
        [InlineKeyboardButton(text="Назад", callback_data="back")],
    ])


def get_use_item_kb(game):
    usable_items = [
        item for item, count in game.inventory.items()
        if count > 0 and is_item_consumable(item)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=item, callback_data=f"use_consumable_{item}")]
        for item in usable_items
    ] + [[InlineKeyboardButton(text="Назад", callback_data="back")]])


def get_drop_item_kb(game):
    items = [(item, count) for item, count in game.inventory.items() if count > 0]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item} ×{count}", callback_data=f"drop_item_{item}")]
        for item, count in items
    ] + [[InlineKeyboardButton(text="Назад", callback_data="back")]])


def get_drop_quantity_kb(item_name: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Выбросить 1", callback_data=f"drop_qty:1:{item_name}")],
        [InlineKeyboardButton(text="Выбросить всё", callback_data=f"drop_qty:all:{item_name}")],
        [InlineKeyboardButton(text="Ввести число", callback_data=f"drop_qty:custom:{item_name}")],
        [InlineKeyboardButton(text="Назад", callback_data="back")],
    ])

def get_main_kb(game):
    row1 = [
        InlineKeyboardButton(text="🔍 Исследовать", callback_data="action_1"),
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="action_2"),
    ]
    # Костёр на главном только пока горит (прочность > 0)
    if getattr(game, "campfire_active", False) and getattr(game, "campfire_durability", 0) > 0:
        d = int(game.campfire_durability)
        m = int(getattr(game, "campfire_max_durability", 10) or 10)
        row1.append(InlineKeyboardButton(text=f"🔥 Костёр {d}/{m}", callback_data="menu_campfire"))

    water = game.inventory.get("Вода", 0)
    drink_text = f"💧 Пить ({water}/{game.water_capacity})" if water > 0 else "💧 Пить (пусто)"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        row1,
        [
            InlineKeyboardButton(text=drink_text, callback_data="action_3"),
            InlineKeyboardButton(text="😴 Спать", callback_data="action_4"),
        ],
    ])
    if game.weather in {"rain", "storm"}:
        kb.inline_keyboard.append([
            InlineKeyboardButton(text="🌧️ Собрать дождевую воду", callback_data="action_collect_water")
        ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(text="🗺️ Локации", callback_data="locations_menu")
    ])
    return kb


def get_campfire_kb(game):
    """Меню Костра."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥩 Пожарить предмет", callback_data="campfire_cook_single")],
        [InlineKeyboardButton(text="📜 Рецепты", callback_data="campfire_recipes")],
        [InlineKeyboardButton(text="🪵 Подкинуть дров", callback_data="campfire_add_fuel_menu")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")],
    ])
    return kb

def get_campfire_recipes_kb(game):
    """Меню рецептов костра — динамический список с маркерами доступности."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍖 Жареное мясо", callback_data="campfire_recipe_meat")],
        [InlineKeyboardButton(text="⬅️ Назад в костёр", callback_data="menu_campfire")],
    ])
    return kb

def get_campfire_recipe_kb(game, recipe_name: str):
    """Кнопки для выбора ингредиентов рецепта."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥩 Мясо", callback_data=f"campfire_ingredient_{recipe_name}_meat")],
        [InlineKeyboardButton(text="🍄 Грибы", callback_data=f"campfire_ingredient_{recipe_name}_mushroom")],
        [InlineKeyboardButton(text="🥕 Овощи", callback_data=f"campfire_ingredient_{recipe_name}_veg")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="campfire_recipes")],
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

def get_trap_buttons_kb(game):
    """Кнопки ловушек для каждой локации (1-7)."""
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for loc_id in range(1, 8):
        trap = game.traps.get(loc_id)
        if trap and trap.get("is_active"):
            location_name = {
                2: "Ручей", 3: "Лощина", 4: "Просека", 5: "Яр",
                6: "Пещера", 7: "Святилище"
            }.get(loc_id, f"Локация {loc_id}")
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"🕳️ {location_name}",
                    callback_data=f"trap_place_{loc_id}"
                )
            ])
        elif trap and trap.get("is_broken"):
            # Ловушка сломана — кнопка для установки новой
            location_name = {
                2: "Ручей", 3: "Лощина", 4: "Просека", 5: "Яр",
                6: "Пещера", 7: "Святилище"
            }.get(loc_id, f"Локация {loc_id}")
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"🔨 {location_name}",
                    callback_data=f"trap_replace_{loc_id}"
                )
            ])
    if kb.inline_keyboard:
        kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")])
    return kb

inventory_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👁 Осмотреть", callback_data="inv_inspect"),
     InlineKeyboardButton(text="✋ Использовать", callback_data="inv_use")],
    [InlineKeyboardButton(text="🗑 Выкинуть", callback_data="inv_drop"),
     InlineKeyboardButton(text="🔨 Крафт", callback_data="inv_craft")],
    [InlineKeyboardButton(text="📜 Рецепты", callback_data="inv_recipes"),
     InlineKeyboardButton(text="👤 Персонаж", callback_data="inv_character")],
    [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
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

def get_campfire_kb(game):
    """Меню Костра."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥩 Пожарить предмет", callback_data="campfire_cook_single")],
        [InlineKeyboardButton(text="📜 Рецепты", callback_data="campfire_recipes")],
        [InlineKeyboardButton(text="🪵 Подкинуть дров", callback_data="campfire_add_fuel_menu")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")],
    ])
    return kb

def get_campfire_fuel_kb(game):
    """Подменю выбора количества дров."""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="[ До максимума ]", callback_data="campfire_fuel_max")],
        [InlineKeyboardButton(text="[ Своё количество ]", callback_data="campfire_fuel_custom")],
        [InlineKeyboardButton(text="[ ⬅️ Назад в костёр ]", callback_data="menu_campfire")],
    ])
    return kb

def get_location_kb(game, location_id: int):
    """Получить клавиатуру для конкретной локации."""
    # Для теперь просто возвращаем основную клавиатуру
    return get_main_kb(game)


def get_campfire_light_confirm_kb():
    """Подтверждение розжига скрафченного костра."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Разжечь", callback_data="campfire_confirm_light")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="inv_use")],
    ])
