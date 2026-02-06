import random

class Item:
    def __init__(self, name, icon, desc, weight=1, slot=None, armor=0, uses=1):
        self.name = name
        self.icon = icon
        self.desc = desc
        self.weight = weight
        self.slot = slot
        self.armor = armor
        self.uses = uses

class Game:
    def __init__(self):
        self.hp = 100
        self.hunger = 20
        self.thirst = 60
        self.ap = 5
        self.karma = 0
        self.search_progress = 0  # для сигнала
        self.day = 1
        self.log = ["🌲 Ты проснулся в лесу. Что будешь делать?"]
        self.inventory = [
            Item("Спички", "🔥", "Можно разжечь костёр", 1),
            Item("Вилка", "🍴", "Оружие или инструмент", 1, slot=None),
            Item("Кусок коры", "🪵", "Можно использовать для крафта", 2),
        ]
        self.equipment = {
            "head": None,
            "torso": None,
            "back": None,
            "hands": None,
            "legs": None,
            "feet": None,
            "trinket": None,
        }
        self.max_weight = 20

    def add_log(self, text):
        self.log.append(text)
        if len(self.log) > 20:
            self.log = self.log[-20:]

    def get_ui(self):
        return (
            f"❤️ {self.hp}   🍖 {self.hunger}   💧 {self.thirst}  ⚡ {self.ap}   ☀️ {self.day}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            + "\n".join(f"> {line}" for line in self.log) + "\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

    def get_inventory_text(self):
        return "🎒 Инвентарь:\n" + "\n".join(f"• {item.icon} {item.name} ({item.weight} кг) - {item.desc}" for item in self.inventory) if self.inventory else "🎒 Инвентарь пуст"