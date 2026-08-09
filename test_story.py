"""
Тестирование handle_story с новым state
"""

from collections import Counter
from stories import handle_story
from keyboards import get_main_kb, peek_kb, cat_kb

# Создаём mock game объект
class MockGame:
    def __init__(self):
        self.inventory = Counter({
            "Спички ": 1,
            "Ветка": 1,
            "Факел": 1,
        })
        self.weather = "clear"
        self.location = "Лесной старт"
        self.story_state = "cat_choice"
        self.equipment = {"hand": None}
        
    def add_log(self, text):
        self.log = getattr(self, "log", [])
        self.log.append(text)
        
    def get_ui(self):
        return f"Location: {self.location}\nStory: {self.story_state}\n"

# Создаём экземпляр
game = MockGame()

print("=== Перед handle_story ===")
print(f"Location: {game.location}")
print(f"Story state: {game.story_state}")
print(f"Inventory: {dict(game.inventory)}")

# Тестируем разные состояния
for state in ["cat_choice", "wolf_flee", "wolf_fight", "peek_den"]:
    print(f"\n=== Тест: {state} ===")
    game.story_state = state
    
    text, kb = handle_story(f"{state}_choice", game, "test_uid")
    
    if text:
        print(f"Text: {text}")
    else:
        print("Text: None")
    
    print(f"New story state: {game.story_state}")
