"""
modules/hints.py — Модуль для генерации контекстных подсказок игроку.
"""

from typing import List


def get_active_hints(game_state) -> List[str]:
    """
    Получить список активных подсказок для текущего состояния игры.

    Args:
        game_state: Объект GameState с инвентарём, экипировкой и флагами.

    Returns:
        Список строк с подсказками.
    """
    hints = []

    # Флаг, что подсказка на крафт факела уже показана
    hint_torch_craft_shown = getattr(game_state, "hint_torch_craft_shown", False)

    # Ингредиенты для факела (рецепт крафта: Ветка + Сухой мох)
    torch_craft_ingredients = [
        "Ветка",
        "Сухой мох",
    ]

    # Проверяем, есть ли все ингредиенты для факела
    has_all_ingredients = all(
        game_state.inventory.get(ingredient, 0) > 0
        for ingredient in torch_craft_ingredients
    )

    # Факел в инвентаре
    torch_in_inventory = game_state.inventory.get("Факел", 0) > 0

    # Факел экипирован в руку (поддержка левой, правой или общего слота)
    torch_equipped = (
        game_state.equipment.get("hand_left") == "Факел"
        or game_state.equipment.get("hand_right") == "Факел"
        or game_state.equipment.get("hand") == "Факел"
    )

    # Подсказка на крафт: ингредиенты собраны, факел ещё не скрафчен и не показывали подсказку
    if has_all_ingredients and not torch_in_inventory and not hint_torch_craft_shown:
        hints.append("«Кажется, из этого можно скрафтить факел.»")
        # Устанавливаем флаг, чтобы не спамить подсказкой
        game_state.hint_torch_craft_shown = True

    # Подсказка на экипировку: факел скрафчен и в инвентаре, но не в руке
    if torch_in_inventory and not torch_equipped:
        hints.append("«Лучше взять факел в руки.»")

    return hints
