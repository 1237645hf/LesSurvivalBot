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


def can_craft(game, recipe_name: str) -> bool:
    ingredients = CRAFT_RECIPES.get(recipe_name, [])
    if not ingredients:
        return False
    return all(game.inventory.get(n, 0) >= q for n, q in ingredients)


def craft_mark(game, recipe_name: str) -> str:
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
            hand_field = "hand" if "hand" in game.equipment else "hands"
            if game.equipment.get(hand_field) is None:
                game.inventory["Факел"] -= 1
                if game.inventory["Факел"] <= 0:
                    del game.inventory["Факел"]
                game.equipment[hand_field] = "Факел"
                game.add_log("Вы экипировали факел в руку.")
                text = game.get_ui()
                kb = get_main_kb(game)
            else:
                game.add_log("У вас уже что-то в руке.")
                text = game.get_ui()
                kb = get_main_kb(game)
        else:
            game.add_log("Нельзя экипировать факел сейчас.")
            text = game.get_ui()
            kb = get_main_kb(game)
    return text, kb
