"""
modules/finds.py — Лут исследования по локациям (источник правды: еда.txt).

Основной бросок + независимый доп. бросок (кора / глина на L3).
Поддержка soft cap по типу ресурсов и случайных фраз при пустом поиске.
"""

from typing import Dict, List, Any, Optional, Tuple
import random


# ──────────────────────────────────────────────────────────────────────────────
# ТАБЛИЦЫ ОСНОВНОГО ЛУТА ПО ЛОКАЦИЯМ (Сумма весов = 100 на локацию)
# ──────────────────────────────────────────────────────────────────────────────
LOCATION_FINDS: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"item": "Ветка", "chance": 35},
        {"item": "Лесная ягода", "chance": 20},
        {"item": "Лесной гриб", "chance": 20},
        {"item": "Камень", "chance": 15},
        {"item": "Мох", "chance": 10},
    ],
    2: [
        {"item": "Ветка", "chance": 40},
        {"item": "Красная ягода", "chance": 25},
        {"item": "Камень", "chance": 25},
        {"item": "Сланцевая пластина", "chance": 10},
    ],
    3: [
        {"item": "Сланец", "chance": 30},
        {"item": "Ветка", "chance": 25},
        {"item": "Фиолетовая ягода", "chance": 20},
        {"item": "Дикий гриб", "chance": 20},
        {"item": "Сухой мох", "chance": 5},
    ],
    4: [
        {"item": "Ветка", "chance": 40},
        {"item": "Лесная ягода", "chance": 20},
        {"item": "Лесной гриб", "chance": 20},
        {"item": "Кость", "chance": 10},
        {"item": "Кожа", "chance": 10},
    ],
    5: [
        {"item": "Слизь", "chance": 35},
        {"item": "Ветка", "chance": 30},
        {"item": "Болотная ягода", "chance": 20},
        {"item": "Болотный гриб", "chance": 10},
        {"item": "Светящийся гриб", "chance": 5},
    ],
    6: [
        {"item": "Ветка", "chance": 35},
        {"item": "Пещерный гриб", "chance": 25},
        {"item": "Камень", "chance": 25},
        {"item": "Пещерный мох", "chance": 15},
    ],
    7: [
        {"item": "Ветка", "chance": 25},
        {"item": "Камень", "chance": 25},
        {"item": "Горная ягода", "chance": 20},
        {"item": "Горный гриб", "chance": 20},
        {"item": "Горный лишайник", "chance": 10},
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# БОНУСНЫЙ ЛУТ
# ──────────────────────────────────────────────────────────────────────────────
BONUS_FINDS: Dict[int, List[Dict[str, Any]]] = {
    1: [{"item": "Кусок коры", "chance": 30}],
    2: [{"item": "Кусок коры", "chance": 30}],
    3: [
        {"item": "Глина", "chance": 40},
        {"item": "Кусок коры", "chance": 30},
    ],
    4: [
        {"item": "Кусок коры", "chance": 40},
        {"item": "Ветка", "chance": 30, "count_range": (1, 2)},
    ],
    5: [{"item": "Кусок коры", "chance": 30}],
    6: [],
    7: [],
}

# ──────────────────────────────────────────────────────────────────────────────
# SOFT CAP ДЛЯ РЕСУРСОВ: (cap_soft, cap_hard)
# ──────────────────────────────────────────────────────────────────────────────
RESOURCE_SOFT_CAPS: Dict[str, Tuple[int, int]] = {
    "Ветка": (50, 80),
    "Камень": (15, 25),
    "Кусок коры": (25, 40),
    "Кора": (25, 40),
    "Мох": (15, 30),
    "Сухой мох": (15, 30),
    "Сухая трава": (15, 30),
    "Пещерный мох": (15, 30),
    "Горный лишайник": (15, 30),
    "Лесная ягода": (40, 60),
    "Красная ягода": (40, 60),
    "Фиолетовая ягода": (40, 60),
    "Болотная ягода": (40, 60),
    "Горная ягода": (40, 60),
    "Ягода": (40, 60),
    "Лесной гриб": (40, 60),
    "Дикий гриб": (40, 60),
    "Болотный гриб": (40, 60),
    "Пещерный гриб": (40, 60),
    "Горный гриб": (40, 60),
    "Гриб": (40, 60),
    "Светящийся гриб": (5, 10),
    "Кость": (20, 35),
    "Кожа": (25, 40),
    "Слизь": (50, 75),
    "Янтарное ядро": (15, 25),
    "Пузырёк": (20, 30),
    "Янтарное зелье": (10, 20),
    "Сланец": (20, 35),
    "Сланцевая пластина": (7, 17),
    "Глина": (15, 25),
}

# Канонический набор фраз при пустом результате поиска
EMPTY_FIND_PHRASES: List[str] = [
    "Ничего не нашёл.",
    "В этот раз не повезло.",
    "Всё обыскал, но пусто.",
    "Пусто.",
    "Повезёт в следующий раз.",
]

STICK_NAMES = {"Ветка", "Палка", "Палки"}

# Ягоды и грибы: при выпадении в броске дают 1 или 2 шт.
BERRY_MUSHROOM_NAMES = {
    "Лесная ягода",
    "Красная ягода",
    "Фиолетовая ягода",
    "Болотная ягода",
    "Горная ягода",
    "Ягода",
    "Лесной гриб",
    "Дикий гриб",
    "Болотный гриб",
    "Пещерный гриб",
    "Горный гриб",
    "Гриб",
    "Светящийся гриб",
}


def _roll_single_item(table: List[Dict[str, Any]]) -> str:
    """Выбрать ровно 1 предмет из таблицы по процентным шансам (весам)."""
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
    """Вспомогательный ролл для тестов механик дропа."""
    if not table:
        return []
    roll = random.randint(1, 100)
    acc = 0
    for entry in table:
        acc += int(entry.get("chance", 0))
        if roll <= acc:
            item = entry["item"]
            if item in BERRY_MUSHROOM_NAMES:
                return [item] * random.choice([1, 2])
            if item in STICK_NAMES:
                return [item] * random.randint(1, 3)
            return [item]
    last = table[-1]["item"]
    if last in BERRY_MUSHROOM_NAMES:
        return [last] * random.choice([1, 2])
    if last in STICK_NAMES:
        return [last] * random.randint(1, 3)
    return [last]


def _roll_bonus(table: List[Dict[str, Any]]) -> List[str]:
    """Бонусный ролл для редких региональных ресурсов."""
    found = []
    for entry in table:
        if random.randint(1, 100) <= int(entry.get("chance", 0)):
            item = entry["item"]
            count_range = entry.get("count_range")
            if count_range:
                cnt = random.randint(count_range[0], count_range[1])
                found.extend([item] * cnt)
            elif item in BERRY_MUSHROOM_NAMES:
                found.extend([item] * random.choice([1, 2]))
            elif item in STICK_NAMES:
                found.extend([item] * random.randint(1, 3))
            else:
                found.append(item)
    return found


def _apply_soft_cap(raw_drops: List[str], inventory: Optional[Dict[str, int]] = None) -> List[str]:
    """Применяет soft cap по виду ресурса к итоговому списку дропа.
    
    1. Группирует raw_drops по имени.
    2. Для каждого имени один roll:
       have = inventory.get(name, 0)
       если have >= hard → p = 0.10
       elif have >= soft → p = 0.50
       else → p = 1.0
    3. Успех → оставить весь qty этого имени; провал → весь qty отбросить.
    4. Имя не из словаря → всегда оставить.
    5. inventory is None → {} (всегда p = 1.0).
    """
    if not raw_drops:
        return []
    if inventory is None:
        inventory = {}

    counts: Dict[str, int] = {}
    for item in raw_drops:
        counts[item] = counts.get(item, 0) + 1

    kept_items: set[str] = set()
    for name in counts:
        if name not in RESOURCE_SOFT_CAPS:
            kept_items.add(name)
            continue
        soft, hard = RESOURCE_SOFT_CAPS[name]
        have = inventory.get(name, 0)
        if have >= hard:
            p = 0.10
        elif have >= soft:
            p = 0.50
        else:
            p = 1.0

        if random.random() < p:
            kept_items.add(name)

    return [item for item in raw_drops if item in kept_items]


def location_id_from_game(game) -> int:
    idx = getattr(game, "location_index", None)
    if isinstance(idx, int) and 0 <= idx <= 6:
        return idx + 1
    cur = str(getattr(game, "current_location", "") or "")
    mapping = {
        "Стартов": 1, "Лесной": 1, "Ручей": 2, "Лощин": 3, "Просека": 4, "Охотник": 4,
        "Яр": 5, "Слизн": 5, "Пещер": 6, "Мохнат": 6, "Святилищ": 7, "Вершин": 7,
    }
    for key, lid in mapping.items():
        if key in cur:
            return lid
    return 1


def roll_find(location_id: int, inventory: Optional[Dict[str, int]] = None, extra_roll: bool = False) -> List[str]:
    """3 броска при исследовании:
    Бросок A: таблица локации (1 предмет по шансам; ягоды/грибы 1-2 шт.).
    Бросок B: второй независимый бросок по таблице локации (всегда делается; ягоды/грибы 1-2 шт.).
    Бросок C: ~30% шанс на ветки/палки, количество 1, 2 или 3 с равной вероятностью.
    + Бонусный бросок (кора, глина).
    + Дополнительный бросок при экипированном амулете охотника (extra_roll=True).
    + Soft cap по виду предмета ко всему итоговому списку после A+B+C+bonus.
    """
    location_id = int(location_id)
    table = LOCATION_FINDS.get(location_id, LOCATION_FINDS[1])
    raw_drops: List[str] = []

    # Бросок A
    item_a = _roll_single_item(table)
    if item_a:
        if item_a in BERRY_MUSHROOM_NAMES:
            raw_drops.extend([item_a] * random.choice([1, 2]))
        else:
            raw_drops.append(item_a)

    # Бросок B
    item_b = _roll_single_item(table)
    if item_b:
        if item_b in BERRY_MUSHROOM_NAMES:
            raw_drops.extend([item_b] * random.choice([1, 2]))
        else:
            raw_drops.append(item_b)

    # Дополнительный бросок амулета
    if extra_roll:
        item_extra = _roll_single_item(table)
        if item_extra:
            if item_extra in BERRY_MUSHROOM_NAMES:
                raw_drops.extend([item_extra] * random.choice([1, 2]))
            else:
                raw_drops.append(item_extra)

    # Бросок C (~40% шанс на палки, 1..4 шт.)
    if random.randint(1, 100) <= 40:
        count = random.choice([1, 2, 3, 4])
        raw_drops.extend(["Ветка"] * count)

    # Бонусный бросок
    bonus = _roll_bonus(BONUS_FINDS.get(location_id, []))
    if bonus:
        raw_drops.extend(bonus)

    # Применение soft cap к итоговому списку
    return _apply_soft_cap(raw_drops, inventory)


def apply_finds_to_inventory(game, found: List[str]) -> str:
    """Применяет найденные предметы к инвентарю и возвращает текст для лога.
    При пустом списке находок возвращает одну из 5 канонических фраз.
    """
    if not found:
        return random.choice(EMPTY_FIND_PHRASES)
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


LOCATION_EMOJIS: Dict[int, str] = {
    1: "🌲",
    2: "🏞️",
    3: "🏔️",
    4: "🏹",
    5: "🍄",
    6: "⛰️",
    7: "🔮",
}


def is_explore_callback(data: str) -> bool:
    """Проверяет, относится ли callback к исследованию или сбору воды."""
    return data in ("action_1", "action_fill_rain_bottle", "action_collect_water")


async def handle_explore_callback(
    data: str,
    game: Any,
    uid: int,
    callback: Optional[Any] = None,
) -> Tuple[Optional[str], Optional[Any]]:
    """Обрабатывает исследование локации (action_1) и сбор дождевой воды (action_fill_rain_bottle, action_collect_water).

    Все импорты клавиатур, сюжетных триггеров и игровых состояний выполняются
    локально внутри функции для предотвращения циклических зависимостей.
    """
    from keyboards import get_main_kb, get_death_kb
    from game_state import get_death_text
    from story.location_stories import (
        check_forest_research_story_trigger,
        handle_story,
        start_slug_pack_battle,
    )

    if data == "action_1":
        if game.ap <= 0:
            ap_warning = "Не хватает очков действий! Нужно поспать (Отдых)."
            game.add_log(ap_warning)
            if callback:
                await callback.answer(ap_warning, show_alert=True)
            text = game.get_ui()
            kb = get_main_kb(game)
            return text, kb

        deltas = game.consume_action(action_type="search", base_hunger=2, base_thirst=4)
        loc_id = location_id_from_game(game)
        loc_emoji = LOCATION_EMOJIS.get(loc_id, "🌲")

        parts = []
        if deltas.get("delta_hunger"):
            parts.append(f"Сытость {deltas['delta_hunger']}")
        if deltas.get("delta_thirst"):
            parts.append(f"Жажда {deltas['delta_thirst']}")
        hp_delta = deltas.get("delta_hp", 0)
        if hp_delta:
            hp_reasons = []
            if deltas.get("hunger_damage_to_hp"):
                hp_reasons.append("голодание")
            if deltas.get("thirst_damage_to_hp"):
                hp_reasons.append("обезвоживание")
            reason = f" ({', '.join(hp_reasons)})" if hp_reasons else ""
            parts.append(f"HP {hp_delta}{reason}")

        res_str = ", ".join(parts) if parts else "без изменений"
        game.add_log(f"{loc_emoji} Исследование: {res_str}")

        if game.hp <= 0:
            game.hp = 0
            game.active_story_callback = None
            text = get_death_text(game, "💀 Ты умер от голода и истощения.")
            kb = get_death_kb()
            return text, kb

        torch_equipped = (
            game.equipment.get("hand_left") == "Факел"
        )
        lantern_equipped = (
            game.equipment.get("hand_left") == "Старый фонарь"
        )

        # Проверка сюжетных триггеров через модуль story/location_stories.py
        story_event, story_log = check_forest_research_story_trigger(game, loc_id, torch_equipped)
        if story_event:
            if story_log:
                game.add_log(story_log)
            text, kb = handle_story(story_event, game, uid)
        elif loc_id == 5 and getattr(game, "slug_bait_active", False) and random.random() < 0.5:
            if lantern_equipped:
                cur_d = int(getattr(game, "lantern_durability", 20) or 0)
                if cur_d > 0:
                    cur_d -= 1
                    game.lantern_durability = cur_d
            game.add_log("🍯 Сладкий запах приманки привлёк скопление слизней! Они выползают из расщелин!")
            text, kb = start_slug_pack_battle(game, count=random.randint(1, 6))
        else:
            has_amulet = (game.equipment.get("trinket") == "Костяной амулет охотника")
            found_list = roll_find(loc_id, game.inventory, extra_roll=has_amulet)
            msg = apply_finds_to_inventory(game, found_list)
            if lantern_equipped:
                cur_d = int(getattr(game, "lantern_durability", 20) or 0)
                if cur_d > 0:
                    cur_d -= 1
                    game.lantern_durability = cur_d
                max_d = int(getattr(game, "lantern_max_durability", 20) or 20)
                if cur_d == 0:
                    game.add_log(f"🔦 {msg} [Фонарь погас (0/{max_d}) — требуется заправить через крафт]")
                else:
                    game.add_log(f"🔦 {msg} [Фонарь: {cur_d}/{max_d}]")
            elif torch_equipped:
                game.add_log(f"🔦 {msg}")
            else:
                game.add_log(msg)
            text = game.get_ui()
            kb = get_main_kb(game)
        return text, kb

    elif data == "action_fill_rain_bottle":
        if game.weather not in {"rain", "storm"}:
            game.add_log("⚠️ Дождь уже закончился.")
        elif game.ap < 1:
            game.add_log("⚠️ Не хватает очков действий (требуется 1 ⚡ AP)!")
        else:
            has_empty = game.inventory.get("Пустая бутылка", 0) > 0
            bottles = getattr(game, "rain_bottles", [])
            partial_idx = next((i for i, w in enumerate(bottles) if w < 20), None)

            if partial_idx is not None:
                game.consume_action(1)
                gained = random.randint(2, 4)
                new_val = min(20, bottles[partial_idx] + gained)
                actual_add = new_val - bottles[partial_idx]
                bottles[partial_idx] = new_val
                game.add_log(f"🌧️ Ты подставил бутылку под дождь и набрал +{actual_add} делений влаги ({new_val}/20).")
            elif has_empty:
                game.consume_action(1)
                gained = random.randint(2, 4)
                game.inventory["Пустая бутылка"] -= 1
                if game.inventory["Пустая бутылка"] <= 0:
                    del game.inventory["Пустая бутылка"]
                game.inventory["Бутылка дождевой воды"] = game.inventory.get("Бутылка дождевой воды", 0) + 1
                bottles.append(gained)
                game.rain_bottles = bottles
                game.add_log(f"🌧️ Ты наполнил пустую бутылку дождевой водой (+{gained} деления, {gained}/20).")
            else:
                game.add_log("У тебя нет подходящей пустой ёмкости для сбора дождевой воды.")
        text = game.get_ui()
        kb = get_main_kb(game)
        return text, kb

    elif data == "action_collect_water":
        if game.weather in {"rain", "storm"}:
            game.thirst = min(100, game.thirst + 20)
            game.add_log("🌧️ Ты подставил ладони под дождь и напился свежей воды (+20 жажды).")
        else:
            game.add_log("⚠️ Дождь уже закончился.")
        text = game.get_ui()
        kb = get_main_kb(game)
        return text, kb

    return None, None

