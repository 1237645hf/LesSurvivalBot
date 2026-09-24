import asyncio
import logging
import os
import time
import random
from textwrap import wrap
from pathlib import Path
from aiohttp import web, ClientSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from pymongo import MongoClient  # noqa: F401 вЂ” РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РІ services/database.py

from game_math import (
    process_damage,
    get_resource_multiplier,
    get_base_resource_cost,
    get_thirst_base_cost,
    calculate_ap_by_hp,
)
from game_state import GameState, Game
from modules.hints import get_active_hints
from modules.traps import (
    HUNTABLE_ANIMALS,
    TRAP_CHANCE_BY_LOCATION,
    place_trap,
    remove_trap,
    activate_trap,
    get_trap_for_location,
    get_trap_description,
    get_trap_loot,
    get_active_traps,
    roll_trap_roll,
    process_trap_rollover,
    apply_trap_loot_to_inventory,
    traps_unlocked,
)
from modules.cooking import COOKING_RECIPES, cook_item, list_recipes, format_recipe_card
from modules.items import (
    get_item_effects,
    get_item_negative_effects,
    is_item_consumable,
    format_item_card,
    get_item_rank_marker,
    get_item_display_name,
)

# Р“РѕС‚РѕРІРєР°: РµРґРёРЅС‹Р№ РёСЃС‚РѕС‡РЅРёРє вЂ” modules/cooking.py (РµРґР°.txt). CAMPFIRE_RECIPES СѓРґР°Р»С‘РЅ.


def format_resource_log_text(deltas: dict) -> str:
    """РЎРѕР±СЂР°С‚СЊ СЃС‚СЂРѕРєСѓ Р»РѕРіР° СЃС‚СЂРѕРіРѕ РїРѕ Р¤РђРљРўРР§Р•РЎРљРРњ РґРµР»СЊС‚Р°Рј РёР· consume_action/light_campfire.

    РџСЂРёРјРµСЂ РІС‹РІРѕРґР°: В«Р“РѕР»РѕРґ -2, Р–Р°Р¶РґР° -1В» РёР»Рё В«Р“РѕР»РѕРґ -1, HP -3 (РіРѕР»РѕРґР°РЅРёРµ)В».
    """
    parts = []
    if deltas.get("delta_hunger"):
        parts.append(f"Р“РѕР»РѕРґ {deltas['delta_hunger']:+d}")
    if deltas.get("delta_thirst"):
        parts.append(f"Р–Р°Р¶РґР° {deltas['delta_thirst']:+d}")
    hp_delta = deltas.get("delta_hp", 0)
    if hp_delta:
        hp_reasons = []
        if deltas.get("hunger_damage_to_hp"):
            hp_reasons.append("РіРѕР»РѕРґР°РЅРёРµ")
        if deltas.get("thirst_damage_to_hp"):
            hp_reasons.append("РѕР±РµР·РІРѕР¶РёРІР°РЅРёРµ")
        reason = f" ({', '.join(hp_reasons)})" if hp_reasons else ""
        parts.append(f"HP {hp_delta:+d}{reason}")
    return ", ".join(parts)


