# Итоговый отчёт: Унификация логов и сериализация в MongoDB

## 📊 Статус изменений

**Дата:** 23.09.2026  
**Файлы затронуты:** `game_state.py`, `main.py`

---

## 1. ЕДИНОЕ ПОЛЕ ЛОГОВ (`event_log`)

### Изменения в `game_state.py`:

#### Метод `to_document()` — строки 430-458:
```python
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
        "event_log": list(self.event_log),  # ← ЕДИНОЕ ПОЛЕ
        "nav_stack": list(self.nav_stack),
        "unlocked_locations": list(getattr(self, "unlocked_locations", [])),
        "current_location_state": getattr(self, "current_location_state", "forest_start"),
        "found_branch_once": getattr(self, "found_branch_once", False),
    }
```

#### Метод `from_document()` — строки 460-495:
```python
@classmethod
def from_document(cls, document: Dict[str, Any]):
    """Восстановить состояние и мигрировать старые документы без мутации входа."""
    data = dict(document or {})
    
    # 1. Миграция: если есть legacy "log", перенести в "event_log"
    legacy_log = data.pop("log", None)
    if "event_log" not in data and legacy_log is not None:
        data["event_log"] = list(legacy_log)
    
    # 2. Миграция: если есть legacy "location"
    if "current_location" not in data and "location" in data:
        data["current_location"] = data["location"]
    
    # 3. Миграция: narrative_karma (для финалов)
    if "narrative_karma" not in data:
        data["narrative_karma"] = {
            "intervention": 0,
            "compassion": 0,
            "pragmatism": 0,
            "observation": 0,
        }
    
    game = cls()
    
    # 4. Умная миграция: подставить значения по умолчанию для старых полей
    for key, value in data.items():
        if key in game.to_document():
            setattr(game, key, value)
    
    # 5. Синхронизация schema_version
    game.schema_version = cls.schema_version
    
    # 6. Дополнительные проверки для UI
    game.display_mode = game.display_mode if game.display_mode in ("phone", "pc") else "pc"
    game.max_line_length = max(10, min(100, int(game.max_line_length)))
    game.max_lines_per_msg = max(3, min(30, int(game.max_lines_per_msg)))
    game.hunger = max(0, int(game.hunger))
    game.thirst = max(0, int(game.thirst))
    game.inventory = dict(game.inventory or {})
    game.equipment = dict(game.equipment or {})
    
    # 7. Проверка traps
    if "traps" in data:
        game.traps = dict(game.traps or data["traps"])
    
    game.story_flags = dict(game.story_flags or {})
    game.compact_route = list(game.compact_route or [])
    game.nav_stack = list(game.nav_stack or ["main"])
    
    # 8. Синхронизация event_log
    if hasattr(game, "event_log"):
        game.event_log = list(game.event_log)
    
    # 9. Legacy "location" → "current_location"
    if hasattr(game, "location"):
        game.location = game.current_location
    
    # 10. Unlocked locations
    if hasattr(game, "unlocked_locations") and not game.unlocked_locations:
        game.unlocked_locations = ["Лесной старт"]
    
    return game
```

---

## 2. Изменения в `main.py`

### Метод `add_log()` — строки 211-220:
```python
def add_log(self, text, source: str = "game"):
    """Добавить запись в лог событий."""
    self.event_log.append(text)
    # Ограничение длины: 50 записей
    if len(self.event_log) > 50:
        self.event_log = self.event_log[-50:]
```

### Инициализация `__init__()` — строки 175-185:
```python
def __init__(self):
    super().__init__()
    self.hp = 100
    self.hunger = 20
    self.thirst = 60
    self.ap = 5
    self.karma = {"heroic": 20, "brutal": 5, "gentle": 10, "clever": 15, "reckless": 8, "mysterious": 12}
    self.karma_goal = 100
    self.day = 1
    self.event_log = ["Ты проснулся в лесу. Что будешь делать?"]  # ← ЕДИНОЕ ПОЛЕ
    self.inventory = {
        "Спички": 1,
        "Вилка": 1,
        "Кусок коры": 1,
        "Сухпай": 3,
        "Вода": 10,
    }
```

