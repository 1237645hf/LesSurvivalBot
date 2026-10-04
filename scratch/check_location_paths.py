import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import re

from game_state import Game
from keyboards import get_locations_kb, get_main_kb
from story.location_stories import (
    is_story_callback,
    handle_story,
    handle_l1_dome,
    handle_l1_wolf_lair,
    handle_location_1_forest_start,
    handle_location_2_ruchey,
    handle_location_3_slate_hollow,
    handle_location_4_hunters_glade,
    handle_location_5_slug_pit,
    handle_location_6_furry_cave,
    handle_location_7_sanctuary_peak,
)

# 1. Collect all callback_data from story/location_stories.py
with open("story/location_stories.py", "r", encoding="utf-8") as f:
    story_content = f.read()

story_cbs = set(re.findall(r'callback_data=[\'"]([^\'"]+)[\'"]', story_content))

print(f"Total callbacks in location_stories.py: {len(story_cbs)}")

# 2. Check which ones are recognized by is_story_callback
unrecognized_story_cbs = []
for cb in story_cbs:
    # special cases that might be handled outside story (e.g. back, menu_main, etc.)
    if cb in ("back", "menu_main", "locations_menu", "action_1", "action_2", "action_3", "action_4"):
        continue
    if not is_story_callback(cb):
        unrecognized_story_cbs.append(cb)

if unrecognized_story_cbs:
    print(f"WARNING: The following {len(unrecognized_story_cbs)} callbacks from location_stories are NOT recognized by is_story_callback:")
    for cb in sorted(unrecognized_story_cbs):
        print(f"  - {cb}")
else:
    print("ALL callbacks in location_stories.py are recognized by is_story_callback (or main nav)!")

# 3. Test handle_story on every single callback from story_cbs
failed_cbs = []
for cb in sorted(story_cbs):
    if cb in ("back", "menu_main", "locations_menu"):
        continue
    game = Game()
    # Give some items/stats so requirements don't arbitrarily crash
    game.inventory["Факел"] = 1
    game.inventory["Крепкий посох"] = 1
    game.inventory["Сланцевая пластина"] = 5
    game.equipment["hand_left"] = "Факел"
    game.equipment["hand_right"] = "Крепкий посох"
    game.ap = 10
    game.hp = 100
    game.thirst = 50
    game.hunger = 50
    
    try:
        text, kb = handle_story(cb, game, 12345)
        if text is None and kb is None:
            failed_cbs.append((cb, "Returned (None, None)"))
    except Exception as e:
        failed_cbs.append((cb, f"Exception: {type(e).__name__}: {e}"))

if failed_cbs:
    print(f"\nFound {len(failed_cbs)} callbacks that failed in handle_story:")
    for cb, reason in failed_cbs:
        print(f"  - {cb}: {reason}")
else:
    print("\nALL callbacks in location_stories.py returned valid text and kb when called directly via handle_story!")
