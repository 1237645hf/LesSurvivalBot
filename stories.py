# Сюжетные события, тексты, триггеры, мысли
EVENTS = {
    'wolf': {
        'text': "Вы встретили волка!",
        'kb': wolf_kb,
        'effects': {
            'wolf_flee': {'hp': -10, 'karma': -5},
            'wolf_fight': {'hp': -20, 'karma': +10}
        },
        'outcomes': {
            'wolf_flee': "Вы убежали от волка, но поранились.",
            'wolf_fight': "Вы сразились с волком и победили."
        },
        'trigger': {'day': randint(1, 5), 'ap': 3, 'counters': {'berries': 2}}  # Пример триггера
    },
    'cat': {
        'text': "Вы нашли кота!",
        'kb': cat_kb,
        # ... аналогично для cat_take/leave
    },
    'peek_den': {
        'text': "Вы заглянули в нору...",
        'kb': peek_den_kb,
        # ... эффекты/исходы
    },
    # Добавь 20+ событий сюда как dict (text, kb from keyboards, effects, outcomes, trigger)
}

def get_thought(key):
    thoughts = {
        'branch_found': "Мысль: А из этой ветки можно сделать факел?",
        # Добавь больше мыслей
    }
    return thoughts.get(key, "")

def trigger_event(game):
    for event_name, event in EVENTS.items():
        trig = event.get('trigger', {})
        if (trig.get('day') == game.day and
            trig.get('ap') == game.ap and
            all(game.resource_counters[k] >= v for k, v in trig.get('counters', {}).items())):
            return event_name
    return None
