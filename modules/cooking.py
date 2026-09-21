"""
modules/cooking.py — Модуль для кулинарных рецептов на костре.
Обрабатывает жарку/варку предметов на камине.
"""

from typing import Dict, Any, Tuple, Optional


# Таблица рецептов (7 блюд)
COOKING_RECIPES: Dict[str, Dict[str, Any]] = {
    # Печёные ягоды (берёмы)
    "cook_berries": {
        "result": "Печёные ягоды",
        "ingredients": ["Кусок коры", "Красная ягода", "Белая ягода", "Жёлтая ягода", "Белая ягода", "Тёмная ягода"],
        "needs_bark": True,
        "water_from_flask": 10,  # 10 делений воды из фляги
    },
    # Жареные грибы (мухоморы)
    "cook_mushroom": {
        "result": "Жареные грибы",
        "ingredients": ["Кусок коры", "Лисичка", "Подберёзник", "Мухомор", "Печёнка", "Моховик"],
        "needs_bark": True,
        "water_from_flask": 10,
    },
    # Мясо на коре
    "cook_meat": {
        "result": "Мясо на коре",
        "ingredients": ["Кусок коры", "Сырое мясо"],
        "needs_bark": True,
        "water_from_flask": 10,
    },
    # Ягодный отвар
    "cook_berry_stew": {
        "result": "Ягодный отвар",
        "ingredients": ["Кусок коры", "Красная ягода", "Белая ягода", "Жёлтая ягода", "Белая ягода", "Тёмная ягода"],
        "needs_bark": True,
        "water_from_flask": 10,
    },
    # Грибная похлёбка
    "cook_mushroom_soup": {
        "result": "Грибная похлёбка",
        "ingredients": ["Кусок коры", "Лисичка", "Подберёзник", "Мухомор", "Печёнка", "Моховик"],
        "needs_bark": True,
        "water_from_flask": 10,
    },
    # Охотничья похлёбка
    "cook_hunter_soup": {
        "result": "Охотничья похлёбка",
        "ingredients": ["Кусок коры", "Сырое мясо", "Красная ягода", "Белая ягода", "Жёлтая ягода", "Белая ягода", "Тёмная ягода"],
        "needs_bark": True,
        "water_from_flask": 10,
    },
    # Лесная тушёнка
    "cook_forest_stew": {
        "result": "Лесная тушёнка",
        "ingredients": ["Кусок коры", "Сырое мясо", "Лисичка", "Подберёзник", "Мухомор", "Печёнка", "Моховик"],
        "needs_bark": True,
        "water_from_flask": 10,
    },
}


def get_recipe_for_id(recipe_id: str) -> Optional[Dict[str, Any]]:
    """Получить рецепт по ID."""
    return COOKING_RECIPES.get(recipe_id)


def get_item_name_from_item_dict(item_dict: Dict[str, Any]) -> str:
    """Получить имя предмета из словаря (для отображения)."""
    return item_dict.get("description", item_dict.get("name", "Неизвестный предмет"))


def get_item_type(item_name: str) -> Optional[str]:
    """Получить тип предмета по имени (для проверки тегов)."""
    from modules import items
    return items.ITEMS.get(item_name, {}).get("type")


def get_berry_items() -> Tuple[str, ...]:
    """Получить кортеж ягод из items.py."""
    from modules import items
    return items.BERRY_ITEMS


def get_mushroom_items() -> Tuple[str, ...]:
    """Получить кортеж грибов из items.py."""
    from modules import items
    return items.MUSHROOM_ITEMS


def has_flask_water(game: Any) -> bool:
    """Проверить, есть ли во фляге вода."""
    return game.flask_water > 0


def get_flask_water_amount(game: Any) -> int:
    """Получить количество делений воды во фляге."""
    return game.flask_water


def cook_item(game: Any, recipe_id: str) -> Tuple[bool, str]:
    """
    Приготовить блюдо на костре.

    Args:
        game: Объект Game из game_state.py
        recipe_id: ID рецепта из COOKING_RECIPES (например, "cook_berries")

    Returns:
        (ok: bool, message: str) — результат и сообщение
    """
    recipe = get_recipe_for_id(recipe_id)
    if not recipe:
        return False, f"Рецепт '{recipe_id}' не найден!"

    bark_name = "Кусок коры"
    bark_amount = 1  # Сколько коры нужно
    needed_bark = bark_amount

    # 1) Проверка коры
    bark_in_inventory = game.inventory.get(bark_name, 0)
    if bark_in_inventory < needed_bark:
        return False, f"Нужно {needed_bark} {bark_name}({bark_name}), а есть {bark_in_inventory}!"

    # 2) Проверка воды во фляге (если в рецепте указано)
    water_needed = recipe.get("water_from_flask", 10)
    if water_needed > 0:
        flask_water = get_flask_water_amount(game)
        if flask_water < water_needed:
            return False, f"Нужно {water_needed} делений воды во фляге, а есть {flask_water}!"

    # 3) Проверка ингредиентов (берём первые N предметов из списка)
    # Берём первые 6 ингредиентов (или меньше, если их меньше)
    ingredient_names = recipe.get("ingredients", [])
    num_ingredients = len(ingredient_names)
    if num_ingredients > 6:
        num_ingredients = 6

    # Проверяем каждый ингредиент
    for i in range(num_ingredients):
        ing_name = ingredient_names[i]
        ing_in_inventory = game.inventory.get(ing_name, 0)

        if ing_in_inventory < 1:
            # Если ингредиент не найден — возвращаем его имя из описания
            return False, f"Нужен {ing_name}, а есть {ing_in_inventory}!"

    # 4) Списываем кору
    game.inventory[bark_name] -= bark_amount
    if game.inventory[bark_name] <= 0:
        del game.inventory[bark_name]

    # 5) Списываем воду (если нужно)
    if water_needed > 0:
        game.flask_water -= water_needed
        if game.flask_water <= 0:
            del game.flask_water

    # 6) Списываем ингредиенты
    for i in range(num_ingredients):
        ing_name = ingredient_names[i]
        game.inventory[ing_name] -= 1
        if game.inventory[ing_name] <= 0:
            del game.inventory[ing_name]

    # 7) Добавляем готовое блюдо
    result_item = recipe["result"]
    game.inventory[result_item] = game.inventory.get(result_item, 0) + 1

    # Формируем сообщение
    message = f"🍳 {result_item} готово!"
    if num_ingredients < 6:
        message += f" ({', '.join(ingredient_names[:num_ingredients])} → {result_item})"

    return True, message