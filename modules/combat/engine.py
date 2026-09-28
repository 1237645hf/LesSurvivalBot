"""
engine.py — Движок пошагового боя для боссов и опасных противников.
Поддерживает Старого волка (L1.5) и Секача солонца (L3).
"""
from typing import Tuple
import random
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.combat.enemies import get_enemy
from keyboards import get_wolf_battle_kb, get_boar_battle_kb


def _calc_player_damage(game) -> int:
    """Расчёт урона игрока с учётом оружия и аксессуаров."""
    eq = getattr(game, "equipment", {}) or {}
    # Проверяем оружие в руках
    weapon = eq.get("hand_right") or eq.get("hand") or eq.get("hands") or eq.get("hand_left")
    base_dmg = 5
    if weapon == "Окованный посох":
        base_dmg = random.randint(9, 11)
    elif weapon == "Крепкий посох":
        base_dmg = random.randint(5, 7)
    else:
        base_dmg = random.randint(4, 6)

    # Бонус от амулета "Клык волка"
    if eq.get("trinket") == "Клык волка":
        base_dmg += 3

    return base_dmg


def get_battle_kb(game, enemy_id: str = "old_wolf") -> InlineKeyboardMarkup:
    """Универсальное получение клавиатуры для текущего противника."""
    battle = getattr(game, "wolf_battle", None) or {}
    enemy_id = battle.get("enemy_id", enemy_id)
    if enemy_id == "ancient_boar":
        return get_boar_battle_kb(
            is_stunned=battle.get("is_stunned", False),
            is_charging=battle.get("is_charging", False),
        )
    return get_wolf_battle_kb()


