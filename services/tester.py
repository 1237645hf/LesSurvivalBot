"""
services/tester.py — Модуль режима тестировщика и песочницы (Sandbox Mode).

Функционал:
- Авторизация тестеров (белый список ID, testers.json, переменные окружения).
- Запуск сюжетных веток локаций (L1–L7) с учётом текущей локации.
- Симулятор боёвки со всеми противниками игры.
- Быстрая выдача и экипировка сетов брони и оружия.
- Пополнение/очистка инвентаря и разблокировка рецептов.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Set, Tuple
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TESTERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testers.json")
DEFAULT_TESTER_IDS: Set[int] = {906082819}


def load_tester_ids() -> Set[int]:
    """Загружает список ID тестировщиков из файла testers.json, констант и ENV."""
    ids = set(DEFAULT_TESTER_IDS)
    env_testers = os.getenv("TESTER_IDS")
    if env_testers:
        for p in env_testers.split(","):
            p_strip = p.strip()
            if p_strip.isdigit():
                ids.add(int(p_strip))
    if os.path.exists(TESTERS_FILE):
        try:
            with open(TESTERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
                            ids.add(int(item))
        except Exception as e:
            logging.warning(f"Не удалось прочитать testers.json: {e}")
    else:
        save_tester_ids(ids)
    return ids


def save_tester_ids(ids: Set[int]) -> bool:
    """Сохраняет список тестировщиков в testers.json."""
    try:
        with open(TESTERS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(ids)), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Не удалось сохранить testers.json: {e}")
        return False


def is_tester(uid: int) -> bool:
    """Проверяет, имеет ли пользователь права тестировщика."""
    return uid in load_tester_ids()


def add_tester(uid: int) -> bool:
    """Добавляет нового тестировщика."""
    ids = load_tester_ids()
    ids.add(uid)
    return save_tester_ids(ids)


# ──────────────────────────────────────────────────────────────────────────────
# КАТАЛОГ СЮЖЕТНЫХ ВЕТОК ПО ЛОКАЦИЯМ (L1–L7)
# ──────────────────────────────────────────────────────────────────────────────

LOCATION_STORIES: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = {
    "Стартовый лес": [
        ("🐺 Встреча с волком у пня", "forest_start", {}),
        ("🐱 Спасение котёнка", "pet_approach", {}),
        ("🔮 Купол с артефактом", "l1_dome_start", {}),
        ("🕳️ Волчье логово", "wolf_lair_start", {"l1_completed": True}),
    ],
    "Ручей со змеями": [
        ("🌊 Берег ручья (змеи и рюкзак)", "l2_1", {}),
        ("🌿 Заросли терновника (проверка брони)", "l2_thorns_approach", {"l2_prologue_completed": True}),
        ("🧱 Загадка плотины и переправа", "l2_bridge_puzzle_start", {"l2_prologue_completed": True, "l2_thorns_passed": True}),
    ],
    "Скромная лощина": [
        ("🏕️ Обустройство стоянки", "l3_enter_camp", {}),
        ("📜 Каменная плита с записями", "tablet_notes_view", {"l3_shelter_unlocked": True}),
        ("🐗 Разведка гребня (встреча с кабаном)", "l3_7_morning", {"l3_shelter_unlocked": True}),
    ],
    "Просека охотников": [
        ("🦌 Глава 1: Засада и олень", "l4_scene_1", {}),
        ("🟢 Глава 2: Слизни на просеке", "l4_ch2_slug_ambush", {"l4_completed": True}),
        ("🐺🐺 Глава 3: Стая волков", "l4_ch3_ambush", {"l4_completed": True, "l4_ch2_completed": True}),
    ],
    "Яр Слаймов": [
        ("☣️ Вход в Яр Слаймов", "slug_pit_start", {}),
        ("🍯 Меню приманки для слизней", "l5_bait_menu", {"slug_bait_active": True}),
        ("👑 Босс: Древний Слизень", "l5_boss_start", {}),
    ],
    "Мохнатая пещера": [
        ("🏔️ Начало подъёма в бурю", "location_enter_6", {}),
        ("🦇 Нападение нетопырей", "l6_bats_battle", {}),
        ("🔥 Тёплая пещера", "warm_cave_start", {"warm_cave_shelter": True}),
    ],
    "Святилище": [
        ("✨ Вершина Святилища", "sanctuary_peak_start", {}),
        ("🏆 Прикосновение к чаше (финал)", "sanctuary_resolve", {}),
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# СЕТЫ СНАРЯЖЕНИЯ
# ──────────────────────────────────────────────────────────────────────────────

EQUIPMENT_SETS: Dict[str, Dict[str, Any]] = {
    "slate": {
        "title": "🪨 Полный Сланцевый Сет",
        "equipment": {
            "head": "Сланцевая маска",
            "body": "Сланцевый панцирь",
            "pants": "Сланцевые поножи",
            "boots": "Сланцевые ботинки",
            "hand_right": "Охотничье сланцевое копьё",
            "hand_left": "Старый фонарь",
        },
    },
    "fur": {
        "title": "🐻 Полный Меховой Сет",
        "equipment": {
            "head": "Меховой капюшон",
            "body": "Меховой плащ-нагрудник",
            "pants": "Меховые поножи",
            "boots": "Меховые сапоги",
            "hand_right": "Крепкий посох",
            "hand_left": "Факел",
        },
    },
    "starter": {
        "title": "🎒 Стартовый походный набор",
        "equipment": {
            "body": "Стартовая куртка",
            "pants": "Стартовые штаны",
            "boots": "Стартовые ботинки",
            "hand_left": "Факел",
            "flask": "Армейская фляга",
        },
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# СИМУЛЯТОР БОЁВКИ
# ──────────────────────────────────────────────────────────────────────────────

COMBAT_ENEMIES: List[Tuple[str, str, str]] = [
    ("old_wolf", "🐺 Старый волк (L1)", "engine"),
    ("ancient_boar", "🐗 Секач солонца (L3)", "engine"),
    ("wolf_pack", "🐺🐺 Стая волков (L4)", "engine"),
    ("slug_pack", "🟢 Стая слизней (L5)", "slug_pack"),
    ("giant_slime", "👑 Исполинский слайм (L5)", "engine"),
    ("cave_bats", "🦇 Пещерные нетопыри (L6)", "engine"),
]


# ──────────────────────────────────────────────────────────────────────────────
# ФУНКЦИИ УПРАВЛЕНИЯ ТЕСТОВЫМ РЕЖИМОМ
# ──────────────────────────────────────────────────────────────────────────────

def enable_test_mode(game: Any) -> None:
    """Активирует тестовый режим, выдает все предметы x1000 и открывает все локации/крафты."""
    from modules.items import ITEMS
    from crafts import CRAFT_RECIPES

    game.is_test_mode = True

    # 1. Выдача всех предметов по 1000 штук
    for item_name in ITEMS.keys():
        game.inventory[item_name] = 1000

    # 2. Разблокировка всех локаций
    game.locations_unlocked = True
    game.unlocked_locations = [
        "Стартовый лес",
        "Ручей со змеями",
        "Скромная лощина",
        "Просека охотников",
        "Яр Слаймов",
        "Мохнатая пещера",
        "Святилище",
    ]

    # 3. Разблокировка всех крафтов
    game.unlocked_crafts = list(CRAFT_RECIPES.keys())
    if not hasattr(game, "story_flags") or not isinstance(game.story_flags, dict):
        game.story_flags = {}
    game.story_flags["slate_unlocked"] = True
    game.story_flags["fur_recipes_unlocked"] = True
    game.story_flags["l2_thorns_seen"] = True

    # 4. Восстановление характеристик
    game.hp = 100
    game.hunger = 100
    game.thirst = 100
    game.warmth = 100
    game.poison = 0
    game.hypothermia = 0

    # 5. Спец-снаряжение (полная фляга, фонарь)
    game.flask_water = 20
    game.army_flask_water = 20
    game.lantern_durability = 20
    game.campfire_durability = 30
    game.story_flags["has_stove"] = True
    game.story_flags["l3_shelter_unlocked"] = True

    game.add_log("🧪 Тестовый режим активирован. Выдано всё по 1 000 шт. Сохранения в БД отключены.")


def apply_equipment_set(game: Any, set_key: str) -> str:
    """Экипирует выбранный комплект снаряжения."""
    set_data = EQUIPMENT_SETS.get(set_key)
    if not set_data:
        return "Неизвестный сет."
    eq = set_data["equipment"]
    if not hasattr(game, "equipment") or not isinstance(game.equipment, dict):
        game.equipment = {}
    for slot, item in eq.items():
        game.equipment[slot] = item
        # Убедимся, что предмет есть в инвентаре/надет
        if item and game.inventory.get(item, 0) <= 0:
            game.inventory[item] = 1000
    if eq.get("flask") == "Армейская фляга":
        game.army_flask_water = 20
        game.flask_water = 20
    game.add_log(f"🛡️ Экипирован комплект: {set_data['title']}")
    return set_data["title"]


def toggle_pet_status(game: Any) -> bool:
    """Переключает статус наличия котёнка."""
    has_pet = game.is_story_flag_set("has_pet")
    if has_pet:
        game.story_flags["has_pet"] = False
        game.pet_name = None
        game.add_log("🐱 Питомец: отключен.")
        return False
    else:
        game.story_flags["has_pet"] = True
        game.pet_name = getattr(game, "pet_name", None) or "Барсик"
        game.add_log(f"🐱 Питомец: включен ({game.pet_name}).")
        return True


# ──────────────────────────────────────────────────────────────────────────────
# КЛАВИАТУРЫ РЕЖИМА ТЕСТИРОВЩИКА
# ──────────────────────────────────────────────────────────────────────────────

def get_tester_main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню панели тестировщика."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭 Сюжетки текущей локации", callback_data="tester_loc_stories")],
        [InlineKeyboardButton(text="⚔️ Симулятор боёв", callback_data="tester_combat_menu")],
        [InlineKeyboardButton(text="🛡️ Сеты экипировки", callback_data="tester_sets_menu")],
        [
            InlineKeyboardButton(text="📦 Выдать всё x1000", callback_data="tester_refill_items"),
            InlineKeyboardButton(text="🗑️ Очистить инв.", callback_data="tester_clear_inv"),
        ],
        [InlineKeyboardButton(text="❤️ Вылечить на 100%", callback_data="tester_heal_max")],
        [InlineKeyboardButton(text="❌ Выйти из режима тестирования", callback_data="tester_exit_mode")],
        [InlineKeyboardButton(text="↩️ В лагерь", callback_data="back_to_main")],
    ])


def get_tester_loc_stories_kb(game: Any) -> InlineKeyboardMarkup:
    """Клавиатура сюжетных веток для текущей локации с тумблером питомца."""
    cur_loc = getattr(game, "current_location", "Стартовый лес")
    # Подбираем каноническое название локации
    matched_loc = "Стартовый лес"
    for loc_name in LOCATION_STORIES.keys():
        if loc_name.lower() in str(cur_loc).lower():
            matched_loc = loc_name
            break

    scenes = LOCATION_STORIES.get(matched_loc, [])
    has_pet = game.is_story_flag_set("has_pet")
    pet_text = "🐱 Спутник: [✅ С котёнком]" if has_pet else "🐱 Спутник: [❌ Без котёнка]"

    rows: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=pet_text, callback_data="tester_pet_toggle")]
    ]

    for title, callback_key, _ in scenes:
        rows.append([InlineKeyboardButton(text=title, callback_data=f"tester_story_{callback_key}")])

    rows.append([
        InlineKeyboardButton(text="🗺️ Сменить локацию", callback_data="locations_menu"),
        InlineKeyboardButton(text="↩️ Назад в меню", callback_data="tester_main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_tester_combat_menu_kb() -> InlineKeyboardMarkup:
    """Клавиатура симулятора боёвки со всеми противниками."""
    rows: List[List[InlineKeyboardButton]] = []
    for enemy_id, title, _ in COMBAT_ENEMIES:
        rows.append([InlineKeyboardButton(text=title, callback_data=f"tester_combat_{enemy_id}")])
    rows.append([InlineKeyboardButton(text="↩️ В меню тестера", callback_data="tester_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_tester_sets_menu_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора готовых сетов снаряжения."""
    rows: List[List[InlineKeyboardButton]] = []
    for set_key, set_data in EQUIPMENT_SETS.items():
        rows.append([InlineKeyboardButton(text=set_data["title"], callback_data=f"tester_set_{set_key}")])
    rows.append([InlineKeyboardButton(text="↩️ В меню тестера", callback_data="tester_main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
