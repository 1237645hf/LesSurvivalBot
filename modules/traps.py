"""
modules/traps.py — Охотничьи ловушки (источник правды: еда.txt).

- Разблокировка с L4; после открытия — установка на L1–L7.
- 1 ловушка на локацию.
- Утро (после сна): 40% ломка / 60% успех + лут из TRAP_LOOT_TABLE.
"""

from typing import Dict, List, Optional, Any
import random


TRAP_UNLOCK_LOCATION = 4

TRAP_LOOT_TABLE: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"name": "Заяц", "chance": 100, "loot": {"Сырое мясо": 1}},
    ],
    2: [
        {"name": "Ящерица", "chance": 60, "loot": {"Сырое мясо": 1}},
        {"name": "Камышовый козёл", "chance": 40, "loot": {"Сырое мясо": 2, "Кожа": 1, "Кость": 1}},
    ],
    3: [
        {"name": "Пещерный суслик", "chance": 70, "loot": {"Сырое мясо": 1}},
        {"name": "Барсук", "chance": 30, "loot": {"Сырое мясо": 2, "Кожа": 1}},
    ],
    4: [
        {"name": "Дикий кабан", "chance": 50, "loot": {"Сырое мясо": 4, "Кожа": 2, "Кость": 2}},
        {"name": "Молодой олень", "chance": 50, "loot": {"Сырое мясо": 5, "Кожа": 3, "Кость": 2, "Мех": 3}},
    ],
    5: [
        {"name": "Аппетитный слизень", "chance": 60, "loot": {"Сырое мясо": 1, "Слизь": 2}},
        {"name": "Болотная улитка", "chance": 40, "loot": {"Сырое мясо": 1, "Слизь": 1}},
    ],
    6: [
        {"name": "Пещерный суслик", "chance": 60, "loot": {"Сырое мясо": 1}},
        {"name": "Горный баран", "chance": 40, "loot": {"Сырое мясо": 3, "Мех": 2, "Кость": 2}},
    ],
    7: [
        {"name": "Горный орёл", "chance": 60, "loot": {"Сырое мясо": 2}},
        {"name": "Снежный песец", "chance": 40, "loot": {"Сырое мясо": 1, "Мех": 1}},
    ],
}

HUNTABLE_ANIMALS: Dict[str, str] = {}
for entries in TRAP_LOOT_TABLE.values():
    for e in entries:
        HUNTABLE_ANIMALS[e["name"]] = e["name"]

TRAP_CHANCE_BY_LOCATION: Dict[int, int] = {i: 60 for i in range(1, 8)}


def traps_unlocked(game_state) -> bool:
    flags = getattr(game_state, "story_flags", {}) or {}
    if flags.get("traps_unlocked"):
        return True
    loc = int(getattr(game_state, "location_index", 0) or 0)
    if loc >= 3:
        return True
    cur = str(getattr(game_state, "current_location", "") or "")
    if "Охотник" in cur or "Просека" in cur:
        return True
    return False


def mark_traps_unlocked(game_state) -> None:
    if not hasattr(game_state, "story_flags") or game_state.story_flags is None:
        game_state.story_flags = {}
    game_state.story_flags["traps_unlocked"] = True


def get_trap_description(location_id: int = None) -> List[str]:
    return [
        "Охотничьи ловушки доступны с **Просеки Охотников (L4)**.",
        "После открытия — не более одной ловушки на локацию (L1–L7).",
        "Проверка улова — после **сна** (новый день).",
        "40% — ловушка пуста, 20% — ломается, 40% — добыча по таблице локации.",
    ]


def get_active_traps(game_state) -> Dict[int, Dict]:
    traps = getattr(game_state, "traps", {}) or {}
    return {lid: t for lid, t in traps.items() if t.get("is_active")}


def get_trap_for_location(game_state, location_id: int) -> Optional[Dict]:
    traps = getattr(game_state, "traps", {}) or {}
    t = traps.get(int(location_id))
    if t and t.get("is_active"):
        return t
    return None


