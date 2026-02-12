# ГРУППА: Данные событий (EVENTS)
# Описание: Словарь с сюжетными событиями (текст, выборы, эффекты, триггеры). Это база для истории, легко добавлять 20+.

# БЛОК 1.1: EVENTS dict
# Описание: Структура событий (wolf, cat и т.д.). Нужно для запуска и исходов.
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
        'trigger': {'day': 2, 'ap': 3, 'counters': {'berries': 2}}  # Статичный триггер (убрал randint)
    },
    'cat': {
        'text': "Вы нашли кота!",
        'kb': cat_kb,
        'effects': {
            'cat_take': {'karma': +5},
            'cat_leave': {'karma': -5}
        },
        'outcomes': {
            'cat_take': "Вы забрали кота.",
            'cat_leave': "Вы оставили кота."
        },
        'trigger': {'day': 3}  # Пример
    },
    'peek_den': {
        'text': "Вы заглянули в нору...",
        'kb': peek_den_kb,
        'effects': {},  # Добавь
        'outcomes': {},  # Добавь
        'trigger': {'counters': {'sticks': 1}}  # Пример
    },
    # Добавь 20+ событий: {'event20': {'text': '...', 'trigger': {'day':10}}}
}

# ГРУППА: Функции для мыслей и триггеров
# Описание: Получение мыслей, проверка условий для событий. Нужно для динамического сюжета.

# БЛОК 2.1: Получение мысли (get_thought)
# Описание: Словарь мыслей по ключу. Нужно для подсказок в логах (типа о факеле).
def get_thought(key):
    thoughts = {
        'branch_found': "Мысль: А из этой ветки можно сделать факел?",
        # Добавь больше: 'berries_eaten': "Мысль: Переел?"
    }
    return thoughts.get(key, "")

# БЛОК 2.2: Проверка триггера события (trigger_event)
# Описание: Цикл по EVENTS, проверка условий (day, ap, counters). Возвращает имя события если подходит. Нужно для запуска сюжета по триггерам.
def trigger_event(game):
    for event_name, event in EVENTS.items():
        trig = event.get('trigger', {})
        if (trig.get('day') == game.day and
            trig.get('ap') == game.ap and
            all(game.resource_counters.get(k, 0) >= v for k, v in trig.get('counters', {}).items())):
            return event_name
    return None
