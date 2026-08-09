"""
Тестовый файл для проверки логики Game
"""

from collections import Counter

class Game:
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

game = Game()
game.add_log("Твои действия:")

print("Location:", game.location)
print("Story:", game.story_state)
print("Inventory:", dict(game.inventory))
