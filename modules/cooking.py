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

from aiogram import types

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
    if recipe.get("needs_bark", True):
        bark_avail = inv.get("Кусок коры", 0) + inv.get("Кора", 0)
        plate_avail = inv.get("Сланцевая тарелка", 0)
        if (bark_avail + plate_avail) < 1:
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
        bark_avail = inv.get("Кусок коры", 0) + inv.get("Кора", 0)
        plates_avail = inv.get("Сланцевая тарелка", 0)
        limits.append(bark_avail + plates_avail)

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
    inv = getattr(game, "inventory", {}) or {} if game is not None else {}
    bark_have = inv.get("Кусок коры", 0) + inv.get("Кора", 0)
    plate_have = inv.get("Сланцевая тарелка", 0)
    dish_have = bark_have + plate_have

    meat_have = inv.get("Сырое мясо", 0)
    berries_have = _count_tagged_items(inv, "berry") if game is not None else 0
    mushrooms_have = _count_tagged_items(inv, "mushroom") if game is not None else 0

    flask = int(getattr(game, "flask_water", 0) or 0)
    has_flask_item = bool(getattr(game, "equipment", {}).get("flask")) if game is not None else False
    flask_water_available = flask if has_flask_item else 0
    bottles_in_inv = inv.get("Бутылка воды", 0)
    plain_water = inv.get("Вода", 0)
    water_have = flask_water_available + bottles_in_inv * 20 + plain_water

    ing_parts = []
    if recipe.get("needs_bark"):
        if game is not None:
            status = "✅" if dish_have >= 1 else "❌"
            ing_parts.append(f"{status} Посуда (Кусок коры или Сланцевая тарелка): 1 (в наличии: {dish_have})")
        else:
            ing_parts.append("Посуда: Кусок коры или Сланцевая тарелка: 1")
    if recipe.get("needs_meat"):
        if game is not None:
            status = "✅" if meat_have >= 1 else "❌"
            ing_parts.append(f"{status} Сырое мясо: 1 (в наличии: {meat_have})")
        else:
            ing_parts.append("Сырое мясо: 1")
    if recipe.get("berries_needed"):
        b_need = recipe["berries_needed"]
        if game is not None:
            status = "✅" if berries_have >= b_need else "❌"
            ing_parts.append(f"{status} Любые [Ягоды]: {b_need} (в наличии: {berries_have})")
        else:
            ing_parts.append(f"Любые [Ягоды]: {b_need}")
    if recipe.get("mushrooms_needed"):
        m_need = recipe["mushrooms_needed"]
        if game is not None:
            status = "✅" if mushrooms_have >= m_need else "❌"
            ing_parts.append(f"{status} Любые [Грибы]: {m_need} (в наличии: {mushrooms_have})")
        else:
            ing_parts.append(f"Любые [Грибы]: {m_need}")
    water = recipe.get("water_from_flask", 0)
    if water > 0:
        if game is not None:
            status = "✅" if water_have >= water else "❌"
            ing_parts.append(f"{status} Вода: {water} (в наличии: {water_have})")
        else:
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
        game.food_cooked = getattr(game, "food_cooked", 0) + cooked
        return cooked, f"Приготовлено: {res_name} ×{cooked}"
    return 0, "Не удалось приготовить блюдо."


