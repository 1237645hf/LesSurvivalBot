import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import re
from game_state import Game
from story.location_stories import handle_story, is_story_callback

with open("story/location_stories.py", "r", encoding="utf-8") as f:
    code = f.read()

# All callback_data from buttons in location_stories.py
button_cbs = sorted(set(re.findall(r'callback_data=[\'"]([^\'"]+)[\'"]', code)))
print(f"Total button callbacks defined in location_stories.py: {len(button_cbs)}")

# Also all callback_data from keyboards.py related to locations
with open("keyboards.py", "r", encoding="utf-8") as f:
    kb_code = f.read()
kb_cbs = sorted(set(re.findall(r'callback_data=[\'"]([^\'"]+)[\'"]', kb_code)))

location_related_kb_cbs = [
    cb for cb in kb_cbs
    if any(cb.startswith(p) for p in ("location_", "l1_", "l2_", "l3_", "l4_", "l5_", "l6_", "l7_", "wolf_", "boar_", "trap_"))
    or cb in ("locations_menu", "tablet_notes_view", "tablet_notes_edit", "l5_bait_menu", "l5_slug_ambush", "l5_bait_remove")
]

print(f"Location-related callbacks from keyboards.py: {len(location_related_kb_cbs)}")

all_cbs_to_test = sorted(set(button_cbs + location_related_kb_cbs))

# Test each one
results = {"ok": 0, "none": [], "crash": [], "not_in_is_story": []}

for cb in all_cbs_to_test:
    # Generic main navigation callbacks
    if cb in ("back", "menu_main", "locations_menu", "action_1", "action_2", "action_3", "action_4", "noop", "start_new_game_confirmed", "location_enter_1"):
        results["ok"] += 1
        continue
    
    if not is_story_callback(cb) and not any(cb.startswith(p) for p in ("trap_", "tablet_page:", "tablet_notes_")):
        results["not_in_is_story"].append(cb)

    # Initialize a well-equipped game
    game = Game()
    game.ap = 20
    game.hp = 100
    game.thirst = 50
    game.hunger = 50
    game.inventory["Факел"] = 1
    game.inventory["Крепкий посох"] = 1
    game.inventory["Сланцевая пластина"] = 10
    game.inventory["Слизь"] = 10
    game.inventory["Ветка"] = 10
    game.inventory["Кусок коры"] = 10
    game.inventory["Камень"] = 10
    game.inventory["Светящийся гриб"] = 5
    game.inventory["Янтарная слизь"] = 5
    game.inventory["Приманка для слизней"] = 2
    game.inventory["Костяной амулет охотника"] = 1
    game.inventory["Рюкзак с красной заплаткой"] = 1
    game.equipment["hand_left"] = "Факел"
    game.equipment["hand_right"] = "Крепкий посох"
    game.equipment["pet"] = "Барсик"
    game.set_story_flag("has_pet", True)
    game.set_story_flag("l1_completed", True)
    game.set_story_flag("l2_completed", True)
    game.set_story_flag("l3_shelter_unlocked", True)
    game.set_story_flag("l4_completed", True)
    game.set_story_flag("l5_completed", True)

    try:
        # If it's a story callback:
        if is_story_callback(cb):
            text, kb = handle_story(cb, game, 12345)
            if text is None:
                results["none"].append(cb)
            else:
                results["ok"] += 1
        else:
            # Trap or tablet callback
            results["ok"] += 1
    except Exception as e:
        results["crash"].append((cb, f"{type(e).__name__}: {e}"))

print(f"\nRESULTS:")
print(f"  OK: {results['ok']}")
print(f"  NOT recognized by is_story_callback: {results['not_in_is_story']}")
print(f"  Returned text=None: {results['none']}")
print(f"  Crashed: {results['crash']}")
