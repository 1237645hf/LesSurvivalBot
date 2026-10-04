"""
game_state.py — Центральное хранилище состояния игры.
Здесь живут кармы, инвентарь, экипировка и история событий.
"""

import random
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
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

    # Базовые ресурсы (стартовый инвентарь нового игрока)

    inventory: Dict[str, int] = field(default_factory=lambda: {
        "Спички": 3,
        "Кусок коры": 1,
        "Сухпай": 3,
        "Бутылка воды": 2,
    })
    
    # Емкость ресурсов
    water_capacity: int = 20
    food_capacity: int = 10
    
    # Жизненные показатели (стартовые значения нового игрока)
    hp: int = 100
    hunger: int = 20
    thirst: int = 60
    
    # Экипировка (единый словарь с унифицированными ключами)
    equipment: Dict[str, str] = field(default_factory=lambda: {
        "head": None,
        "torso": None,
        "pants": None,
        "boots": None,
        "back": None,
        "hand_right": None,
        "hand_left": None,
        "flask": None,
        "pet": None,
        "trinket": None,
    })
    
    # Атмосфера
    weather: str = "clear"
    
    # Состояние сюжета
    story_state: Optional[str] = None
    active_story_callback: Optional[str] = None
    
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
    
    # Устаревшая карма (сохраняется для обратной совместимости сохранений)
    karma: Dict[str, int] = field(default_factory=dict)

    # Бонус AP от экипировки (суммируется с базовым AP по HP)
    equipment_ap_bonus: int = 0

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

    # Состояние Фонаря
    lantern_durability: int = 20
    lantern_max_durability: int = 20

    # Футляр на поножах и приманка для слизней
    pants_pocket: Optional[str] = None
    slug_bait_active: bool = False

    # Вода во фляге (макс 10 делений)
    flask_water: int = 10
    rain_bottles: List[int] = field(default_factory=list)

    # Открытые рецепты крафта (старт: Костёр, Факел)
    unlocked_crafts: List[str] = field(default_factory=lambda: ["Костёр", "Факел"])

    # Одноразовые результаты выборов и компактная запись пройденного пути.
    story_flags: Dict[str, Any] = field(default_factory=dict)
    compact_route: List[str] = field(default_factory=list)
    nav_stack: List[str] = field(default_factory=lambda: ["main"])
    
    current_location: str = "Лесной старт"
    location_index: int = 0
    
    # Дополнительные поля для совместимости с Game
    ap: int = 5  # Действия в день
    day: int = 1  # Текущий день
    
    # История событий (стартовое сообщение без временной метки)
    event_log: List[str] = field(default_factory=lambda: [
        "Ты проснулся в лесу. Что будешь делать?",
    ])
    
    # Статус кот-компаньона
    companion_name: str = "Кот"
    companion_status: str = "alive"
    
    # Поля совместимости из Game (ранее отсутствовали в GameState)
    location: str = "Стартовый лес"
    unlocked_locations: List[str] = field(default_factory=lambda: [
        "Стартовый лес", "Ручей со змеями", "Скромная лощина",
        "Просека охотников", "Яр слизней", "Мохнатая пещера", "Святилище",
    ])
    last_message_id: Optional[int] = None
    current_location_state: str = "forest_start"
    found_branch_once: bool = False
    karma_goal: int = 100
    
    # Счётчик исследований с факелом (триггер для истории волка)
    torch_research_count: int = 0

    # Прогресс Волчьего логова и открытия локаций
    locations_unlocked: bool = False
    wolf_lair_unlocked: bool = False
    wolf_lair_active: bool = False
    wolf_lair_defeated: bool = False
    l1_post_research_count: int = 0
    wolf_battle: Optional[Dict[str, Any]] = None
    l2_puzzle_attempt: int = 0
    l2_puzzle_step: int = 1
    header_message_id: Optional[int] = None

    # Имя персонажа (устанавливается при старте игры)
    player_name: str = "Выживший"
    character_name: str = "Выживший"
    # Флаг ожидания ввода имени при старте
    is_name_set: bool = False


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

    @property
    def log(self):
        """Безопасный алиас для последних записей лога событий."""
        return self.event_log[-3:] if hasattr(self, "event_log") and self.event_log else []

    def calculate_daily_ap(self) -> int:
        """Рассчитать AP строго по уровню HP с учетом экипировки.

        Бонусы от предметов в каждом слоте (включая обе руки) суммируются.
        """
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

        # 2. Бонусы от экипировки (сумма всех предметов в слотах)
        equipment_bonus = 0
        for item in getattr(self, "equipment", {}).values():
            if isinstance(item, dict):
                equipment_bonus += int(item.get("ap_bonus", item.get("ap_modifier", 0)))
        # Пока факел экипирован в руке — он даёт +1 AP
        if self.equipment.get("hand_left") == "Факел":
            equipment_bonus += 1
        elif self.equipment.get("hand_left") == "Старый фонарь":
            equipment_bonus += 2
        # Поножи дают +1 AP
        if self.equipment.get("pants") in ("Кожаные поножи", "Сланцевые поножи"):
            equipment_bonus += 1
        # Добавляем отдельный бонус от поля equipment_ap_bonus (если есть)
        equipment_bonus += int(getattr(self, "equipment_ap_bonus", 0))

        return base_ap + equipment_bonus

    def consume_action(self, action_type: str = "default", base_hunger: int = 2, base_thirst: int = 1, ap_cost: int = 1):
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

        cost = max(0, int(ap_cost))
        if cost <= 0:
            return result
        if self.ap < cost:
            return result
        self.ap = max(0, self.ap - cost)

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
            self.hp = max(0, old_hp - overflow_hp_damage)

        result["success"] = True
        result["delta_ap"] = self.ap - old_ap
        result["delta_hunger"] = self.hunger - old_hunger
        result["delta_thirst"] = self.thirst - old_thirst
        result["delta_hp"] = self.hp - old_hp

        # −1 прочность костра за действие С ТРАТОЙ AP (success), кроме сна
        if self.campfire_active and action_type != "sleep" and ap_cost > 0:
            self.campfire_durability -= 1
            if self.campfire_durability <= 0:
                self.campfire_durability = 0
                if self.is_stove:
                    self.add_log("🧱 Печь остыла.")
                else:
                    self.campfire_active = False
                    self.add_log("🔥 Костёр погас.")

        return result

    @property
    def is_stove(self) -> bool:
        flags = getattr(self, "story_flags", {}) or {}
        if flags.get("has_stove") or flags.get("l3_shelter_unlocked"):
            return True
        loc_idx = int(getattr(self, "location_index", 0) or 0)
        cur_loc = str(getattr(self, "current_location", "") or "")
        return loc_idx == 2 or "Лощина" in cur_loc

    def rekindle_stove(self):
        """Растопить остывшую печь: 2 AP, +7 голода, +18 жажды, даёт 1 огонь."""
        if self.ap < 2:
            return False, "Недостаточно энергии (нужно 2 ⚡ AP)."
        self.ap -= 2
        self.hunger = max(0, self.hunger - 7)
        self.thirst = max(0, self.thirst - 18)
        self.campfire_active = True
        self.campfire_durability = 1
        self.campfire_max_durability = 30
        self.add_log("Печь растоплена. В глубине очага снова теплится огонёк (+1 к огню).")
        return True, "Печь успешно растоплена!"

    def light_campfire(self):
        """Умный розжиг костра по 3 сценариям:
        1. От горящего факела в руке: 1 AP, 0 спичек, 0 голода, 0 жажды.
        2. Спичками из инвентаря: 1 AP, 1 спичка, 0 голода, 0 жажды.
        3. Вручную трением (нет факела и нет спичек): 2 AP, 7 голода, 18 жажды.
        """
        result = {
            "success": False,
            "lit": False,
            "method": "friction",
            "delta_ap": 0,
            "delta_hunger": 0,
            "delta_thirst": 0,
            "delta_hp": 0,
            "hunger_damage_to_hp": 0,
            "thirst_damage_to_hp": 0,
        }

        has_torch = (
            self.equipment.get("hand_left") == "Факел"
        )
        has_matches = self.inventory.get("Спички", 0) > 0

        # Минимальные требования по AP
        min_ap = 1 if (has_torch or has_matches) else 2
        if self.ap < min_ap:
            return result

        old_ap = self.ap
        old_hunger = self.hunger
        old_thirst = self.thirst
        old_hp = self.hp

        if has_torch:
            # Сценарий 1: От горящего факела
            self.ap = max(0, self.ap - 1)
            result["method"] = "torch"
            self.add_log("🔥 Костёр зажжён от горящего факела! Спички и силы сэкономлены (−1 ⚡ AP).")
        elif has_matches:
            # Сценарий 2: Спичками
            self.ap = max(0, self.ap - 1)
            self.inventory["Спички"] -= 1
            if self.inventory["Спички"] <= 0:
                del self.inventory["Спички"]
            result["method"] = "match"
            self.add_log("🔥 Костёр быстро разведён спичкой (−1 спичка, −1 ⚡ AP). Сытость и жажда сохранены.")
        else:
            # Сценарий 3: Трение сушняка вручную
            self.ap = max(0, self.ap - 2)
            result["method"] = "friction"
            hunger_cost = get_base_resource_cost(self, base_cost=7)
            thirst_cost = get_thirst_base_cost(self, base_cost=18)

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
                self.hp = max(0, old_hp - overflow_hp_damage)

            self.add_log("🔥 Костёр с трудом разведён трением (−2 ⚡ AP, −7 сытости, −18 жажды).")

        self.campfire_max_durability = 10
        self.campfire_durability = self.campfire_max_durability
        self.campfire_active = True

        result["success"] = True
        result["lit"] = True
        result["delta_ap"] = self.ap - old_ap
        result["delta_hunger"] = self.hunger - old_hunger
        result["delta_thirst"] = self.thirst - old_thirst
        result["delta_hp"] = self.hp - old_hp

        return result

    def reset_daily_ap(self) -> int:
        """Сбросить AP в начале дня по текущему состоянию персонажа."""
        self.ap = self.calculate_daily_ap()
        return self.ap

    def _init_default_values(self):
        """Установить дефолтные значения для UI."""
        self.equipment.setdefault("head", None)
        self.equipment.setdefault("torso", None)
        self.equipment.setdefault("pants", None)
        self.equipment.setdefault("boots", None)
        self.equipment.setdefault("back", None)
        self.equipment.setdefault("pet", None)
        self.equipment.setdefault("hand_right", None)
        self.equipment.setdefault("hand_left", None)
        self.equipment.setdefault("flask", None)
        self.equipment.setdefault("trinket", None)
    
    def add_log(self, message: str, source: str = "game"):
        """Добавить запись в лог событий (макс. 50 записей) без серверных часов."""
        clean_msg = re.sub(r"^\[\d{2}:\d{2}\]\s*", "", message)
        self.event_log.append(clean_msg)
        # Ограничение: хранить не более 50 последних записей
        if len(self.event_log) > 50:
            self.event_log = self.event_log[-50:]
    
    def sleep_and_turn_day(self) -> int:
        """Сменить день (сон): ресурсы, костёр за ночь, AP, факел.

        Порядок строго по спецификации:
        1. Тратим остаток AP/ресурсов за ночь.
        2. Костёр −3 прочности (возможно тухнет).
        3. Факел в руке сгорает → исчезает из руки и инвентаря.
        4. reset_daily_ap() (факел уже сгорел → бонуса нет).
        5. Если костёр НЕ горит утром → −1 AP (ровно один раз).
        6. day += 1 — день наступил.
        """
        # 1. Ночные расходы ресурсов
        if self.ap > 0:
            self.consume_action(action_type="sleep", base_hunger=1, base_thirst=1)

        # 2. Костёр / Печь за ночь: −3 прочности
        if self.campfire_active:
            self.campfire_durability = max(0, int(self.campfire_durability) - 3)
            if self.campfire_durability <= 0:
                self.campfire_durability = 0
                if self.is_stove:
                    self.add_log("Печь остыла. Огонь погас, но печь можно растопить заново.", "sleep")
                else:
                    self.campfire_active = False
                    self.add_log("Костёр потух. Ты не уследил за огнём.", "sleep")

        # 3. Факел в руке ночью сгорает
        torch_in_hand = (
            self.equipment.get("hand_left") == "Факел"
            or self.equipment.get("hand_right") == "Факел"
        )
        if torch_in_hand:
            if self.equipment.get("hand_left") == "Факел":
                self.equipment["hand_left"] = None
            if self.equipment.get("hand_right") == "Факел":
                self.equipment["hand_right"] = None
            if "Факел" in self.inventory:
                del self.inventory["Факел"]
            self.add_log("💨 Твой факел догорел и угас за ночь.", "sleep")

        # 4. AP на новый день (факел уже сгорел — бонуса +1 AP нет)
        self.reset_daily_ap()

        # 5. Без костра утром — штраф −1 AP ровно один раз (не ниже 1)
        cold_penalty_applied = False
        if not self.campfire_active:
            self.ap = max(1, int(self.ap) - 1)
            cold_penalty_applied = True
            self.add_log("За ночь ты промёрз. Сегодня сил меньше (−1 ⚡).", "sleep")

        # 6. Новый день — счётчик растёт
        self.day += 1

        # 7. Смена погоды (ясно/пасмурно/дождь/гроза)
        old_weather = self.weather
        self.weather = self.roll_weather_for_new_day()
        weather_icons = {"clear": "☀️", "cloudy": "☁️", "rain": "🌧️", "storm": "⛈️"}
        weather_names = {"clear": "Ясно", "cloudy": "Пасмурно", "rain": "Дождь", "storm": "Гроза"}
        w_icon = weather_icons.get(self.weather, "☀️")
        w_name = weather_names.get(self.weather, self.weather)
        self.add_log(f"{w_icon} Утро дня {self.day}. Погода: {w_name}.", "sleep")

        # 8. Уничтожение приманки для слизней за ночь
        if getattr(self, "slug_bait_active", False):
            self.slug_bait_active = False
            self.add_log("За ночь лесные слизни без остатка сожрали приманку в Яру Слизней.", "sleep")

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
        """Рассчитать бонусы к характеристикам."""
        return {
            "strength": 0,
            "agility": 0,
            "charm": 0,
            "mystery": 0,
        }
    
    def adjust_karma(self, category: str, amount: int):
        """Изменить карму по категории (при наличии перенаправляет в narrative_karma)."""
        if category in getattr(self, "narrative_karma", {}):
            self.adjust_narrative_karma(category, amount)
        elif hasattr(self, "karma"):
            self.karma[category] = self.karma.get(category, 0) + amount

    def adjust_narrative_karma(self, category: str, amount: int):
        """Изменить шкалу, используемую условиями семи финалов."""
        if category in self.narrative_karma:
            self.narrative_karma[category] += amount

    def set_story_flag(self, name: str, value: Any = True):
        """Записать сюжетный флаг и вернуть, изменилось ли его значение."""
        changed = self.story_flags.get(name) != value
        self.story_flags[name] = value
        return changed

    def is_story_flag_set(self, name: str) -> bool:
        """Проверить, установлен ли сюжетный флаг."""
        return bool(self.story_flags.get(name))

    def has_story_flag(self, name: str) -> bool:
        """Проверить, установлен ли сюжетный флаг (алиас)."""
        return bool(self.story_flags.get(name))

    def record_route(self, code: str):
        """Добавить выбор в компактный маршрут без повторной записи подряд."""
        if not self.compact_route or self.compact_route[-1] != code:
            self.compact_route.append(code)

    def to_document(self) -> Dict[str, Any]:
        """Вернуть MongoDB-документ состояния без служебных объектов dataclass."""
        return {
            "schema_version": getattr(self, "schema_version", 2),
            "display_mode": getattr(self, "display_mode", "standard"),
            "max_line_length": getattr(self, "max_line_length", 4096),
            "max_lines_per_msg": getattr(self, "max_lines_per_msg", 100),
            "inventory": dict(self.inventory),
            "equipment": dict(self.equipment),
            "traps": {str(k): dict(v) if isinstance(v, dict) else v for k, v in getattr(self, "traps", {}).items()},
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
            "event_log": list(self.event_log),
            "nav_stack": list(self.nav_stack),
            "unlocked_locations": list(getattr(self, "unlocked_locations", [])),
            "current_location_state": getattr(self, "current_location_state", "forest_start"),
            "found_branch_once": getattr(self, "found_branch_once", False),
            "location": getattr(self, "location", self.current_location),
            "karma_goal": getattr(self, "karma_goal", 100),
            "torch_research_count": getattr(self, "torch_research_count", 0),
            "campfire_active": bool(getattr(self, "campfire_active", False)),
            "campfire_durability": int(getattr(self, "campfire_durability", 0)),
            "campfire_max_durability": int(getattr(self, "campfire_max_durability", 10)),
            "lantern_durability": int(getattr(self, "lantern_durability", 20)),
            "lantern_max_durability": int(getattr(self, "lantern_max_durability", 20)),
            "pants_pocket": getattr(self, "pants_pocket", None),
            "slug_bait_active": bool(getattr(self, "slug_bait_active", False)),
            "flask_water": int(getattr(self, "flask_water", 10)),
            "rain_bottles": list(getattr(self, "rain_bottles", [])),
            "unlocked_crafts": list(getattr(self, "unlocked_crafts", ["Костёр", "Факел"])),
            "player_name": str(getattr(self, "player_name", getattr(self, "character_name", "Выживший"))),
            "character_name": str(getattr(self, "character_name", getattr(self, "player_name", "Выживший"))),
            "is_name_set": bool(getattr(self, "is_name_set", False)),
            "equipment_ap_bonus": int(getattr(self, "equipment_ap_bonus", 0)),
            "locations_unlocked": bool(getattr(self, "locations_unlocked", False)),
            "wolf_lair_unlocked": bool(getattr(self, "wolf_lair_unlocked", False)),
            "wolf_lair_active": bool(getattr(self, "wolf_lair_active", False)),
            "wolf_lair_defeated": bool(getattr(self, "wolf_lair_defeated", False)),
            "l1_post_research_count": int(getattr(self, "l1_post_research_count", 0)),
            "wolf_battle": dict(getattr(self, "wolf_battle", {})) if getattr(self, "wolf_battle", None) else None,
            "l2_puzzle_attempt": int(getattr(self, "l2_puzzle_attempt", 0)),
            "l2_puzzle_step": int(getattr(self, "l2_puzzle_step", 1)),
            "active_story_callback": getattr(self, "active_story_callback", None),
            "last_message_id": getattr(self, "last_message_id", None),
            "header_message_id": getattr(self, "header_message_id", None),
        }


    @classmethod
    def from_document(cls, document: Dict[str, Any]):
        """Восстановить состояние и мигрировать старые документы без мутации входа."""
        data = dict(document or {})
        # Миграция: если есть legacy "log", перенести в "event_log"
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
        # Умная миграция: подставить значения по умолчанию для старых полей
        for key, value in data.items():
            if key in game.to_document():
                setattr(game, key, value)
        # Синхронизировать schema_version
        game.schema_version = cls.schema_version
        # Синхронизация имени
        p_name = data.get("player_name") or data.get("character_name") or "Выживший"
        game.player_name = str(p_name)
        game.character_name = str(p_name)
        if "is_name_set" in data:
            game.is_name_set = bool(data["is_name_set"])
        elif p_name != "Выживший":
            game.is_name_set = True

        game.hunger = max(0, int(game.hunger))
        game.thirst = max(0, int(game.thirst))
        game.inventory = dict(game.inventory or {})
        game.inventory.pop("Вилка", None)
        if "Вода" in game.inventory:
            water_count = game.inventory.pop("Вода")
            bottles = max(1, water_count // 5) if water_count >= 5 else 1
            game.inventory["Бутылка воды"] = game.inventory.get("Бутылка воды", 0) + bottles
        game.equipment = dict(game.equipment or {})
        if game.equipment.get("hand_right") == "Вилка":
            game.equipment["hand_right"] = None
        if game.equipment.get("hand_left") == "Вилка":
            game.equipment["hand_left"] = None
        if "traps" in data and isinstance(data["traps"], dict):
            game.traps = {}
            for k, v in data["traps"].items():
                try:
                    game.traps[int(k)] = v
                except (ValueError, TypeError):
                    game.traps[k] = v
        game.story_flags = dict(game.story_flags or {})
        game.compact_route = list(game.compact_route or [])
        game.nav_stack = list(game.nav_stack or ["main"])
        if hasattr(game, "event_log"):
            game.event_log = list(game.event_log)
        if hasattr(game, "location"):
            game.location = game.current_location
        if hasattr(game, "unlocked_locations") and not game.unlocked_locations:
            game.unlocked_locations = ["Лесной старт"]
        # Миграция костра и рецептов
        if not getattr(game, "unlocked_crafts", None):
            game.unlocked_crafts = ["Костёр", "Факел"]
        else:
            game.unlocked_crafts = list(game.unlocked_crafts)
        game.campfire_active = bool(getattr(game, "campfire_active", False))
        game.campfire_durability = int(getattr(game, "campfire_durability", 0) or 0)
        game.campfire_max_durability = int(getattr(game, "campfire_max_durability", 10) or 10)
        if game.campfire_durability <= 0:
            game.campfire_active = False
        game.lantern_durability = int(data.get("lantern_durability", getattr(game, "lantern_durability", 20)) or 20)
        game.lantern_max_durability = int(data.get("lantern_max_durability", getattr(game, "lantern_max_durability", 20)) or 20)
        game.pants_pocket = data.get("pants_pocket", getattr(game, "pants_pocket", None))
        game.slug_bait_active = bool(data.get("slug_bait_active", getattr(game, "slug_bait_active", False)))
        game.flask_water = int(getattr(game, "flask_water", 10) or 10)
        game.rain_bottles = [int(x) for x in data.get("rain_bottles", [])]
        game.locations_unlocked = bool(data.get("locations_unlocked", False))
        game.wolf_lair_unlocked = bool(data.get("wolf_lair_unlocked", False))
        game.wolf_lair_active = bool(data.get("wolf_lair_active", False))
        game.wolf_lair_defeated = bool(data.get("wolf_lair_defeated", False))
        game.l1_post_research_count = int(data.get("l1_post_research_count", 0))
        game.torch_research_count = int(data.get("torch_research_count", 0))
        game.wolf_battle = dict(data["wolf_battle"]) if data.get("wolf_battle") else None
        game.active_story_callback = data.get("active_story_callback")
        game.header_message_id = data.get("header_message_id")

        # Авто-исцеление (auto-heal) старых повреждённых сейвов:
        if isinstance(game.story_flags, dict):
            # 1. L1: если l1_started стоял, но ветка не завершена и нет активного сюжетного окна -> сбросить l1_started
            if game.story_flags.get("l1_started") and not game.story_flags.get("l1_completed") and not game.active_story_callback:
                game.story_flags.pop("l1_started", None)

            # 2. L1.5: если l1_5_triggered стоял, но логово не открыто и нет активного окна -> сбросить l1_5_triggered
            if game.story_flags.get("l1_5_triggered") and not game.wolf_lair_unlocked and not game.active_story_callback:
                game.story_flags.pop("l1_5_triggered", None)

            # 3. L3: если l3_story_started стоял, но убежище не открыто и нет активного окна -> сбросить l3_story_started
            if game.story_flags.get("l3_story_started") and not game.story_flags.get("l3_shelter_unlocked") and not game.active_story_callback:
                game.story_flags.pop("l3_story_started", None)

            # 4. L3.7: если l3_7_triggered стоял, но солонец не открыт, гребень не завершён и нет активного окна -> сбросить l3_7_triggered
            if game.story_flags.get("l3_7_triggered") and "Солонец (Секач)" not in getattr(game, "unlocked_locations", []) and not game.story_flags.get("l3_ridge_completed") and not game.active_story_callback:
                game.story_flags.pop("l3_7_triggered", None)

        return game
    
    def reset_navigate(self):
        """Сброс навигации после сюжетного события."""
        self.story_state = None
        self.add_log("Навигация сброшена", "nav")
    
    def get_karma_title(self) -> str:
        """Получить заголовок сюжетной кармы для UI."""
        if hasattr(self, "narrative_karma") and self.narrative_karma:
            max_item = max(self.narrative_karma.items(), key=lambda x: x[1])
            if max_item[1] > 0:
                titles = {
                    "compassion": "Сострадательный",
                    "pragmatism": "Прагматик",
                    "intervention": "Решительный",
                    "observation": "Наблюдатель",
                }
                return f"{titles.get(max_item[0], max_item[0].capitalize())} {max_item[1]}"
        return "Выживший"
    
    def get_karma_progress(self) -> Dict[str, Any]:
        """Получить прогресс сюжетной кармы для финальных развязок."""
        progress = {}
        thresholds = {
            "compassion": 8,
            "pragmatism": 8,
            "intervention": 8,
            "observation": 12,
        }
        for category, threshold in thresholds.items():
            current = self.narrative_karma.get(category, 0)
            progress[category] = {
                "current": current,
                "threshold": threshold,
                "reached": current >= threshold,
                "level": current // 4,
            }
        return progress
    
    def get_event_log(self, limit: int = 10) -> List[str]:
        """Получить последние записи из лога событий."""
        return self.event_log[-limit:] if len(self.event_log) > limit else self.event_log
    

    def unlock_craft(self, name: str) -> bool:
        """Открыть рецепт крафта. True если открыт впервые."""
        if not hasattr(self, "unlocked_crafts") or self.unlocked_crafts is None:
            self.unlocked_crafts = ["Костёр", "Факел"]
        if name in self.unlocked_crafts:
            return False
        self.unlocked_crafts.append(name)
        self.add_log(f"Открыт новый рецепт: {name}. Загляни в 📜 Рецепты.")
        return True

    def get_status_bar(self, max_width: Optional[int] = None) -> str:
        """Сформировать статус-бар (без костра — костёр только кнопкой на главном)."""
        weather_icon = {"clear": "☀️", "cloudy": "☁️", "rain": "🌧️", "storm": "⛈️"}.get(self.weather, "☀️")
        status_str = (
            f"❤️ {self.hp} | 🍖 {self.hunger} | 💧 {self.thirst} | ⚡ {self.ap} | {weather_icon} {self.day}"
        )
        if max_width is not None and len(status_str) > max_width:
            status_str = status_str.replace(f"{weather_icon} ", weather_icon, 1)
        return status_str
    def get_ui(self) -> str:
        """Статус-бар + разделитель + лог событий (8-12 строк) + разделитель без часов сервера."""
        recent_logs = self.event_log[-10:] if self.event_log else []
        clean_logs = [re.sub(r"^\[\d{2}:\d{2}\]\s*", "", line) for line in recent_logs]
        status = self.get_status_bar()
        if clean_logs:
            log_part = "\n".join(f"> {line}" for line in clean_logs)
            return (
                f"{status}\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"{log_part}\n"
                "━━━━━━━━━━━━━━━━━━━"
            )
        return status

    def get_inventory_text(self) -> str:
        """Текст инвентаря: еда с маркерами ранга (🟡) и дикоросов (🌿), остальные предметы с каноническими эмодзи."""
        from modules.items import get_item_rank, get_item_rank_marker, get_item_emoji, is_item_consumable

        equipped_hands = {
            self.equipment.get("hand_left"),
            self.equipment.get("hand_right"),
        }

        # Разделяем на расходники/еду (сортируются по рангу от 5 к 1) и остальные предметы
        items_list = [(item, count) for item, count in self.inventory.items() if count > 0]

        def sort_key(entry):
            item, _ = entry
            is_food = is_item_consumable(item)
            rank = get_item_rank(item)
            return (0 if is_food else 1, -rank, item)

        sorted_items = sorted(items_list, key=sort_key)

        lines = []
        for item, count in sorted_items:
            item_clean = item.replace(" 🔥", "").replace("🔥", "").strip()
            equipped_mark = " (в руке)" if item in equipped_hands or item_clean in equipped_hands else ""
            if is_item_consumable(item_clean):
                marker = get_item_rank_marker(item_clean)
            else:
                marker = get_item_emoji(item_clean)
            line = f"• {marker} {item} x{count}{equipped_mark}" if count > 1 else f"• {marker} {item}{equipped_mark}"
            lines.append(line)
        content = "Инвентарь:\n" + "\n".join(lines) if lines else "Инвентарь пуст"
        return f"━━━━━━━━━━━━━━━━━━━\n{content}\n━━━━━━━━━━━━━━━━━━━"
    
    def get_character_text(self) -> str:
        """Экран персонажа: имя + экипировка по слотам + стартовая одежда + фляга + бонусы."""
        from modules.items import get_item_emoji

        p_name = getattr(self, "player_name", None)
        c_name = getattr(self, "character_name", None)
        if p_name and p_name != "Выживший":
            hero_name = p_name
        elif c_name and c_name != "Выживший":
            hero_name = c_name
        elif c_name:
            hero_name = c_name
        elif p_name:
            hero_name = p_name
        else:
            hero_name = "Выживший"

        # Стартовая одежда (если слот пуст)
        starting_clothes = {
            "head": "⚪ Грязная кепка",
            "torso": "⚪ Потасканная куртка",
            "pants": "⚪ Рваные штаны",
            "boots": "⚪ Стоптанные ботинки",
            "back": "⚪ Пакет «BMW»",
        }

        # Питомец: только Пусто или реальное имя (никакого кота по умолчанию)
        pet_val = self.equipment.get("pet")
        if not pet_val:
            c_name = getattr(self, "companion_name", None)
            has_pet = getattr(self, "has_story_flag", lambda f: False)("has_pet") or getattr(self, "story_flags", {}).get("has_pet")
            if c_name and c_name != "Кот" and has_pet:
                pet_val = c_name
        pet_str = pet_val or "Пусто"

        # Фляга
        flask_item = self.equipment.get("flask")
        if flask_item:
            flask_w = int(getattr(self, "flask_water", 0) or 0)
            if "Бутылк" in flask_item or flask_item == "flask":
                flask_str = f"🧴 Бутылка воды ({flask_w}/20)"
            elif "Армейская" in flask_item:
                flask_str = f"🟨 Армейская фляга ({flask_w}/20)"
            else:
                flask_str = f"{flask_item} ({flask_w}/20)"
        else:
            flask_str = "Пусто"

        left_item = self.equipment.get("hand_left")
        if left_item == "Факел":
            left_emoji = get_item_emoji("Факел")
            left_label = f"{left_emoji} Левая рука:"
            left_val = "⚪ Факел\n⚡ AP: +1"
        elif left_item == "Старый фонарь":
            left_emoji = get_item_emoji("Старый фонарь")
            left_label = f"{left_emoji} Левая рука:"
            dur = int(getattr(self, "lantern_durability", 20) or 0)
            max_d = int(getattr(self, "lantern_max_durability", 20) or 20)
            left_val = f"⚪ Старый фонарь [{dur}/{max_d}]\n⚡ AP: +2"
        elif left_item:
            left_emoji = get_item_emoji(left_item)
            left_label = f"{left_emoji} Левая рука:"
            left_val = f"⚪ {left_item}"
        else:
            left_label = "🫲 Левая рука:"
            left_val = "Пусто"

        right_item = self.equipment.get("hand_right")
        from modules.items import ITEMS
        if right_item:
            right_emoji = get_item_emoji(right_item)
            right_label = f"{right_emoji} Правая рука:"
            extra = ""
            if right_item in ITEMS:
                eff = ITEMS[right_item].get("effects", {})
                notes = []
                if "damage" in eff:
                    notes.append(f"⚔️ Урон +{eff['damage']}")
                if "stun_chance" in eff:
                    notes.append(f"💫 Оглушение +{eff['stun_chance']}%")
                if notes:
                    extra = f"\n{' | '.join(notes)}"
            right_val = f"⚪ {right_item}{extra}"
        else:
            right_label = "🫱 Правая рука:"
            right_val = "Пусто"

        slots_order = [
            ("head", "🧢 Голова:"),
            ("torso", "👕 Торс:"),
            ("pants", "👖 Штаны:"),
            ("boots", "🥾 Ботинки:"),
            ("back", "🎒 Спина:"),
            ("hand_right", right_label),
            ("hand_left", left_label),
            ("flask", "🧴 Фляга:"),
            ("trinket", "💍 Безделушка:"),
            ("pet", "🐾 Котёнок:"),
        ]

        blocks = [f"👤 ВЫЖИВШИЙ: {hero_name}"]
        for slot_key, label in slots_order:
            if slot_key == "hand_left":
                val = left_val
            elif slot_key == "hand_right":
                val = right_val
            elif slot_key in starting_clothes:
                item_val = self.equipment.get(slot_key) or starting_clothes[slot_key]
                if slot_key == "pants" and item_val == "Кожаные поножи":
                    pocket_item = getattr(self, "pants_pocket", None)
                    pocket_str = f"\n👝 Футляр: {pocket_item}" if pocket_item else "\n👝 Футляр: пусто"
                    val = f"{item_val}{pocket_str}"
                else:
                    val = item_val
            elif slot_key == "flask":
                val = flask_str
            elif slot_key == "trinket":
                tr = self.equipment.get("trinket")
                if tr == "Костяной амулет охотника":
                    val = "⚪ Костяной амулет охотника\n🏃 Уворот: +5% | 🔍 Чуткий поиск"
                elif tr == "Клык волка":
                    val = "⚪ Клык волка\n⚔️ Урон +1"
                else:
                    val = tr or "Пусто"
            elif slot_key == "pet":
                val = pet_str
            else:
                val = self.equipment.get(slot_key) or "Пусто"
            blocks.append(f"{label}\n{val}")

        # Общие бонусы снаряжения в порядке хотбара: ❤️ 🍖 💧 ⚡
        bonus_lines = []
        bonus_hp = self.max_hp - 100
        bonus_hunger = 0
        bonus_thirst = 0
        bonus_ap = 0

        if self.equipment.get("hand_left") == "Факел":
            bonus_ap += 1
        elif self.equipment.get("hand_left") == "Старый фонарь":
            bonus_ap += 2
        if self.equipment.get("pants") in ("Кожаные поножи", "Сланцевые поножи"):
            bonus_ap += 1
        bonus_ap += int(getattr(self, "equipment_ap_bonus", 0) or 0)

        for item_data in self.equipment.values():
            if isinstance(item_data, dict):
                bonus_hunger += int(item_data.get("hunger_bonus", 0))
                bonus_thirst += int(item_data.get("thirst_bonus", 0))
                bonus_ap += int(item_data.get("ap_bonus", item_data.get("ap_modifier", 0)))

        stat_parts = []
        if bonus_hp != 0:
            stat_parts.append(f"❤️ HP {bonus_hp:+d}")
        if bonus_hunger != 0:
            stat_parts.append(f"🍖 Сытость {bonus_hunger:+d}")
        if bonus_thirst != 0:
            stat_parts.append(f"💧 Жажда {bonus_thirst:+d}")
        if bonus_ap != 0:
            stat_parts.append(f"⚡ AP {bonus_ap:+d}")
        if self.armor_defense > 0:
            stat_parts.append(f"🛡 Защита +{self.armor_defense}")

        stat_line = ", ".join(stat_parts)

        slate_items = {
            "head": "Сланцевая маска",
            "torso": "Сланцевый панцирь",
            "pants": "Сланцевые поножи",
            "boots": "Сланцевые ботинки",
        }
        slate_count = sum(1 for slot, name in slate_items.items() if self.equipment.get(slot) == name)

        leather_items = {
            "head": "Кожаный капюшон",
            "torso": "Кожаный нагрудник",
            "pants": "Кожаные поножи",
            "boots": "Кожаные сапоги",
        }
        leather_count = sum(1 for slot, name in leather_items.items() if self.equipment.get(slot) == name)

        set_block_lines = []
        if slate_count > 0:
            set_block_lines.append(f"КОМПЛЕКТ: {slate_count} из 4")
            if self.is_full_slate_set_equipped():
                set_block_lines.append("• 🛡 Иммунитет к оглушению")
            if slate_count > 0 or getattr(self, "is_story_flag_set", lambda f: False)("l2_thorns_seen"):
                set_block_lines.append(f"• 🛡 Защита от шипов: {slate_count}/4")
        elif leather_count > 0:
            set_block_lines.append(f"КОМПЛЕКТ: {leather_count} из 4")
            if self.is_full_leather_set_equipped():
                set_block_lines.append("• 🏃 Уворот: 35%")
                set_block_lines.append("• 🧪 Защита от кислоты")
            else:
                if self.dodge_chance > 0:
                    set_block_lines.append(f"• 🏃 Уворот: +{self.dodge_chance}%")
                if self.equipment.get("torso") == "Кожаный нагрудник":
                    set_block_lines.append("• 🧪 Защита от кислоты")

        if right_item and right_item in ITEMS:
            r_eff = ITEMS[right_item].get("effects", {})
            if "stun_chance" in r_eff:
                set_block_lines.append(f"• 💫 Шанс оглушения: +{r_eff['stun_chance']}%")

        content_sections = []
        if stat_line:
            content_sections.append(stat_line)
        if set_block_lines:
            content_sections.append("\n".join(set_block_lines))

        if not content_sections:
            bonus_block = "📊 ОБЩИЕ БОНУСЫ СНАРЯЖЕНИЯ:\n• Бонусы отсутствуют."
        else:
            bonus_block = "📊 ОБЩИЕ БОНУСЫ СНАРЯЖЕНИЯ:\n" + "\n\n".join(content_sections)
        blocks.append(bonus_block)

        body = "\n\n".join(blocks)
        return f"━━━━━━━━━━━━━━━━━━━\n{body}\n━━━━━━━━━━━━━━━━━━━"

    @property
    def max_hp(self) -> int:
        bonus = 0
        armor_hp = {
            "Сланцевая маска": 8,
            "Сланцевый панцирь": 25,
            "Сланцевые поножи": 12,
            "Сланцевые ботинки": 5,
            "Кожаный капюшон": 5,
            "Кожаный нагрудник": 16,
            "Кожаные поножи": 8,
            "Кожаные сапоги": 4,
        }
        for item in (getattr(self, "equipment", {}) or {}).values():
            if item in armor_hp:
                bonus += armor_hp[item]
        return 100 + bonus

    @property
    def armor_defense(self) -> int:
        defense = 0
        armor_def = {
            "Сланцевая маска": 2,
            "Сланцевый панцирь": 5,
            "Сланцевые поножи": 3,
            "Сланцевые ботинки": 2,
            "Кожаный капюшон": 1,
            "Кожаный нагрудник": 3,
            "Кожаные поножи": 2,
            "Кожаные сапоги": 1,
        }
        for item in (getattr(self, "equipment", {}) or {}).values():
            if item in armor_def:
                defense += armor_def[item]
        return defense

    def is_full_slate_set_equipped(self) -> bool:
        eq = getattr(self, "equipment", {}) or {}
        return (
            eq.get("head") == "Сланцевая маска"
            and eq.get("torso") == "Сланцевый панцирь"
            and eq.get("pants") == "Сланцевые поножи"
            and eq.get("boots") == "Сланцевые ботинки"
        )

    def is_full_leather_set_equipped(self) -> bool:
        eq = getattr(self, "equipment", {}) or {}
        return (
            eq.get("head") == "Кожаный капюшон"
            and eq.get("torso") == "Кожаный нагрудник"
            and eq.get("pants") == "Кожаные поножи"
            and eq.get("boots") == "Кожаные сапоги"
        )

    @property
    def dodge_chance(self) -> int:
        """Шанс уворота в процентах (0..100%)."""
        leather_dodge = {
            "Кожаный капюшон": 5,
            "Кожаный нагрудник": 15,
            "Кожаные поножи": 8,
            "Кожаные сапоги": 7,
        }
        dodge = 0
        for item in (getattr(self, "equipment", {}) or {}).values():
            if item in leather_dodge:
                dodge += leather_dodge[item]
        if self.equipment.get("trinket") == "Костяной амулет охотника":
            dodge += 5
        return dodge

    def count_slate_pieces_equipped(self) -> int:
        eq = getattr(self, "equipment", {}) or {}
        count = 0
        if eq.get("head") == "Сланцевая маска":
            count += 1
        if eq.get("torso") == "Сланцевый панцирь":
            count += 1
        if eq.get("pants") == "Сланцевые поножи":
            count += 1
        if eq.get("boots") == "Сланцевые ботинки":
            count += 1
        return count

    def get_death_text(self, reason: str = "") -> str:
        return get_death_text(self, reason)


def get_death_text(game=None, reason: str = "") -> str:
    """Единый экран гибели персонажа."""
    hero = getattr(game, "character_name", "Выживший") if game else "Выживший"
    day = getattr(game, "day", 1) if game else 1
    parts = ["💀 **Ты погиб.**"]
    if reason:
        parts.append(reason)
    parts.append(f"Выживание {hero} подошло к концу на {day}-й день.\nЛес оказался сильнее.")
    return "\n\n".join(parts)


# Алиас для обратной совместимости: Game = GameState
# Все модули, делающие from game_state import Game, получат тот же класс.
Game = GameState


# Дерево родителей для гарантированной навигации «↩️ Назад» (Блок 2)
PARENT_SCREEN: Dict[str, str] = {
    # Поддерево инвентаря
    "inventory": "main",
    "inspect": "inventory",
    "item_card": "inspect",
    "craft": "inventory",
    "recipes": "craft",
    "drop": "inventory",
    "drop_qty": "inventory",
    "character": "inventory",
    # Поддерево костра
    "campfire": "main",
    "campfire_fuel": "campfire",
    "fuel_qty": "campfire_fuel",
    "campfire_recipes": "campfire",
    "recipe_card": "campfire_recipes",
    # Прочие экраны
    "locations": "main",
    "l1_dome": "locations",
    "wolf_lair": "locations",
    "wolf_battle": "wolf_lair",
    "combat": "wolf_lair",
    "settings": "main",
    "tablet_notes": "main",
    "traps": "inventory",
}

CANONICAL_STACKS: Dict[str, List[str]] = {
    "main": ["main"],
    "inventory": ["main", "inventory"],
    "inspect": ["main", "inventory", "inspect"],
    "item_card": ["main", "inventory", "inspect", "item_card"],
    "craft": ["main", "inventory", "craft"],
    "recipes": ["main", "inventory", "craft", "recipes"],
    "drop": ["main", "inventory", "drop"],
    "character": ["main", "inventory", "character"],
    "traps": ["main", "inventory", "traps"],
    "campfire": ["main", "campfire"],
    "campfire_fuel": ["main", "campfire", "campfire_fuel"],
    "fuel_qty": ["main", "campfire", "campfire_fuel", "fuel_qty"],
    "campfire_recipes": ["main", "campfire", "campfire_recipes"],
    "recipe_card": ["main", "campfire", "campfire_recipes", "recipe_card"],
    "locations": ["main", "locations"],
    "l1_dome": ["main", "locations", "l1_dome"],
    "wolf_lair": ["main", "locations", "wolf_lair"],
    "wolf_battle": ["main", "locations", "wolf_lair", "wolf_battle"],
    "combat": ["main", "locations", "wolf_lair", "combat"],
    "settings": ["main", "settings"],
    "tablet_notes": ["main", "tablet_notes"],
}


def get_settings_text(game: Any = None) -> str:
    return (
        "⚙️ **Настройки**\n\n"
        "Интерфейс игры работает в стандартном полноразмерном режиме Telegram.\n"
        "Обрезка сообщений отключена для сохранения всех слотов и описаний."
    )


def handle_back_navigation(game: Any, uid: int) -> Tuple[Optional[str], Optional[Any]]:
    """Обрабатывает нажатие кнопки «↩️ Назад» и возвращает (text, kb) для целевого экрана.

    Детерминированно смотрит текущий экран в PARENT_SCREEN и восстанавливает
    канонический стек из CANONICAL_STACKS.
    """
    from keyboards import (
        get_main_kb,
        inventory_inline_kb,
        character_inline_kb,
        get_inspect_menu_kb,
        get_drop_item_kb,
        get_campfire_kb,
        get_campfire_recipes_kb,
        get_campfire_fuel_kb,
        get_locations_kb,
        get_settings_kb,
    )
    from crafts import get_craft_menu_text, get_craft_menu_kb
    from modules.cooking import get_campfire_text, COOKING_RECIPES, can_cook
    from story.location_stories import handle_story, handle_l1_wolf_lair

    if getattr(game, "story_state", None) not in ("WAITING_FOR_CHARACTER_NAME", "WAITING_FOR_PET_NAME"):
        game.story_state = None
    if hasattr(game, "story_flags") and isinstance(game.story_flags, dict):
        game.story_flags.pop("drop_item_name", None)
        game.story_flags.pop("fuel_item", None)
        game.story_flags.pop("cook_recipe_id", None)

    current = game.nav_stack[-1] if getattr(game, "nav_stack", None) else "main"
    target = PARENT_SCREEN.get(current, "main")

    # Выставляем канонический стек для target экрана
    game.nav_stack = list(CANONICAL_STACKS.get(target, ["main"]))

    if target == "main":
        game.active_story_callback = None
        if getattr(game, "story_state", None) not in ("WAITING_FOR_CHARACTER_NAME", "WAITING_FOR_PET_NAME"):
            game.story_state = None
        text = game.get_ui()
        kb = get_main_kb(game)
    elif target == "inventory":
        text = game.get_inventory_text()
        kb = inventory_inline_kb
    elif target == "character":
        text = game.get_character_text()
        kb = character_inline_kb
    elif target in ("craft", "recipes"):
        text = get_craft_menu_text(game)
        kb = get_craft_menu_kb(game)
    elif target == "inspect":
        items_in_inv = [item for item, c in game.inventory.items() if c > 0]
        if items_in_inv:
            text = "🔍 Подробный осмотр предметов\n\nВыберите предмет из инвентаря, чтобы изучить его описание, эффекты и свойства:"
            kb = get_inspect_menu_kb(game)
        else:
            text = game.get_inventory_text()
            kb = inventory_inline_kb
    elif target == "drop":
        if any(count > 0 for count in game.inventory.values()):
            text = "Выберите предмет для удаления:"
            kb = get_drop_item_kb(game)
        else:
            text = game.get_inventory_text()
            kb = inventory_inline_kb
    elif target == "campfire":
        text = get_campfire_text(game)
        kb = get_campfire_kb(game)
    elif target == "campfire_recipes":
        available_count = sum(1 for r_id in COOKING_RECIPES if can_cook(game, r_id))
        if available_count > 0:
            text = "📜 Рецепты костра\n\nВыберите блюдо, чтобы узнать ингредиенты и приготовить:"
        else:
            text = "📜 Рецепты костра\n\nСейчас у вас недостаточно ингредиентов ни для одного блюда.\nНайдите ягоды, грибы, мясо, воду или кусок коры."
        kb = get_campfire_recipes_kb(game)
    elif target == "campfire_fuel":
        cur_d = getattr(game, "campfire_durability", 0)
        max_d = getattr(game, "campfire_max_durability", 10)
        text = f"🔥 КОСТЁР ({cur_d}/{max_d})\nВыберите топливо для поддержания огня:"
        kb = get_campfire_fuel_kb(game)
    elif target == "locations":
        text = "Куда направиться?"
        kb = get_locations_kb(game)
    elif target == "wolf_lair":
        text, kb = handle_l1_wolf_lair("wolf_lair_enter", game, uid)
    elif target == "settings":
        text = get_settings_text(game)
        kb = get_settings_kb(game)
    else:
        text = game.get_ui()
        kb = get_main_kb(game)

    return text, kb


# Алиас для альтернативного именования
resolve_back_screen = handle_back_navigation




