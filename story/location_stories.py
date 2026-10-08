"""
location_stories.py — Локационно-специфичные нарративные ветки.
Каждая локация имеет свой уникальный поток событий, ресурсы и опасности.
"""

import random
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import (
    get_main_kb,
    wolf_kb,
    peek_kb,
    cat_kb,
    next_kb,
    get_locations_kb,
    get_wolf_battle_kb,
    get_death_kb,
)
from game_state import get_death_text
from modules.items import is_item_consumable, get_item_rank, get_item_type, get_item_emoji
from modules.combat import (
    start_battle,
    apply_action,
    get_battle_text,
    get_battle_kb,
    get_battle_text as get_wolf_battle_text,
)
from modules.combat.engine import _calc_player_damage

from game_math import (
    process_damage,
    get_resource_multiplier,
    get_base_resource_cost,
)


# ──────────────────────────────────────────────────────────────────────────────
# ИМПОРТЫ ЛОКАЦИЙ (L1–L7)
# ──────────────────────────────────────────────────────────────────────────────

from story.locations.loc1_forest import (
    handle_location_1_forest_start,
    handle_l1_dome,
    handle_l1_wolf_lair,
)
from story.locations.loc2_stream import (
    handle_location_2_ruchey,
    L2_PUZZLE_BANK,
    get_l2_slate_armor_count,
    get_l2_thorn_damage,
)
from story.locations.loc3_hollow import handle_location_3_slate_hollow
from story.locations.loc4_hunters import (
    handle_location_4_hunters_glade,
    SLUG_ACTIONS,
    _render_slug_battle,
    _render_wolf_pack_battle,
)
from story.locations.loc5_slug_pit import (
    handle_location_5_slug_pit,
    start_slug_pack_battle,
    _render_slug_pack_battle,
    SLIME_NAMES_POOL,
)
from story.locations.loc6_furry_cave import handle_location_6_furry_cave
from story.locations.loc7_sanctuary import (
    handle_location_7_sanctuary_peak,
    resolve_ending,
    ending_text,
    ENDING_STORY_TEXT,
    ENDING_TITLES,
    THRESHOLDS,
)


def handle_story(data: str, game, uid: int):
    """Обработать сюжетную сцену волка и котёнка или передать в ветку других локаций."""
    res = None
    if data.startswith("l1_dome"):
        res = handle_l1_dome(data, game, uid)
    elif data.startswith("l2_") or data.startswith("ruchey_") or data.startswith("river_") or data.startswith("snake_") or data.startswith("story_") or data == "location_enter_2":
        if data == "location_enter_2":
            game.current_location = "Ручей со змеями"
            game.location = game.current_location
        res = handle_location_2_ruchey(data, game, uid)
    elif (
        data.startswith("l3_")
        or data.startswith("slate_")
        or data.startswith("rest_")
        or data.startswith("examine")
        or data.startswith("boar_")
        or data in ("location_enter_3", "location_enter_boar")
    ):
        if data == "location_enter_3":
            game.current_location = "Скромная лощина"
        res = handle_location_3_slate_hollow(data, game, uid)
    elif data.startswith("l4_") or data.startswith("hunters_") or data.startswith("glade_") or data == "location_enter_4":
        if data == "location_enter_4":
            unlocked = getattr(game, "unlocked_locations", []) or []
            if "Просека охотников" not in unlocked and "Просека Охотников" not in unlocked:
                unlocked.append("Просека охотников")
                unlocked.append("Просека Охотников")
                game.unlocked_locations = unlocked
            game.current_location = "Просека охотников"
            res = handle_location_4_hunters_glade("hunters_glade_start", game, uid)
        else:
            res = handle_location_4_hunters_glade(data, game, uid)
    elif data.startswith("slug_") or data.startswith("pit_") or data.startswith("l5_") or data.startswith("slime_battle") or data == "location_enter_5":
        if data == "location_enter_5":
            game.current_location = "Яр слизней"
            res = handle_location_5_slug_pit("slug_pit_start", game, uid)
        else:
            res = handle_location_5_slug_pit(data, game, uid)
    elif data.startswith("furry_") or data.startswith("warm_") or data.startswith("cave_") or data == "location_enter_6":
        if data == "location_enter_6":
            game.current_location = "Мохнатая пещера"
            res = handle_location_6_furry_cave("furry_cave_start", game, uid)
        else:
            res = handle_location_6_furry_cave(data, game, uid)
    elif data.startswith("sanctuary_") or data == "location_enter_7":
        if data == "location_enter_7":
            game.current_location = "Святилище"
            res = handle_location_7_sanctuary_peak("sanctuary_peak_start", game, uid)
        else:
            res = handle_location_7_sanctuary_peak(data, game, uid)
    elif (
        data.startswith("l1_5")
        or data.startswith("l1_6")
        or data.startswith("l1_7")
        or data.startswith("wolf_lair")
        or data.startswith("wolf_battle")
        or data in ("location_enter_1",)
    ):
        res = handle_l1_wolf_lair(data, game, uid)
    else:
        res = handle_location_1_forest_start(data, game, uid)

    if res is not None:
        text, kb = res
        if text is None:
            text = game.get_ui()
            kb = get_main_kb(game)
        return text, kb
    return None, None



