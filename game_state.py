"""
game_state.py — Центральное хранилище состояния игры.
Здесь живут кармы, инвентарь, экипировка и история событий.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

from game_math import (
    get_base_resource_cost,
    get_thirst_base_cost,
)

from modules.hints import get_active_hints


@dataclass
class GameState:
    """Состояние игры — единый источник правды."""

    schema_version: int = 2

    # Настройки отображения игрока
    display_mode: str = "pc"
    max_line_length: int = 35
    max_lines_per_msg: int = 10
    
    # Базовые ресурсы
    inventory: Dict[str, int] = field(default_factory=lambda: {
        "Вода": 2,
        "Еда": 3,
        "Спички": 1,
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
        "pet": None,
        "hand": None,
    })
    
    # Атмосфера
    weather: str = "clear"
    
    # Состояние сюжета
    story_state: Optional[str] = None
    
    # Охотничьи ловушки (ключ: location_id 3-7, значение: dict с is_active)
    traps: Dict[int, Dict] = field(default_factory=dict)

    def roll_weather_for_new_day(self) -> str:
        """Случайно определить погоду на новый день.

        Шансы: ясное 50%, пасмурное 25%, дождь 15%, гроза 10%.
        """
        weights = {
            "clear": 50,
            "cloudy": 25,
            "rain": 15,
            "storm": 10,
        }
        return random.choices(
            population=list(weights.keys()),
            weights=list(weights.values()),
            k=1,
        )[0]
    
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

    # Каноническая карма сюжетных финалов из сценарной спецификации.
    narrative_karma: Dict[str, int] = field(default_factory=lambda: {
        "intervention": 0,
        "compassion": 0,
        "pragmatism": 0,
        "observation": 0,
    })

    # Состояние Костра
    campfire_active: bool = False
    campfire_durability: int = 0
    campfire_max_durability: int = 10

    # Вода во фляге (макс 10 делений)
    flask_water: int = 10

    # Одноразовые результаты выборов и компактная запись пройденного пути.
    story_flags: Dict[str, Any] = field(default_factory=dict)
    compact_route: List[str] = field(default_factory=list)
    nav_stack: List[str] = field(default_factory=lambda: ["main"])
    
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
        self.nav_stack = ["main"]

    def push_screen(self, screen: str):
        self.nav_stack.append(screen)

    def pop_screen(self):
        if len(self.nav_stack) > 1:
            self.nav_stack.pop()
        return self.nav_stack[-1]
        
    def __post_init__(self):
        """Инициализация после создания."""
        if not self.is_initialized:
            self._init_default_values()
            self.is_initialized = True
    
    @property
    def energy(self):
        """Совместимый алиас действия/энергии для старого и нового кода."""
        return self.ap

    @energy.setter
    def energy(self, value):
        self.ap = value

    def calculate_daily_ap(self) -> int:
        """Рассчитать AP строго по уровню HP с учетом экипировки."""
        # 1. Базовое AP по порогам HP
        if self.hp >= 50:
            base_ap = 5
        elif self.hp >= 40:
            base_ap = 4
        elif self.hp >= 30:
            base_ap = 3
        elif self.hp >= 10:
            base_ap = 2
        else:
            base_ap = 1

        # 2. Бонусы от экипировки
        equipment_bonus = 0
        for item in getattr(self, "equipment", {}).values():
            if isinstance(item, dict):
                equipment_bonus += int(item.get("ap_bonus", item.get("ap_modifier", 0)))
        equipment_bonus += int(getattr(self, "equipment_ap_bonus", 0))

        return base_ap + equipment_bonus

    def consume_action(self, action_type: str = "default", base_hunger: int = 2, base_thirst: int = 1):
        """Списание AP и ресурсов с возвратом ФАКТИЧЕСКИХ дельт.

        Если голод или жажда доходят до 0, остаток уходит в урон HP
        (голодание / обезвоживание). HP гарантированно не ниже 1.

        Возвращает:
            dict с ключами:
                success (bool) — было ли действие выполнено (AP > 0)
                delta_ap (int) — фактическое изменение AP
                delta_hunger (int) — фактическое изменение hunger (отриц. = списано)
                delta_thirst (int) — фактическое изменение thirst (отриц. = списано)
                delta_hp (int) — фактическое изменение HP (отриц. = урон)
                hunger_damage_to_hp (int) — сколько HP снялось из-за голодания
                thirst_damage_to_hp (int) — сколько HP снялось из-за обезвоживания
        """
        result = {
            "success": False,
            "delta_ap": 0,
            "delta_hunger": 0,
            "delta_thirst": 0,
            "delta_hp": 0,
            "hunger_damage_to_hp": 0,
            "thirst_damage_to_hp": 0,
        }
        if self.ap <= 0:
            return result

        old_ap = self.ap
        old_hunger = self.hunger
        old_thirst = self.thirst
        old_hp = self.hp

        self.ap = max(0, self.ap - 1)

        hunger_cost = get_base_resource_cost(self, base_cost=base_hunger)
        thirst_cost = get_thirst_base_cost(self, base_cost=base_thirst)

        new_hunger = old_hunger - hunger_cost
        if new_hunger < 0:
            result["hunger_damage_to_hp"] = -new_hunger
            new_hunger = 0
        self.hunger = new_hunger

        new_thirst = old_thirst - thirst_cost
        if new_thirst < 0:
            result["thirst_damage_to_hp"] = -new_thirst
            new_thirst = 0
        self.thirst = new_thirst

        overflow_hp_damage = result["hunger_damage_to_hp"] + result["thirst_damage_to_hp"]
        if overflow_hp_damage > 0:
            self.hp = max(1, old_hp - overflow_hp_damage)

        result["success"] = True
        result["delta_ap"] = self.ap - old_ap
        result["delta_hunger"] = self.hunger - old_hunger
        result["delta_thirst"] = self.thirst - old_thirst
        result["delta_hp"] = self.hp - old_hp

        # −1 прочность костра за действие с тратой AP (success), кроме сна
        if self.campfire_active and action_type != "sleep":
            self.campfire_durability -= 1
            if self.campfire_durability <= 0:
                self.campfire_durability = 0
                self.campfire_active = False
                self.add_log("Костёр погас.")

        return result

    def light_campfire(self):
        """Развести костёр: 1 AP, 7 голода, 15 жажды.

        Фиксированно устанавливает:
            self.campfire_max_durability = 10
            self.campfire_durability = 10
            self.campfire_active = True

        Возвращает:
            dict с тем же набором ключей, что и consume_action, плюс:
                lit (bool) — получилось ли развести (AP ≥ 1)
        """
        result = {
            "success": False,
            "lit": False,
            "delta_ap": 0,
            "delta_hunger": 0,
            "delta_thirst": 0,
            "delta_hp": 0,
            "hunger_damage_to_hp": 0,
            "thirst_damage_to_hp": 0,
        }
        if self.ap < 1:
            return result

        old_ap = self.ap
        old_hunger = self.hunger
        old_thirst = self.thirst
        old_hp = self.hp

        self.ap = max(0, self.ap - 1)

        hunger_cost = get_base_resource_cost(self, base_cost=7)
        thirst_cost = get_thirst_base_cost(self, base_cost=15)

        new_hunger = old_hunger - hunger_cost
        if new_hunger < 0:
            result["hunger_damage_to_hp"] = -new_hunger
            new_hunger = 0
        self.hunger = new_hunger

        new_thirst = old_thirst - thirst_cost
        if new_thirst < 0:
            result["thirst_damage_to_hp"] = -new_thirst
            new_thirst = 0
        self.thirst = new_thirst

        overflow_hp_damage = result["hunger_damage_to_hp"] + result["thirst_damage_to_hp"]
        if overflow_hp_damage > 0:
            self.hp = max(1, old_hp - overflow_hp_damage)

        # Затраты на розжиг: 1 AP, 7 голода и 15 жажды
        self.campfire_max_durability = 10
        self.campfire_durability = self.campfire_max_durability
        self.campfire_active = True

        result["success"] = True
        result["lit"] = True
        result["delta_ap"] = self.ap - old_ap
        result["delta_hunger"] = self.hunger - old_hunger
        result["delta_thirst"] = self.thirst - old_thirst
        result["delta_hp"] = self.hp - old_hp

        self.add_log(f"🔥 Костёр разведён! Прочность: {self.campfire_durability}/{self.campfire_max_durability}")
        return result

    def reset_daily_ap(self) -> int:
        """Сбросить AP в начале дня по текущему состоянию персонажа."""
        self.ap = self.calculate_daily_ap()
        return self.ap

    def _init_default_values(self):
        """Установить дефолтные значения для UI."""
        # Умные заглушки для UI
        self.equipment["hands"] = "Руки"  # По умолчанию
        self.equipment["chest"] = "Куртка"
        self.equipment["head"] = "Шапка"
        self.equipment["feet"] = "Ботинки"
        self.equipment.setdefault("pet", None)
        self.equipment.setdefault("hand", None)
    
    def add_log(self, message: str, source: str = "game"):
        """Добавить запись в лог событий."""
        timestamp = datetime.now().strftime("%H:%M")
        self.event_log.append(f"[{timestamp}] {message}")
        # Не ограничивать длину, чтобы история росла
    
    def sleep_and_turn_day(self) -> int:
        """Сменить день (сон): списать ресурсы, обновить AP и обработать сгоревший факел."""
        # 1. Списание AP и ресурсов (если есть)
        if self.ap > 0:
            self.consume_action(action_type="sleep", base_hunger=1, base_thirst=1)
        
        # 2. Проверка на сгоревший факел
        torch_in_hand = self.equipment.get("hand") == "Факел"
        if torch_in_hand:
            # Снимаем факел с руки
            self.equipment["hand"] = None
            self.add_log("За ночь твой факел прогорел.", "sleep")
        
        # 3. Сброс AP для нового дня
        self.reset_daily_ap()
        return self.ap
    
    def get_ui_value(self, key: str, fallback: Any = None) -> Any:
        """Умное получение значения для UI с умными заглушками."""
        if key in self.equipment:
            value = self.equipment[key]
            # Если предмет "исторический" (факел), показываем его даже если это заглушка
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

    def adjust_narrative_karma(self, category: str, amount: int):
        """Изменить шкалу, используемую условиями семи финалов."""
        if category in self.narrative_karma:
            self.narrative_karma[category] += amount

    def set_story_flag(self, name: str, value: Any = True):
        """Записать сюжетный флаг и вернуть, изменилось ли его значение."""
        changed = self.story_flags.get(name) != value
        self.story_flags[name] = value
        return changed

    def record_route(self, code: str):
        """Добавить выбор в компактный маршрут без повторной записи подряд."""
        if not self.compact_route or self.compact_route[-1] != code:
            self.compact_route.append(code)

    def to_document(self) -> Dict[str, Any]:
        """Вернуть MongoDB-документ состояния без служебных объектов dataclass."""
        return {
            "schema_version": self.schema_version,
            "display_mode": self.display_mode,
            "max_line_length": self.max_line_length,
            "max_lines_per_msg": self.max_lines_per_msg,
            "inventory": dict(self.inventory),
            "equipment": dict(self.equipment),
            "traps": dict(self.traps),
            "karma": dict(self.karma),
            "narrative_karma": dict(self.narrative_karma),
            "story_flags": dict(self.story_flags),
            "compact_route": list(self.compact_route),
            "story_state": self.story_state,
            "current_location": self.current_location,
            "current_location_key": self.current_location_key,
            "location_index": self.location_index,
            "day": self.day,
            "ap": self.ap,
            "hp": self.hp,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "water_capacity": self.water_capacity,
            "food_capacity": self.food_capacity,
            "weather": self.weather,
            "companion_name": self.companion_name,
            "companion_status": self.companion_status,
            "event_log": list(getattr(self, "log", self.event_log)),
            "nav_stack": list(self.nav_stack),
            "unlocked_locations": list(getattr(self, "unlocked_locations", [])),
            "current_location_state": getattr(self, "current_location_state", "forest_start"),
            "found_branch_once": getattr(self, "found_branch_once", False),
        }

    @classmethod
    def from_document(cls, document: Dict[str, Any]):
        """Восстановить состояние и мигрировать старые документы без мутации входа."""
        data = dict(document or {})
        legacy_log = data.pop("log", None)
        if "event_log" not in data and legacy_log is not None:
            data["event_log"] = list(legacy_log)
        if "current_location" not in data and "location" in data:
            data["current_location"] = data["location"]
        if "narrative_karma" not in data:
            data["narrative_karma"] = {
                "intervention": 0,
                "compassion": 0,
                "pragmatism": 0,
                "observation": 0,
            }
        game = cls()
        allowed = set(game.to_document())
        for key, value in data.items():
            if key in allowed:
                setattr(game, key, value)
        game.schema_version = cls.schema_version
        game.display_mode = game.display_mode if game.display_mode in ("phone", "pc") else "pc"
        game.max_line_length = max(10, min(100, int(game.max_line_length)))
        game.max_lines_per_msg = max(3, min(30, int(game.max_lines_per_msg)))
        game.hunger = max(0, int(game.hunger))
        game.thirst = max(0, int(game.thirst))
        game.inventory = dict(game.inventory or {})
        game.equipment = dict(game.equipment or {})
        if "traps" in data:
            game.traps = dict(game.traps or data["traps"])
        game.story_flags = dict(game.story_flags or {})
        game.compact_route = list(game.compact_route or [])
        game.nav_stack = list(game.nav_stack or ["main"])
        if hasattr(game, "log"):
            game.log = list(game.event_log)
        if hasattr(game, "location"):
            game.location = game.current_location
        if hasattr(game, "unlocked_locations") and not game.unlocked_locations:
            game.unlocked_locations = ["Лесной старт"]
        return game
    
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
    
    def get_status_bar(self, max_width: Optional[int] = None) -> str:
        """Сформировать статус-бар с компактным отображением номера дня."""
        weather_icon = {"clear": "☀️", "cloudy": "☁️", "rain": "🌧️", "storm": "⛈️"}.get(self.weather, "☀️")
        # Всегда показываем костёр: прочность или «Потух»
        if self.campfire_active and self.campfire_durability > 0:
            campfire_status = f"🔥{self.campfire_durability}/{self.campfire_max_durability}"
        else:
            campfire_status = "🔥Потух"
        status_str = (
            f"❤️{self.hp}|🍖{self.hunger}|💧{self.thirst}|⚡{self.ap}|{weather_icon}{self.day}|{campfire_status}"
        )
        if max_width is not None and len(status_str) > max_width:
            status_str = status_str.replace(f"{weather_icon}День ", weather_icon, 1)
        return status_str
    def get_ui(self) -> str:
        """Получить компактный статус-бар персонажа и дневную погоду."""
        max_width = self.max_line_length if self.display_mode == "phone" else None
        status_bar = self.get_status_bar(max_width)
        
        # Добавляем активные подсказки, если они есть
        hints = get_active_hints(self)
        if hints:
            status_bar += "\n" + "\n".join(hints)
        
        return status_bar
    
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
