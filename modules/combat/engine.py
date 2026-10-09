"""
engine.py — Движок пошагового боя для боссов и опасных противников.
Поддерживает Старого волка (L1.5) и Секача солонца (L3).
"""
from typing import Tuple
import random
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.combat.enemies import get_enemy
from modules.items import ITEMS
from keyboards import get_wolf_battle_kb, get_boar_battle_kb, get_slime_battle_kb


def _calc_player_damage(game) -> int:
    """Расчёт урона игрока с учётом оружия и аксессуаров."""
    eq = getattr(game, "equipment", {}) or {}
    # Проверяем оружие в правой руке
    weapon = eq.get("hand_right")
    base_dmg = 5
    if weapon in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё"):
        base_dmg = random.randint(19, 24)
    elif weapon == "Окованный посох":
        base_dmg = random.randint(9, 11)
    elif weapon == "Крепкий посох":
        effects = ITEMS[weapon]["effects"]
        base_dmg = random.randint(effects["damage_min"], effects["damage_max"])
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
    if enemy_id in ("giant_slime", "trash_slime"):
        phase = battle.get("phase", "1")
        core_side = battle.get("core_side", "right")
        pocket_item = None
        if game.equipment.get("pants") == "Кожаные поножи":
            pocket_item = getattr(game, "pants_pocket", None)
        return get_slime_battle_kb(phase=phase, core_side=core_side, pocket_item=pocket_item)
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
    elif enemy_id == "giant_slime":
        phase = battle.get("phase", "1")
        phase_names = {
            "1": "Отвод ядра",
            "2A": "Ядро на прицеле",
            "3A": "Кислотный фонтан",
            "4A": "Ступор твари",
            "5A": "Восстановление формы",
            "2B": "Потеря цели",
            "3B": "Тяжёлый навал",
            "4B": "Вязкая пауза",
            "5B": "Сбор массы",
        }
        phase_name = phase_names.get(phase, "Сражение")
        if phase == "4A":
            st = battle.get("stun_turns", 1)
            status_text = f"💫 Ступор твари (шока осталось: {st})"
        else:
            status_text = f"📍 Фаза: {phase_name}"
        status_line = f"{status_text}\n"

    enemy_icon = "🐗" if enemy_id == "ancient_boar" else ("🕳️" if enemy_id == "trash_slime" else ("☣️" if enemy_id == "giant_slime" else "🐺"))
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
            "is_lunging": False,
            "is_flattened": False,
            "is_stunned": False,
            "is_enraged": False,
            "boar_status": "⚡ Мчится на таран!" if is_charging else "",
            "last_log": start_log,
        }
    elif enemy_id == "giant_slime":
        side = random.choice(["right", "left"])
        side_txt = "ВПРАВО" if side == "right" else "ВЛЕВО"
        start_log = f"Слайм колышется, ядро смещается {side_txt}."
        game.wolf_battle = {
            "enemy_id": enemy_id,
            "wolf_hp": 555,
            "wolf_max_hp": 555,
            "player_dmg_dealt": 0,
            "wolf_dmg_dealt": 0,
            "turn_count": 0,
            "dodge_count": 0,
            "phase": "1",
            "core_side": side,
            "stun_turns": 0,
            "last_log": start_log,
        }
    else:
        game.wolf_battle = {
            "enemy_id": enemy_id,
            "wolf_hp": wolf_hp,
            "wolf_max_hp": enemy["max_hp"],
            "player_dmg_dealt": player_dmg,
            "wolf_dmg_dealt": wolf_dmg,
            "turn_count": 0,
            "dodge_count": 0,
            "phase": 1,
            "is_charging": False,
            "is_lunging": False,
            "is_flattened": False,
            "is_stunned": False,
            "is_enraged": False,
            "boar_status": "",
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
    for prefix in ("wolf_battle_", "boar_battle_", "slime_battle_", "trash_battle_"):
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
            if game.hp <= 0:
                game.hp = 0
                game.wolf_battle = None
                game.story_state = None
                game.active_story_callback = None
                from keyboards import get_death_kb
                from game_state import get_death_text
                text = get_death_text(game, f"🐗 Секач насмерть сбил тебя внезапным тараном (−{ram_dmg} HP).", "Солонец (Секач)")
                return text, get_death_kb()
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
    # БОЙ С ИСПОЛИНСКИМ СЛАЙМОМ (Локация 5: Заводь Исполина)
    # =========================================================================
    # =========================================================================
    # БОЙ СО СЛАЙМАМИ (Локация 5: Исполинский слайм и Мусорный слайм)
    # =========================================================================
    if enemy_id in ("giant_slime", "trash_slime"):
        if clean_action == "flee":
            game.ap = 0
            game.wolf_battle = None
            flee_state = "l5_ancient_escape" if enemy_id == "trash_slime" else "l5_arena_escape"
            game.story_state = flee_state
            game.active_story_callback = None
            from story.location_stories import handle_location_5_slug_pit
            return handle_location_5_slug_pit(flee_state, game, getattr(game, "user_id", None))

        cur_phase = str(battle.get("phase", "1"))
        core_side = battle.get("core_side", "right")
        battle["turn_count"] = battle.get("turn_count", 0) + 1
        log_lines = []

        def _check_victory():
            if battle["wolf_hp"] <= 0:
                battle["wolf_hp"] = 0
                vic_cb = enemy.get("victory_callback", "l5_2_7")
                game.active_story_callback = vic_cb
                game.story_state = vic_cb
                boss_label = "МУСОРНЫМ СЛАЙМОМ" if enemy_id == "trash_slime" else "ИСПОЛИНОМ"
                text = (
                    f"⚔️ ПОБЕДА НАД {boss_label}!\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    f"• Нанесено тобой: {battle['player_dmg_dealt']} ед.\n"
                    f"• Нанёс слайм: {battle['wolf_dmg_dealt']} ед.\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "Точный удар сокрушил ядро твари, разбрызгивая едкую пену."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💥 Нанести добивающий удар ➔", callback_data=vic_cb)]
                ])
                return text, kb
            return None

        def _check_death(reason: str):
            if game.hp <= 0:
                game.hp = 0
                game.wolf_battle = None
                game.active_story_callback = None
                from keyboards import get_death_kb
                from game_state import get_death_text
                return get_death_text(game, reason, "Заводь Исполина"), get_death_kb()
            return None

        def _use_pocket_item():
            p_item = getattr(game, "pants_pocket", None)
            if not p_item:
                return "В кармане поножей ничего нет."
            from modules.items import ITEMS
            if p_item == "Янтарное зелье":
                heal_amt = min(game.max_hp - game.hp, 70)
                game.hp += heal_amt
                game.inventory["Пузырёк"] = game.inventory.get("Пузырёк", 0) + 1
                msg = f"🧪 Ты принимаешь Янтарное зелье! (+{heal_amt} HP). Пустой пузырёк убран в рюкзак."
            else:
                eff = ITEMS.get(p_item, {}).get("effects", {})
                hp_gain = eff.get("hp", 20)
                heal_amt = min(game.max_hp - game.hp, hp_gain)
                game.hp += heal_amt
                msg = f"🍽️ Ты принимаешь {p_item} из кармана! (+{heal_amt} HP)."
            game.pants_pocket = None
            return msg

        # --- ФАЗА 1: Отвод ядра ---
        if cur_phase == "1":
            if clean_action in ("step_left", "step_right"):
                is_correct = (clean_action == "step_right" and core_side == "right") or (clean_action == "step_left" and core_side == "left")
                if is_correct:
                    battle["phase"] = "2A"
                    log_lines.append("⚡ Ты делаешь точный шаг в сторону открытого ядра! Тонкая плёнка натянута — ядро беззащитно!\nЯдро натягивает оболочку! Самое время бить!")
                else:
                    battle["phase"] = "2B"
                    log_lines.append("⚠️ Ты шагнул не в ту сторону! Тварь повернулась тушей оленя, плотная масса надёжно закрыла ядро!\nОшибся с направлением, ядро скрыто! Слайм вздымается!")
            elif clean_action == "attack":
                p_dmg = random.randint(5, 8)
                battle["wolf_hp"] = max(0, battle["wolf_hp"] - p_dmg)
                battle["player_dmg_dealt"] += p_dmg
                v = _check_victory()
                if v:
                    return v
                battle["phase"] = "2B"
                log_lines.append(f"⚔️ Удар в лоб вязнет в плотной массе слизи (−{p_dmg} HP), ядро заслонено!\nОшибся с направлением, ядро скрыто! Слайм вздымается!")
            elif clean_action == "defend":
                battle["phase"] = "2B"
                log_lines.append("🛡 Ты уходишь в защиту, теряя ядро из вида! Тварь перегруппировывается.\nОшибся с направлением, ядро скрыто! Слайм вздымается!")
            elif clean_action == "pocket":
                log_lines.append(_use_pocket_item())

        # --- ФАЗА 2А: Ядро на прицеле ---
        elif cur_phase == "2A":
            if clean_action in ("attack", "crit"):
                p_dmg = random.randint(35, 40)
                battle["wolf_hp"] = max(0, battle["wolf_hp"] - p_dmg)
                battle["player_dmg_dealt"] += p_dmg
                v = _check_victory()
                if v:
                    return v
                battle["phase"] = "3A"
                log_lines.append(f"💥 Точный выпад прямо в обнажённое ядро: −{p_dmg} HP!\nИз раны хлещет пена с брызгами во все стороны!")
            elif clean_action == "defend":
                battle["phase"] = "1"
                side = random.choice(["right", "left"])
                battle["core_side"] = side
                side_txt = "ВПРАВО" if side == "right" else "ВЛЕВО"
                log_lines.append(f"🛡 Ты закрываешься и упускаешь момент! Тварь оправилась.\nСлайм колышется, ядро смещается {side_txt}.")
            elif clean_action == "pocket":
                log_lines.append(_use_pocket_item())

        # --- ФАЗА 3А: Кислотный фонтан ---
        elif cur_phase == "3A":
            if clean_action in ("dodge_left", "dodge_right"):
                battle["phase"] = "4A"
                battle["stun_turns"] = random.randint(1, 3)
                log_lines.append("⚡ Ты ловко уходишь от фонтана кислоты в сторону (0 урона)!\nУ твари шок! Кипящие капли хлещут, тварь парализована!")
            elif clean_action == "attack":
                taken = 50
                game.hp = max(0, game.hp - taken)
                battle["wolf_dmg_dealt"] += taken
                d = _check_death("☣️ Едкая струя кислоты сожгла тебя при попытке безрассудной атаки (−50 HP).")
                if d:
                    return d
                battle["phase"] = "4A"
                battle["stun_turns"] = random.randint(1, 3)
                log_lines.append(f"💥 Жадная атака дорого обошлась: струя кислоты накрывает тебя с ног до головы (−{taken} HP)!\nУ твари шок! Кипящие капли хлещут, тварь парализована!")
            elif clean_action == "defend":
                taken = 25
                game.hp = max(0, game.hp - taken)
                battle["wolf_dmg_dealt"] += taken
                d = _check_death("☣️ Кислотные брызги прожгли твою защиту (−25 HP).")
                if d:
                    return d
                battle["phase"] = "4A"
                battle["stun_turns"] = random.randint(1, 3)
                log_lines.append(f"🛡 Брызги кислоты заливают блок: −{taken} HP!\nУ твари шок! Кипящие капли хлещут, тварь парализована!")
            elif clean_action == "pocket":
                log_lines.append(_use_pocket_item())

        # --- ФАЗА 4А: Ступор твари ---
        elif cur_phase == "4A":
            if clean_action == "attack":
                p_dmg = 12
                battle["wolf_hp"] = max(0, battle["wolf_hp"] - p_dmg)
                battle["player_dmg_dealt"] += p_dmg
                v = _check_victory()
                if v:
                    return v
                battle["stun_turns"] = battle.get("stun_turns", 1) - 1
                if battle["stun_turns"] > 0:
                    log_lines.append(f"⚔️ Удар по краю туши: −{p_dmg} HP! Тварь всё ещё бьётся в конвульсиях (осталось ходов: {battle['stun_turns']}).")
                else:
                    battle["phase"] = "5A"
                    log_lines.append(f"⚔️ Удар по краю туши: −{p_dmg} HP!\nРеакция угасла. Слайм судорожно собирает желе.")
            elif clean_action == "pocket":
                p_msg = _use_pocket_item()
                battle["stun_turns"] = battle.get("stun_turns", 1) - 1
                if battle["stun_turns"] > 0:
                    log_lines.append(f"{p_msg}\nТварь всё ещё в шоке (осталось ходов: {battle['stun_turns']}).")
                else:
                    battle["phase"] = "5A"
                    log_lines.append(f"{p_msg}\nРеакция угасла. Слайм судорожно собирает желе.")
            elif clean_action == "defend":
                battle["stun_turns"] = battle.get("stun_turns", 1) - 1
                if battle["stun_turns"] > 0:
                    log_lines.append(f"🛡 Ты восстанавливаешь силы, выжидая момент (осталось ходов: {battle['stun_turns']}).")
                else:
                    battle["phase"] = "5A"
                    log_lines.append("🛡 Ты восстанавливаешь силы.\nРеакция угасла. Слайм судорожно собирает желе.")

        # --- ФАЗА 5А: Восстановление формы ---
        elif cur_phase == "5A":
            if clean_action == "watch":
                battle["phase"] = "1"
                side = random.choice(["right", "left"])
                battle["core_side"] = side
                side_txt = "ВПРАВО" if side == "right" else "ВЛЕВО"
                log_lines.append(f"👁️ Ты следишь за ядром и не теряешь позицию!\nСлайм колышется, ядро смещается {side_txt}.")
            elif clean_action == "attack":
                battle["phase"] = "3B"
                log_lines.append("⚔️ Слепой удар вязнет в стягивающейся массе! Тварь резко вздымается!\nДвухметровая масса накатывает высокой волной!")
            elif clean_action == "defend":
                battle["phase"] = "3B"
                log_lines.append("🛡 Ты застываешь в обороне, отдавая инициативу! Слайм вздымается над тобой!\nДвухметровая масса накатывает высокой волной!")
            elif clean_action == "pocket":
                log_lines.append(_use_pocket_item())

        # --- ФАЗА 2Б: Потеря цели ---
        elif cur_phase == "2B":
            if clean_action == "prepare":
                battle["phase"] = "3B"
                log_lines.append("⚠️ Ты группируешься перед ударом!\nДвухметровая масса накатывает высокой волной!")
            elif clean_action == "pocket":
                log_lines.append(_use_pocket_item())

        # --- ФАЗА 3Б: Тяжёлый навал ---
        elif cur_phase == "3B":
            if clean_action == "dodge_back":
                battle["phase"] = "4B"
                log_lines.append("⚡ Ты вовремя отпрыгиваешь назад (0 урона)! Волна слизи с грохотом шлёпается о камни!\nТварь распласталась. Кругом шипящие лужи кислоты!")
            elif clean_action == "attack":
                taken = 50
                game.hp = max(0, game.hp - taken)
                battle["wolf_dmg_dealt"] += taken
                d = _check_death("☣️ Тяжёлая волна слизи раздавила тебя при лобовой атаке (−50 HP).")
                if d:
                    return d
                battle["phase"] = "4B"
                log_lines.append(f"💥 Волна массы сбивает тебя с ног и накрывает с головой: −{taken} HP!\nТварь распласталась. Кругом шипящие лужи кислоты!")
            elif clean_action == "defend":
                taken = 25
                game.hp = max(0, game.hp - taken)
                battle["wolf_dmg_dealt"] += taken
                d = _check_death("☣️ Масса слизи расплющила твою защиту (−25 HP).")
                if d:
                    return d
                battle["phase"] = "4B"
                log_lines.append(f"🛡 Ты пытаешься блокировать всей массой посоха, но тебя придавливает тяжестью: −{taken} HP!\nТварь распласталась. Кругом шипящие лужи кислоты!")
            elif clean_action == "pocket":
                log_lines.append(_use_pocket_item())

        # --- ФАЗА 4Б: Вязкая пауза ---
        elif cur_phase == "4B":
            if clean_action == "attack":
                p_dmg = 8
                battle["wolf_hp"] = max(0, battle["wolf_hp"] - p_dmg)
                battle["player_dmg_dealt"] += p_dmg
                v = _check_victory()
                if v:
                    return v
                battle["phase"] = "5B"
                log_lines.append(f"⚔️ Тычок посохом по растекшейся жиже: −{p_dmg} HP.\nСлайм стягивает жижу в кучу. Кругом кислотные лужи!")
            elif clean_action == "defend":
                battle["phase"] = "5B"
                log_lines.append("🛡 Ты держишь дистанцию, не рискуя наступать в кислоту.\nСлайм стягивает жижу в кучу. Кругом кислотные лужи!")
            elif clean_action == "pocket":
                log_lines.append(_use_pocket_item())

        # --- ФАЗА 5Б: Сбор массы ---
        elif cur_phase == "5B":
            if clean_action in ("watch", "defend"):
                battle["phase"] = "1"
                side = random.choice(["right", "left"])
                battle["core_side"] = side
                side_txt = "ВПРАВО" if side == "right" else "ВЛЕВО"
                act_desc = "Ты внимательно следишь за перетеканием массы" if clean_action == "watch" else "Ты выжидаешь за блоком"
                log_lines.append(f"👁️ {act_desc}!\nСлайм колышется, ядро смещается {side_txt}.")
            elif clean_action == "attack":
                battle["phase"] = "3B"
                log_lines.append("⚔️ Несвоевременная атака срывает позицию! Слайм резко вздымается!\nДвухметровая масса накатывает высокой волной!")
            elif clean_action == "pocket":
                log_lines.append(_use_pocket_item())

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
