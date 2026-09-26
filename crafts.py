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
        or game.equipment.get("hand") == "Факел"
    )


def can_craft(game, recipe_name: str) -> bool:
    ingredients = CRAFT_RECIPES.get(recipe_name, [])
    if not ingredients:
        return False
    if recipe_name == "Факел" and has_torch(game):
        return False
    return all(_check_ingredient(game, n, q) for n, q in ingredients)


def craft_mark(game, recipe_name: str) -> str:
    if recipe_name == "Факел" and has_torch(game):
        return "❌ (уже есть)"
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
        else:
            game.inventory[n] -= q
            if game.inventory[n] <= 0:
                del game.inventory[n]

    # Добавление скрафченного предмета
    game.inventory[recipe_name] = game.inventory.get(recipe_name, 0) + 1
    if hasattr(game, "unlock_craft"):
        game.unlock_craft(recipe_name)

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
}


def get_craft_menu_text(game) -> str:
    """Формирует текст экрана крафта: показывает сколько есть / сколько надо для каждого ингредиента."""
    unlocked = list(getattr(game, "unlocked_crafts", ["Костёр", "Факел"]) or ["Костёр", "Факел"])
    lines = ["🔨 Крафт (только открытые рецепты):", ""]
    has_any = False
    for name in unlocked:
        if name not in CRAFT_RECIPES:
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
    keyboard = []
    for name in unlocked:
        if name not in CRAFT_RECIPES:
            continue
        icon = CRAFT_ICONS.get(name, "📦")
        mark = craft_mark(game, name)
        keyboard.append([
            InlineKeyboardButton(text=f"{icon} {name} {mark}", callback_data=f"craft_{name}")
        ])
    keyboard.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def handle_craft(data, game, uid):
    text = None
    kb = None
    if data.startswith("craft_"):
        recipe = data.removeprefix("craft_")
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
                game.equipment["hand"] = "Факел"
                game.ap += 1
                game.add_log("Вы взяли факел в левую руку (+1 ⚡ AP пока факел в руке). Счётчик исследований активирован.")
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
    return text, kb
