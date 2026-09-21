"""
game_math.py — Унифицированная математика урона и списания ресурсов.

Логика строго детерминирована (без random), с акцентом на физику выживания:
- Снижение урона при низком HP
- Предохранитель HP (не ниже 1)
- Перенапряжение при HP < 30% (урон конвертируется в ресурсы)
"""

import math


def process_damage(game_state, raw_damage: int) -> tuple[int, str]:
    """Обработка урона и перенапряжения с предохранителем `max(1, ...)`."""
    hp = getattr(game_state, "hp", 100)
    max_hp_damage = hp - 1
    effective_damage = min(raw_damage, max_hp_damage)
    
    # Здоровье не падает ниже 1
    new_hp = max(1, hp - effective_damage)
    log_parts = []
    
    if new_hp < 30 and effective_damage > 10:
        absorbed = raw_damage - effective_damage
        resource_cost = min(15, max(1, math.ceil(absorbed / 10)))
        
        hunger = getattr(game_state, "hunger", 50)
        thirst = getattr(game_state, "thirst", 75)
        
        if hunger >= thirst:
            game_state.hunger = max(1, hunger - resource_cost)
            log_parts.append(f"Перенапряжение: Голод упал на {resource_cost}.")
        else:
            game_state.thirst = max(1, thirst - resource_cost)
            log_parts.append(f"Перенапряжение: Жажда упала на {resource_cost}.")
        
        game_state.hp = new_hp
    else:
        game_state.hp = new_hp
    
    if new_hp < hp:
        log_parts.append(f"Ты получил {effective_damage} урона.")
    
    log_text = "\n".join(log_parts) if log_parts else "Урон поглощён."
    return new_hp, log_text


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
    
    # В пасмурную погоду жажда не тратится
    weather_modifier = 1 if weather == "cloudy" else 1
    
    cost = int(base_cost * multiplier * weather_modifier)
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