def place_trap(game_state, location_id: int) -> Optional[Dict]:
    location_id = int(location_id)
    if not traps_unlocked(game_state):
        return None
    mark_traps_unlocked(game_state)
    traps = getattr(game_state, "traps", None)
    if traps is None:
        game_state.traps = {}
        traps = game_state.traps
    if location_id in traps and traps[location_id].get("is_active"):
        return None
    trap = {
        "location_id": location_id,
        "is_active": True,
        "is_broken": False,
        "pending_animal": None,
        "pending_loot": None,
        "placed_day": getattr(game_state, "day", 1),
    }
    traps[location_id] = trap
    return trap


def remove_trap(game_state, location_id: int) -> Optional[Dict]:
    traps = getattr(game_state, "traps", {}) or {}
    location_id = int(location_id)
    if location_id in traps:
        return traps.pop(location_id)
    return None


def activate_trap(game_state) -> Optional[Dict]:
    """
    Совместимость с импортом в main.py.
    Реальная проверка утром — process_trap_rollover / roll_trap_roll.
    Здесь только сброс is_active у уже сломанных ловушек.
    """
    traps = getattr(game_state, "traps", {}) or {}
    for loc_id, trap in traps.items():
        if trap.get("is_broken"):
            trap["is_active"] = False
    return traps


def _pick_animal(location_id: int) -> Optional[Dict[str, Any]]:
    table = TRAP_LOOT_TABLE.get(int(location_id), [])
    if not table:
        return None
    roll = random.randint(1, 100)
    acc = 0
    for entry in table:
        acc += int(entry.get("chance", 0))
        if roll <= acc:
            return entry
    return table[-1]


def roll_trap_roll(game_state, location_id: int) -> Optional[Dict]:
    location_id = int(location_id)
    traps = getattr(game_state, "traps", {}) or {}
    trap = traps.get(location_id)
    if not trap or not trap.get("is_active"):
        return None

    roll = random.randint(1, 100)
    if roll <= 40:
        # 40% — ловушка пустая (остаётся активной, но улова нет)
        trap["is_broken"] = False
        trap["pending_animal"] = None
        trap["pending_loot"] = None
        return trap
    elif roll <= 60:
        # 20% (41-60) — ловушка ломается
        trap["is_broken"] = True
        trap["is_active"] = False
        trap["pending_animal"] = None
        trap["pending_loot"] = None
        return trap

    # 40% (61-100) — успешная добыча
    entry = _pick_animal(location_id)
    if not entry:
        return trap
    trap["is_broken"] = False
    trap["pending_animal"] = entry["name"]
    trap["pending_loot"] = dict(entry.get("loot") or {})
    return trap


def get_trap_loot(game_state, location_id: int) -> Optional[Dict]:
    trap = get_trap_for_location(game_state, location_id)
    if trap and trap.get("pending_animal"):
        return {
            "animal": trap["pending_animal"],
            "animal_name": trap["pending_animal"],
            "loot": trap.get("pending_loot") or {},
        }
    return None


def process_trap_rollover(game_state) -> List[Dict]:
    traps = getattr(game_state, "traps", {}) or {}
    results = []
    for loc_id in list(traps.keys()):
        trap = traps[loc_id]
        if not trap.get("is_active"):
            continue
        rolled = roll_trap_roll(game_state, int(loc_id))
        if not rolled:
            continue
        if rolled.get("is_broken"):
            results.append({
                "location_id": int(loc_id),
                "broken": True,
                "animal": None,
                "loot": {},
            })
        elif rolled.get("pending_animal"):
            results.append({
                "location_id": int(loc_id),
                "broken": False,
                "animal": rolled["pending_animal"],
                "loot": dict(rolled.get("pending_loot") or {}),
            })
    return results


def apply_trap_loot_to_inventory(game_state, loot: Dict[str, int]) -> None:
    inv = game_state.inventory
    for item, qty in (loot or {}).items():
        inv[item] = inv.get(item, 0) + int(qty)
