"""
modules/combat — Универсальный боевой модуль (боссы, противники, раунды боя).
"""

from modules.combat.enemies import ENEMIES, get_enemy
from modules.combat.engine import (
    start_battle,
    apply_action,
    get_battle_text,
)

# Алиас для обратной совместимости
get_wolf_battle_text = get_battle_text

__all__ = [
    "ENEMIES",
    "get_enemy",
    "start_battle",
    "apply_action",
    "get_battle_text",
    "get_wolf_battle_text",
]
