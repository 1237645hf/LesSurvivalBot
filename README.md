# Лесная игра (LesSurvivalBot)

Telegram-бот: survival, 7 локаций, сюжет, карма, 7 концовок.
Python 3.10+, aiogram 3, polling (Render / локально).

---

## Для ИИ и разработчика — прочитай ВЕСЬ файл

1. Читай **от начала до конца**. Не останавливайся на середине.
2. Конец документа = блок **«Последнее обновление»** с датой в самом низу. Пока не увидел эту дату — чтение не завершено.
3. Не выдумывай файлы и таблицы, которых нет в разделах ниже.
4. Не возвращай удалённый `CAMPFIRE_RECIPES` в `main.py`.
5. Тесты только в `tests/`. Не клади `test_*.py` в корень.
6. Windows: Python через `.venv` и оператор `&` в PowerShell (раздел «Запуск»).

Статический разбор кода — нормален. Не выдумывай «второй» баланс еды.

---




---

## Архитектура: Fat Module, Thin Loader

```
main.py              — Telegram, callback’и, тонкие вызовы modules
game_state.py        — HP, голод, жажда, AP, костёр, traps, flask_water, save/load
game_math.py         — урон, множители голода/жажды, AP по HP
location_stories.py  — сюжет L1–L7 + финалы
location_crafts.py   — крафт по локациям
location_sources.py  — длинные тексты
crafts.py            — глобальный крафт
keyboards.py         — Inline + нижнее Reply-меню
modules/
  items.py           — реестр предметов, effects, is_item_consumable
  cooking.py         — COOKING_RECIPES, cook_item (кора, вода 0–3, теги)
  traps.py           — ловушки, TRAP_LOOT_TABLE, process_trap_rollover
  finds.py           — лут исследования L1–L7 + бонус кора/глина
  hints.py           — подсказки
```

`main.py` не хранит таблицы еды/рецептов — только вызывает modules.

---

## 🛑 STRICT AI AGENT RULES (ПРАВИЛА ДЛЯ ИИ-ПОМОЩНИКА)

### 1. ПОЛНЫЙ ЗАПРЕТ НА ТЕРМИНАЛ И ИСПОЛНЕНИЕ КОМАНД

- **СТРОГО ЗАПРЕЩЕНО** использовать терминал, консоль PowerShell или CMD для выполнения ЛЮБЫХ команд.
- **ЗАПРЕЩЕНО** выполнять системные команды поиска и инвентаризации (например, `Get-ChildItem`, `dir`, `ls`, `find`).
- **ЗАПРЕЩЕНО** запускать Python-скрипты, тесты или однострочники (например, `python main.py`, `python -c "..."`, `pytest`, `py_compile`).
- У тебя **НЕТ доступа** к окружению и терминалу. Вся работа — это **СТАТИЧЕСКИЙ АНАЛИЗ** (чтение кода глазами и поиск через инструменты редактора).

### 2. РАЗМЕЩЕНИЕ ФАЙЛОВ И ТЕСТОВ

- **ЗАПРЕЩЕНО** создавать временные `.py` файлы, проверки и отладочные скрипты в корне проекта (например, `check_items.py`, `debug.py`).
- Все проверочные автотесты разрешено создавать **ТОЛЬКО** в папке `tests/`.

### 3. РАЗРЕШЁННЫЕ И ЗАПРЕЩЁННЫЕ ИНСТРУМЕНТЫ
**✅ РАЗРЕШЕНО (Используй это)**|**❌ ЗАПРЕЩЕНО (Вызовет сбой ИИ)**|
|:---|:---|
|Чтение файлов через инструменты редактора (`read_file`)|Запуск терминала PowerShell / Cmd / Bash|
|Поиск по тексту и файлам (`search_files`, `grep`)|Выполнение `Get-ChildItem` или `dir`|
|Анализ структуры кода в уме|Запуск `python -c "import ..."`|
|Составление таблиц и отчётов в ответе пользователю||
|Создание `.py` скриптов в корне проекта| |

---

## Куда класть код

| Что | Куда |
|-----|------|
| Сюжет локации | `location_stories.py` + `elif` в `main.py` |
| Локальный крафт | `location_crafts.py` |
| Глобальный крафт (предметы) | **`crafts.py`** → `CRAFT_RECIPES` + `do_craft` |
| Лут исследования | **только** `modules/finds.py` |
| Свойства предметов / еда / Схема | **только** `modules/items.py` |
| Рецепты готовки у костра | **только** `modules/cooking.py` |
| Ловушки | **только** `modules/traps.py` |
| Поля save (в т.ч. костёр, unlocked_crafts) | `game_state.py` → `to_document` / `from_document` |
| Кнопки | `keyboards.py` + обработчик в `main.py` |
| Тест | `tests/` |

**Нельзя:** `modules/locations.py`, `modules/quests.py`, `modules/crafting.py`, второй набор рецептов/`CAMPFIRE_RECIPES` в `main.py`.

### Callback-префиксы

