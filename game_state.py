"""
game_state.py — Центральное хранилище состояния игры.
Здесь живут кармы, инвентарь, экипировка и история событий.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class GameState:
    """Состояние игры — единый источник правды."""
    
    # Базовые ресурсы
    inventory: Dict[str, int] = field(default_factory=lambda: {
        "Вода": 2,
        "Еда": 3,
        "Спички 🔥": 1,
        "Ветка": 1,
        "Факел": 1,
    })
    
    # Емкость ресурсов
    water_capacity: int = 5
    food_capacity: int = 10
    
    # Жизненные показатели
    hp: int = 100
    hunger: int = 50
    thirst: int = 75
    
    # Экипировка (где?)
    equipment: Dict[str, str] = field(default_factory=lambda: {
        "head": None,
        "chest": None,
        "legs": None,
        "hands": None,
        "feet": None,
        "back": None,
    })
    
    # Атмосфера
    weather: str = "dry"
    
    # Состояние сюжета
    story_state: Optional[str] = None
    
    # Ключевой предмет локации (что запускает сцену)
    current_location_key: str = "Факел"
    
    current_location: str = "Лесной старт"
    location_index: int = 0
    
    # Система кармы
    karma: Dict[str, int] = field(default_factory=lambda: {
        "heroic": 5,      # Славный герой
        "brutal": 3,      # Жёсткий боец
        "gentle": 5,      # Нежный душа
        "clever": 5,      # Хитрый умен
        "reckless": 3,    # Безрассудный
        "mysterious": 5,  # Таинственный
    })
    
    # История событий
    event_log: List[str] = field(default_factory=list)
    
    # Статус кот-компаньона
    companion_name: str = "Кот"
    companion_status: str = "alive"
    
    # Флаг инициализации
    is_initialized: bool = False
    
    # Метод сброса навигации (для завершения локации)
    def reset_nav(self):
        """Сбрасывает навигацию для следующей локации."""
        pass
    
    def __post_init__(self):
        """Инициализация после создания."""
        if not self.is_initialized:
            self._init_default_values()
            self.is_initialized = True
    
    def _init_default_values(self):
        """Установить дефолтные значения для UI."""
        # Умные заглушки для UI
        self.equipment["hands"] = "Руки"  # По умолчанию
        self.equipment["chest"] = "Куртка"
        self.equipment["head"] = "Шапка"
        self.equipment["feet"] = "Ботинки"
    
    def add_log(self, message: str, source: str = "game"):
        """Добавить запись в лог событий."""
        timestamp = datetime.now().strftime("%H:%M")
        self.event_log.append(f"[{timestamp}] {message}")
        # Не ограничивать длину, чтобы история росла
    
    def get_ui_value(self, key: str, fallback: Any = None) -> Any:
        """Умное получение значения для UI с умными заглушками."""
        if key in self.equipment:
            value = self.equipment[key]
            if value and value != "Руки" and value != "Куртка":
                return value
            return self.equipment.get(key, fallback)
        return self.inventory.get(key, fallback)
    
    def get_equipment_slot(self, slot: str, default: str = "Экипировано") -> str:
        """Получить название экипировки в слоте."""
        item = self.equipment.get(slot)
        if item and item != "Руки":
            return f"{item} 🎖️"
        if item:
            return f"{item} 🎖️"
        return default
    
    def calculate_karma_bonus(self) -> Dict[str, int]:
        """Рассчитать бонусы от кармы к характеристикам."""
        stats = {
            "strength": self.karma.get("brutal", 3),
            "agility": self.karma.get("clever", 5),
            "charm": self.karma.get("gentle", 5),
            "mystery": self.karma.get("mysterious", 5),
        }
        return stats
    
    def adjust_karma(self, category: str, amount: int):
        """Изменить карму по категории."""
        if category in self.karma:
            self.karma[category] += amount
            self.add_log(f"Карма {category} изменилась на {amount}", "karma")
    
    def reset_navigate(self):
        """Сброс навигации после сюжетного события."""
        self.story_state = None
        self.add_log("Навигация сброшена", "nav")
    
    def get_karma_title(self) -> str:
        """Получить заголовок кармы для UI."""
        # Находим категорию с наибольшим значением
        if self.karma:
            max_karma = max(self.karma.items(), key=lambda x: x[1])
            return f"{max_karma[0].capitalize()} {max_karma[1]}"
        return "Герой"


# Глобальное состояние игры
game = GameState()
