"""
modules/cooking.py — Единая система готовки на костре по рангам качества.

Рецепты:
⚪ Обычный ранг:
  - Печёные ягоды (ягоды×5 + кора, вода 0)
  - Жареные грибы (грибы×5 + кора, вода 0)
🟢 Необычный ранг:
  - Ягодный отвар (ягоды×5 + кора + вода 1)
  - Грибная похлёбка (грибы×5 + кора + вода 2)
🔵 Редкий ранг:
  - Мясо на коре (сырое мясо×1 + кора, вода 0)
🟣 Эпический ранг:
  - Охотничья похлёбка (сырое мясо×1 + ягоды×5 + кора + вода 3)
  - Лесная тушёнка (сырое мясо×1 + грибы×3 + кора + вода 3)
🟡 Легендарный ранг:
  - Таёжный пир (сырое мясо×1 + грибы×3 + ягоды×3 + кора + вода 3)
"""

from typing import Any, Dict, List, Optional, Tuple

from modules import items


COOKING_RECIPES: Dict[str, Dict[str, Any]] = {
    "cook_roast_berries": {
        "result": "Печёные ягоды",
        "rank": 1,
        "water_from_flask": 0,
        "needs_bark": True,
        "needs_meat": False,
        "berries_needed": 5,
        "mushrooms_needed": 0,
        "label": "⚪ Печёные ягоды (ягоды×5 + кора)",
        "description": "Быстро прогретые на углях сладкие лесные ягоды. Теряют вредную сырую кислоту, становясь мягким и безопасным источником сил.",
    },
    "cook_roast_mushrooms": {
        "result": "Жареные грибы",
        "rank": 1,
        "water_from_flask": 0,
        "needs_bark": True,
        "needs_meat": False,
        "berries_needed": 0,
        "mushrooms_needed": 5,
        "label": "⚪ Жареные грибы (грибы×5 + кора)",
        "description": "Подрумяненные шляпки на древесной коре. Высокая температура полностью нейтрализует лесные яды, хотя блюдо получается довольно сухим.",
    },
    "cook_berry_stew": {
        "result": "Ягодный отвар",
        "rank": 2,
        "water_from_flask": 1,
        "needs_bark": True,
        "needs_meat": False,
        "berries_needed": 5,
        "mushrooms_needed": 0,
        "label": "🟢 Ягодный отвар (ягоды×5 + кора + 1 вода)",
        "description": "Насыщенный горячий настой из лесных плодов. Мягко согревает изнутри, приятно утоляет жажду и постепенно возвращает жизненные силы.",
    },
    "cook_mushroom_soup": {
        "result": "Грибная похлёбка",
        "rank": 2,
        "water_from_flask": 2,
        "needs_bark": True,
        "needs_meat": False,
        "berries_needed": 0,
        "mushrooms_needed": 5,
        "label": "🟢 Грибная похлёбка (грибы×5 + кора + 2 вода)",
        "description": "Ароматный отвар на грибных шляпках. Наваристая юшка хорошо насыщает, увлажняет пересохшее горло и ускоряет затягивание мелких ран.",
    },
    "cook_roast_meat": {
        "result": "Мясо на коре",
        "rank": 3,
        "water_from_flask": 0,
        "needs_bark": True,
        "needs_meat": True,
        "berries_needed": 0,
        "mushrooms_needed": 0,
        "label": "🔵 Мясо на коре (сырое мясо + кора)",
        "description": "Прожаренный на углях кусок сочной дичи. Калорийный белковый обед гарантированно очищен от опасных паразитов и придаёт телу крепость.",
    },
    "cook_hunter_soup": {
        "result": "Охотничья похлёбка",
        "rank": 4,
        "water_from_flask": 3,
        "needs_bark": True,
        "needs_meat": True,
        "berries_needed": 5,
        "mushrooms_needed": 0,
        "label": "🟣 Охотничья похлёбка (мясо + ягоды×5 + кора + 3 вода)",
        "description": "Густой наваристый суп с волокнами дичи и ягодной кислинкой. Комплексный обед: полностью утоляет жажду, надолго набивает желудок и лечит тело.",
    },
    "cook_forest_stew": {
        "result": "Лесная тушёнка",
        "rank": 4,
        "water_from_flask": 3,
        "needs_bark": True,
        "needs_meat": True,
        "berries_needed": 0,
        "mushrooms_needed": 3,
        "label": "🟣 Лесная тушёнка (мясо + грибы×3 + кора + 3 вода)",
        "description": "Томлёное мясо с грибами в густом собственном соку. Невероятно питательное блюдо, целебные свойства которого способны вытянуть даже из тяжёлого состояния.",
    },
    "cook_taiga_feast": {
        "result": "Таёжный пир",
        "rank": 5,
        "water_from_flask": 3,
        "needs_bark": True,
        "needs_meat": True,
        "berries_needed": 3,
        "mushrooms_needed": 3,
        "label": "🟡 Таёжный пир (мясо + грибы×3 + ягоды×3 + кора + 3 вода)",
        "description": "Вершина костровой кулинарии из всех богатств тайги. Мощный горячий навар моментально возвращает к жизни, закрывая все базовые потребности выживания.",
    },
}


