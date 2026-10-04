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
    # Проверяем оружие в правой руке
    weapon = eq.get("hand_right")
    base_dmg = 5
    if weapon == "Окованный посох":
        base_dmg = random.randint(9, 11)
    elif weapon == "Крепкий посох":
        base_dmg = random.randint(5, 7)
    else:
        base_dmg = random.randint(4, 6)

    # Бонус от амулета "Клык волка"
    if eq.get("trinket") == "Клык волка":
        base_dmg += 1

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
    status_line = ""
    if enemy_id == "ancient_boar":
        cur_phase = 2 if wolf_hp <= (wolf_max_hp // 2) else 1
        phase_str = f" | 🔥 ФАЗА {cur_phase}"
        if battle.get("is_stunned"):
            status_text = "💫 Оглушён (1 ход)"
        elif battle.get("is_charging"):
            status_text = "⚡ Мчится на таран!"
        elif battle.get("is_enraged") or (cur_phase == 2 and not battle.get("is_stunned")):
            status_text = "💢 Рассвирепел"
        else:
            status_text = battle.get("boar_status", "⏳ Готовится к броску")
        status_line = f"📍 Статус зверя: {status_text}\n"

    enemy_icon = "🐗" if enemy_id == "ancient_boar" else "🐺"
    return (
        f"{title}{phase_str}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"❤️ Твоё здоровье: {game.hp}/{max_hp} HP{armor_str}\n"
        f"{enemy_icon} {enemy_name}: {wolf_hp}/{wolf_max_hp} HP\n"
        f"{status_line}"
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
    wolf_hp = enemy["max_hp"]
    player_dmg = 0
    wolf_dmg = 0
    start_log = enemy.get("start_log", "")

    if enemy_id == "ancient_boar":
        start_log = "🐗 Секач сорвался с места и на полной скорости несётся на тебя на таран!"

    game.wolf_battle = {
        "enemy_id": enemy_id,
        "wolf_hp": wolf_hp,
        "wolf_max_hp": enemy["max_hp"],
        "player_dmg_dealt": player_dmg,
        "wolf_dmg_dealt": wolf_dmg,
        "turn_count": 0,
        "dodge_count": 0,
        "phase": 1,
        "is_charging": is_charging,
        "is_stunned": False,
        "is_enraged": False,
        "boar_status": "⚡ Мчится на таран!" if is_charging else "",
        "last_log": start_log,
    }
    game.active_story_callback = enemy.get("screen_callback", "wolf_battle_screen" if enemy_id == "old_wolf" else "boar_battle_screen")
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
    screen_cb = enemy.get("screen_callback", "wolf_battle_screen" if enemy_id == "old_wolf" else "boar_battle_screen")

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

        # ПЕРВЫЙ ХОД (Стартовый таран врасплох)
        if battle.get("turn_count", 0) == 0:
            battle["turn_count"] = 1
            game.active_story_callback = screen_cb
            ram_dmg = 44
            strike_dmg = 18
            game.hp = max(0, game.hp - ram_dmg)
            battle["wolf_hp"] = max(0, battle["wolf_hp"] - strike_dmg)
            battle["player_dmg_dealt"] += strike_dmg
            battle["wolf_dmg_dealt"] += ram_dmg
            battle["is_charging"] = False
            battle["is_enraged"] = True
            battle["boar_status"] = "💢 В ярости"
            log_lines = [
                f"⚠️ Внезапный таран сбивает с ног: Секач сносит −{ram_dmg} HP (Твоё HP: {game.hp}/{getattr(game, 'max_hp', 100)})!",
                f"🦯 На встречном движении ты бьёшь посохом: −{strike_dmg} HP! Зверь разворачивается в ярости."
            ]
            battle["last_log"] = "\n".join(log_lines)
            return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)

        if clean_action in ("attack", "crit") and battle.get("is_stunned"):
            p_dmg = _calc_player_damage(game) * 2
            battle["wolf_hp"] = max(0, battle["wolf_hp"] - p_dmg)
            battle["player_dmg_dealt"] += p_dmg
            battle["is_stunned"] = False
            battle["is_charging"] = False
            battle["is_enraged"] = True
            battle["boar_status"] = "💢 В ярости"
            log_lines = [
                f"💥 Критический удар посохом: −{p_dmg} HP (Секач: {battle['wolf_hp']}/{enemy.get('max_hp', 350)} HP).",
                "🐗 Секач оправился от оглушения и в ярости готов к бою!"
            ]

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

            half_hp = enemy.get("max_hp", 350) // 2
            if battle["wolf_hp"] <= half_hp and not battle.get("phase2_announced"):
                battle["phase2_announced"] = True
                battle["phase"] = 2
                battle["is_enraged"] = True
                log_lines.append("🔥 ФАЗА 2: НЕИСТОВСТВО! Секач в ярости!")

            game.active_story_callback = screen_cb
            battle["last_log"] = "\n".join(log_lines)
            return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)

        if clean_action == "dodge":
            d_count = battle.get("dodge_count", 0) + 1
            battle["dodge_count"] = d_count
            was_charging = battle.get("is_charging", False)
            battle["is_charging"] = False

            if was_charging:
                battle["is_stunned"] = True
                battle["is_enraged"] = False
                battle["boar_status"] = "💫 Оглушён (1 ход)"
                log_lines = [
                    "⚡ Уворот успешен! Секач со всего размаха врезался в скалу (Оглушён на 1 ход)."
                ]
            else:
                log_lines = ["⚡ Ты ушёл в сторону, но Секач не шёл на таран."]

            game.active_story_callback = screen_cb
            battle["last_log"] = "\n".join(log_lines)
            return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)

        if clean_action in ("attack", "crit"):
            p_dmg = _calc_player_damage(game)
            battle["wolf_hp"] = max(0, battle["wolf_hp"] - p_dmg)
            battle["player_dmg_dealt"] += p_dmg
            log_lines = [f"🦯 Удар посохом: −{p_dmg} HP (Секач: {battle['wolf_hp']}/{enemy.get('max_hp', 350)} HP)."]

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

            was_charging = battle.get("is_charging", False)
            if was_charging:
                # Игрок не нажал уворот, а ударил в лоб: Секач сносит тараном
                ram_dmg = max(10, 50 - armor_def)
                game.hp = max(0, game.hp - ram_dmg)
                battle["wolf_dmg_dealt"] += ram_dmg
                battle["is_charging"] = False
                battle["is_enraged"] = True
                battle["boar_status"] = "💢 В ярости"
                log_lines.append(f"🐗 Секач сносит тебя встречным тараном: −{ram_dmg} HP! Зверь разворачивается в ярости.")

                if game.hp <= 0:
                    game.hp = 0
                    game.wolf_battle = None
                    from keyboards import get_death_kb
                    from game_state import get_death_text
                    text = get_death_text(game, f"🐗 Секач растоптал тебя встречным тараном (−{ram_dmg} HP).", "Солонец (Секач)")
                    return text, get_death_kb()
            else:
                # 15% шанс оглушения от Окованного посоха
                stun_proc = False
                weapon = (getattr(game, "equipment", {}) or {}).get("hand_right")
                if weapon:
                    from modules.items import ITEMS
                    eff = ITEMS.get(weapon, {}).get("effects", {})
                    s_chance = eff.get("stun_chance", 0)
                    if s_chance > 0 and random.randint(1, 100) <= s_chance:
                        stun_proc = True

                if stun_proc:
                    battle["is_stunned"] = True
                    battle["is_charging"] = False
                    battle["is_enraged"] = False
                    battle["boar_status"] = "💫 Оглушён (1 ход)"
                    log_lines.append("💫 Сокрушительный удар посохом оглушил зверя на 1 ход!")
                else:
                    b_dmg = max(6, 26 - armor_def)
                    game.hp = max(0, game.hp - b_dmg)
                    battle["wolf_dmg_dealt"] += b_dmg

                    if battle.get("boar_status") == "💢 В ярости":
                        battle["is_enraged"] = False
                        battle["is_charging"] = False
                        battle["boar_status"] = "⏳ Разгоняется"
                        log_lines.append(f"🐗 Секач в ярости бьёт клыками: −{b_dmg} HP и начинает разбег!")
                    else:
                        battle["is_enraged"] = False
                        battle["is_charging"] = True
                        battle["boar_status"] = "⚡ Мчится на таран!"
                        log_lines.append(f"🐗 Секач наносит выпад клыками: −{b_dmg} HP, набрал скорость и мчится на таран!")

                    if game.hp <= 0:
                        game.hp = 0
                        game.wolf_battle = None
                        from keyboards import get_death_kb
                        from game_state import get_death_text
                        text = get_death_text(game, f"🐗 Секач распорол клыками в ближнем бою (−{b_dmg} HP).", "Солонец (Секач)")
                        return text, get_death_kb()

            half_hp = enemy.get("max_hp", 350) // 2
            if battle["wolf_hp"] <= half_hp and not battle.get("phase2_announced"):
                battle["phase2_announced"] = True
                battle["phase"] = 2
                battle["is_enraged"] = True
                log_lines.append("🔥 ФАЗА 2: НЕИСТОВСТВО! Секач в ярости!")

            game.active_story_callback = screen_cb
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
                text = get_death_text(game, f"🐗 Секач пробил твою защиту смертельным ударом (−{taken} HP).", "Солонец (Секач)")
                return text, get_death_kb()

            game.active_story_callback = screen_cb
            battle["last_log"] = "\n".join(log_lines)
            return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)

    # =========================================================================
    # СТАНДАРТНАЯ ЛОГИКА ДЛЯ СТАРОГО ВОЛКА (Локация 1.5)
    # =========================================================================
    has_torch = (
        game.equipment.get("hand_left") == "Факел"
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
                text = get_death_text(game, f"🐺 Старый волк нанёс смертельный удар (−{w_dmg} HP).", "Волчье логово")
                kb = get_death_kb()
                return text, kb

        game.active_story_callback = screen_cb
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
                text = get_death_text(game, f"🐺 Волк пробил твою защиту смертельным ударом (−{w_dmg} HP).", "Волчье логово")
                kb = get_death_kb()
                return text, kb

        game.active_story_callback = screen_cb
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
    game.active_story_callback = screen_cb
    return get_battle_text(game, enemy_id), get_battle_kb(game, enemy_id)