def cook_item(game: Any, recipe_id: str) -> Tuple[bool, str]:
    recipe = get_recipe_for_id(recipe_id)
    if not recipe:
        return False, f"Рецепт '{recipe_id}' не найден."

    inv = game.inventory
    used_plate = False
    if recipe.get("needs_bark", True):
        plate = "Сланцевая тарелка"
        bark = "Кусок коры"
        bark_avail = inv.get(bark, 0) + inv.get("Кора", 0)
        plate_avail = inv.get(plate, 0)
        if plate_avail > 0:
            used_plate = True
        elif bark_avail > 0:
            used_plate = False
        else:
            return False, f"Нужен {bark} или {plate} (посуда для готовки)."

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
        if used_plate:
            _consume(inv, "Сланцевая тарелка", 1)
        elif inv.get("Кусок коры", 0) > 0:
            _consume(inv, "Кусок коры", 1)
        else:
            _consume(inv, "Кора", 1)

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

    if used_plate:
        used_ingredients.append("Сланцевая тарелка×1")
    else:
        used_ingredients.append("Кусок коры×1")

    # Списание воды
    if water_needed > 0:
        remaining_needed = water_needed

        # 1. Забираем из надетой фляги
        if flask_water_available > 0:
            take = min(flask_water_available, remaining_needed)
            game.flask_water = flask_water_available - take
            remaining_needed -= take
            container_name = getattr(game, "equipment", {}).get("flask") or "Бутылка воды"
            if "Армейская" in container_name:
                game.army_flask_water = game.flask_water
                if game.flask_water <= 0:
                    game.flask_water = 0
                    game.army_flask_water = 0
                    if hasattr(game, "add_log"):
                        game.add_log(f"Ёмкость «{container_name}» опустела (0/20)!")
            else:
                if game.flask_water <= 0:
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
    if used_plate:
        result = f"{result} (🍽️)"
    inv[result] = inv.get(result, 0) + 1
    rank_marker = items.get_item_rank_marker(result)

    return True, f"🍳 {rank_marker} {result} готово! ({', '.join(used_ingredients)} → {result})"


def get_campfire_text(game: Any = None, action_header: Optional[str] = None) -> str:
    """Формирует живое описание костра или печи с рамками сверху и снизу."""
    durability = int(getattr(game, "campfire_durability", 0) or 0)
    is_stove = getattr(game, "is_stove", False) if game else False
    max_d = 30 if is_stove else int(getattr(game, "campfire_max_durability", 10) or 10)
    ratio = durability / max_d if max_d > 0 else 0

    if is_stove:
        title = "🧱 ПЕЧЬ"
        if ratio >= 0.8:
            narrative = "Каменная печь раскалена докрасна и наполняет укрытие густым жаром. Угли пышут мощным теплом."
        elif ratio >= 0.5:
            narrative = "В печи ровно гудит пламя. Каменные стенки накопили жар, угли держат тепло."
        elif ratio >= 0.2:
            narrative = "Огонь в печи стихает, на дне топки тлеют серые угли. Пора подбросить топлива."
        elif durability > 0:
            narrative = "Печь почти остыла, в золе едва теплятся последние искры."
        else:
            narrative = "Печь полностью остыла. Очаг можно растопить заново."
    else:
        title = "🔥 КОСТЁР"
        if ratio >= 0.8:
            narrative = "Костёр ярко пылает и озаряет лагерь. Жаркие угли согревают всё вокруг, треск сучьев отгоняет лесную тьму."
        elif ratio >= 0.5:
            narrative = "Костёр уверенно потрескивает, ровное пламя дарит тепло и уют. Огонь стабилен, но со временем потребует дров."
        elif ratio >= 0.3:
            narrative = "Пламя заметно ослабло, костёр начинает угасать. Дым стелется по земле, пора подбросить веток."
        elif durability > 0:
            narrative = "Костёр едва тлеет, остались лишь тусклые угли. Ещё немного — и лагерь погрузится в ледяной мрак."
        else:
            narrative = "Костёр потух. Вокруг лишь холодный пепел."

    body = [title, narrative]
    if action_header:
        body.append(f"{action_header}\nОгонь: {durability}/{max_d}")
    else:
        body.append(f"Огонь: {durability}/{max_d}")

    content = "\n\n".join(body)
    return f"━━━━━━━━━━━━━━━━━━━\n{content}\n━━━━━━━━━━━━━━━━━━━"


def format_resource_log_text(deltas: dict) -> str:
    """Собрать строку лога строго по ФАКТИЧЕСКИМ дельтам из consume_action/light_campfire."""
    parts = []
    if deltas.get("delta_hunger"):
        parts.append(f"Голод {deltas['delta_hunger']:+d}")
    if deltas.get("delta_thirst"):
        parts.append(f"Жажда {deltas['delta_thirst']:+d}")
    hp_delta = deltas.get("delta_hp", 0)
    if hp_delta:
        hp_reasons = []
        if deltas.get("hunger_damage_to_hp"):
            hp_reasons.append("голодание")
        if deltas.get("thirst_damage_to_hp"):
            hp_reasons.append("обезвоживание")
        reason = f" ({', '.join(hp_reasons)})" if hp_reasons else ""
        parts.append(f"HP {hp_delta:+d}{reason}")
    return ", ".join(parts)