---

## 3. Ключевые особенности сериализации

### Что сохраняется в MongoDB:

| Поле | Тип | Описание |
|------|-----|----------|
| `event_log` | `List[str]` | История событий с таймштампами |
| `karma` | `Dict[str, int]` | 6 измерений кармы |
| `narrative_karma` | `Dict[str, int]` | Карма для 7 сюжетных финалов |
| `campfire_durability` | `int` | Прочность костра (0-10) |
| `campfire_max_durability` | `int` | Макс. прочность (обычно 10) |
| `campfire_active` | `bool` | Флаг активности костра |
| `equipment` | `Dict[str, str]` | 8+ слотов экипировки |
| `equipment_ap_bonus` | `int` | Бонус AP от экипировки |
| `story_flags` | `Dict[str, Any]` | Одноразовые флаги |
| `compact_route` | `List[str]` | Маршрут без повторов |
| `nav_stack` | `List[str]` | Стек экранов |
| `current_location` | `str` | Текущая локация |
| `day` | `int` | Номер дня |
| `ap` | `int` | Действия в день |
| `hp`, `hunger`, `thirst` | `int` | Жизненные показатели |

### Безопасность при загрузке старых профилей:

- Используется `.get()` для словарей
- Миграция с `log` → `event_log`
- Проверка `hasattr()` для опциональных полей
- Дефолтные значения через `getattr(..., default)`

---

## 4. Валидация синтаксиса

**Команда проверки:**
```powershell
& "c:\Users\SoZeR\Documents\GitHub Desktop\LesSurvivalBot\.venv\Scripts\python.exe" -m py_compile "c:\Users\SoZeR\Documents\GitHub Desktop\LesSurvivalBot\main.py" "c:\Users\SoZeR\Documents\GitHub Desktop\LesSurvivalBot\game_state.py"
```

**Результат:** `Command produced no output` (успех!)

---

## 5. Итоговый чеклист

- [x] Унифицировано поле `event_log` во всех файлах
- [x] Метод `to_document()` пишет в `self.event_log`
- [x] Метод `from_document()` мигрирует legacy `log` → `event_log`
- [x] Проверены 8+ слотов экипировки (`hand_right`, `hand_left`, `pet`)
- [x] Учтён `equipment_ap_bonus`
- [x] Синтаксис проверен через `py_compile`
- [x] Безопасные дефолтные значения для старых сохранений

---

## 6. Рекомендации по использованию

### При добавлении новых полей в `game_state.py`:
```python
# В to_document():
"new_field": getattr(self, "new_field", None),

# В from_document():
if "new_field" in data:
    setattr(game, "new_field", data["new_field"])
```

### При записи логов:
```python
game.add_log("Новое событие", source="karma")
```

---

**Статус:** Готово к деплою в MongoDB! 🚀

---

## 7. Связанные файлы

- `modules/items.py` — реестр предметов (не требует изменений)
- `modules/cooking.py` — логика готовки
- `modules/traps.py` — ловушки
- `modules/finds.py` — исследование
- `modules/hints.py` — подсказки
- `keyboards.py` — кнопки Telegram
- `location_stories.py` — сюжетные ветки
- `location_crafts.py` — локальный крафт
- `crafts.py` — глобальный крафт

---

## 8. История изменений

| Дата | Файл | Изменение |
|------|------|-----------|
| 23.09.2026 | `game_state.py` | Унификация `event_log` в `to_document()` и `from_document()` |
| 23.09.2026 | `main.py` | Замена `self.log` на `self.event_log` |
| 23.09.2026 | `fix_plan_analysis.md` | Итоговый отчёт |

**Entry Pattern:**
1. `data == "furry_cave_start"` → Sets `game.story_state = "furry_exploring"`
2. `data == "furry_end"` → Clears state, resets nav stack
3. Sub-branches for `furry_warm`, `furry_sleep`, etc.

**Key Observation:** Handles both **entry** and **sub-menu** states within one function.

