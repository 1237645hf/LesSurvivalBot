from typing import Optional, List, Tuple
from keyboards import inventory_inline_kb, get_main_kb
from modules.items import TINDER_ITEMS


# Рецепты крафта: имя -> список (предмет, кол-во)
CRAFT_RECIPES = {
    "Факел": [("Ветка", 2), ("Сушняк", 1)],
    "Костёр": [("Ветка", 5), ("Камень", 4), ("Сушняк", 1)],
    "Крепкий посох": [("Ветка", 8)],
    "Сланцевая маска": [("Сланцевая пластина", 2), ("Кусок коры", 2), ("Мох", 2)],
    "Сланцевый панцирь": [("Сланцевая пластина", 8), ("Кусок коры", 5), ("Мох", 4), ("Ветка", 4)],
    "Сланцевые поножи": [("Сланцевая пластина", 6), ("Кусок коры", 3), ("Мох", 4)],
    "Сланцевые ботинки": [("Сланцевая пластина", 2), ("Мох", 3), ("Кусок коры", 2)],
    "Древесный уголь": [("Ветка", 5), ("Кусок коры", 2)],
    "Сланцевый слиток": [("Сланец", 2), ("Глина", 2)],
    "Сланцевая тарелка": [("Сланцевый слиток", 1)],
    "Охотничья ловушка": [("Ветка", 4), ("Кусок коры", 2), ("Кожа", 1), ("Кость", 1)],
    "Окованный посох": [("Крепкий посох", 1), ("Сланцевый слиток", 1), ("Кусок коры", 2)],
    "Кожаный капюшон": [("Кожа", 2), ("Кусок коры", 1)],
    "Кожаный нагрудник": [("Кожа", 4), ("Сланцевый слиток", 1), ("Ветка", 2)],
    "Кожаные поножи": [("Кожа", 3), ("Кусок коры", 2)],
    "Кожаные сапоги": [("Кожа", 2), ("Кусок коры", 1)],
    "Зарядить фонарь": [("Старый фонарь", 1), ("Янтарное ядро", 2)],
    "Пузырёк": [("Сланцевый слиток", 1)],
    "Янтарное зелье": [("Пузырёк", 3), ("Янтарное ядро", 1), ("Болотная ягода", 1)],
    "Приманка для слизней": [("Ягода", 10)],
    "Охотничье сланцевое копьё": [
        ("Ветка", 15),
        ("Кожа", 2),
        ("Сланцевый слиток", 2),
        ("Светящийся гриб", 3),
    ],
}

CRAFT_YIELDS = {
    "Древесный уголь": 3,
    "Сланцевая тарелка": 2,
    "Пузырёк": 5,
    "Янтарное зелье": 3,
}


def get_available_tinder(game) -> Optional[str]:
    """Возвращает первый доступный предмет сушняка/растопки из инвентаря."""
    for name in TINDER_ITEMS:
        if game.inventory.get(name, 0) > 0:
            return name
    return None

get_available_sushnyak = get_available_tinder


def count_tinder(game) -> int:
    """Суммарное количество любого сушняка в инвентаре."""
    return sum(game.inventory.get(name, 0) for name in TINDER_ITEMS)

count_sushnyak = count_tinder


def _check_ingredient(game, name: str, need: int) -> bool:
    if name in ("Сушняк", "Трут", "Мох"):
        return count_tinder(game) >= need
    if name in ("Кусок коры", "Кора"):
        return (game.inventory.get("Кусок коры", 0) + game.inventory.get("Кора", 0)) >= need
    if name in ("Ветка", "Палка", "Палки"):
        return (game.inventory.get("Ветка", 0) + game.inventory.get("Палка", 0) + game.inventory.get("Палки", 0)) >= need
    if name in ("Сланец", "Сланцевая пластина"):
        return (game.inventory.get("Сланец", 0) + game.inventory.get("Сланцевая пластина", 0)) >= need
    if name in ("Болотная ягода", "Ягода"):
        if game.inventory.get(name, 0) >= need:
            return True
        total_berries = sum(game.inventory.get(b, 0) for b in ("Лесная ягода", "Красная ягода", "Фиолетовая ягода", "Болотная ягода", "Горная ягода", "Ягода"))
        return total_berries >= need
    if name == "Старый фонарь":
        return game.inventory.get("Старый фонарь", 0) >= need or game.equipment.get("hand_left") == "Старый фонарь"
    return game.inventory.get(name, 0) >= need


def _count_ready(game, ingredients) -> Tuple[int, int]:
    """Сколько позиций ингредиентов закрыто / всего."""
    ok = 0
    for name, need in ingredients:
        if _check_ingredient(game, name, need):
            ok += 1
    return ok, len(ingredients)


