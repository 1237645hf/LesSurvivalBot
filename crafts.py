from collections import Counter

RECIPES = {
    'факел': {
        'ingredients': {'ветка': 1},
        'result': 'факел',
        'description': "Простой факел для освещения.",
        'trigger_thought': "Мысль: Теперь можно экипировать факел?"
    },
    # Добавь больше: 'еда': {'ягоды': 2}, запутывающие как 'fake_tool': {'камень':1} без результата
}

def check_craft(game, recipe_name):
    recipe = RECIPES.get(recipe_name)
    if not recipe:
        return "Нет такого рецепта."
    if all(game.inventory.get(ing, 0) >= count for ing, count in recipe['ingredients'].items()):
        for ing, count in recipe['ingredients'].items():
            game.inventory[ing] -= count
        game.inventory[recipe['result']] += 1
        game.resource_counters[recipe['result']] += 1  # Инкремент
        thought = recipe.get('trigger_thought')
        if thought:
            game.add_log(thought)
        return f"Скрафчено: {recipe['result']}"
    return "Недостаточно ингредиентов."

def use_item(game, item):
    if item not in game.inventory or game.inventory[item] < 1:
        return "Нет такого предмета."
    if item == 'ягоды':
        game.hunger = max(0, game.hunger - 20)
        game.inventory[item] -= 1
        game.resource_counters[item] -= 1  # Декремент если нужно
        # Check trigger после use
        from stories import trigger_event
        event = trigger_event(game)
        if event:
            game.story_state = event
            return EVENTS[event]['text']
        return "Вы съели ягоды. Сытость улучшилась."
    # Добавь больше use: 'грибы' для hp, etc.
    return "Предмет не может быть использован."
