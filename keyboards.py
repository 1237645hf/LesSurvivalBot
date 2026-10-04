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


def get_death_kb() -> InlineKeyboardMarkup:
    """Клавиатура экрана смерти: рестарт игры."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Начать заново", callback_data="start_new_game_confirmed")],
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
    elif item_name == "Армейская фляга":
        keyboard.append([InlineKeyboardButton(text="🧴 Надеть на пояс (в слот фляги)", callback_data="equip_army_flask")])
    elif item_name == "Бутылка дождевой воды":
        keyboard.append([InlineKeyboardButton(text="💧 Сделать глоток (риск)", callback_data="drink_rain_bottle")])
    elif item_name == "Факел":
        keyboard.append([InlineKeyboardButton(text="🕯️ Взять в левую руку", callback_data="use_item_Факел")])
    elif item_name == "Крепкий посох":
        keyboard.append([InlineKeyboardButton(text="🦯 Взять в правую руку", callback_data="use_item_Крепкий посох")])
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
    elif item_name == "Окованный посох":
        keyboard.append([InlineKeyboardButton(text="🦯 Взять в правую руку", callback_data="use_item_Окованный посох")])
    elif item_name == "Клык волка":
        keyboard.append([InlineKeyboardButton(text="📿 Надеть амулет", callback_data="use_item_Клык волка")])
    elif item_name == "Охотничья ловушка":
        keyboard.append([InlineKeyboardButton(text="🪤 Установить ловушку", callback_data="use_item_Охотничья ловушка")])
    elif item_name == "Приманка для слизней":
        keyboard.append([InlineKeyboardButton(text="🍯 Установить приманку", callback_data="use_item_Приманка для слизней")])
    elif item_name == "Старый фонарь":
        keyboard.append([InlineKeyboardButton(text="🔦 Взять в левую руку", callback_data="use_item_Старый фонарь")])
    elif item_name == "Костяной амулет охотника":
        keyboard.append([InlineKeyboardButton(text="🧿 Надеть амулет", callback_data="use_item_Костяной амулет охотника")])
    elif is_item_consumable(item_name):
        keyboard.append([InlineKeyboardButton(text="🍽️ Съесть / Применить", callback_data=f"use_consumable_{item_name}")])

    if game and game.equipment.get("pants") == "Кожаные поножи":
        from modules.items import ITEMS
        it_info = ITEMS.get(item_name, {})
        is_healing = (
            item_name == "Янтарное зелье"
            or it_info.get("effects", {}).get("hp", 0) > 0
            or it_info.get("type") in ("potion", "food", "medicine")
        )
        if is_healing:
            if getattr(game, "pants_pocket", None) == item_name:
                keyboard.append([InlineKeyboardButton(text="👝 Извлечь из футляра", callback_data="pocket_remove")])
            else:
                keyboard.append([InlineKeyboardButton(text="👝 Вложить в футляр на поножах", callback_data=f"pocket_insert_{item_name}")])

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
    # Ряд 1: Исследовать + Костёр/Печь (справа)
    explore_text = "🔍 Исследовать"
    if game and getattr(game, "equipment", {}).get("hand_left") == "Старый фонарь":
        dur = int(getattr(game, "lantern_durability", 20) or 0)
        max_dur = int(getattr(game, "lantern_max_durability", 20) or 20)
        explore_text = f"🔦 Исследовать ({dur}/{max_dur})"

    row1 = [
        InlineKeyboardButton(text=explore_text, callback_data="action_1"),
    ]
    is_stove = getattr(game, "is_stove", False)
    if is_stove:
        d = int(getattr(game, "campfire_durability", 0) or 0)
        row1.append(InlineKeyboardButton(text=f"🧱 Печь {d}/30", callback_data="menu_campfire"))
    elif getattr(game, "campfire_active", False) and getattr(game, "campfire_durability", 0) > 0:
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
    if is_stove or "Лощина" in str(getattr(game, "current_location", "")):
        kb_rows.append([
            InlineKeyboardButton(text="📜 Каменная плита", callback_data="tablet_notes_view")
        ])
    if "Яр Слизней" in str(getattr(game, "current_location", "")):
        if getattr(game, "slug_bait_active", False):
            kb_rows.append([
                InlineKeyboardButton(text="🍯 Приманка для слизней (Активна)", callback_data="l5_bait_menu")
            ])
        elif game.inventory.get("Приманка для слизней", 0) > 0:
            kb_rows.append([
                InlineKeyboardButton(text="🍯 Установить приманку", callback_data="use_item_Приманка для слизней")
            ])
    if game.weather in {"rain", "storm"}:
        rain_btns = [
            InlineKeyboardButton(text="🌧️ Пить дождь", callback_data="action_collect_water")
        ]
        has_empty_bottle = game.inventory.get("Пустая бутылка", 0) > 0
        has_partial_rain_bottle = any(w < 20 for w in getattr(game, "rain_bottles", []))
        if has_empty_bottle or has_partial_rain_bottle:
            rain_btns.append(
                InlineKeyboardButton(text="🧴 Набрать дождь (1 ⚡)", callback_data="action_fill_rain_bottle")
            )
        kb_rows.append(rain_btns)
    cur_loc = str(getattr(game, "current_location", ""))
    if "Святилище" in cur_loc:
        kb_rows.append([
            InlineKeyboardButton(text="✨ Прикоснуться к чаше", callback_data="sanctuary_resolve")
        ])
    elif "Мохнатая пещера" in cur_loc and not (hasattr(game, "is_story_flag_set") and game.is_story_flag_set("l6_completed")):
        kb_rows.append([
            InlineKeyboardButton(text="🦇 Исследовать пещеру", callback_data="furry_cave_start")
        ])
    if getattr(game, "locations_unlocked", False):
        kb_rows.append([
            InlineKeyboardButton(text="🗺️ Локации", callback_data="locations_menu")
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)



def get_campfire_kb(game=None):
    """Меню Костра/Печи (Рецепты, Подкинуть, Растопить и Назад)."""
    is_stove = getattr(game, "is_stove", False) if game else False
    dur = int(getattr(game, "campfire_durability", 0) or 0) if game else 1
    if is_stove and dur <= 0:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Растопить печь (2 ⚡ AP)", callback_data="stove_rekindle")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
        ])
    kb_rows = [
        [InlineKeyboardButton(text="📜 Рецепты", callback_data="campfire_recipes"),
         InlineKeyboardButton(text="🪵 Подкинуть", callback_data="campfire_add_fuel_menu")],
    ]
    # Прямая кнопка кипячения воды во фляге
    has_flask = (
        game
        and (game.equipment.get("flask") == "Армейская фляга" or game.inventory.get("Армейская фляга", 0) > 0)
    )
    has_rain_water = (
        game
        and (
            game.inventory.get("Бутылка дождевой воды", 0) > 0
            or any(w > 0 for w in getattr(game, "rain_bottles", []))
        )
    )
    flask_w = int(getattr(game, "flask_water", 0) or 0) if game else 0
    if has_flask and has_rain_water and flask_w < 20:
        kb_rows.append([
            InlineKeyboardButton(text=f"🔥 Вскипятить воду ({flask_w}/20)", callback_data="campfire_boil_water")
        ])
    kb_rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


def get_campfire_fuel_kb(game):
    """Подменю выбора топлива: Палки (+1), Кора (2 шт = +1) и Древесный уголь (+3)."""
    inv = getattr(game, "inventory", {}) or {}
    sticks = inv.get("Ветка", 0) + inv.get("Палки", 0) + inv.get("Палка", 0)
    bark = inv.get("Кусок коры", 0) + inv.get("Кора", 0)
    coal = inv.get("Древесный уголь", 0)

    keyboard = [
        [InlineKeyboardButton(text=f"🪵 Палки ({sticks})", callback_data="fuel_menu:sticks")],
        [InlineKeyboardButton(text=f"🧱 Кора ({bark})", callback_data="fuel_menu:bark")],
    ]
    if coal > 0 or getattr(game, "is_stove", False):
        keyboard.append([InlineKeyboardButton(text=f"⚫ Древесный уголь ({coal})", callback_data="fuel_menu:coal")])
    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_fuel_quantity_kb(fuel_type: str, game=None):
    """Выбор количества топлива для подкидывания в костёр/печь."""
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
    elif fuel_type == "coal":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⚫ Добавить 1 (+3 🔥)", callback_data="feed_fuel_action:coal:1"),
                InlineKeyboardButton(text="⚫ До максимума", callback_data="feed_fuel_action:coal:max"),
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
    keyboard = []
    unlocked = getattr(game, "unlocked_locations", []) or []

    def is_loc_unlocked(*keywords):
        if not unlocked:
            return False
        for loc in unlocked:
            loc_low = str(loc).lower()
            if any(kw.lower() in loc_low for kw in keywords):
                return True
        return False

    # 0. Забытый купол (В САМОМ ВЕРХУ, пока не получен лут)
    if game.is_story_flag_set("l1_dome_discovered") and not game.is_story_flag_set("l1_dome_completed"):
        keyboard.append([InlineKeyboardButton(text="🪂 Забытый купол", callback_data="l1_dome_enter")])

    # Волчье логово (если открыто и не побеждено)
    wolf_unlocked = getattr(game, "wolf_lair_unlocked", False) or getattr(game, "wolf_lair_active", False)
    wolf_defeated = getattr(game, "wolf_lair_defeated", False) or game.is_story_flag_set("wolf_lair_defeated")
    if wolf_unlocked and not wolf_defeated:
        has_staff = game.equipment.get("hand_right") == "Крепкий посох"
        btn_text = "🐾 Волчье логово" if has_staff else "🐾 Волчье логово (Опасно)"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data="wolf_lair_enter")])

    # 1. Стартовый лес
    if is_loc_unlocked("лес", "старт") or not unlocked:
        keyboard.append([InlineKeyboardButton(text="🌲 Стартовый лес", callback_data="location_enter_1")])
    # 2. Ручей со змеями
    if is_loc_unlocked("ручей"):
        keyboard.append([InlineKeyboardButton(text="🏞️ Ручей со змеями", callback_data="location_enter_2")])
    # 3. Скромная лощина
    if is_loc_unlocked("лощин"):
        keyboard.append([InlineKeyboardButton(text="⛰️ Скромная лощина", callback_data="location_enter_3")])
    # Босс: Солонец (Секач)
    if is_loc_unlocked("секач", "солонец") and not game.is_story_flag_set("l3_ridge_completed"):
        keyboard.append([InlineKeyboardButton(text="🐗 Солонец (Секач)", callback_data="location_enter_boar")])
    # 4. Просека охотников
    if is_loc_unlocked("просек", "охотник"):
        keyboard.append([InlineKeyboardButton(text="🏹 Просека охотников", callback_data="location_enter_4")])
    # 5. Яр слизней
    if is_loc_unlocked("яр", "слизн"):
        keyboard.append([InlineKeyboardButton(text="🐌 Яр слизней", callback_data="location_enter_5")])
    # 6. Мохнатая пещера
    if is_loc_unlocked("пещер", "мохнат"):
        keyboard.append([InlineKeyboardButton(text="🦇 Мохнатая пещера", callback_data="location_enter_6")])
    # 7. Святилище
    if is_loc_unlocked("святилищ"):
        keyboard.append([InlineKeyboardButton(text="🏛️ Святилище", callback_data="location_enter_7")])

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


def get_boar_battle_kb(is_stunned: bool = False, is_charging: bool = False):
    """Клавиатура боя с Секачом: Атаковать всегда, Уворот только при таране."""
    kb = []
    if is_charging:
        kb.append([
            InlineKeyboardButton(text="⚔️ Атаковать", callback_data="boar_battle_attack"),
            InlineKeyboardButton(text="⚡ Уворот", callback_data="boar_battle_dodge"),
        ])
    else:
        kb.append([
            InlineKeyboardButton(text="⚔️ Атаковать", callback_data="boar_battle_attack"),
        ])
    kb.append([InlineKeyboardButton(text="🏃 Сбежать", callback_data="boar_battle_flee")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_trap_buttons_kb(game):
    """Кнопки ловушек для каждой локации (1-7)."""
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    location_names = {
        1: "Стартовый лес",
        2: "Ручей со змеями",
        3: "Скромная лощина",
        4: "Просека охотников",
        5: "Яр слизней",
        6: "Мохнатая пещера",
        7: "Святилище",
    }
    traps = getattr(game, "traps", {}) or {}
    for loc_id in range(1, 8):
        loc_name = location_names.get(loc_id, f"Локация {loc_id}")
        if loc_id == 5:
            if getattr(game, "slug_bait_active", False):
                kb.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=f"🍯 {loc_name} (приманка активна)",
                        callback_data="l5_bait_menu"
                    )
                ])
            else:
                kb.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=f"🍯 {loc_name} (только приманка)",
                        callback_data="trap_place_5"
                    )
                ])
            continue
        trap = traps.get(loc_id)
        if trap and trap.get("is_active"):
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"✅ {loc_name} (взведена)",
                    callback_data=f"trap_status_{loc_id}"
                )
            ])
        elif trap and trap.get("is_broken"):
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"🔨 {loc_name} (сломана — заменить)",
                    callback_data=f"trap_replace_{loc_id}"
                )
            ])
        else:
            kb.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"🪤 {loc_name} (поставить)",
                    callback_data=f"trap_place_{loc_id}"
                )
            ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return kb


def get_l5_bait_menu_kb():
    """Меню управления приманкой в Яру Слизней."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Устроить засаду!", callback_data="l5_slug_ambush")],
        [InlineKeyboardButton(text="🚫 Снять приманку", callback_data="l5_bait_remove")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
    ])


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
    [InlineKeyboardButton(text="🕯️ Использовать факел", callback_data="wolf_torch")],
    [InlineKeyboardButton(text="🤫 Уйти тихо", callback_data="wolf_leave")]
])

peek_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👀 Заглянуть под пень", callback_data="l1_2")]
])

l1_2_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✋ Протянуть руку", callback_data="l1_2b")],
    [InlineKeyboardButton(text="🚫 Оставить его здесь", callback_data="l1_2a")]
])

l1_2b_1_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🤝 Забрать с собой", callback_data="l1_3")],
    [InlineKeyboardButton(text="🚫 Оставить здесь", callback_data="l1_2c")]
])

cat_kb = l1_2b_1_kb

next_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Выйти в лагерь", callback_data="story_next")]
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


def get_tablet_notes_kb(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для просмотра записей на каменной плите с пагинацией."""
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"tablet_page:{current_page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"tablet_page:{current_page + 1}"))

    kb = []
    if nav_row:
        kb.append(nav_row)
    kb.append([InlineKeyboardButton(text="✏️ Высечь свою надпись", callback_data="tablet_notes_edit")])
    kb.append([InlineKeyboardButton(text="↩️ В лагерь", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_tablet_edit_kb() -> InlineKeyboardMarkup:
    """Клавиатура при вводе надписи на плите."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Отмена", callback_data="tablet_notes_view")],
    ])