def has_torch(game) -> bool:
    """Проверка, есть ли уже факел у персонажа (в инвентаре или в руках)."""
    return (
        game.inventory.get("Факел", 0) > 0
        or game.equipment.get("hand_left") == "Факел"
        or game.equipment.get("hand_right") == "Факел"
    )


def has_campfire(game) -> bool:
    """Проверка, есть ли уже скрафченный костёр в инвентаре или горит на стоянке."""
    return (
        game.inventory.get("Костёр", 0) > 0
        or bool(getattr(game, "campfire_active", False))
    )


def can_craft(game, recipe_name: str) -> bool:
    ingredients = CRAFT_RECIPES.get(recipe_name, [])
    if not ingredients:
        return False
    if recipe_name == "Факел" and has_torch(game):
        return False
    if recipe_name == "Костёр" and has_campfire(game):
        return False
    if recipe_name == "Приманка для слизней":
        if getattr(game, "current_location", None) != "Яр Слизней":
            return False
    if recipe_name in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё"):
        has_spear = (
            game.inventory.get("Охотничье сланцевое копьё", 0) > 0
            or game.inventory.get("🔱 Охотничье сланцевое копьё", 0) > 0
            or game.equipment.get("hand_right") in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё")
        )
        if has_spear:
            return False
        if not (game.is_story_flag_set("l5_boss_defeated") or game.is_story_flag_set("boss_giant_slime_defeated")):
            return False
    if recipe_name == "Зарядить фонарь":
        has_lantern = (
            game.equipment.get("hand_left") == "Старый фонарь"
            or game.inventory.get("Старый фонарь", 0) > 0
        )
        has_cores = game.inventory.get("Янтарное ядро", 0) >= 2
        not_full = int(getattr(game, "lantern_durability", 20) or 0) < 20
        return has_lantern and has_cores and not_full
    return all(_check_ingredient(game, n, q) for n, q in ingredients)


def craft_mark(game, recipe_name: str) -> str:
    if recipe_name == "Факел" and has_torch(game):
        return "❌ (уже есть)"
    if recipe_name == "Костёр" and has_campfire(game):
        return "❌ (уже есть)"
    if recipe_name == "Приманка для слизней" and getattr(game, "current_location", None) != "Яр Слизней":
        return "❌ (только в Яру Слизней)"
    if recipe_name in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё"):
        has_spear = (
            game.inventory.get("Охотничье сланцевое копьё", 0) > 0
            or game.inventory.get("🔱 Охотничье сланцевое копьё", 0) > 0
            or game.equipment.get("hand_right") in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё")
        )
        if has_spear:
            return "❌ (уже есть)"
        if not (game.is_story_flag_set("l5_boss_defeated") or game.is_story_flag_set("boss_giant_slime_defeated")):
            return "❌ (заблокировано)"
    if recipe_name == "Зарядить фонарь":
        has_lantern = (
            game.equipment.get("hand_left") == "Старый фонарь"
            or game.inventory.get("Старый фонарь", 0) > 0
        )
        if not has_lantern:
            return "❌ (нет фонаря)"
        if int(getattr(game, "lantern_durability", 20) or 0) >= 20:
            return "❌ (уже заряжен)"
    ingredients = CRAFT_RECIPES.get(recipe_name, [])
    ok, total = _count_ready(game, ingredients)
    if total == 0:
        return ""
    if ok == total:
        return f"✅ {ok}/{total}"
    return f"❌ {ok}/{total}"


