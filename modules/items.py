"""
modules/items.py — Модуль для описания предметов (инвентарь).
Отвечает за свойства предметов: еда, экипировка, ловушки, лут из ловушек.
"""

from typing import Dict, Optional, Tuple


# Таблицы тегов для ягод и грибов (для гибкого подбора ингредиентов в рецептах)
BERRY_ITEMS: Tuple[str, ...] = (
    "Красная ягода",
    "Белая ягода",
    "Золотая ягода",
    "Синяя ягода",
    "Тёмная ягода",
)

MUSHROOM_ITEMS: Tuple[str, ...] = (
    "Лисичка",
    "Подберёзник",
    "Мухомор",
    "Печёнка",
    "Моховик",
)


# Таблица предметов с их описаниями и эффектами
ITEMS: Dict[str, Dict[str, any]] = {
    # Ловушки
    "Охотничья ловушка": {
        "description": "Простая ловушка из дерева и верёвки. Ожидает, что в неё попадёт животное.",
        "type": "trap",
        "stackable": True,
    },
    # Кора для костра
    "Кусок коры": {
        "description": "Плоский кусок коры. Идеальная подставка для жарки.",
        "type": "tool",
        "stackable": True,
    },
    # Вода во фляге
    "Вода": {
        "description": "Простая вода из ручья. Утоляет жажду.",
        "type": "drink",
        "effects": {
            "thirst": 4,
        },
        "stackable": True,
    },
    # Мясо из ловушек
    "Сырое мясо": {
        "description": "Свежее мясо от пойманного животного. Отлично восстанавливает здоровье.",
        "type": "food",
        "effects": {
            "hunger": 3,  # Насыщает на 3 единицы
        },
        "stackable": True,
    },
    # Еда из базового набора
    "Ягода": {
        "description": "Сладкая ягода из леса. Быстро утоляет голод.",
        "type": "food",
        "effects": {
            "hunger": 2,
        },
        "stackable": True,
    },
    "Ветчина": {
        "description": "Высушенное мясо, которое хранится долго.",
        "type": "food",
        "effects": {
            "hunger": 5,
        },
        "stackable": True,
    },
    # Вода
    "Вода": {
        "description": "Простая вода из ручья. Утоляет жажду.",
        "type": "drink",
        "effects": {
            "thirst": 4,
        },
        "stackable": True,
    },
    # Экипировка
    "Кожаный жилет": {
        "description": "Лёгкая защита для туловища от когтей и зубов.",
        "type": "torso",
        "effects": {
            "armor": 10,
        },
        "stackable": False,
    },
    "Меховой капюшон": {
        "description": "Шерсть животного, защищающая голову от холода и укусов.",
        "type": "head",
        "effects": {
            "armor": 8,
        },
        "stackable": False,
    },
    # Инструменты
    "Факел": {
        "description": "Свет в тёмном лесу. Отпугивает некоторых существ.",
        "type": "tool",
        "effects": {
            "light": 30,  # Минуты света
        },
        "stackable": True,
    },
    # Приготовленные блюда
    "Печёные ягоды": {
        "description": "Ягоды, запечённые на костре. Универсальный перекус.",
        "type": "food",
        "effects": {
            "hunger": 15,
            "poison": 0,  # Нет отравления
        },
        "stackable": True,
    },
    "Жареные грибы": {
        "description": "Грибы, обжаренные на коры. Сытный обед.",
        "type": "food",
        "effects": {
            "hunger": 20,
            "poison": 0,
        },
        "stackable": True,
    },
    "Мясо на коре": {
        "description": "Мясо, зажаренное на коре. Отличное питание.",
        "type": "food",
        "effects": {
            "hunger": 40,
            "hp": 10,
        },
        "stackable": True,
    },
    "Ягодный отвар": {
        "description": "Настой из ягод. Восстанавливает жажду и здоровье.",
        "type": "drink",
        "effects": {
            "hunger": 15,
            "thirst": 25,
            "hp": 5,
        },
        "stackable": True,
    },
    "Грибная похлёбка": {
        "description": "Наваристый суп из грибов. Сытно и вкусно.",
        "type": "food",
        "effects": {
            "hunger": 25,
            "thirst": 15,
        },
        "stackable": True,
    },
    "Охотничья похлёбка": {
        "description": "Суп из мяса и ягод. Кухня настоящего охотника.",
        "type": "food",
        "effects": {
            "hunger": 50,
            "thirst": 30,
            "hp": 15,
        },
        "stackable": True,
    },
    "Лесная тушёнка": {
        "description": "Суп из мяса и грибов. Идеально для выживания.",
        "type": "food",
        "effects": {
            "hunger": 60,
            "thirst": 20,
            "hp": 10,
        },
        "stackable": True,
    },
    # Ягоды для тага
    "Красная ягода": {
        "description": "Ярко-красная ягода. Отличается от других.",
        "type": "berry",
        "effects": {
            "hunger": 2,
        },
        "stackable": True,
    },
    "Зелёная ягода": {
        "description": "Необычная зелёная ягода. Свирепая!",
        "type": "berry",
        "effects": {
            "hunger": 2,
        },
        "stackable": True,
    },
    "Жёлтая ягода": {
        "description": "Ярко-жёлтая ягода. Яркая и сладкая.",
        "type": "berry",
        "effects": {
            "hunger": 2,
        },
        "stackable": True,
    },
    "Белая ягода": {
        "description": "Редкая белая ягода. Как снег в лесу.",
        "type": "berry",
        "effects": {
            "hunger": 2,
        },
        "stackable": True,
    },
    "Тёмная ягода": {
        "description": "Глубоко-фиолетовая ягода. Ночная красавица.",
        "type": "berry",
        "effects": {
            "hunger": 2,
        },
        "stackable": True,
    },
    # Грибы для тага
    "Лисичка": {
        "description": "Изумрудно-жёлтая лисичка. Грибная классика.",
        "type": "mushroom",
        "effects": {
            "hunger": 2,
        },
        "stackable": True,
    },
    "Подберёзник": {
        "description": "Белый гриб с коричневой шляпкой. Сочный.",
        "type": "mushroom",
        "effects": {
            "hunger": 2,
        },
        "stackable": True,
    },
    "Мухомор": {
        "description": "Ядовитый красный гриб. Красивый, но опасный.",
        "type": "mushroom",
        "effects": {
            "hunger": 2,
            "poison": 5,
        },
        "stackable": True,
    },
    "Печёнка": {
        "description": "Грибная печёнка. Неоново-зелёная.",
        "type": "mushroom",
        "effects": {
            "hunger": 2,
        },
        "stackable": True,
    },
    "Моховик": {
        "description": "Тёмно-фиолетовый гриб. Редкий экземпляр.",
        "type": "mushroom",
        "effects": {
            "hunger": 2,
        },
        "stackable": True,
    },
}