`action_1` (исследовать), `action_2` (инвентарь), `action_3` (пить), `action_4` / сон,  
`inv_craft`, `inv_recipes`, `inv_use`, `use_consumable_*`,  
`craft_*`, `campfire_confirm_light`, `menu_campfire`, `campfire_*`,  
`cook_*`, префиксы локаций (`river_`, `slate_`, `hunters_`, …).

---

## Игровые системы (актуально)

### Исследование (`action_1` → `modules/finds.py`)

- При `ap <= 0` — отказ, без лута.
- Иначе `consume_action(action_type="search")`, затем `roll_find` + инвентарь.
- Лут зависит от локации; бонус: кора; на L3 ещё глина.

### Готовка у костра (`modules/cooking.py`)

- Нужен **активный костёр** (см. ниже).
- 1× «Кусок коры» на рецепт.
- Вода из **фляги** `flask_water`: 0 / 1 / 2 / 3 по рецепту.
- Теги: любая ягода из `BERRY_ITEMS`, любой гриб из `MUSHROOM_ITEMS`.
- 7 рецептов: печёные ягоды, жареные грибы, мясо на коре, отвар, похлёбки, тушёнка.

### Предметы (`modules/items.py`)

- Ягоды: Лесная, Красная, Фиолетовая, Болотная, Горная.
- Грибы: Лесной, Дикий, Болотный, Пещерный, Горный.
- Расходники: `is_item_consumable` + `get_item_effects` (Сухпай, вода, ягоды…).
- **«Костёр»** — предмет после крафта; `can_use=True`; розжиг только через «Использовать».
- **«Схема»** — **заглушка** (предмет есть, логика открытия рецептов по схеме — TODO, не выдумывать).

### Ловушки (`modules/traps.py`)

- Разблокировка с L4; установка на L1–L7, одна на локацию.
- После сна: 40% ломка / 60% успех + `TRAP_LOOT_TABLE`.
- `apply_trap_loot_to_inventory(game, loot)` — **сначала game, потом loot**.

### Костёр и AP (`game_state.py`)

- `light_campfire()`: 1 AP, ресурсы, прочность 10, `campfire_active=True`.
- `consume_action(..., ap_cost=1)` **по умолчанию**: при успехе и `action_type != "sleep"` прочность костра −1.
- Не ставь `ap_cost=0` по умолчанию — иначе костёр не сгорает при обычных действиях.
- Статус-бар всегда: `🔥n/10` или `🔥Потух`.

### `consume_action`

Параметры: `action_type`, `base_hunger`, `base_thirst`, **`ap_cost=1`**.  
Возвращает фактические дельты. Лог игроку — `format_resource_log_text(deltas)` по факту.

---

## 7 локаций

1 Лесной старт · 2 Ручей · 3 Лощина · 4 Просека охотников · 5 Яр слизней · 6 Мохнатая пещера · 7 Вершина святилища (финалы)

---

## Запуск (Windows / PowerShell)

Для **человека / CI**. ИИ-агенту в VS Code терминал по правилам выше **запрещён**.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& ".\.venv\Scripts\Activate.ps1"

& ".\.venv\Scripts\python.exe" -m py_compile main.py game_state.py crafts.py
& ".\.venv\Scripts\python.exe" -c "from modules import items, cooking, traps, finds; print(len(cooking.COOKING_RECIPES), items.BERRY_ITEMS[0])"
& ".\.venv\Scripts\python.exe" -m pytest tests/ -v
& ".\.venv\Scripts\python.exe" main.py
```

Ожидаемо: `7 Лесная ягода`.  
Переменные: `TOKEN`, опционально `MONGO_URI`.

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

---

## Советы при добавлении контента

1. **Новый ресурс с локации** — имя и effects в `items.py`, шанс в `finds.py`. Не пиши лут в `main.py`.
2. **Новый рецепт готовки у костра** — только `cooking.py`.
3. **Новый глобальный крафт** — `CRAFT_RECIPES` в `crafts.py` + при необходимости старт в `unlocked_crafts`.
4. **Новая ветка сюжета** — `location_stories.py` + `elif` в `main.py` + кнопка в `keyboards.py`.
5. **Новое поле состояния** — `game_state.py` + `to_document` / `from_document`.
6. **Новый расходник** — `items.py` с `effects` и `can_use=True`.
7. Кнопки — с **одним** эмодзи в начале текста.
8. Сначала точечный баг, потом рефактор. Не плодить вторые таблицы.

---

## Структура репозитория

| Путь | Роль |
|------|------|
| `main.py` | Оркестратор, callback’и |
| `game_state.py` / `game_math.py` | Состояние, сон, костёр, AP |
| `crafts.py` | Глобальный крафт предметов |
| `modules/*` | Еда, лут, ловушки, готовка, items |
| `location_*.py`, `keyboards.py` | Сюжет, UI |
| `tests/` | Автотесты |
| `requirements.txt`, `Procfile`, `render.yaml` | Деплой |

---

## Последнее обновление

**Дата:** 2026-09-23

Документ прочитан полностью, только если ты видишь эту дату и строку выше.  
Статус: modules + main + game_state согласованы; `ap_cost` по умолчанию должен быть **1**; статус костра всегда в UI.