def do_craft(game, recipe_name: str):
    """Скрафтить предмет. Учитывает зажигание факела (от костра, спичками или искрами)."""
    ingredients = CRAFT_RECIPES.get(recipe_name)
    if not ingredients:
        return False, "Неизвестный рецепт."
    if recipe_name == "Факел" and has_torch(game):
        return False, "У вас уже есть факел! Нельзя иметь больше одного факела одновременно."
    if recipe_name == "Костёр" and has_campfire(game):
        return False, "У вас уже есть костёр! Нельзя создать второй."
    if recipe_name == "Зарядить фонарь":
        has_lantern = (
            game.equipment.get("hand_left") == "Старый фонарь"
            or game.inventory.get("Старый фонарь", 0) > 0
        )
        if not has_lantern:
            return False, "У вас нет старого фонаря для зарядки!"
        if game.inventory.get("Янтарное ядро", 0) < 2:
            return False, "Не хватает янтарных ядер (нужно 2 шт.)!"
        if int(getattr(game, "lantern_durability", 20) or 0) >= 20:
            return False, "Фонарь уже полностью заправлен (20/20)!"
        game.inventory["Янтарное ядро"] -= 2
        if game.inventory["Янтарное ядро"] <= 0:
            del game.inventory["Янтарное ядро"]
        game.lantern_durability = 20
        game.add_log("Вы заправили старый фонарь чистым янтарным маслом (20/20 исследований).")
        return True, "Старый фонарь успешно заправлен янтарным маслом (20/20)!"
    if recipe_name == "Приманка для слизней":
        if getattr(game, "current_location", None) != "Яр Слизней":
            return False, "Приманку для слизней можно изготовить только находясь в Яру Слизней!"
    if recipe_name in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё"):
        has_spear = (
            game.inventory.get("Охотничье сланцевое копьё", 0) > 0
            or game.inventory.get("🔱 Охотничье сланцевое копьё", 0) > 0
            or game.equipment.get("hand_right") in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё")
        )
        if has_spear:
            return False, "У вас уже есть охотничье сланцевое копьё! Нельзя создать второе."
        if not (game.is_story_flag_set("l5_boss_defeated") or game.is_story_flag_set("boss_giant_slime_defeated")):
            return False, "Рецепт заблокирован! Победите Исполинского слайма."
    if not can_craft(game, recipe_name):
        missing = []
        for n, q in ingredients:
            if n in ("Сушняк", "Трут", "Мох"):
                have = count_tinder(game)
                if have < q:
                    missing.append(f"Мох/сушняк {have}/{q}")
            elif n in ("Кусок коры", "Кора"):
                have = game.inventory.get("Кусок коры", 0) + game.inventory.get("Кора", 0)
                if have < q:
                    missing.append(f"Кора {have}/{q}")
            elif n in ("Ветка", "Палка", "Палки"):
                have = game.inventory.get("Ветка", 0) + game.inventory.get("Палка", 0) + game.inventory.get("Палки", 0)
                if have < q:
                    missing.append(f"Ветки {have}/{q}")
            elif n in ("Болотная ягода", "Ягода"):
                have = sum(game.inventory.get(b, 0) for b in ("Лесная ягода", "Красная ягода", "Фиолетовая ягода", "Болотная ягода", "Горная ягода", "Ягода"))
                if have < q:
                    missing.append(f"Ягоды {have}/{q}")
            else:
                have = game.inventory.get(n, 0)
                if have < q:
                    missing.append(f"{n} {have}/{q}")
        return False, "Не хватает: " + ", ".join(missing)

    # Списание ресурсов
    for n, q in ingredients:
        rem = q
        if n in ("Сушняк", "Трут", "Мох"):
            for t_name in TINDER_ITEMS:
                if rem <= 0:
                    break
                have = game.inventory.get(t_name, 0)
                if have > 0:
                    take = min(have, rem)
                    game.inventory[t_name] -= take
                    rem -= take
                    if game.inventory[t_name] <= 0:
                        del game.inventory[t_name]
        elif n in ("Кусок коры", "Кора"):
            for b_name in ("Кусок коры", "Кора"):
                if rem <= 0:
                    break
                have = game.inventory.get(b_name, 0)
                if have > 0:
                    take = min(have, rem)
                    game.inventory[b_name] -= take
                    rem -= take
                    if game.inventory[b_name] <= 0:
                        del game.inventory[b_name]
        elif n in ("Ветка", "Палка", "Палки"):
            for s_name in ("Ветка", "Палка", "Палки"):
                if rem <= 0:
                    break
                have = game.inventory.get(s_name, 0)
                if have > 0:
                    take = min(have, rem)
                    game.inventory[s_name] -= take
                    rem -= take
                    if game.inventory[s_name] <= 0:
                        del game.inventory[s_name]
        elif n in ("Сланец", "Сланцевая пластина"):
            for sl_name in ("Сланец", "Сланцевая пластина"):
                if rem <= 0:
                    break
                have = game.inventory.get(sl_name, 0)
                if have > 0:
                    take = min(have, rem)
                    game.inventory[sl_name] -= take
                    rem -= take
                    if game.inventory[sl_name] <= 0:
                        del game.inventory[sl_name]
        elif n in ("Болотная ягода", "Ягода"):
            for b_name in ("Болотная ягода", "Лесная ягода", "Красная ягода", "Фиолетовая ягода", "Горная ягода", "Ягода"):
                if rem <= 0:
                    break
                have = game.inventory.get(b_name, 0)
                if have > 0:
                    take = min(have, rem)
                    game.inventory[b_name] -= take
                    rem -= take
                    if game.inventory[b_name] <= 0:
                        del game.inventory[b_name]
        else:
            game.inventory[n] -= q
            if game.inventory[n] <= 0:
                del game.inventory[n]

    # Добавление скрафченного предмета
    yield_qty = CRAFT_YIELDS.get(recipe_name, 1)
    game.inventory[recipe_name] = game.inventory.get(recipe_name, 0) + yield_qty
    if hasattr(game, "unlock_craft"):
        game.unlock_craft(recipe_name)
    if recipe_name in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё"):
        game.set_story_flag("crafted_hunting_spear", True)

    # Особая логика зажигания факела при создании
    if recipe_name == "Факел":
        if getattr(game, "campfire_active", False) and getattr(game, "campfire_durability", 0) > 0:
            extra_msg = " Огонь взят от углей костра без траты спичек и сил."
        elif game.inventory.get("Спички", 0) > 0:
            game.inventory["Спички"] -= 1
            if game.inventory["Спички"] <= 0:
                del game.inventory["Спички"]
            extra_msg = " Зажжён спичкой (−1 спичка, 0 ⚡ AP)."
        else:
            game.ap = max(0, game.ap - 1)
            extra_msg = " С трудом зажжён искрами трения (−1 ⚡ AP)."
        game.add_log(f"Скрафчен факел.{extra_msg}")
        return True, f"Успешно создан Факел!{extra_msg}"

    game.add_log(f"Скрафчено: {recipe_name}.")
    return True, f"Успешно создано: {recipe_name}"


