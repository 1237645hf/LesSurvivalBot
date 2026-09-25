"""
enemies.py — Конфигурации боевых противников.
"""
from typing import Dict, Any


ENEMIES: Dict[str, Dict[str, Any]] = {
    "old_wolf": {
        "id": "old_wolf",
        "name": "Старый волк",
        "title": "🐺 ЛОГОВО СТАРОГО ВОЛКА",
        "max_hp": 50,
        "attack_min": 5,
        "attack_max": 7,
        "defended_min": 2,
        "defended_max": 4,
        "start_log": "Ты переступаешь порог пещеры. Волк припадает на передние лапы и глухо рычит.",
        "victory_callback": "l1_5_aftermath",
        "flee_callback": "locations_menu",
        "flee_text": (
            "Ты резко отшатываешься назад, выставив посох перед собой, и сломя голову выбегаешь из пещеры обратно в овраг. "
            "За спиной раздаётся яростный, но бессильный хрип зверя."
        ),
    }
}


def get_enemy(enemy_id: str = "old_wolf") -> Dict[str, Any]:
    """Получить конфигурацию врага по его ID (по умолчанию старый волк)."""
    return ENEMIES.get(enemy_id, ENEMIES["old_wolf"])