def get_item_description(item_name: str) -> str:
    """
    Получить описание предмета по его названию.

    Args:
        item_name: Название предмета (например, "Охотничья ловушка").

    Returns:
        Описание или "Нет описания" если предмета нет в таблице.
    """
    item = ITEMS.get(item_name, {})
    return item.get("description", "Нет описания")


def get_item_type(item_name: str) -> str:
    """
    Получить тип предмета (для сортировки инвентаря).

    Args:
        item_name: Название предмета.

    Returns:
        Тип предмета: "trap", "food", "drink", "torso", "head", "tool" и т.д.
    """
    item = ITEMS.get(item_name, {})
    return item.get("type", "misc")


def get_item_effects(item_name: str) -> Dict[str, int]:
    """
    Получить эффекты предмета (бонусы к голоду, жажде, защите).

    Args:
        item_name: Название предмета.

    Returns:
        Словарь эффектов: {"hunger": 3, "thirst": 4} или пустой словарь.
    """
    item = ITEMS.get(item_name, {})
    return item.get("effects", {})


def get_item_stackable(item_name: str) -> bool:
    """
    Проверить, можно ли складировать предмет.

    Args:
        item_name: Название предмета.

    Returns:
        True если предмет складированный, False — если уникальный.
    """
    item = ITEMS.get(item_name, {})
    return item.get("stackable", True)


def get_all_items() -> Dict[str, Dict]:
    """
    Получить все предметы из таблицы.

    Returns:
        Копия словаря ITEMS.
    """
    return ITEMS.copy()
