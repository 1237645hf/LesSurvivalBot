"""
modules/finds.py — Лут исследования по локациям (источник правды: еда.txt).

Основной бросок + независимый доп. бросок (кора / глина на L3).
"""

from typing import Dict, List, Any
import random


LOCATION_FINDS: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"item": "Лесная ягода", "chance": 20},
        {"item": "Лесной гриб", "chance": 20},
        {"item": "Мох", "chance": 25},
        {"item": "Ветка", "chance": 20},
        {"item": "Камень", "chance": 15},
    ],
    2: [
        {"item": "Красная ягода", "chance": 30},
        {"item": "Ветка", "chance": 35},
        {"item": "Камень", "chance": 25},
        {"item": "Сланцевая пластина", "chance": 10},
    ],
    3: [
        {"item": "Фиолетовая ягода", "chance": 15},
        {"item": "Дикий гриб", "chance": 15},
        {"item": "Сухой мох", "chance": 15},
        {"item": "Сланец", "chance": 40},
        {"item": "Сланцевая заготовка", "chance": 15},
    ],
    4: [
        {"item": "Лесная ягода", "chance": 15},
        {"item": "Лесной гриб", "chance": 15},
        {"item": "Сухая трава", "chance": 20},
        {"item": "Ветка", "chance": 30},
        {"item": "Кость", "chance": 10},
        {"item": "Кожа", "chance": 10},
    ],
    5: [
        {"item": "Болотная ягода", "chance": 20},
        {"item": "Болотный гриб", "chance": 20},
        {"item": "Светящийся гриб", "chance": 5},
        {"item": "Слизь", "chance": 35},
        {"item": "Ветка", "chance": 20},
    ],
    6: [
        {"item": "Пещерный гриб", "chance": 25},
        {"item": "Пещерный мох", "chance": 20},
        {"item": "Камень", "chance": 30},
        {"item": "Ветка", "chance": 25},
    ],
    7: [
        {"item": "Горная ягода", "chance": 25},
        {"item": "Горный гриб", "chance": 25},
        {"item": "Горный лишайник", "chance": 25},
        {"item": "Камень", "chance": 25},
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


def _roll_table(table: List[Dict[str, Any]]) -> List[str]:
    if not table:
        return []
    roll = random.randint(1, 100)
    acc = 0
    for entry in table:
        acc += int(entry.get("chance", 0))
        if roll <= acc:
            return [entry["item"]]
    return [table[-1]["item"]]


def _roll_bonus(table: List[Dict[str, Any]]) -> List[str]:
    found = []
    for entry in table:
        if random.randint(1, 100) <= int(entry.get("chance", 0)):
            found.append(entry["item"])
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
    location_id = int(location_id)
    main = _roll_table(LOCATION_FINDS.get(location_id, LOCATION_FINDS[1]))
    bonus = _roll_bonus(BONUS_FINDS.get(location_id, []))
    return main + bonus


def apply_finds_to_inventory(game, found: List[str]) -> str:
    if not found:
        return "Ничего не нашёл."
    inv = game.inventory
    for item in found:
        inv[item] = inv.get(item, 0) + 1
    return "Нашёл: " + ", ".join(found)
