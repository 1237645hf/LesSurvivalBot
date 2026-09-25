from typing import Optional, List, Tuple
from keyboards import inventory_inline_kb, get_main_kb
from modules.items import TINDER_ITEMS


# Рецепты крафта: имя -> список (предмет, кол-во)
CRAFT_RECIPES = {
    "Факел": [("Ветка", 2), ("Сушняк", 1)],
    "Костёр": [("Ветка", 5), ("Камень", 4), ("Сушняк", 1)],
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
    if name in ("Сушняк", "Трут"):
        return count_tinder(game) >= need
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
            if n in ("Сушняк", "Трут"):
                have = count_tinder(game)
                if have < q:
                    missing.append(f"Сушняк (мох/трава) {have}/{q}")
            else:
                have = game.inventory.get(n, 0)
                if have < q:
                    missing.append(f"{n} {have}/{q}")
        return False, "Не хватает: " + ", ".join(missing)

    # Списание ресурсов
    for n, q in ingredients:
        if n in ("Сушняк", "Трут"):
            tinder_name = get_available_tinder(game)
            if tinder_name:
                game.inventory[tinder_name] -= q
                if game.inventory[tinder_name] <= 0:
                    del game.inventory[tinder_name]
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
            if n in ("Сушняк", "Трут"):
                have = count_tinder(game)
                display_n = "Мох"
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
    if data in ("craft_Факел", "craft_Костёр"):
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
    return text, kb
