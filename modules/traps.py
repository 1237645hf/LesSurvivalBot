"""
modules/traps.py — Модуль для механики «Охотничья ловушка».
Отвечает за логику ловушек: установка, проверка улова, сломанные ловушки.
"""

from typing import Dict, List, Optional
import random


# Таблица животных, которые могут попасться в ловушки
# Ключ — имя животного, значение — описание
HUNTABLE_ANIMALS: Dict[str, str] = {
    "Заяц": "Маленький и быстрый заяц, легко попадается в ловушку.",
    "Волк": "Хищник, ловушка для него — настоящий вызов.",
    "Лиса": "Ловкая лиса, но хитрость не всегда спасает.",
    "Медведь": "Гигант в норке, ловушка для него — испытание.",
    "Рысь": "Котоподобное существо, которое может застрять.",
    "Барсук": "Землекоп, который вырывается из ловушки.",
    "Енот": "Озорной енот, который всё ломает.",
}

# Шанс (в процентах) попадания животного в ловушку на каждой локации
TRAP_CHANCE_BY_LOCATION: Dict[int, int] = {
    1: 5,   # Лесной старт — 5%
    2: 10,  # Ручей — 10%
    3: 15,  # Скромная Лощина — 15% (разблокировка)
    4: 20,  # Лес охотников — 20%
    5: 25,  # Лес слизней — 25%
    6: 30,  # Пещера — 30%
    7: 35,  # Святилище — 35%
}


def get_trap_description(location_id: int = None) -> List[str]:
    """
    Получить описание ловушек для текущей локации.

    Args:
        location_id: ID текущей локации (1–7). Если None — описание для всех.

    Returns:
        Список строк с описанием ловушек.
    """
    descriptions = [
        "На некоторых локациях можно установить **охотничьи ловушки**.",
        "",
        "На каждой локации — не более одной ловушки одновременно.",
        "Ловушка работает только после **сна** (новый день).",
        "Если ловушка сломалась — добыча утеряна, нужно скрафтить новую.",
    ]

    # Добавляем список возможных животных
    if HUNTABLE_ANIMALS:
        animals_list = ", ".join(HUNTABLE_ANIMALS.keys())
        descriptions.append(f"В ловушки могут попадать: {animals_list}.")

    return descriptions


def get_active_traps(game_state) -> Dict[int, Dict]:
    """
    Получить список активных ловушек для всех локаций.

    Args:
        game_state: Объект GameState с полем `traps`.

    Returns:
        Словарь вида {location_id: trap_data}.
    """
    traps = getattr(game_state, "traps", {})
    return {loc_id: trap for loc_id, trap in traps.items() if trap.get("is_active", False)}


def get_trap_for_location(game_state, location_id: int) -> Optional[Dict]:
    """
    Получить данные о ловушке на конкретной локации.

    Args:
        game_state: Объект GameState.
        location_id: ID локации (1–7).

    Returns:
        Словарь trap_data или None, если ловушка не установлена.
    """
    traps = getattr(game_state, "traps", {})
    if location_id in traps:
        trap = traps[location_id]
        if trap.get("is_active", False):
            return trap
    return None


def place_trap(game_state, location_id: int) -> Optional[Dict]:
    """
    Поставить ловушку на локацию.

    Args:
        game_state: Объект GameState.
        location_id: ID локации (1–7).

    Returns:
        Созданный объект ловушки или None, если ловушка уже стоит.
    """
    traps = getattr(game_state, "traps", {})

    # Создаем новую ловушку
    trap = {
        "location_id": location_id,
        "is_active": True,
        "is_broken": False,
        "pending_animal": None,
        "pending_loot": None,
        "placed_day": getattr(game_state, "day", 1),
    }

    # Проверяем, не стоит ли уже ловушка
    if location_id in traps and traps[location_id].get("is_active", False):
        return None  # Ловушка уже стоит

    traps[location_id] = trap
    return trap


def remove_trap(game_state, location_id: int) -> Optional[Dict]:
    """
    Снять ловушку с локации (после того как она сломалась).

    Args:
        game_state: Объект GameState.
        location_id: ID локации.

    Returns:
        Снятая ловушка или None, если её не было.
    """
    traps = getattr(game_state, "traps", {})

    if location_id in traps:
        trap = traps[location_id]
        if trap.get("is_active", False):
            traps.pop(location_id)
            return trap
    return None


def activate_trap(game_state) -> Optional[Dict]:
    """
    Активировать ловушку (после сна — проверка улова).

    Args:
        game_state: Объект GameState.

    Returns:
        Активированная ловушка или None, если не стояла.
    """
    traps = getattr(game_state, "traps", {})

    for loc_id, trap in traps.items():
        if trap.get("is_active", False):
            # Проверяем, не сломалась ли ловушка
            if trap.get("is_broken", False):
                trap["is_active"] = False  # Отключаем, но не удаляем
            elif trap.get("pending_animal") is not None:
                # Животное поймано, проверяем, поймалось ли
                trap["pending_animal"] = None
                trap["pending_loot"] = None

    return traps  # Возвращаем обновлённый словарь


def roll_trap_roll(game_state, location_id: int) -> Optional[Dict]:
    """
    Провести проверку ловушки (шанс поимки животного).

    Args:
        game_state: Объект GameState.
        location_id: ID локации.

    Returns:
        Обновлённая ловушка с пойманным животным или None.
    """
    traps = getattr(game_state, "traps", {})

    if location_id not in traps:
        return None

    trap = traps[location_id]
    if not trap.get("is_active", False):
        return None

    # Шанс ловли на этой локации
    base_chance = TRAP_CHANCE_BY_LOCATION.get(location_id, 10)

    # Случайное число от 1 до 100
    roll = random.randint(1, 100)

    # DEBUG: Print the actual values
    print(f"  DEBUG roll_trap_roll: location_id={location_id}, base_chance={base_chance}, roll={roll}")

    if roll <= base_chance:
        # Животное попало в ловушку
        animal = random.choice(list(HUNTABLE_ANIMALS.keys()))
        trap["pending_animal"] = animal
        trap["pending_loot"] = {
            "item": "Сырое мясо",
            "qty": 1,
        }
        return trap

    return trap


def get_trap_loot(game_state, location_id: int) -> Optional[Dict]:
    """
    Получить лут из ловушки (если животное поймано).

    Args:
        game_state: Объект GameState.
        location_id: ID локации.

    Returns:
        Лут с животным и мясом или None.
    """
    trap = get_trap_for_location(game_state, location_id)

    if trap and trap.get("pending_animal"):
        animal = trap["pending_animal"]
        return {
            "animal": animal,
            "animal_name": HUNTABLE_ANIMALS.get(animal, animal),
            "loot": trap.get("pending_loot", {}),
        }

    return None


def process_trap_rollover(game_state) -> List[Dict]:
    """
    Пройтись по всем ловушкам и проверить улов после сна.

    Args:
        game_state: Объект GameState.

    Returns:
        Список обработанных ловушек с результатами.
    """
    traps = getattr(game_state, "traps", {})
    results = []

    for loc_id, trap in traps.items():
        if trap.get("is_active", False):
            roll = roll_trap_roll(game_state, loc_id)
            results.append({
                "location_id": loc_id,
                "trap": trap,
                "rolled": roll is not None,
                "animal": roll["pending_animal"] if roll else None,
            })

    return results