CRAFT_ICONS = {
    "Факел": "🔦",
    "Костёр": "🔥",
    "Крепкий посох": "🪵",
    "Сланцевая маска": "🎭",
    "Сланцевый панцирь": "🦺",
    "Сланцевые поножи": "👖",
    "Сланцевые ботинки": "🥾",
    "Древесный уголь": "⚫",
    "Сланцевый слиток": "🧱",
    "Сланцевая тарелка": "🍽️",
    "Охотничья ловушка": "🪤",
    "Приманка для слизней": "🍯",
    "Окованный посох": "🦯",
    "Охотничье сланцевое копьё": "🔱",
    "🔱 Охотничье сланцевое копьё": "🔱",
    "Кожаный капюшон": "🧢",
    "Кожаный нагрудник": "🦺",
    "Кожаные поножи": "👖",
    "Кожаные сапоги": "🥾",
    "Зарядить фонарь": "🔦",
    "Пузырёк": "🧪",
    "Янтарное зелье": "🍹",
}


def get_craft_menu_text(game) -> str:
    """Формирует текст экрана крафта: показывает сколько есть / сколько надо для каждого ингредиента."""
    unlocked = list(getattr(game, "unlocked_crafts", ["Костёр", "Факел"]) or ["Костёр", "Факел"])
    has_spear = (
        game.inventory.get("Охотничье сланцевое копьё", 0) > 0
        or game.inventory.get("🔱 Охотничье сланцевое копьё", 0) > 0
        or game.equipment.get("hand_right") in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё")
    )
    if (game.is_story_flag_set("l5_boss_defeated") or game.is_story_flag_set("boss_giant_slime_defeated")) and not has_spear and "Охотничье сланцевое копьё" not in unlocked:
        unlocked.append("Охотничье сланцевое копьё")
    lines = ["🔨 Крафт (только открытые рецепты):", ""]
    has_any = False
    for name in unlocked:
        if name not in CRAFT_RECIPES:
            continue
        if name == "Факел" and has_torch(game):
            continue
        if name == "Костёр" and has_campfire(game):
            continue
        if name in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё") and has_spear:
            continue
        if name == "Зарядить фонарь":
            has_lantern = (
                game.equipment.get("hand_left") == "Старый фонарь"
                or game.inventory.get("Старый фонарь", 0) > 0
            )
            if not has_lantern:
                continue
        has_any = True
        icon = CRAFT_ICONS.get(name, "📦")
        ingredients = CRAFT_RECIPES[name]
        ing_strs = []
        for n, q in ingredients:
            if n in ("Сушняк", "Трут", "Мох"):
                have = count_tinder(game)
                display_n = "Мох"
            elif n in ("Кусок коры", "Кора"):
                have = game.inventory.get("Кусок коры", 0) + game.inventory.get("Кора", 0)
                display_n = "Кусок коры"
            elif n in ("Ветка", "Палка", "Палки"):
                have = game.inventory.get("Ветка", 0) + game.inventory.get("Палка", 0) + game.inventory.get("Палки", 0)
                display_n = "Ветка"
            else:
                have = game.inventory.get(n, 0)
                display_n = n
            ing_strs.append(f"{display_n} ({have}/{q})")
        lines.append(f"• {icon} {name}: {', '.join(ing_strs)}")
    if not has_any:
        lines.append("Пока нечего крафтить.")
    body = "\n".join(lines)
    return f"━━━━━━━━━━━━━━━━━━━\n{body}\n━━━━━━━━━━━━━━━━━━━"