def is_campfire_callback(data: str) -> bool:
    """Проверяет, относится ли callback.data к механике костра, топлива или готовки."""
    return (
        data in (
            "action_light_campfire",
            "campfire_confirm_light",
            "campfire_screen",
            "menu_campfire",
            "campfire_add_fuel_menu",
            "stove_rekindle",
            "campfire_recipes",
            "campfire_boil_water",
        )
        or data.startswith((
            "cook_",
            "cook_recipe:",
            "recipe:",
            "fuel_menu:",
            "feed_fuel_action:",
            "feed_fuel:",
        ))
    )


async def handle_campfire_callback(
    data: str,
    game: Any,
    uid: int,
    callback: Optional[Any] = None,
) -> Tuple[Optional[str], Optional[Any]]:
    """Обрабатывает все callback-запросы костра, печи, топлива, готовки и кипячения воды.

    Импорты клавиатур происходят строго внутри функции для защиты от циклических зависимостей.
    """
    from keyboards import (
        get_campfire_kb,
        get_campfire_fuel_kb,
        get_fuel_quantity_kb,
        get_campfire_recipes_kb,
        get_campfire_recipe_view_kb,
        get_main_kb,
    )

    text = None
    kb = None

    if data.startswith(("cook_recipe_view_", "cook_recipe:", "recipe:")):
        if data.startswith("cook_recipe_view_"):
            recipe_id = data.removeprefix("cook_recipe_view_")
        elif data.startswith("cook_recipe:"):
            recipe_id = data.removeprefix("cook_recipe:")
        else:
            recipe_id = data.removeprefix("recipe:")

        game.push_screen("recipe_card")
        game.story_state = "WAITING_FOR_COOK_COUNT"
        game.story_flags["cook_recipe_id"] = recipe_id
        max_count = get_recipe_max_count(game, recipe_id)
        text = format_recipe_card(recipe_id, game)
        kb = get_campfire_recipe_view_kb(recipe_id, max_count)
        return text, kb

    elif data.startswith("cook_qty:"):
        parts = data.split(":", 2)
        recipe_id = parts[1]
        qty_mode = parts[2]
        if not getattr(game, "campfire_active", False) or getattr(game, "campfire_durability", 0) <= 0:
            if callback:
                await callback.answer("🔥 Костёр погас! Разведите его снова.", show_alert=True)
            return None, None
        max_c = get_recipe_max_count(game, recipe_id)
        if max_c <= 0:
            if callback:
                await callback.answer("⚠️ Недостаточно ингредиентов!", show_alert=True)
            return None, None
        to_cook = max_c if qty_mode == "all" else 1
        cooked, message = cook_portions(game, recipe_id, to_cook)
        if cooked <= 0:
            if callback:
                await callback.answer(f"⚠️ {message}", show_alert=True)
            return None, None
        game.story_state = None
        game.story_flags.pop("cook_recipe_id", None)
        game.add_log(message)
        game.nav_stack = ["main", "campfire"]
        header = f"✅ {message}"
        text = get_campfire_text(game, action_header=header)
        kb = get_campfire_kb(game)
        return text, kb

    elif data.startswith("cook_exec_") or (data.startswith("cook_") and not data.startswith("cook_recipe_view_") and not data.startswith("cook_qty:") and not data.startswith("cook_recipe:")):
        recipe_id = data.removeprefix("cook_exec_")
        if not getattr(game, "campfire_active", False) or getattr(game, "campfire_durability", 0) <= 0:
            if callback:
                await callback.answer("🔥 Костёр погас! Разведите его снова.", show_alert=True)
            return None, None
        cooked, message = cook_portions(game, recipe_id, 1)
        if cooked <= 0:
            if callback:
                await callback.answer(f"⚠️ {message}", show_alert=True)
            return None, None
        game.story_state = None
        game.story_flags.pop("cook_recipe_id", None)
        game.add_log(message)
        game.nav_stack = ["main", "campfire"]
        header = f"✅ {message}"
        text = get_campfire_text(game, action_header=header)
        kb = get_campfire_kb(game)
        return text, kb
    elif data == "action_light_campfire":
        has_torch = (
            game.equipment.get("hand_left") == "Факел"
        )
        has_matches = game.inventory.get("Спички", 0) > 0
        min_ap = 1 if (has_torch or has_matches) else 2
        if game.ap < min_ap:
            warning_msg = f"⚠️ Не хватает очков действий (требуется {min_ap} ⚡)!"
            game.add_log(warning_msg)
            if callback:
                await callback.answer(warning_msg, show_alert=True)
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            campfire_result = game.light_campfire()
            if campfire_result.get("lit"):
                res_log = format_resource_log_text(campfire_result)
                if res_log:
                    game.add_log(res_log)
                text = f"🔥 Вы развели костёр! (Прочность: {game.campfire_durability}/{game.campfire_max_durability})"
                kb = get_campfire_kb(game)
            else:
                warning_msg = f"⚠️ Не хватает очков действий (требуется {min_ap} ⚡)!"
                game.add_log(warning_msg)
                if callback:
                    await callback.answer(warning_msg, show_alert=True)
                text = game.get_ui()
                kb = get_main_kb(game)
        return text, kb

    elif data == "campfire_confirm_light":
        has_torch = (
            game.equipment.get("hand_left") == "Факел"
        )
        has_matches = game.inventory.get("Спички", 0) > 0
        min_ap = 1 if (has_torch or has_matches) else 2

        if game.inventory.get("Костёр", 0) < 1:
            game.add_log("⚠️ Нет костра в инвентаре.")
            if callback:
                await callback.answer("⚠️ Нет костра в инвентаре!", show_alert=True)
            text = game.get_ui()
            kb = get_main_kb(game)
        elif game.ap < min_ap:
            warning_msg = f"⚠️ Не хватает очков действий (требуется {min_ap} ⚡)!"
            game.add_log(warning_msg)
            if callback:
                await callback.answer(warning_msg, show_alert=True)
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            campfire_result = game.light_campfire()
            if not campfire_result.get("lit"):
                warning_msg = f"⚠️ Не хватает очков действий (требуется {min_ap} ⚡)!"
                game.add_log(warning_msg)
                if callback:
                    await callback.answer(warning_msg, show_alert=True)
                text = game.get_ui()
                kb = get_main_kb(game)
            else:
                game.inventory["Костёр"] -= 1
                if game.inventory["Костёр"] <= 0:
                    del game.inventory["Костёр"]
                game.add_log("🔥 Костёр успешно разведён (10/10)! Кнопка костра теперь доступна на главном экране.")
                text = game.get_ui()
                kb = get_main_kb(game)
        return text, kb

    elif data in ("campfire_screen", "menu_campfire"):
        game.story_state = None
        game.story_flags.pop("cook_recipe_id", None)
        game.story_flags.pop("fuel_item", None)
        game.push_screen("campfire")
        text = get_campfire_text(game)
        kb = get_campfire_kb(game)
        return text, kb

    elif data == "campfire_add_fuel_menu":
        game.story_state = None
        game.story_flags.pop("fuel_item", None)
        game.push_screen("campfire_fuel")
        inv = getattr(game, "inventory", {}) or {}
        sticks = inv.get("Ветка", 0) + inv.get("Палки", 0) + inv.get("Палка", 0)
        bark = inv.get("Кусок коры", 0) + inv.get("Кора", 0)
        coal = inv.get("Древесный уголь", 0)
        is_stove = getattr(game, "is_stove", False)
        if sticks <= 0 and bark <= 0 and coal <= 0:
            text = "⚠️ В инвентаре нет подходящего топлива!\nНужны палки/ветки, кора или древесный уголь."
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
            ])
        else:
            cur_d = getattr(game, "campfire_durability", 0)
            max_d = 30 if is_stove else getattr(game, "campfire_max_durability", 10)
            title = "🧱 ПЕЧЬ" if is_stove else "🔥 КОСТЁР"
            text = f"{title} ({cur_d}/{max_d})\nВыберите топливо для поддержания огня:"
            kb = get_campfire_fuel_kb(game)
        return text, kb

    elif data == "stove_rekindle":
        ok, msg = game.rekindle_stove()
        if not ok:
            if callback:
                await callback.answer(f"⚠️ {msg}", show_alert=True)
            return None, None
        if callback:
            await callback.answer("🔥 Печь растоплена!", show_alert=True)
        text = get_campfire_text(game, action_header="🔥 Печь растоплена (+1 к огню)")
        kb = get_campfire_kb(game)
        return text, kb

    elif data.startswith("fuel_menu:"):
        fuel_type = data.removeprefix("fuel_menu:")
        inv = getattr(game, "inventory", {}) or {}
        is_stove = getattr(game, "is_stove", False)
        cur_max = 30 if is_stove else int(getattr(game, "campfire_max_durability", 10) or 10)
        needed = max(0, cur_max - game.campfire_durability)
        if not getattr(game, "campfire_active", False) or getattr(game, "campfire_durability", 0) <= 0:
            if is_stove:
                if callback:
                    await callback.answer("🧱 Печь остыла! Растопите её заново.", show_alert=True)
            else:
                if callback:
                    await callback.answer("🔥 Костёр уже погас! Разведите его заново.", show_alert=True)
            text = get_campfire_text(game)
            kb = get_campfire_kb(game)
            return text, kb
        elif needed <= 0:
            if callback:
                await callback.answer("Очаг и так пылает сильным жаром", show_alert=True)
            text = get_campfire_text(game)
            kb = get_campfire_kb(game)
            return text, kb
        elif fuel_type == "sticks":
            sticks = inv.get("Ветка", 0) + inv.get("Палки", 0) + inv.get("Палка", 0)
            if sticks <= 0:
                if callback:
                    await callback.answer("⚠️ В инвентаре нет палок/веток!", show_alert=True)
                return None, None
            game.push_screen("fuel_qty")
            game.story_state = "WAITING_FOR_FUEL_COUNT"
            game.story_flags["fuel_item"] = "sticks"
            cur = game.campfire_durability
            max_d = cur_max
            max_can_add = min(sticks, needed)
            text = (
                "🪵 Палки (1 палка = +1 к огню)\n\n"
                f"Сейчас огонь: {cur}/{max_d}\n"
                f"В инвентаре: {sticks} палок\n"
                f"Чтобы дойти до {max_d}/{max_d}, нужно: {needed} палок\n"
                f"Сейчас можешь подкинуть максимум {max_can_add} палок (станет {cur + max_can_add}/{max_d}).\n\n"
                "Выбери кнопку или напиши число в чат.\n\n"
                "💬 Или напиши в чат число, сколько подкинуть."
            )
            kb = get_fuel_quantity_kb("sticks", game)
            return text, kb
        elif fuel_type == "coal":
            coal = inv.get("Древесный уголь", 0)
            if coal <= 0:
                if callback:
                    await callback.answer("⚠️ В инвентаре нет древесного угля!", show_alert=True)
                return None, None
            game.push_screen("fuel_qty")
            game.story_state = "WAITING_FOR_FUEL_COUNT"
            game.story_flags["fuel_item"] = "coal"
            cur = game.campfire_durability
            max_d = cur_max
            text = (
                "⚫ Древесный уголь (1 шт. = +3 к огню)\n\n"
                f"Сейчас огонь: {cur}/{max_d}\n"
                f"В инвентаре: {coal} угля\n"
                f"Подкидывание 1 куска угля добавит +3 к огню.\n\n"
                "Выбери кнопку или напиши число в чат.\n\n"
                "💬 Или напиши в чат число, сколько подкинуть."
            )
            kb = get_fuel_quantity_kb("coal", game)
            return text, kb
        else:
            bark = inv.get("Кусок коры", 0) + inv.get("Кора", 0)
            if bark < 2:
                if callback:
                    await callback.answer(f"⚠️ Нужно чётное число коры, минимум 2 (в наличии: {bark} шт.)", show_alert=True)
                return None, None
            game.push_screen("fuel_qty")
            game.story_state = "WAITING_FOR_FUEL_COUNT"
            game.story_flags["fuel_item"] = "bark"
            cur = game.campfire_durability
            max_d = cur_max
            max_bark = min((bark // 2) * 2, needed * 2)
            max_fire = max_bark // 2
            text = (
                "🧱 Кора (2 коры = +1 к огню, кидаем только парами!)\n\n"
                f"Сейчас огонь: {cur}/{max_d}\n"
                f"В инвентаре: {bark} коры (пар: {bark // 2})\n"
                f"Чтобы дойти до {max_d}/{max_d}, нужно: +{needed} огня = {needed * 2} коры\n"
                f"Сейчас можешь подкинуть максимум {max_bark} коры → +{max_fire} к огню (станет {cur + max_fire}/{max_d}).\n\n"
                "Выбери кнопку или напиши чётное число в чат.\n\n"
                "💬 Или напиши в чат число, сколько подкинуть."
            )
            kb = get_fuel_quantity_kb("bark", game)
            return text, kb

    elif data.startswith("feed_fuel_action:") or data.startswith("feed_fuel:"):
        game.story_state = None
        game.story_flags.pop("fuel_item", None)
        if data.startswith("feed_fuel_action:"):
            parts = data.split(":", 2)
            fuel_kind = parts[1]  # sticks, bark or coal
            action_mode = parts[2]  # 1, 2, max, custom
        else:
            parts = data.split(":", 2)
            raw_item = parts[1]
            action_mode = parts[2]
            if "уголь" in raw_item.lower():
                fuel_kind = "coal"
            elif "кор" in raw_item.lower():
                fuel_kind = "bark"
            else:
                fuel_kind = "sticks"

        inv = getattr(game, "inventory", {}) or {}
        is_stove = getattr(game, "is_stove", False)
        cur_max = 30 if is_stove else int(getattr(game, "campfire_max_durability", 10) or 10)
        needed = max(0, cur_max - game.campfire_durability)

        if not getattr(game, "campfire_active", False) or getattr(game, "campfire_durability", 0) <= 0:
            if is_stove:
                if callback:
                    await callback.answer("🧱 Печь остыла! Растопите её заново.", show_alert=True)
            else:
                if callback:
                    await callback.answer("🔥 Костёр уже погас! Разведите его заново.", show_alert=True)
            text = get_campfire_text(game)
            kb = get_campfire_kb(game)
            return text, kb
        elif needed <= 0:
            if callback:
                await callback.answer("Очаг и так пылает сильным жаром", show_alert=True)
            text = get_campfire_text(game)
            kb = get_campfire_kb(game)
            return text, kb
        elif action_mode == "custom":
            game.story_state = "WAITING_FOR_FUEL_COUNT"
            game.story_flags["fuel_item"] = fuel_kind
            if fuel_kind == "bark":
                bark = inv.get("Кусок коры", 0) + inv.get("Кора", 0)
                text = f"🧱 Введите количество коры для костра в чат:\n(Доступно: {bark} шт., 2 коры = +1 к огню, минимум 2)"
            elif fuel_kind == "coal":
                coal = inv.get("Древесный уголь", 0)
                text = f"⚫ Введите количество угля в чат:\n(Доступно: {coal} шт., 1 уголь = +3 к огню)"
            else:
                sticks = inv.get("Ветка", 0) + inv.get("Палки", 0) + inv.get("Палка", 0)
                text = f"🪵 Введите количество палок для костра в чат:\n(Доступно: {sticks} шт., нужно до максимума: {needed} шт.)"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="↩️ Назад", callback_data="campfire_screen")]
            ])
            return text, kb
        elif fuel_kind == "coal":
            coal_avail = inv.get("Древесный уголь", 0)
            if coal_avail <= 0:
                if callback:
                    await callback.answer("⚠️ В инвентаре нет древесного угля!", show_alert=True)
                return None, None
            to_use = 1 if action_mode == "1" else min(coal_avail, max(1, (needed + 2) // 3))
            inv["Древесный уголь"] -= to_use
            if inv["Древесный уголь"] <= 0:
                del inv["Древесный уголь"]
            fire_added = to_use * 3
            game.campfire_durability += fire_added
            game.nav_stack = ["main", "campfire"]
            max_d = 30 if is_stove else game.campfire_max_durability
            game.add_log(f"⚫ Подкинуто: Древесный уголь ×{to_use} (+{fire_added} 🔥). Огонь: {game.campfire_durability}/{max_d}.")
            action_header = f"⚫ Подкинуто: Древесный уголь ×{to_use} (+{fire_added} огня)"
            text = get_campfire_text(game, action_header=action_header)
            kb = get_campfire_kb(game)
            return text, kb
        elif fuel_kind == "bark":
            bark_avail = inv.get("Кусок коры", 0) + inv.get("Кора", 0)
            if bark_avail < 2:
                if callback:
                    await callback.answer("⚠️ Нужно чётное число коры, минимум 2", show_alert=True)
                return None, None
            if action_mode in ("2", "1"):
                count = 2
            else:
                count = bark_avail
            spent = (count // 2) * 2
            spent = min(spent, (bark_avail // 2) * 2, needed * 2)
            if spent == 0:
                if callback:
                    await callback.answer("⚠️ Нужно чётное число коры, минимум 2", show_alert=True)
                return None, None
            to_deduct = spent
            for k in ("Кусок коры", "Кора"):
                if to_deduct <= 0:
                    break
                have = inv.get(k, 0)
                take = min(have, to_deduct)
                inv[k] -= take
                if inv[k] <= 0:
                    del inv[k]
                to_deduct -= take
            fire_added = spent // 2
            game.campfire_durability += fire_added
            game.nav_stack = ["main", "campfire"]
            max_d = 30 if is_stove else game.campfire_max_durability
            game.add_log(f"🧱 Подкинуто: Кора ×{spent} (+{fire_added} 🔥). Огонь: {game.campfire_durability}/{max_d}.")
            action_header = f"🧱 Подкинуто: Кора ×{spent} (+{fire_added} огня)"
            text = get_campfire_text(game, action_header=action_header)
            kb = get_campfire_kb(game)
            return text, kb
        else:
            sticks_avail = inv.get("Ветка", 0) + inv.get("Палки", 0) + inv.get("Палка", 0)
            if sticks_avail <= 0:
                if callback:
                    await callback.answer("⚠️ В инвентаре нет палок/веток!", show_alert=True)
                return None, None
            to_use = 1 if action_mode == "1" else min(sticks_avail, needed)
            if to_use <= 0:
                if callback:
                    await callback.answer("⚠️ В инвентаре нет палок/веток!", show_alert=True)
                return None, None
            to_deduct = to_use
            for k in ("Ветка", "Палки", "Палка"):
                if to_deduct <= 0:
                    break
                have = inv.get(k, 0)
                take = min(have, to_deduct)
                inv[k] -= take
                if inv[k] <= 0:
                    del inv[k]
                to_deduct -= take
            game.campfire_durability += to_use
            game.nav_stack = ["main", "campfire"]
            max_d = 30 if is_stove else game.campfire_max_durability
            game.add_log(f"🪵 Подкинуто: Палки ×{to_use}. Огонь: {game.campfire_durability}/{max_d}.")
            action_header = f"🪵 Подкинуто: Ветка ×{to_use} (+{to_use} огня)"
            text = get_campfire_text(game, action_header=action_header)
            kb = get_campfire_kb(game)
            return text, kb

    elif data == "campfire_recipes":
        game.story_state = None
        game.story_flags.pop("cook_recipe_id", None)
        game.push_screen("campfire_recipes")
        available_count = sum(1 for r_id in COOKING_RECIPES if can_cook(game, r_id))
        if available_count > 0:
            text = "📜 Рецепты костра\n\nВыберите блюдо, чтобы узнать ингредиенты и приготовить:"
        else:
            text = (
                "📜 Рецепты костра\n\n"
                "Сейчас у вас недостаточно ингредиентов ни для одного блюда.\n\n"
                "💡 Для готовки на костре требуется:\n"
                "• Посуда для жарки: Кусок коры или Сланцевая тарелка\n"
                "• Свежие лесные припасы: ягоды (от 5 шт.), грибы (от 5 шт.) или сырое мясо"
            )
        kb = get_campfire_recipes_kb(game)
        return text, kb

    elif data == "campfire_boil_water":
        if not getattr(game, "campfire_active", False) or getattr(game, "campfire_durability", 0) <= 0:
            if callback:
                await callback.answer("⚠️ Костёр погас! Сначала разожги его.", show_alert=True)
            return None, None
        has_flask = (
            game.equipment.get("flask") == "Армейская фляга"
            or game.inventory.get("Армейская фляга", 0) > 0
        )
        if not has_flask:
            if callback:
                await callback.answer("⚠️ Нужна металлическая 🟨 Армейская фляга!", show_alert=True)
            return None, None

        cur_w = (
            int(getattr(game, "flask_water", 0) or 0)
            if game.equipment.get("flask") == "Армейская фляга"
            else int(getattr(game, "army_flask_water", 0) or 0)
        )
        if cur_w >= 20:
            if callback:
                await callback.answer("⚠️ Фляга уже полна (20/20)!", show_alert=True)
            return None, None

        bottles = getattr(game, "rain_bottles", [])
        if not bottles and game.inventory.get("Бутылка дождевой воды", 0) > 0:
            bottles = [4] * game.inventory.get("Бутылка дождевой воды", 1)
            game.rain_bottles = bottles

        if not bottles:
            if callback:
                await callback.answer("⚠️ Нет дождевой воды для кипячения!", show_alert=True)
            return None, None

        if game.equipment.get("flask") != "Армейская фляга":
            if hasattr(game, "unequip_flask_to_inventory"):
                game.unequip_flask_to_inventory()
            else:
                old_flask = game.equipment.get("flask")
                if old_flask:
                    game.inventory[old_flask] = game.inventory.get(old_flask, 0) + 1
            game.inventory["Армейская фляга"] -= 1
            if game.inventory["Армейская фляга"] <= 0:
                del game.inventory["Армейская фляга"]
            game.equipment["flask"] = "Армейская фляга"
            game.flask_water = cur_w

        space = 20 - cur_w
        available = bottles[0]
        transfer = min(space, available)
        new_flask_water = cur_w + transfer
        game.flask_water = new_flask_water
        game.army_flask_water = new_flask_water

        game.campfire_durability = max(0, game.campfire_durability - 1)
        if game.campfire_durability <= 0 and not getattr(game, "is_stove", False):
            game.campfire_active = False

        rem = available - transfer
        if rem <= 0:
            bottles.pop(0)
            game.inventory["Бутылка дождевой воды"] = max(0, game.inventory.get("Бутылка дождевой воды", 1) - 1)
            if game.inventory["Бутылка дождевой воды"] <= 0:
                del game.inventory["Бутылка дождевой воды"]
            game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1
            msg = (
                f"🔥 Ты перелил {transfer} гл. дождевой воды во флягу и прокипятил на углях. "
                f"Во фляге теперь {new_flask_water}/20 чистой воды. Пустая бутылка вернулась в инвентарь."
            )
        else:
            bottles[0] = rem
            msg = (
                f"🔥 Ты перелил {transfer} гл. дождевой воды во флягу до краёв ({new_flask_water}/20) и прокипятил. "
                f"В бутылке осталось {rem}/20 дождевой воды."
            )
        game.add_log(msg)
        text = f"🔥 Прочность костра: {game.campfire_durability}/{game.campfire_max_durability}\n\n{msg}"
        kb = get_campfire_kb(game)
        return text, kb

    return None, None
