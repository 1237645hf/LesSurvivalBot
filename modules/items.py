"""
modules/items.py — Единый реестр предметов (источник правды: еда.txt).
"""

from typing import Dict, Tuple


# Региональные ягоды (тег [Ягоды]) — из еда.txt
BERRY_ITEMS: Tuple[str, ...] = (
    "Лесная ягода",
    "Красная ягода",
    "Фиолетовая ягода",
    "Болотная ягода",
    "Горная ягода",
)

# Региональные грибы (тег [Грибы]) — из еда.txt
MUSHROOM_ITEMS: Tuple[str, ...] = (
    "Лесной гриб",
    "Дикий гриб",
    "Болотный гриб",
    "Пещерный гриб",
    "Горный гриб",
)


ITEMS: Dict[str, Dict] = {
    "Охотничья ловушка": {
        "description": "Простая ловушка из дерева и верёвки.",
        "type": "trap",
        "stackable": True,
    },
    "Кусок коры": {
        "description": "Плоский кусок коры. Посуда для готовки на костре.",
        "type": "tool",
        "stackable": True,
    },
    "Глина": {
        "description": "Липкая глина. Находится в лощине.",
        "type": "resource",
        "stackable": True,
    },
    "Факел": {
        "description": "Свет в тёмном лесу.",
        "type": "tool",
        "effects": {"light": 30},
        "stackable": True,
    },
    "Ветка": {
        "description": "Сухая ветка. Топливо и крафт.",
        "type": "resource",
        "stackable": True,
    },
    "Камень": {
        "description": "Обычный камень.",
        "type": "resource",
        "stackable": True,
    },
    "Мох": {
        "description": "Мягкий мох.",
        "type": "resource",
        "stackable": True,
    },
    "Сухой мох": {
        "description": "Высушенный мох.",
        "type": "resource",
        "stackable": True,
    },
    "Пещерный мох": {
        "description": "Мох из пещеры.",
        "type": "resource",
        "stackable": True,
    },
    "Горный лишайник": {
        "description": "Лишайник с вершины.",
        "type": "resource",
        "stackable": True,
    },
    "Сухая трава": {
        "description": "Пучок сухой травы.",
        "type": "resource",
        "stackable": True,
    },
    "Слизь": {
        "description": "Липкая слизь.",
        "type": "resource",
        "stackable": True,
    },
    "Светящийся гриб": {
        "description": "Редкий светящийся гриб (не для обычной готовки).",
        "type": "resource",
        "effects": {"hunger": 1},
        "stackable": True,
    },
    "Сланец": {
        "description": "Кусок сланца.",
        "type": "resource",
        "stackable": True,
    },
    "Сланцевая пластина": {
        "description": "Обработанная пластина сланца.",
        "type": "resource",
        "stackable": True,
    },
    "Сланцевая заготовка": {
        "description": "Заготовка из сланца.",
        "type": "resource",
        "stackable": True,
    },
    "Кость": {
        "description": "Кость животного.",
        "type": "resource",
        "stackable": True,
    },
    "Кожа": {
        "description": "Шкура/кожа.",
        "type": "resource",
        "stackable": True,
    },
    "Мех": {
        "description": "Клок меха.",
        "type": "resource",
        "stackable": True,
    },
    "Кости": {
        "description": "Несколько костей.",
        "type": "resource",
        "stackable": True,
    },
    "Вода": {
        "description": "Вода. Утоляет жажду (инвентарь).",
        "type": "drink",
        "effects": {"thirst": 4},
        "stackable": True,
    },
    "Сырое мясо": {
        "description": "Свежее мясо с ловушки.",
        "type": "food",
        "effects": {"hunger": 3},
        "stackable": True,
    },
    "Лесная ягода": {
        "description": "Ягода лесного старта.",
        "type": "berry",
        "effects": {"hunger": 2},
        "stackable": True,
    },
    "Красная ягода": {
        "description": "Ягода у ручья.",
        "type": "berry",
        "effects": {"hunger": 2},
        "stackable": True,
    },
    "Фиолетовая ягода": {
        "description": "Ягода лощины.",
        "type": "berry",
        "effects": {"hunger": 2},
        "stackable": True,
    },
    "Болотная ягода": {
        "description": "Ягода яра слизней.",
        "type": "berry",
        "effects": {"hunger": 2},
        "stackable": True,
    },
    "Горная ягода": {
        "description": "Ягода вершины.",
        "type": "berry",
        "effects": {"hunger": 2},
        "stackable": True,
    },
    "Лесной гриб": {
        "description": "Гриб лесного старта.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "stackable": True,
    },
    "Дикий гриб": {
        "description": "Гриб лощины.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "stackable": True,
    },
    "Болотный гриб": {
        "description": "Гриб яра слизней.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "stackable": True,
    },
    "Пещерный гриб": {
        "description": "Гриб мохнатой пещеры.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "stackable": True,
    },
    "Горный гриб": {
        "description": "Гриб вершины святилища.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "stackable": True,
    },
    "Печёные ягоды": {
        "description": "Ягоды, запечённые на коре.",
        "type": "food",
        "effects": {"hunger": 15, "poison": 0},
        "stackable": True,
    },
    "Жареные грибы": {
        "description": "Грибы, обжаренные на коре.",
        "type": "food",
        "effects": {"hunger": 20, "poison": 0},
        "stackable": True,
    },
    "Мясо на коре": {
        "description": "Мясо, зажаренное на коре.",
        "type": "food",
        "effects": {"hunger": 40, "hp": 10},
        "stackable": True,
    },
    "Ягодный отвар": {
        "description": "Отвар из ягод.",
        "type": "drink",
        "effects": {"hunger": 15, "thirst": 25, "hp": 5},
        "stackable": True,
    },
    "Грибная похлёбка": {
        "description": "Похлёбка из грибов.",
        "type": "food",
        "effects": {"hunger": 25, "thirst": 15},
        "stackable": True,
    },
    "Охотничья похлёбка": {
        "description": "Мясо и ягоды.",
        "type": "food",
        "effects": {"hunger": 50, "thirst": 30, "hp": 15},
        "stackable": True,
    },
    "Лесная тушёнка": {
        "description": "Мясо и грибы.",
        "type": "food",
        "effects": {"hunger": 60, "thirst": 20, "hp": 10},
        "stackable": True,
    },
}


def get_item_description(item_name: str) -> str:
    return ITEMS.get(item_name, {}).get("description", "Нет описания")


def get_item_type(item_name: str) -> str:
    return ITEMS.get(item_name, {}).get("type", "misc")


def get_item_effects(item_name: str) -> Dict[str, int]:
    return dict(ITEMS.get(item_name, {}).get("effects", {}))


def get_item_stackable(item_name: str) -> bool:
    return ITEMS.get(item_name, {}).get("stackable", True)


def get_all_items() -> Dict[str, Dict]:
    return ITEMS.copy()


def is_berry(item_name: str) -> bool:
    return item_name in BERRY_ITEMS or get_item_type(item_name) == "berry"


def is_mushroom(item_name: str) -> bool:
    return item_name in MUSHROOM_ITEMS or get_item_type(item_name) == "mushroom"
