from keyboards import inventory_inline_kb, get_main_kb

# Рецепты крафта: имя -> список (предмет, кол-во)
CRAFT_RECIPES = {
    "Факел": [("Спички", 1), ("Ветка", 1)],
    "Костёр": [("Ветка", 5), ("Камень", 4), ("Мох", 1)],
}


def _count_ready(game, ingredients):
    """Сколько позиций ингредиентов полностью закрыто / всего."""
    ok = 0
    for name, need in ingredients:
        if game.inventory.get(name, 0) >= need:
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
    return all(game.inventory.get(n, 0) >= q for n, q in ingredients)


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
    """Скрафтить без AP. Возвращает (ok: bool, message: str)."""
    ingredients = CRAFT_RECIPES.get(recipe_name)
    if not ingredients:
        return False, "Неизвестный рецепт."
    if recipe_name == "Факел" and has_torch(game):
        return False, "У вас уже есть факел! Нельзя иметь больше одного факела одновременно."
    if not can_craft(game, recipe_name):
        missing = []
        for n, q in ingredients:
            have = game.inventory.get(n, 0)
            if have < q:
                missing.append(f"{n} {have}/{q}")
        return False, "Не хватает: " + ", ".join(missing)
    for n, q in ingredients:
        game.inventory[n] -= q
        if game.inventory[n] <= 0:
            del game.inventory[n]
    game.inventory[recipe_name] = game.inventory.get(recipe_name, 0) + 1
    if hasattr(game, "unlock_craft"):
        game.unlock_craft(recipe_name)
    game.add_log(f"Скрафчено: {recipe_name}.")
    return True, f"Успешно создано: {recipe_name}"


def handle_craft(data, game, uid):
    text = None
    kb = None
    if data in ("craft_Факел", "craft_Костёр"):
        recipe = data.removeprefix("craft_")
        ok, msg = do_craft(game, recipe)
        if not ok:
            game.add_log(msg)
        inv_text = game.get_inventory_text() if hasattr(game, "get_inventory_text") else ""
        text = f"{msg}\n\n{inv_text}" if inv_text else msg
        kb = inventory_inline_kb
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
