# ГРУППА: Импорты
# Описание: Импорт для работы с коллекциями и сторис. Нужно для рецептов и триггеров.

# БЛОК 1.1: Стандартные импорты
# Описание: Counter для инвентаря/счётчиков.
from collections import Counter

# БЛОК 1.2: Импорты из stories
# Описание: Для триггеров после использования/крафта. Добавлено для фикса.
from stories import EVENTS, trigger_event

# ГРУППА: Данные рецептов
# Описание: Словарь с рецептами. Это база для крафта, легко добавлять новые.

# БЛОК 2.1: RECIPES dict
# Описание: Рецепты (ингредиенты, результат, описание). Нужно для проверки и создания предметов.
RECIPES = {
    'факел': {
        'ingredients': {'ветка': 1},
        'result': 'факел',
        'description': "Простой факел для освещения.",
        'trigger_thought': "Мысль: Теперь можно экипировать факел?"
    },
    # Добавь: 'еда': {'ingredients': {'ягоды': 2}, 'result': 'еда'},
    # Запутывающие: 'fake': {'ingredients': {'камень':1}, 'result': None} — без результата
}

# ГРУППА: Функции крафта и использования
# Описание: Логика проверки/создания, использования предметов с триггерами.

# БЛОК 3.1: Проверка и крафт (check_craft)
# Описание: Проверка ингредиентов, вычитание, добавление результата, мысль. Нужно для механики крафта.
def check_craft(game, recipe_name):
    recipe = RECIPES.get(recipe_name)
    if not recipe:
        return "Нет такого рецепта."
    if all(game.inventory.get(ing, 0) >= count for ing, count in recipe['ingredients'].items()):
        for ing, count in recipe['ingredients'].items():
            game.inventory[ing] -= count
        game.inventory[recipe['result']] += 1
        game.resource_counters[recipe['result']] += 1  # Инкремент счётчика
        thought = recipe.get('trigger_thought')
        if thought:
            game.add_log(thought)
        return f"Скрафчено: {recipe['result']}"
    return "Недостаточно ингредиентов."

# БЛОК 3.2: Использование предмета (use_item)
# Описание: Логика для конкретных предметов (ягоды — сытость), декремент, триггер. Нужно для взаимодействия с инвентарём.
def use_item(game, item):
    if item not in game.inventory or game.inventory[item] < 1:
        return "Нет такого предмета."
    if item == 'ягоды':
        game.hunger = max(0, game.hunger - 20)
        game.inventory[item] -= 1
        game.resource_counters[item] -= 1  # Декремент если нужно
        # Проверка триггера после use
        event = trigger_event(game)
        if event:
            game.story_state = event
            return EVENTS[event]['text']
        return "Вы съели ягоды. Сытость улучшилась."
    # Добавь: 'грибы' для hp, etc.
    return "Предмет не может быть использован."
