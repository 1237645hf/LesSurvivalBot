import sys, os, re
sys.path.insert(0, os.path.abspath('.'))
from story.location_stories import is_story_callback

with open('story/locations/loc5_slug_pit.py', encoding='utf-8') as f:
    content = f.read()

cbs = re.findall(r'callback_data=["\']([^"\']+)["\']', content)
unique_cbs = sorted(set(cbs))

not_story = []
for cb in unique_cbs:
    if cb in ('back', 'menu_main', 'already_here', 'locations_menu', 'location_enter_1', 'location_enter_2', 'location_enter_3', 'location_enter_4', 'location_enter_5', 'location_enter_6', 'location_enter_7'):
        continue
    if not is_story_callback(cb):
        not_story.append(cb)

print('Callbacks not recognized by is_story_callback:', not_story)
