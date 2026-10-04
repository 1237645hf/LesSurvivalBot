import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import re

from game_state import Game, handle_back_navigation
from keyboards import get_locations_kb, get_main_kb
from story.location_stories import is_story_callback, handle_story
from main import (
    is_session_callback,
    is_tablet_callback,
    is_traps_callback,
    is_inventory_callback,
    is_campfire_callback,
    is_craft_callback,
    is_explore_callback,
)

def simulate_callback(data: str, game: Game, uid: int = 12345):
    """Simulate main.py callback routing logic."""
    if data == "noop":
        return "noop", None
    if data in ("menu_character", "inv_character", "character_screen"):
        game.push_screen("character")
        return game.get_character_text(), None
    if data == "locations_menu":
        game.push_screen("locations")
        return "Куда направиться?", get_locations_kb(game)
    if data == "location_enter_1":
        game.current_location = "Стартовый лес"
        game.reset_nav()
        return game.get_ui(), get_main_kb(game)
    if data in ("back", "back_to_inv", "inv_back"):
        return handle_back_navigation(game, uid)
    if data == "menu_main":
        game.active_story_callback = None
        return game.get_ui(), get_main_kb(game)
    if is_story_callback(data):
        return handle_story(data, game, uid)
    
    return None, None

def get_buttons_from_kb(kb):
    buttons = []
    if not kb:
        return buttons
    inline_keyboard = getattr(kb, "inline_keyboard", None)
    if inline_keyboard is None and isinstance(kb, list):
        inline_keyboard = kb
    if inline_keyboard:
        for row in inline_keyboard:
            for btn in row:
                if hasattr(btn, "callback_data") and btn.callback_data:
                    buttons.append((btn.text, btn.callback_data))
    return buttons

# Known non-story callbacks that can appear on screens:
GENERIC_ALLOWED = {
    "back", "menu_main", "locations_menu", "action_1", "action_2", "action_3", "action_4",
    "noop", "start_new_game_confirmed", "kitten_to_main", "story_next",
    "l1_dome_leave", "l1_dome_leave_final", "menu_campfire", "tablet_notes_view",
    "menu_character", "inv_inspect", "inv_craft", "inv_drop", "action_sleep",
    "fuel_menu:sticks", "fuel_menu:bark", "fuel_menu:coal", "campfire_recipes",
    "campfire_add_fuel_menu", "stove_rekindle", "campfire_boil_water",
    "action_collect_water", "action_fill_rain_bottle", "location_enter_1",
    "equip_bottle_flask", "drink_bottle_single", "equip_army_flask", "drink_rain_bottle",
    "use_item_Факел", "use_item_Крепкий посох", "use_item_Рюкзак с красной заплаткой",
    "use_item_Сланцевая маска", "use_item_Сланцевый панцирь", "use_item_Сланцевые поножи",
    "use_item_Сланцевые ботинки", "use_item_Отремонтированные ботинки", "use_item_Окованный посох",
    "use_item_Клык волка", "use_item_Охотничья ловушка", "use_item_Приманка для слизней",
    "use_item_Старый фонарь", "use_item_Костяной амулет охотника", "l5_bait_menu",
    "trap_place_1", "trap_place_2", "trap_place_3", "trap_place_4", "trap_place_5",
    "trap_place_6", "trap_place_7",
}

# Starting points for all locations and sub-stories
start_points = {
    "L1 - Dome": "l1_dome_enter",
    "L1 - Wolf Lair Entrance": "wolf_lair_enter",
    "L1 - Wolf Lair Story (L1.5)": "l1_5_start",
    "L1 - Prologue (Cat)": "forest_start",
    "L2 - River / Dam": "location_enter_2",
    "L2 - Puzzle": "l2_puzzle_start",
    "L3 - Slate Hollow Entrance": "location_enter_3",
    "L3 - Oven Story (L3.1)": "l3_1_fire_low",
    "L3 - Boar Story (L3.7)": "l3_7_morning",
    "L3 - Boar Battle Direct": "location_enter_boar",
    "L4 - Entrance": "location_enter_4",
    "L4 - Ch0 Deer (L4.1)": "l4_1_entry",
    "L4 - Ch1 Cliff": "l4_ch1_1_cliff",
    "L4 - Ch2 Pack": "l4_ch2_1_shadow",
    "L4 - Ch3 Shelter": "l4_ch3_1_shelter",
    "L5 - Slug Pit Entrance": "location_enter_5",
    "L5 - Slug Pit Story Start": "slug_pit_start",
    "L5 - Slug Ambush": "l5_slug_ambush",
    "L6 - Furry Cave Entrance": "location_enter_6",
    "L6 - Furry Cave Story Start": "furry_cave_start",
    "L7 - Sanctuary Peak Entrance": "location_enter_7",
    "L7 - Sanctuary Story Start": "sanctuary_peak_start",
}

print("="*60)
print("TRAVERSING ALL LOCATION BUTTON PATHS")
print("="*60)

for loc_name, start_cb in start_points.items():
    print(f"\n--- Checking {loc_name} (start: {start_cb}) ---")
    visited = set()
    queue = [start_cb]
    broken = []
    total_screens = 0

    while queue:
        cb = queue.pop(0)
        if cb in visited:
            continue
        visited.add(cb)
        total_screens += 1

        # Create a game state suitable for testing
        game = Game()
        game.ap = 20
        game.hp = 100
        game.thirst = 50
        game.hunger = 50
        # equip relevant items
        game.inventory["Факел"] = 1
        game.inventory["Крепкий посох"] = 1
        game.inventory["Сланцевая пластина"] = 10
        game.inventory["Слизь"] = 10
        game.inventory["Ветка"] = 10
        game.inventory["Кусок коры"] = 10
        game.inventory["Камень"] = 10
        game.equipment["hand_left"] = "Факел"
        game.equipment["hand_right"] = "Крепкий посох"

        try:
            text, kb = simulate_callback(cb, game)
            if text is None:
                broken.append((cb, "Returned text is None"))
                continue
            
            buttons = get_buttons_from_kb(kb)
            for btn_text, target_cb in buttons:
                # Do not recurse infinitely into generic nav or repeat
                if target_cb not in visited:
                    if target_cb in GENERIC_ALLOWED or target_cb.startswith("pocket_") or target_cb.startswith("use_preview_") or target_cb.startswith("use_consumable_"):
                        continue
                    if not is_story_callback(target_cb) and target_cb != "location_enter_1":
                        broken.append((f"{cb} -> [{btn_text}] ({target_cb})", "NOT recognized by is_story_callback or main router"))
                    else:
                        queue.append(target_cb)

        except Exception as e:
            broken.append((cb, f"CRASH: {type(e).__name__}: {e}"))

    print(f"Finished {loc_name}: {total_screens} distinct callbacks checked.")
    if broken:
        print(f"  FOUND {len(broken)} ISSUES:")
        for path, err in broken:
            print(f"    * {path} : {err}")
    else:
        print("  All button paths cleanly routed!")
