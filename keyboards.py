from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from modules.items import is_item_consumable


def get_settings_kb(game=None):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
    ])


def get_start_resume_kb(hero_name: str) -> InlineKeyboardMarkup:
    """Стартовая клавиатура для продолжения игры за существующего персонажа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"▶️ Продолжить за {hero_name}", callback_data="load_game")],
        [InlineKeyboardButton(text="⚠️ Начать с чистого листа", callback_data="confirm_new_game")],
    ])


def get_confirm_new_game_kb() -> InlineKeyboardMarkup:
    """Подтверждение удаления персонажа и начала игры заново."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Да, удалить и начать заново", callback_data="start_new_game_confirmed")],
        [InlineKeyboardButton(text="↩️ Вернуться к персонажу", callback_data="cancel_new_game")],
    ])


def get_start_new_game_kb() -> InlineKeyboardMarkup:
    """Стартовая кнопка для нового игрока."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать выживание", callback_data="start_new_game")],
    ])



from modules.items import is_item_consumable, get_item_rank, get_item_rank_marker, get_item_emoji


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
    """Клавиатура подробного осмотра любого предмета в инвентаре (без 🔍 на каждой кнопке)."""
    items_list = [(item, count) for item, count in game.inventory.items() if count > 0]
    items_list.sort(key=lambda entry: (0 if is_item_consumable(entry[0]) else 1, -get_item_rank(entry[0]), entry[0]))

    keyboard = []
    for item, count in items_list:
        item_clean = item.replace(" 🔥", "").replace("🔥", "").strip()
        if is_item_consumable(item_clean):
            marker = get_item_rank_marker(item_clean)
        else:
            marker = get_item_emoji(item_clean)
        qty_str = f" ×{count}" if count > 1 else ""
        keyboard.append([
            InlineKeyboardButton(text=f"{marker} {item}{qty_str}", callback_data=f"inspect_item_{item}")
        ])
    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
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
    elif item_name == "Крепкий посох":
        keyboard.append([InlineKeyboardButton(text="🪵 Взять в правую руку", callback_data="use_item_Крепкий посох")])
    elif item_name == "Рюкзак с красной заплаткой":
        keyboard.append([InlineKeyboardButton(text="🎒 Надеть на спину", callback_data="use_item_Рюкзак с красной заплаткой")])
    elif item_name == "Сланцевая маска":
        keyboard.append([InlineKeyboardButton(text="🎭 Надеть маску", callback_data="use_item_Сланцевая маска")])
    elif item_name == "Сланцевый панцирь":
        keyboard.append([InlineKeyboardButton(text="🦺 Надеть панцирь", callback_data="use_item_Сланцевый панцирь")])
    elif item_name == "Сланцевые поножи":
        keyboard.append([InlineKeyboardButton(text="👖 Надеть поножи", callback_data="use_item_Сланцевые поножи")])
    elif item_name == "Сланцевые ботинки":
        keyboard.append([InlineKeyboardButton(text="🥾 Надеть ботинки", callback_data="use_item_Сланцевые ботинки")])
    elif item_name == "Отремонтированные ботинки":
        keyboard.append([InlineKeyboardButton(text="🥾 Надеть ботинки", callback_data="use_item_Отремонтированные ботинки")])
    elif is_item_consumable(item_name):
        keyboard.append([InlineKeyboardButton(text="🍽️ Съесть / Применить", callback_data=f"use_consumable_{item_name}")])

    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_campfire_recipe_view_kb(recipe_id: str, max_count: int = 1):
    """Кнопки окна рецепта костра с выбором порций (Приготовить 1 / Приготовить всё)."""
    keyboard = []
    if max_count >= 1:
        row = [InlineKeyboardButton(text="🍳 Приготовить 1", callback_data=f"cook_qty:{recipe_id}:1")]
        if max_count > 1:
            row.append(InlineKeyboardButton(text=f"🍲 Приготовить всё ({max_count})", callback_data=f"cook_qty:{recipe_id}:all"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_drop_item_kb(game):
    items = [(item, count) for item, count in game.inventory.items() if count > 0]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item} ×{count}", callback_data=f"drop_item_{item}")]
        for item, count in items
    ] + [[InlineKeyboardButton(text="↩️ Назад", callback_data="back")]])


def get_drop_quantity_kb(item_name: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Выбросить 1", callback_data=f"drop_qty:1:{item_name}"),
         InlineKeyboardButton(text="📦 Выбросить всё", callback_data=f"drop_qty:all:{item_name}")],
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

    # Ряд 2: Инвентарь + Пить (если фляга) + Спать
    row2 = [
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="action_2"),
    ]
    if game.equipment.get("flask"):
        water_left = int(getattr(game, "flask_water", 0) or 0)
        row2.append(InlineKeyboardButton(text=f"💧 Пить ({water_left}/20)", callback_data="action_3"))
    row2.append(InlineKeyboardButton(text="😴 Спать", callback_data="action_4"))

    kb_rows = [row1, row2]
    if game.weather in {"rain", "storm"}:
        kb_rows.append([
            InlineKeyboardButton(text="🌧️ Пить дождь", callback_data="action_collect_water")
        ])
    if getattr(game, "locations_unlocked", False):
        kb_rows.append([
            InlineKeyboardButton(text="🗺️ Локации", callback_data="locations_menu")
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)



def get_campfire_kb(game=None):
    """Меню Костра (только Рецепты, Подкинуть и Назад)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Рецепты", callback_data="campfire_recipes"),
         InlineKeyboardButton(text="🪵 Подкинуть", callback_data="campfire_add_fuel_menu")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
    ])