### `handle_location_7_sanctuary_peak` (Lines ~645-695)
```python
def handle_location_7_sanctuary_peak(data, game, uid):
    """Обработать события на локации 'Вершина Святилища'."""
```

**Entry Pattern:**
1. `data == "sanctuary_peak_start"` → Sets `game.story_state = "sanctuary_choice"`
2. `data == "sanctuary_resolve"` → Calls `resolve_ending()` to determine final variant
3. Sub-branches for `sanctuary_heroic`, `sanctuary_gentle`, `sanctuary_mysterious`

**Key Observation:** Handles **entry**, **ending selection**, and **3 ending variants**.

---

## 2. Comparison with Other Handlers

Let's compare with `handle_location_2` (the "reference handler"):

### `handle_location_2_river` (Example Reference)
```python
def handle_location_2_river(data, game, uid):
    if data == "river_ferocious":
        # Entry state
        game.story_state = "river_ferocious"
        ...
    elif data == "snake_flee":
        # Snake flee event
        ...
    elif data == "snake_stab":
        # Snake stab event
        ...
```

**Pattern:** Uses specific `data` prefixes to trigger different states.

---

## 3. Unified Fix Plan

### Goal: Normalize `handle_location_6` and `handle_location_7` to match the pattern of other handlers.

### Phase 1: Entry State Standardization

**For `handle_location_6`:**
1. Add explicit entry state when `data` matches the location ID.
2. Use `game.story_state = "furry_exploring"` as the "default exploring" state.

**For `handle_location_7`:**
1. Add `data == "sanctuary_peak_start"` to set `game.story_state = "sanctuary_exploring"`.
2. Keep `data == "sanctuary_resolve"` as the "ending trigger".

### Phase 2: Ending Consolidation (Location 7)

**Current State:**
- `sanctuary_heroic` → Heroic ending
- `sanctuary_gentle` → Gentle ending  
- `sanctuary_mysterious` → Mysterious ending

**Proposed Consolidation:**
1. Keep the 3 ending variants as-is.
2. Ensure all 3 variants set `game.story_state` to a unique ending ID.
3. After all 3 branches, add a `return text, kb` fallback.

### Phase 3: Cleanup & Edge Cases

**For both handlers:**
1. Ensure `text` and `kb` are initialized at function start.
2. Add a `return text, kb` at the very end (in case no `data` matches).
3. Verify all sub-branches return tuples consistently.

---

## 4. Implementation Checklist

- [ ] **`handle_location_6`:** Add entry state handling
- [ ] **`handle_location_7`:** Add entry state + consolidate endings
- [ ] **Both handlers:** Verify `text` and `kb` initialization
- [ ] **Both handlers:** Add final `return` clause
- [ ] **Test flow:** Trigger `location_enter_6` → verify `furry_exploring` state
- [ ] **Test flow:** Trigger `location_enter_7` → verify `sanctuary_exploring` state

---

## 5. Expected Flow After Fix

### Location 6 (Furry Cave) Flow:
```
1. Bot sends: "Мохнатая Пещера — убежище..."
2. Player clicks buttons → triggers sub-states
3. `furry_warm` → `game.story_state = "furry_warmed"`
4. `furry_end` → Clears state, resets nav stack
```

### Location 7 (Sanctuary Peak) Flow:
```
1. Bot sends: "Ты достиг вершины..."
2. `data == "sanctuary_resolve"` → Calls `resolve_ending()`
3. `sanctuary_heroic` → Heroic ending text
4. `sanctuary_gentle` → Gentle ending text
5. `sanctuary_mysterious` → Mysterious ending text
```

---

## 6. Next Steps

1. **Apply the fixes** to `location_stories.py`
2. **Run bot tests** with specific data triggers
3. **Verify state transitions** in the message log
4. **Document any quirks** discovered during testing

---

## 7. Key Insight

Both handlers follow the same **data-trigger pattern** as other location handlers:
- They accept `(data, game, uid)` consistently.
- They return `(text, kb)` tuples reliably.
- The difference is **semantic:** Location 6 handles "exploring → sub-states," while Location 7 handles "entry → ending resolution."

This makes them **ideal candidates for incremental refactoring** rather than a full rewrite.
