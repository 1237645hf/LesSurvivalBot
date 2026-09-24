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


CONSUMABLE_EFFECT_KEYS = {"hunger", "thirst", "hp", "poison"}


ITEMS: Dict[str, Dict] = {
    "Спички": {
        "description": "Нужны для розжига и создания факела.",
        "type": "tool",
        "can_use": False,
        "stackable": True,
    },
    "Вилка": {
        "description": "Столовая вилка. Нужна для приготовления блюд.",
        "type": "tool",
        "can_use": False,
        "stackable": True,
    },
    "Сухпай": {
        "description": "Армейский сухпай. Сытный и долгой варки.",
        "type": "food",
        "effects": {"hunger": 30},
        "can_use": True,
        "stackable": True,
    },
    "Еда": {
        "description": "Обобщённая еда. Утоляет голод.",
        "type": "food",
        "effects": {"hunger": 30},
        "can_use": True,
        "stackable": True,
    },
    "Зелье здоровья": {
        "description": "Лечебное зелье. Восстанавливает здоровье.",
        "type": "potion",
        "effects": {"hp": 25},
        "can_use": True,
        "stackable": True,
    },
    "Ягода": {
        "description": "Съедобная ягода. Утоляет лёгкий голод.",
        "type": "berry",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Гриб": {
        "description": "Съедобный гриб. Утоляет лёгкий голод.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Охотничья ловушка": {
        "description": "Простая ловушка из дерева и верёвки.",
        "type": "trap",
        "can_use": True,
        "stackable": True,
    },
    "Кусок коры": {
        "description": "Плоский кусок коры. Посуда для готовки на костре.",
        "type": "tool",
        "can_use": True,
        "stackable": True,
    },
    "Глина": {
        "description": "Липкая глина. Находится в лощине.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Факел": {
        "description": "Свет в тёмном лесу.",
        "type": "tool",
        "effects": {"light": 30},
        "can_use": True,
        "stackable": True,
    },
    "Костёр": {
        "description": "Сложенная кладка для розжига. Используй, чтобы развести огонь на стоянке.",
        "type": "tool",
        "can_use": True,
        "stackable": True,
    },
    # TODO: заглушка — логика открытия рецептов по схеме позже
    "Схема": {
        "description": "Потёртая схема крафта. (Пока заглушка — эффект откроем позже.)",
        "type": "quest",
        "can_use": False,
        "stackable": True,
    },
    "Ветка": {
        "description": "Сухая ветка. Топливо и крафт.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Камень": {
        "description": "Обычный камень.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Мох": {
        "description": "Мягкий мох.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Сухой мох": {
        "description": "Высушенный мох.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Пещерный мох": {
        "description": "Мох из пещеры.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Горный лишайник": {
        "description": "Лишайник с вершины.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Сухая трава": {
        "description": "Пучок сухой травы.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Слизь": {
        "description": "Липкая слизь.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Светящийся гриб": {
        "description": "Редкий светящийся гриб (не для обычной готовки).",
        "type": "resource",
        "effects": {"hunger": 1},
        "can_use": True,
        "stackable": True,
    },
    "Сланец": {
        "description": "Кусок сланца.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Сланцевая пластина": {
        "description": "Обработанная пластина сланца.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Сланцевая заготовка": {
        "description": "Заготовка из сланца.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Кость": {
        "description": "Кость животного.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Кожа": {
        "description": "Шкура/кожа.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Мех": {
        "description": "Клок меха.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Кости": {
        "description": "Несколько костей.",
        "type": "resource",
        "can_use": False,
        "stackable": True,
    },
    "Вода": {
        "description": "Вода. Утоляет жажду (инвентарь).",
        "type": "drink",
        "effects": {"thirst": 4},
        "can_use": True,
        "stackable": True,
    },
    "Бутылка воды": {
        "description": "Стеклянная бутылка чистой воды (20 глотков). Можно экипировать в слот фляги или выпить.",
        "type": "drink",
        "effects": {"thirst": 15},
        "can_use": True,
        "stackable": True,
    },
    "Пустая бутылка": {
        "description": "Пустая стеклянная бутылка. Можно наполнить водой у ручья или во время дождя.",
        "type": "tool",
        "can_use": False,
        "stackable": True,
    },
    "Сырое мясо": {
        "description": "Свежее мясо с ловушки.",
        "type": "food",
        "effects": {"hunger": 3},
        "can_use": True,
        "stackable": True,
    },
    "Лесная ягода": {
        "description": "Ягода лесного старта.",
        "type": "berry",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Красная ягода": {
        "description": "Ягода у ручья.",
        "type": "berry",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Фиолетовая ягода": {
        "description": "Ягода лощины.",
        "type": "berry",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Болотная ягода": {
        "description": "Ягода яра слизней.",
        "type": "berry",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Горная ягода": {
        "description": "Ягода вершины.",
        "type": "berry",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Лесной гриб": {
        "description": "Гриб лесного старта.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Дикий гриб": {
        "description": "Гриб лощины.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Болотный гриб": {
        "description": "Гриб яра слизней.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Пещерный гриб": {
        "description": "Гриб мохнатой пещеры.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Горный гриб": {
        "description": "Гриб вершины святилища.",
        "type": "mushroom",
        "effects": {"hunger": 2},
        "can_use": True,
        "stackable": True,
    },
    "Печёные ягоды": {
        "description": "Ягоды, запечённые на коре.",
        "type": "food",
        "effects": {"hunger": 15, "poison": 0},
        "can_use": True,
        "stackable": True,
    },
    "Жареные грибы": {
        "description": "Грибы, обжаренные на коре.",
        "type": "food",
        "effects": {"hunger": 20, "poison": 0},
        "can_use": True,
        "stackable": True,
    },
    "Мясо на коре": {
        "description": "Мясо, зажаренное на коре.",
        "type": "food",
        "effects": {"hunger": 40, "hp": 10},
        "can_use": True,
        "stackable": True,
    },
    "Ягодный отвар": {
        "description": "Отвар из ягод.",
        "type": "drink",
        "effects": {"hunger": 15, "thirst": 25, "hp": 5},
        "can_use": True,
        "stackable": True,
    },
    "Грибная похлёбка": {
        "description": "Похлёбка из грибов.",
        "type": "food",
        "effects": {"hunger": 25, "thirst": 15},
        "can_use": True,
        "stackable": True,
    },
    "Охотничья похлёбка": {
        "description": "Мясо и ягоды.",
        "type": "food",
        "effects": {"hunger": 50, "thirst": 30, "hp": 15},
        "can_use": True,
        "stackable": True,
    },
    "Лесная тушёнка": {
        "description": "Мясо и грибы.",
        "type": "food",
        "effects": {"hunger": 60, "thirst": 20, "hp": 10},
        "can_use": True,
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


def _item_can_use(item_name: str) -> bool:
    return ITEMS.get(item_name, {}).get("can_use", True)


def _has_consumable_effects(item_name: str) -> bool:
    effects = ITEMS.get(item_name, {}).get("effects", {})
    return any(k in CONSUMABLE_EFFECT_KEYS for k in effects)


def _is_consumable_type(item_name: str) -> bool:
    return get_item_type(item_name) in {"food", "drink", "berry", "mushroom", "potion"}


def is_item_consumable(item_name: str) -> bool:
    """
    Определяет, должен ли предмет попадать в меню «Использовать» (расходники).

    Условие: флаг can_use=True И (имеет эффекты характеристик ИЛИ тип — расходный).
    """
    if not _item_can_use(item_name):
        return False
    if _has_consumable_effects(item_name):
        return True
    if _is_consumable_type(item_name):
        return True
    return False