def get_craft_menu_kb(game):
    """Клавиатура крафта: иконка предмета + короткое название + статус ✅/❌ n/m."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    unlocked = list(getattr(game, "unlocked_crafts", ["Костёр", "Факел"]) or ["Костёр", "Факел"])
    has_spear = (
        game.inventory.get("Охотничье сланцевое копьё", 0) > 0
        or game.inventory.get("🔱 Охотничье сланцевое копьё", 0) > 0
        or game.equipment.get("hand_right") in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё")
    )
    if (game.is_story_flag_set("l5_boss_defeated") or game.is_story_flag_set("boss_giant_slime_defeated")) and not has_spear and "Охотничье сланцевое копьё" not in unlocked:
        unlocked.append("Охотничье сланцевое копьё")
    keyboard = []
    for name in unlocked:
        if name not in CRAFT_RECIPES:
            continue
        if name == "Факел" and has_torch(game):
            continue
        if name == "Костёр" and has_campfire(game):
            continue
        if name in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё") and has_spear:
            continue
        if name == "Зарядить фонарь":
            has_lantern = (
                game.equipment.get("hand_left") == "Старый фонарь"
                or game.inventory.get("Старый фонарь", 0) > 0
            )
            if not has_lantern:
                continue
        icon = CRAFT_ICONS.get(name, "📦")
        mark = craft_mark(game, name)
        keyboard.append([
            InlineKeyboardButton(text=f"{icon} {name} {mark}", callback_data=f"craft_{name}")
        ])
    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def is_craft_callback(data: str) -> bool:
    """Проверяет, относится ли callback к меню крафта, рецептам или использованию экипируемых предметов."""
    return data in ("inv_craft", "inv_recipes") or data.startswith("craft_") or data.startswith("confirm_craft_") or data.startswith("use_item_")


def handle_craft(data, game, uid):
    text = None
    kb = None
    if data == "inv_craft":
        game.push_screen("craft")
        text = get_craft_menu_text(game)
        kb = get_craft_menu_kb(game)
        return text, kb
    elif data == "inv_recipes":
        game.push_screen("recipes")
        text = get_craft_menu_text(game)
        kb = get_craft_menu_kb(game)
        return text, kb
    elif data == "craft_Крепкий посох":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        branches = game.inventory.get("Ветка", 0) + game.inventory.get("Палка", 0) + game.inventory.get("Палки", 0)
        req_icon = "✅" if branches >= 8 else "❌"
        text = (
            "━━━━━━━━━━━━━━━━━━━\n"
            "🦯 Крепкий посох\n\n"
            "Обтёсанная тяжёлая ветвь — надёжное оружие против лесных хищников.\n\n"
            f"📦 Требования: {req_icon} Ветка ({branches}/8)\n"
            "⚔️ Свойства: Урон в бою: 4–6 ед. (Правая рука)\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        buttons = []
        if branches >= 8:
            buttons.append([InlineKeyboardButton(text="🔨 Скрафтить", callback_data="confirm_craft_Крепкий посох")])
    elif data in ("craft_Охотничье сланцевое копьё", "craft_🔱 Охотничье сланцевое копьё"):
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        sticks = game.inventory.get("Ветка", 0) + game.inventory.get("Палка", 0) + game.inventory.get("Палки", 0)
        leather = game.inventory.get("Кожа", 0)
        bars = game.inventory.get("Сланцевый слиток", 0)
        mushrooms = game.inventory.get("Светящийся гриб", 0)

        can_make = sticks >= 15 and leather >= 2 and bars >= 2 and mushrooms >= 3
        req_sticks = "✅" if sticks >= 15 else "❌"
        req_leather = "✅" if leather >= 2 else "❌"
        req_bars = "✅" if bars >= 2 else "❌"
        req_mushrooms = "✅" if mushrooms >= 3 else "❌"

        text = (
            "━━━━━━━━━━━━━━━━━━━\n"
            "🔱 Охотничье сланцевое копьё\n\n"
            "Длинное копьё с клиновидным наконечником из сланца, вымоченным в соке светящихся грибов. "
            "Дробящие удары вязли в желе, но узкое тяжёлое остриё легко достанет ядро сквозь любую толщу, "
            "а кожаная обмотка не даст древку выскользнуть из мокрых рук.\n\n"
            f"📦 Требования:\n"
            f"• {req_sticks} Ветка ({sticks}/15)\n"
            f"• {req_leather} Кожа ({leather}/2)\n"
            f"• {req_bars} Сланцевый слиток ({bars}/2)\n"
            f"• {req_mushrooms} Светящийся гриб ({mushrooms}/3)\n\n"
            "⚔️ Свойства: Урон в бою: 19–24 ед. (Правая рука)\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        buttons = []
        if can_make:
            buttons.append([InlineKeyboardButton(text="🔨 Скрафтить", callback_data="confirm_craft_Охотничье сланцевое копьё")])
        buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
        return text, InlineKeyboardMarkup(inline_keyboard=buttons)
    elif data.startswith("confirm_craft_") or data.startswith("craft_"):
        recipe = data.removeprefix("confirm_craft_").removeprefix("craft_")
        ok, msg = do_craft(game, recipe)
        if ok:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            text = f"🔨 {msg}\n\nПредмет успешно добавлен в инвентарь."
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ В инвентарь", callback_data="back")]
            ])
        else:
            game.add_log(msg)
            text = f"❌ {msg}\n\n{get_craft_menu_text(game)}"
            kb = get_craft_menu_kb(game)
    elif data == "use_item_Факел":
        if game.inventory.get("Факел", 0) > 0:
            # Факел помещается ТОЛЬКО в левую руку
            if game.equipment.get("hand_left") is None:
                game.inventory["Факел"] -= 1
                if game.inventory["Факел"] <= 0:
                    del game.inventory["Факел"]
                game.equipment["hand_left"] = "Факел"
                game.ap += 1
                text = game.get_ui()
                kb = get_main_kb(game)
            else:
                game.add_log("Левая рука занята! Сначала освободите её (в правую руку факел брать нельзя).")
                text = game.get_ui()
                kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет факела.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Крепкий посох":
        if game.inventory.get("Крепкий посох", 0) > 0:
            old_item = game.equipment.get("hand_right")
            if old_item:
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Крепкий посох"] -= 1
            if game.inventory["Крепкий посох"] <= 0:
                del game.inventory["Крепкий посох"]
            game.equipment["hand_right"] = "Крепкий посох"
            game.add_log("Вы взяли крепкий посох в правую руку (⚔️ Урон 4–6).")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет крепкого посоха.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data in ("use_item_Охотничье сланцевое копьё", "use_item_🔱 Охотничье сланцевое копьё"):
        item_key = "Охотничье сланцевое копьё"
        if game.inventory.get(item_key, 0) <= 0 and game.inventory.get("🔱 Охотничье сланцевое копьё", 0) > 0:
            item_key = "🔱 Охотничье сланцевое копьё"
        if game.inventory.get(item_key, 0) > 0:
            old_item = game.equipment.get("hand_right")
            if old_item:
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory[item_key] -= 1
            if game.inventory[item_key] <= 0:
                del game.inventory[item_key]
            game.equipment["hand_right"] = "Охотничье сланцевое копьё"
            game.add_log("Вы взяли охотничье сланцевое копьё в правую руку (⚔️ Урон 19–24).")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет охотничьего сланцевого копья.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Рюкзак с красной заплаткой":
        if game.inventory.get("Рюкзак с красной заплаткой", 0) > 0:
            old_item = game.equipment.get("back")
            if old_item:
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Рюкзак с красной заплаткой"] -= 1
            if game.inventory["Рюкзак с красной заплаткой"] <= 0:
                del game.inventory["Рюкзак с красной заплаткой"]
            game.equipment["back"] = "Рюкзак с красной заплаткой"
            game.add_log("Вы надели рюкзак с красной заплаткой на спину.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет рюкзака с красной заплаткой.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Сланцевая маска":
        if game.inventory.get("Сланцевая маска", 0) > 0:
            old_item = game.equipment.get("head")
            if old_item and old_item not in ("⚪ Грязная кепка", "Грязная кепка", "Пусто"):
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Сланцевая маска"] -= 1
            if game.inventory["Сланцевая маска"] <= 0:
                del game.inventory["Сланцевая маска"]
            game.equipment["head"] = "Сланцевая маска"
            game.add_log("Вы надели сланцевую маску.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет сланцевой маски.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Сланцевый панцирь":
        if game.inventory.get("Сланцевый панцирь", 0) > 0:
            old_item = game.equipment.get("torso")
            if old_item and old_item not in ("⚪ Потасканная куртка", "Потасканная куртка", "Пусто"):
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Сланцевый панцирь"] -= 1
            if game.inventory["Сланцевый панцирь"] <= 0:
                del game.inventory["Сланцевый панцирь"]
            game.equipment["torso"] = "Сланцевый панцирь"
            game.add_log("Вы надели сланцевый панцирь.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет сланцевого панциря.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Сланцевые поножи":
        if game.inventory.get("Сланцевые поножи", 0) > 0:
            old_item = game.equipment.get("pants")
            if old_item and old_item not in ("⚪ Рваные штаны", "Рваные штаны", "Пусто"):
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Сланцевые поножи"] -= 1
            if game.inventory["Сланцевые поножи"] <= 0:
                del game.inventory["Сланцевые поножи"]
            game.equipment["pants"] = "Сланцевые поножи"
            game.add_log("Вы надели сланцевые поножи.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет сланцевых поножей.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Сланцевые ботинки":
        if game.inventory.get("Сланцевые ботинки", 0) > 0:
            old_item = game.equipment.get("boots")
            if old_item and old_item not in ("⚪ Стоптанные ботинки", "Стоптанные ботинки", "Пусто"):
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Сланцевые ботинки"] -= 1
            if game.inventory["Сланцевые ботинки"] <= 0:
                del game.inventory["Сланцевые ботинки"]
            game.equipment["boots"] = "Сланцевые ботинки"
            game.add_log("Вы надели сланцевые ботинки.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет сланцевых ботинок.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Отремонтированные ботинки":
        if game.inventory.get("Отремонтированные ботинки", 0) > 0:
            old_item = game.equipment.get("boots")
            if old_item and old_item not in ("⚪ Стоптанные ботинки", "Стоптанные ботинки", "Пусто"):
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Отремонтированные ботинки"] -= 1
            if game.inventory["Отремонтированные ботинки"] <= 0:
                del game.inventory["Отремонтированные ботинки"]
            game.equipment["boots"] = "Отремонтированные ботинки"
            game.add_log("Вы надели отремонтированные ботинки.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет отремонтированных ботинок.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Охотничья ловушка":
        from keyboards import get_trap_buttons_kb
        if game.inventory.get("Охотничья ловушка", 0) > 0:
            if hasattr(game, "push_screen"):
                game.push_screen("traps")
            text = (
                "🪤 <b>Установка охотничьей ловушки</b>\n\n"
                "Выбери локацию, где хочешь взвести ловушку на ночь.\n"
                "Утром после сна проверяй результат (добыча или поломка).\n"
                "<i>На каждой локации может стоять только одна ловушка.</i>"
            )
            kb = get_trap_buttons_kb(game)
        else:
            game.add_log("В инвентаре нет готовой охотничьей ловушки.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Окованный посох":
        if game.inventory.get("Окованный посох", 0) > 0:
            old_item = game.equipment.get("hand_right")
            if old_item:
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Окованный посох"] -= 1
            if game.inventory["Окованный посох"] <= 0:
                del game.inventory["Окованный посох"]
            game.equipment["hand_right"] = "Окованный посох"
            game.add_log("Вы взяли окованный посох в правую руку (⚔️ Урон 8–10).")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет окованного посоха.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Клык волка":
        if game.inventory.get("Клык волка", 0) > 0:
            old_item = game.equipment.get("trinket")
            if old_item:
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Клык волка"] -= 1
            if game.inventory["Клык волка"] <= 0:
                del game.inventory["Клык волка"]
            game.equipment["trinket"] = "Клык волка"
            game.add_log("Вы надели амулет «Клык волка» (+1 к урону в бою).")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет клыка волка.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Схема кожаной брони":
        if game.inventory.get("Схема кожаной брони", 0) > 0:
            game.inventory["Схема кожаной брони"] -= 1
            if game.inventory["Схема кожаной брони"] <= 0:
                del game.inventory["Схема кожаной брони"]
            unlocked = list(getattr(game, "unlocked_crafts", ["Костёр", "Факел"]) or ["Костёр", "Факел"])
            for arm in ("Кожаный капюшон", "Кожаный нагрудник", "Кожаные поножи", "Кожаные сапоги"):
                if arm not in unlocked:
                    unlocked.append(arm)
            game.unlocked_crafts = unlocked
            game.set_story_flag("leather_armor_unlocked", True)
            game.add_log("Открыт крафт кожаной брони.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет схемы кожаной брони.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Кожаный капюшон":
        if game.inventory.get("Кожаный капюшон", 0) > 0:
            old_item = game.equipment.get("head")
            if old_item and old_item not in ("⚪ Грязная кепка", "Грязная кепка", "Пусто"):
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Кожаный капюшон"] -= 1
            if game.inventory["Кожаный капюшон"] <= 0:
                del game.inventory["Кожаный капюшон"]
            game.equipment["head"] = "Кожаный капюшон"
            game.add_log("Вы надели кожаный капюшон.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет кожаного капюшона.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Кожаный нагрудник":
        if game.inventory.get("Кожаный нагрудник", 0) > 0:
            old_item = game.equipment.get("torso")
            if old_item and old_item not in ("⚪ Потасканная куртка", "Потасканная куртка", "Пусто"):
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Кожаный нагрудник"] -= 1
            if game.inventory["Кожаный нагрудник"] <= 0:
                del game.inventory["Кожаный нагрудник"]
            game.equipment["torso"] = "Кожаный нагрудник"
            game.add_log("Вы надели кожаный нагрудник.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет кожаного нагрудника.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Кожаные поножи":
        if game.inventory.get("Кожаные поножи", 0) > 0:
            old_item = game.equipment.get("pants")
            if old_item and old_item not in ("⚪ Рваные штаны", "Рваные штаны", "Пусто"):
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Кожаные поножи"] -= 1
            if game.inventory["Кожаные поножи"] <= 0:
                del game.inventory["Кожаные поножи"]
            game.equipment["pants"] = "Кожаные поножи"
            game.add_log("Вы надели кожаные поножи.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет кожаных поножей.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Кожаные сапоги":
        if game.inventory.get("Кожаные сапоги", 0) > 0:
            old_item = game.equipment.get("boots")
            if old_item and old_item not in ("⚪ Стоптанные ботинки", "Стоптанные ботинки", "Пусто"):
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Кожаные сапоги"] -= 1
            if game.inventory["Кожаные сапоги"] <= 0:
                del game.inventory["Кожаные сапоги"]
            game.equipment["boots"] = "Кожаные сапоги"
            game.add_log("Вы надели кожаные сапоги.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет кожаных сапог.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Костяной амулет охотника":
        if game.inventory.get("Костяной амулет охотника", 0) > 0:
            old_item = game.equipment.get("trinket")
            if old_item:
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Костяной амулет охотника"] -= 1
            if game.inventory["Костяной амулет охотника"] <= 0:
                del game.inventory["Костяной амулет охотника"]
            game.equipment["trinket"] = "Костяной амулет охотника"
            game.add_log("Вы надели костяной амулет охотника (+5 к увороту, чуткое чутьё при исследовании).")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет костяного амулета охотника.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Старый фонарь":
        if game.inventory.get("Старый фонарь", 0) > 0:
            old_item = game.equipment.get("hand_left")
            if old_item:
                game.inventory[old_item] = game.inventory.get(old_item, 0) + 1
            game.inventory["Старый фонарь"] -= 1
            if game.inventory["Старый фонарь"] <= 0:
                del game.inventory["Старый фонарь"]
            game.equipment["hand_left"] = "Старый фонарь"
            dur = int(getattr(game, "lantern_durability", 20) or 0)
            max_dur = int(getattr(game, "lantern_max_durability", 20) or 20)
            game.add_log(f"Вы взяли старый фонарь в левую руку [🔦 {dur}/{max_dur}] (+2 ⚡ AP пока фонарь в руке).")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("В инвентаре нет старого фонаря.")
            text = game.get_ui()
            kb = get_main_kb(game)
    elif data == "use_item_Приманка для слизней":
        if game.inventory.get("Приманка для слизней", 0) <= 0:
            game.add_log("В инвентаре нет приманки для слизней.")
            text = game.get_ui()
            kb = get_main_kb(game)
        elif getattr(game, "current_location", None) != "Яр Слизней":
            game.add_log("Приманку для слизней можно установить только в Яру Слизней.")
            text = game.get_ui()
            kb = get_main_kb(game)
        elif getattr(game, "slug_bait_active", False):
            game.add_log("В Яру Слизней уже установлена активная приманка.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.inventory["Приманка для слизней"] -= 1
            if game.inventory["Приманка для слизней"] <= 0:
                del game.inventory["Приманка для слизней"]
            game.slug_bait_active = True
            game.add_log("Вы установили приманку для слизней в Яру Слизней. Сладкий ягодный дух растекается по лощине.")
            text = game.get_ui()
    if text is None:
        from keyboards import inventory_inline_kb
        text = game.get_inventory_text()
        kb = inventory_inline_kb
    return text, kb
