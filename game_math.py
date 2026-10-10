"""
game_math.py — Унифицированная математика урона и списания ресурсов.

Логика строго детерминирована (без random), с акцентом на физику выживания:
- Зависимость расхода ресурсов (голод/жажда) от уровня HP
- Зависимость доступных очков действий (AP) от уровня HP
- Прямой расчёт урона по HP без пола 1 и без перенапряжения
"""

import math


def process_damage(game_state, raw_damage: int = 0) -> tuple[int, str]:
    """Обработка урона персонажу (без пола 1 и без перенапряжения)."""
    hp = getattr(game_state, "hp", 100)
    try:
        effective_damage = max(0, int(raw_damage or 0))
    except (TypeError, ValueError):
        effective_damage = 0
    new_hp = max(0, hp - effective_damage)
    if game_state is not None:
        game_state.hp = new_hp

    if new_hp <= 0:
        return 0, f"Ты получил {effective_damage} урона. Здоровье упало до 0."
    if effective_damage > 0:
        return new_hp, f"Ты получил {effective_damage} урона."
    return new_hp, "Урон поглощён."


def get_resource_multiplier(game_state: object, resource_type: str) -> float:
    """
    Получить коэффициент расхода ресурса в зависимости от HP.

    Логика:
    - HP >= 50% → x1.0 (базовый режим)
    - 21% <= HP <= 49% → Голод x1.15, Жажда x1.5
    - HP <= 20% → Голод x1.3, Жажда x2.0

    Аргументы:
        game_state: Объект GameState
        resource_type: "hunger" или "thirst"

    Возвращает:
        float — коэффициент (1.0, 1.15, 1.3 и т.д.)
    """
    hp = getattr(game_state, "hp", 100)
    
    if resource_type == "hunger":
        if hp >= 50:
            return 1.0
        elif hp >= 21:
            return 1.15
        else:
            return 1.3
    elif resource_type == "thirst":
        if hp >= 50:
            return 1.0
        elif hp >= 21:
            return 1.5
        else:
            return 2.0
    
    return 1.0  # Дефолт


def get_base_resource_cost(game_state: object, base_cost: int = 2) -> int:
    """
    Рассчитать базовую стоимость ресурса с учётом погоды и HP.

    Используется для обычных действий (поиск, крафт и т.д.).

    Аргументы:
        game_state: Объект GameState
        base_cost: int — базовая стоимость (по умолчанию 2)

    Возвращает:
        int — итоговая стоимость
    """
    multiplier = get_resource_multiplier(game_state, "hunger")
    weather = getattr(game_state, "weather", "clear")
    
    # В грозу голод тратится в 3 раза быстрее
    weather_modifier = 3 if weather == "storm" else 1
    
    cost = int(base_cost * multiplier * weather_modifier)
    return cost


def get_thirst_base_cost(game_state: object, base_cost: int = 1) -> int:
    """
    Рассчитать базовую стоимость жажды с учётом погоды и HP.

    Аргументы:
        game_state: Объект GameState
        base_cost: int — базовая стоимость (по умолчанию 1)

    Возвращает:
        int — итоговая стоимость
    """
    multiplier = get_resource_multiplier(game_state, "thirst")
    weather = getattr(game_state, "weather", "clear")
    
    if weather == "storm":
        weather_modifier = 2.0
    elif weather == "rain":
        weather_modifier = 0.75
    elif weather == "cloudy":
        weather_modifier = 0.5
    else:  # clear
        weather_modifier = 1.0
    
    cost = max(1, int(round(base_cost * multiplier * weather_modifier)))
    return cost


def calculate_ap_by_hp(game_state: object) -> int:
    """
    Рассчитать дневные действия (AP) по текущему HP.

    Логика:
    - HP >= 50 → 5 действий
    - HP 40-49 → 4 действия
    - HP 30-39 → 3 действия
    - HP 10-29 → 2 действия
    - HP < 10 → 1 действие

    Аргументы:
        game_state: Объект GameState

    Возвращает:
        int — количество действий в день
    """
    hp = getattr(game_state, "hp", 100)
    
    if hp >= 50:
        return 5
    elif hp >= 40:
        return 4
    elif hp >= 30:
        return 3
    elif hp >= 10:
        return 2
    else:
        return 1


def get_starvation_damage(hunger: int) -> int:
    """Урон HP от уровня сытости за действие (таблица B).

    Шкала:
    - >= 40 → 0
    - 20–39 → -2 (2 урона)
    - 1–19  → -4 (4 урона)
    - 0     → -6 (6 урона)
    """
    h = max(0, int(hunger))
    if h >= 40:
        return 0
    elif h >= 20:
        return 2
    elif h >= 1:
        return 4
    else:
        return 6


def get_dehydration_damage(thirst: int) -> int:
    """Урон HP от уровня жажды за действие (таблица B).

    Шкала:
    - >= 40 → 0
    - 20–39 → -2 (2 урона)
    - 1–19  → -4 (4 урона)
    - 0     → -6 (6 урона)
    """
    t = max(0, int(thirst))
    if t >= 40:
        return 0
    elif t >= 20:
        return 2
    elif t >= 1:
        return 4
    else:
        return 6


def calculate_survival_damage(hunger: int, thirst: int) -> int:
    """Суммарный урон от голода и жажды по таблице B (только Исследовать и Сон)."""
    return get_starvation_damage(hunger) + get_dehydration_damage(thirst)


def calculate_passive_regen(hunger: int, thirst: int, action_type: str = "explore") -> int:
    """Пассивный реген HP (таблица A).

    Условие: hunger >= 70 И thirst >= 70. Иначе 0.
    - Исследовать: +2 HP
    - Сон: +4 HP
    """
    h = max(0, int(hunger))
    t = max(0, int(thirst))
    if h >= 70 and t >= 70:
        if str(action_type).lower() in ("sleep", "action_sleep", "action_4"):
            return 4
        return 2
    return 0
