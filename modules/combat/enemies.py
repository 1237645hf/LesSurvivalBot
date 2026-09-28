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
        "attack_max": 8,
        "defended_min": 2,
        "defended_max": 4,
        "start_log": "Ты переступаешь порог пещеры. Волк припадает на передние лапы и глухо рычит.",
        "victory_callback": "l1_5_aftermath",
        "flee_callback": "locations_menu",
        "flee_text": (
            "Ты резко отшатываешься назад, выставив посох перед собой, и сломя голову выбегаешь из пещеры обратно в овраг. "
            "За спиной раздаётся яростный, но бессильный хрип зверя."
        ),
    },
    "ancient_boar": {
        "id": "ancient_boar",
        "name": "Секач солонца",
        "title": "🐗 СОЛОНЕЦ СЕКАЧА",
        "max_hp": 350,
        "attack_min": 22,
        "attack_max": 26,
        "defended_min": 10,
        "defended_max": 14,
        "charge_damage": 50,
        "start_log": "⚠️ ТАРАН! Урон: 50. Сметёт всё на пути!",
        "victory_callback": "l3_11a_win",
        "flee_callback": "l3_flee_to_camp",
        "flee_text": (
            "Ты отпрыгиваешь назад, скатываешься по осыпи и укрываешься за каменными плитами Лощины. "
            "Секач шумно сопит у солонца, не преследуя тебя дальше."
        ),
    },
}


def get_enemy(enemy_id: str = "old_wolf") -> Dict[str, Any]:
    """Получить конфигурацию врага по его ID (по умолчанию старый волк)."""
    return ENEMIES.get(enemy_id, ENEMIES["old_wolf"])
