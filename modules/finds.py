"""
modules/finds.py — Лут исследования по локациям (источник правды: еда.txt).

Основной бросок + независимый доп. бросок (кора / глина на L3).
"""

from typing import Dict, List, Any
import random


LOCATION_FINDS: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"item": "Лесная ягода", "chance": 15},
        {"item": "Лесной гриб", "chance": 15},
        {"item": "Мох", "chance": 20},
        {"item": "Ветка", "chance": 35},
        {"item": "Камень", "chance": 15},
    ],
    2: [
        {"item": "Красная ягода", "chance": 25},
        {"item": "Ветка", "chance": 40},
        {"item": "Камень", "chance": 25},
        {"item": "Сланцевая пластина", "chance": 10},
    ],
    3: [
        {"item": "Фиолетовая ягода", "chance": 15},
        {"item": "Дикий гриб", "chance": 15},
        {"item": "Сухой мох", "chance": 15},
        {"item": "Ветка", "chance": 25},
        {"item": "Сланец", "chance": 30},
    ],
    4: [
        {"item": "Лесная ягода", "chance": 10},
        {"item": "Лесной гриб", "chance": 10},
        {"item": "Сухая трава", "chance": 15},
        {"item": "Ветка", "chance": 40},
        {"item": "Кость", "chance": 15},
        {"item": "Кожа", "chance": 10},
    ],
    5: [
        {"item": "Болотная ягода", "chance": 15},
        {"item": "Болотный гриб", "chance": 15},
        {"item": "Светящийся гриб", "chance": 5},
        {"item": "Слизь", "chance": 35},
        {"item": "Ветка", "chance": 30},
    ],
    6: [
        {"item": "Пещерный гриб", "chance": 20},
        {"item": "Пещерный мох", "chance": 20},
        {"item": "Камень", "chance": 25},
        {"item": "Ветка", "chance": 35},
    ],
    7: [
        {"item": "Горная ягода", "chance": 20},
        {"item": "Горный гриб", "chance": 20},
        {"item": "Горный лишайник", "chance": 20},
        {"item": "Камень", "chance": 15},
        {"item": "Ветка", "chance": 25},
    ],
}

BONUS_FINDS: Dict[int, List[Dict[str, Any]]] = {
    1: [{"item": "Кусок коры", "chance": 30}],
    2: [{"item": "Кусок коры", "chance": 30}],
    3: [
        {"item": "Глина", "chance": 40},
        {"item": "Кусок коры", "chance": 30},
    ],
    4: [{"item": "Кусок коры", "chance": 40}],
    5: [{"item": "Кусок коры", "chance": 30}],
    6: [],
    7: [],
}


STICK_NAMES = {"Ветка", "Палка", "Палки"}


def _roll_single_item(table: List[Dict[str, Any]]) -> str:
    """Выбрать ровно 1 предмет из таблицы по процентным шансам."""
    if not table:
        return "Ветка"
    total_chance = sum(int(entry.get("chance", 0)) for entry in table)
    roll = random.randint(1, max(100, total_chance))
    acc = 0
    for entry in table:
        acc += int(entry.get("chance", 0))
        if roll <= acc:
            return entry["item"]
    return table[-1]["item"]


def _roll_table(table: List[Dict[str, Any]]) -> List[str]:
    if not table:
        return []
    roll = random.randint(1, 100)
    acc = 0
    for entry in table:
        acc += int(entry.get("chance", 0))
        if roll <= acc:
            item = entry["item"]
            if item in STICK_NAMES:
                return [item] * random.randint(1, 3)
            return [item]
    last = table[-1]["item"]
    if last in STICK_NAMES:
        return [last] * random.randint(1, 3)
    return [last]


def _roll_bonus(table: List[Dict[str, Any]]) -> List[str]:
    found = []
    for entry in table:
        if random.randint(1, 100) <= int(entry.get("chance", 0)):
            item = entry["item"]
            if item in STICK_NAMES:
                found.extend([item] * random.randint(1, 3))
            else:
                found.append(item)
    return found



def location_id_from_game(game) -> int:
    idx = getattr(game, "location_index", None)
    if isinstance(idx, int) and 0 <= idx <= 6:
        return idx + 1
    cur = str(getattr(game, "current_location", "") or "")
    mapping = {
        "Лесной": 1, "Ручей": 2, "Лощин": 3, "Просека": 4, "Охотник": 4,
        "Яр": 5, "Слизн": 5, "Пещер": 6, "Мохнат": 6, "Святилищ": 7, "Вершин": 7,
    }
    for key, lid in mapping.items():
        if key in cur:
            return lid
    return 1


def roll_find(location_id: int) -> List[str]:
    """3 броска при исследовании:
    Бросок A: таблица локации (1 предмет по шансам).
    Бросок B: второй независимый бросок по таблице локации (всегда делается).
    Бросок C: ~30% шанс на ветки/палки, количество 1, 2 или 3 с равной вероятностью.
    + Бонусный бросок (кора, глина).
    """
    location_id = int(location_id)
    table = LOCATION_FINDS.get(location_id, LOCATION_FINDS[1])
    found: List[str] = []

    # Бросок A
    item_a = _roll_single_item(table)
    if item_a:
        found.append(item_a)

    # Бросок B
    item_b = _roll_single_item(table)
    if item_b:
        found.append(item_b)

    # Бросок C (~30% шанс на палки, 1..3 шт.)
    if random.randint(1, 100) <= 30:
        count = random.choice([1, 2, 3])
        found.extend(["Ветка"] * count)

    # Бонусный бросок
    bonus = _roll_bonus(BONUS_FINDS.get(location_id, []))
    if bonus:
        found.extend(bonus)

    return found


def apply_finds_to_inventory(game, found: List[str]) -> str:
    if not found:
        return "Ничего не нашёл."
    inv = game.inventory
    counts: Dict[str, int] = {}
    for item in found:
        counts[item] = counts.get(item, 0) + 1
        inv[item] = inv.get(item, 0) + 1
    parts = []
    for item, qty in counts.items():
        if qty > 1:
            parts.append(f"{item} ×{qty}")
        else:
            parts.append(item)
    return "Нашёл: " + ", ".join(parts)