def check_forest_research_story_trigger(game, loc_id: int, torch_equipped: bool) -> tuple[str | None, str | None]:
    """Проверяет сюжетные триггеры при исследовании локации 1 (Лесной старт).
    
    Алгоритм:
    - L1 (Встреча с волком у пня): при наличии факела на 4-е исследование запускается forest_start.
    - L1.5 (Волчье логово): запускается не ранее чем через 4 дня после завершения L1 (day >= l1_completed_day + 4)
      на 3-е исследование леса после этого срока.
      
    Возвращает:
        (callback_name, log_message) или (None, None).
    """
    if loc_id == 2:
        # Триггер Локации 2 (Стена терновника и путь к плотине):
        # 1. Пролог (рюкзак) завершён (l2_prologue_completed).
        # 2. Терновник ещё не обнаружен и не пройден.
        # 3. Прошло 5 дней со дня завершения пролога (day >= l2_prologue_completed_day + 5).
        # 4. На 3-е исследование ручья запускается Стена терновника.
        if (
            game.is_story_flag_set("l2_prologue_completed")
            and not game.is_story_flag_set("l2_thorns_discovered")
            and not game.is_story_flag_set("l2_thorns_cleared")
        ):
            base_day = game.story_flags.get("l2_prologue_completed_day", 1)
            cur_day = getattr(game, "day", 1)
            if cur_day >= base_day + 5:
                count = game.story_flags.get("l2_research_count", 0) + 1
                game.story_flags["l2_research_count"] = count
                if count >= 3:
                    game.set_story_flag("l2_thorns_discovered", True)
                    return "l2_thorns_approach", "🌿 Заросли у ручья сгущаются — впереди встаёт стена непроходимого терновника..."
            return None, None

    if loc_id == 3:
        # Триггер Локации 3 (Скромная Лощина: обнаружение печи и убежища)
        # Условие: не сразу в первый день, а после сна на локации (день > дня входа или общий день >= 5)
        # на 2-е исследование этого дня.
        if not game.is_story_flag_set("l3_shelter_unlocked"):
            l3_entered = game.story_flags.get("l3_entered_day")
            if l3_entered is None:
                game.story_flags["l3_entered_day"] = getattr(game, "day", 1)
                l3_entered = game.story_flags["l3_entered_day"]

            cur_day = getattr(game, "day", 1)
            if cur_day > l3_entered or cur_day >= 5:
                count = getattr(game, "l3_research_count", 0) + 1
                game.l3_research_count = count
                if count >= 2:
                    game.set_story_flag("l3_story_started", True)
                    return "l3_1_fire_low", "🔥 Впереди под нависающей плитой мерцает тёплый отблеск..."

        elif (
            game.is_story_flag_set("l3_shelter_unlocked")
            and not game.is_story_flag_set("l3_ridge_completed")
            and "Солонец (Секач)" not in (getattr(game, "unlocked_locations", []) or [])
        ):
            game.set_story_flag("l3_7_triggered", True)
            return "l3_7_morning", "🐗 С каменистого гребня доносится глухой хруст..."

        return None, None

    if loc_id == 4:
        # Триггер Локации 4 (Просека Охотников):
        # 1. Пролог: Освобождение оленя (минимум 2 ночи на L4)
        if not game.is_story_flag_set("l4_completed"):
            l4_entered = game.story_flags.get("l4_entered_day")
            if l4_entered is None:
                game.story_flags["l4_entered_day"] = getattr(game, "day", 1)
                l4_entered = game.story_flags["l4_entered_day"]

            cur_day = getattr(game, "day", 1)
            sleeps = game.story_flags.get("l4_sleep_count", 0)
            if sleeps >= 2 or cur_day >= l4_entered + 2 or game.is_story_flag_set("l4_started"):
                game.set_story_flag("l4_started", True)
                return "l4_1_entry", "🏹 Ты замечаешь странную натянутую верёвку между деревьями..."
            return None, None

        # 2. Сюжетка 1: «Преграда на обрыве» (4 сна после пролога)
        if not game.is_story_flag_set("l4_ch1_cliff_completed"):
            if "l4_deer_sleeps" not in game.story_flags and "l4_ch1_sleeps" not in game.story_flags:
                game.story_flags["l4_deer_sleeps"] = game.story_flags.get("l4_sleep_count", 0)
            if "l4_deer_completed_day" not in game.story_flags and "l4_ch1_completed_day" not in game.story_flags:
                game.story_flags["l4_deer_completed_day"] = getattr(game, "day", 1)
            base_sleeps = game.story_flags.get("l4_deer_sleeps", game.story_flags.get("l4_ch1_sleeps", 0))
            base_day = game.story_flags.get("l4_deer_completed_day", game.story_flags.get("l4_ch1_completed_day", 1))
            sleeps = game.story_flags.get("l4_sleep_count", 0)
            cur_day = getattr(game, "day", 1)
            if (sleeps - base_sleeps >= 4) or (cur_day >= base_day + 4) or game.is_story_flag_set("l4_ch1_cliff_started"):
                game.set_story_flag("l4_ch1_cliff_started", True)
                return "l4_ch1_1_cliff", "🌫️ С севера просеки веет влажным белесым паром и едким запахом..."
            return None, None

        # 3. Сюжетка 2: «Серая стая» (4 сна после Сюжетки 1)
        if not game.is_story_flag_set("l4_ch2_pack_completed"):
            if "l4_ch2_sleeps" not in game.story_flags:
                game.story_flags["l4_ch2_sleeps"] = game.story_flags.get("l4_sleep_count", 0)
            if "l4_ch2_day" not in game.story_flags:
                game.story_flags["l4_ch2_day"] = getattr(game, "day", 1)
            base_sleeps = game.story_flags.get("l4_ch2_sleeps", 0)
            base_day = game.story_flags.get("l4_ch2_day", 1)
            sleeps = game.story_flags.get("l4_sleep_count", 0)
            cur_day = getattr(game, "day", 1)
            if (sleeps - base_sleeps >= 4) or (cur_day >= base_day + 4) or game.is_story_flag_set("l4_ch2_pack_started"):
                game.set_story_flag("l4_ch2_pack_started", True)
                return "l4_ch2_1_shadow", "🐺 В вечернем тумане раздаётся резкий, голодный вой стаи..."
            return None, None

        # 4. Сюжетка 3: «Дозорный помост и решение по броне» (4 сна после Сюжетки 2)
        if not game.is_story_flag_set("l4_fully_completed"):
            if "l4_ch3_sleeps" not in game.story_flags:
                game.story_flags["l4_ch3_sleeps"] = game.story_flags.get("l4_sleep_count", 0)
            if "l4_ch3_day" not in game.story_flags:
                game.story_flags["l4_ch3_day"] = getattr(game, "day", 1)
            base_sleeps = game.story_flags.get("l4_ch3_sleeps", 0)
            base_day = game.story_flags.get("l4_ch3_day", 1)
            sleeps = game.story_flags.get("l4_sleep_count", 0)
            cur_day = getattr(game, "day", 1)
            if (sleeps - base_sleeps >= 4) or (cur_day >= base_day + 4) or game.is_story_flag_set("l4_ch3_started"):
                game.set_story_flag("l4_ch3_started", True)
                return "l4_ch3_1_shelter", "🌲 В кронах двух сплётшихся сосен виднеется старый дозорный помост..."
            return None, None

    if loc_id == 5:
        # Проверка сюжетного триггера Главы 2 Локации 5 (Заводь Исполина):
        # 1. Первая глава завершена (l5_completed).
        # 2. Вторая глава еще не запускалась и не завершена.
        # 3. На 3-й день (или позже) после завершения L5 Chapter 1 (или общего дня >= 3).
        # 4. На 3-й день — 3-е исследование локации 5 (не обязательно подряд, можно заходить в костёр и т.д.).
        if (
            game.is_story_flag_set("l5_completed")
            and not game.is_story_flag_set("l5_ch2_completed")
            and not game.is_story_flag_set("l5_ch2_started")
        ):
            if "l5_completed_day" not in game.story_flags:
                game.story_flags["l5_completed_day"] = getattr(game, "day", 1)
            base_day = game.story_flags.get("l5_completed_day", 1)
            cur_day = getattr(game, "day", 1)

            if cur_day >= base_day + 2 or cur_day >= 3:
                count = game.story_flags.get("l5_day3_research_count", 0) + 1
                game.story_flags["l5_day3_research_count"] = count
                if count >= 3:
                    game.set_story_flag("l5_ch2_started", True)
                    return "l5_2_1", "👣 На сухом уступе возле сланцевой плиты приходят мысли о виденной твари..."
        return None, None

    if loc_id != 1:
        return None, None

    # Триггер 1: Встреча со старым волком у пня (пролог L1)
    if torch_equipped:
        torch_count = getattr(game, "torch_research_count", 0) + 1
        game.torch_research_count = torch_count
        if (
            getattr(game, "day", 1) >= 3
            and torch_count >= 4
            and not game.is_story_flag_set("l1_completed")
        ):
            return "forest_start", "🔦 Ты замечаешь странные следы и слышишь глухое рычание..."

    # Триггер 2: Обнаружение волчьего логова (L1.5)
    if (
        game.is_story_flag_set("l1_completed")
        and not getattr(game, "wolf_lair_unlocked", False)
    ):
        l1_day = game.story_flags.get("l1_completed_day", 1)
        if game.day >= l1_day + 4:
            game.l1_post_research_count = getattr(game, "l1_post_research_count", 0) + 1
            if game.l1_post_research_count >= 3:
                game.set_story_flag("l1_5_triggered")
                return "l1_5_start", None

    # Триггер 3: Забытый купол (дуб с парашютом)
    # Запуск: после первой ночи (day == 2) на 2-е исследование леса без факела
    if (
        getattr(game, "day", 1) == 2
        and not torch_equipped
        and not game.is_story_flag_set("l1_dome_discovered")
        and not game.is_story_flag_set("l1_dome_completed")
    ):
        day2_count = getattr(game, "l1_day2_research_count", 0) + 1
        game.l1_day2_research_count = day2_count
        if day2_count >= 2:
            game.set_story_flag("l1_dome_discovered", True)
            return "l1_dome_start", None

    return None, None


def is_story_callback(data: str) -> bool:
    """Проверяет, относится ли данный callback к сюжетным веткам L1-L7."""
    return (
        data in (
            "forest_start",
            "story_start",
            "wolf_start",
            "wolf_leave",
            "wolf_torch",
            "peek_den",
            "pet_leave",
            "pet_take",
            "waiting_pet_name",
            "story_next",
            "sanctuary_resolve",
            "location_enter_2",
            "location_enter_3",
            "location_enter_4",
            "location_enter_5",
            "location_enter_6",
            "location_enter_7",
            "location_enter_boar",
        )
        or data.startswith((
            "l1_", "l1_dome", "l1_5", "l1_6", "l1_7", "wolf_lair", "wolf_battle", "boar_",
            "l2_", "ruchey_", "river_", "snake_", "story_",
            "l3_", "slate_", "rest_", "examine",
            "hunters_", "glade_", "l4_",
            "slug_", "pit_", "l5_", "slime_battle",
            "furry_", "warm_", "cave_",
            "sanctuary_",
        ))
    )