def load_env_file(path: str = ".env"):
    """Р—Р°РіСЂСѓР·РёС‚СЊ РїРµСЂРµРјРµРЅРЅС‹Рµ РёР· .env, РµСЃР»Рё РѕРЅРё РµС‰С‘ РЅРµ Р·Р°РґР°РЅС‹ РІ РѕРєСЂСѓР¶РµРЅРёРё."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file()

from keyboards import (
    get_main_kb,
    get_locations_kb,
    get_settings_kb,
    get_bottom_menu,
    get_use_item_kb,
    get_drop_item_kb,
    get_drop_quantity_kb,
    get_campfire_kb,
    get_campfire_fuel_kb,
    get_campfire_recipes_kb,
    get_campfire_recipe_kb,
    get_campfire_light_confirm_kb,
    get_bottle_actions_kb,
    get_inspect_menu_kb,
    get_item_card_actions_kb,
    get_campfire_recipe_view_kb,
    inventory_inline_kb,
    character_inline_kb,
)
from crafts import handle_craft, do_craft, can_craft, craft_mark, CRAFT_RECIPES
from story.location_stories import (
    handle_story,
    handle_location_2_ruchey,
    handle_location_3_slate_hollow,
    handle_location_4_hunters_glade,
    handle_location_5_slug_pit,
    handle_location_6_furry_cave,
    handle_location_7_sanctuary_peak,
    ending_text,
    resolve_ending,
    ENDING_TITLES,
)
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# РќРђРЎРўР РћР™РљР
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN РЅРµ РЅР°Р№РґРµРЅ!")

MONGO_URI = os.getenv("MONGO_URI") or "mongodb://localhost:27017/test"

logging.basicConfig(level=logging.INFO)
logging.info("Р‘РѕС‚ Р·Р°РїСѓСЃРєР°РµС‚СЃСЏ РІ СЂРµР¶РёРјРµ Telegram polling")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Р“Р»РѕР±Р°Р»СЊРЅС‹Рµ СЃР»РѕРІР°СЂРё РґР»СЏ С‚СЂРµРєРёРЅРіР° СЃРѕСЃС‚РѕСЏРЅРёР№ (Р·Р°РїСЂРѕСЃС‹, СЃРѕРѕР±С‰РµРЅРёСЏ)
last_request_time = {}
last_active_msg_id = {}

# Р РµРіРёСЃС‚СЂР°С†РёСЏ СЃРёСЃС‚РµРјРЅС‹С… РєРѕРјР°РЅРґ Telegram РґР»СЏ СЃРёРЅРµР№ РєРЅРѕРїРєРё Menu
# set_my_commands РІС‹Р·С‹РІР°РµС‚СЃСЏ РІ run_bot() СЃ await

# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# Р‘РђР—Рђ Р”РђРќРќР«РҐ
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
from services.database import (
    players_collection,
    load_game,
    save_game,
    games,
    MemoryPlayersCollection,
)


ITEM_DESCRIPTIONS = {
    "РЎРїРёС‡РєРё": "РќСѓР¶РЅС‹ РґР»СЏ СЂРѕР·Р¶РёРіР° Рё СЃРѕР·РґР°РЅРёСЏ С„Р°РєРµР»Р°.",
    "Р’РµС‚РєР°": "РџРѕРґС…РѕРґРёС‚ РґР»СЏ РєСЂР°С„С‚Р° РїСЂРѕСЃС‚С‹С… РїСЂРµРґРјРµС‚РѕРІ.",
    "Р¤Р°РєРµР»": "РћСЃРІРµС‰Р°РµС‚ РїСѓС‚СЊ Рё РїРѕРјРѕРіР°РµС‚ РїРµСЂРµР¶РёС‚СЊ РѕРїР°СЃРЅС‹Рµ РІСЃС‚СЂРµС‡Рё.",
    "РЎР»Р°РЅС†РµРІР°СЏ РїР»Р°СЃС‚РёРЅР°": "РљР»СЋС‡РµРІРѕР№ РјР°С‚РµСЂРёР°Р» РґР»СЏ СЃРЅР°СЂСЏР¶РµРЅРёСЏ Сѓ СЂСѓС‡СЊСЏ.",
    "РЎР»Р°РЅРµРІС‹Р№ С€Р»РµРј": "Р—Р°С‰РёС‰Р°РµС‚ РіРѕР»РѕРІСѓ РѕС‚ РѕРїР°СЃРЅРѕСЃС‚РµР№ Р»РѕРєР°С†РёРё.",
    "РЎР»Р°РЅРµРІР°СЏ Р±СЂРѕРЅСЏ": "Р—Р°С‰РёС‰Р°РµС‚ РіСЂСѓРґСЊ РІ РїСѓС‚РµС€РµСЃС‚РІРёРё.",
}


def get_inspectable_items(game):
    return [
        item for item, count in game.inventory.items()
        if count > 0 and item in ITEM_DESCRIPTIONS
    ]


def get_usable_items(game):
    return [
        item for item, count in game.inventory.items()
        if count > 0 and is_item_consumable(item)
    ]


def get_callback_answer(callback):
    data = callback.data or ""
    game = games.get(callback.from_user.id)
    if data == "inv_inspect" and (not game or not get_inspectable_items(game)):
        return "РЈ РІР°СЃ РЅРµС‚ РєР»СЋС‡РµРІС‹С… РїСЂРµРґРјРµС‚РѕРІ РґР»СЏ РїРѕРґСЂРѕР±РЅРѕРіРѕ РѕСЃРјРѕС‚СЂР°", True
    if data in ("inv_use", "inv_drop") and (
        not game or not any(count > 0 for count in game.inventory.values())
    ):
        return ("РќРµС‡РµРіРѕ РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊ" if data == "inv_use" else "РќРµС‡РµРіРѕ РІС‹РєРёРґС‹РІР°С‚СЊ"), True
    if data == "inv_use" and not get_usable_items(game):
        return "РќРµС‡РµРіРѕ РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊ", True
    return None, False


def use_consumable(item, game):
    """РСЃРїРѕР»СЊР·РѕРІР°С‚СЊ РїСЂРµРґРјРµС‚ СЃ СѓС‡С‘С‚РѕРј РґРёРЅР°РјРёС‡РµСЃРєРёС… РєРѕСЌС„С„РёС†РёРµРЅС‚РѕРІ.

    РСЃС‚РѕС‡РЅРёРє РїСЂР°РІРґС‹ РїРѕ СЌС„С„РµРєС‚Р°Рј вЂ” modules/items.py (get_item_effects).
    """
    if item == "Р’РѕРґР°":
        hunger_mult = get_resource_multiplier(game, "hunger")
        water_cost = 1 + max(0, (30 - game.hunger) // 10)
        if game.inventory.get("Р’РѕРґР°", 0) < water_cost:
            return f"РќСѓР¶РЅРѕ РІРѕРґС‹: {water_cost}. Р’ РёРЅРІРµРЅС‚Р°СЂРµ РЅРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ РІРѕРґС‹."
        game.inventory["Р’РѕРґР°"] -= water_cost
        if game.inventory["Р’РѕРґР°"] <= 0:
            del game.inventory["Р’РѕРґР°"]
        thirst_restore = 10 * get_resource_multiplier(game, "thirst")
        game.thirst = min(100, game.thirst + thirst_restore)
        result = f"Р–Р°Р¶РґР° РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅР° РЅР° {int(thirst_restore)}. РџРѕС‚СЂР°С‡РµРЅРѕ РІРѕРґС‹: {water_cost}."
    else:
        effects = get_item_effects(item)

        if not effects and "Р·РµР»СЊ" in item.lower():
            effects = {"hp": 25}
        if not effects and item == "Р•РґР°":
            effects = {"hunger": 30}

        if not effects:
            return None

        restore_parts = []

        if "hunger" in effects:
            hunger_mult = get_resource_multiplier(game, "hunger")
            hunger_val = int(effects["hunger"] * hunger_mult)
            game.hunger = min(100, game.hunger + hunger_val)
            restore_parts.append(f"Р“РѕР»РѕРґ СѓС‚РѕР»РµРЅ ({hunger_val} РµРґ.)")

        if "thirst" in effects:
            thirst_mult = get_resource_multiplier(game, "thirst")
            thirst_val = int(effects["thirst"] * thirst_mult)
            game.thirst = min(100, game.thirst + thirst_val)
            restore_parts.append(f"Р–Р°Р¶РґР° РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅР° ({thirst_val} РµРґ.)")

        if "hp" in effects:
            hp_val = effects["hp"]
            game.hp = min(100, game.hp + hp_val)
            if hp_val >= 0:
                restore_parts.append(f"Р—РґРѕСЂРѕРІСЊРµ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРѕ ({hp_val} РµРґ.)")
            else:
                restore_parts.append(f"РџРѕР»СѓС‡РµРЅ СѓСЂРѕРЅ ({abs(hp_val)} РµРґ.)")

        if "poison" in effects and effects["poison"]:
            poison_val = effects["poison"]
            game.hp = max(0, game.hp - poison_val)
            restore_parts.append(f"Отравление ({poison_val} урона)")

        # Проверка негативных эффектов (расстройство желудка, токсины, паразиты)
        neg = get_item_negative_effects(item)
        if neg:
            chance = int(neg.get("chance", 0))
            if random.randint(1, 100) <= chance:
                neg_effects = neg.get("effects", {})
                if "thirst" in neg_effects:
                    game.thirst = max(0, game.thirst + neg_effects["thirst"])
                if "hp" in neg_effects:
                    game.hp = max(1, game.hp + neg_effects["hp"])
                msg = neg.get("log_message") or neg.get("description")
                restore_parts.append(f"⚠️ {msg}")

        if not restore_parts:
            return None

        result = " ".join(restore_parts)

        game.inventory[item] -= 1
        if game.inventory[item] <= 0:
            del game.inventory[item]

    game.add_log(f"РСЃРїРѕР»СЊР·РѕРІР°РЅРѕ: {item}. {result}")
    return f"РСЃРїРѕР»СЊР·РѕРІР°РЅРѕ: {item}. {result}\n\n{game.get_ui()}"

# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# РџР РР’Р•РўРЎРўР’РР•
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
GUIDE_TEXT = (
    "Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ РІ Р»РµСЃ РІС‹Р¶РёРІР°РЅРёСЏ!\n\n"
    "РљСЂР°С‚РєРёР№ РіР°Р№Рґ:\n"
    "вќ¤пёЏ Р—РґРѕСЂРѕРІСЊРµ\n"
    "рџЌ– РЎС‹С‚РѕСЃС‚СЊ\n"
    "рџ’§ Р–Р°Р¶РґР°\n"
    "вљЎ Р”РµР№СЃС‚РІРёСЏ РЅР° РґРµРЅСЊ\n\n"
    "РљР°СЂРјР° РїРѕРјРѕР¶РµС‚ РІС‹Р±СЂР°С‚СЊСЃСЏ.\n\n"
    "РџРѕРїСЂРѕР±СѓР№ РІС‹Р¶РёС‚СЊ, РґСЂСѓРі РјРѕР№..."
)

# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# Р’РЎРџРћРњРћР“РђРўР•Р›Р¬РќРђРЇ Р¤РЈРќРљР¦РРЇ РЎ RETRY РџР Р FLOOD
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
async def safe_delete_message(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest as exc:
        logging.warning(f"РќРµ СѓРґР°Р»РѕСЃСЊ СѓРґР°Р»РёС‚СЊ {message_id}: {exc}")
    except Exception as exc:
        logging.exception(f"РћС€РёР±РєР° СѓРґР°Р»РµРЅРёСЏ СЃРѕРѕР±С‰РµРЅРёСЏ {message_id}: {exc}")


async def safe_edit_message(chat_id: int, msg_id: int, text: str, reply_markup=None):
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=reply_markup)
        return True
    except TelegramRetryAfter as exc:
        logging.warning(f"Flood control: Р¶РґС‘Рј {exc.retry_after} СЃРµРє РїРµСЂРµРґ РїРѕРІС‚РѕСЂРѕРј edit")
        try:
            await asyncio.sleep(exc.retry_after + 0.5)
            await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=reply_markup)
            return True
        except TelegramBadRequest as exc2:
            logging.warning(f"РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚СЂРµРґР°РєС‚РёСЂРѕРІР°С‚СЊ РїРѕСЃР»Рµ retry {msg_id}: {exc2}")
            await safe_delete_message(chat_id, msg_id)
            return False
        except Exception as exc2:
            logging.exception(f"РћС€РёР±РєР° РїРѕРІС‚РѕСЂРЅРѕРіРѕ edit {msg_id}: {exc2}")
            return False
    except TelegramBadRequest as exc:
        logging.warning(f"РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚СЂРµРґР°РєС‚РёСЂРѕРІР°С‚СЊ {msg_id}: {exc}")
        await safe_delete_message(chat_id, msg_id)
        return False
    except Exception as exc:
        logging.exception(f"РќРµРѕР¶РёРґР°РЅРЅР°СЏ РѕС€РёР±РєР° edit {msg_id}: {exc}")
        return False


async def update_or_send_message(chat_id: int, uid: int, text: str, reply_markup=None):
    game = games.get(uid)
    text = format_game_text(text, game)
    msg_id = last_active_msg_id.get(uid)
    if msg_id:
        edited = await safe_edit_message(chat_id, msg_id, text, reply_markup)
        if edited:
            return msg_id
        last_active_msg_id.pop(uid, None)

    try:
        msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
        last_active_msg_id[uid] = msg.message_id
        return msg.message_id
    except TelegramRetryAfter as exc:
        logging.warning(f"Flood control send_message: Р¶РґС‘Рј {exc.retry_after} СЃРµРє")
        try:
            await asyncio.sleep(exc.retry_after + 0.5)
            msg = await bot.send_message(chat_id, text, reply_markup=reply_markup)
            last_active_msg_id[uid] = msg.message_id
            return msg.message_id
        except Exception as exc2:
            logging.exception(f"РћС€РёР±РєР° send_message РїРѕСЃР»Рµ retry: {exc2}")
            return None
    except TelegramBadRequest as exc:
        logging.warning(f"РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РїСЂР°РІРёС‚СЊ СЃРѕРѕР±С‰РµРЅРёРµ: {exc}")
        return None
    except Exception as exc:
        logging.exception(f"РќРµРѕР¶РёРґР°РЅРЅР°СЏ РѕС€РёР±РєР° send_message: {exc}")
        return None


def format_game_text(text: str, game) -> str:
    """РћС‚С„РѕСЂРјР°С‚РёСЂРѕРІР°С‚СЊ СЃРѕРѕР±С‰РµРЅРёРµ РїРѕРґ РІС‹Р±СЂР°РЅРЅС‹Р№ СЂРµР¶РёРј СЌРєСЂР°РЅР° РёРіСЂРѕРєР°."""
    if not game:
        return text

    line_length = game.max_line_length if game.display_mode == "phone" else None
    lines = []
    for line in text.splitlines() or [""]:
        if line_length:
            lines.extend(wrap(line, width=line_length, replace_whitespace=False) or [""])
        else:
            lines.append(line)

    max_lines = game.max_lines_per_msg
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = f"{lines[-1]}\nвЂ¦"
    return "\n".join(lines)


def get_settings_text(game):
    mode = "рџ“± РўРµР»РµС„РѕРЅ" if game.display_mode == "phone" else "рџ’» РљРѕРјРїСЊСЋС‚РµСЂ"
    return (
        "вљ™пёЏ РќР°СЃС‚СЂРѕР№РєРё РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ\n\n"
        f"Р РµР¶РёРј: {mode}\n"
        f"Р”Р»РёРЅР° СЃС‚СЂРѕРєРё: {game.max_line_length}\n"
        f"РЎС‚СЂРѕРє РЅР° СЃРѕРѕР±С‰РµРЅРёРµ: {game.max_lines_per_msg}"
    )

# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# РҐР•РќР”Р›Р•Р Р«
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    logging.info(f"[START] РџРѕР»СѓС‡РµРЅ /start РѕС‚ {uid}")
    try:
        for i in range(1, 50):
            await bot.delete_message(chat_id, message.message_id - i)
    except:
        pass
    loaded = load_game(uid)
    if loaded:
        text = "Р’С‹ РїСЂРёС€Р»Рё РІ СЃРµР±СЏ РїРѕСЃСЂРµРґРё Р»РµСЃР°. Р’С‹ РЅРёС‡РµРіРѕ РЅРµ РїРѕРјРЅРёС‚Рµ... Р’ РїР°РјСЏС‚Рё Р»РёС€СЊ РѕР±СЂС‹РІРєРё РїСЂРѕС€Р»РѕРіРѕ."
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="рџ”„ РџСЂРѕРґРѕР»Р¶РёС‚СЊ", callback_data="load_game")],
            [types.InlineKeyboardButton(text="вљ пёЏ РќР°С‡Р°С‚СЊ СЃРЅР°С‡Р°Р»Р°", callback_data="confirm_new_game")]
        ])
    else:
        text = GUIDE_TEXT
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="рџљЂ РќР°С‡Р°С‚СЊ РІС‹Р¶РёРІР°РЅРёРµ", callback_data="start_new_game")]
        ])
    # РќРёР¶РЅСЏСЏ Reply-РєР»Р°РІРёР°С‚СѓСЂР° РѕС‚РєР»СЋС‡РµРЅР° вЂ” С‚РѕР»СЊРєРѕ Menu Рё inline
    try:
        await message.answer("\u200b", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await update_or_send_message(chat_id, uid, text, kb)


def _ensure_game(uid: int):
    """Р”РѕСЃС‚Р°С‚СЊ РёРіСЂСѓ РёР· РїР°РјСЏС‚Рё РёР»Рё Mongo."""
    game = games.get(uid)
    if game is None:
        game = load_game(uid)
        if game is not None:
            games[uid] = game
    return game


@dp.message(Command("main", "menu", "home"))
async def cmd_main(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    game = _ensure_game(uid)
    if not game:
        await message.answer("РЎРЅР°С‡Р°Р»Р° /start")
        return
    await update_or_send_message(chat_id, uid, game.get_ui(), get_main_kb(game))


@dp.message(Command("inventory", "inv"))
async def cmd_inventory(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    game = _ensure_game(uid)
    if not game:
        await message.answer("РЎРЅР°С‡Р°Р»Р° /start")
        return
    game.push_screen("inventory")
    await update_or_send_message(chat_id, uid, game.get_inventory_text(), inventory_inline_kb)
    save_game(uid, game)


@dp.message(Command("character", "char", "hero"))
async def cmd_character(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    game = _ensure_game(uid)
    if not game:
        await message.answer("РЎРЅР°С‡Р°Р»Р° /start")
        return
    game.push_screen("character")
    await update_or_send_message(chat_id, uid, game.get_character_text(), character_inline_kb)
    save_game(uid, game)


@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    game = _ensure_game(uid)
    if not game:
        await message.answer("РЎРЅР°С‡Р°Р»Р° /start")
        return
    game.push_screen("settings")
    await update_or_send_message(chat_id, uid, get_settings_text(game), get_settings_kb(game))
    save_game(uid, game)

@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    chat_id = callback.message.chat.id
    data = callback.data or ""
    try:
        now = time.time()
        last = last_request_time.get(uid, 0)
        if now - last < 0.35:
            await callback.answer()
            return
        last_request_time[uid] = now

        ans = get_callback_answer(callback)
        if ans and ans[0]:
            await callback.answer(str(ans[0]), show_alert=bool(ans[1]) if len(ans) > 1 else False)
        else:
            await callback.answer()

        logging.info(f"[CALLBACK] {data} РѕС‚ {uid}")
        game = games.get(uid)
        if game is None:
            game = load_game(uid)
            if game is not None:
                games[uid] = game
        if data in ("new_game", "start_new_game"):
            game = Game()
            games[uid] = game
            save_game(uid, game)
            text = game.get_ui()
            kb = get_main_kb(game)
            await update_or_send_message(chat_id, uid, text, kb)
            return
        if data == "load_game":
            game = load_game(uid) or Game()
            games[uid] = game
            save_game(uid, game)
            text = game.get_ui()
            kb = get_main_kb(game)
            await update_or_send_message(chat_id, uid, text, kb)
            return
        if data == "confirm_new_game":
            text = "РЈРґР°Р»РёС‚СЊ С‚РµРєСѓС‰РµРіРѕ РїРµСЂСЃРѕРЅР°Р¶Р° Рё РЅР°С‡Р°С‚СЊ РЅРѕРІСѓСЋ РёСЃС‚РѕСЂРёСЋ?"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="вњ… Р”Р°, РЅР°С‡Р°С‚СЊ Р·Р°РЅРѕРІРѕ", callback_data="start_new_game_confirmed")],
                [types.InlineKeyboardButton(text="вќЊ РћСЃС‚Р°РІРёС‚СЊ РїРµСЂСЃРѕРЅР°Р¶Р°", callback_data="cancel_new_game")]
            ])
            await update_or_send_message(chat_id, uid, text, kb)
            return
        if data == "start_new_game_confirmed":
            game = Game()
            games[uid] = game
            save_game(uid, game)
            text = game.get_ui()
            kb = get_main_kb(game)
            await update_or_send_message(chat_id, uid, text, kb)
            return
        if data == "cancel_new_game":
            # Р’РѕР·РІСЂР°С‰Р°РµРј РёРіСЂРѕРєР° РІ РіР»Р°РІРЅРѕРµ РјРµРЅСЋ СЃС‚Р°СЂС‚Р°
            text = "Р’С‹ РѕС‚РјРµРЅРёР»Рё РїРµСЂРµР·Р°РїСѓСЃРє. Р§С‚Рѕ РґРµР»Р°РµРј?"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="рџ”„ РџСЂРѕРґРѕР»Р¶РёС‚СЊ", callback_data="load_game")],
                [types.InlineKeyboardButton(text="вљ пёЏ РќР°С‡Р°С‚СЊ СЃРЅР°С‡Р°Р»Р°", callback_data="confirm_new_game")]
            ])
            await update_or_send_message(chat_id, uid, text, kb)
            return

        if game is None:
            await update_or_send_message(
                chat_id,
                uid,
                "РЎРµСЃСЃРёСЏ РЅРµ РЅР°Р№РґРµРЅР°. РќР°Р¶РјРё /start",
                types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="рџљЂ РќР°С‡Р°С‚СЊ РІС‹Р¶РёРІР°РЅРёРµ", callback_data="start_new_game")]
                ]),
            )
            return

        text = None
        kb = None

        if data == "settings_mode_phone":
            game.display_mode = "phone"
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_mode_pc":
            game.display_mode = "pc"
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_length_minus":
            game.max_line_length = max(10, game.max_line_length - 5)
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_length_plus":
            game.max_line_length = min(100, game.max_line_length + 5)
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_height_minus":
            game.max_lines_per_msg = max(3, game.max_lines_per_msg - 1)
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_height_plus":
            game.max_lines_per_msg = min(30, game.max_lines_per_msg + 1)
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "settings_noop":
            text = get_settings_text(game)
            kb = get_settings_kb(game)
        elif data == "locations_menu":
            game.push_screen("locations")
            text = "РљСѓРґР° РЅР°РїСЂР°РІРёС‚СЊСЃСЏ?"
            kb = get_locations_kb(game)
        elif data.startswith("trap_place_"):
            location_id = int(data.replace("trap_place_", ""))
            game.traps[location_id] = {
                "location_id": location_id,
                "is_active": True,
                "is_broken": False,
                "placed_day": game.day,
            }
            game.add_log(f"Р›РѕРІСѓС€РєР° СѓСЃС‚Р°РЅРѕРІР»РµРЅР° РІ {location_id}-Р№ Р»РѕРєР°С†РёРё!")
            text = f"Р›РѕРІСѓС€РєР° СѓСЃС‚Р°РЅРѕРІР»РµРЅР° РІ {location_id}-Р№ Р»РѕРєР°С†РёРё!"
            kb = get_main_kb(game)
        elif data.startswith("trap_replace_"):
            location_id = int(data.replace("trap_replace_", ""))
            game.traps[location_id] = {
                "location_id": location_id,
                "is_active": True,
                "is_broken": False,
                "placed_day": game.day,
            }
            game.add_log(f"РќРѕРІР°СЏ Р»РѕРІСѓС€РєР° СѓСЃС‚Р°РЅРѕРІР»РµРЅР° РІ {location_id}-Р№ Р»РѕРєР°С†РёРё (СЃС‚Р°СЂР°СЏ СЃР»РѕРјР°РЅР°)!")
            text = f"РќРѕРІР°СЏ Р»РѕРІСѓС€РєР° РІ {location_id}-Р№ Р»РѕРєР°С†РёРё!"
            kb = get_main_kb(game)
        elif data == "location_enter_2":
            game.current_location = "Р СѓС‡РµР№ СЃ Р—РјРµСЏРјРё"
            text, kb = handle_location_2_ruchey("river_ferocious", game, uid)
        elif data == "location_enter_3":
            game.current_location = "РЎРєСЂРѕРјРЅР°СЏ Р›РѕС‰РёРЅР°"
            text, kb = handle_location_3_slate_hollow("slate_hollow_start", game, uid)
        elif data == "location_enter_4":
            game.current_location = "РџСЂРѕСЃРµРєР° РћС…РѕС‚РЅРёРєРѕРІ"
            text, kb = handle_location_4_hunters_glade("hunters_glade_start", game, uid)
        elif data == "location_enter_5":
            game.current_location = "РЇСЂ РЎР»РёР·РЅРµР№"
            text, kb = handle_location_5_slug_pit("slug_pit_start", game, uid)
        elif data == "location_enter_6":
            game.current_location = "РњРѕС…РЅР°С‚Р°СЏ РџРµС‰РµСЂР°"
            text, kb = handle_location_6_furry_cave("furry_cave_start", game, uid)
        elif data == "location_enter_7":
            game.current_location = "Р’РµСЂС€РёРЅР° РЎРІСЏС‚РёР»РёС‰Р°"
            text, kb = handle_location_7_sanctuary_peak("sanctuary_peak_start", game, uid)
        elif data == "sanctuary_resolve":
            text, kb = handle_location_7_sanctuary_peak(data, game, uid)
        elif data == "action_2":
            game.push_screen("inventory")
            text = game.get_inventory_text()
            kb = inventory_inline_kb
        elif data == "inv_character":
            game.push_screen("character")
            text = game.get_character_text()
        elif data.startswith("cook_exec_") or (data.startswith("cook_") and not data.startswith("cook_recipe_view_")):
            # Непосредственное приготовление блюда на костре
            recipe_id = data.removeprefix("cook_exec_")
            if not game.campfire_active or game.campfire_durability <= 0:
                await callback.answer("🔥 Костёр погас! Разведите его снова.", show_alert=True)
                return
            ok, message = cook_item(game, recipe_id)
            if not ok:
                await callback.answer(message, show_alert=True)
                return
            deltas = game.consume_action(action_type="cook", base_hunger=2, base_thirst=1)
            res_log = format_resource_log_text(deltas)
            if res_log:
                game.add_log(res_log)
            game.campfire_durability = max(0, game.campfire_durability - 1)
            save_game(uid, game)
            text = f"{message}\n(Остаток огня: {game.campfire_durability}/{game.campfire_max_durability})"
            kb = get_campfire_kb(game)
            await safe_edit_message(chat_id, callback.message.message_id, text, kb)
            await callback.answer()
            return
        elif data.startswith("cook_recipe_view_"):
            # Карточка рецепта костра перед готовкой
            recipe_id = data.removeprefix("cook_recipe_view_")
            text = format_recipe_card(recipe_id)
            kb = get_campfire_recipe_view_kb(recipe_id)
            await safe_edit_message(chat_id, callback.message.message_id, text, kb)
            await callback.answer()
            return
        elif data == "inv_craft":
            game.push_screen("craft")
            unlocked = list(getattr(game, "unlocked_crafts", ["РљРѕСЃС‚С‘СЂ", "Р¤Р°РєРµР»"]) or ["РљРѕСЃС‚С‘СЂ", "Р¤Р°РєРµР»"])
            kb_c = types.InlineKeyboardMarkup(inline_keyboard=[])
            lines = ["рџ”Ё РљСЂР°С„С‚ (С‚РѕР»СЊРєРѕ РѕС‚РєСЂС‹С‚С‹Рµ СЂРµС†РµРїС‚С‹):", ""]
            for name in unlocked:
                if name not in CRAFT_RECIPES:
                    continue
                mark = craft_mark(game, name)
                ings = ", ".join(f"{n}Г—{q}" for n, q in CRAFT_RECIPES[name])
                lines.append(f"{name} {mark} вЂ” {ings}")
                kb_c.inline_keyboard.append([
                    types.InlineKeyboardButton(
                        text=f"рџ”Ё {name} {mark}",
                        callback_data=f"craft_{name}",
                    )
                ])
            if not kb_c.inline_keyboard:
                lines.append("РџРѕРєР° РЅРµС‡РµРіРѕ РєСЂР°С„С‚РёС‚СЊ.")
            kb_c.inline_keyboard.append([types.InlineKeyboardButton(text="в†©пёЏ РќР°Р·Р°Рґ", callback_data="action_2")])
            text = "\n".join(lines)
            kb = kb_c

        elif data == "campfire_confirm_light":
            if game.inventory.get("Костёр", 0) < 1:
                game.add_log("Нет костра в инвентаре.")
                text = game.get_ui()
                kb = get_main_kb(game)
            elif game.ap < 2:
                game.add_log("Не хватает очков действий, чтобы развести костёр (требуется 2 ⚡).")
                text = game.get_ui()
                kb = get_main_kb(game)
            else:
                campfire_result = game.light_campfire()
                if not campfire_result.get("lit"):
                    game.add_log("Не удалось развести костёр (не хватает сил).")
                    text = game.get_ui()
                    kb = get_main_kb(game)
                else:
                    game.inventory["Костёр"] -= 1
                    if game.inventory["Костёр"] <= 0:
                        del game.inventory["Костёр"]
                    game.add_log("🔥 Костёр успешно разведён (10/10)! Кнопка костра теперь доступна на главном экране.")
                    text = game.get_ui()
                    kb = get_main_kb(game)

        elif data == "inv_recipes":
            unlocked = list(getattr(game, "unlocked_crafts", ["РљРѕСЃС‚С‘СЂ", "Р¤Р°РєРµР»"]) or ["РљРѕСЃС‚С‘СЂ", "Р¤Р°РєРµР»"])
            lines = ["рџ“њ Р РµС†РµРїС‚С‹:", ""]
            for name in unlocked:
                if name not in CRAFT_RECIPES:
                    lines.append(f"вЂў {name}")
                    continue
                mark = craft_mark(game, name)
                ings = ", ".join(f"{n}Г—{q}" for n, q in CRAFT_RECIPES[name])
                lines.append(f"вЂў {name} {mark}")
                lines.append(f"  ({ings})")
            text = "\n".join(lines)
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="в†©пёЏ РќР°Р·Р°Рґ", callback_data="action_2")]
            ])

        elif data == "campfire_screen":
            # Р­РєСЂР°РЅ РєРѕСЃС‚СЂР°
            max_durability = game.campfire_max_durability
            durability = game.campfire_durability
            text = f"рџ”Ґ РљРћРЎРўРЃР \nРџСЂРѕС‡РЅРѕСЃС‚СЊ РїР»Р°РјРµРЅРё: {durability}/{max_durability} РґРµР»РµРЅРёР№."
            kb = get_campfire_kb(game)
        elif data == "menu_campfire":
            # РњРµРЅСЋ РєРѕСЃС‚СЂР° (РѕСЃРЅРѕРІРЅРѕРµ)
            text = f"рџ”Ґ РљРћРЎРўРЃР \nРџСЂРѕС‡РЅРѕСЃС‚СЊ РїР»Р°РјРµРЅРё: {game.campfire_durability}/{game.campfire_max_durability} РґРµР»РµРЅРёР№."
            kb = get_campfire_kb(game)
        elif data == "campfire_add_fuel_menu":
            # РџРѕРґРјРµРЅСЋ РІС‹Р±РѕСЂР° РґСЂРѕРІ
            text = "Р’С‹Р±РµСЂРёС‚Рµ, СЃРєРѕР»СЊРєРѕ РґСЂРѕРІ РїРѕРґРєРёРЅСѓС‚СЊ:"
            kb = get_campfire_fuel_kb(game)
        elif data == "campfire_fuel_max":
            # Р”Рѕ РјР°РєСЃРёРјСѓРјР°
            if "Р’РµС‚РєР°" in game.inventory:
                needed = game.campfire_max_durability - game.campfire_durability
                branches = game.inventory["Р’РµС‚РєР°"]
                if branches == 0 or needed == 0:
                    text = "РљРѕСЃС‚С‘СЂ РїРѕС‡С‚Рё РїРѕР»РѕРЅ РёР»Рё РІРµС‚РѕРє РЅРµС‚!"
                    kb = types.InlineKeyboardMarkup(inline_keyboard=[
                        [types.InlineKeyboardButton(text="[ в¬…пёЏ РќР°Р·Р°Рґ РІ РєРѕСЃС‚С‘СЂ ]", callback_data="menu_campfire")]
                    ])
                else:
                    to_use = min(branches, needed)
                    game.inventory["Р’РµС‚РєР°"] -= to_use
                    if game.inventory["Р’РµС‚РєР°"] <= 0:
                        del game.inventory["Р’РµС‚РєР°"]
                    game.campfire_durability += to_use
                    text = f"рџЄµ Р”РѕР±Р°РІР»РµРЅРѕ РІРµС‚РѕРє: {to_use}. РџСЂРѕС‡РЅРѕСЃС‚СЊ РєРѕСЃС‚СЂР°: {game.campfire_durability}/{game.campfire_max_durability}."
                    kb = get_campfire_kb(game)
            else:
                text = "РќРµС‚ РІРµС‚РѕРє РІ РёРЅРІРµРЅС‚Р°СЂРµ!"
                kb = types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="[ в¬…пёЏ РќР°Р·Р°Рґ РІ РєРѕСЃС‚С‘СЂ ]", callback_data="menu_campfire")]
                ])
        elif data == "campfire_fuel_custom":
            # РЎРІРѕС‘ РєРѕР»РёС‡РµСЃС‚РІРѕ вЂ” Р¶РґС‘Рј РІРІРѕРґР° РѕС‚ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ
            text = "РЎРєРѕР»СЊРєРѕ РІРµС‚РѕРє РїРѕРґРєРёРЅСѓС‚СЊ?"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="[ в¬…пёЏ РќР°Р·Р°Рґ РІ РєРѕСЃС‚С‘СЂ ]", callback_data="menu_campfire")]
            ])
        elif data == "campfire_cook_single":
            # РџРѕР¶Р°СЂРёС‚СЊ РѕРґРёРЅ РїСЂРµРґРјРµС‚ вЂ” РІС‹Р±РёСЂР°РµРј РёР· РёРЅРІРµРЅС‚Р°СЂСЏ
            text = "рџҐ© Р§С‚Рѕ РїРѕР¶Р°СЂРёС‚СЊ?"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="рџЌ– РњСЏСЃРѕ", callback_data="campfire_cook_meat")],
                [types.InlineKeyboardButton(text="рџЌ„ Р“СЂРёР±С‹", callback_data="campfire_cook_mushroom")],
                [types.InlineKeyboardButton(text="рџҐ• РћРІРѕС‰Рё", callback_data="campfire_cook_veg")],
                [types.InlineKeyboardButton(text="в¬…пёЏ РќР°Р·Р°Рґ", callback_data="menu_campfire")],
            ])
        elif data == "campfire_recipes":
            # Список рецептов из modules/cooking.py (ранжированы по качеству)
            text = "📜 **Рецепты костра**\nВыберите блюдо, чтобы узнать ингредиенты, эффекты и приготовить:"
            kb = types.InlineKeyboardMarkup(inline_keyboard=[])
            for recipe_id, label in list_recipes():
                kb.inline_keyboard.append([
                    types.InlineKeyboardButton(text=label, callback_data=f"cook_recipe_view_{recipe_id}")
                ])
            kb.inline_keyboard.append([
                types.InlineKeyboardButton(text="⬅️ Назад в костёр", callback_data="menu_campfire")
            ])
            text += f"\nВсего доступно {len(COOKING_RECIPES)} рецептов."
        elif data.startswith("campfire_recipe_"):
            text = "Выберите рецепт из списка."
            kb = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="📜 Рецепты", callback_data="campfire_recipes")],
                [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_campfire")],
            ])
        elif data.startswith("campfire_ingredient_"):
            recipe = data.removeprefix("campfire_ingredient_")
            ingredient = data.removeprefix("campfire_ingredient_").split("_")[-1]
            text = f"Выбираем {ingredient}..."
            kb = get_campfire_recipe_kb(game, recipe)
        elif data == "inv_inspect":
            items_in_inv = [item for item, c in game.inventory.items() if c > 0]
            if not items_in_inv:
                await callback.answer("Инвентарь пуст!", show_alert=True)
                return
            game.push_screen("inspect")
            text = "🔍 **Подробный осмотр предметов**\n\nВыберите предмет из инвентаря, чтобы изучить его описание, эффекты, риски и свойства:"
            kb = get_inspect_menu_kb(game)

        elif data.startswith("inspect_item_"):
            item = data.removeprefix("inspect_item_")
            text = format_item_card(item)
            kb = get_item_card_actions_kb(item, game)

        elif data.startswith("use_preview_"):
            item = data.removeprefix("use_preview_")
            text = format_item_card(item)
            kb = get_item_card_actions_kb(item, game)

        elif data == "inv_use":
            usable = get_usable_items(game)
            if not usable:
                return
            game.push_screen("use")
            text = "Р’С‹Р±РµСЂРёС‚Рµ РїСЂРµРґРјРµС‚ РґР»СЏ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ:"
            kb = get_use_item_kb(game)

        elif data == "inv_drop":
            if not any(count > 0 for count in game.inventory.values()):
                return
            game.push_screen("drop")
            text = "Р’С‹Р±РµСЂРёС‚Рµ РїСЂРµРґРјРµС‚ РґР»СЏ СѓРґР°Р»РµРЅРёСЏ:"
            kb = get_drop_item_kb(game)

        elif data.startswith("use_consumable_"):
            item = data.removeprefix("use_consumable_")
            if item == "Костёр":
                if game.inventory.get("Костёр", 0) < 1:
                    game.add_log("Нет костра в инвентаре.")
                    text = game.get_ui()
                    kb = get_main_kb(game)
                elif game.ap < 2:
                    game.add_log("Не хватает очков действий для розжига костра (требуется 2 ⚡).")
                    text = game.get_ui()
                    kb = get_main_kb(game)
                else:
                    text = (
                        "Ты складываешь камни и ветки в аккуратную кладку. "
                        "Искра цепляется за мох — и огонь готов родиться. "
                        "В круге света теплее не только телу: даже лес будто "
                        "отступает на шаг. Некоторые звери обойдут стоянку стороной."
                        + "\n\n"
                        + "Затраты: 2 ⚡, голод −7 (с модификаторами), жажда −18 (с модификаторами)."
                        + "\n"
                        + "После розжига на главном экране появится костёр (10/10) и откроются рецепты готовки."
                    )
                    kb = get_campfire_light_confirm_kb()
            elif item == "Бутылка воды":
                text = (
                    "🧴 Бутылка чистой воды (20 глотков).\n\n"
                    "Ты можешь надеть её на пояс (в слот фляги), чтобы кнопка «💧 Пить» появилась на главном экране, либо сделать один глоток прямо сейчас."
                )
                kb = get_bottle_actions_kb()
            else:
                result = use_consumable(item, game)
                if result is not None:
                    text = result
                    kb = get_main_kb(game)

        elif data == "equip_bottle_flask":
            if game.inventory.get("Бутылка воды", 0) > 0:
                game.inventory["Бутылка воды"] -= 1
                if game.inventory["Бутылка воды"] <= 0:
                    del game.inventory["Бутылка воды"]
                game.equipment["flask"] = "Бутылка воды"
                game.flask_water = 20
                game.add_log("🧴 Бутылка воды экипирована в слот фляги (20/20). Теперь кнопка «Пить» доступна на главном экране!")
            else:
                game.add_log("В инвентаре нет бутылки воды.")
            text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "drink_bottle_single":
            if game.equipment.get("flask") and getattr(game, "flask_water", 0) > 0:
                game.flask_water -= 1
                game.thirst = min(100, game.thirst + 15)
                game.add_log(f"💧 Ты сделал глоток воды (+15 жажды). Во фляге: {game.flask_water}/20.")
                if game.flask_water <= 0:
                    container_name = game.equipment.get("flask") or "Бутылка воды"
                    game.equipment["flask"] = None
                    game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1
                    game.add_log(f"Ёмкость «{container_name}» опустошена! В инвентаре осталась пустая бутылка.")
            elif game.inventory.get("Бутылка воды", 0) > 0:
                game.inventory["Бутылка воды"] -= 1
                if game.inventory["Бутылка воды"] <= 0:
                    del game.inventory["Бутылка воды"]
                game.equipment["flask"] = "Бутылка воды"
                game.flask_water = 19
                game.thirst = min(100, game.thirst + 15)
                game.add_log("🧴 Ты экипировал бутылку на пояс и сделал глоток (+15 жажды). Во фляге: 19/20.")
            else:
                game.add_log("Нет доступной воды для питья.")
            text = game.get_ui()
            kb = get_main_kb(game)
        elif data.startswith("drop_item_"):
            item = data.removeprefix("drop_item_")
            if game.inventory.get(item, 0) > 0:
                game.push_screen("drop_qty")
                current_count = game.inventory[item]
                text = f"РЎРєРѕР»СЊРєРѕ РІС‹РєРёРЅСѓС‚СЊ В«{item}В»?\nР’ РёРЅРІРµРЅС‚Р°СЂРµ: {current_count} С€С‚."
                kb = get_drop_quantity_kb(item)

        elif data.startswith("drop_qty:"):
            parts = data.split(":", 2)
            if len(parts) < 3:
                return
            qty_type = parts[1]
            item = parts[2]
            current_count = game.inventory.get(item, 0)
            if current_count <= 0:
                while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
                    game.nav_stack.pop()
                text = f"РџСЂРµРґРјРµС‚Р° В«{item}В» РЅРµС‚ РІ РёРЅРІРµРЅС‚Р°СЂРµ.\n\n{game.get_inventory_text()}"
                kb = inventory_inline_kb
            else:
                drop_count = 0
                if qty_type == "1":
                    drop_count = 1
                elif qty_type == "all":
                    drop_count = current_count
                elif qty_type == "custom":
                    game.story_state = "WAITING_FOR_DROP_QUANTITY"
                    game.story_flags["drop_item_name"] = item
                    text = f"Р’РІРµРґРёС‚Рµ РєРѕР»РёС‡РµСЃС‚РІРѕ В«{item}В» РґР»СЏ РІС‹Р±СЂРѕСЃР°:\n(Р”РѕСЃС‚СѓРїРЅРѕ: {current_count} С€С‚.)"
                    kb = types.InlineKeyboardMarkup(inline_keyboard=[
                        [types.InlineKeyboardButton(text="в¬…пёЏ РќР°Р·Р°Рґ", callback_data="drop_qty_cancel")]
                    ])
                    if text is not None:
                        game.record_route(data)
                        await update_or_send_message(chat_id, uid, text, kb)
                        save_game(uid, game)
                    return

                if drop_count > 0:
                    while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
                        game.nav_stack.pop()
                    game.inventory[item] -= drop_count
                    if game.inventory[item] <= 0:
                        del game.inventory[item]
                    game.add_log(f"Р’С‹РєРёРЅСѓС‚Рѕ: {item} Г—{drop_count}")
                    text = f"РЈРґР°Р»РµРЅРѕ: {item} Г—{drop_count}.\n\n{game.get_inventory_text()}"
                    kb = inventory_inline_kb

        elif data == "drop_qty_cancel":
            game.story_state = None
            if "drop_item_name" in game.story_flags:
                del game.story_flags["drop_item_name"]
            prev = game.pop_screen()
            if prev == "drop_qty":
                prev = game.pop_screen()
            if prev == "drop":
                if any(count > 0 for count in game.inventory.values()):
                    text = "Р’С‹Р±РµСЂРёС‚Рµ РїСЂРµРґРјРµС‚ РґР»СЏ СѓРґР°Р»РµРЅРёСЏ:"
                    kb = get_drop_item_kb(game)
                else:
                    text = game.get_inventory_text()
                    kb = inventory_inline_kb
            elif prev == "inventory":
                text = game.get_inventory_text()
                kb = inventory_inline_kb
            else:
                text = game.get_ui()
                kb = get_main_kb(game)

        elif data == "back":
            prev = game.pop_screen()
            if prev == "main":
                text = game.get_ui()
                kb = get_main_kb(game)
            elif prev == "inventory":
                text = game.get_inventory_text()
                kb = inventory_inline_kb
            elif prev == "character":
                text = game.get_character_text()
                kb = character_inline_kb
            elif prev == "drop":
                text = game.get_inventory_text()
                kb = inventory_inline_kb
            elif prev == "drop_qty":
                if any(count > 0 for count in game.inventory.values()):
                    text = "Р’С‹Р±РµСЂРёС‚Рµ РїСЂРµРґРјРµС‚ РґР»СЏ СѓРґР°Р»РµРЅРёСЏ:"
                    kb = get_drop_item_kb(game)
                else:
                    text = game.get_inventory_text()
                    kb = inventory_inline_kb
            elif prev == "craft":
                unlocked = list(getattr(game, "unlocked_crafts", ["РљРѕСЃС‚С‘СЂ", "Р¤Р°РєРµР»"]) or ["РљРѕСЃС‚С‘СЂ", "Р¤Р°РєРµР»"])
                kb_c = types.InlineKeyboardMarkup(inline_keyboard=[])
                lines = ["рџ”Ё РљСЂР°С„С‚:", ""]
                for name in unlocked:
                    if name not in CRAFT_RECIPES:
                        continue
                    mark = craft_mark(game, name)
                    ings = ", ".join(f"{n}Г—{q}" for n, q in CRAFT_RECIPES[name])
                    lines.append(f"{name} {mark} вЂ” {ings}")
                    kb_c.inline_keyboard.append([
                        types.InlineKeyboardButton(
                            text=f"рџ”Ё {name} {mark}",
                            callback_data=f"craft_{name}",
                        )
                    ])
                if not kb_c.inline_keyboard:
                    lines.append("РџРѕРєР° РЅРµС‡РµРіРѕ РєСЂР°С„С‚РёС‚СЊ.")
                kb_c.inline_keyboard.append([
                    types.InlineKeyboardButton(text="в†©пёЏ РќР°Р·Р°Рґ", callback_data="action_2")
                ])
                text = chr(10).join(lines)
                kb = kb_c
            elif prev == "use":
                text = game.get_ui()
                kb = get_main_kb(game)
            elif prev == "settings":
                text = get_settings_text(game)
                kb = get_settings_kb(game)
            else:
                text = game.get_ui()
                kb = get_main_kb(game)

        elif data.startswith("craft_") or data.startswith("use_item_"):
            text, kb = handle_craft(data, game, uid)
            if text is None:
                text = game.get_inventory_text()
                kb = inventory_inline_kb

        elif data.startswith("river_") or data.startswith("snake_") or data.startswith("story_"):
            text, kb = handle_location_2_ruchey(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data.startswith("slate_") or data.startswith("rest_") or data.startswith("examine"):
            text, kb = handle_location_3_slate_hollow(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data.startswith("hunters_") or data.startswith("glade_"):
            text, kb = handle_location_4_hunters_glade(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data.startswith("slug_") or data.startswith("pit_"):
            text, kb = handle_location_5_slug_pit(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data.startswith("furry_") or data.startswith("warm_") or data.startswith("sleep") or data.startswith("cave_"):
            text, kb = handle_location_6_furry_cave(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data.startswith("sanctuary_") and data != "sanctuary_resolve":
            text, kb = handle_location_7_sanctuary_peak(data, game, uid)
            if text is None:
                text = game.get_ui()
                kb = get_main_kb(game)

        elif data in ("wolf_leave", "wolf_torch", "peek_den", "pet_leave", "pet_take", "story_next"):
            if game.ap <= 0:
                text = "РќРµС‚ СЃРёР». РќСѓР¶РЅРѕ РїРѕСЃРїР°С‚СЊ."
                kb = get_main_kb(game)
            else:
                text, kb = handle_story(data, game, uid)

        elif data == "action_1":
            if game.ap <= 0:
                ap_warning = "Не хватает очков действий! Нужно поспать (Отдых)."
                game.add_log(ap_warning)
                await callback.answer(ap_warning, show_alert=True)
                text = game.get_ui()
                kb = get_main_kb(game)
                if text is not None:
                    await update_or_send_message(chat_id, uid, text, kb)
                    save_game(uid, game)
                return

            deltas = game.consume_action(action_type="search", base_hunger=2, base_thirst=1)
            res_log = format_resource_log_text(deltas)
            if res_log:
                game.add_log(res_log)

            # Счётчик исследований с факелом (факел только в левой руке)
            torch_equipped = (
                game.equipment.get("hand_left") == "Факел"
                or game.equipment.get("hand") == "Факел"
            )
            if torch_equipped:
                torch_research_count = getattr(game, "torch_research_count", 0) + 1
                game.torch_research_count = torch_research_count

                # На 4-м исследовании с факелом — гарантированно 1-я Сюжетная История
                if torch_research_count >= 4:
                    game.add_log(f"{torch_research_count}-е исследование с факелом! Запускаем Главную Сюжетную Историю.")
                    text, kb = handle_story(data, game, uid)
                else:
                    # Логика исследования с факелом: 40% пусто / 20% сломается / 40% добыча
                    roll = random.randint(1, 100)
                    if roll <= 40:
                        # 40% — ничего не найдено, факел цел
                        game.add_log("🔍 Ты внимательно осмотрелся, освещая путь факелом, но ничего ценного не нашёл.")
                    elif roll <= 60:
                        # 20% (41-60) — факел ломается!
                        game.equipment["hand_left"] = None
                        if "hand" in game.equipment:
                            game.equipment["hand"] = None
                        game.ap = max(0, game.ap - 1)
                        game.add_log("💥 Твой факел с треском сломался и потух (−1 ⚡ AP)! Теперь его нужно скрафтить заново.")
                    else:
                        # 40% (61-100) — успешная добыча
                        loc_id = location_id_from_game(game)
                        found_list = roll_find(loc_id)
                        msg = apply_finds_to_inventory(game, found_list)
                        game.add_log(msg)
                    text = game.get_ui()
                    kb = get_main_kb(game)
            else:
                # Без факела — обычный поиск по локации
                loc_id = location_id_from_game(game)
                found_list = roll_find(loc_id)
                msg = apply_finds_to_inventory(game, found_list)
                game.add_log(msg)
                text = game.get_ui()
                kb = get_main_kb(game)

        elif data in ("action_sleep", "action_4"):
            game.sleep_and_turn_day()
            trap_msgs = []
            # Утро: 40% пусто / 20% ломка / 40% добыча по таблице локации
            for event in process_trap_rollover(game):
                loc_id = event.get("location_id")
                if event.get("broken"):
                    msg = f"Ловушка на локации {loc_id}: сломалась, добычи нет."
                    game.add_log(msg)
                    trap_msgs.append(msg)
                    continue
                animal = event.get("animal")
                loot = event.get("loot") or {}
                if loot:
                    apply_trap_loot_to_inventory(game, loot)
                    loot_txt = ", ".join(f"{k}×{v}" for k, v in loot.items())
                    msg = f"Ловушка на локации {loc_id}: {animal} (+{loot_txt})"
                    game.add_log(msg)
                    trap_msgs.append(msg)
                elif animal:
                    msg = f"Ловушка на локации {loc_id}: {animal}"
                    game.add_log(msg)
                    trap_msgs.append(msg)
                trap = getattr(game, "traps", {}).get(loc_id)
                if trap:
                    trap["pending_animal"] = None
                    trap["pending_loot"] = None
            if trap_msgs:
                text = game.get_ui() + "\n" + "\n".join(trap_msgs)
            else:
                text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "action_3":
            # Пить из экипированной бутылки/фляги
            if game.equipment.get("flask"):
                water_left = int(getattr(game, "flask_water", 0) or 0)
                if water_left > 0:
                    game.flask_water = water_left - 1
                    game.thirst = min(100, game.thirst + 15)
                    game.add_log(f"💧 Ты сделал глоток воды из бутылки (+15 жажды). Во фляге: {game.flask_water}/20.")
                    if game.flask_water <= 0:
                        container_name = game.equipment.get("flask") or "Бутылка воды"
                        game.equipment["flask"] = None
                        game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1
                        game.add_log(f"Ёмкость «{container_name}» опустошена! В инвентаре осталась пустая бутылка.")
                else:
                    container_name = game.equipment.get("flask") or "Бутылка воды"
                    game.equipment["flask"] = None
                    game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1
                    game.add_log(f"Ёмкость «{container_name}» опустошена! В инвентаре осталась пустая бутылка.")
            elif game.inventory.get("Бутылка воды", 0) > 0:
                game.add_log("Бутылка в инвентаре не надета! Перейди в инвентарь и нажми «Бутылка воды» -> «Надеть на пояс».")
            elif game.inventory.get("Вода", 0) > 0:
                game.inventory["Вода"] -= 1
                if game.inventory["Вода"] <= 0:
                    del game.inventory["Вода"]
                game.thirst = min(100, game.thirst + 15)
                game.add_log("Ты сделал глоток воды (+15 жажды).")
            else:
                game.add_log("У тебя нет воды для питья.")
            text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "action_light_campfire":
            campfire_result = game.light_campfire()
            if campfire_result.get("lit"):
                res_log = format_resource_log_text(campfire_result)
                if res_log:
                    game.add_log(res_log)
                text = f"рџ”Ґ Р’С‹ СЂР°Р·РІРµР»Рё РєРѕСЃС‚С‘СЂ! (РџСЂРѕС‡РЅРѕСЃС‚СЊ: {game.campfire_durability}/{game.campfire_max_durability})"
                kb = get_campfire_kb(game)
            else:
                text = "РќРµ С…РІР°С‚Р°РµС‚ AP РґР»СЏ РєРѕСЃС‚СЂР°!"
                kb = get_main_kb(game)

        elif data == "action_collect_water":
            if game.weather in {"rain", "storm"} and game.ap > 0:
                game.ap -= 1
                game.inventory["Р’РѕРґР°"] = game.inventory.get("Р’РѕРґР°", 0) + 1
                game.add_log("РўС‹ РЅР°Р±СЂР°Р» РґРѕР¶РґРµРІРѕР№ РІРѕРґС‹!")
                text = "РўС‹ РЅР°Р±СЂР°Р» РґРѕР¶РґРµРІРѕР№ РІРѕРґС‹!"
                kb = get_main_kb(game)
            else:
                text = game.get_ui()
                kb = get_main_kb(game)
        
        elif data == "menu_main":
            text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "karma_escape":
            karma_ok = all(v > 0 for v in game.karma.values())
            if karma_ok:
                game.add_log("РљР°СЂРјР° РёРґРµР°Р»СЊРЅР° вЂ” С‚С‹ СЃР±РµР¶Р°Р» РёР· Р»РµСЃР°!")
                game.story_state = "karma_escape"
            else:
                game.add_log("РљР°СЂРјР° РЅРµ РёРґРµР°Р»СЊРЅР° вЂ” РѕСЃС‚Р°С‘С€СЊСЃСЏ РІ Р»РµСЃСѓ.")
                game.story_state = "karma_stuck"
            text = game.get_ui()
            kb = get_main_kb(game)

        if text is not None:
            game.record_route(data)
            await update_or_send_message(chat_id, uid, text, kb)
            save_game(uid, game)
    except Exception as exc:
        logging.exception(f"РћС€РёР±РєР° callback {data if 'data' in locals() else 'unknown'} РґР»СЏ {uid}: {exc}")
        try:
            await callback.answer("РћС€РёР±РєР° РѕР±СЂР°Р±РѕС‚РєРё РєРЅРѕРїРєРё. РџРѕРїСЂРѕР±СѓР№ РµС‰С‘ СЂР°Р· РёР»Рё /start", show_alert=True)
        except Exception:
            pass

@dp.message(F.text & ~F.text.startswith("/"))
async def process_text_message(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    try:
        raw_text = message.text.strip() if message.text else ""
        text = raw_text[:80] if raw_text else ""
        # РќРёР¶РЅСЏСЏ РєР»Р°РІРёР°С‚СѓСЂР° РѕС‚РєР»СЋС‡РµРЅР°; РµСЃР»Рё РѕСЃС‚Р°Р»Р°СЃСЊ вЂ” С‚Рµ Р¶Рµ РґРµР№СЃС‚РІРёСЏ
        if text in ("рџљЂ РќР°С‡Р°С‚СЊ / РЎС‚Р°СЂС‚", "рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ / РџРµСЂРµР·Р°РїСѓСЃРє", "рџЏ  Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ"):
            await cmd_start(message)
            return
        if text in ("рџ“Љ РЎС‚Р°С‚СѓСЃ", "рџЏ  Р“Р»Р°РІРЅС‹Р№ СЌРєСЂР°РЅ"):
            await cmd_main(message)
            return
        if text in ("рџЋ’ РРЅРІРµРЅС‚Р°СЂСЊ",):
            await cmd_inventory(message)
            return
        if text in ("рџ‘¤ РџРµСЂСЃРѕРЅР°Р¶",):
            await cmd_character(message)
            return
        if text in ("вљ™пёЏ РќР°СЃС‚СЂРѕР№РєРё",):
            await cmd_settings(message)
            return

        game = _ensure_game(uid)
        if not game:
            return

        # Р”РµР»РµРіРёСЂСѓРµРј РґРёР°Р»РѕРіРѕРІС‹Рµ FSM-СЃРѕСЃС‚РѕСЏРЅРёСЏ РІ services/dialogs.py
        from services.dialogs import process_text_input
        bot_ctx = {
            "last_active_msg_id": last_active_msg_id,
            "safe_edit_message": safe_edit_message,
            "safe_delete_message": safe_delete_message,
            "update_or_send_message": update_or_send_message,
            "format_game_text": format_game_text,
            "inventory_inline_kb": inventory_inline_kb,
            "get_campfire_kb": get_campfire_kb,
        }
        await process_text_input(uid, chat_id, text, message, game, bot_ctx)

    except Exception as exc:
        logging.exception(f"РћС€РёР±РєР° process_text_message РґР»СЏ {uid}: {exc}")
        try:
            await message.answer("РЇ РЅРµ СЃРјРѕРі РѕР±СЂР°Р±РѕС‚Р°С‚СЊ СЌС‚Рѕ СЃРѕРѕР±С‰РµРЅРёРµ. РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰С‘ СЂР°Р·.")
        except Exception:
            pass



# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
# РЎР•Р Р’Р•Р  Р РџРРќР“
# в”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђв”Ђ
from services.server import keep_alive_pinger, start_health_check_server, PING_URLS


async def run_bot():
    """Р—Р°РїСѓСЃС‚РёС‚СЊ polling Рё РіР°СЂР°РЅС‚РёСЂРѕРІР°РЅРЅРѕ Р·Р°РєСЂС‹С‚СЊ РІРЅРµС€РЅРёРµ СЂРµСЃСѓСЂСЃС‹ РїСЂРё РѕСЃС‚Р°РЅРѕРІРєРµ."""
    await start_health_check_server()
    
    # Р—Р°РїСѓСЃРє РїРёРЅРіР° РІ РѕС‚РґРµР»СЊРЅРѕРј task вЂ” С‡С‚РѕР±С‹ РЅРµ РјРµС€Р°Р» Р·Р°РїСѓСЃРєСѓ Р±РѕС‚Р°
    pinger_task = asyncio.create_task(keep_alive_pinger(300))
    
    try:
        # Р”Р°РµРј СЃРµСЂРІРµСЂСѓ "РѕС‚РґРѕС…РЅСѓС‚СЊ" РїРµСЂРµРґ СѓСЃС‚Р°РЅРѕРІРєРѕР№ РєРѕРјР°РЅРґ
        logging.info("РЎРµСЂРІРµСЂ Р·Р°РїСѓС‰РµРЅ вЂ” РґР°РµРј РµРјСѓ 10 СЃРµРєСѓРЅРґ РЅР° 'СЂР°Р·РѕРіСЂРµРІ'...")
        await asyncio.sleep(10)
        logging.info("Р—Р°РїСѓСЃРєР°РµРј РєРѕРјР°РЅРґС‹ Р±РѕС‚Р°...")
        # РћР±РµСЂС‚С‹РІР°РµРј РєРѕРјР°РЅРґС‹ РІ try/except вЂ” aiogram РјРѕР¶РµС‚ СЂРѕРЅСЏС‚СЊ Unauthorized РЅР° СѓР¶Рµ Р·Р°РїСѓС‰РѕРЅРЅРѕРј Р±РѕС‚Рµ
        try:
            await bot.set_my_commands([
                types.BotCommand(command="start", description="РќР°С‡Р°С‚СЊ РІС‹Р¶РёРІР°РЅРёРµ"),
                types.BotCommand(command="main", description="Р“Р»Р°РІРЅС‹Р№ СЌРєСЂР°РЅ"),
                types.BotCommand(command="inventory", description="РРЅРІРµРЅС‚Р°СЂСЊ"),
                types.BotCommand(command="character", description="РџРµСЂСЃРѕРЅР°Р¶"),
                types.BotCommand(command="settings", description="РќР°СЃС‚СЂРѕР№РєРё"),
            ])
            await bot.delete_webhook(drop_pending_updates=False)
            logging.info("РљРѕРјР°РЅРґС‹ СѓСЃС‚Р°РЅРѕРІР»РµРЅС‹ вЂ” Р·Р°РїСѓСЃРєР°РµРј polling...")
            await dp.start_polling(bot)
        except Exception as cmd_err:
            logging.error(f"РћС€РёР±РєР° РїСЂРё РЅР°СЃС‚СЂРѕР№РєРµ РєРѕРјР°РЅРґ: {cmd_err}")
            # РџСЂРѕРґРѕР»Р¶Р°РµРј polling вЂ” РѕРЅ СЃР°Рј РѕР±СЂР°Р±РѕС‚Р°РµС‚ РєРѕРјР°РЅРґС‹
            await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"РћС€РёР±РєР° РІ РѕСЃРЅРѕРІРЅРѕРј РїРѕС‚РѕРєРµ Р±РѕС‚Р°: {e}")
        # РџРµСЂРµР·Р°РїСѓСЃРєР°РµРј РїРёРЅРі, РµСЃР»Рё Р±РѕС‚ СѓРїР°Р»
        if pinger_task.done() and not pinger_task.cancelled():
            logging.warning("РџРёРЅРіРµСЂ Р·Р°РІРµСЂС€РёР» СЂР°Р±РѕС‚Сѓ вЂ” РїРµСЂРµР·Р°РїСѓСЃРєР°РµРј РµРіРѕ...")
            pinger_task = asyncio.create_task(keep_alive_pinger(300))
    finally:
        from services.database import mongo_client
        if mongo_client is not None:
            mongo_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_bot())