def get_recipe_for_id(recipe_id: str) -> Optional[Dict[str, Any]]:
    return COOKING_RECIPES.get(recipe_id)


def list_recipes() -> List[Tuple[str, str]]:
    """Возвращает рецепты, отсортированные от самого высокого ранга к низшему."""
    sorted_recipes = sorted(
        COOKING_RECIPES.items(),
        key=lambda item: item[1].get("rank", 1),
        reverse=True,
    )
    return [(rid, r.get("label", rid)) for rid, r in sorted_recipes]


def _count_tagged_items(inventory: Dict[str, int], tag: str) -> int:
    """Подсчитывает суммарное количество ягод или грибов всех видов в инвентаре."""
    candidates = items.BERRY_ITEMS if tag == "berry" else items.MUSHROOM_ITEMS
    check = items.is_berry if tag == "berry" else items.is_mushroom
    total = 0
    for name in candidates:
        total += inventory.get(name, 0)
    for name, qty in inventory.items():
        if name not in candidates and qty > 0 and check(name):
            total += qty
    return total


def _consume_tagged_items(inventory: Dict[str, int], tag: str, amount: int) -> List[str]:
    """Списывает amount ягод или грибов из инвентаря и возвращает список списанного."""
    candidates = list(items.BERRY_ITEMS if tag == "berry" else items.MUSHROOM_ITEMS)
    check = items.is_berry if tag == "berry" else items.is_mushroom
    for name in inventory.keys():
        if name not in candidates and check(name):
            candidates.append(name)

    consumed = []
    remaining = amount
    for name in candidates:
        if remaining <= 0:
            break
        have = inventory.get(name, 0)
        if have > 0:
            take = min(have, remaining)
            inventory[name] -= take
            if inventory[name] <= 0:
                del inventory[name]
            remaining -= take
            consumed.append(f"{name}×{take}")
    return consumed


def _consume(inventory: Dict[str, int], name: str, amount: int = 1) -> None:
    inventory[name] = inventory.get(name, 0) - amount
    if inventory[name] <= 0:
        del inventory[name]


def can_cook(game: Any, recipe_id: str) -> bool:
    """Проверяет, хватает ли ингредиентов прямо сейчас для приготовления блюда."""
    recipe = get_recipe_for_id(recipe_id)
    if not recipe:
        return False

    inv = getattr(game, "inventory", {}) or {}
    bark = "Кусок коры"
    if recipe.get("needs_bark", True):
        if inv.get(bark, 0) < 1:
            return False

    if recipe.get("needs_meat"):
        if inv.get("Сырое мясо", 0) < 1:
            return False

    berries_needed = int(recipe.get("berries_needed", 0))
    if berries_needed > 0:
        if _count_tagged_items(inv, "berry") < berries_needed:
            return False

    mushrooms_needed = int(recipe.get("mushrooms_needed", 0))
    if mushrooms_needed > 0:
        if _count_tagged_items(inv, "mushroom") < mushrooms_needed:
            return False

    water_needed = int(recipe.get("water_from_flask", 0))
    if water_needed > 0:
        flask = int(getattr(game, "flask_water", 0) or 0)
        has_flask_item = bool(getattr(game, "equipment", {}).get("flask"))
        flask_water_available = flask if has_flask_item else 0
        bottles_in_inv = inv.get("Бутылка воды", 0)
        plain_water = inv.get("Вода", 0)
        total_water = flask_water_available + bottles_in_inv * 20 + plain_water
        if total_water < water_needed:
            return False

    return True


