"""
modules/cooking.py — Единая система готовки на костре (источник правды: еда.txt).

Рецепты:
  сухая обжарка — вода 0
  простая варка — вода 1–2
  сытная варка — вода 3
Кора (1 шт.) обязательна для всех рецептов.
Теги [Ягоды] / [Грибы] — любой региональный тип из items.
"""

from typing import Any, Dict, List, Optional, Tuple

from modules import items


COOKING_RECIPES: Dict[str, Dict[str, Any]] = {
    "cook_roast_berries": {
        "result": "Печёные ягоды",
        "water_from_flask": 0,
        "needs_bark": True,
        "needs_meat": False,
        "tag": "berry",
        "label": "Печёные ягоды (ягода + кора)",
    },
    "cook_roast_mushrooms": {
        "result": "Жареные грибы",
        "water_from_flask": 0,
        "needs_bark": True,
        "needs_meat": False,
        "tag": "mushroom",
        "label": "Жареные грибы (гриб + кора)",
    },
    "cook_roast_meat": {
        "result": "Мясо на коре",
        "water_from_flask": 0,
        "needs_bark": True,
        "needs_meat": True,
        "tag": None,
        "label": "Мясо на коре (сырое мясо + кора)",
    },
    "cook_berry_stew": {
        "result": "Ягодный отвар",
        "water_from_flask": 1,
        "needs_bark": True,
        "needs_meat": False,
        "tag": "berry",
        "label": "Ягодный отвар (ягода + кора + 1 вода)",
    },
    "cook_mushroom_soup": {
        "result": "Грибная похлёбка",
        "water_from_flask": 2,
        "needs_bark": True,
        "needs_meat": False,
        "tag": "mushroom",
        "label": "Грибная похлёбка (гриб + кора + 2 вода)",
    },
    "cook_hunter_soup": {
        "result": "Охотничья похлёбка",
        "water_from_flask": 3,
        "needs_bark": True,
        "needs_meat": True,
        "tag": "berry",
        "label": "Охотничья похлёбка (мясо + ягода + кора + 3 вода)",
    },
    "cook_forest_stew": {
        "result": "Лесная тушёнка",
        "water_from_flask": 3,
        "needs_bark": True,
        "needs_meat": True,
        "tag": "mushroom",
        "label": "Лесная тушёнка (мясо + гриб + кора + 3 вода)",
    },
}


def get_recipe_for_id(recipe_id: str) -> Optional[Dict[str, Any]]:
    return COOKING_RECIPES.get(recipe_id)


def list_recipes() -> List[Tuple[str, str]]:
    return [(rid, r.get("label", rid)) for rid, r in COOKING_RECIPES.items()]


def _find_tagged_item(inventory: Dict[str, int], tag: str) -> Optional[str]:
    if tag == "berry":
        candidates = items.BERRY_ITEMS
        check = items.is_berry
    elif tag == "mushroom":
        candidates = items.MUSHROOM_ITEMS
        check = items.is_mushroom
    else:
        return None
    for name in candidates:
        if inventory.get(name, 0) > 0:
            return name
    for name, qty in inventory.items():
        if qty > 0 and check(name):
            return name
    return None


def _consume(inventory: Dict[str, int], name: str, amount: int = 1) -> None:
    inventory[name] = inventory.get(name, 0) - amount
    if inventory[name] <= 0:
        del inventory[name]


def cook_item(game: Any, recipe_id: str) -> Tuple[bool, str]:
    recipe = get_recipe_for_id(recipe_id)
    if not recipe:
        return False, f"Рецепт '{recipe_id}' не найден."

    inv = game.inventory
    bark = "Кусок коры"

    if recipe.get("needs_bark", True):
        if inv.get(bark, 0) < 1:
            return False, f"Нужен {bark}."

    water_needed = int(recipe.get("water_from_flask", 0))
    flask = int(getattr(game, "flask_water", 0) or 0)
    has_flask_item = bool(getattr(game, "equipment", {}).get("flask"))
    flask_water_available = flask if has_flask_item else 0

    bottles_in_inv = inv.get("Бутылка воды", 0)
    plain_water = inv.get("Вода", 0)
    total_water = flask_water_available + bottles_in_inv * 20 + plain_water

    if water_needed > 0 and total_water < water_needed:
        return False, f"Недостаточно воды (нужно {water_needed}, доступно {total_water})."

    meat_name = None
    if recipe.get("needs_meat"):
        if inv.get("Сырое мясо", 0) < 1:
            return False, "Нужно Сырое мясо."
        meat_name = "Сырое мясо"

    tagged_name = None
    tag = recipe.get("tag")
    if tag:
        tagged_name = _find_tagged_item(inv, tag)
        if not tagged_name:
            need = "ягоду" if tag == "berry" else "гриб"
            return False, f"Нужна любая {need} (тег [{'Ягоды' if tag == 'berry' else 'Грибы'}])."

    if recipe.get("needs_bark", True):
        _consume(inv, bark, 1)

    if water_needed > 0:
        remaining_needed = water_needed

        # 1. Сначала берём из экипированной фляги/бутылки
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

        # 2. Если нужно ещё — берём из следующей бутылки в инвентаре
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

    if meat_name:
        _consume(inv, meat_name, 1)

    if tagged_name:
        _consume(inv, tagged_name, 1)

    result = recipe["result"]
    inv[result] = inv.get(result, 0) + 1

    used = []
    if meat_name:
        used.append(meat_name)
    if tagged_name:
        used.append(tagged_name)
    used.append(bark)
    if water_needed:
        used.append(f"вода×{water_needed}")

    return True, f"🍳 {result} готово! ({', '.join(used)} → {result})"
