from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from modules.items import is_item_consumable


def get_settings_kb(game=None):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
    ])



from modules.items import is_item_consumable, get_item_rank, get_item_rank_marker


def get_use_item_kb(game):
    """Список расходуемых предметов, отсортированный по рангу качества (лучшие сверху)."""
    usable_items = [
        item for item, count in game.inventory.items()
        if count > 0 and is_item_consumable(item)
    ]
    # Сортировка: от наивысшего ранга (5) к низшему (1), затем по алфавиту
    usable_items.sort(key=lambda it: (-get_item_rank(it), it))

    keyboard = []
    for item in usable_items:
        marker = get_item_rank_marker(item)
        keyboard.append([
            InlineKeyboardButton(text=f"{marker} {item}", callback_data=f"use_preview_{item}")
        ])
    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_inspect_menu_kb(game):
    """Клавиатура подробного осмотра любого предмета в инвентаре."""
    items = [(item, count) for item, count in game.inventory.items() if count > 0]
    # Сортируем: еда по рангу, затем остальные предметы
    items.sort(key=lambda entry: (0 if is_item_consumable(entry[0]) else 1, -get_item_rank(entry[0]), entry[0]))

    keyboard = []
    for item, count in items:
        marker = get_item_rank_marker(item)
        keyboard.append([
            InlineKeyboardButton(text=f"🔍 {marker} {item} ×{count}", callback_data=f"inspect_item_{item}")
        ])
    keyboard.append([InlineKeyboardButton(text="↩️ Назад в инвентарь", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_item_card_actions_kb(item_name: str, game=None):
    """Кнопки действий для карточки предмета."""
    keyboard = []
    if item_name == "Костёр":
        keyboard.append([InlineKeyboardButton(text="🔥 Разжечь костёр", callback_data="use_consumable_Костёр")])
    elif item_name == "Бутылка воды":
        keyboard.append([InlineKeyboardButton(text="🧴 Надеть на пояс (в слот фляги)", callback_data="equip_bottle_flask")])
        keyboard.append([InlineKeyboardButton(text="💧 Сделать глоток (+15 жажды)", callback_data="drink_bottle_single")])
    elif item_name == "Факел":
        keyboard.append([InlineKeyboardButton(text="🔦 Взять в левую руку", callback_data="use_item_Факел")])
    elif is_item_consumable(item_name):
        keyboard.append([InlineKeyboardButton(text="🍽️ Применить / Съесть", callback_data=f"use_consumable_{item_name}")])

    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_campfire_recipe_view_kb(recipe_id: str):
    """Кнопки окна рецепта костра."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Приготовить блюдо", callback_data=f"cook_exec_{recipe_id}")],
        [InlineKeyboardButton(text="↩️ Назад к рецептам", callback_data="campfire_recipes")],
    ])


def get_drop_item_kb(game):
    items = [(item, count) for item, count in game.inventory.items() if count > 0]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item} ×{count}", callback_data=f"drop_item_{item}")]
        for item, count in items
    ] + [[InlineKeyboardButton(text="↩️ Назад", callback_data="back")]])


def get_drop_quantity_kb(item_name: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Выбросить 1", callback_data=f"drop_qty:1:{item_name}")],
        [InlineKeyboardButton(text="📦 Выбросить всё", callback_data=f"drop_qty:all:{item_name}")],
        [InlineKeyboardButton(text="🔢 Ввести число", callback_data=f"drop_qty:custom:{item_name}")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
    ])

def get_bottle_actions_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧴 Надеть на пояс (в слот фляги)", callback_data="equip_bottle_flask")],
        [InlineKeyboardButton(text="💧 Сделать глоток (+15 жажды)", callback_data="drink_bottle_single")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
    ])



def get_main_kb(game):
    # Ряд 1: Исследовать + Костёр (справа, только если горит)
    row1 = [
        InlineKeyboardButton(text="🔍 Исследовать", callback_data="action_1"),
    ]
    if getattr(game, "campfire_active", False) and getattr(game, "campfire_durability", 0) > 0:
        d = int(game.campfire_durability)
        m = int(getattr(game, "campfire_max_durability", 10) or 10)
        row1.append(InlineKeyboardButton(text=f"🔥 Костёр {d}/{m}", callback_data="menu_campfire"))

    # Ряд 2: Инвентарь + Пить (если фляга надета) + Спать
    row2 = [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="action_2")]
    if game.equipment.get("flask"):
        water_left = int(getattr(game, "flask_water", 0) or 0)
        row2.append(InlineKeyboardButton(text=f"💧 Пить ({water_left}/20)", callback_data="action_3"))
    row2.append(InlineKeyboardButton(text="😴 Спать", callback_data="action_4"))

    kb = InlineKeyboardMarkup(inline_keyboard=[row1, row2])
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
        [InlineKeyboardButton(text="🪵 Подкинуть дров / топлива", callback_data="campfire_add_fuel_menu")],
        [InlineKeyboardButton(text="🍲 Приготовить еду", callback_data="campfire_recipes")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
    ])
    return kb


def get_campfire_fuel_kb(game):
    """Подменю выбора топлива: Ветка/Палки (+1 к огню) и Кусок коры (+1 к огню)."""
    keyboard = []
    inv = getattr(game, "inventory", {}) or {}

    # 1. Ветка / Палки
    branches = inv.get("Ветка", 0) + inv.get("Палки", 0) + inv.get("Палка", 0)
    if branches > 0:
        actual_branch = "Ветка" if inv.get("Ветка", 0) > 0 else ("Палки" if inv.get("Палки", 0) > 0 else "Палка")
        keyboard.append([
            InlineKeyboardButton(text=f"🪵 Ветка (+1) — {branches} шт.", callback_data=f"feed_fuel:{actual_branch}:1")
        ])
        if branches > 1:
            keyboard.append([
                InlineKeyboardButton(text="🪵 Ветки (до максимума)", callback_data=f"feed_fuel:{actual_branch}:max")
            ])

    # 2. Кусок коры
    bark = inv.get("Кусок коры", 0)
    if bark > 0:
        keyboard.append([
            InlineKeyboardButton(text=f"🪵 Кусок коры (+1) — {bark} шт.", callback_data="feed_fuel:Кусок коры:1")
        ])
        if bark > 1:
            keyboard.append([
                InlineKeyboardButton(text="🪵 Кусок коры (до максимума)", callback_data="feed_fuel:Кусок коры:max")
            ])

    keyboard.append([InlineKeyboardButton(text="⬅️ Назад в костёр", callback_data="menu_campfire")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


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
        [InlineKeyboardButton(text="💧 Ручей", callback_data="location_enter_2")],
        [InlineKeyboardButton(text="🏔 Лощина", callback_data="location_enter_3")],
        [InlineKeyboardButton(text="🏹 Просека", callback_data="location_enter_4")],
        [InlineKeyboardButton(text="🍄 Яр", callback_data="location_enter_5")],
        [InlineKeyboardButton(text="🦇 Пещера", callback_data="location_enter_6")],
        [InlineKeyboardButton(text="🔮 Святилище", callback_data="location_enter_7")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
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
        kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return kb


inventory_inline_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔍 Осмотреть", callback_data="inv_inspect"),
     InlineKeyboardButton(text="✋ Использовать", callback_data="inv_use")],
    [InlineKeyboardButton(text="🗑 Выкинуть", callback_data="inv_drop"),
     InlineKeyboardButton(text="🔨 Крафт", callback_data="inv_craft")],
    [InlineKeyboardButton(text="📜 Рецепты", callback_data="inv_recipes"),
     InlineKeyboardButton(text="👤 Персонаж", callback_data="inv_character")],
    [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
])


def get_inventory_kb(game=None, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура инвентаря."""
    return inventory_inline_kb


character_inline_kb = InlineKeyboardMarkup(inline_keyboard=[

    [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
])


wolf_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🤫 Уйти тихо", callback_data="wolf_leave")],
    [InlineKeyboardButton(text="🔦 Использовать факел", callback_data="wolf_torch")]
])

peek_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👀 Заглянуть внутрь", callback_data="peek_den")]
])

cat_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚫 Оставить его здесь", callback_data="pet_leave")],
    [InlineKeyboardButton(text="🤝 Забрать с собой", callback_data="pet_take")]
])

next_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="➡️ Дальше", callback_data="story_next")]
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
        [InlineKeyboardButton(text="⬆️ До максимума", callback_data="campfire_fuel_max")],
        [InlineKeyboardButton(text="🔢 Своё количество", callback_data="campfire_fuel_custom")],
        [InlineKeyboardButton(text="↩️ Назад в костёр", callback_data="menu_campfire")],
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
