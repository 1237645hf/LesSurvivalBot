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
        "Спички ": 1,  # Для совместимости со старым кодом
        "Ветка": 1,
        "Факел": 1,
        "Бутылка воды": 2,  # Для совместимости с Game
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
    
    # Система кармы (6 измерений для эмоционального разветвления)
    karma: Dict[str, int] = field(default_factory=lambda: {
        "heroic": 20,
        "brutal": 5,
        "gentle": 10,
        "clever": 15,
        "reckless": 8,
        "mysterious": 12,
    })
    
    current_location: str = "Лесной старт"
    location_index: int = 0
    
    # Дополнительные поля для совместимости с Game
    ap: int = 5  # Действия в день
    day: int = 1  # Текущий день
    
    # История событий
    event_log: List[str] = field(default_factory=lambda: [
        "[00:00] Ты проснулся в лесу. Что будешь делать?",
    ])
    
    # Статус кот-компаньона
    companion_name: str = "Кот"
    companion_status: str = "alive"
    
    # Флаг инициализации
    is_initialized: bool = False
    
    # Метод сброса навигации (для завершения локации)
    def reset_nav(self):
        """Сбрасывает навигацию для следующей локации."""
        self.current_location = "Лесной старт"
        self.location_index = 0
        
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
    
    def get_karma_progress(self) -> Dict[str, int]:
        """Получить прогресс кармы для финальных развязок."""
        # Проверяем, достигла ли карма определённого порога
        progress = {}
        thresholds = {
            "heroic": 30,
            "brutal": 25,
            "gentle": 25,
            "clever": 25,
            "reckless": 20,
            "mysterious": 25,
        }
        for category, threshold in thresholds.items():
            current = self.karma.get(category, 0)
            progress[category] = {
                "current": current,
                "threshold": threshold,
                "reached": current >= threshold,
                "level": current // 10,  # Уровень кармы
            }
        return progress
    
    def get_event_log(self, limit: int = 10) -> List[str]:
        """Получить последние записи из лога событий."""
        return self.event_log[-limit:] if len(self.event_log) > limit else self.event_log
    
    def get_ui(self) -> str:
        """Получить текст UI для отображения в боте."""
        weather_icon = {"clear": "☀️", "cloudy": "☁️", "rain": "🌧️", "dry": "☀️", "cool": "❄️"}.get(self.weather, "☀️")
        # Получить последние 5 записей из лога
        recent_events = self.get_event_log(5)
        log_text = "\n".join(f"> {line}" for line in recent_events)
        
        return (
            f"❤️ {self.hp} | 🍖 {self.hunger} | 💧 {self.thirst} | {weather_icon} {self.current_location}\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"{log_text}\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
    
    def get_inventory_text(self) -> str:
        """Получить текст инвентаря для отображения в боте."""
        lines = []
        for item, count in self.inventory.items():
            if count > 0:
                line = f"• {item} x{count}" if count > 1 else f"• {item}"
                lines.append(line)
        
        text = "Инвентарь:\n" + "\n".join(lines) if lines else "Инвентарь пуст"
        text += "\n━━━━━━━━━━━━━━━━━━━"
        return text
    
    def get_character_text(self) -> str:
        """Получить текст персонажа для отображения в боте."""
        slots = {
            "head": "Голова",
            "chest": "Грудь",
            "legs": "Ноги",
            "hands": "Руки",
            "feet": "Ноги",
            "back": "Спина",
        }
        lines = [f"{name}: {self.equipment.get(slot) or 'Пусто'}" for slot, name in slots.items()]
        return "Персонаж:\n\n" + "\n".join(lines)


# Глобальное состояние игры
game = GameState()
