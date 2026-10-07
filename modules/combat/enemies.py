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
        "screen_callback": "wolf_battle_screen",
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
        "screen_callback": "boar_battle_screen",
    },
    "giant_slime": {
        "id": "giant_slime",
        "name": "Исполинский слайм",
        "title": "☣️ ЗАВОДЬ ИСПОЛИНА",
        "max_hp": 555,
        "attack_min": 10,
        "attack_max": 16,
        "defended_min": 4,
        "defended_max": 8,
        "charge_damage": 26,
        "start_log": "Слайм колышется, ядро смещается ВПРАВО.",
        "victory_callback": "l5_2_7",
        "flee_callback": "l5_arena_escape",
        "flee_text": (
            "Ты отступаешь по узкой осыпи прочь из заводи, пока тварь не успела отрезать путь назад."
        ),
        "screen_callback": "slime_battle_screen",
    },
    "trash_slime": {
        "id": "trash_slime",
        "name": "Мусорный слайм",
        "title": "🕳️ ЛОГОВО МУСОРНОГО СЛАЙМА",
        "max_hp": 800,
        "attack_min": 14,
        "attack_max": 22,
        "defended_min": 6,
        "defended_max": 10,
        "charge_damage": 35,
        "start_log": "Мусорный слайм вздымается со дна промоины, ощетинившись обломками костей и ржавой сталью!",
        "victory_callback": "l5_ancient_win",
        "flee_callback": "l5_ancient_escape",
        "flee_text": (
            "Ты отступаешь по сланцевым уступам вверх из промоины, спасаясь от едкой массы."
        ),
        "screen_callback": "trash_slime_battle_screen",
    },
}


def get_enemy(enemy_id: str = "old_wolf") -> Dict[str, Any]:
    """Получить конфигурацию врага по его ID (по умолчанию старый волк)."""
    return ENEMIES.get(enemy_id, ENEMIES["old_wolf"])
