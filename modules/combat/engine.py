"""
engine.py — Боевой движок пошаговых сражений.
Обрабатывает раунды боя: атака, защита, побег, расчёт урона и обновление состояния.
"""
import random
from typing import Tuple
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards import get_wolf_battle_kb
from modules.combat.enemies import get_enemy


def get_battle_text(game, enemy_id: str = "old_wolf") -> str:
    """Форматирует интерфейс боевого экрана."""
    enemy = get_enemy(enemy_id)
    battle = getattr(game, "wolf_battle", None) or {}
    wolf_hp = battle.get("wolf_hp", enemy["max_hp"])
    wolf_max_hp = battle.get("wolf_max_hp", enemy["max_hp"])
    title = enemy.get("title", "🐺 БОЙ")
    enemy_name = enemy.get("name", "Враг")
    last_log = battle.get("last_log", enemy.get("start_log", ""))
    return (
        f"{title}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"❤️ Твоё здоровье: {game.hp}/100 HP\n"
        f"🐺 {enemy_name}: {wolf_hp}/{wolf_max_hp} HP\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"{last_log}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Выбери действие:"
    )


def start_battle(game, enemy_id: str = "old_wolf") -> Tuple[str, InlineKeyboardMarkup]:
    """Инициализация боя с врагом."""
    enemy = get_enemy(enemy_id)
    game.story_state = "wolf_battle"
    if hasattr(game, "push_screen"):
        game.push_screen("wolf_battle")
    game.wolf_battle = {
        "enemy_id": enemy_id,
        "wolf_hp": enemy["max_hp"],
        "wolf_max_hp": enemy["max_hp"],
        "player_dmg_dealt": 0,
        "wolf_dmg_dealt": 0,
        "last_log": enemy.get("start_log", ""),
    }
    text = get_battle_text(game, enemy_id)
    kb = get_wolf_battle_kb()
    return text, kb


def apply_action(action: str, game, enemy_id: str = "old_wolf") -> Tuple[str, InlineKeyboardMarkup]:
    """Обрабатывает действие игрока в бою (атака / защита / побег)."""
    enemy = get_enemy(enemy_id)
    battle = getattr(game, "wolf_battle", None)
    if not battle:
        start_battle(game, enemy_id)
        battle = game.wolf_battle

    # Нормализуем имя действия
    clean_action = action
    if clean_action.startswith("wolf_battle_"):
        clean_action = clean_action.removeprefix("wolf_battle_")

    has_torch = (
        game.equipment.get("hand_left") == "Факел"
        or game.equipment.get("hand") == "Факел"
        or game.equipment.get("hand_right") == "Факел"
    )

    if clean_action == "attack":
        p_dmg = random.randint(4, 6)
        torch_burn = 1 if has_torch else 0
        total_p_dmg = p_dmg + torch_burn

        battle["wolf_hp"] = max(0, battle["wolf_hp"] - total_p_dmg)
        battle["player_dmg_dealt"] += total_p_dmg

        log_lines = [f"💥 Ты бьёшь посохом: −{p_dmg} HP."]
        if torch_burn:
            log_lines.append("🔥 Огонь факела обжигает зверя: −1 HP.")

        # Проверка победы игрока
        if battle["wolf_hp"] <= 0:
            text = (
                "⚔️ ПОБЕДА!\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"• Нанесено тобой: {battle['player_dmg_dealt']} ед.\n"
                f"• Нанёс волк: {battle['wolf_dmg_dealt']} ед.\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "Зверь повержен и больше не может нападать."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➡️ Продолжить", callback_data=enemy.get("victory_callback", "l1_5_aftermath"))]
            ])
            return text, kb

        # Ответная атака врага
        scared = has_torch and (random.random() < 0.35)
        if scared:
            log_lines.append("🐺 Волк шарахается от пламени факела и промахивается!")
        else:
            w_dmg = random.randint(enemy.get("attack_min", 5), enemy.get("attack_max", 7))
            game.hp = max(1, game.hp - w_dmg)
            battle["wolf_dmg_dealt"] += w_dmg
            log_lines.append(f"🐺 Волк щёлкает клыками и полосует тебя: −{w_dmg} HP.")

        battle["last_log"] = "\n".join(log_lines)
        text = get_battle_text(game, enemy_id)
        kb = get_wolf_battle_kb()
        return text, kb

    elif clean_action == "defend":
        torch_burn = 1 if has_torch else 0
        if torch_burn:
            battle["wolf_hp"] = max(0, battle["wolf_hp"] - torch_burn)
            battle["player_dmg_dealt"] += torch_burn
            log_lines = ["🛡️ Ты закрываешься посохом. Пламя факела опаляет зверя: −1 HP."]
        else:
            log_lines = ["🛡️ Ты уходишь в глухую защиту, выставив перед собой посох."]

        # Проверка победы игрока (если волк сгорел от факела на защите)
        if battle["wolf_hp"] <= 0:
            text = (
                "⚔️ ПОБЕДА!\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                f"• Нанесено тобой: {battle['player_dmg_dealt']} ед.\n"
                f"• Нанёс волк: {battle['wolf_dmg_dealt']} ед.\n"
                "━━━━━━━━━━━━━━━━━━━\n"
                "Зверь повержен и больше не может нападать."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➡️ Продолжить", callback_data=enemy.get("victory_callback", "l1_5_aftermath"))]
            ])
            return text, kb

        # Ответная атака врага по защите (сниженный урон)
        scared = has_torch and (random.random() < 0.35)
        if scared:
            log_lines.append("🐺 Волк пугается огня и пятится назад: урон 0 HP.")
        else:
            w_dmg = random.randint(enemy.get("defended_min", 2), enemy.get("defended_max", 4))
            game.hp = max(1, game.hp - w_dmg)
            battle["wolf_dmg_dealt"] += w_dmg
            log_lines.append(f"🐺 Волк бьёт по защите, скользнув клыками: −{w_dmg} HP (снижено на 50%).")

        battle["last_log"] = "\n".join(log_lines)
        text = get_battle_text(game, enemy_id)
        kb = get_wolf_battle_kb()
        return text, kb

    elif clean_action == "flee":
        game.wolf_battle = None
        game.story_state = None
        game.nav_stack = ["main", "locations"]
        text = enemy.get("flee_text", (
            "Ты резко отшатываешься назад, выставив посох перед собой, и сломя голову выбегаешь из пещеры обратно в овраг. "
            "За спиной раздаётся яростный, но бессильный хрип зверя."
        ))
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ В меню локаций", callback_data=enemy.get("flee_callback", "locations_menu"))]
        ])
        return text, kb

    # Фоллбэк
    return get_battle_text(game, enemy_id), get_wolf_battle_kb()