def get_campfire_fuel_kb(game):
    """Подменю выбора топлива: Палки (1 шт = +1 к огню) и Кора (2 шт = +1 к огню)."""
    inv = getattr(game, "inventory", {}) or {}
    sticks = inv.get("Ветка", 0) + inv.get("Палки", 0) + inv.get("Палка", 0)
    bark = inv.get("Кусок коры", 0) + inv.get("Кора", 0)

    keyboard = [
        [InlineKeyboardButton(text=f"🪵 Палки ({sticks})", callback_data="fuel_menu:sticks")],
        [InlineKeyboardButton(text=f"🧱 Кора ({bark})", callback_data="fuel_menu:bark")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_fuel_quantity_kb(fuel_type: str, game=None):
    """Выбор количества топлива для подкидывания в костёр (без отдельной кнопки ввода числа)."""
    if fuel_type == "sticks":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🪵 Добавить 1", callback_data="feed_fuel_action:sticks:1"),
                InlineKeyboardButton(text="🪵 До максимума", callback_data="feed_fuel_action:sticks:max"),
            ],
            [
                InlineKeyboardButton(text="↩️ Назад", callback_data="back"),
            ],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🧱 Добавить 2 коры (+1 🔥)", callback_data="feed_fuel_action:bark:2"),
                InlineKeyboardButton(text="🧱 До максимума", callback_data="feed_fuel_action:bark:max"),
            ],
            [
                InlineKeyboardButton(text="↩️ Назад", callback_data="back"),
            ],
        ])


def get_campfire_recipes_kb(game):
    """Меню рецептов костра: показывает ТОЛЬКО блюда, на которые хватает ингредиентов прямо сейчас."""
    from modules.cooking import COOKING_RECIPES, can_cook
    from modules.items import get_item_rank_marker

    keyboard = []
    sorted_recipes = sorted(
        COOKING_RECIPES.items(),
        key=lambda item: item[1].get("rank", 1),
        reverse=True,
    )
    for r_id, r_data in sorted_recipes:
        if can_cook(game, r_id):
            res_name = r_data["result"]
            marker = get_item_rank_marker(res_name)
            keyboard.append([
                InlineKeyboardButton(text=f"{marker} {res_name}", callback_data=f"cook_recipe_view_{r_id}")
            ])
    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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
    """Клавиатура перехода по локациям."""
    if getattr(game, "wolf_lair_active", False):
        has_staff = game.equipment.get("hand_right") == "Крепкий посох"
        btn_text = "🐾 Волчье логово" if has_staff else "🐾 Волчье логово (Опасно)"
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data="wolf_lair_enter")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
        ])
    elif getattr(game, "wolf_lair_defeated", False):
        keyboard = [
            [InlineKeyboardButton(text="🌲 Стартовый лес", callback_data="location_enter_1")],
            [InlineKeyboardButton(text="🏞️ Ручей", callback_data="location_enter_2")],
        ]
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Скромная Лощина" in unlocked:
            keyboard.append([InlineKeyboardButton(text="⛰️ Скромная Лощина", callback_data="location_enter_3")])
        keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    else:
        keyboard = []
        unlocked = getattr(game, "unlocked_locations", ["Лесной старт"]) or ["Лесной старт"]
        if "Лесной старт" in unlocked:
            keyboard.append([InlineKeyboardButton(text="🌲 Стартовый лес", callback_data="location_enter_1")])
        if "Ручей" in unlocked or "Ручей с Змеями" in unlocked:
            keyboard.append([InlineKeyboardButton(text="🏞️ Ручей", callback_data="location_enter_2")])
        if "Скромная Лощина" in unlocked:
            keyboard.append([InlineKeyboardButton(text="⛰️ Скромная Лощина", callback_data="location_enter_3")])
        keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_wolf_battle_kb():
    """Клавиатура пошагового боя со старым волком."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚔️ Ударить", callback_data="wolf_battle_attack"),
            InlineKeyboardButton(text="🛡 Защита", callback_data="wolf_battle_defend"),
        ],
        [
            InlineKeyboardButton(text="🏃 Сбежать", callback_data="wolf_battle_flee"),
        ],
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
    [InlineKeyboardButton(text="✋ Осмотреть", callback_data="inv_inspect"),
     InlineKeyboardButton(text="🔨 Крафт", callback_data="inv_craft")],
    [InlineKeyboardButton(text="🗑 Выкинуть", callback_data="inv_drop"),
     InlineKeyboardButton(text="👤 Персонаж", callback_data="menu_character")],
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


def get_location_kb(game, location_id: int):
    """Получить клавиатуру для конкретной локации."""
    return get_main_kb(game)


def get_campfire_light_confirm_kb():
    """Подтверждение розжига скрафченного костра."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Разжечь", callback_data="campfire_confirm_light")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back")],
    ])