def get_battle_text(game, enemy_id: str = "old_wolf") -> str:
    """Формирует экран текущего состояния боя."""
    battle = getattr(game, "wolf_battle", None) or {}
    enemy_id = battle.get("enemy_id", enemy_id)
    enemy = get_enemy(enemy_id)
    wolf_hp = battle.get("wolf_hp", enemy["max_hp"])
    wolf_max_hp = battle.get("wolf_max_hp", enemy["max_hp"])
    title = enemy.get("title", "⚔️ БОЙ")
    enemy_name = enemy.get("name", "Враг")
    last_log = battle.get("last_log", enemy.get("start_log", ""))
    max_hp = getattr(game, "max_hp", 100)
    armor_def = getattr(game, "armor_defense", 0)
    armor_str = f" (🛡 Защита: {armor_def})" if armor_def > 0 else ""

    phase_str = ""
    if enemy_id == "ancient_boar":
        cur_phase = 2 if wolf_hp <= 90 else 1
        phase_str = f" | 🔥 ФАЗА {cur_phase}"

    return (
        f"{title}{phase_str}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"❤️ Твоё здоровье: {game.hp}/{max_hp} HP{armor_str}\n"
        f"🐗 {enemy_name}: {wolf_hp}/{wolf_max_hp} HP\n"
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

    is_charging = (enemy_id == "ancient_boar")
    game.wolf_battle = {
        "enemy_id": enemy_id,
        "wolf_hp": enemy["max_hp"],
        "wolf_max_hp": enemy["max_hp"],
        "player_dmg_dealt": 0,
        "wolf_dmg_dealt": 0,
        "turn_count": 0,
        "dodge_count": 0,
        "phase": 1,
        "is_charging": is_charging,
        "is_stunned": False,
        "last_log": enemy.get("start_log", ""),
    }
    game.active_story_callback = "wolf_battle_screen" if enemy_id == "old_wolf" else "boar_battle_screen"
    text = get_battle_text(game, enemy_id)
    kb = get_battle_kb(game, enemy_id)
    return text, kb


def apply_action(action: str, game, enemy_id: str = "old_wolf") -> Tuple[str, InlineKeyboardMarkup]:
    """Обрабатывает действие игрока в бою (атака / защита / побег)."""
    battle = getattr(game, "wolf_battle", None)
    if not battle:
        start_battle(game, enemy_id)
        battle = game.wolf_battle
    enemy_id = battle.get("enemy_id", enemy_id)
    enemy = get_enemy(enemy_id)

    # Нормализуем имя действия
    clean_action = action
    for prefix in ("wolf_battle_", "boar_battle_"):
        if clean_action.startswith(prefix):
            clean_action = clean_action.removeprefix(prefix)
            break

    # =========================================================================
    # БОЙ С СЕКАЧОМ (Локация 3: Двухфазный бой)
    # =========================================================================
    if enemy_id == "ancient_boar":
        armor_def = getattr(game, "armor_defense", 0)

        if clean_action == "flee":
            game.wolf_battle = None
            game.story_state = None
            game.active_story_callback = None
            game.nav_stack = ["main"]
            text = "Ты отступаешь обратно в лагерь в Лощине."
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏕 В лагерь", callback_data="l3_6_finalize")]
            ])
            return text, kb

        if clean_action == "crit":
            p_dmg = _calc_player_damage(game) * 2
            battle["wolf_hp"] = max(0, battle["wolf_hp"] - p_dmg)
            battle["player_dmg_dealt"] += p_dmg
            battle["is_stunned"] = False
            battle["is_charging"] = False
            log_lines = [f"💥 Крит (×2): −{p_dmg} HP (Секач: {battle['wolf_hp']}/{enemy.get('max_hp', 180)} HP)."]

            if battle["wolf_hp"] <= 0:
                vic_cb = enemy.get("victory_callback", "l3_11a_win")
                game.active_story_callback = vic_cb
                text = (
                    "⚔️ ПОБЕДА!\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    f"• Нанесено тобой: {battle['player_dmg_dealt']} ед.\n"
                    f"• Нанёс Секач: {battle['wolf_dmg_dealt']} ед.\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "Громадный секач рухнул на плиты солонца и затих."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Далее ➔", callback_data=vic_cb)]
                ])
                return text, kb

            if battle["wolf_hp"] <= 90 and not battle.get("phase2_announced"):
                battle["phase2_announced"] = True
                battle["phase"] = 2
                log_lines.append("🔥 ФАЗА 2: НЕИСТОВСТВО! Секач в ярости!")

            log_lines.append("🐗 Секач оправился от оглушения.")
            game.active_story_callback = "boar_battle_screen"
            battle["last_log"] = "\n".join(log_lines)
            return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)

        if clean_action == "block":
            charge_raw = 55 if battle.get("phase") == 2 else 50
            rem = max(0, charge_raw - armor_def)
            block_cut = rem // 2
            taken = max(6, rem - block_cut)
            game.hp = max(0, game.hp - taken)
            battle["wolf_dmg_dealt"] += taken
            battle["is_charging"] = False
            log_lines = [
                f"🛡️ ТАРАН СЕКАЧА! Лобовой удар на {charge_raw} урона! "
                f"Броня погасила {armor_def}. Блок панцирем погасил {block_cut}. Ты устоял! Получено: −{taken} HP."
            ]

            if game.hp <= 0:
                game.hp = 0
                game.wolf_battle = None
                from keyboards import get_death_kb
                from game_state import get_death_text
                text = get_death_text(game, f"🐗 Секач сокрушил твой панцирь тараном (−{taken} HP).")
                return text, get_death_kb()

            game.active_story_callback = "boar_battle_screen"
            battle["last_log"] = "\n".join(log_lines)
            return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)

        if clean_action == "dodge":
            d_count = battle.get("dodge_count", 0) + 1
            battle["dodge_count"] = d_count
            battle["is_charging"] = False
            battle["is_stunned"] = False

            # Логика уворота: 1-й и 4-й — провал, 2-й, 3-й, 5-й и далее — успех (стан кабана)
            if d_count in (1, 4):
                taken = 53 if d_count == 1 else max(10, 50 - armor_def)
                game.hp = max(0, game.hp - taken)
                battle["wolf_dmg_dealt"] += taken
                log_lines = [
                    f"⚠️ Уворот провален! Секач таранит: −{taken} HP (Твоё HP: {game.hp}/{getattr(game, 'max_hp', 100)})."
                ]
                if game.hp <= 0:
                    game.hp = 0
                    game.wolf_battle = None
                    from keyboards import get_death_kb
                    from game_state import get_death_text
                    text = get_death_text(game, f"🐗 Секач сокрушил тебя встречным тараном (−{taken} HP).")
                    return text, get_death_kb()
            else:
                battle["is_stunned"] = True
                log_lines = [
                    "⚡ Уворот успешен! Секач врезался в стену (Оглушён на 1 ход)."
                ]

            game.active_story_callback = "boar_battle_screen"
            battle["last_log"] = "\n".join(log_lines)
            return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)

        if clean_action == "attack":
            p_dmg = _calc_player_damage(game)
            battle["wolf_hp"] = max(0, battle["wolf_hp"] - p_dmg)
            battle["player_dmg_dealt"] += p_dmg
            log_lines = [f"🦯 Удар посохом: −{p_dmg} HP (Секач: {battle['wolf_hp']}/{enemy.get('max_hp', 180)} HP)."]

            if battle["wolf_hp"] <= 0:
                vic_cb = enemy.get("victory_callback", "l3_11a_win")
                game.active_story_callback = vic_cb
                text = (
                    "⚔️ ПОБЕДА!\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    f"• Нанесено тобой: {battle['player_dmg_dealt']} ед.\n"
                    f"• Нанёс Секач: {battle['wolf_dmg_dealt']} ед.\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "Громадный секач рухнул на плиты солонца и затих."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Далее ➔", callback_data=vic_cb)]
                ])
                return text, kb

            if battle["wolf_hp"] <= 90 and not battle.get("phase2_announced"):
                battle["phase2_announced"] = True
                battle["phase"] = 2
                log_lines.append("🔥 ВТОРАЯ ФАЗА: НЕИСТОВСТВО! Секач захлёбывается яростью, его глаза налились кровью! Удары стали свирепее!")

            turn_count = battle.get("turn_count", 0) + 1
            battle["turn_count"] = turn_count

            # Во 2-й фазе таран каждый 2-й ход, в 1-й — каждый 3-й
            freq = 2 if battle.get("phase") == 2 else 3
            if turn_count % freq == 0:
                battle["is_charging"] = True
                log_lines.append("⚠️ ТАРАН! Урон: 50. Сметёт всё на пути!")
            else:
                raw_atk = random.randint(25, 29) if battle.get("phase") == 2 else random.randint(22, 26)
                taken = max(4, raw_atk - armor_def)
                game.hp = max(0, game.hp - taken)
                battle["wolf_dmg_dealt"] += taken
                log_lines.append(f"🐗 Секач атакует клыками на {raw_atk}. Броня погасила {armor_def}. Получено: −{taken} HP.")

                if game.hp <= 0:
                    game.hp = 0
                    game.wolf_battle = None
                    from keyboards import get_death_kb
                    from game_state import get_death_text
                    text = get_death_text(game, f"🐗 Секач нанёс смертельный удар клыками (−{taken} HP).")
                    return text, get_death_kb()

            game.active_story_callback = "boar_battle_screen"
            battle["last_log"] = "\n".join(log_lines)
            return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)

        if clean_action == "defend":
            if battle.get("is_charging"):
                charge_raw = 55 if battle.get("phase") == 2 else 50
                rem = max(0, charge_raw - armor_def)
                block_cut = rem // 2
                taken = max(6, rem - block_cut)
                game.hp = max(0, game.hp - taken)
                battle["wolf_dmg_dealt"] += taken
                battle["is_charging"] = False
                log_lines = [
                    f"🛡️ ТАРАН СЕКАЧА! Лобовой удар на {charge_raw} урона! "
                    f"Броня погасила {armor_def}. Блок панцирем погасил {block_cut}. Получено: −{taken} HP."
                ]
            else:
                is_phase2 = battle.get("phase") == 2
                b_atk = random.randint(14, 18) if is_phase2 else random.randint(10, 14)
                taken = max(3, (b_atk - armor_def // 2) // 2)
                game.hp = max(0, game.hp - taken)
                battle["wolf_dmg_dealt"] += taken
                log_lines = [f"🛡️ Ты встречаешь удар посохом. Секач бьёт по защите на {b_atk}. Погашено: {b_atk - taken}. Получено: −{taken} HP."]

            if battle["wolf_hp"] <= 90 and not battle.get("phase2_announced"):
                battle["phase2_announced"] = True
                battle["phase"] = 2
                log_lines.append("🔥 ВТОРАЯ ФАЗА: НЕИСТОВСТВО! Секач захлёбывается яростью, его глаза налились кровью!")

            if game.hp <= 0:
                game.hp = 0
                game.wolf_battle = None
                from keyboards import get_death_kb
                from game_state import get_death_text
                text = get_death_text(game, f"🐗 Секач пробил твою защиту смертельным ударом (−{taken} HP).")
                return text, get_death_kb()

            game.active_story_callback = "boar_battle_screen"
            battle["last_log"] = "\n".join(log_lines)
            return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)

    # =========================================================================
    # СТАНДАРТНАЯ ЛОГИКА ДЛЯ СТАРОГО ВОЛКА (Локация 1.5)
    # =========================================================================
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
            game.active_story_callback = enemy.get("victory_callback", "l1_5_aftermath")
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
            game.hp = max(0, game.hp - w_dmg)
            battle["wolf_dmg_dealt"] += w_dmg
            log_lines.append(f"🐺 Волк щёлкает клыками и полосует тебя: −{w_dmg} HP.")

            if game.hp <= 0:
                game.hp = 0
                game.active_story_callback = None
                game.wolf_battle = None
                from keyboards import get_death_kb
                from game_state import get_death_text
                text = get_death_text(game, f"🐺 Старый волк нанёс смертельный удар (−{w_dmg} HP).")
                kb = get_death_kb()
                return text, kb

        game.active_story_callback = "wolf_battle_screen"
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
            game.active_story_callback = enemy.get("victory_callback", "l1_5_aftermath")
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
            game.hp = max(0, game.hp - w_dmg)
            battle["wolf_dmg_dealt"] += w_dmg
            log_lines.append(f"🐺 Волк бьёт по защите, скользнув клыками: −{w_dmg} HP (снижено на 50%).")

            if game.hp <= 0:
                game.hp = 0
                game.active_story_callback = None
                game.wolf_battle = None
                from keyboards import get_death_kb
                from game_state import get_death_text
                text = get_death_text(game, f"🐺 Волк пробил твою защиту смертельным ударом (−{w_dmg} HP).")
                kb = get_death_kb()
                return text, kb

        game.active_story_callback = "wolf_battle_screen"
        battle["last_log"] = "\n".join(log_lines)
        text = get_battle_text(game, enemy_id)
        kb = get_wolf_battle_kb()
        return text, kb

    elif clean_action == "flee":
        game.wolf_battle = None
        game.story_state = None
        game.active_story_callback = None
        game.nav_stack = ["main", "locations"]
        text = enemy.get("flee_text", (
            "Ты резко отшатываешься назад, выставив посох перед собой, и сломя голову выбегаешь из пещеры обратно в овраг. "
            "За спиной раздаётся яростный, но бессильный хрип зверя."
        ))
        flee_cb = enemy.get("flee_callback", "locations_menu")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ В овраг", callback_data=flee_cb)]
        ])
        return text, kb

    # Фоллбэк
    return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)