def get_recipe_max_count(game: Any, recipe_id: str) -> int:
    """Рассчитывает максимум доступных порций для блюда по минимуму доступных ресурсов."""
    recipe = get_recipe_for_id(recipe_id)
    if not recipe:
        return 0

    inv = getattr(game, "inventory", {}) or {}
    bark = "Кусок коры"
    limits = []

    if recipe.get("needs_bark", True):
        limits.append(inv.get(bark, 0))

    if recipe.get("needs_meat"):
        limits.append(inv.get("Сырое мясо", 0))

    berries_needed = int(recipe.get("berries_needed", 0))
    if berries_needed > 0:
        limits.append(_count_tagged_items(inv, "berry") // berries_needed)

    mushrooms_needed = int(recipe.get("mushrooms_needed", 0))
    if mushrooms_needed > 0:
        limits.append(_count_tagged_items(inv, "mushroom") // mushrooms_needed)

    water_needed = int(recipe.get("water_from_flask", 0))
    if water_needed > 0:
        flask = int(getattr(game, "flask_water", 0) or 0)
        has_flask_item = bool(getattr(game, "equipment", {}).get("flask"))
        flask_water_available = flask if has_flask_item else 0
        bottles_in_inv = inv.get("Бутылка воды", 0)
        plain_water = inv.get("Вода", 0)
        total_water = flask_water_available + bottles_in_inv * 20 + plain_water
        limits.append(total_water // water_needed)

    if not limits:
        return 0
    return max(0, min(limits))


def format_recipe_card(recipe_id: str, game: Any = None) -> str:
    """Форматирует информационную карточку рецепта для костра по единой Модели экранов."""
    recipe = get_recipe_for_id(recipe_id)
    if not recipe:
        return "Рецепт не найден."

    res_name = recipe["result"]
    res_data = items.ITEMS.get(res_name, {})
    rank_marker = items.get_item_rank_marker(res_name)

    lines = [f"🍳 {rank_marker} {res_name}", ""]
    desc = recipe.get("description", "")
    if desc:
        lines.append(desc)
        lines.append("")

    # Ингредиенты в едином формате
    ing_parts = []
    if recipe.get("needs_bark"):
        ing_parts.append("Кусок коры: 1")
    if recipe.get("needs_meat"):
        ing_parts.append("Сырое мясо: 1")
    if recipe.get("berries_needed"):
        ing_parts.append(f"Любые [Ягоды]: {recipe['berries_needed']}")
    if recipe.get("mushrooms_needed"):
        ing_parts.append(f"Любые [Грибы]: {recipe['mushrooms_needed']}")
    water = recipe.get("water_from_flask", 0)
    if water > 0:
        ing_parts.append(f"Вода: {water}")

    lines.append("Ингредиенты:")
    for ing in ing_parts:
        lines.append(f"• {ing}")
    lines.append("")

    max_count = get_recipe_max_count(game, recipe_id) if game is not None else 0
    lines.append(f"Доступно для готовки: {max_count} шт.")
    lines.append("")

    # Эффекты готового блюда
    effects = res_data.get("effects", {})
    eff_parts = []
    if effects.get("hunger"):
        eff_parts.append(f"🍖 Сытость +{effects['hunger']}")
    if effects.get("thirst"):
        eff_parts.append(f"💧 Жажда +{effects['thirst']}")
    if effects.get("hp"):
        eff_parts.append(f"❤️ Здоровье +{effects['hp']} HP")
    lines.append("Эффект блюда: " + (", ".join(eff_parts) if eff_parts else "Сытный обед"))

    neg = res_data.get("negative_effects")
    if neg:
        lines.append(f"Негативный эффект: {neg.get('description')}")
    else:
        lines.append("Негативный эффект: Отсутствуют (безопасная горячая пища)")

    note = res_data.get("note")
    if note:
        lines.append(f"Примечание: {note}")

    lines.append("")
    lines.append("💬 Или напиши в чат число, сколько приготовить.")

    body = "\n".join(lines)
    return f"━━━━━━━━━━━━━━━━━━━\n{body}\n━━━━━━━━━━━━━━━━━━━"


def cook_portions(game: Any, recipe_id: str, count: int) -> Tuple[int, str]:
    """Готовит до count порций на костре. Возвращает (успешно_приготовлено, сообщение)."""
    if count <= 0:
        return 0, "Количество должно быть больше нуля."
    recipe = get_recipe_for_id(recipe_id)
    if not recipe:
        return 0, f"Рецепт '{recipe_id}' не найден."

    max_c = get_recipe_max_count(game, recipe_id)
    to_cook = min(count, max_c)
    if to_cook <= 0:
        return 0, "Недостаточно ингредиентов для приготовления."

    cooked = 0
    for _ in range(to_cook):
        ok, msg = cook_item(game, recipe_id)
        if not ok:
            break
        cooked += 1

    res_name = recipe["result"]
    if cooked > 0:
        return cooked, f"Приготовлено: {res_name} ×{cooked}"
    return 0, "Не удалось приготовить блюдо."


def cook_item(game: Any, recipe_id: str) -> Tuple[bool, str]:
    recipe = get_recipe_for_id(recipe_id)
    if not recipe:
        return False, f"Рецепт '{recipe_id}' не найден."

    inv = game.inventory
    bark = "Кусок коры"

    if recipe.get("needs_bark", True):
        if inv.get(bark, 0) < 1:
            return False, f"Нужен {bark} (посуда для костра)."

    # Проверка мяса
    if recipe.get("needs_meat"):
        if inv.get("Сырое мясо", 0) < 1:
            return False, "Нужно Сырое мясо ×1."

    # Проверка ягод
    berries_needed = int(recipe.get("berries_needed", 0))
    if berries_needed > 0:
        berries_have = _count_tagged_items(inv, "berry")
        if berries_have < berries_needed:
            return False, f"Нужно {berries_needed} ягод (тег [Ягоды]), у вас: {berries_have}."

    # Проверка грибов
    mushrooms_needed = int(recipe.get("mushrooms_needed", 0))
    if mushrooms_needed > 0:
        mushrooms_have = _count_tagged_items(inv, "mushroom")
        if mushrooms_have < mushrooms_needed:
            return False, f"Нужно {mushrooms_needed} грибов (тег [Грибы]), у вас: {mushrooms_have}."

    # Проверка воды (с учётом фляги и запасных бутылок в инвентаре)
    water_needed = int(recipe.get("water_from_flask", 0))
    flask = int(getattr(game, "flask_water", 0) or 0)
    has_flask_item = bool(getattr(game, "equipment", {}).get("flask"))
    flask_water_available = flask if has_flask_item else 0

    bottles_in_inv = inv.get("Бутылка воды", 0)
    plain_water = inv.get("Вода", 0)
    total_water = flask_water_available + bottles_in_inv * 20 + plain_water

    if water_needed > 0 and total_water < water_needed:
        return False, f"Недостаточно воды (нужно {water_needed}, доступно {total_water})."

    # --- Списание ингредиентов ---
    if recipe.get("needs_bark", True):
        _consume(inv, bark, 1)

    meat_used = False
    if recipe.get("needs_meat"):
        _consume(inv, "Сырое мясо", 1)
        meat_used = True

    used_ingredients = []
    if meat_used:
        used_ingredients.append("Сырое мясо×1")

    if berries_needed > 0:
        c_berries = _consume_tagged_items(inv, "berry", berries_needed)
        used_ingredients.extend(c_berries)

    if mushrooms_needed > 0:
        c_mushrooms = _consume_tagged_items(inv, "mushroom", mushrooms_needed)
        used_ingredients.extend(c_mushrooms)

    used_ingredients.append("Кусок коры×1")

    # Списание воды
    if water_needed > 0:
        remaining_needed = water_needed

        # 1. Забираем из надетой фляги
        if flask_water_available > 0:
            take = min(flask_water_available, remaining_needed)
            game.flask_water = flask_water_available - take
            remaining_needed -= take
            if game.flask_water <= 0:
                container_name = getattr(game, "equipment", {}).get("flask") or "Бутылка воды"
                if hasattr(game, "equipment"):
                    game.equipment["flask"] = None
                inv["Пустая бутылка"] = inv.get("Пустая бутылка", 0) + 1
                if hasattr(game, "add_log"):
                    game.add_log(f"Ёмкость «{container_name}» опустошена! В инвентаре осталась пустая бутылка.")

        # 2. Если нужно ещё — добираем из бутылки в инвентаре
        while remaining_needed > 0 and inv.get("Бутылка воды", 0) > 0:
            inv["Бутылка воды"] -= 1
            if inv["Бутылка воды"] <= 0:
                del inv["Бутылка воды"]
            if hasattr(game, "equipment"):
                game.equipment["flask"] = "Бутылка воды"
            take = min(20, remaining_needed)
            game.flask_water = 20 - take
            remaining_needed -= take
            if game.flask_water <= 0:
                if hasattr(game, "equipment"):
                    game.equipment["flask"] = None
                inv["Пустая бутылка"] = inv.get("Пустая бутылка", 0) + 1
                if hasattr(game, "add_log"):
                    game.add_log("Ёмкость «Бутылка воды» опустошена! В инвентаре осталась пустая бутылка.")
            else:
                if hasattr(game, "add_log"):
                    game.add_log(f"Взята новая ёмкость «Бутылка воды» из инвентаря (осталось {game.flask_water}/20).")

        # 3. Резервный забор обычной воды
        if remaining_needed > 0 and inv.get("Вода", 0) > 0:
            take = min(inv["Вода"], remaining_needed)
            _consume(inv, "Вода", take)
            remaining_needed -= take

        used_ingredients.append(f"вода×{water_needed}")

    result = recipe["result"]
    inv[result] = inv.get(result, 0) + 1
    rank_marker = items.get_item_rank_marker(result)

    return True, f"🍳 {rank_marker} {result} готово! ({', '.join(used_ingredients)} → {result})"
