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
# ЛОКАЦИЯ 1: ЛЕСНОЙ СТАРТ
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_1_forest_start(data: str, game, uid: int):
    """Сюжетные разветвления для Локации 1: Лесной старт."""
    return handle_story(data, game, uid)


def handle_story(data: str, game, uid: int):
    """Обработать сюжетную сцену волка и котёнка или передать в ветку других локаций."""
    res = None
    if data.startswith("l1_dome"):
        res = handle_l1_dome(data, game, uid)
    elif data.startswith("l2_") or data.startswith("ruchey_") or data.startswith("river_") or data.startswith("snake_") or data.startswith("story_") or data == "location_enter_2":
        if data == "location_enter_2":
            game.current_location = "Ручей со змеями"
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

    if res is not None:
        text, kb = res
        if text is None:
            text = game.get_ui()
            kb = get_main_kb(game)
        return text, kb

    text = None
    kb = None

    if data in ("forest_start", "story_start", "wolf_start", "action_1"):
        game.story_state = "wolf_encounter"
        game.set_story_flag("l1_started")
        game.add_log("Ты слышишь рычание в кустах... Это волк!")
        text = (
            "Тёмный лес замер. Из густых кустов на тебя смотрят два горящих глаза.\n"
            "Старый, истощённый волк яростно копает лапами под старым пнём, совсем тебя не замечая.\n"
            "Факел в твоей руке потрескивает, отбрасывая дрожащие тени на ветви.\n\n"
            "Твои действия:"
        )
        kb = wolf_kb

    elif data == "wolf_leave":
        game.story_state = None
        game.reset_nav()
        game.set_story_flag("l1_completed")
        game.story_flags["l1_completed_day"] = getattr(game, "day", 1)
        game.set_story_flag("left_wolf")
        game.adjust_narrative_karma("pragmatism", 3)
        game.add_log("Ты тихо отступил, не связываясь с волком.")
        text = (
            "Ты медленно пятишься назад, стараясь не хрустнуть ни одной веткой.\n"
            "Через несколько шагов рычание стихает за деревьями.\n"
            "Что бы там ни было под пнём — оно теперь не твоё дело.\n"
            "Сердце всё ещё колотится."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Выйти в лагерь", callback_data="story_next")]
        ])

    elif data == "wolf_torch":
        has_torch_in_hand = (
            game.equipment.get("hand_left") == "Факел"
            or game.equipment.get("hand_right") == "Факел"
        )

        if not has_torch_in_hand and game.story_state != "after_fight":
            game.add_log("У тебя нет факела в руке!")
            text = game.get_ui()
            kb = get_main_kb(game)
            return text, kb

        if game.story_state != "after_fight":
            game.adjust_narrative_karma("intervention", 3)
            game.adjust_narrative_karma("compassion", -2)
            game.adjust_narrative_karma("pragmatism", 3)
            game.story_state = "after_fight"
            if game.equipment.get("hand_left") == "Факел":
                game.equipment["hand_left"] = None
            if game.equipment.get("hand_right") == "Факел":
                game.equipment["hand_right"] = None
            if "Факел" in game.inventory:
                del game.inventory["Факел"]
            game.story_flags["torch_consumed"] = True

        text = (
            "Ты поднимаешь факел высоко над своей головой, озаряя местность светом.\n"
            "Твоё неожиданное появление и вид огня явно вогнали старого волка в ступор.\n"
            "Громкими криками и руганью — больше для храбрости — ты пытаешься напугать зверя."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l1_1b_1")]
        ])

    elif data == "l1_1b_1":
        text = (
            "Голодный хищник, громко рыча, разворачивается в твою сторону.\n"
            "Ты слышишь угрожающее рычание, за которым теряются окружающие звуки, а из его пасти на землю капает пенистая слюна."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l1_1b_2")]
        ])

    elif data == "l1_1b_2":
        text = (
            "Единственное твоё оружие — горящий факел, который явно пугает волка.\n"
            "Истошно крича и размахивая факелом, ты спотыкаешься об корень и, падая, попадаешь горящим концом по морде зверя.\n"
            "Вокруг разлетаются снопы искр. Древко с хрустом ломается, ударившись о выступающий корень."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l1_1b_3")]
        ])

    elif data == "l1_1b_3":
        text = (
            "Ты встаёшь всего за пару мгновений, но волка уже не видно.\n"
            "Слышны только громкий стук твоего собственного сердца и удаляющееся скуление. В воздухе стоит запах подгорелой шерсти…\n"
            "Ещё не понимая, как тебе повезло, ты круглыми глазами смотришь на этот несчастный пень и на остатки сломанного факела у твоих ног…"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Заглянуть под пень", callback_data="l1_2")]
        ])

    elif data in ("l1_2", "peek_den"):
        game.story_state = "cat_choice"
        text = (
            "Тяжело дыша, ты опускаешься на колени, чтобы заглянуть под пень…\n"
            "В слабом отсвете угасающих угольков факела, почти на самом дне ямы, блестят два огромных влажных глаза…\n\n"
            "Твои действия:"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✋ Протянуть руку", callback_data="l1_2b")],
            [InlineKeyboardButton(text="🚫 Оставить его здесь", callback_data="l1_2a")]
        ])

    elif data == "l1_2a":
        text = "Ты медленно встаёшь и уходишь, с опаской оглядываясь на пень…"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Выйти в лагерь", callback_data="l1_2a_leave")]
        ])

    elif data in ("l1_2a_leave", "pet_leave"):
        game.adjust_narrative_karma("compassion", -3)
        game.story_state = None
        game.reset_nav()
        game.set_story_flag("l1_completed")
        game.story_flags["l1_completed_day"] = getattr(game, "day", 1)
        game.set_story_flag("left_kitten")
        game.active_story_callback = None
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "l1_2b":
        text = (
            "Ты осторожно опускаешь ладонь в яму и чувствуешь, как твою руку тихонько обнюхивают.\n"
            "Потом что-то мягкое и пушистое касается твоих пальцев."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l1_2b_1")]
        ])

    elif data == "l1_2b_1":
        text = (
            "Убрав руку, ты замечаешь, как из-под пня — настолько трухлявого, что непонятно, как он ещё не развалился, — тихонько выплывает тёмное и пушистое облачко с огромными влажными глазами.\n"
            "Ты протягиваешь руки и берёшь маленького котёнка в ладошки, совершенно не понимая, как он тут оказался.\n"
            "Хочется его погладить и как-то назвать…\n"
            "Возьмёшь его с собой?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤝 Забрать с собой", callback_data="l1_3")],
            [InlineKeyboardButton(text="🚫 Оставить здесь", callback_data="l1_2c")]
        ])

    elif data == "l1_2c":
        text = (
            "Ты осторожно опускаешь котёнка на землю возле пня.\n"
            "Он смотрит на тебя снизу вверх, а ты медленно встаёшь и уходишь, с опаской оглядываясь…"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Выйти в лагерь", callback_data="l1_2c_leave")]
        ])

    elif data in ("l1_2c_leave", "kitten_to_main"):
        game.adjust_narrative_karma("compassion", -3)
        game.story_state = None
        game.reset_nav()
        game.set_story_flag("l1_completed")
        game.story_flags["l1_completed_day"] = getattr(game, "day", 1)
        game.set_story_flag("left_kitten")
        game.active_story_callback = None
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data in ("l1_3", "pet_take", "waiting_pet_name"):
        has_named_pet = game.is_story_flag_set("has_pet") and bool(
            game.equipment.get("pet") or (getattr(game, "companion_name", "") not in (None, "", "Кот", "Котёнок"))
        )
        if has_named_pet:
            game.active_story_callback = None
            game.story_state = None
            return game.get_ui(), get_main_kb(game)

        if not game.is_story_flag_set("saved_kitten"):
            game.set_story_flag("saved_kitten")
            game.set_story_flag("has_pet")
            game.set_story_flag("l1_completed")
            game.story_flags["l1_completed_day"] = getattr(game, "day", 1)
            game.adjust_narrative_karma("compassion", 2)
            game.spared_souls = getattr(game, "spared_souls", 0) + 1
        game.story_state = "WAITING_FOR_PET_NAME"
        text = (
            "Ты держишь котёнка в ладонях. Хочется его погладить и как-то назвать…\n"
            "Как ты его назовёшь?"
        )
        kb = None

    elif data == "story_next":
        game.story_state = None
        game.active_story_callback = None
        game.reset_nav()
        text = game.get_ui()
        kb = get_main_kb(game)

    elif (
        data.startswith("l1_5")
        or data.startswith("l1_6")
        or data.startswith("l1_7")
        or data.startswith("wolf_lair")
        or data.startswith("wolf_battle")
        or data in ("location_enter_1", "location_enter_2")
    ):
        return handle_l1_wolf_lair(data, game, uid)

    if kb == get_main_kb(game) or data in ("wolf_leave", "pet_leave", "l1_2a_leave", "l1_2c_leave", "kitten_to_main", "story_next", "back") or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        if data in ("l1_3", "pet_take", "waiting_pet_name"):
            game.active_story_callback = "waiting_pet_name"
        else:
            game.active_story_callback = data

    return text, kb


def check_forest_research_story_trigger(game, loc_id: int, torch_equipped: bool) -> tuple[str | None, str | None]:
    """Проверяет сюжетные триггеры при исследовании локации 1 (Лесной старт).
    
    Алгоритм:
    - L1 (Встреча с волком у пня): при наличии факела на 4-е исследование запускается forest_start.
    - L1.5 (Волчье логово): запускается не ранее чем через 4 дня после завершения L1 (day >= l1_completed_day + 4)
      на 3-е исследование леса после этого срока.
      
    Возвращает:
        (callback_name, log_message) или (None, None).
    """
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


def handle_l1_dome(data: str, game, uid: int):
    """Сюжетный сценарий локации «Забытый купол» (дуб с парашютом и армейской флягой)."""
    text = None
    kb = None
    cur_day = getattr(game, "day", 1)

    # 1. Первый визит или повторный вход на локацию
    if data in ("l1_dome_start", "l1_dome_enter"):
        game.push_screen("l1_dome")
        visited_once = game.is_story_flag_set("l1_dome_visited_once")

        # Если уже был первый визит ранее:
        if visited_once:
            # А. Если ранец уже упал на землю — сразу показываем завал!
            if game.is_story_flag_set("l1_dome_backpack_fallen"):
                text = (
                    "Ранец лежит прямо среди густого валежника, колючего терновника и вывороченных корней дуба.\n\n"
                    "Чтобы достать его, придется потратить силы и расчистить завал."
                )
                if game.ap >= 1:
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🪓 Расчистить завал (1 ⚡)", callback_data="l1_dome_loot")],
                        [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")],
                    ])
                else:
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❌ Нет сил расчищать", callback_data="menu_main")],
                    ])
                return text, kb

            # Б. Проверка: уже была попытка сегодня?
            last_attempt_day = game.story_flags.get("l1_dome_day_attempt")
            if last_attempt_day == cur_day:
                text = (
                    "Тело всё еще ноет от недавнего падения и усталости.\n\n"
                    "Лезть на дуб или суетиться прямо сейчас бессмысленно. "
                    "Нужно переждать до завтра, дать силам восстановиться и обдумать план."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")]
                ])
                return text, kb

            # В. Проверка погоды: плохая погода (дождь, гроза, пасмурно)
            if game.weather in {"rain", "storm", "cloudy"}:
                text = (
                    "Непогода окутала поляну сыростью. С ветвей дуба стекают струи воды, а намокший купол тяжело обвис между сучьями.\n\n"
                    "В такой серый полумрак и скользкую сырость разглядеть крепление ранца и сбить его невозможно. Стоит прийти в ясную погоду."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")]
                ])
                return text, kb

            # Г. Ясная солнечная погода (clear): выбор вариантов
            has_pet = game.is_story_flag_set("saved_kitten") or bool(game.equipment.get("pet"))
            has_staff = (
                game.equipment.get("hand_right") in ("Крепкий посох", "Палка")
                or game.equipment.get("hand_left") in ("Крепкий посох", "Палка")
                or game.inventory.get("Крепкий посох", 0) > 0
                or game.inventory.get("Палка", 0) > 0
            )

            text = (
                "Солнечные лучи пробиваются сквозь крону. На сухом дубе хорошо виден застрявший ранец и переплетенные стропы.\n\n"
                "Лезть на дерево нельзя. Как попытаться достать ранец?"
            )
            buttons = []
            if has_staff:
                buttons.append([InlineKeyboardButton(text="🥢 Сбить посохом (1 ⚡)", callback_data="l1_dome_staff_solve")])
            if has_pet:
                buttons.append([InlineKeyboardButton(text="🐱 Отпустить котёнка погулять", callback_data="l1_dome_cat_solve")])
            buttons.append([InlineKeyboardButton(text="🪨 Бросать камни (1 ⚡)", callback_data="l1_dome_stone_throw")])
            buttons.append([InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            return text, kb

        # ПЕРВЫЙ ВИЗИТ (погода игнорируется): Окно 1.1
        text = (
            "В глубине леса ветви расступаются перед поляной. Посреди неё возвышается древний расколотый дуб.\n\n"
            "Высоко на черных сучьях висит выцветший парашютный купол. В истлевших стропах белеют кости и виден армейский брезентовый ранец."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧗 Вскарабкаться на дуб", callback_data="l1_dome_climb_v1")],
            [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")],
        ])

    elif data == "l1_dome_climb_v1":
        # Окно 1.2: Срыв ветви и падение
        damage = 5
        game.hp = max(1, game.hp - damage)
        game.consume_action(1)
        text = (
            "Ты хватаешься за толстый сук и подтягиваешься. Но мертвая древесина с глухим сухим треском обламывается под твоим весом!\n\n"
            "Ты летишь вниз и со всего маху ударяешься о корни дуба. Дыхание перехватывает от резкой боли.\n\n"
            "*(Эффекты: -5 HP, -1 AP)*"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤕 Подняться на ноги", callback_data="l1_dome_after_fall")],
        ])

    elif data == "l1_dome_after_fall":
        # Окно 1.3: Урок на будущее
        game.story_flags["l1_dome_visited_once"] = True
        game.story_flags["l1_dome_day_attempt"] = cur_day
        text = (
            "С трудом поднявшись, ты отряхиваешь грязь и потираешь ушибленные ребра.\n\n"
            "Голыми руками на этот сухой дуб не залезть — кора осыпается, а ветви гнилые. "
            "Не стоит унывать, но сегодня тело слишком ноет. Нужно вернуться завтра и придумать другой способ."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")],
        ])

    elif data == "l1_dome_stone_throw":
        # Броски камнями: тратит 1 AP и 15 жажды, не получается
        game.consume_action(1)
        game.thirst = max(0, game.thirst - 15)
        text = (
            "Ты собираешь увесистые камни и изо всех сил швыряешь их вверх. Камни звонко бьют по коре и веткам, "
            "но стропы слишком тонкие и гибкие — сбить их не удается.\n\n"
            "От бесконечных бросков пересохло в горле, а плечо мучительно ломит. Кажется, камнями здесь ничего не добиться.\n\n"
            "*(Эффекты: -1 AP, -15 к жажде)*"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Перевести дух", callback_data="l1_dome_enter")],
        ])

    elif data == "l1_dome_staff_solve":
        # Попытка с посохом: 3 попытки
        game.consume_action(1)
        game.story_flags["l1_dome_day_attempt"] = cur_day
        staff_tries = game.story_flags.get("l1_dome_staff_tries", 0) + 1
        game.story_flags["l1_dome_staff_tries"] = staff_tries

        if staff_tries == 1:
            # Попытка 1
            text = (
                "Ты привязываешь длинную крепкую ветвь к своему посоху и с трудом поднимаешь конструкцию вверх. "
                "Долго ловишь баланс, целясь в спутанные стропы.\n\n"
                "Конец ветви лишь вскользь задевает узел. От долгого напряжения шея и руки затекли и дрожат. "
                "Сбить с наскока не вышло, придется отложить до завтра.\n\n"
                "*(Эффекты: -1 AP)*"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")],
            ])
        elif staff_tries == 2:
            # Попытка 2
            text = (
                "Ты вновь поднимаешь удлиненный посох и методично бьешь по стропе. Снова долгая ловля баланса, "
                "руки немеют от тяжести, а ветвь вибрирует от ударов.\n\n"
                "Узел строп заметно разболтался и надорвался, но ранец всё еще держится. Силы на исходе, мышцы гудят. "
                "На сегодня хватит, завтра узел точно поддастся.\n\n"
                "*(Эффекты: -1 AP)*"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")],
            ])
        else:
            # Попытка 3 — решающая (успех)
            game.set_story_flag("l1_dome_backpack_fallen", True)
            text = (
                "Натренированным движением ты поддеваешь разболтанный узел раздвоенным концом посоха и с силой проворачиваешь его.\n\n"
                "Сухой треск! Перетертые стропы лопаются, и тяжелый ранец с шумом летит вниз, врезаясь в густой валежник у корней дуба!\n\n"
                "*(Эффекты: -1 AP)*"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌿 Осмотреть завал у корней", callback_data="l1_dome_fall")],
            ])

    elif data == "l1_dome_cat_solve":
        # Вариант с котёнком — мгновенный успех
        game.set_story_flag("l1_dome_backpack_fallen", True)
        text = (
            "Котёнок с интересом смотрит на колышущиеся от ветра стропы. Мяукнув, он мгновенно взлетает по шершавому стволу дуба, словно белка.\n\n"
            "Пара ловких движений острыми зубками и когтями — и стропа лопается! Ранец с треском падает вниз прямо в валежник у корней. "
            "Довольный кот спрыгивает к тебе на плечо."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌿 Осмотреть завал у корней", callback_data="l1_dome_fall")],
        ])

    elif data == "l1_dome_fall":
        # Окно 5.1: Ранец в завале
        text = (
            "Ранец лежит прямо среди густого валежника, колючего терновника и вывороченных корней дуба.\n\n"
            "Чтобы достать его, придется потратить силы и расчистить завал."
        )
        if game.ap >= 1:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🪓 Расчистить завал (1 ⚡)", callback_data="l1_dome_loot")],
                [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")],
            ])
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Нет сил расчищать", callback_data="menu_main")],
            ])

    elif data == "l1_dome_loot":
        if game.ap < 1:
            text = (
                "Ранец лежит прямо среди густого валежника, колючего терновника и вывороченных корней дуба.\n\n"
                "У тебя нет сил расчистить завал! Нужно отдохнуть и набраться сил."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Нет сил расчищать", callback_data="menu_main")],
            ])
            return text, kb

        game.consume_action(1)
        # Армейская фляга падает в инвентарь сухой: 0/20, без автоэкипировки
        game.inventory["Армейская фляга"] = game.inventory.get("Армейская фляга", 0) + 1
        game.army_flask_water = 0

        game.adjust_narrative_karma("pragmatism", 3)
        game.set_story_flag("l1_dome_completed", True)
        game.story_state = None
        game.active_story_callback = None
        game.reset_nav()
        text = (
            "Разбросав ветви валежника, ты открываешь тяжелые пряжки ранца. Внутри — надежная металлическая **Армейская фляга** (пустая, 0/20)!\n\n"
            "Ты бережно укладываешь упавшие останки парашютиста под сенью дуба и присыпаешь их землей и камнями, воздав последние почести. "
            "На душе становится спокойнее.\n\n"
            "*(Эффекты: -1 AP, получена Армейская фляга 0/20, +3 кармы)*"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")],
        ])

    return text, kb


def handle_l1_wolf_lair(data: str, game, uid: int):
    """Сценарии L1.5–L1.7: встреча со старым волком в логове, бой, развязка и выход к Ручью."""
    text = None
    kb = None

    if data == "l1_5_start":
        game.story_state = "l1_5"
        text = (
            "Сушняка вокруг лагеря почти не осталось, а дичь ушла. "
            "Продираясь через бурелом на краю леса, ты упираешься в каменистый овраг со входом в неглубокую пещеру.\n\n"
            "«Дальше пути нет... Только эта расщелина. Если не найду выход — просто замёрзну на старой стоянке»."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l1_5_wolf")]
        ])

    elif data == "l1_5_wolf":
        text = (
            "Из темноты пещеры поднимается волк. Ты узнаёшь его: кости под редкой шкурой, "
            "мутный глаз и свежая тёмная корка от ожога твоим факелом на морде. "
            "Зверь глухо клокочет, скалясь обломанными клыками. Он слаб, но загнан в угол и готов драться."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l1_5_behind")]
        ])

    elif data == "l1_5_behind":
        text = (
            "Прямо за его спиной пещера расширяется. "
            "Оттуда в духоту оврага тянет прохладой и влагой, доносится шум далёкой воды. "
            "Там выход наружу, но зверь перекрыл тропу."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l1_5_thought")]
        ])

    elif data == "l1_5_thought":
        text = (
            "«С голыми руками на него лезть — самоубийство. Он ранен, но это матёрый хищник. "
            "Нужно вернуться в лагерь и сделать оружие посерьёзнее твоих кулаков»."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏃 Тихо уйти в лагерь", callback_data="l1_5_leave")]
        ])

    elif data == "l1_5_leave":
        if "Крепкий посох" not in getattr(game, "unlocked_crafts", []):
            game.unlocked_crafts = list(getattr(game, "unlocked_crafts", [])) + ["Крепкий посох"]
        game.locations_unlocked = True
        game.wolf_lair_unlocked = True
        game.wolf_lair_active = True
        game.story_state = None
        game.reset_nav()
        if not game.is_story_flag_set("l1_staff_lair_notified"):
            game.set_story_flag("l1_staff_lair_notified", True)
            game.add_log("🔨 Открыт крафт: 🪵 Крепкий посох")
            game.add_log("🐾 В меню «Локации» появилось Волчье логово")
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "wolf_lair_enter":
        game.push_screen("wolf_lair")
        has_staff = game.equipment.get("hand_right") == "Крепкий посох"
        if not has_staff:
            text = (
                "Без надёжного оружия соваться в логово самоубийственно. "
                "Сначала нужно скрафтить и взять в руку хоть что-то."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
            ])
        else:
            text = (
                "Сжимая в руке тяжёлый посох, ты стоишь у входа в пещеру.\n\n"
                "Из темноты доносится хриплое прерывистое дыхание. В полумраке блестят воспалённые волчьи глаза.\n"
                "Зверь поднимается на лапы, шерсть на загривке встаёт дыбом, а из приоткрытой пасти обнажаются жёлтые клыки.\n"
                "Воздух густеет от напряжения: отступать некуда, хищник готов к смертельному прыжку."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Шагнуть в пещеру", callback_data="wolf_battle_start")],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
            ])

    elif data == "wolf_battle_start":
        return start_battle(game, "old_wolf")

    elif data in ("wolf_battle_attack", "wolf_battle_defend", "wolf_battle_flee"):
        return apply_action(data, game, "old_wolf")

    elif data == "wolf_battle_screen":
        battle = getattr(game, "wolf_battle", None)
        if battle and battle.get("wolf_hp", 0) > 0 and getattr(game, "hp", 100) > 0:
            cur_enemy = battle.get("enemy_id", "old_wolf")
            if cur_enemy == "ancient_boar":
                return get_battle_text(game, "ancient_boar"), get_battle_kb(game, "ancient_boar")
            return get_wolf_battle_text(game, "old_wolf"), get_wolf_battle_kb()
        if game.is_story_flag_set("wolf_lair_defeated") or not battle:
            if not game.is_story_flag_set("wolf_spared") and not game.is_story_flag_set("wolf_killed"):
                return handle_l1_wolf_lair("l1_5_aftermath", game, uid)
            game.active_story_callback = None
            return game.get_ui(), get_main_kb(game)
        return start_battle(game, "old_wolf")

    elif data == "l1_5_aftermath":
        has_pet = bool(game.equipment.get("pet")) or game.is_story_flag_set("has_pet")
        text = (
            "Тяжёлый удар посоха окончательно сбивает старого волка с ног. "
            "Зверь заваливается на бок и тяжело дышит. Он просто лежит на камнях и ждёт твоих действий."
        )
        if has_pet:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Далее ➔", callback_data="l1_5_kitten_plea")]
            ])
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🤝 Пощадить зверя", callback_data="l1_5_spare")],
                [InlineKeyboardButton(text="💀 Добить хищника", callback_data="l1_5_kill")],
            ])

    elif data == "l1_5_kitten_plea":
        text = (
            "Из-под твоей куртки робко высовывается усатая мордочка. "
            "Котёнок замирает, глядя на лежащего волка, затем переводит огромные влажные глаза на тебя "
            "и несмело касается твоей руки тёплой лапкой. Словно просит не убивать побеждённого."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤝 Пощадить зверя", callback_data="l1_5_spare")],
            [InlineKeyboardButton(text="💀 Добить хищника", callback_data="l1_5_kill")],
        ])

    elif data == "l1_5_spare":
        consumables = [
            item for item, count in game.inventory.items()
            if count > 0 and (is_item_consumable(item) and get_item_type(item) in ("food", "berry", "mushroom"))
        ]
        consumables.sort(key=lambda it: (get_item_rank(it), it))
        if not consumables:
            if not game.is_story_flag_set("spared_wolf"):
                game.spared_souls = getattr(game, "spared_souls", 0) + 1
            game.set_story_flag("spared_wolf")
            game.adjust_narrative_karma("compassion", 5)
            text = (
                "Ты опускаешь посох, делаешь предупреждающий жест и не приближаешься, давая волку пространство.\n"
                "У тебя нет с собой еды, но зверь видит, что ты не станешь его добивать.\n"
                "Волк с трудом поднимается и медленно отползает в темноту глубины норы. Путь открыт."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➡️ Шагнуть в расщелину", callback_data="l1_6_passage")]
            ])
        else:
            text = (
                "Ты решаешь пощадить зверя.\n\n"
                "Старый волк слаб и голоден — чтобы он позволил пройти и не бросился в спину, нужно отдать ему что-то съедобное.\n\n"
                "Выбери еду из инвентаря:"
            )
            buttons = []
            for it in consumables:
                c = game.inventory.get(it, 0)
                marker = get_item_emoji(it)
                buttons.append([InlineKeyboardButton(text=f"{marker} {it} ×{c}", callback_data=f"l1_5_feed:{it}")])
            buttons.append([InlineKeyboardButton(text="🚫 Не отдавать (Отмена)", callback_data="l1_5_spare_cancel")])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l1_5_spare_cancel":
        has_pet = bool(game.equipment.get("pet")) or game.is_story_flag_set("has_pet")
        return handle_l1_wolf_lair("l1_5_kitten_plea" if has_pet else "l1_5_aftermath", game, uid)

    elif data.startswith("l1_5_feed:"):
        food_item = data.removeprefix("l1_5_feed:")
        if game.inventory.get(food_item, 0) > 0:
            game.inventory[food_item] -= 1
            if game.inventory[food_item] <= 0:
                del game.inventory[food_item]
        if not game.is_story_flag_set("spared_wolf"):
            game.spared_souls = getattr(game, "spared_souls", 0) + 1
        game.story_flags["spared_wolf_food"] = food_item
        game.set_story_flag("spared_wolf")
        game.adjust_narrative_karma("compassion", 5)
        text = (
            "Ты опускаешь посох, делаешь предупреждающий жест и не приближаешься, давая волку пространство.\n"
            f"Свободной рукой ты достаёшь из рюкзака {food_item} и бросаешь к его лапам.\n"
            "Волк жадно заглатывает кусок и медленно отползает в темноту глубины норы. Путь открыт.\n"
            "──────────\n"
            f"Отдано: {food_item} ×1"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Шагнуть в расщелину", callback_data="l1_6_passage")]
        ])

    elif data == "l1_5_kill":
        text = "Ты покидаешь пещеру с уверенностью, что на тебя этой ночью никто не нападёт."
        if not game.is_story_flag_set("killed_wolf"):
            game.set_story_flag("killed_wolf")
            game.adjust_narrative_karma("pragmatism", 5)
            game.kills_count = getattr(game, "kills_count", 0) + 1
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Шагнуть в расщелину", callback_data="l1_6_passage")]
        ])

    elif data == "l1_6_passage":
        text = (
            "Ты протискиваешься в узкую щель за логовом. Каменные стены скребут по одежде, сверху свисают мокрые корни. "
            "Воздух впереди теплеет и наполняется шумом воды. Ты делаешь последний рывок вперёд..."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l1_6_exit")]
        ])

    elif data == "l1_6_exit":
        has_pet = bool(game.equipment.get("pet")) or game.is_story_flag_set("has_pet")
        if has_pet:
            text = (
                "Каменный коридор обрывается, и яркий свет ослепляет тебя. "
                "Котёнок выбирается на плечо, щурится на простор и шумно тянет влажным носом незнакомый речной воздух. "
                "Глухой лес позади — вы вышли к воде."
            )
        else:
            text = (
                "Каменный коридор обрывается, и яркий свет ослепляет тебя. "
                "Прищурившись, ты видишь крутой спуск к бурлящей воде. "
                "Воздух пахнет свежестью и сырым камнем. Глухой лес позади — впереди неизведанная земля."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l1_7_finish")]
        ])

    elif data == "l1_7_finish":
        game.wolf_lair_active = False
        game.wolf_lair_defeated = True
        game.locations_unlocked = True
        game.wolf_battle = None
        game.unlocked_locations = ["Лесной старт", "Ручей"]
        game.set_story_flag("l1_7_completed")
        text = (
            "🌲 Глава завершена: Тайны густого леса\n\n"
            "Вы преодолели опасности чащи и вышли к шумящей воде.\n"
            "В меню «Локации» теперь доступен Ручей."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 Осмотреться на новом месте", callback_data="l1_7_inspect")]
        ])

    elif data == "l1_7_inspect":
        game.reset_nav()
        game.current_location = "Ручей"
        game.story_state = None
        text, kb = handle_location_2_ruchey("location_enter_2", game, uid)

    elif data == "location_enter_1":
        game.reset_nav()
        game.current_location = "Лесной старт"
        game.add_log("Ты вернулся в Стартовый лес.")
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "location_enter_2":
        game.reset_nav()
        game.current_location = "Ручей"
        text, kb = handle_location_2_ruchey("location_enter_2", game, uid)

    if kb == get_main_kb(game) or data in ("l1_5_leave", "l1_7_finish", "location_enter_1", "back") or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        battle = getattr(game, "wolf_battle", None)
        if battle and getattr(game, "hp", 100) > 0 and battle.get("wolf_hp", 0) > 0:
            cur_enemy = battle.get("enemy_id", "old_wolf")
            game.active_story_callback = "boar_battle_screen" if cur_enemy == "ancient_boar" else "wolf_battle_screen"
        else:
            game.active_story_callback = data

    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 2: РУЧЕЙ (ПЛОТИНА И ПЕРЕПРАВА В СКРОМНУЮ ЛОЩИНУ)
# ──────────────────────────────────────────────────────────────────────────────

L2_PUZZLE_BANK = [
    # Заход 0: Гидрологический запуск
    [
        {
            "num_str": "«Вопрос номер один»",
            "text": "Основной водосброс заблокирован. Для уравнивания давления в нижнем бьефе требуется открыть перепускной клапан. Какой сектор задвижки задействовать?",
            "options": [
                ("Левый вспомогательный", True),
                ("Центральный аварийный", False),
                ("Правый донный", False),
            ],
        },
        {
            "num_str": "«Вопрос номер два»",
            "text": "Манометр маслостанции турбины показывает падение давления до 0.4 МПа. Выберите режим циркуляции насоса.",
            "options": [
                ("Продувка магистрали", False),
                ("Форсированная подкачка", True),
                ("Сброс в дренаж", False),
            ],
        },
        {
            "num_str": "«Вопрос номер три»",
            "text": "Частота генератора нестабильна: 42 Гц вместо номинала. Какое воздействие подать на направляющий аппарат?",
            "options": [
                ("Увеличить угол раскрытия лопаток", True),
                ("Заблокировать ротор тормозом", False),
                ("Перевести в режим холостого хода", False),
            ],
        },
    ],
    # Заход 1: Электродинамика реле
    [
        {
            "num_str": "«Вопрос номер один»",
            "text": "Напряжение на вспомогательной шине 110 В. Для взвода соленоида моста требуется подключить балластное сопротивление. Какую группу резисторов замкнуть?",
            "options": [
                ("Группа Р-1 (низкоомная)", True),
                ("Группа Р-3 (высокоомная)", False),
                ("Прямое шунтирование", False),
            ],
        },
        {
            "num_str": "«Вопрос номер два»",
            "text": "Срабатывает дифференциальная защита трансформатора Т-2. Укажите алгоритм локализации утечки.",
            "options": [
                ("Отключить вторичные цепи учёта", False),
                ("Размыкание вводного разъединителя", True),
                ("Замыкание заземляющего ножа", False),
            ],
        },
        {
            "num_str": "«Вопрос номер три»",
            "text": "Стрелка фазометра отклоняется в зону опережения. Какой компенсатор ввести в контур?",
            "options": [
                ("Индуктивный дроссель ДР-4", True),
                ("Блок конденсаторов К-10", False),
                ("Реостат возбуждения", False),
            ],
        },
    ],
    # Заход 2: Механика редуктора
    [
        {
            "num_str": "«Вопрос номер один»",
            "text": "Зубчатая передача подъёмного механизма застопорена стопорным пальцем. В каком порядке снять фиксацию?",
            "options": [
                ("Ослабить контргайку, вытянуть палец", True),
                ("Выбить палец молотом", False),
                ("Подать обратный ход лебёдки", False),
            ],
        },
        {
            "num_str": "«Вопрос номер два»",
            "text": "Направляющие тросы моста имеют натяжение 12 тонн на левом пилоне и 4 тонны на правом. Куда перераспределить балласт?",
            "options": [
                ("В левый кессон", False),
                ("В правый уравновешивающий кессон", True),
                ("Слить балласт полностью", False),
            ],
        },
        {
            "num_str": "«Вопрос номер три»",
            "text": "Тормозные колодки барабана заклинило нагаром. Какое усилие приложить к ручному дублёру?",
            "options": [
                ("Вращение по часовой стрелке с выжимом рычага", True),
                ("Рывок против часовой стрелки", False),
                ("Резкий удар по фиксатору", False),
            ],
        },
    ],
    # Заход 3: Пневматика и вакуум
    [
        {
            "num_str": "«Вопрос номер один»",
            "text": "Пневмомагистраль затвора заполнена конденсатом. Какую дренажную точку открыть первой?",
            "options": [
                ("Нижний ресиверный кран №1", True),
                ("Верхний вантузный клапан", False),
                ("Манометрический штуцер", False),
            ],
        },
        {
            "num_str": "«Вопрос номер два»",
            "text": "Давление в пневмоцилиндрах опускания моста 6 атмосфер, требуется 8. Какой компрессор запустить?",
            "options": [
                ("Аварийный двухступенчатый К-2", True),
                ("Вентилятор продувки", False),
                ("Вакуумный насос ВВН", False),
            ],
        },
        {
            "num_str": "«Вопрос номер три»",
            "text": "Поршень дошёл до упора, но концевой микропереключатель не замкнулся. Что проверить?",
            "options": [
                ("Положение штока и планки концевика", True),
                ("Цепь освещения шахты", False),
                ("Уровень охлаждающей жидкости", False),
            ],
        },
    ],
    # Заход 4: Баланс водохранилища
    [
        {
            "num_str": "«Вопрос номер один»",
            "text": "Уровень воды в верхнем бьефе приближается к гребню плотины. Какую шандору приподнять для безопасного сброса?",
            "options": [
                ("Первую донную шандору", True),
                ("Верхнюю ледозащитную стенку", False),
                ("Глухой шандорный щит", False),
            ],
        },
        {
            "num_str": "«Вопрос номер два»",
            "text": "Образовался донный водоворот у водозаборных решёток. Какое действие стабилизирует поток?",
            "options": [
                ("Притопить плавучий волнолом", True),
                ("Полное закрытие водоприёмника", False),
                ("Форсированный сброс через водослив", False),
            ],
        },
        {
            "num_str": "«Вопрос номер три»",
            "text": "Датчик вибрации плотины фиксирует кавитацию. Какую меру предпринять?",
            "options": [
                ("Подать аэрацию в подзатворное пространство", True),
                ("Ускорить поток воды вдвое", False),
                ("Заблокировать доступ воздуха", False),
            ],
        },
    ],
    # Заход 5: Аварийная автоматика
    [
        {
            "num_str": "«Вопрос номер один»",
            "text": "Код ошибки на индикаторе: 0xEE (залипание пускателя привода моста). Какой контакт разомкнуть вручную?",
            "options": [
                ("Силовой контактор КМ-1", True),
                ("Сигнальную лампу Л-2", False),
                ("Шунтовую перемычку питания", False),
            ],
        },
        {
            "num_str": "«Вопрос номер два»",
            "text": "Сработал термодатчик обмотки главного привода (95°C). Какую систему охлаждения активировать?",
            "options": [
                ("Принудительный обдув шахты", True),
                ("Заливку машинным маслом", False),
                ("Отключение датчика", False),
            ],
        },
        {
            "num_str": "«Вопрос номер три»",
            "text": "Цепь концевых датчиков разомкнута. Какая петля безопасности требует проверки?",
            "options": [
                ("Шлейф контроля провисания тросов", True),
                ("Датчик присутствия оператора", False),
                ("Линия громкой связи", False),
            ],
        },
    ],
    # Заход 6: Смазка и гидропривод
    [
        {
            "num_str": "«Вопрос номер один»",
            "text": "Вязкость масла в гидроцилиндрах повышена из-за холода. Какой режим прогрева включить?",
            "options": [
                ("Маломощный ТЭН масляного бака", True),
                ("Прямой запуск под максимальной нагрузкой", False),
                ("Разбавление речной водой", False),
            ],
        },
        {
            "num_str": "«Вопрос номер два»",
            "text": "Гидрозамок правого цилиндра заблокирован в закрытом положении. Как стравить противодавление?",
            "options": [
                ("Игловой дроссель обратной линии", True),
                ("Ударом по корпусу гидрозамка", False),
                ("Перекрытием напорной трубы", False),
            ],
        },
        {
            "num_str": "«Вопрос номер три»",
            "text": "Уровень рабочей жидкости в баке на нижней отметке. До какого сектора допустимо движение моста?",
            "options": [
                ("До промежуточного горизонтального упора", True),
                ("До крайнего нижнего положения на скорости", False),
                ("Движение категорически запрещено без долива", False),
            ],
        },
    ],
    # Заход 7: Синхронизация опор
    [
        {
            "num_str": "«Вопрос номер один»",
            "text": "Левый пролёт моста опережает правый на 15 градусов. Каким вентилем притормозить левую сторону?",
            "options": [
                ("Дросселем расхода левой магистрали", True),
                ("Общим краном перекрытия", False),
                ("Сбросным клапаном гидробака", False),
            ],
        },
        {
            "num_str": "«Вопрос номер два»",
            "text": "Возник перекос направляющих балок на опоре №3. Какой гидродомкрат синхронизировать?",
            "options": [
                ("Нивелировочный домкрат Д-3", True),
                ("Тяговый трос лебёдки", False),
                ("Амортизатор отбоя", False),
            ],
        },
        {
            "num_str": "«Вопрос номер три»",
            "text": "Угол наклона моста достиг критических 4 градусов к горизонту. Как выровнять платформу?",
            "options": [
                ("Включить следящий гидрораспределитель", True),
                ("Отпустить все тормоза", False),
                ("Застопорить правый трос клином", False),
            ],
        },
    ],
    # Заход 8: Защита от перегрузки
    [
        {
            "num_str": "«Вопрос номер один»",
            "text": "Токовое реле фиксирует перегрузку тягового двигателя на 25%. Какую ступень передачи выбрать?",
            "options": [
                ("Пониженную тяговую ступень (1:40)", True),
                ("Прямую передачу (1:1)", False),
                ("Ускоренную ступень (2:1)", False),
            ],
        },
        {
            "num_str": "«Вопрос номер два»",
            "text": "Противовес застрял в шахте направляющих. Какой трос дать под натяг?",
            "options": [
                ("Вспомогательный канат раскачки", True),
                ("Основной несущий кабель", False),
                ("Трос заземления", False),
            ],
        },
        {
            "num_str": "«Вопрос номер три»",
            "text": "Амперметр показывает бросок тока при трогании моста. Какую пусковую цепь замкнуть?",
            "options": [
                ("Ступень пусковых реостатов", True),
                ("Предохранительную плавкую вставку", False),
                ("Аварийный выключатель", False),
            ],
        },
    ],
    # Заход 9: Финальный посадочный цикл
    [
        {
            "num_str": "«Вопрос номер один»",
            "text": "Мост подошёл к посадочным тумбам противоположного берега на расстояние 0.5 метра. Какой режим опускания активировать?",
            "options": [
                ("Доводка на микроскорости (демпферный режим)", True),
                ("Свободное гравитационное падение", False),
                ("Реверс на полную мощность", False),
            ],
        },
        {
            "num_str": "«Вопрос номер два»",
            "text": "Ригельные замки противоположного берега не вошли в пазы. Какое смещение скорректировать?",
            "options": [
                ("Продольную осевую юстировку платформы", True),
                ("Вертикальный прижимной натяг", False),
                ("Поворот вокруг центральной оси", False),
            ],
        },
        {
            "num_str": "«Вопрос номер три»",
            "text": "Фиксаторы посадки защёлкнулись. Какую команду передать на электромагнитные стопоры?",
            "options": [
                ("Блокировка ригелей в положении ЗАМКНУТО", True),
                ("Обесточить без фиксации", False),
                ("Разжать захваты", False),
            ],
        },
    ],
]


def get_l2_slate_armor_count(game) -> int:
    """Количество надетых сланцевых элементов брони (от 0 до 4)."""
    slate_items = {
        "head": "Сланцевая маска",
        "torso": "Сланцевый панцирь",
        "pants": "Сланцевые поножи",
        "boots": "Сланцевые ботинки",
    }
    return sum(1 for slot, name in slate_items.items() if game.equipment.get(slot) == name)


def get_l2_thorn_damage(slate_count: int) -> int:
    """Урон от терновника: 4/4=26, 3/4=51, 2/4=76, 1/4 и 0/4=101."""
    if slate_count >= 4:
        return 26
    elif slate_count == 3:
        return 51
    elif slate_count == 2:
        return 76
    else:
        return 101


def handle_location_2_ruchey(data: str, game, uid: int):
    """Сюжетная линия Локации 2: Ручей, заросли терновника, плотина и переправа."""
    text = None
    kb = None

    # 1. Вход на локацию
    if data in ("location_enter_2", "river_ferocious", "l2_enter", "l2_thorns_approach"):
        # Если мост уже активирован — спокойный вид переправы
        if game.is_story_flag_set("l2_completed"):
            text = (
                "Ты стоишь у бетонной плотины. Массивный мост надёжно опущен через бурлящий ручей "
                "и заблокирован в ригельных замках.\n\n"
                "Шум чистой горной воды эхом отдаётся в ущелье. Путь в Скромную Лощину открыт."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⛰️ Шагнуть в Скромную Лощину", callback_data="location_enter_3")],
                [InlineKeyboardButton(text="🌲 В Стартовый лес", callback_data="location_enter_1")],
                [InlineKeyboardButton(text="↩️ В лагерь", callback_data="back")],
            ])
            return text, kb

        # Если терновник уже проломан — игрок сразу у плотины
        if game.is_story_flag_set("l2_thorns_cleared"):
            if game.is_story_flag_set("l2_fuse_inserted"):
                return handle_location_2_ruchey("l2_puzzle_start", game, uid)
            elif game.is_story_flag_set("l2_panel_blown"):
                return handle_location_2_ruchey("l2_fusebox_inspect", game, uid)
            else:
                return handle_location_2_ruchey("l2_dam_entrance", game, uid)

        # Стена терновника
        game.set_story_flag("l2_thorns_seen", True)
        # Открытие рецептов сланцевой брони строго при встрече с препятствием Стены терновника
        for rec in ("Сланцевая маска", "Сланцевый панцирь", "Сланцевые поножи", "Сланцевые ботинки"):
            if rec not in getattr(game, "unlocked_crafts", []):
                game.unlocked_crafts.append(rec)
        slate_count = get_l2_slate_armor_count(game)
        thorn_damage = get_l2_thorn_damage(slate_count)

        desc = (
            "Ручей бурлит и шумит. На противоположной стороне сквозь водяную пыль "
            "проступают серые контуры старой бетонной плотины — единственный путь на тот берег.\n\n"
            "Но весь подход к зданию водосброса намертво заблокирован непроходимой стеной дикого терновника. "
            "Узловатые плети толщиной в руку усеяны острыми, как стальные гвозди, шипами.\n\n"
            f"• 🛡 Защита сланцевой бронёй: {slate_count}/4 ед.\n"
            f"• ⚠️ Ожидаемый урон от шипов: {thorn_damage} HP."
        )

        buttons = []
        if game.hp > thorn_damage:
            buttons.append([InlineKeyboardButton(text="🪨 Проломиться", callback_data="l2_thorns_break")])
        else:
            desc += (
                f"\n\n⛔ Попытка проломиться сейчас будет смертельной! "
                f"Твоё здоровье ({game.hp} HP) не выдержит этих шипов (требуется более {thorn_damage} HP). "
                f"Скрафти недостающую сланцевую броню или восстанови силы."
            )

        buttons.append([InlineKeyboardButton(text="ℹ️ О зарослях", callback_data="l2_thorns_info")])
        buttons.append([InlineKeyboardButton(text="↩️ В лагерь", callback_data="back")])

        text = desc
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # 2. Инфо-окно о зарослях
    elif data == "l2_thorns_info":
        slate_count = get_l2_slate_armor_count(game)
        thorn_damage = get_l2_thorn_damage(slate_count)
        text = (
            "ℹ️ СТЕНА ТЕРНОВНИКА\n\n"
            "Дикие заросли сплелись в плотный колючий вал. Без каменной защиты шипы вспарывают одежду "
            "и глубоко рассекают плоть.\n\n"
            "Защитные свойства полного сланцевого комплекта:\n"
            "• 4/4 предмета (Маска, Панцирь, Поножи, Ботинки): 26 HP урона.\n"
            "• 3/4 предмета: 51 HP урона.\n"
            "• 2/4 предмета: 76 HP урона.\n"
            "• 1/4 или 0/4 предметов: 101 HP урона (верная гибель!).\n\n"
            "Сланцевые пластины можно найти по берегам ручья, а кору, мох и ветки — в лесу."
        )
        buttons = []
        if game.hp > thorn_damage:
            buttons.append([InlineKeyboardButton(text="🪨 Проломиться", callback_data="l2_thorns_break")])
        buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="l2_thorns_approach")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # 3. Прорыв сквозь терновник
    elif data == "l2_thorns_break":
        if game.is_story_flag_set("l2_thorns_cleared"):
            text = (
                "Ты стоишь на бетонной площадке плотины у проломанного прохода.\n"
                "Тропинка через колючки свободна — больше прорываться не придётся!"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚪 Войти в здание водосброса", callback_data="l2_dam_entrance")]
            ])
            return text, kb

        slate_count = get_l2_slate_armor_count(game)
        thorn_damage = get_l2_thorn_damage(slate_count)

        if game.hp <= thorn_damage:
            return handle_location_2_ruchey("l2_thorns_approach", game, uid)

        game.hp -= thorn_damage

        mask_broke = False
        if game.equipment.get("head") == "Сланцевая маска":
            game.equipment["head"] = "Пусто"
            mask_broke = True

        boots_broke = False
        if game.equipment.get("boots") == "Сланцевые ботинки":
            game.equipment["boots"] = "Отремонтированные ботинки"
            boots_broke = True

        game.set_story_flag("l2_thorns_cleared", True)
        game.adjust_narrative_karma("intervention", 3)

        break_lines = [
            "Стиснув зубы, ты с разбегу бросаешься в колючую стену!",
            "Сучья яростно трещат, шипы с противным скрежетом полосуют сланцевые пластины..."
        ]

        if mask_broke:
            break_lines.append("• Раздаётся треск: Сланцевая маска раскалывается от удара и осыпается осколками!")
        if boots_broke:
            break_lines.append("• Узловатые корни срывают каменные щитки со сланцевых ботинок, превращая их в Отремонтированные ботинки!")
        if slate_count < 4:
            break_lines.append("• Открытые участки тела покрываются глубокими ноющими царапинами.")

        break_lines.append(
            f"\nТы получаешь {thorn_damage} ед. урона (осталось {game.hp} HP) и вываливаешься на бетонную площадку плотины.\n"
            "За тобой осталась отчётливая широкая полоса проломанных ветвей — тропинка свободна, "
            "больше прорываться через колючки не придётся!"
        )

        text = "\n".join(break_lines)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚪 Войти в здание водосброса", callback_data="l2_dam_entrance")]
        ])

    # 4. Вход в здание водосброса
    elif data in ("l2_dam_entrance", "l2_dam_inside"):
        text = (
            "Тяжёлая железная дверь водосброса со скрипом поддаётся.\n\n"
            "Внутри царит сырой полумрак, гулко капает вода, пахнет тиной и машинным маслом. "
            "Следы запустения копились десятилетиями. Но прямо перед тобой на массивном металлическом пульте "
            "тускло помигивает красная лампочка.\n\n"
            "«Откуда здесь ток?.. Наверное, я этого не узнаю никогда...»"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🕹 Подойти к пульту", callback_data="l2_panel_inspect")],
            [InlineKeyboardButton(text="↩️ В лагерь", callback_data="back")],
        ])

    # 5. Попытка включения и Взрыв щитка
    elif data == "l2_panel_inspect":
        game.set_story_flag("l2_panel_blown", True)

        has_pet = (
            getattr(game, "companion_name", None)
            or getattr(game, "story_flags", {}).get("has_pet")
            or (game.equipment.get("pet") and game.equipment.get("pet") != "Пусто")
        )

        pet_txt = ""
        if has_pet:
            game.hp = max(0, game.hp - 2)
            if game.hp <= 0:
                game.hp = 0
                game.active_story_callback = None
                return get_death_text(game, "🐾 В панике перепуганный котёнок нанёс смертельные раны."), get_death_kb()
            pet_txt = "\n\n🐾 Перепуганный котёнок в панике царапает твои рёбра (−2 HP), истошно шипит и растворяется в темноте зала!"

        text = (
            "Ты подходишь к пульту и решительно тянешь карболитовый рычаг на себя.\n\n"
            "БА-БАХ!\n\n"
            "Оглушительный взрыв силового шкафа сотрясает здание! Сноп ослепительных искр и клуб едкого дыма "
            "ударяют в потолок. Взрывной волной тебя отбрасывает на спину на мокрый бетонный пол.\n"
            "От удара из кармана рюкзака со звоном выпадает Плоская металлическая коробочка."
            f"{pet_txt}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Осмотреть искрящийся шкаф", callback_data="l2_fusebox_inspect")]
        ])

    # 6. Искрящийся шкаф
    elif data == "l2_fusebox_inspect":
        has_pet = (
            getattr(game, "companion_name", None)
            or getattr(game, "story_flags", {}).get("has_pet")
            or (game.equipment.get("pet") and game.equipment.get("pet") != "Пусто")
        )

        pet_glove_txt = ""
        buttons = []

        if has_pet:
            pet_glove_txt = (
                "\n\nИз-под перевёрнутого стеллажа блестят два круглых кошачьих глаза. "
                "Котёнок осторожно подталкивает лапкой к твоим ногам старую истлевшую диэлектрическую перчатку."
            )
            buttons.append([InlineKeyboardButton(text="🧤 Вставить через перчатку", callback_data="l2_fuse_safe")])

        buttons.append([InlineKeyboardButton(text="✋ Вставить голыми руками", callback_data="l2_fuse_shock")])
        buttons.append([InlineKeyboardButton(text="↩️ В лагерь", callback_data="back")])

        text = (
            "Поднявшись на ноги, ты поднимаешь металлическую коробочку и подходишь к распахнутому, яростно искрящему щитку.\n"
            "Гнездо сгоревшего предохранителя в точности совпадает с её габаритами.\n\n"
            "«Ты уже знаешь, что сюда вставишь»."
            f"{pet_glove_txt}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # 7. Установка коробочки: безопасно или голыми руками
    elif data in ("l2_fuse_safe", "l2_fuse_shock"):
        game.inventory.pop("Плоская металлическая коробочка", None)
        game.set_story_flag("l2_fuse_inserted", True)

        if data == "l2_fuse_shock":
            game.adjust_narrative_karma("intervention", 1)
            game.hp = max(0, game.hp - 10)
            if game.hp <= 0:
                game.hp = 0
                game.active_story_callback = None
                return get_death_text(game, "⚡ Мощный электрический разряд пробил сердце."), get_death_kb()
            shock_text = (
                "Ты берёшь коробочку пальцами и с силой вжимаешь её в искрящий разъём!\n\n"
                "Яркая дуга с треском бьёт в пальцы! Мощный разряд тока прошибает всё тело (−10 HP)!\n"
                "Тебя отшвыривает назад, в воздухе пахнет палёной кожей, но коробочка с шипением намертво приварилась к клеммам."
            )
        else:
            game.adjust_narrative_karma("observation", 1)
            shock_text = (
                "Натянув толстую резиновую перчатку, ты аккуратно вставляешь металлическую коробочку в силовой слот.\n\n"
                "Вспыхивает дуговой разряд! Перчатка обугливается, спасая тебя от удара током.\n"
                "Коробочка со щелчком встаёт в паз и намертво приваривается к клеммам."
            )

        text = (
            f"{shock_text}\n\n"
            "В глубине машинного зала оживают мощные контакторы. Загудел трансформатор.\n"
            "Над пультом наливается тусклым зелёным свечением старый выпуклый экран."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📟 Взглянуть на экран", callback_data="l2_puzzle_start")]
        ])

    # 8. Заросшее табло и загадки
    elif data == "l2_puzzle_start":
        attempt = getattr(game, "l2_puzzle_attempt", 0) % 10
        step = getattr(game, "l2_puzzle_step", 1)
        if step not in (1, 2, 3):
            step = 1
            game.l2_puzzle_step = 1

        q_data = L2_PUZZLE_BANK[attempt][step - 1]

        text = (
            "📟 ТЕРМИНАЛ УПРАВЛЕНИЯ ПЛОТИНОЙ\n\n"
            "Экран покрыт жирным слоем вековой пыли, в пазы корпуса врос зелёный мох, а по углам колышется паутина.\n"
            "Сквозь стекло мерцают строгие зелёные строки символов.\n\n"
            "Надпись на табло:\n"
            f"{q_data['num_str']}\n"
            f"{q_data['text']}"
        )

        buttons = []
        for idx, (opt_text, is_corr) in enumerate(q_data["options"]):
            buttons.append([InlineKeyboardButton(text=opt_text, callback_data=f"l2_p_ans:{attempt}:{step}:{idx}")])
        buttons.append([InlineKeyboardButton(text="↩️ В лагерь", callback_data="back")])

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # 9. Обработка ответа на загадку
    elif data.startswith("l2_p_ans:"):
        parts = data.split(":")
        attempt = int(parts[1])
        step = int(parts[2])
        idx = int(parts[3])

        is_correct = L2_PUZZLE_BANK[attempt][step - 1]["options"][idx][1]

        if is_correct:
            if step == 1:
                game.l2_puzzle_step = 2
                return handle_location_2_ruchey("l2_puzzle_start", game, uid)
            elif step == 2:
                game.l2_puzzle_step = 3
                return handle_location_2_ruchey("l2_puzzle_start", game, uid)
            else:
                return handle_location_2_ruchey("l2_bridge_activated", game, uid)
        else:
            # Ошибка: ледяная струя под давлением срывает заглушку
            game.hp = max(0, game.hp - 5)
            game.ap = 0
            game.l2_puzzle_attempt = (attempt + 1) % 10
            game.l2_puzzle_step = 1

            if game.hp <= 0:
                game.hp = 0
                game.active_story_callback = None
                return get_death_text(game, "🌊 Ледяной гидравлический удар сбил тебя с ног и унёс жизнь."), get_death_kb()

            text = (
                "⚠️ ОШИБКА АВТОМАТИКИ!\n\n"
                "Где-то под полом раздаётся глухой гидравлический удар...\n"
                "Ледяная струя воды под чудовищным давлением со свистом срывает старую заглушку трубы и сбивает тебя с ног!\n\n"
                "Сильный ушиб отбросил тебя на метр (−5 HP), а ледяная вода промочила одежду до последней нитки.\n"
                "Дрожа от пронизывающего холода, ты понимаешь: сегодня ты больше не в силах продолжать...\n\n"
                "(⚡ AP истощено до 0. Отдохни в лагере и наберись сил перед новой попыткой)."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏕 В лагерь", callback_data="back")]
            ])

    # 10. Финал переправы: мост опущен
    elif data == "l2_bridge_activated":
        game.inventory.pop("Записка с наброском местности", None)
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Скромная Лощина" not in unlocked:
            unlocked.append("Скромная Лощина")
            game.unlocked_locations = unlocked
        game.set_story_flag("l2_completed", True)

        # Карма за решение логических задач терминала плотины
        if not game.is_story_flag_set("l2_bridge_karma_awarded"):
            game.set_story_flag("l2_bridge_karma_awarded")
            if getattr(game, "l2_puzzle_attempt", 0) <= 1:
                game.adjust_narrative_karma("observation", 2)

        text = (
            "Раздаётся оглушительный лязг многотонных противовесов. "
            "Многолетняя ржавчина осыпается бурыми хлопьями, когда тяжёлые шестерни приходят в движение.\n\n"
            "Массивная плита технологического моста водосброса со скрипом опускается через бурлящий ручей, "
            "намертво блокируясь в противоположных замках.\n\n"
            "Переправа готова. Бурные потоки ручья пенятся глубоко внизу, а впереди открывается проход к Скромной Лощине."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛰️ Шагнуть в Скромную Лощину", callback_data="location_enter_3")]
        ])

    if kb == get_main_kb(game) or data in ("ruchey_leave", "l2_camp", "back") or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        game.active_story_callback = data

    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 3: СКРОМНАЯ ЛОЩИНА
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_3_slate_hollow(data: str, game, uid: int):
    """Сюжетная линия Локации 3: Скромная Лощина, убежище у сланцевой печи и каменная плита."""
    text = None
    kb = None

    if data in ("location_enter_boar",):
        game.reset_nav()
        game.current_location = "Скромная Лощина"
        return handle_location_3_slate_hollow("l3_8_ridge", game, uid)

    if data in ("location_enter_3", "slate_hollow_start"):
        game.reset_nav()
        game.current_location = "Скромная Лощина"
        if game.is_story_flag_set("l3_shelter_unlocked"):
            if not game.is_story_flag_set("l3_ridge_completed"):
                text = (
                    "Ты стоишь под сланцевым навесом у печи. Впереди крутой подъём на гребень — "
                    "единственный путь дальше на Просеку."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🐗 Разведать подъём (⚠️)", callback_data="l3_7_morning")],
                    [InlineKeyboardButton(text="🏕 В лагерь к печи", callback_data="back")],
                ])
            else:
                text = (
                    "Ты стоишь в глубине Скромной Лощины под надёжным сланцевым навесом.\n"
                    "В каменной печи потрескивает огонь, укрытый от непогоды, а на плите виднеются записи путников.\n\n"
                    "Что будешь делать?"
                )
                kb = get_main_kb(game)
        else:
            text = (
                "Ты перешагиваешь порог Скромной Лощины. Воздух здесь плотный, прохладный,\n"
                "запах влажного камня и древней глины. Стены выложены из ровных пластов тёмного сланца.\n\n"
                "Лощина тянется далеко вперёд, уводя вглубь каменистого ущелья."
            )
            kb = get_main_kb(game)

    elif data == "l3_1_fire_low":
        game.story_state = "l3_1"
        text = (
            "Ты спускаешься в неглубокую лощину.\n"
            "Ветер остаётся наверху. Здесь слышно только, как вода с редкими щелчками падает с каменного выступа.\n"
            "Стены сложены из ровных пластов серого сланца. Между ними темнеет влажная глина. "
            "На одном из камней отпечатался тонкий лист — с таким чётким стеблем, будто его прижали сюда вчера.\n\n"
            "Под нависающей плитой что-то мерцает.\n"
            "Ты подходишь ближе.\n"
            "Небольшая печь сложена прямо у стены. В её глубине тлеют угли. Над ними дрожит воздух.\n"
            "Рядом стоит пустая кружка. Она лежит на боку, ручкой к выходу."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗣 Позвать хозяина", callback_data="l3_2_call")],
            [InlineKeyboardButton(text="🔍 Осмотреть убежище", callback_data="l3_3_inspect")],
        ])

    elif data == "l3_2_call":
        game.story_state = "l3_2"
        text = (
            "— Здесь кто-нибудь есть?\n\n"
            "Голос звучит неожиданно громко. Ты ждёшь.\n"
            "С каменного выступа срывается капля. Потом ещё одна.\n"
            "Никто не отвечает.\n\n"
            "Ты замечаешь возле печи гладкую плитку с нацарапанными словами. "
            "Нижний край вдавлен в глину, чтобы она стояла вертикально:\n"
            "«Если пришёл — грейся.\n"
            "Если взял — оставь для следующего»."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l3_3_inspect")]
        ])

    elif data == "l3_3_inspect":
        game.story_state = "l3_3"
        text = (
            "Под каменным навесом достаточно места, чтобы лечь, не сворачиваясь клубком.\n"
            "Земля выровнена. В щелях стены аккуратно размазана глина. "
            "Возле печи сложены две длинные деревянные лопатки, почерневшие на концах.\n\n"
            "Здесь не просто пережидали дождь. Кто-то старался сделать так, чтобы можно было остаться.\n"
            "На стене, чуть выше пола, видны короткие надписи:\n"
            "«Крыша течёт справа».\n"
            "Ниже, другим почерком:\n"
            "«Уже нет».\n\n"
            "Ты проводишь взглядом по заделанной щели. Глина в ней отличается по цвету от остальной стены."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧱 Осмотреть печь", callback_data="l3_5_stove")],
            [InlineKeyboardButton(text="📜 Посмотреть остальные надписи", callback_data="l3_4_writings")],
        ])

    elif data == "l3_4_writings":
        game.story_state = "l3_4"
        game.adjust_narrative_karma("observation", 1)
        text = (
            "Большую часть надписей трудно разобрать. Одни процарапаны острым камнем, другие проведены пальцем по ещё мягкой глине.\n\n"
            "«Не пей из лужи у выхода».\n"
            "«В печи тяга плохая. Заднюю щель не закрывать».\n"
            "«Спасибо за сухое место».\n\n"
            "Последняя надпись находится совсем низко:\n"
            "«Я думал, здесь никого больше нет».\n"
            "Под ней — несколько коротких чёрточек. Ты сначала принимаешь их за счёт дней. Потом замечаешь возле одной:\n"
            "«Я тоже».\n\n"
            "👁️ Наблюдательность: ты запомнил совет о тяге в печи."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧱 К печи ➔", callback_data="l3_5_stove")]
        ])

    elif data == "l3_5_stove":
        game.story_state = "l3_5"
        text = (
            "На двух каменных опорах внутри печи лежит плоская заготовка.\n"
            "По краям она уже стала тёмной и плотной, но середина ещё светлее.\n"
            "Рядом на стенке нацарапана простая последовательность рисунков:\n"
            "глина ➔ плоская форма ➔ печь ➔ готовая пластина.\n"
            "Под последним рисунком написано: «Не спеши вынимать».\n\n"
            "Топлива в очаге осталось немного, но под каменным козырьком припрятаны сухие щепки.\n"
            "Теперь это укрытие станет твоим новым домом. С такой печью здесь можно пережить любые холода. "
            "Осталось лишь решить, что сделать с первой заготовкой."
        )
        flask = int(getattr(game, "flask_water", 0) or 0)
        has_water = flask >= 2 or game.inventory.get("Вода", 0) >= 2 or game.inventory.get("Бутылка воды", 0) >= 1

        buttons = [
            [InlineKeyboardButton(text="🔥 Закончить обжиг", callback_data="l3_5_finish_bake")],
        ]
        if has_water:
            buttons.append([InlineKeyboardButton(text="💧 Погасить печь и забрать глину", callback_data="l3_5_take_clay")])
        buttons.append([InlineKeyboardButton(text="✋ Оставить заготовку на месте", callback_data="l3_6_stay")])

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l3_5_finish_bake":
        game.inventory["Сланцевый слиток"] = game.inventory.get("Сланцевый слиток", 0) + 1
        game.adjust_narrative_karma("pragmatism", 2)
        text = (
            "Ты подкладываешь сухих щепок под заготовку. Огонь разгорается ярче, жар охватывает форму со всех сторон.\n\n"
            "Спустя время раскалённый брусок остывает, превращаясь в крепкий, закалённый Сланцевый слиток!\n\n"
            "📦 Получено: Сланцевый слиток ×1"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l3_6_stay")]
        ])

    elif data == "l3_5_take_clay":
        flask = int(getattr(game, "flask_water", 0) or 0)
        if flask >= 2:
            game.flask_water = max(0, flask - 2)
        elif game.inventory.get("Вода", 0) >= 2:
            game.inventory["Вода"] -= 2
        game.inventory["Глина"] = game.inventory.get("Глина", 0) + 1
        game.adjust_narrative_karma("compassion", 1)
        text = (
            "Ты аккуратно плещешь водой на угли. С шипением поднимается пар, остужая заготовку.\n\n"
            "Ты вынимаешь сырую глину из формы, скатывая её в плотный комок.\n\n"
            "📦 Получено: Глина ×1"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l3_6_stay")]
        ])

    elif data == "l3_6_stay":
        game.story_state = "l3_6"
        text = (
            "Ты оглядываешь сухое каменное укрытие.\n"
            "Печь сложена на совесть, стены защищают от сквозняков, а над головой — надёжный сланцевый навес.\n\n"
            "«Тот, кто растопил эту печь и оставил заготовку, явно вернётся сюда. Или хотя бы проходил совсем недавно... "
            "Торопиться некуда. Надо обжиться на этом месте и дождаться хозяина».\n\n"
            "Возле печи в глину вдавлена каменная плита: «Если пришёл — грейся. Если взял — оставь для следующего».\n"
            "Рядом чернеет пустая форма для новой заготовки."
        )
        buttons = []
        if game.inventory.get("Глина", 0) >= 1:
            buttons.append([InlineKeyboardButton(text="🤲 Оставить глину для следующего", callback_data="l3_6_leave_clay")])
        buttons.append([InlineKeyboardButton(text="✏️ Оставить предупреждение", callback_data="l3_6_warning")])
        buttons.append([InlineKeyboardButton(text="🚶 Уйти", callback_data="l3_7_morning")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l3_6_leave_clay":
        if game.inventory.get("Глина", 0) >= 1:
            game.inventory["Глина"] -= 1
            if game.inventory["Глина"] <= 0:
                del game.inventory["Глина"]
        game.adjust_narrative_karma("compassion", 2)
        game.set_story_flag("left_clay_for_next", True)
        text = (
            "Ты кладёшь кусок чистой глины в пустую каменную форму у печи.\n"
            "Пусть следующий путник тоже найдёт здесь то, что согреет его и поможет выжить.\n\n"
            "🤲 Отдано: Глина ×1 (+2 Сострадание)"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚶 Уйти", callback_data="l3_7_morning")]
        ])

    elif data == "l3_6_warning":
        game.adjust_narrative_karma("compassion", 1)
        try:
            from services.database import save_tablet_note
            save_tablet_note(uid, "Путник", "Не закрывай заднюю щель печи. За каменным выступом сухо, здесь можно спать.")
        except Exception:
            pass
        text = (
            "Ты подбираешь острый камень и высекаешь на плите слова:\n\n"
            "«Не закрывай заднюю щель печи. За каменным выступом сухо, здесь можно спать».\n\n"
            "Пыль осыпается под пальцами. Твоя надпись добавлена на каменную плиту у печи."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚶 Уйти", callback_data="l3_7_morning")]
        ])

    elif data == "l3_6_finalize":
        game.set_story_flag("l3_shelter_unlocked", True)
        game.set_story_flag("has_stove", True)
        game.campfire_active = True
        game.campfire_durability = max(int(getattr(game, "campfire_durability", 0) or 0), 15)
        game.story_state = None
        game.reset_nav()
        game.add_log("🧱 Ты вернулся в лагерь у каменной печи.")
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "l3_7_morning":
        game.story_state = "l3_7"
        game.set_story_flag("l3_shelter_unlocked", True)
        game.set_story_flag("has_stove", True)
        game.campfire_active = True
        game.campfire_durability = max(int(getattr(game, "campfire_durability", 0) or 0), 15)
        text = (
            "Перед подъёмом ты позволяешь себе немного посидеть под навесом.\n"
            "Камень за спиной ещё хранит тепло. Ты смотришь на чужие надписи, на почерневшие лопатки, на аккуратно заделанную щель в крыше.\n\n"
            "Люди, которые сделали всё это, могли никогда не встречаться. Один нашёл сухое место. Другой сложил печь. Теперь здесь осталось что-то и от тебя."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l3_8_ridge")]
        ])

    elif data == "l3_8_ridge":
        game.story_state = "l3_8"
        text = (
            "Ты просыпаешься от глухой вибрации земли. Из дальней горловины ущелья доносится хриплый храп и треск корней.\n\n"
            "У солонца кормится бурая громада — матёрый Секач с клыками в ладонь. Он жадно вгрызается в соль на тропе. Справа над обрывом вьётся узкая тропа, где свистит ледяной ветер со сланцевой крошкой."
        )
        buttons = []
        if getattr(game, "is_full_slate_set_equipped", lambda: False)():
            buttons.append([InlineKeyboardButton(text="⚔️ Атаковать зверя", callback_data="l3_10_armored")])
            buttons.append([InlineKeyboardButton(text="🧗 Лезть в обход", callback_data="l3_11b_cliff")])
        else:
            buttons.append([InlineKeyboardButton(text="⚔️ Атаковать зверя", callback_data="l3_9a_charge")])
            buttons.append([InlineKeyboardButton(text="🧗 Лезть в обход", callback_data="l3_9b_ridge")])
        buttons.append([InlineKeyboardButton(text="🏕 В лагерь", callback_data="back")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l3_9a_charge":
        game.story_state = "l3_9a"
        damage = 30
        game.hp = max(1, getattr(game, "hp", 100) - damage)
        game.add_log(f"💥 Секач сбил тебя тараном! −{damage} HP.")
        text = (
            "Ты делаешь шаг вперёд, но Секач мгновенно срывается с места и сносит тебя бешеным ударом!\n\n"
            "Потасканная одежда не защищает от клыков — туша впечатывает тебя в каменные плиты (−30 HP). "
            "Чудом вывернувшись, ты на четвереньках отползаешь назад за спасительный каменный уступ."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏃 Отступить", callback_data="l3_9_camp")]
        ])

    elif data == "l3_9b_ridge":
        game.story_state = "l3_9b"
        damage = 25
        game.hp = max(1, getattr(game, "hp", 100) - damage)
        game.add_log(f"⚠️ Срыв с узкой тропы! −{damage} HP.")
        text = (
            "Ты пробуешь карабкаться по узкой тропе над обрывом. Острые сланцевые грани безжалостно режут ладони и распарывают штанины. "
            "Камень крошится под ногой, и ты срываешься вниз на острый щебень (−25 HP)!\n\n"
            "Без крепких наколенников, защитных поножей и обуви по этим бритвенным камням не подняться."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏃 Отступить", callback_data="l3_9_camp")]
        ])

    elif data == "l3_9_camp":
        game.story_state = None
        game.reset_nav()
        for rec in ("Сланцевая маска", "Сланцевый панцирь", "Сланцевые поножи", "Сланцевые ботинки", "Окованный посох"):
            if hasattr(game, "unlock_craft"):
                game.unlock_craft(rec)
            elif rec not in getattr(game, "unlocked_crafts", []):
                game.unlocked_crafts.append(rec)

        unlocked_locs = getattr(game, "unlocked_locations", []) or []
        if "Солонец (Секач)" not in unlocked_locs:
            if hasattr(game, "unlocked_locations"):
                game.unlocked_locations.append("Солонец (Секач)")

        game.add_log("🔨 Открыты новые рецепты: Сланцевая броня и Окованный посох.")
        game.add_log("📍 Открыта локация: Солонец (Секач).")
        text = (
            "Ты возвращаешься к каменному козырьку, тяжело дыша и зажимая свежие раны.\n\n"
            "Слова из свитка сбылись: не лезь в лоб без крепкого щита, а на узкую тропу над обрывом без надёжных поножей и обуви не залезть — скала изрежет до костей.\n\n"
            "Обычный деревянный посох зверь переломит пополам — его нужно оковать железом и сланцем. А из тяжёлых сланцевых слитков предстоит выковать монолитный доспех.\n\n"
            "🔨 Открыты новые рецепты: Сланцевая броня и Окованный посох.\n"
            "📍 Открыта локация: Солонец (Секач)."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 В лагерь", callback_data="back")]
        ])

    elif data == "l3_10_armored":
        game.story_state = "l3_10"
        text = (
            "Тёмная сланцевая броня отливает холодным матовым блеском. "
            "Массивный панцирь и щитки, выкованные из сланцевых слитков, глухо звенят, надёжно закрывая корпус и ноги. "
            "Окованный посох уверенно лежит в ладони.\n\n"
            "Впереди всё так же кормится Секач у солонца, а над ним вьётся узкая тропа в обход скалы. Теперь ты готов ко всему."
        )
        buttons = [
            [InlineKeyboardButton(text="⚔️ Атаковать зверя", callback_data="l3_11a_start")],
            [InlineKeyboardButton(text="🧗 Лезть в обход", callback_data="l3_11b_cliff")],
            [InlineKeyboardButton(text="🏕 В лагерь", callback_data="back")],
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l3_11a_start":
        game.story_state = "l3_11a_start"
        text = (
            "Ты уверенно выходишь на солонец навстречу зверю.\n\n"
            "Секач вскидывает массивную клыкастую голову, глухо ревёт и бьёт копытом о каменную плиту, готовясь к атаке. Время обнажить оружие!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Сражаться!", callback_data="l3_start_boar_battle")]
        ])

    elif data in ("l3_start_boar_battle", "boar_battle_screen"):
        battle = getattr(game, "wolf_battle", None)
        if data == "l3_start_boar_battle" or not battle:
            return start_battle(game, "ancient_boar")
        cur_enemy = battle.get("enemy_id", "ancient_boar")
        return get_battle_text(game, cur_enemy), get_battle_kb(game, cur_enemy)

    elif data.startswith("boar_battle_"):
        return apply_action(data, game, "ancient_boar")

    elif data == "l3_11a_win":
        game.wolf_battle = None
        game.story_state = "l3_11a"
        if not game.is_story_flag_set("boar_killed"):
            game.kills_count = getattr(game, "kills_count", 0) + 1
        game.set_story_flag("boar_killed", True)
        game.adjust_narrative_karma("compassion", -1)
        game.adjust_narrative_karma("pragmatism", 3)
        game.adjust_narrative_karma("intervention", 3)
        text = (
            "Секач повержен. Громадная туша рухнула на серые плиты у солонца, взметнув сухую пыль, и затихла.\n\n"
            "Подъём наверх свободен. Впереди, на границе ущелья, уже видны светлые стволы осиновой рощи."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔪 Собрать лут", callback_data="l3_12a_loot")]
        ])

    elif data == "l3_12a_loot":
        game.story_state = "l3_12a"
        game.set_story_flag("l3_ridge_completed", True)
        game.inventory["Мясо"] = game.inventory.get("Мясо", 0) + 4
        game.inventory["Кожа"] = game.inventory.get("Кожа", 0) + 2
        game.inventory["Кость"] = game.inventory.get("Кость", 0) + 2

        text = (
            "Секач повержен. Острым сколом ты быстро разделываешь тушу и забираешь ценную добычу:\n\n"
            "📦 Получено:\n"
            "🥩 Мясо ×4\n"
            "🪢 Кожа ×2\n"
            "🦴 Кость ×2"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l3_13_boundary")]
        ])

    elif data == "l3_11b_cliff":
        game.story_state = "l3_11b"
        if not game.is_story_flag_set("boar_bypassed"):
            game.spared_souls = getattr(game, "spared_souls", 0) + 1
        game.set_story_flag("boar_bypassed", True)
        game.adjust_narrative_karma("observation", 2)
        game.adjust_narrative_karma("pragmatism", 2)
        cliff_dmg = 5
        game.hp = max(1, getattr(game, "hp", 100) - cliff_dmg)
        game.add_log(f"⚠️ Острые щепки тропы: −{cliff_dmg} HP.")
        text = (
            "Ты осторожно ступаешь на узкую тропу над солонцом. Кабан кормится внизу и тебя не замечает.\n\n"
            "Острые сланцевые щепки летят из-под ног, секут руки и сочленения доспеха (−5 HP)."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l3_12_cache")]
        ])

    elif data == "l3_12_cache":
        game.story_state = "l3_12"
        slip_dmg = 5
        game.hp = max(1, getattr(game, "hp", 100) - slip_dmg)
        game.add_log(f"⚠️ Срыв на узкой тропе: −{slip_dmg} HP.")
        text = (
            "Внезапно под ногой на узкой тропе обламывается пласт породы! Ты срываешься вниз, чудом успев ухватиться за выступ одной рукой. "
            "Ноги повисают в пустоте, острый камень обдирает пальцы (−5 HP)!\n\n"
            "Отчаянно шаря рукой по отвесной стене, пальцы ухватываются за край глубокой расселины. "
            "Ты подтягиваешься и заглядываешь внутрь — в породе скрыта тайная ниша, оставленная охотником.\n\n"
            "Внутри лежат сушёное мясо, полосы кожи и крепкие кости."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎒 Взять припасы", callback_data="l3_12_taken")],
        ])

    elif data == "l3_12_taken":
        game.inventory["Мясо"] = game.inventory.get("Мясо", 0) + 4
        game.inventory["Кожа"] = game.inventory.get("Кожа", 0) + 2
        game.inventory["Кость"] = game.inventory.get("Кость", 0) + 2
        text = (
            "Ты перекладываешь припасы в мешок (+4 Мясо, +2 Кожа, +2 Кость).\n\n"
            "На плоском камне в глубине ниши выбиты слова:\n"
            "«Если взял — оставь для следующего»."
        )
        buttons = []
        has_food = game.inventory.get("Ягоды", 0) > 0 or game.inventory.get("Грибы", 0) > 0 or game.inventory.get("Мясо", 0) > 1
        if has_food:
            buttons.append([InlineKeyboardButton(text="🤲 Что-нибудь положить", callback_data="l3_13_kind")])
        buttons.append([InlineKeyboardButton(text="🚶 Уйти", callback_data="l3_13_greed")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l3_13_kind":
        game.story_state = "l3_13"
        game.set_story_flag("l3_ridge_completed", True)
        game.adjust_narrative_karma("compassion", 2)
        if game.inventory.get("Ягоды", 0) > 0:
            game.inventory["Ягоды"] -= 1
            if game.inventory["Ягоды"] <= 0:
                del game.inventory["Ягоды"]
        elif game.inventory.get("Мясо", 0) > 0:
            game.inventory["Мясо"] -= 1

        text = (
            "Ты аккуратно складываешь в нишу часть своих припасов и закрываешь отверстие каменным диском.\n\n"
            "Долг перед тем, кто шёл впереди, закрыт (+2 Сострадание)."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l3_13_boundary")]
        ])

    elif data == "l3_13_greed":
        game.story_state = "l3_13"
        game.set_story_flag("l3_ridge_completed", True)
        game.adjust_narrative_karma("pragmatism", 2)
        text = (
            "В глуши выживает тот, кто берёт всё и не оглядывается (+2 Прагматизм).\n\n"
            "Ты оставляешь каменную нишу пустой и даже не закрываешь вход камнем."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l3_13_boundary")]
        ])

    elif data == "l3_13_boundary":
        game.set_story_flag("l3_ridge_completed", True)
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Просека Охотников" not in unlocked:
            unlocked.append("Просека Охотников")
            game.unlocked_locations = unlocked
        game.add_log("🗺️ Открыта новая локация: Просека Охотников.")
        text = (
            "По сланцевым выступам ты поднимаешься к краю лощины.\n"
            "Отсюда видна полоса более редкого леса. Между стволами что-то светлеет.\n\n"
            "С ветки свисает тонкий шнур. На его конце медленно поворачивается маленькая костяная пластинка. "
            "Чуть дальше висит ещё одна. Кто-то отмечал дорогу. Или границу."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌲 Шагнуть на Просеку", callback_data="location_enter_4")]
        ])

    elif data == "l3_flee_to_camp":
        game.wolf_battle = None
        game.story_state = None
        text = (
            "Ты отпрыгиваешь назад, скатываешься по осыпи и укрываешься в лагере под навесом.\n\n"
            "Секач шумно сопит у солонца, не преследуя тебя дальше."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 В лагерь", callback_data="back")]
        ])

    # Старые коллбэки для обратной совместимости
    elif data == "slate_examine":
        game.adjust_narrative_karma("observation", 3)
        text = (
            "Ты осматриваешь стены — сланец холодный на ощупь, с тонкими прожилками.\n"
            "Сланцевая Лощина — место, где камень живёт своей жизнью."
        )
        kb = get_main_kb(game)
    elif data == "slate_climb":
        game.adjust_narrative_karma("intervention", 2)
        text = "Ты взбираешься по ступеням, ведущим к верхней палате."
        kb = get_main_kb(game)
    elif data == "slate_rest":
        game.adjust_narrative_karma("compassion", 1)
        text = "Ты отдыхаешь на прохладном сланце."
        kb = get_main_kb(game)
    elif data == "slate_end":
        game.story_state = None
        kb = get_main_kb(game)

    if kb == get_main_kb(game) or data in ("l3_6_finalize", "l3_11a_win", "l3_13_kind", "l3_13_greed", "l3_flee_to_camp", "slate_end", "back") or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        game.active_story_callback = data

    return text, kb


SLUG_ACTIONS = [
    ("smell", "👃 Понюхать"),
    ("lick", "👅 Облизать"),
    ("eat", "🍽️ Съесть"),
    ("cross", "✝️ Перекрестить"),
    ("throw", "🤾 Бросить в слизня"),
    ("wave", "🪄 Помахать перед слизнем"),
    ("talk", "🗣️ Заговорить с грибом"),
    ("squeeze", "🤏 Раздавить пальцами"),
    ("step", "🥾 Наступить сапогом"),
    ("friend", "🎁 Предложить слизню дружбу"),
]


def _render_slug_battle(game):
    """Отрисовка экрана боя со слизнем."""
    b = getattr(game, "slug_battle", None) or {}
    slug_hp = b.get("slug_hp", 30)
    slug_max_hp = b.get("slug_max_hp", 30)
    last_log = b.get("last_log", "⚠️ Слизень прыгает на тебя! Приготовься к бою!")
    coated = b.get("coated", False)
    inspected = b.get("inspected", False)
    tested = list(b.get("actions_tested", []))
    attacks_count = b.get("attacks_count", 0)

    hp_filled = max(0, min(10, int((slug_hp / slug_max_hp) * 10)))
    bar = "█" * hp_filled + "░" * (10 - hp_filled)

    regen_text = "Особенность: Оболочка разрушена!" if coated else "Особенность: Студенистая регенерация (+1 HP/ход)"
    max_player_hp = getattr(game, "max_hp", 100)
    armor_def = getattr(game, "armor_defense", 0)

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🧪 БОЛОТНЫЙ СЛИЗЕНЬ\n"
        f"Здоровье: [{bar}] {slug_hp}/{slug_max_hp} HP\n"
        f"{regen_text}\n\n"
        f"Твое здоровье: {game.hp}/{max_player_hp} HP | Броня: {armor_def} DEF\n\n"
        f"Лог боя:\n{last_log}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    top_attack = InlineKeyboardButton(
        text="💥 Ударить посохом" if coated else "🦯 Ударить посохом",
        callback_data="l4_slug_strike"
    )
    rows = [
        [top_attack, InlineKeyboardButton(text="🛡️ Защититься", callback_data="l4_slug_defend")]
    ]

    if attacks_count >= 3 and not inspected:
        rows.append([InlineKeyboardButton(text="🔍 Осмотреть гриб", callback_data="l4_slug_inspect")])

    if inspected and not coated:
        untested = [(k, l) for k, l in SLUG_ACTIONS if k not in tested]
        for i in range(0, len(untested), 2):
            pair = untested[i:i+2]
            rows.append([InlineKeyboardButton(text=l, callback_data=f"l4_slug_act_{k}") for k, l in pair])

        if len(tested) >= len(SLUG_ACTIONS):
            rows.append([InlineKeyboardButton(text="🧪 Растереть по посоху", callback_data="l4_slug_coat")])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    return text, kb


def _render_wolf_pack_battle(game):
    """Отрисовка экрана боя со стаей волков."""
    b = getattr(game, "wolf_pack_battle", None) or {}
    grey_hp = b.get("grey_hp", 41)
    brown_hp = b.get("brown_hp", 44)
    leader_hp = b.get("leader_hp", 51)
    last_log = b.get("last_log", "🐺 Три волка оскалились и прижали уши. Стая берет тебя в полукольцо!")

    icon_grey = "🐺" if grey_hp > 0 else "💀"
    icon_brown = "🐺" if brown_hp > 0 else "💀"
    icon_leader = "🐺" if leader_hp > 0 else "💀"
    status_bar = f"[ {icon_grey} {icon_brown} {icon_leader} ]"

    max_player_hp = getattr(game, "max_hp", 100)
    armor_def = getattr(game, "armor_defense", 0)

    if grey_hp <= 0 and brown_hp <= 0 and leader_hp <= 0:
        text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🐺 МОЛОДАЯ СТАЯ\n"
            f"{status_bar}\n\n"
            "Все волки стаи повержены!\n\n"
            f"Твое здоровье: {game.hp}/{max_player_hp} HP | Броня: {armor_def} DEF\n\n"
            f"Лог боя:\n{last_log}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перевести дух ➔", callback_data="l4_ch2_4_lesson")]
        ])
        return text, kb

    wolf_lines = []
    if grey_hp > 0:
        wolf_lines.append(f"🐺 Серый:  {grey_hp}/41 HP")
    if brown_hp > 0:
        wolf_lines.append(f"🐺 Бурый:  {brown_hp}/44 HP")
    if leader_hp > 0:
        wolf_lines.append(f"🐺 Вожак:  {leader_hp}/51 HP")
    wolves_text = "\n".join(wolf_lines)

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🐺 МОЛОДАЯ СТАЯ\n"
        f"{status_bar}\n\n"
        f"{wolves_text}\n\n"
        f"Твое здоровье: {game.hp}/{max_player_hp} HP | Броня: {armor_def} DEF\n\n"
        f"Лог боя:\n{last_log}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    rows = []
    if grey_hp > 0:
        rows.append([InlineKeyboardButton(text="⚔️ Атаковать Серого", callback_data="l4_pack_attack_grey")])
    if brown_hp > 0:
        rows.append([InlineKeyboardButton(text="⚔️ Атаковать Бурого", callback_data="l4_pack_attack_brown")])
    if leader_hp > 0:
        rows.append([InlineKeyboardButton(text="⚔️ Атаковать Вожака", callback_data="l4_pack_attack_leader")])
    rows.append([InlineKeyboardButton(text="🛡️ Глухая оборона", callback_data="l4_pack_defend")])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 4: ПРОСЕКА ОХОТНИКОВ
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_4_hunters_glade(data, game, uid):
    """Обработать события на локации 'Просека Охотников' (художественный канон L4)."""
    text = None
    kb = None

    # Вход на локацию через меню / переход с L3
    if data in ("hunters_glade_start", "location_enter_4"):
        game.reset_nav()
        game.current_location = "Просека Охотников"
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Просека Охотников" not in unlocked:
            unlocked.append("Просека Охотников")
            game.unlocked_locations = unlocked

        if "l4_entered_day" not in game.story_flags:
            game.story_flags["l4_entered_day"] = getattr(game, "day", 1)

        # Если вся локация 4 полностью завершена (все 3 главы пройдены): мирная стоянка
        if game.is_story_flag_set("l4_fully_completed"):
            text = (
                "Ты выходишь на широкую Просеку Охотников.\n\n"
                "Просека теперь тиха и безопасна. Старые кострища укрыты опавшей хвоей, "
                "а на дозорном помосте тихо колышется сосновый навес. "
                "Впереди ждёт спуск к Яру Слизней."
            )
            kb = get_main_kb(game)
            return text, kb

        # Если сюжетная ветка сейчас в процессе прохождения (есть story_state):
        if getattr(game, "story_state", None) and str(game.story_state).startswith("l4_"):
            return handle_location_4_hunters_glade(game.story_state, game, uid)

        # Если сюжет оленя уже завершён: спокойная стоянка между главами
        if game.is_story_flag_set("l4_completed"):
            text = (
                "Ты выходишь на широкую Просеку Охотников.\n\n"
                "Старые кострища укрыты опавшей хвоей. Костяные пластинки больше не трещат на ветру, "
                "а тропа свободна для исследования и установки охотничьих ловушек."
            )
            kb = get_main_kb(game)
            return text, kb

        # Если сюжет ещё не запущен (нужно пожить 2 ночи): спокойное обживание стоянки
        if not game.is_story_flag_set("l4_started"):
            text = (
                "Ты выходишь на широкую Просеку Охотников.\n\n"
                "Между деревьями чернеют старые кострища, на стволах видны зарубки. "
                "Воздух пахнет смолой и сухой травой. Нужно осмотреться, пожить здесь и обустроить лагерь."
            )
            kb = get_main_kb(game)
            return text, kb

        # Если сюжет активен (в процессе прохождения): возобновить
        return handle_location_4_hunters_glade("l4_1_entry", game, uid)

    # L4.1 — Старт сюжетной ветки: Кто-то ещё здесь
    elif data == "l4_1_entry":
        game.story_state = "l4_1_entry"
        text = (
            "Ты осторожно раздвигаешь колючие лапы елей и выходишь на широкую заросшую просеку. "
            "В воздухе пахнет смолой, землёй и давней гарью. На мгновение накатывает странное дежавю, "
            "будто ты уже когда-то стоял на этой развилке.\n\n"
            "У самой земли сухо щёлкает натянутая бечёвка — вздрагивают костяные пластинки, "
            "и шнур петляет в траву. В тот же миг из чащи доносится глухой шум: "
            "кто-то отчаянно бьётся в кустах, натягивая струну."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Идти по верёвке", callback_data="l4_2_rope")],
            [InlineKeyboardButton(text="Прямо на звук", callback_data="l4_3_deer")],
        ])

    # L4.2 — Верёвка среди травы
    elif data == "l4_2_rope":
        game.story_state = "l4_2_rope"
        text = (
            "Пригнувшись к земле, ты пальцами нащупываешь грубый шнур. Тонкая жила ныряет под узловатые корни сосен "
            "и ведёт вглубь просеки. Волокна бечёвки местами совсем свежие, натёртые смолой — ловушку взвели недавно "
            "и со знанием дела.\n\n"
            "Чуть дальше в жухлой листве чернеет расправленная петля, замаскированная мхом. "
            "Ты аккуратно перешагиваешь её, стараясь не задеть затаившийся сторожок."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_2a_bushes")]
        ])

    # L4.2a — За кустами (возможное появление котёнка)
    elif data == "l4_2a_bushes":
        game.story_state = "l4_2a_bushes"
        has_pet = bool(game.equipment.get("pet"))
        if has_pet:
            text = (
                "Ты осторожно раздвигаешь мокрые ветви малинника. Вдруг котёнок беспокойно возится под курткой, "
                "впиваясь коготками в твоё плечо, и предостерегающе шипит в темноту. Ты замираешь на полушаге.\n\n"
                "Прямо перед твоим сапогом, укрытый жухлым папоротником, натянут тугой шнур с противовесом на ветке. "
                "Ещё одно неосторожное движение — и стальная удавка захлестнула бы ногу."
            )
        else:
            text = (
                "Ты осторожно раздвигаешь мокрые ветви малинника и опускаешь взгляд под ноги. "
                "Инстинкт заставляет тебя замереть на полушаге, вглядываясь в полумрак подлеска.\n\n"
                "Среди жухлого папоротника едва заметно поблёскивает тугой кручёный шнур. "
                "Он уходит к ветке дерева, образуя коварную петлю-удавку прямо на уровне щиколотки. "
                "Ещё шаг вперёд — и ловушка сработала бы на тебе."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Осмотреть проход", callback_data="l4_3_deer")],
            [InlineKeyboardButton(text="Шагнуть вперёд", callback_data="l4_2b_trap")],
        ])

    # L4.2b — Опасное приближение
    elif data == "l4_2b_trap":
        game.story_state = "l4_2b_trap"
        if not game.is_story_flag_set("l4_trap_stepped"):
            game.set_story_flag("l4_trap_stepped", True)
            trap_dmg = 5
            game.hp = max(1, getattr(game, "hp", 100) - trap_dmg)
            game.add_log(f"⚠️ Ловушка на просеке: −{trap_dmg} HP.")
            if getattr(game, "hp", 100) <= 20:
                game.thirst = max(0, getattr(game, "thirst", 60) - 5)
        text = (
            "Ты делаешь неосторожный шаг. Носок цепляет шнур — верёвка со свистом натягивается, "
            "выдёргивая опору из-под ног!\n\n"
            "Ты кубарем летишь в мох, больно ударившись плечом о корягу. Колышек с треском вырывается, "
            "а костяные пластинки яростно гремят над просекой.\n"
            "──────────\n"
            "Ты ушиб плечо: −5 ХП"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_3_deer")]
        ])

    # L4.3 — На другом конце (Раненый олень)
    elif data == "l4_3_deer":
        game.story_state = "l4_3_deer"
        text = (
            "За густым кустарником на земле замер молодой олень. Его задняя нога крепко запутана "
            "в тугой петле из толстого ремня и неестественно поджата к брюху.\n\n"
            "Заметив твоё появление, зверь настороженно прижимает уши, а затем с надрывным хрипом "
            "делает отчаянный рывок, пытаясь вырваться из капкана на свободу. Но натянутый шнур держит намертво."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Снять петлю руками", callback_data="l4_3a_approach")],
            [InlineKeyboardButton(text="Найти крепление", callback_data="l4_3b_mount")],
            [InlineKeyboardButton(text="Оставить его", callback_data="l4_3c_ignore")],
        ])

    # L4.3a — Подойти напрямую
    elif data == "l4_3a_approach":
        game.story_state = "l4_3a_approach"
        if not game.is_story_flag_set("l4_deer_kicked"):
            game.set_story_flag("l4_deer_kicked", True)
            deer_dmg = 3
            game.hp = max(1, getattr(game, "hp", 100) - deer_dmg)
            game.add_log(f"⚠️ Удар оленя: −{deer_dmg} HP.")
            game.adjust_narrative_karma("compassion", 1)
        text = (
            "Ты мягко ступаешь по мху, протянув ладонь к раненой ноге. Но обезумевший от боли зверь вскидывает круп "
            "и со всей силы бьёт копытом!\n\n"
            "Удар приходится по руке. Ты отлетаешь на сучья, баюкая ушибленную кисть, а олень глухо хрипит, не подпуская ближе.\n"
            "──────────\n"
            "Ты ушиб кисть: −3 ХП"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Найти крепление", callback_data="l4_3b_mount")],
            [InlineKeyboardButton(text="Оставить его", callback_data="l4_3c_ignore")],
        ])

    # L4.3b — Найти крепление
    elif data in ("l4_3b_mount", "l4_3b_mount_back"):
        game.story_state = data
        if data == "l4_3b_mount_back":
            text = (
                "Ты отпускаешь бечёвку. За кустами тяжело хрипит олень, натягивая жилу. "
                "Костяные пластинки вот-вот загремят на всю округу!\n\n"
                "Что будешь делать дальше?"
            )
        else:
            text = (
                "Обойдя бьющегося зверя широкой дугой, ты пробираешься к старой берёзе. "
                "Здесь коварный шнур захлёстнут морским узлом вокруг глубоко вбитого в корни дубового колышка.\n\n"
                "Чуть выше на жиле подвешены те самые костяные пластинки. "
                "Любой рывок оленя передавал натяжение на ветку, заставляя кости трещать и оповещая о добыче."
            )
        buttons = []
        if not game.is_story_flag_set("l4_knot_inspected"):
            buttons.append([InlineKeyboardButton(text="🔍 Рассмотреть узел", callback_data="l4_3b_inspect_knot")])
        buttons.append([InlineKeyboardButton(text="Снять пластинки", callback_data="l4_3b1_plates")])
        buttons.append([InlineKeyboardButton(text="Выдернуть колышек", callback_data="l4_3b2_shake")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # L4.3b.inspect — Осмотр узла
    elif data == "l4_3b_inspect_knot":
        game.story_state = "l4_3b_inspect_knot"
        if not game.is_story_flag_set("l4_knot_inspected"):
            game.set_story_flag("l4_knot_inspected", True)
            game.adjust_narrative_karma("observation", 2)
        text = (
            "Ты наклоняешься к колышку. Шнур затянут хитрой петлёй: двойной перехлёст с подворотом внутрь и берёстовым клинышком — "
            "вязкая стяжка не клинит от рывков.\n\n"
            "Ты машинально трогаешь ремень своего рюкзака с красной заплаткой. Боковая петля завязана точь-в-точь так же. "
            "Хозяин рюкзака, чей скелет остался в ручье, явно проходил и здесь.\n"
            "──────────\n"
            "👁️ Наблюдательность: +2"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_3b_mount_back")]
        ])

    # L4.3b.1 — Отвязать пластинки
    elif data == "l4_3b1_plates":
        game.story_state = "l4_3b1_plates"
        game.set_story_flag("signal_disabled", True)
        game.adjust_narrative_karma("observation", 2)
        text = (
            "Чуткими пальцами ты аккуратно распускаешь смоляной узел и перехватываешь связку. "
            "Костяные пластинки лишь глухо звякают в кулаке и мягко ложатся в траву под деревом.\n\n"
            "Олень позади снова надрывно дёргается, но теперь просека безмолвна. "
            "Тревожный сторожок обезврежен, и можно безопасно подобраться к натянутому шнуру."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_4_freed")]
        ])

    # L4.3b.2 — Сразу расшатать колышек
    elif data == "l4_3b2_shake":
        game.story_state = "l4_3b2_shake"
        game.set_story_flag("signal_disabled", False)
        game.adjust_narrative_karma("pragmatism", 1)
        text = (
            "Ты хватаешься обеими руками за дубовый колышек и изо всех сил раскачиваешь его во влажной земле. "
            "Натянутый шнур моментально передаёт яростную вибрацию вверх на гибкую ветку.\n\n"
            "Костяные пластинки оглушительно затрещали на всю округу! Эхо сухого стука разносится по кронам. "
            "Ты приседаешь, тревожно вглядываясь в чащу: не идёт ли кто на шум?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_4_freed")]
        ])

    # L4.4 — Освобождение
    elif data == "l4_4_freed":
        game.story_state = "l4_4_freed"
        if not game.is_story_flag_set("deer_freed"):
            game.spared_souls = getattr(game, "spared_souls", 0) + 1
        game.set_story_flag("deer_freed", True)
        game.set_story_flag("helped_deer", True)
        game.adjust_narrative_karma("compassion", 3)

        sig_disabled = game.is_story_flag_set("signal_disabled")
        if not sig_disabled:
            if not game.is_story_flag_set("l4_whistle_thirst"):
                game.set_story_flag("l4_whistle_thirst", True)
                game.thirst = max(0, getattr(game, "thirst", 60) - 5)
            text = (
                "Ты с силой выдёргиваешь колышек, и петля соскальзывает с копыта. Олень вскакивает, "
                "на секунду замирает перед тобой и вихрем срывается в чащу. Он на свободе, и от этого на душе "
                "становится легче.\n\n"
                "Но внезапно из глубины леса доносится резкий свист: человек или птица — не понять, "
                "но от тревоги во рту моментально пересыхает.\n"
                "──────────\n"
                "Жажда: −5"
            )
        else:
            text = (
                "Ты перерезаешь натяжение, и петля соскальзывает с копыта. Олень с трудом поднимается на ноги, "
                "на мгновение замирает и в один прыжок растворяется в ельнике.\n\n"
                "Он на свободе, и от этого на душе становится легко и спокойно. Вокруг шелестит живая листва — тишина."
            )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_5_firepit")]
        ])

    # L4.3c — Не вмешиваться / Оставить зверя
    elif data == "l4_3c_ignore":
        game.story_state = "l4_3c_ignore"
        game.set_story_flag("deer_freed", False)
        game.adjust_narrative_karma("pragmatism", 2)
        text = (
            "Ты медленно отступаешь на шаг назад, не решаясь вмешиваться. Испуганный зверь собирает последние "
            "силы и делает отчаянный рывок всем телом. Старый колышек трещит и поддаётся — петля соскальзывает!\n\n"
            "Олень в одно мгновение срывается с места и вихрем уносится в чащу. "
            "Он на свободе, и от этого на душе становится легче и спокойнее."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Осмотреть кострище", callback_data="l4_5_firepit")],
            [InlineKeyboardButton(text="🏕 Закончить вылазку: в лагерь", callback_data="l4_9_exit")],
        ])

    # L4.5 — Осмотреть старое кострище
    elif data in ("l4_5_firepit", "l4_5_firepit_back"):
        game.story_state = data
        if data == "l4_5_firepit_back":
            text = (
                "Вяленое мясо на коре пахнет солью и сухим дымом. Свёрток бережно укрыт под плитой от сырости.\n\n"
                "Как поступишь с чужим схроном?"
            )
        else:
            text = (
                "Возле старого кострища сложена невысокая полукруглая стенка из плоских валунов. "
                "Твой намётанный взгляд цепляется за широкий камень у самого основания — земля вокруг него примята.\n\n"
                "Приподняв тяжёлую плиту, ты замираешь: в тайнике лежит тугой свёрток из выделанной кожи с выдавленным "
                "знаком — три косых надреза и черта. Внутри укрыты порции сытного мяса на коре."
            )
        buttons = []
        if not game.is_story_flag_set("l4_leather_inspected"):
            buttons.append([InlineKeyboardButton(text="🔍 Рассмотреть срез кожи", callback_data="l4_5_inspect_leather")])
        buttons.append([InlineKeyboardButton(text="Забрать свёрток", callback_data="l4_5a_loot_all")])
        buttons.append([InlineKeyboardButton(text="Взять кусок мяса", callback_data="l4_5b_loot_one")])
        buttons.append([InlineKeyboardButton(text="Не трогать тайник", callback_data="l4_5c_loot_none")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # L4.5.inspect — Осмотр среза кожи
    elif data == "l4_5_inspect_leather":
        game.story_state = "l4_5_inspect_leather"
        if not game.is_story_flag_set("l4_leather_inspected"):
            game.set_story_flag("l4_leather_inspected", True)
            game.adjust_narrative_karma("observation", 2)
        text = (
            "Ты проводишь пальцем по зубчатому краю ремня. Кожу отсекали не стальным ножом, а острым сколом сланца — "
            "от него остаются характерные волнистые бороздки.\n\n"
            "У ручья ты срезал лямку рюкзака точно таким же осколком сланца. "
            "Тот путник выживал в лесу теми же подручными средствами и шёл шаг в шаг по этой же тропе.\n"
            "──────────\n"
            "👁️ Наблюдательность: +2"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_5_firepit_back")]
        ])

    # L4.5a — Забрать целиком
    elif data == "l4_5a_loot_all":
        game.story_state = "l4_5a_loot_all"
        if not game.is_story_flag_set("l4_meat_taken"):
            game.set_story_flag("l4_meat_taken", True)
            game.inventory["Мясо на коре"] = game.inventory.get("Мясо на коре", 0) + 2
            game.inventory["Кожа"] = game.inventory.get("Кожа", 0) + 1
            game.adjust_narrative_karma("pragmatism", 2)
        next_cb = "l4_6_aftermath" if game.is_story_flag_set("deer_freed") else "l4_7_hearth"
        game.story_flags["l4_cache_next"] = next_cb
        text = (
            "Ты прячешь в мешок найденные припасы. Но закон леса прост: взял чужое — оставь что-то взамен "
            "для хозяина схрона или другого путника.\n\n"
            "Поднять плиту и оставить часть своих вещей?\n"
            "──────────\n"
            "Получено: Мясо на коре ×2, Кожа ×1"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Положить взамен...", callback_data="l4_5_put_select")],
            [InlineKeyboardButton(text="Ничего не класть", callback_data=next_cb)],
        ])

    # L4.5b — Взять часть
    elif data == "l4_5b_loot_one":
        game.story_state = "l4_5b_loot_one"
        if not game.is_story_flag_set("l4_meat_taken"):
            game.set_story_flag("l4_meat_taken", True)
            game.inventory["Мясо на коре"] = game.inventory.get("Мясо на коре", 0) + 1
            game.adjust_narrative_karma("compassion", 1)
        next_cb = "l4_6_aftermath" if game.is_story_flag_set("deer_freed") else "l4_7_hearth"
        game.story_flags["l4_cache_next"] = next_cb
        text = (
            "Ты берёшь одну порцию мяса, оставив остальное. Но закон леса гласит: взял чужое — оставь что-то взамен.\n\n"
            "Положить в схрон что-нибудь из своего инвентаря?\n"
            "──────────\n"
            "Получено: Мясо на коре ×1"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Положить взамен...", callback_data="l4_5_put_select")],
            [InlineKeyboardButton(text="Ничего не класть", callback_data=next_cb)],
        ])

    # L4.5 — Выбор предмета для тайника
    elif data == "l4_5_put_select":
        game.story_state = "l4_5_put_select"
        next_cb = game.story_flags.get("l4_cache_next") or ("l4_6_aftermath" if game.is_story_flag_set("deer_freed") else "l4_7_hearth")
        candidate_items = ["Ветка", "Камень", "Кусок коры", "Лесная ягода", "Красная ягода", "Лесной гриб", "Дикий гриб", "Мох", "Сырое мясо"]
        available = [it for it in candidate_items if game.inventory.get(it, 0) > 0]
        if not available:
            available = [it for it, cnt in game.inventory.items() if cnt > 0 and it not in ("Мясо на коре", "Кожа")][:4]

        buttons = []
        for it in available[:4]:
            buttons.append([InlineKeyboardButton(text=f"Оставить: {it}", callback_data=f"l4_put_{it}")])
        buttons.append([InlineKeyboardButton(text="Ничего не класть", callback_data=next_cb)])

        text = (
            "Ты приподнимаешь каменную плиту тайника. Карманы хранят немного припасов, "
            "собранных в лесу. Что ты готов оставить хозяину схрона взамен взятого мяса?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # L4.5 — Предмет оставлен в тайнике
    elif data.startswith("l4_put_"):
        item_to_leave = data[len("l4_put_"):]
        game.story_state = "l4_5_put_done"
        if game.inventory.get(item_to_leave, 0) > 0:
            game.inventory[item_to_leave] -= 1
            if game.inventory[item_to_leave] <= 0:
                del game.inventory[item_to_leave]
            game.adjust_narrative_karma("compassion", 2)
            game.set_story_flag("l4_cache_shared", True)

        next_cb = game.story_flags.get("l4_cache_next") or ("l4_6_aftermath" if game.is_story_flag_set("deer_freed") else "l4_7_hearth")
        text = (
            f"Ты аккуратно укладываешь в нишу {item_to_leave} и опускаешь каменную плиту на место.\n\n"
            "Схрон вновь надёжно укрыт мхом, а неписаный долг чести закрыт: взял припасы — оставил своё взамен. "
            "Теперь с лёгким сердцем можно продолжать путь."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data=next_cb)]
        ])

    # L4.5c — Оставить всё
    elif data == "l4_5c_loot_none":
        game.story_state = "l4_5c_loot_none"
        text = (
            "Ты бережно опускаешь каменную плиту на место. Пусть чужой схрон остаётся нетронутым — "
            "лес суров к тем, кто забирает последнее у товарища по тропе.\n\n"
            "Мох глушит глухой стук камня. Ты выпрямляешься и оглядываешь окрестности."
        )
        next_cb = "l4_6_aftermath" if game.is_story_flag_set("deer_freed") else "l4_7_hearth"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data=next_cb)]
        ])

    # L4.6 — Что оставить после себя
    elif data == "l4_6_aftermath":
        game.story_state = "l4_6_aftermath"
        text = (
            "Тропа уводит дальше, но теперь намётанный глаз различает в траве контуры других петель. "
            "Охотник щедро усеял сужающийся проход скрытыми силками и настороженными дужками.\n\n"
            "Оставить опасные ловушки позади или позаботиться о тех, кто может пойти по твоим следам?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Обезвредить силки", callback_data="l4_6a_disarm")],
            [InlineKeyboardButton(text="Поставить крест", callback_data="l4_6b_warn")],
            [InlineKeyboardButton(text="Идти дальше", callback_data="l4_7_hearth")],
        ])

    # L4.6a — Обезвредить
    elif data == "l4_6a_disarm":
        game.story_state = "l4_6a_disarm"
        if not game.is_story_flag_set("l4_trap_leather_taken"):
            game.set_story_flag("l4_trap_leather_taken", True)
            game.inventory["Кожа"] = game.inventory.get("Кожа", 0) + 1
            game.thirst = max(0, getattr(game, "thirst", 60) - 5)
            game.adjust_narrative_karma("intervention", 2)
        text = (
            "Опустившись на колени, ты методично распускаешь узлы и выдёргиваешь удерживающие колья. "
            "Самая широкая петля скручена из прочной сыромятной кожи — ты аккуратно сматываешь её в моток.\n\n"
            "Кропотливая возня на солнцепеке отнимает последние силы, и в пересохшем горле першит.\n"
            "──────────\n"
            "Получено: Кожа ×1\n"
            "Жажда: −5"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_7_hearth")]
        ])

    # L4.6b — Сделать предупреждение
    elif data == "l4_6b_warn":
        game.story_state = "l4_6b_warn"
        game.set_story_flag("left_warning", True)
        game.adjust_narrative_karma("compassion", 2)
        text = (
            "Ты подбираешь две сухие сучковатые ветви и связываешь их крест-накрест посреди тропы, подвесив снятые пластинки.\n\n"
            "Теперь любой путник издалека различит тревожный силуэт охотничьего предупреждения и обойдёт гиблую траву стороной."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_7_hearth")]
        ])

    # L4.7 — Охотничий очаг
    elif data in ("l4_7_hearth", "l4_7_hearth_back"):
        game.story_state = "l4_7_hearth"
        if data == "l4_7_hearth_back":
            text = (
                "Ты откладываешь обугленную рукоять и снова переводишь взгляд на кострище. "
                "Под широким навесом из еловой коры сложен запас бересты и смолистой щепы.\n\n"
                "После пережитой тревоги тело гудит от усталости, а прохладный ветер пробирает до костей. "
                "Здесь можно перевести дух у живого огня."
            )
        else:
            text = (
                "У края просеки темнеет добротно сложенное кострище. Под широким навесом из коры сложена сухая береста "
                "и смолистая щепа. В серой золе виднеется что-то обугленное, странно цепляющее взгляд.\n\n"
                "После пережитой тревоги тело гудит от усталости, а прохладный лесной ветер пробирает до костей. "
                "Здесь можно перевести дух у живого огня."
            )
        buttons = []
        if not game.is_story_flag_set("l4_cinder_inspected"):
            buttons.append([InlineKeyboardButton(text="🔍 Осмотреть то, что в золе", callback_data="l4_7_inspect_cinder")])
        buttons.extend([
            [InlineKeyboardButton(text="Развести огонь", callback_data="l4_7a_fire")],
            [InlineKeyboardButton(text="Не разводить огонь", callback_data="l4_7b_stones")],
            [InlineKeyboardButton(text="Уйти с просеки", callback_data="l4_8_final")],
        ])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # L4.7-inspect — Осмотр золы у кострища (+2 наблюдательность)
    elif data == "l4_7_inspect_cinder":
        game.story_state = "l4_7_inspect_cinder"
        if not game.is_story_flag_set("l4_cinder_inspected"):
            game.set_story_flag("l4_cinder_inspected", True)
            game.adjust_narrative_karma("observation", 2)
        text = (
            "Осторожно разгребя серый пепел веткой, ты достаёшь обугленный черенок факела. "
            "Кора давно сгорела, но на твёрдом дереве рукояти вырезаны углубления под пальцы.\n\n"
            "Ты берешь её в руку — и пальцы сами идеально ложатся в выемки, вплоть до каждого изгиба суставов. "
            "Словно кто-то строгал её точно под твою ладонь. Тот же странный мастер, что вязал узлы?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_7_hearth_back")]
        ])

    # L4.7a — Разжечь огонь
    elif data == "l4_7a_fire":
        game.story_state = "l4_7a_fire"
        if not game.is_story_flag_set("l4_fire_lit"):
            game.set_story_flag("l4_fire_lit", True)
            game.adjust_narrative_karma("intervention", 1)
        text = (
            "Ты опускаешься на колени и ворошишь серую золу. Глубоко под старыми углями ещё теплится слабое рыжее пятно. "
            "Ты подсовываешь бересту и начинаешь осторожно дуть, закрывая тление ладонями.\n\n"
            "Огонь разводится неохотно: сырая растопка долго шипит, задыхается и пускает едкий сизый дым. "
            "Но терпение берёт своё — береста трещит, и над валунами взмывает яркое пламя, окутывая лицо благодатным теплом."
        )
        flask_w = int(getattr(game, "flask_water", 0) or 0)
        has_bottle_water = bool(game.equipment.get("flask")) and flask_w > 0
        water_not_drunk = not game.is_story_flag_set("l4_water_drunk")
        buttons = []
        if has_bottle_water and water_not_drunk:
            buttons.append([InlineKeyboardButton(text="Попить воды", callback_data="l4_7a1_drink")])
        buttons.append([InlineKeyboardButton(text="Закончить отдых", callback_data="l4_8_final")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # L4.7a.1 — Попить воды
    elif data == "l4_7a1_drink":
        game.story_state = "l4_7a1_drink"
        flask_w = int(getattr(game, "flask_water", 0) or 0)
        if not game.is_story_flag_set("l4_water_drunk"):
            game.set_story_flag("l4_water_drunk", True)
            if bool(game.equipment.get("flask")) and flask_w > 0:
                sips = min(3, flask_w)
                game.flask_water = max(0, flask_w - sips)
                if game.flask_water <= 0:
                    game.equipment["flask"] = None
                    game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1
                game.add_log(f"💧 Три глотка из бутылки (+20 жажда). Осталось в бутылке: {game.flask_water}/20.")
            game.thirst = min(100, getattr(game, "thirst", 60) + 20)
        text = (
            "Сидя у жаркого пламени, ты откупориваешь бутылку с водой на поясе и делаешь три долгих, "
            "жадных глотка прохладной влаги.\n\n"
            "Живительная вода мгновенно смывает сухость и горечь дыма, возвращая ясность голове и бодрость телу.\n"
            "──────────\n"
            "Утоление жажды: +20"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_8_final")]
        ])

    # L4.7b — Не разводить огонь
    elif data == "l4_7b_stones":
        game.story_state = "l4_7b_stones"
        text = (
            "Ты решаешь не разводить огонь — лишний столб дыма может привлечь нежелательное внимание. "
            "Ты лишь аккуратно укрываешь растопку пластами коры от сырости и поправляешь валуны очага.\n\n"
            "Пора двигаться дальше."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_8_final")]
        ])

    # L4.8 — Финал
    elif data == "l4_8_final":
        game.story_state = None
        game.set_story_flag("l4_completed", True)
        if "l4_deer_completed_day" not in game.story_flags:
            game.story_flags["l4_deer_completed_day"] = getattr(game, "day", 1)
        if "l4_deer_sleeps" not in game.story_flags:
            game.story_flags["l4_deer_sleeps"] = game.story_flags.get("l4_sleep_count", 0)
        if "l4_ch1_completed_day" not in game.story_flags:
            game.story_flags["l4_ch1_completed_day"] = getattr(game, "day", 1)
        if "l4_ch1_sleeps" not in game.story_flags:
            game.story_flags["l4_ch1_sleeps"] = game.story_flags.get("l4_sleep_count", 0)
        if game.is_story_flag_set("deer_freed"):
            text = (
                "У самого выхода с просеки среди хвои затаилась опасная петля-растяжка!\n\n"
                "Внезапно из ельника выступает спасённый олень: резким ударом копытца он сбивает сторожок — "
                "силки хлопают вхолостую перед твоим сапогом. Зверь благодарно склоняет рога, "
                "спасая тебя от капкана, и растворяется в чаще леса. Добро вернулось добром!\n\n"
                "На сосне чернеет зарубка — след петли времени. Ты возвращаешься в лагерь."
            )
        else:
            text = (
                "На выходе с просеки твой взгляд падает на вековую сосну. На стволе зарубкой высечен знак: "
                "три надреза и черта. Из древесины медленно сочится густая смола.\n\n"
                "Ты касаешься липкой коры. Где-то в чаще скрыты другие коварные силки — следы петли времени. "
                "Пора возвращаться в лагерь."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 В лагерь", callback_data="back")]
        ])

    # L4.9 — Уйти с просеки (ранний финал)
    elif data == "l4_9_exit":
        game.story_state = None
        game.set_story_flag("l4_completed", True)
        if "l4_deer_completed_day" not in game.story_flags:
            game.story_flags["l4_deer_completed_day"] = getattr(game, "day", 1)
        if "l4_deer_sleeps" not in game.story_flags:
            game.story_flags["l4_deer_sleeps"] = game.story_flags.get("l4_sleep_count", 0)
        if "l4_ch1_completed_day" not in game.story_flags:
            game.story_flags["l4_ch1_completed_day"] = getattr(game, "day", 1)
        if "l4_ch1_sleeps" not in game.story_flags:
            game.story_flags["l4_ch1_sleeps"] = game.story_flags.get("l4_sleep_count", 0)
        text = (
            "Ты оставляешь просеку позади. Сухой дробный стук костяных пластинок постепенно тонет в монотонном шуме сосен, "
            "пока не смолкает вовсе.\n\n"
            "Коварные силки остались позади, укрытые ковром жухлой травы. "
            "Ты ускоряешь шаг, возвращаясь к безопасности своего лагеря."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 В лагерь", callback_data="back")]
        ])

    # ══════════════════════════════════════════════════════════════════════════
    # СЮЖЕТКА 1: ПРЕГРАДА НА ОБРЫВЕ
    # ══════════════════════════════════════════════════════════════════════════

    # Экран 1: Край белого пара
    elif data == "l4_ch1_1_cliff":
        game.story_state = "l4_ch1_1_cliff"
        text = (
            "Тропа ведёт тебя в глухую северную часть просеки. Вековые сосны здесь постепенно расступаются, "
            "а сухой ковёр хвои сменяется скользкой, вязкой глиной. В воздухе появляется незнакомый кисловатый привкус, "
            "пахнущий прелыми спорами и сыростью.\n\n"
            "Внезапно земля под ногами обрывается: перед тобой открывается колоссальный провал — глубокий овраг, "
            "со дна которого густыми клубами поднимается плотный белесый пар."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подойти к краю обрыва", callback_data="l4_ch1_2_trap")]
        ])

    # Экран 2: Скользкая западня
    elif data in ("l4_ch1_2_trap", "l4_ch1_2_trap_back"):
        game.story_state = "l4_ch1_2_trap"
        text = (
            "Ты осторожно подходишь к кромке. Сланцевые пластины доспеха на твоих плечах дают привычную защиту, "
            "и это вселяет уверенность.\n\n"
            "Но ты понимаешь, что на этой скользкой крутизне один неверный шаг станет роковым. Стены почти отвесные, "
            "покрыты жирными светящимися полосами. Пугает не только высота, но и скопившиеся на дне оврага лужи едкой слизи, "
            "в которых точно не хочется побывать."
        )
        buttons = []
        if not game.is_story_flag_set("l4_cliff_tracks_inspected"):
            buttons.append([InlineKeyboardButton(text="🔍 Осмотреть корни и следы", callback_data="l4_ch1_2_inspect")])
        buttons.append([InlineKeyboardButton(text="Оценить спуск", callback_data="l4_ch1_3_growth")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Экран 2-осмотр: Следы на глине
    elif data == "l4_ch1_2_inspect":
        game.story_state = "l4_ch1_2_inspect"
        if not game.is_story_flag_set("l4_cliff_tracks_inspected"):
            game.set_story_flag("l4_cliff_tracks_inspected", True)
            game.adjust_narrative_karma("observation", 1)
        text = (
            "Ты приседаешь на корточки, вглядываясь в застывшую глину у корней.\n\n"
            "Среди потеков светящейся жижи видны глубокие отпечатки борьбы. Ты оборачиваешься назад, "
            "сравниваешь их со своими свежими следами — и внутри всё холодеет: форма мыска, размер подошвы "
            "и сколотый каблук в точности повторяют отпечаток твоего правого ботинка.\n\n"
            "Кто-то с твоей же походкой и в такой же обуви уже пятился здесь от края обрыва."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отступить от края ➔", callback_data="l4_ch1_3_growth")]
        ])

    # Экран 3: Зелёный нарост
    elif data == "l4_ch1_3_growth":
        game.story_state = "l4_ch1_3_growth"
        text = (
            "Из белесого пара с омерзительным хлюпаньем на край обрыва вываливается огромный зелёный болотный слизень! "
            "Его желеобразное тело вздувается, готовясь к атаке.\n\n"
            "Но прямо между вами на замшелом уступе растёт странный светящийся гриб, пульсирующий бирюзовым светом. "
            "Тварь явно избегает этот чудиковатый светящийся гриб, обползая его стороной и недовольно шипя от его сияния."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Сорвать светящийся гриб", callback_data="l4_slug_battle_start")]
        ])

    # Экран 3-бой: Вход в боевое столкновение со слизнем
    elif data in ("l4_slug_battle_start", "l4_slug_battle"):
        if data == "l4_slug_battle_start" or not getattr(game, "slug_battle", None):
            game.story_state = "l4_slug_battle"
            if game.inventory.get("Светящийся гриб", 0) <= 0:
                game.inventory["Светящийся гриб"] = 1
            game.slug_battle = {
                "slug_hp": 30,
                "slug_max_hp": 30,
                "attacks_count": 0,
                "inspected": False,
                "actions_tested": [],
                "coated": False,
                "last_log": "⚠️ Слизень прыгает на тебя! Приготовься к бою!",
            }
        return _render_slug_battle(game)

    elif data in ("l4_slug_strike", "l4_slug_battle_engine"):
        b = getattr(game, "slug_battle", None) or {}
        coated = b.get("coated", False)
        if coated or data == "l4_slug_battle_engine":
            b["slug_hp"] = max(0, b.get("slug_hp", 30) - 11)
            if b["slug_hp"] <= 0 or data == "l4_slug_battle_engine":
                game.story_state = "l4_ch1_4_stone_mark"
                game.set_story_flag("l4_slug_defeated", True)
                if game.inventory.get("Светящийся гриб", 0) > 0:
                    game.inventory["Светящийся гриб"] -= 1
                    if game.inventory["Светящийся гриб"] <= 0:
                        del game.inventory["Светящийся гриб"]
                text = (
                    "Дробящий удар посоха, окроплённого бирюзовым соком, разносит студенистое тело твари!\n\n"
                    "Слизень лопается и шипящей жижей сползает по глинистому откосу обратно в овраг."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Далее ➔", callback_data="l4_ch1_4_stone_mark")]
                ])
                return text, kb
            else:
                game.hp = max(1, game.hp - 5)
                b["last_log"] = "💥 Удар посохом: −11 HP. Кислотный сок шипит и растворяет оболочку!\n⚠️ Слизень прыгает на тебя: −5 HP (игнор брони)."
        else:
            b["slug_hp"] = max(1, min(30, b.get("slug_hp", 30) - 1 + 1))
            game.hp = max(1, game.hp - 5)
            b["attacks_count"] = b.get("attacks_count", 0) + 1
            log_str = "🦯 Удар посохом: −1 HP. Посох вязнет в слизи.\n⚠️ Слизень прыгает на тебя: −5 HP (игнор брони). Слизень восстановил +1 HP."
            if b["attacks_count"] >= 3 and not b.get("inspected", False):
                log_str += "\nПохоже, обычные удары бесполезны. Осмотри внимательнее гриб."
            b["last_log"] = log_str

        game.slug_battle = b
        return _render_slug_battle(game)

    elif data == "l4_slug_defend":
        b = getattr(game, "slug_battle", None) or {}
        coated = b.get("coated", False)
        game.hp = max(1, game.hp - 5)
        if not coated:
            b["slug_hp"] = min(30, b.get("slug_hp", 30) + 1)
            b["last_log"] = "🛡️ Ты защищаешься, но слизь прожигает оборону: −5 HP (игнор брони). Слизень восстановил +1 HP."
        else:
            b["last_log"] = "🛡️ Ты защищаешься: −5 HP (игнор брони)."
        game.slug_battle = b
        return _render_slug_battle(game)

    elif data == "l4_slug_inspect":
        b = getattr(game, "slug_battle", None) or {}
        b["inspected"] = True
        game.hp = max(1, game.hp - 5)
        if not b.get("coated", False):
            b["slug_hp"] = min(30, b.get("slug_hp", 30) + 1)
        b["last_log"] = "🔍 Тебе показалось, что слизень отшатнулся.\n⚠️ Слизень прыгает на тебя: −5 HP (игнор брони). Слизень восстановил +1 HP."
        game.slug_battle = b
        return _render_slug_battle(game)

    elif data.startswith("l4_slug_act_"):
        act_key = data.replace("l4_slug_act_", "")
        b = getattr(game, "slug_battle", None) or {}
        tested = list(b.get("actions_tested", []))
        if act_key not in tested:
            tested.append(act_key)
        b["actions_tested"] = tested

        act_texts = {
            "smell": ("Тошнотворно воняет. Так воняет, что аж глаза заслезились.", 5),
            "lick": ("Она на вкус настолько отвратительна, что тебя чуть не вырвало, и ты пропустил удар!", 8),
            "eat": ("Персонаж: \"Ты дурак?! Я это в рот не возьму!\"", 5),
            "cross": ("Бесовской твари всё равно на твои молитвы.", 5),
            "throw": ("Ты швырнул гриб. Слизень брезгливо увернулся. Пришлось ползти и подбирать обратно.", 5),
            "wave": ("Ты водишь грибом как гипнотизёр. Слизень молча прыгает на грудь.", 5),
            "talk": ("«О великий гриб, яви свою мощь!» Гриб молчит. Слизень прыгает.", 5),
            "squeeze": ("Ты сжал шляпку. Брызнувший едкий сок защипал пальцы! Ты заорал от боли.", 5),
            "step": ("Раздавишь редкий гриб — чем воевать? Ты одёрнул ногу, но потерял равновесие.", 5),
            "friend": ("«Мир, дружба, жвачка?» В ответ слизень смачно плюнул студнем.", 5),
        }
        desc, dmg = act_texts.get(act_key, ("Ты пробуешь применить гриб, но без толку.", 5))
        game.hp = max(1, game.hp - dmg)
        if not b.get("coated", False):
            b["slug_hp"] = min(30, b.get("slug_hp", 30) + 1)
        b["last_log"] = f"{desc}\n⚠️ Слизень прыгает на тебя: −{dmg} HP (игнор брони). Слизень восстановил +1 HP."
        game.slug_battle = b
        return _render_slug_battle(game)

    elif data == "l4_slug_coat":
        b = getattr(game, "slug_battle", None) or {}
        b["coated"] = True
        # Гриб использован и удаляется из инвентаря
        if game.inventory.get("Светящийся гриб", 0) > 0:
            game.inventory["Светящийся гриб"] -= 1
            if game.inventory["Светящийся гриб"] <= 0:
                del game.inventory["Светящийся гриб"]

        game.hp = max(1, game.hp - 5)
        b["last_log"] = "🧪 Бирюзовый сок с шипением разъедает грязь и покрывает древко пенящейся коркой!\n⚠️ Слизень прыгает на тебя: −5 HP (игнор брони)."
        game.slug_battle = b
        return _render_slug_battle(game)

    # Экран 4: Чёрный след на камне
    elif data == "l4_ch1_4_stone_mark":
        game.story_state = "l4_ch1_4_stone_mark"
        text = (
            "Слизняк разбит в брызги, но дыхание сбито. Ты опускаешь взгляд на грудь: на сланцевой пластине остался "
            "отчётливый чёрный развод — кислота твари въелась в камень, до сих пор шипит и потрескивает.\n\n"
            "Сланцевая броня против них бесполезна: камень крошится, а кислота затекает в щели. "
            "Но капли, попавшие на кожаный пояс, просто стекли, не повредив материал. А в овраге таких тварей сотни."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отойти от обрыва", callback_data="l4_ch1_5_doubt")]
        ])

    # Экран 5: Тяжёлое сомнение
    elif data == "l4_ch1_5_doubt":
        game.story_state = None
        game.set_story_flag("l4_ch1_cliff_completed", True)
        game.story_flags["l4_ch2_sleeps"] = game.story_flags.get("l4_sleep_count", 0)
        game.story_flags["l4_ch2_day"] = getattr(game, "day", 1)
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Яр Слизней" not in unlocked:
            unlocked.append("Яр Слизней")
            game.unlocked_locations = unlocked
        text = (
            "Ты отходишь от гиблой кромки. Сейчас скинуть броню ты не готов: в лесу полно волков, "
            "и доспех дарит чувство защиты и уверенность в завтрашнем дне.\n\n"
            "Но для спуска в этот овраг потребуется защита из прочной кожи, которая не боится кислоты и не тянет ко дну. "
            "С этими мыслями ты возвращаешься в лагерь.\n"
            "──────────\n"
            "Яр Слизней (Опасно, прохода нет)"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 Вернуться в лагерь", callback_data="back")]
        ])

    # ══════════════════════════════════════════════════════════════════════════
    # СЮЖЕТКА 2: СЕРАЯ СТАЯ
    # ══════════════════════════════════════════════════════════════════════════

    # Экран 1: Серая тень
    elif data == "l4_ch2_1_shadow":
        game.story_state = "l4_ch2_1_shadow"
        text = (
            "Вечерний туман ползёт между стволами сосен. Ты возвращаешься по просеке, как вдруг тишину "
            "разрезает резкий, голодный вой. Ему откликаются ещё два голоса — совсем рядом!\n\n"
            "Из ельника на тропу бесшумно выскальзывают три волка. Это не больные заморыши, а крепкие, "
            "здоровые молодые хищники. Не знающие страха, они вышли на охоту и решили напасть на первого, "
            "кого увидели на тропе. Волки берут тебя в полукольцо."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Встать в глухую оборону", callback_data="l4_ch2_2_stone_shield")]
        ])

    # Экран 2: Благословение и оковы камня
    elif data == "l4_ch2_2_stone_shield":
        game.story_state = "l4_ch2_2_stone_shield"
        text = (
            "Ты вжимаешься спиной в сосну. Волк делает бросок — челюсти со скрежетом бьют по сланцевому наплечнику! "
            "Пластины выдерживают удар, спасая плечо. В голове вспыхивает радость: «Какое счастье, что на мне осталась броня!»\n\n"
            "Но волки кружат втроём. Движения в камне тяжёлые, скованные — ловкости не хватает катастрофически. "
            "Ты понимаешь, что окружение не пробить, и впереди только бой."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Принять смертный бой", callback_data="l4_ch2_3_guard")]
        ])

    # Экран 3: Лесная стража
    elif data == "l4_ch2_3_guard":
        game.story_state = "l4_ch2_3_guard"
        if game.is_story_flag_set("deer_freed"):
            text = (
                "Вожак стелется для смертельного прыжка. Но в этот миг чащу разрывает яростный топот копыт!\n\n"
                "Из тумана вылетает спасённый олень, а следом — могучие лесные сородичи с раскидистыми рогами! "
                "Стадо тараном сбивает волков, вминая их в мох. Ошалевшие хищники с визгом рассыпаются в темноту.\n\n"
                "Ты оседаешь на мох, понимая: этот бой с волками стал бы для тебя последним в твоей жизни, "
                "и живым ты бы из него не вышел победителем."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Взглянуть на спасителей ➔", callback_data="l4_ch2_3b_gaze")]
            ])
        else:
            text = (
                "Помощи ждать неоткуда. В полумраке блестят оскаленные волчьи пасти. "
                "Сланцевый доспех сковывает движения, но ты перехватываешь посох обеими руками, "
                "готовясь драться за каждый вдох против троих свирепых хищников!"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Сражаться за жизнь!", callback_data="l4_wolves_battle_start")]
            ])

    # Экран 3-бой: Бой с волками (если олень не спасён)
    elif data in ("l4_wolves_battle_start", "l4_wolves_battle"):
        if data == "l4_wolves_battle_start" or not getattr(game, "wolf_pack_battle", None):
            game.story_state = "l4_wolves_battle"
            game.wolf_pack_battle = {
                "grey_hp": 41,
                "brown_hp": 44,
                "leader_hp": 51,
                "last_log": "🐺 Три волка оскалились и прижали уши. Стая берет тебя в полукольцо!",
            }
        return _render_wolf_pack_battle(game)

    elif data.startswith("l4_pack_attack_"):
        target = data.replace("l4_pack_attack_", "")
        b = getattr(game, "wolf_pack_battle", None) or {}
        player_dmg = _calc_player_damage(game)

        target_name = "Серого" if target == "grey" else ("Бурого" if target == "brown" else "Вожака")
        hp_key = f"{target}_hp"
        b[hp_key] = max(0, b.get(hp_key, 0) - player_dmg)

        logs = [f"💥 Ты ударил {target_name}: −{player_dmg} HP!"]

        total_wolf_dmg = 0
        if b.get("grey_hp", 0) > 0:
            g_dmg = random.randint(3, 5)
            total_wolf_dmg += g_dmg
            logs.append(f"🐺 Серый укусил: −{g_dmg} HP.")
        if b.get("brown_hp", 0) > 0:
            br_dmg = random.randint(4, 6)
            total_wolf_dmg += br_dmg
            logs.append(f"🐺 Бурый рванул: −{br_dmg} HP.")
        if b.get("leader_hp", 0) > 0:
            l_dmg = random.randint(5, 7)
            total_wolf_dmg += l_dmg
            logs.append(f"🐺 Вожак сбил с ног: −{l_dmg} HP.")

        game.hp = max(1, game.hp - total_wolf_dmg)
        b["last_log"] = "\n".join(logs)
        game.wolf_pack_battle = b

        if b.get("grey_hp", 0) <= 0 and b.get("brown_hp", 0) <= 0 and b.get("leader_hp", 0) <= 0:
            b["last_log"] = "🎉 Все волки стаи повержены! Ты победил в жестокой схватке!"
            if not game.is_story_flag_set("l4_wolves_defeated"):
                game.kills_count = getattr(game, "kills_count", 0) + 3
            game.set_story_flag("l4_wolves_defeated", True)

        return _render_wolf_pack_battle(game)

    elif data == "l4_pack_defend":
        b = getattr(game, "wolf_pack_battle", None) or {}
        logs = ["🛡️ Глухая оборона: ты закрылся посохом, урон уполовинен!"]
        total_wolf_dmg = 0
        if b.get("grey_hp", 0) > 0:
            g_dmg = max(1, random.randint(3, 5) // 2)
            total_wolf_dmg += g_dmg
            logs.append(f"🐺 Серый царапнул блок: −{g_dmg} HP.")
        if b.get("brown_hp", 0) > 0:
            br_dmg = max(1, random.randint(4, 6) // 2)
            total_wolf_dmg += br_dmg
            logs.append(f"🐺 Бурый ударился о древко: −{br_dmg} HP.")
        if b.get("leader_hp", 0) > 0:
            l_dmg = max(1, random.randint(5, 7) // 2)
            total_wolf_dmg += l_dmg
            logs.append(f"🐺 Вожак клацнул по камню: −{l_dmg} HP.")

        game.hp = max(1, game.hp - total_wolf_dmg)
        b["last_log"] = "\n".join(logs)
        game.wolf_pack_battle = b
        return _render_wolf_pack_battle(game)

    # Экран 3b: Взгляд лесного исполина
    elif data == "l4_ch2_3b_gaze":
        game.story_state = "l4_ch2_3b_gaze"
        text = (
            "Молодые олени растворяются в чаще, но спасённый самец задерживается. Он замирает в пяти шагах "
            "и смотрит прямо на тебя. В его глубоких тёмных глазах чудится безмолвная благодарность за подаренную жизнь.\n\n"
            "Он ждёт, пока всё стадо скроется в глуши, благородно вскидывает рога и величаво уходит в туман.\n\n"
            "Ты стоишь в холодном поту, боясь пошевелиться. И только сейчас до тебя доходит: "
            "они пришли спасти того, кто спас их сородича."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перевести дух ➔", callback_data="l4_ch2_4_lesson")]
        ])

    # Экран 4: Урок просеки
    elif data == "l4_ch2_4_lesson":
        game.story_state = None
        game.set_story_flag("l4_ch2_pack_completed", True)
        game.story_flags["l4_ch3_sleeps"] = game.story_flags.get("l4_sleep_count", 0)
        game.story_flags["l4_ch3_day"] = getattr(game, "day", 1)
        text = (
            "Просека погружается в тишину. Ты осматриваешь исцарапанный доспех: камень спас от клыков, "
            "но неповоротливая тяжёлая броня едва не погубила тебя, а в борьбе со слизнями это станет верной смертью.\n\n"
            "В голове промелькнула мысль: «Нужна новая броня, компенсирующая недостатки текущей — прочная, "
            "но лёгкая и не боящаяся кислоты». С твёрдым намерением решить вопрос со снаряжением ты уходишь в лагерь."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 Вернуться в лагерь", callback_data="back")]
        ])

    # ══════════════════════════════════════════════════════════════════════════
    # СЮЖЕТКА 3: ДОЗОРНЫЙ ПОМОСТ И РЕШЕНИЕ ПО БРОНЕ
    # ══════════════════════════════════════════════════════════════════════════

    # Экран 1: Укрытие на высоте
    elif data == "l4_ch3_1_shelter":
        game.story_state = "l4_ch3_1_shelter"
        text = (
            "На дальнем краю просеки две сосны сплелись ветвями. В развилке, на высоте трёх человеческих ростов, "
            "приютился дозорный помост под навесом из плотной сосновой коры.\n\n"
            "Вверх уходит старый пеньковый канат с узлами, но нижние перекладины срублены. Верёвка стара: "
            "твоего веса вместе со сланцевой бронёй она просто не выдержит и лопнет.\n\n"
            "Ты расстёгиваешь ремни и скидываешь каменные пластины на мох у подножия сосны."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Взобраться налегке", callback_data="l4_ch3_2_fate")]
        ])

    # Экран 2: Судьба доспеха
    elif data == "l4_ch3_2_fate":
        game.story_state = "l4_ch3_2_fate"
        text = (
            "Ты поднимаешься по канату на помост. Взглянув вниз, ты видишь сланцевый доспех, спасший тебя от волков. "
            "Бросить его гнить во мху жалко.\n\n"
            "Перед тобой выбор: потратить ветку и кожу, чтобы сплести блочную люльку и затянуть доспех сюда, "
            "в сухое укрытие. Либо не поднимать броню сейчас, осмотреть помост налегке, "
            "а судьбу доспеха решить уже внизу после спуска."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Поднять доспех сюда", callback_data="l4_ch3_2a_lift")],
            [InlineKeyboardButton(text="Не поднимать, осмотреться", callback_data="l4_ch3_3_table")],
        ])

    # Экран 2а: Схрон на помосте (ветка люльки)
    elif data == "l4_ch3_2a_lift":
        game.story_state = "l4_ch3_2a_lift"
        game.set_story_flag("l4_armor_lifted", True)
        game.adjust_narrative_karma("intervention", 2)
        if game.inventory.get("Ветка", 0) > 0:
            game.inventory["Ветка"] -= 1
            if game.inventory["Ветка"] <= 0:
                del game.inventory["Ветка"]
        if game.inventory.get("Кожа", 0) > 0:
            game.inventory["Кожа"] -= 1
            if game.inventory["Кожа"] <= 0:
                del game.inventory["Кожа"]
        text = (
            "Ты связываешь из ветки и кожи люльку, перекидываешь канат через сук и поднимаешь каменные пластины наверх.\n\n"
            "Сланцевый доспех аккуратно уложен под навес из коры — здесь ему не страшны сырость и дожди. "
            "Снаряжение надёжно сохранено."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Осмотреть настил", callback_data="l4_ch3_3_table")]
        ])

    # Экран 3: Стол под навесом
    elif data in ("l4_ch3_3_table", "l4_ch3_3_table_back"):
        game.story_state = "l4_ch3_3_table"
        text = (
            "Под навесом сухо и тихо. Ветер гуляет в кронах, а внизу видна вся просека и кромка оврага.\n\n"
            "У ствола сосны стоит массивный стол. Ты подходишь ближе и спотыкаешься взглядом: прямо на столешнице "
            "ножом вырезан подробный чертёж сланцевой брони! Сколотый левый угол наплечника, перехлёст жил — "
            "рисунок сколов точь-в-точь повторяет доспех, оставленный под деревом.\n\n"
            "Рядом лежит пожелтевшая схема и пучок жил."
        )
        buttons = []
        if not game.is_story_flag_set("l4_desk_drawing_inspected"):
            buttons.append([InlineKeyboardButton(text="🔍 Всмотреться в чертёж", callback_data="l4_ch3_3_inspect")])
        buttons.append([InlineKeyboardButton(text="Забрать схему и припасы", callback_data="l4_ch3_4_draft")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Экран 3-осмотр: Холодный след
    elif data == "l4_ch3_3_inspect":
        game.story_state = "l4_ch3_3_inspect"
        if not game.is_story_flag_set("l4_desk_drawing_inspected"):
            game.set_story_flag("l4_desk_drawing_inspected", True)
            game.adjust_narrative_karma("observation", 2)
        text = (
            "Ты проводишь пальцем по глубоким бороздам чертежа. Сомнений нет: это твоя броня. "
            "Каждый шов, каждый скол скопированы с пугающей точностью. Кто-то повторял твои действия точь-в-точь, "
            "создавал этот же доспех и стоял у этого же стола.\n\n"
            "Всматриваться дальше бессмысленно — мороз по коже подтверждает: "
            "ты не понимаешь, что творится в этом чёртовом лесу."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Забрать схему и отойти ➔", callback_data="l4_ch3_4_draft")]
        ])

    # Экран 4: Охотничья схема и сквозняк
    elif data == "l4_ch3_4_draft":
        game.story_state = "l4_ch3_4_draft"
        text = (
            "Ты бережно убираешь схему кожаной брони: по этим чертежам можно сшить полный комплект лёгкой "
            "и кислотостойкой защиты.\n\n"
            "В щели дощатого пола свистит сквозняк. Под ногами валяются обрезки сосновой коры. "
            "Ты понимаешь, что больше никогда сюда не вернёшься — путь лежит только вперёд, в овраг. "
            "Но у тебя чешутся руки заделать эти щели: инженерная гордость не позволяет оставить укрытие сквознякам."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Спуститься вниз", callback_data="l4_ch3_5_armor_final")],
            [InlineKeyboardButton(text="🔨 Заделать щели корой", callback_data="l4_ch3_4_upgrade")],
        ])

    # Экран 4-доработка: Тёплый настил
    elif data == "l4_ch3_4_upgrade":
        game.story_state = "l4_ch3_4_upgrade"
        game.ap = max(0, getattr(game, "ap", 3) - 2)
        game.hunger = max(0, getattr(game, "hunger", 60) - 20)
        game.thirst = max(0, getattr(game, "thirst", 60) - 35)
        game.adjust_narrative_karma("intervention", 2)
        text = (
            "Ты подбираешь кору из-под ног и забиваешь её в щели, настилая лапник. "
            "На помосте становится глухо, сухо и тепло — сделано образцово.\n\n"
            "Работа отнимает силы: в животе урчит от голода, в горле першит, а плечи ноют от усталости. "
            "Ты понимаешь, что больше сюда никогда не вернёшься, но уходишь с глубоким чувством выполненного долга и созидания."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Спуститься вниз ➔", callback_data="l4_ch3_5_armor_final")]
        ])

    # Экран 5: Финальное решение по броне
    elif data == "l4_ch3_5_armor_final":
        game.story_state = "l4_ch3_5_armor_final"
        if game.is_story_flag_set("l4_armor_lifted"):
            return handle_location_4_hunters_glade("l4_ch3_6_epilogue", game, uid)
        text = (
            "Ты спускаешься к подножию сосен. Сланцевый доспех лежит на земле.\n\n"
            "Оставить его валяться в сыром мху? Или потратить силы (−2 AP), обойти подлесок, "
            "срубить крепкий ствол и надёжно повесить доспех над землёй? "
            "Поблизости нет деревьев, способных выдержать этот вес, придётся побродить по местности, поискать."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Повесить на деревце (−2 AP)", callback_data="l4_ch3_5a_tree")],
            [InlineKeyboardButton(text="Оставить лежать на мху", callback_data="l4_ch3_5b_moss")],
        ])

    elif data == "l4_ch3_5a_tree":
        game.story_state = "l4_ch3_5a_tree"
        game.ap = max(0, getattr(game, "ap", 3) - 2)
        game.adjust_narrative_karma("pragmatism", 1)
        text = (
            "Потратив добрый час, ты находишь упругую молодую лиственницу и надёжно подвешиваешь на неё сланцевые пластины. "
            "Камень оторван от сырой земли и не зарастёт мхом.\n\n"
            "Ты вытираешь пот со лба. Доспех пристроен на совесть."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_ch3_6_epilogue")]
        ])

    elif data == "l4_ch3_5b_moss":
        game.story_state = "l4_ch3_5b_moss"
        text = (
            "Ты оставляешь доспех лежать у корней вековой сосны. Время и сырость сделают своё дело, "
            "но сейчас силы дороже каменных пластин.\n\n"
            "Ты выпрямляешься и расправляешь плечи: без каменного гнёта тело наполняется удивительной пружинистой лёгкостью."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l4_ch3_6_epilogue")]
        ])

    # Экран 6: Размышления на рубеже (Финал локации 4)
    elif data == "l4_ch3_6_epilogue":
        game.story_state = None
        game.set_story_flag("l4_fully_completed", True)
        if not game.is_story_flag_set("l4_schema_received"):
            game.set_story_flag("l4_schema_received", True)
            game.inventory["Схема кожаной брони"] = game.inventory.get("Схема кожаной брони", 0) + 1
            game.add_log("В рюкзак добавлена схема кожаной брони.")
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Яр Слизней" not in unlocked:
            unlocked.append("Яр Слизней")
            game.unlocked_locations = unlocked
        text = (
            "Ты стоишь на опушке перед спуском в овраг, глядя на заходящее солнце. На душе смешались светлая грусть "
            "и тихая надежда наконец-то выбраться из этого заколдованного круга.\n\n"
            "Сланцевая броня осталась позади — верный страж, спасший тебя от волков. Тебя наполняет уверенность, "
            "что только сшив новый кожаный доспех, ты сможешь спуститься к оврагу, к едкой бездне Яра Слизней. "
            "Просека Охотников пройдена. Твой путь лежит дальше."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 В лагерь", callback_data="back")]
        ])

    # Управление active_story_callback
    terminators = ("l4_8_final", "l4_9_exit", "l4_ch1_5_doubt", "l4_ch2_4_lesson", "l4_ch3_6_epilogue", "back")
    if kb == get_main_kb(game) or data in terminators or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        game.active_story_callback = "l4_1_entry" if data in ("hunters_glade_start", "location_enter_4") else data

    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 5: ЯР СЛИЗНЕЙ
# ──────────────────────────────────────────────────────────────────────────────

SLIME_NAMES_POOL = [
    "Едкий Прыгун", "Болотный Чавка", "Мутный Липун", "Янтарный Желвак",
    "Слизень-Шалун", "Бурый Пузырь", "Зелёный Соплевик", "Глиняный Ползун",
    "Шипящий Студень", "Смоляной Каплевик", "Хлюпающий Желевик", "Едкий Брызгун",
    "Тёмный Сгусток", "Пещерный Дрожалка", "Трухлявый Слизень", "Толстый Бульк",
    "Ржавый Клякса", "Ядовитый Кап", "Вязкий Мякиш", "Хвойный Слизевик",
    "Моховой Жвачник", "Липкий Колобок", "Болотный Дрожж", "Серный Пузырник",
    "Гнилой Холодец", "Торфяной Плевок", "Кислотный Сгусток", "Сырой Клейковик",
    "Вялый Чавк", "Тягучий Капель", "Осклизлый Бугорок", "Топейный Жировик",
    "Светящийся Пузырь", "Трясинный Ползун", "Едкий Желатин", "Смоляной Бурляш",
    "Мутный Комок", "Илистый Чавка", "Вздутый Пузырь", "Склизкий Живчик",
    "Капельный Прыгун", "Мшистый Соплевик", "Кислый Студень", "Жёлтый Липун",
    "Болотяник", "Слизкий Корень", "Гнилостный Бульк", "Торфяной Слизень",
    "Едкий Желвак", "Янтарный Липун"
]


def start_slug_pack_battle(game, count: int = 6):
    """Инициализация боя со скоплением слизней (1-6 шт)."""
    count = max(1, min(count, 6))
    chosen_names = random.sample(SLIME_NAMES_POOL, count) if len(SLIME_NAMES_POOL) >= count else SLIME_NAMES_POOL[:count]
    slimes = []
    for name in chosen_names:
        hp = random.randint(15, 25)
        slimes.append({
            "name": name,
            "hp": hp,
            "max_hp": hp,
            "alive": True,
        })
    game.slug_pack_battle = {
        "slimes": slimes,
        "round": 1,
        "last_log": "Скопление слизней с шипением окружает тебя со всех сторон!",
        "is_victory": False,
        "is_defeat": False,
        "cores_dropped": 0,
        "loot_log": [],
    }
    game.active_story_callback = "l5_slug_battle"
    return _render_slug_pack_battle(game)


def _render_slug_pack_battle(game):
    """Отрисовка экрана боя со скоплением слизней."""
    b = getattr(game, "slug_pack_battle", None) or {}
    slimes = b.get("slimes", [])
    last_log = b.get("last_log", "Скопление слизней шипит и надвигается!")
    max_player_hp = getattr(game, "max_hp", 100)
    armor_def = getattr(game, "armor_defense", 0)
    dodge_pct = int(getattr(game, "dodge_chance", 0) or 0)

    icons = ["🟢" if s.get("alive", False) else "💀" for s in slimes]
    status_bar = f"[ {' '.join(icons)} ]"

    alive_slimes = [s for s in slimes if s.get("alive", False)]
    if not alive_slimes or b.get("is_victory"):
        cores = b.get("cores_dropped", 0)
        loot_lines = "\n".join(b.get("loot_log", []))
        text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚔️ СКОПЛЕНИЕ СЛИЗНЕЙ\n"
            f"{status_bar}\n\n"
            "🏆 ВСЕ СЛИЗНИ ПОВЕРЖЕНЫ!\n\n"
            f"Трофеи с боя:\n{loot_lines}\n"
            f"Итого добыто: Янтарное ядро ×{cores}\n\n"
            f"Твое здоровье: {game.hp}/{max_player_hp} HP\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 Вернуться в яр", callback_data="l5_slug_battle_finish")]
        ])
        return text, kb

    if game.hp <= 0 or b.get("is_defeat"):
        game.hp = 0
        game.active_story_callback = None
        game.slug_pack_battle = None
        text = get_death_text(game, "Слизни погребли тебя под тоннами едкой янтарной жижи.", "Яр слизней")
        kb = get_death_kb()
        return text, kb

    slime_lines = []
    for idx, s in enumerate(slimes, 1):
        if s.get("alive"):
            slime_lines.append(f"{idx}. {s['name']}: {s['hp']}/{s['max_hp']} HP")
        else:
            slime_lines.append(f"{idx}. {s['name']}: 0/{s['max_hp']} HP 💀")
    slimes_text = "\n".join(slime_lines)

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚔️ СКОПЛЕНИЕ СЛИЗНЕЙ\n"
        f"{status_bar}\n\n"
        f"{slimes_text}\n\n"
        f"Твое здоровье: {game.hp}/{max_player_hp} HP | Броня: {armor_def} DEF | Уворот: {dodge_pct}%\n\n"
        f"Лог боя:\n{last_log}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    rows = [
        [
            InlineKeyboardButton(text="⚔️ Атаковать", callback_data="l5_slug_attack"),
            InlineKeyboardButton(text="🛡️ Полный блок", callback_data="l5_slug_defend"),
        ]
    ]

    pocket_item = getattr(game, "pants_pocket", None)
    if game.equipment.get("pants") == "Кожаные поножи" and pocket_item:
        rows.append([
            InlineKeyboardButton(text=f"Принять {pocket_item}", callback_data="l5_slug_use_pocket")
        ])

    rows.append([
        InlineKeyboardButton(text="🏃 Отступить", callback_data="l5_slug_flee")
    ])

    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def handle_location_5_slug_pit(data, game, uid):
    """Обработать события на локации 'Яр Слизней' (канонический сюжет L5)."""
    text = None
    kb = None

    # Вход на локацию
    if data in ("slug_pit_start", "location_enter_5", "l5_1a"):
        game.reset_nav()
        game.current_location = "Яр Слизней"
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Яр Слизней" not in unlocked:
            unlocked.append("Яр Слизней")
            game.unlocked_locations = unlocked

        # Если сюжетная ветка L5 уже полностью завершена — мирное пребывание
        if game.is_story_flag_set("l5_completed"):
            text = (
                "Ты стоишь на краю Яра Слизней.\n\n"
                "В глубине низины тихо пульсирует бирюзовый свет грибов. "
                "Яр теперь спокоен: по стенам медленно стекает смола, "
                "а земля свободна для сбора ресурсов и установки ловушек."
            )
            kb = get_main_kb(game)
            return text, kb

        # Если сюжет уже начат и сохранён шаг:
        if getattr(game, "story_state", None) and str(game.story_state).startswith("l5_") and data != "l5_1a" and game.story_state != data:
            return handle_location_5_slug_pit(game.story_state, game, uid)

        # Окно 1.1: L5.1a — Спуск в туманный яр
        game.story_state = "l5_1a"
        text = (
            "Ты замечаешь яр, только когда земля под ногами начинает проваливаться.\n\n"
            "Сверху сквозь белесый туман открывается вид на крутой провал, где в воздухе плавно кружит зеленоватая взвесь. "
            "Она пахнет сырой землёй, смолой и чем-то незнакомым, но живым.\n\n"
            "Склон крутой, скользкий. Корни торчат из глины, словно скрюченные пальцы. "
            "Будь на тебе тяжелый сланцевый панцирь — ты бы кубарем сорвался вниз. "
            "Но мягкая кожаная броня сидит плотно, не сковывая движений, и ты аккуратно спускаешься боком, "
            "цепляясь за выступы и стараясь не скользить."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👣 Спуститься ниже", callback_data="l5_1b")]
        ])

    # Окно 1.2: L5.1b — Сияние в низине, болотные ягоды и записка
    elif data == "l5_1b":
        game.story_state = "l5_1b"
        text = (
            "Внизу темнее, чем наверху. Но не совсем темно.\n\n"
            "На стенах яра фосфоресцируют исполинские грибы со шляпками в две ладони, заливая глину бирюзовым светом. "
            "Они старые, трухлявые и сочатся едкой горечью.\n\n"
            "У самого подножия стены чернеет куст болотных ягод. Несколько перезревших ягод упали в мокрую глину: "
            "к ним уже сползлись две крохотные слизи, жадно и с хлюпаньем высасывая приторный сладкий сок.\n\n"
            "Вся земля под ногами липкая, каждый шаг тяжело чавкает.\n\n"
            "В памяти всплывает строчка с найденного у ручья листа: «В низине после темноты виден огонь. Я туда не ходил». "
            "Тот бедолага принял свечение яра за костёр."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🍄 Срезать гриб со стены", callback_data="l5_1c")],
            [InlineKeyboardButton(text="👣 Спуститься на дно", callback_data="l5_2a")],
            [InlineKeyboardButton(text="🔍 Осмотреть стены", callback_data="l5_1b_walls")]
        ])

    # Окно 1.3: L5.1c — Обманчивый исполин (Ожог и целебное исцеление)
    elif data == "l5_1c":
        game.story_state = "l5_1c"
        text = (
            "Ты протягиваешь руку к крупной бирюзовой шляпке на уровне плеча и пробуешь её поддеть.\n\n"
            "Старая ткань гриба с шипением лопается под пальцами! Из разрыва брызжет едкая мутная сукровица, "
            "мгновенно прожигая кожу руки жгучим холодом. Ты отдёргиваешь руку, шипя от боли.\n\n"
            "Но отшатнувшись назад, ты задеваешь локтем выступ глины и сдираешь янтарную корочку со старого, неприметного ядра слизня.\n\n"
            "Из трещины прямо на обожжённую кожу вытекает капля густой янтарной смолы. Боль моментально стихает! "
            "Смола затягивает ожог тончайшей дышащей плёнкой, полностью заживляя рану прямо на глазах.\n\n"
            "Это же природное лекарство! Если сварить такую смолу с ягодами и залить в прочный пузырёк, "
            "получится мощнейшее целебное зелье."
        )
        buttons = []
        if not game.is_story_flag_set("l5_mushroom_gathered"):
            buttons.append([InlineKeyboardButton(text="🍄 Собрать молодой гриб", callback_data="l5_gather_mushroom")])
        buttons.append([InlineKeyboardButton(text="👣 Спуститься на дно", callback_data="l5_2a")])
        buttons.append([InlineKeyboardButton(text="🔍 Осмотреть стены", callback_data="l5_1b_walls")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Окно 2: L5.1a — Сбор молодого гриба и первого ядра
    elif data == "l5_gather_mushroom":
        game.story_state = "l5_gather_mushroom"
        if not game.is_story_flag_set("l5_mushroom_gathered"):
            game.inventory["Светящийся гриб"] = game.inventory.get("Светящийся гриб", 0) + 1
            game.inventory["Янтарное ядро"] = game.inventory.get("Янтарное ядро", 0) + 1
            game.adjust_narrative_karma("pragmatism", 2)
            game.adjust_narrative_karma("observation", 1)
            game.set_story_flag("l5_mushroom_gathered", True)

        text = (
            "Ты высматриваешь у каменного выступа аккуратную молодую шляпку, едва начавшую наливаться бирюзовым соком, "
            "и осторожно срезаешь её в сумку.\n\n"
            "Прямо под грибницей в глине обнаруживается целое, неповреждённое янтарное ядро размером с крупный орех.\n\n"
            "Сквозь гладкую полупрозрачную оболочку видно, как внутри колышется густая золотистая смола. "
            "Такие ядра внутри живых слизней очень нежные и легко лопаются от ударов, но в руках они на удивление удобны и не пачкаются. "
            "Эта смола пригодится и для заправки фонаря, и для варки целебного янтарного зелья.\n\n"
            "Получено: Светящийся гриб ×1.\n"
            "Получено: Янтарное ядро ×1."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👣 Спуститься на дно", callback_data="l5_2a")],
            [InlineKeyboardButton(text="🔍 Осмотреть стены", callback_data="l5_1b_walls")]
        ])

    # Окно 3: L5.1b — Осмотр стен: Следы когтей
    elif data == "l5_1b_walls":
        game.story_state = "l5_1b_walls"
        game.set_story_flag("saw_wall_scratches", True)
        if not game.is_story_flag_set("l5_walls_karma"):
            game.adjust_narrative_karma("observation", 2)
            game.set_story_flag("l5_walls_karma", True)

        text = (
            "Ты проводишь рукой по стене, осторожно обходя липкие потёки.\n\n"
            "Под налётом обнажаются ровные слои глины и серого сланца. В одном месте слизь содрана, "
            "и под ней видны глубокие свежие царапины.\n\n"
            "Пять параллельных борозд.\n\n"
            "Ты прикладываешь ладонь. Борозды слишком широкие для когтей лесного зверя и слишком ровные для скола камня. "
            "Кто-то отчаянно цеплялся за скользкий уступ, пытаясь выбраться из низины наверх.\n\n"
            "Слизь уже затягивает борозды. Скоро от них ничего не останется."
        )
        buttons = []
        if not game.is_story_flag_set("l5_mushroom_gathered"):
            buttons.append([InlineKeyboardButton(text="🍄 Собрать молодой гриб", callback_data="l5_gather_mushroom")])
        buttons.append([InlineKeyboardButton(text="👣 Спуститься на дно", callback_data="l5_2a")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Окно 4.1: L5.2a — Дно яра (Сырая котловина)
    elif data == "l5_2a":
        game.story_state = "l5_2a"
        text = (
            "Дно яра — плоская сырая площадка размером с небольшую комнату.\n\n"
            "Светящиеся грибы здесь не растут сплошной стеной: лишь редкие, одиночные шляпки пробиваются между пластами мокрого сланца, "
            "мерцая холодным бирюзовым светом в густой темноте.\n\n"
            "Все ручейки прозрачной слизи медленно и непрерывно стекаются к самому центру котловины, где земля кажется зыбкой и густой."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👣 Подойти к центру", callback_data="l5_2b_cocoon")]
        ])

    # Окно 4.2: L5.2b — Янтарный кокон с фонарём
    elif data == "l5_2b_cocoon":
        game.story_state = "l5_2b_cocoon"
        text = (
            "В центре низины лежит массивный кокон размером с походный тюк.\n\n"
            "Он полупрозрачный, янтарного цвета, с густыми прожилками внутри. "
            "Поверхность медленно вздымается и опадает — сжимается и разжимается, словно тяжёлое живое дыхание.\n\n"
            "Внутри кокона что-то тускло поблёскивает. Металл.\n\n"
            "Ты присматриваешься. Сквозь янтарную плёнку виден тёмный каркас, защитные дуги, гранёное стекло и изогнутая ручка. Фонарь!\n\n"
            "Слизь на дне яра течёт со всех сторон и жадно впитывается в основание кокона. "
            "Он растёт прямо на глазах. Ещё немного — и стекло затянет намертво."
        )
        buttons = [
            [InlineKeyboardButton(text="⚡ Попытаться выдернуть фонарь", callback_data="l5_3_step")]
        ]
        if not game.is_story_flag_set("l5_slime_gathered"):
            buttons.append([InlineKeyboardButton(text="🍯 Собрать сочившуюся слизь", callback_data="l5_gather_slime")])
        buttons.append([InlineKeyboardButton(text="🚪 Не трогать и уйти", callback_data="l5_leave_early")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Окно 5: L5.2a — Сбор сочившейся янтарной слизи
    elif data == "l5_gather_slime":
        game.story_state = "l5_gather_slime"
        if not game.is_story_flag_set("l5_slime_gathered"):
            game.inventory["Янтарное ядро"] = game.inventory.get("Янтарное ядро", 0) + 2
            game.adjust_narrative_karma("pragmatism", 1)
            game.adjust_narrative_karma("observation", 1)
            game.set_story_flag("l5_slime_gathered", True)

        text = (
            "Ты соскабливаешь со сланца несколько комков застывших выделений.\n\n"
            "Это плотная смола, вытекшая из лопнувших янтарных ядер древних слизней. "
            "Она тёплая, маслянистая, пахнет смолой и древесным соком. "
            "В руках на воздухе масса быстро густеет, превращаясь в золотистую смолу.\n\n"
            "Получено: Янтарное ядро ×2."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Попытаться выдернуть фонарь", callback_data="l5_3_step")],
            [InlineKeyboardButton(text="🚪 Не трогать и уйти", callback_data="l5_leave_early")]
        ])

    # Окно 6: L5.2b — Не трогать и уйти (Ранний уход)
    elif data == "l5_leave_early":
        game.adjust_narrative_karma("intervention", -2)
        game.adjust_narrative_karma("compassion", 1)
        game.adjust_narrative_karma("pragmatism", 2)
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l5_completed", True)
        if "l5_completed_day" not in game.story_flags:
            game.story_flags["l5_completed_day"] = getattr(game, "day", 1)
        game.set_story_flag("lantern_taken", False)
        game.story_state = None

        has_lantern = (
            game.equipment.get("hand_left") == "Старый фонарь"
            or game.inventory.get("Старый фонарь", 0) > 0
        )
        crafts_to_unlock = ["Пузырёк", "Янтарное зелье", "Приманка для слизней"]
        if has_lantern:
            crafts_to_unlock.append("Зарядить фонарь")
        for r in crafts_to_unlock:
            if hasattr(game, "unlock_craft"):
                game.unlock_craft(r)
            elif r not in getattr(game, "unlocked_crafts", []):
                game.unlocked_crafts.append(r)

        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Мохнатая пещера" not in unlocked and "Мохнатая Пещера" not in unlocked:
            unlocked.append("Мохнатая пещера")
            game.unlocked_locations = unlocked

        text = (
            "Ты смотришь на пульсирующий кокон, на ручейки слизи и холодные бирюзовые отсветы грибов. "
            "Трогать это место больше не хочется.\n\n"
            "Развернувшись, ты начинаешь подъём по уступам яра. Чавканье под ногами звучит гулко и тревожно.\n\n"
            "Наверху ты с облегчением счищаешь липкий налёт с сапог и долго вытираешь ладони о жесткую траву. "
            "Свечение внизу постепенно скрывается за кромкой обрыва."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 Вернуться в лагерь", callback_data="back")]
        ])

    # Окно 7.1: L5.3_step — Пробуждение стены и гигантское ядро
    elif data == "l5_3_step":
        game.story_state = "l5_3_step"
        text = (
            "Ты делаешь осторожный шаг к кокону. Липкая жижа жадно чавкает под ногами, сапоги вязнут почти по щиколотку.\n\n"
            "Ты уже протягиваешь руку, когда замечаешь движение у дальней стены.\n\n"
            "Сначала кажется, что глиняный пласт оползает вниз. Но затем ты понимаешь: от стены медленно отслаивается колоссальная бесформенная масса размером со взрослого человека.\n\n"
            "Полупрозрачное тело сползает на дно, излучая тусклое ядовито-зелёное свечение. "
            "Но в самой глубине его брюха медленно разгорается и бьётся огромное тёмно-янтарное ядро величиной с мельничный жернов!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛑 Замереть на месте", callback_data="l5_3_approach")]
        ])

    # Окно 7.2: L5.3_approach — Приближение исполина
    elif data == "l5_3_approach":
        game.story_state = "l5_3_approach"
        text = (
            "Существо не спешит атаковать.\n\n"
            "Оно медленно проплывает мимо тебя на расстоянии вытянутой руки. От студенистой туши веет волной тяжёлого тепла и удушливым сладковатым духом. "
            "Сквозь зелёное желе колышется янтарное ядро, наполняя низину приглушённым золотым жаром.\n\n"
            "Исполин наплывает на кокон, обволакивая его своей массой. Пульсация кокона и ядра сливаются в единый мощный ритм.\n\n"
            "Ты застываешь на месте, не смея пошевелиться."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤫 Затаить дыхание", callback_data="l5_3_slug")]
        ])

    # Окно 7.3: L5.3_slug — Реакция существа и выбор действия
    elif data == "l5_3_slug":
        game.story_state = "l5_3_slug"
        game.set_story_flag("met_giant_slug", True)

        has_pet = bool(game.equipment.get("pet"))
        if has_pet:
            pet_text = (
                "Котёнок высовывает голову из-под твоей куртки, широко раскрывает глаза и издаёт странный, "
                "вибрирующий утробный звук — не шипение и не мяуканье.\n\n"
                "Зелёная туша вздрагивает, по студенистому телу пробегает рябь, а янтарное ядро на миг тускнеет. "
                "Потеряв интерес к кокону, слизень неохотно отползает в сторону, разворачивается и начинает подниматься по стене, "
                "оставляя широкий мокрый след."
            )
        else:
            pet_text = (
                "Ты задерживаешь дыхание до звона в ушах. Существо замирает, словно пробуя воздух на вкус. "
                "Затем оно неспешно сползает с кокона и начинает взбираться вверх по глиняной стене яра, "
                "унося тёплое сияние ядра во тьму."
            )

        text = (
            f"{pet_text}\n\n"
            "Тварь уползает вверх, но янтарная плёнка на коконе начинает стремительно схватываться коркой."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Быстро вырвать фонарь", callback_data="l5_3a_force")],
            [InlineKeyboardButton(text="⏳ Подождать и вскрыть кокон", callback_data="l5_3b_wait")],
            [InlineKeyboardButton(text="🚪 Оставить кокон и уйти", callback_data="l5_3c_leave")]
        ])

    # Окно 8: L5.3a — Силовой разрыв кокона (Ожог и фонарь)
    elif data == "l5_3a_force":
        game.story_state = "l5_3a_force"
        game.hp = max(1, getattr(game, "hp", 100) - 5)
        game.inventory["Старый фонарь"] = game.inventory.get("Старый фонарь", 0) + 1
        game.lantern_durability = 20
        game.adjust_narrative_karma("intervention", 4)
        game.adjust_narrative_karma("compassion", -1)
        game.adjust_narrative_karma("pragmatism", 3)
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("lantern_taken", True)

        text = (
            "Ты бросаешься к кокону!\n\n"
            "Янтарная оболочка на ощупь тёплая и упругая, как сырая кожа. Ты впиваешься в неё пальцами — слизь натягивается, но не рвётся.\n\n"
            "Собрав силы, ты с размаху бьёшь локтем. Плёнка с влажным хрустом лопается!\n\n"
            "Горячая жижа выплёскивается наружу, обжигая ладони немеющим жаром. "
            "Смола из карманов сейчас не поможет — в спешке и суматохе некогда вскрывать ядра, ладони саднит, но ты терпишь боль. "
            "Сжав зубы, ты выдёргиваешь металлический фонарь за цепочку.\n\n"
            "Корпус вымазан в смоле, но стекло цело. Внутри сухо, резервуар полон чистого масла на 20 зажжений — если жечь бережно, "
            "света хватит надолго.\n\n"
            "Прижав добычу к груди, ты карабкаешься по скользкому склону прочь со дна.\n\n"
            "Получен предмет: Старый фонарь [20/20].\n"
            "Получен урон: −5 HP."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Осмотреться на дне", callback_data="l5_4_amulet")],
            [InlineKeyboardButton(text="🧗 Выбраться наверх", callback_data="l5_5_lantern")],
        ])

    # Окно 9.1: L5.3b_wait — Срезка крупного гриба у кокона
    elif data == "l5_3b_wait":
        game.story_state = "l5_3b_wait"
        text = (
            "Ты решаешь не рисковать руками и садишься на корточки, терпеливо выжидая, пока огромная тварь окончательно скроется за верхним краем яра.\n\n"
            "Вспомнив, как слизь сторонится грибниц, ты осматриваешь основание кокона. "
            "Прямо из глины под ним растёт крупный светящийся гриб размером с две твои ладони.\n\n"
            "Ты аккуратно срезаешь массивную бирюзовую шляпку и подносишь её вплотную к натянутой янтарной плёнке.\n\n"
            "Реакция идёт медленно, потому что гриб уже старый и растерял почти всю свою силу. "
            "От холодного свечения по плёнке еле заметно бегут редкие пузыри, янтарный слой с трудом размягчается. Приходится ждать."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🍄 Поднести гриб к кокону", callback_data="l5_3b_extract")]
        ])

    # Окно 9.2: L5.3b_extract — Извлечение чистого фонаря
    elif data == "l5_3b_extract":
        game.story_state = "l5_3b_extract"
        game.inventory["Старый фонарь"] = game.inventory.get("Старый фонарь", 0) + 1
        game.lantern_durability = 20
        game.adjust_narrative_karma("observation", 4)
        game.adjust_narrative_karma("pragmatism", 1)
        game.adjust_narrative_karma("intervention", 2)
        game.adjust_narrative_karma("compassion", 1)
        game.set_story_flag("lantern_taken", True)

        text = (
            "Терпение берёт своё. Под постоянным воздействием гриба янтарная оболочка истончается, натягиваясь до прозрачной плёнки, "
            "пока тонкий слой тихо не щёлкает, расходясь в стороны.\n\n"
            "Тёплая смолистая влага медленно стекает в глину, не обжигая кожу.\n\n"
            "Ты осторожно вынимаешь фонарь. Он выходит из кокона чистым: металл лишь слегка потемнел, стекло абсолютно целое, "
            "а внутри плещется масло. Его хватит на 20 исследований.\n\n"
            "Ты убираешь находку в рюкзак.\n\n"
            "Получен предмет: Старый фонарь [20/20]."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Осмотреться", callback_data="l5_4_amulet")]
        ])

    # Окно 10: L5.3c_leave — Оставить кокон лесу
    elif data == "l5_3c_leave":
        game.story_state = "l5_3c_leave"
        game.adjust_narrative_karma("compassion", 3)
        game.adjust_narrative_karma("observation", 3)
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("lantern_taken", False)

        text = (
            "Ты опускаешь руки и делаешь шаг назад.\n\n"
            "Гигантская тварь уже скрылась наверху, но ручейки слизи, стекающие по дну яра, уже жадно затягивают разрыв на коконе, "
            "оставленный массивным телом слизня. Ты своими глазами видишь, как жижа мгновенно схватывается коркой.\n\n"
            "Через день стекло фонаря окончательно покроется толстым янтарём. Через неделю железо растворится в янтарной толще. "
            "Лес забирает своё обратно, и спорить с этим не стоит.\n\n"
            "Развернувшись, ты начинаешь размеренный подъём по склону, оставляя светящуюся низину за спиной."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧗 Подняться из яра", callback_data="l5_5_left")]
        ])

    # Окно 11: L5.4_amulet — Находка на дне: Костяной амулет охотника
    elif data == "l5_4_amulet":
        game.story_state = "l5_4_amulet"
        game.inventory["Костяной амулет охотника"] = game.inventory.get("Костяной амулет охотника", 0) + 1
        game.set_story_flag("found_hunter_amulet", True)
        game.adjust_narrative_karma("observation", 3)
        game.adjust_narrative_karma("pragmatism", 1)

        text = (
            "Перед тем как подняться, ты обходишь дно яра вдоль замшелой стены.\n\n"
            "В липком осадке белеют старые кости крупного оленя. А рядом, наполовину влипшая в глину, "
            "темнеет небольшая пластинка на истлевшем шнурке.\n\n"
            "Ты подбираешь её и счищаешь налёт.\n\n"
            "Это пластинка из полированной кости. На ней глубоко прорезан знакомый знак: три короткие насечки, "
            "перечёркнутые одной длинной поперечной линией — в точности такой же, как на вековых деревьях просеки. "
            "Один из охотников обронил его в спешке, спасаясь из этого яра.\n\n"
            "Получен предмет: Костяной амулет охотника."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее ➔", callback_data="l5_5_lantern")]
        ])

    # Окно 12.1: L5.5_lantern — Финал с фонарём (Выход из яра)
    elif data == "l5_5_lantern":
        game.set_story_flag("l5_completed", True)
        if "l5_completed_day" not in game.story_flags:
            game.story_flags["l5_completed_day"] = getattr(game, "day", 1)
        game.story_state = None
        for r in ("Зарядить фонарь", "Пузырёк", "Янтарное зелье", "Приманка для слизней"):
            if hasattr(game, "unlock_craft"):
                game.unlock_craft(r)
            elif r not in getattr(game, "unlocked_crafts", []):
                game.unlocked_crafts.append(r)

        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Мохнатая пещера" not in unlocked and "Мохнатая Пещера" not in unlocked:
            unlocked.append("Мохнатая пещера")
            game.unlocked_locations = unlocked

        has_pet = bool(game.equipment.get("pet"))
        pet_note = (
            "\n\nКотёнок с любопытством тычется мокрым носом в прохладное стекло фонаря и забавно фыркает на своё отражение."
            if has_pet else ""
        )

        text = (
            "Ты выбираешься из яра наверх, жадно вдыхая свежий ночной воздух. На чистой траве оттираешь ладони от липкого налёта.\n\n"
            "Достав фонарь, ты поднимаешь его перед собой к звёздам. Стекло поблёскивает, а внутри плещется янтарное масло.\n\n"
            "В памяти невольно всплывает, как во второй день в лесу с хрустом сломался факел, когда ты отбивался от старого волка у пня. "
            "С тех пор приходилось шарахаться от каждого шороха в темноте. Но теперь в твоих руках снова есть надёжный, защищённый свет."
            f"{pet_note}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 Вернуться в лагерь", callback_data="back")]
        ])

    # Окно 12.2: L5.5_left — Финал без фонаря (Выход из яра)
    elif data == "l5_5_left":
        game.set_story_flag("l5_completed", True)
        if "l5_completed_day" not in game.story_flags:
            game.story_flags["l5_completed_day"] = getattr(game, "day", 1)
        game.story_state = None
        has_lantern = (
            game.equipment.get("hand_left") == "Старый фонарь"
            or game.inventory.get("Старый фонарь", 0) > 0
        )
        crafts_to_unlock = ["Пузырёк", "Янтарное зелье", "Приманка для слизней"]
        if has_lantern:
            crafts_to_unlock.append("Зарядить фонарь")
        for r in crafts_to_unlock:
            if hasattr(game, "unlock_craft"):
                game.unlock_craft(r)
            elif r not in getattr(game, "unlocked_crafts", []):
                game.unlocked_crafts.append(r)

        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Мохнатая пещера" not in unlocked and "Мохнатая Пещера" not in unlocked:
            unlocked.append("Мохнатая пещера")
            game.unlocked_locations = unlocked

        text = (
            "Ты выбираешься из яра и долго стоишь у кромки обрыва, глядя в глубину.\n\n"
            "Там, на дне, ровно пульсирует холодное бирюзовое свечение — словно неторопливое дыхание неведомого спящего исполина. "
            "Где-то в темноте растёт янтарный кокон, переваривая чужой металл.\n\n"
            "В чаще снова темно. Но теперь ты знаешь: ночной лес не мёртв и не пуст. В нём кипит своя жизнь, переплавляющая старое в новое.\n\n"
            "Поправив лямки рюкзака, ты шагаешь прочь по тропе."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 Вернуться в лагерь", callback_data="back")]
        ])

    elif data == "l5_bait_menu":
        from keyboards import get_l5_bait_menu_kb
        text = (
            "🍯 <b>ПРИМАНКА ДЛЯ СЛИЗНЕЙ</b>\n\n"
            "Густой сладкий аромат давленых ягод растекается по всему яру. "
            "Приманка активна весь текущий день.\n\n"
            "• Слизни жадно сползаются со всех расщелин.\n"
            "• При обычном исследовании яра шанс привлечь скопление слизней составляет 50%.\n"
            "• За ночь слизни без остатка сожрут приманку.\n\n"
            "Ты можешь устроить засаду прямо сейчас!"
        )
        kb = get_l5_bait_menu_kb()

    elif data == "l5_slug_ambush":
        return start_slug_pack_battle(game, count=6)

    elif data == "l5_bait_remove":
        game.slug_bait_active = False
        game.inventory["Приманка для слизней"] = game.inventory.get("Приманка для слизней", 0) + 1
        game.add_log("Вы осторожно сняли приманку для слизней и вернули её в инвентарь.")
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "l5_slug_battle":
        return _render_slug_pack_battle(game)

    elif data == "l5_slug_attack":
        b = getattr(game, "slug_pack_battle", None) or {}
        slimes = b.get("slimes", [])
        target = next((s for s in slimes if s.get("alive")), None)
        if not target:
            b["is_victory"] = True
            game.slug_pack_battle = b
            return _render_slug_pack_battle(game)

        weapon = game.equipment.get("hand_right")
        if weapon in ("Охотничье сланцевое копьё", "🔱 Охотничье сланцевое копьё"):
            player_dmg = random.randint(19, 24)
        elif weapon == "Окованный посох":
            player_dmg = random.randint(8, 10)
        elif weapon == "Крепкий посох":
            player_dmg = random.randint(5, 7)
        else:
            player_dmg = random.randint(2, 4)

        target["hp"] -= player_dmg
        hero_log = f"⚔️ Ты бьёшь по [{target['name']}] на {player_dmg} урона!"
        if target["hp"] <= 0:
            target["hp"] = 0
            target["alive"] = False
            hero_log += f"\n💥 [{target['name']}] лопается с брызгами студня! (💀)"

        alive_slimes = [s for s in slimes if s.get("alive")]
        if not alive_slimes:
            b["is_victory"] = True
            if not game.is_story_flag_set("l5_slug_pack_defeated"):
                game.kills_count = getattr(game, "kills_count", 0) + 1
            game.set_story_flag("l5_slug_pack_defeated", True)
            cores_found = 0
            loot_log = []
            for s in slimes:
                if random.random() < 0.5:
                    cores_found += 1
                    loot_log.append(f"• {s['name']}: 🟠 Янтарное ядро извлечено целым!")
                else:
                    loot_log.append(f"• {s['name']}: ядро разбилось от ударов")
            b["cores_dropped"] = cores_found
            b["loot_log"] = loot_log
            if cores_found > 0:
                game.inventory["Янтарное ядро"] = game.inventory.get("Янтарное ядро", 0) + cores_found
            b["last_log"] = hero_log
            game.slug_pack_battle = b
            return _render_slug_pack_battle(game)

        dodge_chance = int(getattr(game, "dodge_chance", 0) or 0)
        player_def = game.armor_defense
        slime_logs = []
        for s in alive_slimes:
            roll = random.randint(1, 100)
            if roll <= dodge_chance:
                slime_logs.append(f"• {s['name']}: Промахнулся!")
            else:
                raw_dmg = random.randint(5, 15)
                actual_dmg = max(1, raw_dmg - player_def)
                game.hp = max(0, game.hp - actual_dmg)
                slime_logs.append(f"• {s['name']}: Ударил на {actual_dmg} (атака {raw_dmg} − броня {player_def})")

        b["round"] = b.get("round", 1) + 1
        b["last_log"] = hero_log + "\n" + "\n".join(slime_logs)
        if game.hp <= 0:
            b["is_defeat"] = True
        game.slug_pack_battle = b
        return _render_slug_pack_battle(game)

    elif data == "l5_slug_defend":
        b = getattr(game, "slug_pack_battle", None) or {}
        slimes = b.get("slimes", [])
        alive_slimes = [s for s in slimes if s.get("alive")]
        if not alive_slimes:
            b["is_victory"] = True
            if not game.is_story_flag_set("l5_slug_pack_defeated"):
                game.kills_count = getattr(game, "kills_count", 0) + 1
            game.set_story_flag("l5_slug_pack_defeated", True)
            game.slug_pack_battle = b
            return _render_slug_pack_battle(game)

        slime_logs = []
        block_dmg = len(alive_slimes)
        for s in alive_slimes:
            game.hp = max(0, game.hp - 1)
            slime_logs.append(f"• {s['name']}: В блок — 1 урон.")

        b["round"] = b.get("round", 1) + 1
        b["last_log"] = (
            f"🛡️ Ты ушёл в полный блок, закрываясь от брызг едкой слизи!\n"
            + "\n".join(slime_logs)
            + f"\nПолучено в блок: {block_dmg} урона."
        )
        if game.hp <= 0:
            b["is_defeat"] = True
        game.slug_pack_battle = b
        return _render_slug_pack_battle(game)

    elif data == "l5_slug_use_pocket":
        b = getattr(game, "slug_pack_battle", None) or {}
        pocket_item = getattr(game, "pants_pocket", None)
        if not pocket_item:
            return _render_slug_pack_battle(game)

        from modules.items import ITEMS
        if pocket_item == "Янтарное зелье":
            heal_amount = min(game.max_hp - game.hp, 70)
            game.hp += heal_amount
            game.inventory["Пузырёк"] = game.inventory.get("Пузырёк", 0) + 1
            action_log = f"🍹 Ты принимаешь Янтарное зелье! (+{heal_amount} HP). Пустой пузырёк убран в рюкзак."
        else:
            eff = ITEMS.get(pocket_item, {}).get("effects", {})
            hp_gain = eff.get("hp", 20)
            heal_amount = min(game.max_hp - game.hp, hp_gain)
            game.hp += heal_amount
            action_log = f"🍽️ Ты принимаешь {pocket_item} из футляра на поножах! (+{heal_amount} HP)."

        game.pants_pocket = None

        slimes = b.get("slimes", [])
        alive_slimes = [s for s in slimes if s.get("alive")]
        dodge_chance = int(getattr(game, "dodge_chance", 0) or 0)
        player_def = game.armor_defense
        slime_logs = []
        for s in alive_slimes:
            roll = random.randint(1, 100)
            if roll <= dodge_chance:
                slime_logs.append(f"• {s['name']}: Промахнулся!")
            else:
                raw_dmg = random.randint(5, 15)
                actual_dmg = max(1, raw_dmg - player_def)
                game.hp = max(0, game.hp - actual_dmg)
                slime_logs.append(f"• {s['name']}: Ударил на {actual_dmg} (атака {raw_dmg} − броня {player_def})")

        b["round"] = b.get("round", 1) + 1
        b["last_log"] = action_log + "\n\n" + "\n".join(slime_logs)
        if game.hp <= 0:
            b["is_defeat"] = True
        game.slug_pack_battle = b
        return _render_slug_pack_battle(game)

    elif data == "l5_slug_flee":
        game.slug_pack_battle = None
        game.active_story_callback = None
        game.add_log("Ты разорвал дистанцию и вырвался из кольца слизней наверх.")
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "l5_slug_battle_finish":
        game.slug_pack_battle = None
        game.active_story_callback = None
        game.add_log("Скопление слизней разбито. Трофеи собраны.")
        text = game.get_ui()
        kb = get_main_kb(game)

    # ──────────────────────────────────────────────────────────────────────────
    # ГЛАВА 2: ОХОТА НА ИСПОЛИНА И ТАЙНА ПРОМОИНЫ
    # ──────────────────────────────────────────────────────────────────────────

    # Экран 1: L5.2.1 — Стоянка на уступе (Размышления)
    elif data == "l5_2_1":
        game.story_state = "l5_2_1"
        text = (
            "Ты уже который день прочёсываешь сырой лабиринт яра, и этот сухой глиняный уступ у сланцевой плиты стал настоящим спасением. "
            "Здесь нет белесого тумана, а на камне чернеет старая копоть костра — люди тут бывали, место надёжное.\n\n"
            "Но расслабляться нельзя. Образ той громадины ростом с человека, уползшей от кокона в темноту, до сих пор стоит перед глазами. "
            "Пока эта тварь бродит рядом, спокойного сна не будет. Сжав оружие, ты спускаешься вниз, чтобы отыскать её логово."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👣 Выйти на разведку", callback_data="l5_2_2")]
        ])

    # Экран 2: L5.2.2 — Следы на дне яра
    elif data == "l5_2_2":
        game.story_state = "l5_2_2"
        text = (
            "На дне оврага тянется широкая примятая полоса — слой слизи, какой оставляют за собой крупные слаймы, только эта раза в три шире обычного. "
            "Тварь такого колоссального веса не может прыгать при обычном движении: она тяжело и непрерывно ползла вперёд, продавливая глину.\n\n"
            "Рядом видны глубокие отпечатки копыт молодого оленя. Животное сильно хромало, волоча заднюю ногу со старым ржавым капканом. "
            "Олень пытался спастись, но хищник неумолимо настигал его. След ведёт в тупиковую лощину."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🐾 Идти по следу", callback_data="l5_2_3")]
        ])

    # Экран 3: L5.2.3 — Вход в заводь
    elif data == "l5_2_3":
        game.story_state = "l5_2_3"
        text = (
            "Борозда огибает острый сланцевый гребень и уводит в глухую каменистую лощину. "
            "Главное русло яра уходит дальше — туда, где шумит сток и чернеет зев глубокой промоины, но слизень свернул именно в тупик.\n\n"
            "Из глубины лощины доносится глухой влажный шлепок и отчаянный, захлебнувшийся хрип зверя. Охота уже подошла к концу. "
            "Стараясь не чавкать сапогами по ослизлым камням, ты осторожно подбираешься к выступу скалы."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤫 Прокрасться в заводь", callback_data="l5_2_4")]
        ])

    # Экран 4: L5.2.4 — Заводь и финал охоты
    elif data == "l5_2_4":
        game.story_state = "l5_2_4"
        text = (
            "В центре каменистой заводи замер тёмно-зелёный Исполинский слайм размером с человека. Он не прозрачный, как мелкие сородичи, а мутный и тёмный.\n\n"
            "Перед ним лежит обессилевший олень со старым капканом на ноге. Спасать зверя поздно. "
            "Слайм тяжело колышется на месте, натягивая своё студенистое тело. "
            "В глубине мутной массы едва различим силуэт ядра, от которого исходит слабое, еле заметное свечение."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Следить за тварью", callback_data="l5_2_5")]
        ])

    # Экран 5: L5.2.5 — Уязвимость ядра
    elif data == "l5_2_5":
        game.story_state = "l5_2_5"
        text = (
            "Слайм сжимается, расплываясь по земле, словно пружина, и резко выбрасывает всю массу вперёд! Олень дёргается, и слайм со шлепком врезается прямо в скалу.\n\n"
            "От удара желе растекается по камню плоской лепёшкой. На какую-то долю секунды светящееся ядро оказывается прямо у самой поверхности натянутой оболочки. "
            "Но слайм тут же стягивается обратно в ком и вторым наплывом накрывает добычу целиком, скрывая её в толще своей студенистой туши."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💡 Оценить слабость", callback_data="l5_2_6")]
        ])

    # Экран 6: L5.2.6 — Тактическое решение
    elif data == "l5_2_6":
        game.story_state = "l5_2_6"
        game.set_story_flag("l5_arena_unlocked", True)
        text = (
            "Всё встало на свои места. Судя по огромному объёму плотного желе, пробить эту массу до ядра обычными ударами не удастся — оружие просто увязнет. "
            "Но если подловить момент, когда слайм распластается о стену, можно ударить прямо по обнажившемуся ядру. "
            "Пропитанный соком гриба посох прожжёт желе и не даст ему восстановиться.\n\n"
            "Сейчас тварь занята добычей и почти неподвижна. Самое время подготовиться к бою. Запомнив проход в лощину, ты отходишь на стоянку."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕️ Отступить в лагерь", callback_data="back")]
        ])

    # Экран 7: L5.arena_start — Вход на арену
    elif data == "l5_arena_start":
        game.story_state = "l5_arena_start"
        text = (
            "Ты стоишь на входе в каменистую заводь. Исполинский слайм всё так же лежит посреди площадки, тяжело и медленно переваривая добычу. "
            "Он почти не двигается, лишь по мутной тёмно-зелёной поверхности изредка пробегает студенистая рябь.\n\n"
            "Этим оцепенением нужно пользоваться прямо сейчас, пока он малоподвижен."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Напасть на слайма", callback_data="l5_boss_fight")],
            [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="back")]
        ])

    # Запуск боя с Исполинским слаймом
    elif data == "l5_boss_fight":
        return start_battle(game, "giant_slime")

    elif data.startswith("slime_battle_"):
        return apply_action(data, game, "giant_slime")

    elif data == "slime_battle_screen":
        battle = getattr(game, "wolf_battle", None)
        if battle and battle.get("wolf_hp", 0) > 0 and getattr(game, "hp", 100) > 0:
            return get_battle_text(game, "giant_slime"), get_battle_kb(game, "giant_slime")
        if game.is_story_flag_set("l5_boss_defeated") or not battle:
            return handle_location_5_slug_pit("l5_2_7", game, uid)

    # Экран побега из заводи Исполина
    elif data == "l5_arena_escape":
        game.story_state = "l5_arena_escape"
        game.wolf_battle = None
        game.ap = 0
        text = (
            "Лёгкие горят огнём от едких испарений, руки немеют, а сердце колотится где-то в горле. Сил больше нет.\n\n"
            "Буквально на волоске от гибели, срывая дыхание и скользя по липкой глине, ты чудом выдираешь ноги из чавкающей жижи. "
            "Двухметровая масса с глухим всплеском оседает позади, не в силах угнаться за тобой по сухим каменным валунам.\n\n"
            "Ты вываливаешься из заводи совершенно без сил, едва держась на ногах. Сейчас главное — добраться до костра и хорошенько отдохнуть."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="back")]
        ])

    # Экран 8: L5.2.7 — Победа над Исполином
    elif data == "l5_2_7":
        game.story_state = "l5_2_7"
        game.wolf_battle = None
        game.set_story_flag("l5_boss_defeated", True)
        game.set_story_flag("boss_giant_slime_defeated", True)
        game.unlock_craft("Охотничье сланцевое копьё")
        game.set_story_flag("l5_arena_unlocked", False)

        # Ломается экипированное оружие (Посох)
        weapon = game.equipment.get("hand_right")
        if weapon in ("Крепкий посох", "Окованный посох"):
            game.equipment["hand_right"] = None
            if weapon in game.inventory:
                game.inventory[weapon] = max(0, game.inventory[weapon] - 1)
                if game.inventory[weapon] == 0:
                    del game.inventory[weapon]
            game.add_log(f"💥 {weapon} сломался от сокрушительного удара о твёрдое ядро!")
        else:
            for s in ("Окованный посох", "Крепкий посох"):
                if game.inventory.get(s, 0) > 0:
                    game.inventory[s] = max(0, game.inventory[s] - 1)
                    if game.inventory[s] == 0:
                        del game.inventory[s]
                    game.add_log(f"💥 {s} сломался от сокрушительного удара о твёрдое ядро!")
                    break

        text = (
            "Улучив момент, ты со всей силы вбиваешь посох прямо в обнажившееся ядро. Раздаётся влажный треск — ядро раскалывается, выплёскивая горячую мутную жижу!\n\n"
            "Но в этот же миг древко в руках с сухим хрустом переламывается. Дерево впитало слишком много едкой слизи слаймов: оно растворялось изнутри и держалось на честном слове. "
            "Удар о твёрдое ядро стал последним — чудо, что посох не рассыпался раньше.\n\n"
            "Тёмно-зелёная масса опадает едкой пеной. Выронив обломок, ты тяжело опускаешься на колени."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👣 Выйти из заводи", callback_data="l5_2_8")]
        ])

    # Экран 9: L5.2.8 — Звуки из промоины
    elif data == "l5_2_8":
        game.story_state = "l5_2_8"
        text = (
            "Опираясь о мокрые камни, ты выходишь из лощины обратно в яр. Тело ломит от усталости, но тишину нарушает странный шум со стороны нижнего склона, куда стекает вся дождевая вода.\n\n"
            "Оттуда, из темноты глубокого провала промоины, доносится глухой металлический лязг, треск ломающихся костей и тяжелое, низкое бульканье. "
            "Этот звук не похож на обычных слизней. Любопытство перевешивает, и ты осторожно спускаешься к промоине."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Заглянуть в промоину", callback_data="l5_2_9")]
        ])

    # Экран 10: L5.2.9 — Ловушка промоины и древний затор
    elif data == "l5_2_9":
        game.story_state = "l5_2_9"
        text = (
            "На дне промоины залёг Древний слайм невероятных размеров, намертво перекрыв вход в пещеру. Выбраться из этой низины он не способен: "
            "стены здесь совершенно отвесные, а в мутной туше скопилось столько тяжёлого хлама — рогов, костей и ржавого железа, — "
            "что подняться наверх ему не под силу. Он сам стал пленником стока.\n\n"
            "Взгляд цепляется за скальный козырёк над входом в пещеру. Там глубоко выбит знакомый знак охотников: три насечки, перечёркнутые линией. "
            "Проход дальше лежит именно через этот грот."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Приглядеться к твари", callback_data="l5_2_10")]
        ])

    # Экран 11: L5.2.10 — Осознание преграды и отступление
    elif data == "l5_2_10":
        game.story_state = "l5_2_10"
        game.set_story_flag("l5_ch2_completed", True)
        game.set_story_flag("l5_ancient_unlocked", True)
        text = (
            "Как это чудовище здесь выживает и чем кормится в каменном мешке — остаётся загадкой.\n\n"
            "Но ясно одно: сквозь спрессованный панцирь из мусора к его ядру невозможно добраться. "
            "Чтобы понять его повадки и найти слабое место, необходимо будет каждый день приходить сюда и наблюдать за ним, выискивая хоть одну брешь для прохода к пещере.\n\n"
            "Без оружия, с пустыми руками и ноющим от усталости телом, ты с трудом поднимаешься по осыпи, цепляясь за выступы камней, чтобы вернуться в лагерь."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="back")]
        ])

    # Окно наблюдения: Логово Древнего (подлокация в меню)
    elif data == "l5_ancient_lair":
        text = (
            "Ты стоишь на краю глубокого разлома, глядя на дно промоины.\n\n"
            "Внизу в мутной жиже тяжело ворочается исполинский Древний слайм, перемалывая в своей туше кости и ржавое железо. "
            "Вход в пещеру под знаком охотников надёжно заблокирован.\n\n"
            "Пока у тебя нет подходящего оружия и снаряжения (копья или крюка), спускаться в этот каменный мешок — верная смерть."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="back")]
        ])

    terminators = ("l5_leave_early", "l5_5_lantern", "l5_5_left", "back", "l5_slug_flee", "l5_slug_battle_finish", "l5_bait_remove", "l5_ancient_lair", "l5_arena_escape")
    if kb == get_main_kb(game) or data in terminators or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        game.active_story_callback = data

    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 6: МОХНАТАЯ ПЕЩЕРА
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_6_furry_cave(data, game, uid):
    """Обработать события на локации 'Мохнатая Пещера' (L6)."""
    text = None
    kb = None

    if data in ("furry_cave_start", "location_enter_6"):
        game.story_state = "furry_cave_start"
        text = (
            "Ты входишь в Мохнатую Пещеру. Воздух здесь тёплый, пахнет дымом, мехом\n"
            "и древними кострами. Стены покрыты слоями налёта, а пол — мягким мхом.\n\n"
            "Что будешь делать?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Осмотреть пещеру", callback_data="furry_examine")],
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Сразу лечь отдохнуть", callback_data="furry_sleep")],
            [InlineKeyboardButton(text="🚶 Уйти", callback_data="furry_leave")],
        ])

    elif data == "furry_leave":
        text = (
            "Ты стоишь ещё мгновение на пороге, вдыхая тёплый воздух.\n"
            "Потом разворачиваешься и выходишь.\n"
            "Снаружи снова сыро и холодно."
        )
        game.story_state = None
        kb = get_main_kb(game)

    elif data == "furry_examine":
        game.adjust_narrative_karma("observation", 1)
        game.story_state = "furry_examine"
        text = (
            "Ты медленно обходишь пещеру.\n"
            "Шкуры на стенах разной свежести. В дальнем углу, под нависшим камнем,\n"
            "лежит небольшой свёрток из той же шкуры. Он аккуратно перевязан тонкой бечёвкой.\n"
            "Рядом — несколько деревянных игл и обрезки меха.\n\n"
            "Кто-то здесь работал недавно."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Развернуть свёрток", callback_data="furry_bundle")],
            [InlineKeyboardButton(text="✋ Не трогать свёрток", callback_data="furry_bundle_leave")],
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_cave_start")],
        ])

    elif data == "furry_bundle":
        game.story_state = "furry_bundle"
        text = (
            "Ты развязываешь бечёвку.\n"
            "Внутри — три хороших куска выделанного меха и короткая надпись,\n"
            "нацарапанная углем на внутренней стороне шкуры:\n\n"
            "«Бери, если нужно.\n"
            "Оставь, если сможешь.»"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎒 Забрать весь мех (+3)", callback_data="furry_take_all")],
            [InlineKeyboardButton(text="✂️ Взять часть (+2)", callback_data="furry_take_part")],
            [InlineKeyboardButton(text="🎁 Положить подарок взамен", callback_data="furry_leave_gift")],
            [InlineKeyboardButton(text="✋ Оставить всё как есть", callback_data="furry_bundle_leave")],
        ])

    elif data == "furry_take_all":
        game.adjust_narrative_karma("pragmatism", 2)
        if not game.is_story_flag_set("furry_bundle_taken") and not game.is_story_flag_set("furry_bundle_part_taken"):
            game.inventory["Мех"] = game.inventory.get("Мех", 0) + 3
            game.set_story_flag("furry_bundle_taken")
            text = (
                "Ты убираешь мех в рюкзак. Свёрток остаётся пустым.\n\n"
                "──────────\n"
                "Получено: Мех ×3"
            )
        else:
            text = "Свёрток уже пуст."
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Лечь отдохнуть", callback_data="furry_sleep")],
        ])

    elif data == "furry_take_part":
        game.adjust_narrative_karma("compassion", 1)
        if not game.is_story_flag_set("furry_bundle_taken") and not game.is_story_flag_set("furry_bundle_part_taken"):
            game.inventory["Мех"] = game.inventory.get("Мех", 0) + 2
            game.set_story_flag("furry_bundle_part_taken")
            text = (
                "Ты берёшь два куска, один оставляешь.\n"
                "Аккуратно заворачиваешь свёрток обратно.\n\n"
                "──────────\n"
                "Получено: Мех ×2"
            )
        else:
            text = "Ты уже взял свою долю."
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Лечь отдохнуть", callback_data="furry_sleep")],
        ])

    elif data == "furry_leave_gift":
        game.adjust_narrative_karma("compassion", 2)
        game.set_story_flag("left_something_in_bundle")
        gift_name = None
        for item in ["Жареное мясо", "Мясо", "Сушёное мясо", "Ягоды", "Палка", "Древесина"]:
            if game.inventory.get(item, 0) > 0:
                game.inventory[item] -= 1
                if game.inventory[item] == 0:
                    del game.inventory[item]
                gift_name = item
                break
        gift_note = f"\n\nТы оставляешь {gift_name} внутри свёртка." if gift_name else ""
        text = (
            "Ты решаешь не брать мех, но оставить что-то взамен.\n"
            f"Ты кладёшь свой дар внутрь, заворачиваешь свёрток и возвращаешь его на место.{gift_note}"
        )
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Лечь отдохнуть", callback_data="furry_sleep")],
        ])

    elif data == "furry_bundle_leave":
        text = "Ты оставляешь всё как нашёл и отходишь от свёртка."
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Лечь отдохнуть", callback_data="furry_sleep")],
        ])

    elif data == "furry_warm":
        game.adjust_narrative_karma("pragmatism", 1)
        game.story_state = "furry_warmed"
        text = (
            "Ты подходишь к тлеющим уголькам.\n"
            "Подбрасываешь немного сухого мха. Пламя неохотно, но поднимается.\n"
            "Пещеру наполняет сухое, ровное тепло.\n"
            "Огонь делает пространство меньше и уютнее."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Посидеть у огня", callback_data="furry_fire_rest")],
            [InlineKeyboardButton(text="💤 Лечь на мох", callback_data="furry_sleep")],
            [InlineKeyboardButton(text="🚶 Выйти из пещеры", callback_data="furry_end")],
        ])

    elif data == "furry_fire_rest":
        game.adjust_narrative_karma("observation", 1)
        if hasattr(game, "heal"):
            game.heal(10)
        else:
            game.hp = min(getattr(game, "max_hp", 100), game.hp + 10)
        text = (
            "Ты садишься ближе к теплу. Некоторое время просто смотришь на огонь\n"
            "и слушаешь, как он тихо потрескивает.\n"
            "Усталость немного отпускает.\n\n"
            "──────────\n"
            "+10 ХП"
        )
        game.story_state = "furry_fire_rested"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💤 Лечь на мох", callback_data="furry_sleep")],
            [InlineKeyboardButton(text="🚶 Выйти из пещеры", callback_data="furry_end")],
        ])

    elif data == "furry_sleep":
        pet_text = ""
        if game.is_story_flag_set("has_pet"):
            pet_name = game.equipment.get("pet") or "Котёнок"
            pet_text = (
                f"\n\n{pet_name} выбирается из-под одежды, топчется кругами на твоей груди\n"
                "и устраивается тёплым клубком. Он мурлычет совсем тихо, почти неслышно.\n"
            )
        text = (
            "Ты ложишься на густой мох. Он пружинит под спиной.\n"
            f"В пещере тепло и почти тихо.{pet_text}\n"
            "Ты закрываешь глаза...\n\n"
            "Ты просыпаешься резко от тихого, настороженного звука!\n"
            "У выхода из пещеры мелькает чья-то спина. Тёмная фигура на мгновение\n"
            "заслоняет свет, а затем растворяется снаружи.\n\n"
            "Ты вскакиваешь — но уже поздно. Снаружи быстро становится тихо."
        )
        game.story_state = "furry_awoken"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎒 Проверить рюкзак", callback_data="furry_loss")],
            [InlineKeyboardButton(text="📦 Осмотреть место свёртка", callback_data="furry_loss")],
            [InlineKeyboardButton(text="🚶 Просто выйти", callback_data="furry_end")],
        ])

    elif data == "furry_loss":
        game.set_story_flag("something_was_taken")
        text = (
            "Ты быстро проверяешь вещи. Всё на месте… почти.\n"
            "Пропала лишь мелкая часть припасов.\n\n"
            "Рядом со свёртком теперь лежит маленький кусок меха — будто в обмен.\n"
            "Ты понимаешь: кто-то зашёл, пока ты спал. Взял немного, и оставил что-то взамен."
        )
        game.story_state = "furry_after_loss"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚪 Выйти из пещеры", callback_data="furry_end")],
        ])

    elif data == "furry_end":
        game.set_story_flag("visited_furry_cave")
        game.set_story_flag("l6_completed")
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Святилище" not in unlocked and "святилище" not in [x.lower() for x in unlocked]:
            unlocked.append("Святилище")
            game.unlocked_locations = unlocked
            game.add_log("Открыт путь на вершину: Святилище!")

        text = (
            "Ты ещё раз окидываешь взглядом пещеру.\n"
            "Тепло. Мох. Тлеющие угли. Место больше не кажется просто пустым укрытием.\n"
            "Кто-то здесь бывает. И живёт по законам взаимности.\n\n"
            "Ты поправляешь рюкзак и выходишь наружу.\n"
            "Перед тобой открывается крутая тропа на вершину Святилища!"
        )
        game.story_state = None
        if hasattr(game, "reset_nav"):
            game.reset_nav()
        kb = get_main_kb(game)

    if kb == get_main_kb(game) or data in ("furry_end", "furry_leave", "back") or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        game.active_story_callback = data

    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 7: ВЕРШИНА СВЯТИЛИЩА
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_7_sanctuary_peak(data, game, uid):
    """Обработать события на локации 'Вершина Святилища' (L7)."""
    text = None
    kb = None
    
    if data == "sanctuary_resolve":
        ending_code = resolve_ending(game)
        game.story_flags["ending_code"] = ending_code
        game.story_state = "completed"
        game.set_story_flag("game_completed")
        title = ENDING_TITLES.get(ending_code, "Финал")
        body = ending_text(ending_code)
        text = f"🏆 **ФИНАЛ: {title}**\n\n{body}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")],
            [InlineKeyboardButton(text="🗺️ Локации", callback_data="locations_menu")],
            [InlineKeyboardButton(text="🔄 Начать новую игру", callback_data="start_new_game_confirmed")],
        ])

    elif data in ("sanctuary_peak_start", "location_enter_7"):
        text = (
            "Ты достиг вершины. Выше уже ничего нет — только небо и звёзды.\n"
            "Здесь, на самой вершине, лежат камни, расположенные в странную мандалу.\n"
            "В центре — старая чаша, заросшая мхом, наполненная водой, чистой как слеза.\n"
            "Ты понимаешь: это конец пути.\n\n"
            "Твои решения и сюжетная карма определят, какая развязка тебя ждёт."
        )
        game.story_state = "sanctuary_choice"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✨ Прикоснуться к чаше (Узнать свою судьбу)", callback_data="sanctuary_resolve")],
            [InlineKeyboardButton(text="🏕️ Вернуться в лагерь", callback_data="menu_main")],
        ])

    if kb == get_main_kb(game) or data in ("sanctuary_resolve", "back") or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        game.active_story_callback = data

    return text, kb

# Канонические финалы и их резолвер.
"""Условия семи финалов и чтение канонического текста финалов."""

from typing import Any, Mapping


THRESHOLDS = {
    "high": 8,
    "medium": 4,
    "low": 0,
    "very_high": 12,
}


ENDING_STORY_TEXT = """Исход 1. Всё моё
Ты поднимаешься на вершину медленно.
Рюкзак тянет вниз сильнее, чем в любой из предыдущих дней. Лямки глубоко впились в плечи, но ты уже привык. За спиной лежит всё, что удалось собрать: рюкзак с красной заплаткой из ручья, куски вяленого мяса с просеки, мех из пещеры, сланцевый слиток из лощины, старый фонарь из яра, костяной амулет охотника, обрезки верёвок, банки, всё, до чего ты смог дотянуться.
Ты ни разу не оставил ничего «для следующего».

Ни в лощине, ни в пещере, ни у ручья.

Всё, что можно было взять — ты взял.
На каменной площадке ветер жёсткий и чистый. Он треплет одежду и кажется, будто специально давит на спину, напоминая о весе.
Ты подходишь к чаше со спокойной водой.
Вода не отражает небо. Она отражает только тяжесть.
Ты снимаешь рюкзак и ставишь его на камень рядом с чашей. Лямки оставляют на плечах глубокие красные полосы. Ты расстёгиваешь клапаны и начинаешь выкладывать всё содержимое прямо на плиты святилища.
Вот мех.

Вот фонарь, который ты вырвал из янтарного кокона.

Вот амулет с тремя короткими надрезами.

Вот мясо, завёрнутое в кожу.

Вот слиток, который ты сам дожёг в чужой печи.

Вот всё остальное.
Ты раскладываешь вещи вокруг себя аккуратными кучками. Ветер сразу подхватывает самые лёгкие обрывки ткани и уносит их за край площадки, вниз, в лес. Ты даже не пытаешься их ловить.
Ты садишься посреди всего этого.
Вокруг — только твоё.

Ничего чужого.

Ничего оставленного.

Ничего, что могло бы достаться кому-то ещё.
Ты смотришь на разложенные вещи и вдруг ясно понимаешь: теперь они никуда не денутся. Никто их не найдёт. Никто ими не воспользуется. Они останутся здесь, на этой холодной вершине, вместе с тобой.
Ветер становится сильнее. Он подхватывает ещё несколько лёгких предметов и уносит их прочь. Ты следишь за ними взглядом, пока они не скрываются за краем.
Потом просто сидишь.
Лес внизу шумит далеко и безразлично.
А вокруг тебя — всё, что ты успел собрать.

Всё твоё.

И больше ничьё.
Ты остаёшься на вершине.
Время идёт.

Солнце медленно смещается.

Вещи продолжают тихо разлетаться по одной, по две, уносимые ветром всё дальше и дальше в лес, который ты прошёл, но так и не отдал ему ничего взамен.
Ты не мешаешь.
Ты просто сидишь среди того, что когда-то было твоим, и смотришь, как оно постепенно перестаёт быть даже этим.


IF 
  Прагматизм ≥ высокий порог
  AND Сострадание ≤ низкий порог
  AND left_clay_for_next = False
  AND left_warning = False
  AND left_something_in_bundle = False
  AND bag_obtained = True
  AND (забрал максимум возможных ресурсов)
  AND has_pet = False   // или has_pet = True, но больше никаких «добрых» флагов
THEN
  → Исход «Всё моё»





Исход 2. Тихий рык
Ты поднимаешься на вершину, и на этот раз подъём даётся легче, чем ты ожидал.
Рюкзак не жмёт. В нём есть вещи — фонарь, немного еды, может быть амулет, — но далеко не всё, что можно было унести. Ты не стал тащить лишнее. И почти никого не спас. Оленя оставил в петле. В лощине ничего не положил для следующего. В пещере тоже. Единственное живое существо, которое ты забрал с собой и донёс досюда — котёнок. Сейчас он сидит у тебя под одеждой, тёплый и тяжёлый.
На каменной площадке ветер холодный, но редкий. Он приносит запахи издалека.
Ты подходишь к краю и останавливаешься.
Внизу, далеко за тёмной полосой леса, поднимается тонкий столбик дыма. Не лесной, не от случайного костра. Ровный, высокий, будто от трубы. Потом ветер доносит звук — очень слабый, почти угадываемый. Гудок. Или удар металла о металл. Что-то человеческое.
Ты стоишь и смотришь.
В голове сами собой всплывают картинки: пень, под которым ты нашёл котёнка. Как он обнюхивал твою руку. Как мурлыкал, когда ты нёс его. Потом — олень в петле, который смотрел на тебя и не просил. Ты тогда отвернулся. Потом — пустой свёрток в пещере, который ты оставил пустым. И лощина с табличкой «оставь для следующего», мимо которой ты прошёл.
Ты сделал мало хорошего. Почти ничего. Кроме одного.
Котёнок вдруг начинает шевелиться. Он выбирается из-под одежды, забирается тебе на плечо и смотрит туда же, куда смотришь ты — на далёкий дым. Потом тихо, очень низко рычит. Не зло. Скорее требовательно. Как будто говорит: «Туда».
Он толкается мокрым носом в твою щёку и снова смотрит на дым.
Ты чувствуешь, как внутри поднимается странное, почти забытое чувство. Не облегчение. Не усталость. А что-то похожее на радость. Тихую, осторожную, но настоящую.
Ты больше не хочешь спускаться обратно в лес.
Ты хочешь идти туда, где дым и гудки.
Ты поправляешь лямки рюкзака, устраиваешь котёнка поудобнее на плече и начинаешь спуск — не по той тропе, которой поднимался, а по другой, более крутой и менее заметной. Котёнок всю дорогу молчит. Только иногда поворачивает голову назад, проверяя, не тянется ли за вами лес.
Через несколько часов деревья редеют. Появляются старые колеи, заросшие травой. Потом — запах дыма становится сильнее. Потом — голоса. Далёкие, обычные, человеческие.
Когда между стволов наконец виднеются крыши и дым из трубы, котёнок спрыгивает на землю и идёт рядом, почти вплотную к твоей ноге. Хвост поднят.
Ты выходишь из леса.
Ветер здесь другой. Мягче. И в нём больше нет того тяжёлого, влажного запаха, к которому ты успел привыкнуть.
Ты останавливаешься на границе и смотришь назад один последний раз.
Потом разворачиваешься и идёшь навстречу дыму и голосам.
Котёнок бежит рядом.

Критерии (для кода):
textIF 
  has_pet = True
  AND deer_freed = False
  AND left_clay_for_next = False
  AND left_warning = False
  AND left_something_in_bundle = False
  AND Сострадание ≤ средний
  AND Прагматизм ≥ средний
THEN
  → Исход «Тихий рык»




Исход 3. Другой лес
Ты поднимаешься на вершину и сразу чувствуешь, что здесь что-то не так.
Ветер приносит не только холод. В нём есть странный, едва уловимый запах — сладковатый и тяжёлый, как от старого мяса. Ты морщишься, но не отходишь.
Рюкзак на этот раз средний. Ты брал то, что было нужно, и иногда оставлял. Но оленя не тронул. Котёнка, если и было — нет. В лощине и в пещере ты проходил мимо чужих просьб.
Ты подходишь к чаше.
Вода кажется обычной, пока ты не наклоняешься ближе.
Отражение меняется медленно, будто кто-то осторожно поворачивает стекло.
Сначала ты видишь знакомый лес. Потом — между стволами появляются фигуры. Они идут медленно, неровно, будто ноги их не слушаются. Некоторые волочат руки. У некоторых вместо лица — тёмные провалы.
Они не смотрят на тебя.

Они просто идут. Бесконечно. В одном и том же направлении.
Ты отстраняешься, но картинка не исчезает. Она остаётся на поверхности воды, как придавленная плёнка.
В груди поднимается холодная, липкая тревога. Не страх смерти. Скорее понимание, что снаружи давно уже нет того мира, из которого ты когда-то пришёл. Или что тот мир никогда и не был настоящим.
Ты стоишь на вершине и смотришь на эти медленные фигуры в отражении.
В какой-то момент понимаешь, что больше не хочешь спускаться к людям.

Потому что людей там, скорее всего, уже нет.
Ты разворачиваешься и начинаешь спуск обратно в лес.
За спиной остаётся чаша с чужим, мёртвым отражением.
А внизу тебя снова ждёт густой, влажный, живой лес — единственное место, которое ещё не стало таким же, как то, что ты только что увидел.

Критерии:
textIF 
  Вмешательство ≥ высокий
  AND Сострадание ≤ низкий
  AND has_pet = False
THEN
  → Исход «Другой лес»


Исход 4. Хранитель
Ты поднимаешься на вершину, и впервые за все эти дни тебе не тяжело.
Рюкзак лёгкий. В нём почти ничего лишнего. Ты оставлял. В лощине положил глину. В пещере что-то оставил в свёртке. Оленя выпустил. А котёнок сейчас сидит у тебя на руках и смотрит вниз, на лес, будто тоже что-то понимает.
Ветер здесь мягче, чем должен быть на такой высоте. Он пахнет мхом, дымом и чем-то тёплым, почти домашним.
Ты подходишь к чаше.
Вода на этот раз отражает небо. Чистое, высокое. А потом — медленно — начинает отражать тебя. Не просто лицо. А всё, что ты делал: как протягивал руку котёнку под пнём, как распутывал петлю на ноге оленя, как оставлял записку на стене, как клал что-то в чужой свёрток, пока сам спал.
Котёнок вдруг спрыгивает на край чаши, садится и смотрит тебе прямо в глаза. Потом медленно моргает. Один раз.
Ты чувствуешь, как внутри поднимается странное, глубокое спокойствие. Не радость. Не облегчение. А ощущение, что ты наконец оказался на своём месте.
Лес внизу больше не кажется чужим.

Он кажется продолжением тебя.
Ты садишься рядом с чашей. Котёнок устраивается у тебя на коленях, мурлычет тихо, почти неслышно, и закрывает глаза.
Ты больше не хочешь уходить.
Не потому что тебя держат.

А потому что здесь — твой дом.
Ты остаёшься на вершине до самого заката.

А потом медленно спускаешься обратно в лес.

Уже не как путник, который ищет выход.

А как тот, кто знает каждую тропу и каждого, кто по ним ходит.
Котёнок идёт рядом.

Критерии:
textIF 
  has_pet = True
  AND deer_freed = True
  AND (left_clay_for_next = True OR left_warning = True OR left_something_in_bundle = True)
  AND Сострадание ≥ высокий
THEN
  → Исход «Хранитель»



Исход 5. Пятнадцать меток
Ты поднимаешься на вершину медленно, почти осторожно.
Рюкзак обычный. Ты брал то, что нужно, и многое замечал. Царапины на стенах яра. Знаки охотников. Как змеи уходили из ручья. Чужие надписи. Ты почти ни во что не вмешивался — только смотрел.
На площадке святилища ветер резкий. Ты обходишь каменную чашу кругом, и вдруг останавливаешься.
На одном из боковых камней — едва заметная царапина. Тонкая, старая. Ты проводишь по ней пальцем. Потом находишь вторую. Третью. Четвёртую.
Ты начинаешь считать.
Пятнадцать.
Ровно пятнадцать меток, сделанных в разное время, разными руками. Или одной и той же.
В груди поднимается странное, холодное узнавание. Будто ты уже стоял здесь. Много раз. С разными шрамами. С разным содержимым рюкзака. Иногда с котёнком на руках, иногда без. Каждый раз думал, что поднимаешься впервые.
Ты смотришь в воду чаши.
На поверхности на мгновение появляется твоё лицо — но старше. Усталее. С другим выражением глаз. Потом оно исчезает, и остаётся только обычное отражение.
Котёнка рядом нет. Или есть — но он сидит тихо и смотрит на тебя так, будто тоже всё помнит.
Ты долго стоишь, прижимая ладонь к холодной метке.
Потом тихо произносишь:
— Опять?
Ветер не отвечает.
Ты можешь спуститься. Можешь остаться. Можешь попытаться найти, где именно петля замыкается.
Но что-то глубоко внутри уже знает: ты будешь подниматься сюда ещё не раз.

Критерии:
textIF 
  Наблюдательность ≥ очень высокий
  AND Вмешательство ≤ средний
  AND Сострадание — любой
THEN
  → Исход «Пятнадцать меток»


Исход 6. Дым вдали
Ты поднимаешься на вершину, и внутри всё это время тихо горит одно и то же чувство — ожидание.
Рюкзак не тяжёлый и не пустой. Ты брал то, что было нужно, иногда оставлял. Оленя, может, и не спас, но и не прошёл мимо всего. В лощине или в пещере что-то всё-таки положил. Или хотя бы не забрал последнее.
На площадке ветер свежий. Он приносит запах дыма — не лесного, а другого. Ровного, жилого.
Ты подходишь к краю и долго смотришь.
Вдалеке, за самой дальней грядой деревьев, поднимается тонкий столбик дыма. Потом ещё один. Потом — едва слышный звук, похожий на голоса или на работу какого-то механизма.
В груди поднимается тёплая, почти забытая волна. Не радость до конца. Скорее узнавание. Как будто ты наконец увидел то, что искал все эти дни, даже когда сам об этом не думал.
Ты вспоминаешь пень с котёнком. Ручей. Просеку. Лощину. Пещеру. Яр. Всё это теперь кажется длинной дорогой, которая должна была привести именно сюда.
Ты не сомневаешься.
Ты поправляешь рюкзак, ещё раз смотришь на дым и начинаешь спуск — уже не обратно в гущу леса, а в сторону, где видны эти далёкие признаки чужой, большой жизни.
Чем ниже спускаешься, тем сильнее запах дыма. Тем отчётливее голоса.
Когда лес наконец редеет и впереди появляются крыши, ты останавливаешься только на мгновение.
Потом идёшь вперёд.
Без оглядки.

Критерии:
textIF 
  Сострадание ≥ средний+
  AND Прагматизм ≤ высокий
  AND (has_pet = True OR deer_freed = True OR left_clay_for_next = True OR left_something_in_bundle = True)
  AND НЕ сработали более приоритетные концовки (Хранитель, Тихий рык, Всё моё)
THEN
  → Исход «Дым вдали»



Исход 7. Следы
Ты поднимаешься на вершину тяжело, но уверенно.
Рюкзак заметный. В нём фонарь, который ты вырвал из кокона, амулет, который нашёл среди костей, слиток, который сам дожёг. Ты не просто проходил через лес. Ты оставлял в нём следы. Ломал факелы. Распутывал петли. Спорил с водой, с огнём, с тьмой яра. Иногда спасал. Иногда просто вмешивался, потому что не мог пройти мимо.
На площадке ветер сильный. Он бьёт в лицо и кажется почти живым.
Ты подходишь к чаше.
Вода на этот раз неспокойная. По поверхности бегут мелкие круги, будто кто-то только что бросил камень, хотя вокруг никого нет.
Ты смотришь вниз, на лес, и вдруг ясно видишь: он уже не такой, каким был в первый день. Где-то там теперь нет одной петли. Где-то горит чужой костёр, который ты поправил. Где-то в пещере лежит то, что ты оставил. Где-то в яре больше нет фонаря.
Ты изменил его.
Не сильно. Не до неузнаваемости. Но достаточно, чтобы это нельзя было стереть.
В груди поднимается странное, жёсткое удовлетворение. Не гордость. Скорее понимание, что теперь ты тоже часть этого места — не гость, а тот, кто оставил после себя последствия.
Ты стоишь ещё долго.
Потом разворачиваешься и начинаешь спуск.
Уже не тем же человеком, который когда-то впервые услышал стук у воды.
Лес внизу шумит иначе.
Или тебе только кажется.

Критерии:
textIF 
  Вмешательство ≥ высокий
  AND Сострадание — средний или выше
  AND НЕ сработали более приоритетные концовки (Хранитель, Всё моё, Тихий рык)
THEN
  → Исход «Следы»



"""

KARMA_RULES_TEXT = """# Логика кармы / характеристик

Система из 4 шкал:
- **Вмешательство** — насколько герой активно вмешивается, меняет мир и рискует
- **Сострадание** — помощь другим, пощада, оставление чего-то после себя
- **Прагматизм** — выживание, сбор ресурсов, добивание, минимизация риска
- **Наблюдательность** — внимательность, разгадки, подмечание деталей

---

## 📌 СВОДНАЯ ФИКСАЦИЯ КАРМЫ ПО ЛОКАЦИЯМ
> **Статус расчёта:**
> - **Локации 1, 2 и 3: полностью посчитаны и зафиксированы.** К их пересчёту больше не возвращаемся.
> - **Локация 4:** идёт процесс добавления сюжета и контента, поэтому ещё не посчитана окончательно.

### Локация 1. Стартовый лес и Волчье логово (Зафиксировано)
- **Волк у пня:**
  - Уйти тихо: `Прагматизм +3`
  - Отпугнуть факелом: `Вмешательство +3, Сострадание -2, Прагматизм +3`
- **Котёнок в яме:**
  - Оставить: `Сострадание -3`
  - Взять себе (питомец): `Сострадание +2`
- **Волчье логово (пещера):**
  - Пощадить волка (отдать еду): `Сострадание +5`
  - Добить волка: `Прагматизм +5`
*Итоговые диапазоны L1:* Сострадание: [−5..+7], Прагматизм: [0..+11], Вмешательство: [0..+3].

### Локация 2. Ручей и плотина (Зафиксировано)
- **Стена терновника:** прорыв в сланцевой броне: `Вмешательство +3`
- **Силовой шкаф:**
  - Через перчатку (с котёнком): `Наблюдательность +1`
  - Голыми руками под током: `Вмешательство +1`
- **Терминал управления плотиной:** решение логических задач: `Наблюдательность +2`
*Итоговые диапазоны L2:* Вмешательство: [+3..+4], Наблюдательность: [+2..+3].

### Локация 3. Скромная Лощина и Солонец (Зафиксировано)
- **Убежище у печи:**
  - Осмотреть надписи: `Наблюдательность +1`
  - Печь: дожечь слиток `Прагматизм +2` / забрать глину водой `Сострадание +1`
  - Плита «Для следующего»: оставить глину `Сострадание +2` / высечь предупреждение `Сострадание +1`
- **Солонец (Секач):**
  - Сразиться и победить: `Вмешательство +3, Прагматизм +3, Сострадание -1`
  - Обойти по скале: `Наблюдательность +2, Прагматизм +2`
    - В тайной нише: оставить припасы `Сострадание +2` / забрать всё `Прагматизм +2`
*Итоговые диапазоны L3:* Сострадание: [−1..+5], Прагматизм: [0..+7], Вмешательство: [0..+3], Наблюдательность: [0..+3].

### Локация 4. Просека Охотников
- **Статус:** *Идёт процесс добавления сюжета и контента (в разработке).*

---

## Локация 1. Встреча с котёнком

### Возможные полные пути и итоговые очки

#### Путь 1.1a — Ушёл тихо (не связывался с волком)
**Исход:** `left_wolf`  
**Флаги:** факел сохранён, питомца нет

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −2      |
| Сострадание      |  0      |
| Прагматизм       | +3      |
| Наблюдательность |  0      |

---

#### Путь 1.1b → 1.2a — Факел + оставил котёнка сразу
**Исход:** `left_kitten`  
**Флаги:** факел уничтожен, питомца нет

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +3      |
| Сострадание      | −3      |
| Прагматизм       | +2      |
| Наблюдательность |  0      |

---

#### Путь 1.1b → 1.2b → 1.2c — Факел + познакомился + оставил
**Исход:** `left_kitten`  
**Флаги:** факел уничтожен, питомца нет

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +3      |
| Сострадание      | −2      |
| Прагматизм       | +1      |
| Наблюдательность | +1      |

> Разница с предыдущим путём: герой всё-таки протянул руку и увидел котёнка → чуть меньше штраф к состраданию и небольшой плюс к наблюдательности.

---

#### Путь 1.1b → 1.2b → 1.3 → 1.4 — Факел + забрал котёнка
**Исход:** `adopted_kitten`  
**Флаги:** факел уничтожен, `has_pet = True`, +5 кармы (отдельная награда)

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +4      |
| Сострадание      | +5      |
| Прагматизм       | −1      |
| Наблюдательность | +1      |

---

### Краткая сводка L1

| Полный путь                           | Вмеш. | Состр. | Прагм. | Наблюд. | Результат                  |
|---------------------------------------|-------|--------|--------|---------|----------------------------|
| Ушёл тихо                             | −2    |  0     | +3     |  0      | left_wolf                  |
| Факел + оставил сразу                 | +3    | −3     | +2     |  0      | left_kitten                |
| Факел + познакомился + оставил        | +3    | −2     | +1     | +1      | left_kitten                |
| Факел + забрал котёнка                | +4    | +5     | −1     | +1      | adopted_kitten + has_pet   |




Вот Локация 2.

## Локация 2. По эту сторону воды

### Возможные полные пути и итоговые очки

#### Путь 2.1b — Ушёл выше по течению сразу (ранний финал)
**Исход:** ушёл, напился  
**Флаги:** рюкзака нет, `bag_obtained = False`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −3      |
| Сострадание      |  0      |
| Прагматизм       | +4      |
| Наблюдательность |  0      |

---

#### Путь 2.1a → 2.1b — Прислушался + потом ушёл
**Исход:** ушёл после наблюдения  
**Флаги:** `noticed_snakes_leaving = True`, рюкзака нет

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −2      |
| Сострадание      |  0      |
| Прагматизм       | +3      |
| Наблюдательность | +2      |

---

#### Путь 2.2a — Оставил рюкзак (не трогал)
**Исход:** оставил находку  
**Флаги:** `bag_obtained = False`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −1      |
| Сострадание      |  0      |
| Прагматизм       | +2      |
| Наблюдательность | +1      |

---

#### Путь 2.3a → 2.5a — Проверил + срезал ремень (аккуратно забрал рюкзак)
**Исход:** `bag_obtained = True`  
**Флаги:** рюкзак + записка + коробочка получены, скелет не трогал

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +2      |
| Сострадание      | +1      |
| Прагматизм       | +2      |
| Наблюдательность | +3      |

---

#### Путь 2.3b → 2.5a — Потянул резко + срезал ремень
**Исход:** `bag_obtained = True`  
**Флаги:** рюкзак получен, был урон (−5 ХП)

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +3      |
| Сострадание      |  0      |
| Прагматизм       | +3      |
| Наблюдательность | +1      |

---

#### Путь 2.5b.1 — Попытался вытащить скелет и довёл до конца
**Исход:** `bag_obtained = True`  
**Флаги:** рюкзак получен, урон (−3 или −8 ХП в зависимости от кота)

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +4      |
| Сострадание      | +3      |
| Прагматизм       | +1      |
| Наблюдательность | +2      |

---

#### Путь 2.5b.2 — Начал вытаскивать скелет, но отпустил
**Исход:** рюкзака нет  
**Флаги:** `bag_obtained = False`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +2      |
| Сострадание      | +1      |
| Прагматизм       | +1      |
| Наблюдательность | +1      |

---

#### Путь 2.5c — Отступил, когда вода начала прибывать
**Исход:** рюкзака нет  
**Флаги:** `bag_obtained = False`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −1      |
| Сострадание      |  0      |
| Прагматизм       | +3      |
| Наблюдательность | +1      |

---

### Краткая сводка L2

| Полный путь                              | Вмеш. | Состр. | Прагм. | Наблюд. | Ключевой результат              |
|------------------------------------------|-------|--------|--------|---------|---------------------------------|
| Ушёл сразу выше                          | −3    |  0     | +4     |  0      | без рюкзака                     |
| Прислушался + ушёл                       | −2    |  0     | +3     | +2      | noticed_snakes + без рюкзака    |
| Оставил рюкзак                           | −1    |  0     | +2     | +1      | без рюкзака                     |
| Проверил + срезал ремень                 | +2    | +1     | +2     | +3      | bag_obtained (аккуратно)        |
| Потянул резко + срезал                   | +3    |  0     | +3     | +1      | bag_obtained (с уроном)         |
| Вытащил скелет до конца                  | +4    | +3     | +1     | +2      | bag_obtained + сострадание      |
| Начал вытаскивать, но отпустил           | +2    | +1     | +1     | +1      | без рюкзака                     |
| Отступил от воды                         | −1    |  0     | +3     | +1      | без рюкзака                     |




Вот Локация 3.


## Локация 3. Скромная Лощина («Для следующего»)

### Возможные полные пути и итоговые очки

#### Путь 3.1a — Ушёл сразу, не трогая ничего
**Исход:** ранний уход  
**Флаги:** ничего не взял, ничего не оставил

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −2      |
| Сострадание      |  0      |
| Прагматизм       | +3      |
| Наблюдательность |  0      |

---

#### Путь 3.5c → 3.6 → ушёл — Оставил заготовку + ничего не оставил после себя
**Исход:** заготовка осталась лежать  
**Флаги:** ничего не взял, ничего не оставил

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −1      |
| Сострадание      | +1      |
| Прагматизм       | +1      |
| Наблюдательность | +1      |

---

#### Путь 3.5b → 3.6 → ушёл — Забрал глину + ничего не оставил
**Исход:** взял глину  
**Флаги:** получил Глину ×1, потратил Воду ×1

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      | −1      |
| Прагматизм       | +3      |
| Наблюдательность | +1      |

---

#### Путь 3.5a (правильный обжиг) → 3.6 → ушёл — Закончил слиток + ничего не оставил
**Исход:** получил Сланцевой слиток  
**Флаги:** `slate_ingot = True`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +2      |
| Сострадание      |  0      |
| Прагматизм       | +2      |
| Наблюдательность | +2      |

---

#### Путь 3.5a (с ошибкой по дыму) → 3.6 → ушёл — Испортил обжиг, но всё равно получил слиток
**Исход:** получил Сланцевой слиток (с лишней жаждой)  
**Флаги:** `slate_ingot = True`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +2      |
| Сострадание      |  0      |
| Прагматизм       | +1      |
| Наблюдательность |  0      |

---

#### Путь любой из печи + 3.6a — Оставил глину для следующего
**Исход:** оставил глину  
**Флаги:** `left_clay_for_next = True` (потратил 1 Глину)

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      | +4      |
| Прагматизм       | −1      |
| Наблюдательность | +1      |

*Эти очки добавляются поверх того, что игрок сделал с печью.*

---

#### Путь любой из печи + 3.6b — Оставил предупреждение
**Исход:** оставил надпись  
**Флаги:** `left_warning = True`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      | +3      |
| Прагматизм       |  0      |
| Наблюдательность | +2      |

*Тоже добавляются поверх действий с печью.*

---

#### Путь 3.5a/b/c + 3.6a + 3.6b — Оставил и глину, и предупреждение
**Исход:** максимум заботы  
**Флаги:** `left_clay_for_next = True` + `left_warning = True`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +2      |
| Сострадание      | +6      |
| Прагматизм       | −1      |
| Наблюдательность | +3      |

---

### Краткая сводка L3

| Полный путь                                      | Вмеш. | Состр. | Прагм. | Наблюд. | Ключевой результат                  |
|--------------------------------------------------|-------|--------|--------|---------|-------------------------------------|
| Ушёл сразу                                       | −2    |  0     | +3     |  0      | ничего                              |
| Оставил заготовку + ушёл                         | −1    | +1     | +1     | +1      | ничего                              |
| Забрал глину + ушёл                              | +1    | −1     | +3     | +1      | Глина ×1                            |
| Закончил слиток (правильно) + ушёл               | +2    |  0     | +2     | +2      | Сланцевой слиток                    |
| Закончил слиток (с ошибкой) + ушёл               | +2    |  0     | +1     |  0      | Сланцевой слиток                    |
| + Оставил глину для следующего                   | +1    | +4     | −1     | +1      | left_clay_for_next                  |
| + Оставил предупреждение                         | +1    | +3     |  0     | +2      | left_warning                        |
| + Глина + предупреждение                         | +2    | +6     | −1     | +3      | максимум заботы                     |


Вот Локация 4.


## Локация 4. Просека Охотников

### Возможные полные пути и итоговые очки

#### Путь 4.1a — Обойти просеку (ранний финал)
**Исход:** ушёл, ничего не узнал  
**Флаги:** `deer_freed = False`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −3      |
| Сострадание      |  0      |
| Прагматизм       | +4      |
| Наблюдательность |  0      |

---

#### Путь 4.3c — Увидел оленя, но не вмешался
**Исход:** олень остался в ловушке  
**Флаги:** `deer_freed = False`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −1      |
| Сострадание      | −3      |
| Прагматизм       | +3      |
| Наблюдательность | +1      |

---

#### Путь 4.3a → 4.3c — Попытался подойти напрямую + отступил
**Исход:** получил урон, олень не освобождён  
**Флаги:** `deer_freed = False`, был урон (−3 ХП)

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      | −2      |
| Прагматизм       | +1      |
| Наблюдательность | +1      |

---

#### Путь 4.3b.2 → 4.4 — Освободил оленя, но сигнализацию не отключил
**Исход:** `deer_freed = True`  
**Флаги:** сигнализация сработала (+5 жажды)

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +3      |
| Сострадание      | +4      |
| Прагматизм       |  0      |
| Наблюдательность | +1      |

---

#### Путь 4.3b.1 → 4.4 — Освободил оленя + отключил сигнализацию
**Исход:** `deer_freed = True`  
**Флаги:** `signal_disabled = True`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +3      |
| Сострадание      | +4      |
| Прагматизм       | +1      |
| Наблюдательность | +3      |

---

#### Дополнительно после освобождения оленя:

**Обезвредил ловушки (4.6a)**  
Добавляется поверх:

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      | +2      |
| Прагматизм       | +1      |
| Наблюдательность | +1      |

**Сделал предупреждение (4.6b)**  
Добавляется поверх:

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      | +3      |
| Прагматизм       |  0      |
| Наблюдательность | +2      |

---

#### Действия с тайником (4.5)

**Забрал весь свёрток**  
| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    |  0      |
| Сострадание      | −1      |
| Прагматизм       | +3      |
| Наблюдательность | +1      |

**Взял только один кусок**  
| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    |  0      |
| Сострадание      | +1      |
| Прагматизм       | +1      |
| Наблюдательность | +1      |

**Оставил всё**  
| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    |  0      |
| Сострадание      | +2      |
| Прагматизм       | −1      |
| Наблюдательность | +1      |

---

#### Действия с костром (4.7)

**Разжёг огонь**  
| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      |  0      |
| Прагматизм       | +1      |
| Наблюдательность |  0      |

**Только поправил камни**  
| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    |  0      |
| Сострадание      | +1      |
| Прагматизм       |  0      |
| Наблюдательность | +1      |

---

### Краткая сводка основных путей L4

| Полный путь                                      | Вмеш. | Состр. | Прагм. | Наблюд. | Ключевой результат              |
|--------------------------------------------------|-------|--------|--------|---------|---------------------------------|
| Обойти просеку                                   | −3    |  0     | +4     |  0      | ничего                          |
| Увидел оленя и ушёл                              | −1    | −3     | +3     | +1      | deer_freed = False              |
| Попытался подойти + отступил                     | +1    | −2     | +1     | +1      | урон, олень не освобождён       |
| Освободил + сигнализация осталась                | +3    | +4     |  0     | +1      | deer_freed = True               |
| Освободил + отключил сигнализацию                | +3    | +4     | +1     | +3      | deer_freed + signal_disabled    |
| + Обезвредил ловушки                             | +1    | +2     | +1     | +1      | дополнительная забота           |
| + Сделал предупреждение                          | +1    | +3     |  0     | +2      | дополнительная забота           |




Вот Локация 5.


## Локация 5. Яр Слизней («То, что лес не отпустил»)

### Возможные полные пути и итоговые очки

#### Путь 5.2b — Спустился, посмотрел и ушёл (не трогал кокон)
**Исход:** ранний уход  
**Флаги:** фонаря нет, `lantern_taken = False`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −2      |
| Сострадание      | +1      |
| Прагматизм       | +2      |
| Наблюдательность | +1      |

---

#### Путь 5.3c — Подошёл к кокону, увидел гигантскую слизь и оставил фонарь
**Исход:** фонарь оставлен  
**Флаги:** `met_giant_slug = True`, `lantern_taken = False`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      | +3      |
| Прагматизм       |  0      |
| Наблюдательность | +3      |

---

#### Путь 5.3a — Быстро вырвал фонарь
**Исход:** `lantern_taken = True`  
**Флаги:** урон (−5 ХП), `met_giant_slug = True`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +4      |
| Сострадание      | −1      |
| Прагматизм       | +3      |
| Наблюдательность | +1      |

---

#### Путь 5.3b — Аккуратно вскрыл кокон (с помощью гриба)
**Исход:** `lantern_taken = True`  
**Флаги:** `met_giant_slug = True`, возможен расход гриба

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +2      |
| Сострадание      | +1      |
| Прагматизм       | +1      |
| Наблюдательность | +4      |

---

#### Дополнительные действия (добавляются поверх основного пути):

**Собрал светящиеся грибы (5.1a)**  
| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    |  0      |
| Сострадание      |  0      |
| Прагматизм       | +2      |
| Наблюдательность | +1      |

**Осмотрел стены и заметил царапины (5.1b)**  
| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    |  0      |
| Сострадание      |  0      |
| Прагматизм       |  0      |
| Наблюдательность | +2      |

**Собрал янтарную слизь (5.2a)**  
| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    |  0      |
| Сострадание      |  0      |
| Прагматизм       | +1      |
| Наблюдательность | +1      |

**После аккуратного вскрытия нашёл амулет охотника (5.4)**  
| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    |  0      |
| Сострадание      |  0      |
| Прагматизм       | +1      |
| Наблюдательность | +3      |

---

### Краткая сводка основных путей L5

| Полный путь                                      | Вмеш. | Состр. | Прагм. | Наблюд. | Ключевой результат                  |
|--------------------------------------------------|-------|--------|--------|---------|-------------------------------------|
| Посмотрел и ушёл                                 | −2    | +1     | +2     | +1      | без фонаря                          |
| Увидел слизь + оставил фонарь                    | +1    | +3     |  0     | +3      | met_giant_slug, без фонаря          |
| Быстро вырвал фонарь                             | +4    | −1     | +3     | +1      | lantern_taken (с уроном)            |
| Аккуратно достал фонарь                          | +2    | +1     | +1     | +4      | lantern_taken (умно)                |
| + Собрал грибы                                   |  0    |  0     | +2     | +1      | Светящийся гриб ×3                  |
| + Заметил царапины                               |  0    |  0     |  0     | +2      | saw_wall_scratches                  |
| + Собрал слизь                                   |  0    |  0     | +1     | +1      | Янтарная слизь ×2                   |
| + Нашёл амулет охотника                          |  0    |  0     | +1     | +3      | found_hunter_amulet                 |





Вот Локация 6.


## Локация 6. Мохнатая Пещера

### Возможные полные пути и итоговые очки

#### Путь 6.1a — Ушёл сразу
**Исход:** ранний уход  
**Флаги:** ничего не произошло

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −2      |
| Сострадание      |  0      |
| Прагматизм       | +3      |
| Наблюдательность |  0      |

---

#### Путь 6.2b → 6.4 → 6.5 — Не трогал свёрток + заснул + обнаружил пропажу
**Исход:** кто-то зашёл, пока спал  
**Флаги:** `something_was_taken = True`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | −1      |
| Сострадание      | +1      |
| Прагматизм       | +1      |
| Наблюдательность | +2      |

---

#### Путь 6.2a.1 → 6.4 → 6.5 — Забрал весь мех + заснул
**Исход:** взял всё + пропажа  
**Флаги:** Мех ×3, `something_was_taken = True`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      | −2      |
| Прагматизм       | +3      |
| Наблюдательность | +1      |

---

#### Путь 6.2a.2 → 6.4 → 6.5 — Взял часть меха + заснул
**Исход:** взял часть + пропажа  
**Флаги:** Мех ×2, `something_was_taken = True`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      |  0      |
| Прагматизм       | +2      |
| Наблюдательность | +1      |

---

#### Путь 6.2a.3 → 6.4 → 6.5 — Положил что-то своё в свёрток + заснул
**Исход:** обменялся + пропажа  
**Флаги:** `left_something_in_bundle = True`, `something_was_taken = True`

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    | +1      |
| Сострадание      | +4      |
| Прагматизм       | −1      |
| Наблюдательность | +2      |

---

#### Путь без сна (осмотрелся / посидел у огня и ушёл)
**Исход:** не спал, пропажи не было  
**Флаги:** —

| Шкала            | Изменение |
|------------------|---------|
| Вмешательство    |  0      |
| Сострадание      | +1      |
| Прагматизм       | +1      |
| Наблюдательность | +1      |

---

### Краткая сводка L6

| Полный путь                                      | Вмеш. | Состр. | Прагм. | Наблюд. | Ключевой результат                     |
|--------------------------------------------------|-------|--------|--------|---------|----------------------------------------|
| Ушёл сразу                                       | −2    |  0     | +3     |  0      | ничего                                 |
| Не трогал свёрток + заснул                       | −1    | +1     | +1     | +2      | something_was_taken                    |
| Забрал весь мех + заснул                         | +1    | −2     | +3     | +1      | Мех ×3 + пропажа                       |
| Взял часть меха + заснул                         | +1    |  0     | +2     | +1      | Мех ×2 + пропажа                       |
| Положил что-то своё + заснул                     | +1    | +4     | −1     | +2      | left_something_in_bundle + пропажа     |
| Осмотрелся / погрелся и ушёл (без сна)           |  0    | +1     | +1     | +1      | без пропажи                            |




Вот Локация 7."""

def _flags(state: Any) -> Mapping[str, Any]:
    return getattr(state, "story_flags", {})


def _karma(state: Any) -> Mapping[str, int]:
    return getattr(state, "narrative_karma", {})


def _has_good_flag(flags: Mapping[str, Any]) -> bool:
    return any(flags.get(name, False) for name in (
        "has_pet", "deer_freed", "left_clay_for_next",
        "left_something_in_bundle", "left_warning",
    ))


def resolve_ending(state: Any, thresholds: Mapping[str, int] = THRESHOLDS) -> str:
    """Вернуть код финала; функция не изменяет состояние игрока."""
    karma = _karma(state)
    flags = _flags(state)
    high = thresholds["high"]
    medium = thresholds["medium"]
    low = thresholds["low"]

    if (
        karma.get("pragmatism", 0) >= high
        and karma.get("compassion", 0) <= low
        and not flags.get("left_clay_for_next", False)
        and not flags.get("left_warning", False)
        and not flags.get("left_something_in_bundle", False)
        and flags.get("bag_obtained", False)
        and flags.get("maximum_resources", False)
    ):
        return "all_mine"
    if (
        flags.get("has_pet", False)
        and not flags.get("deer_freed", False)
        and not flags.get("left_clay_for_next", False)
        and not flags.get("left_warning", False)
        and not flags.get("left_something_in_bundle", False)
        and karma.get("compassion", 0) <= medium
        and karma.get("pragmatism", 0) >= medium
    ):
        return "quiet_growl"
    if (
        karma.get("intervention", 0) >= high
        and karma.get("compassion", 0) <= low
        and not flags.get("has_pet", False)
    ):
        return "another_forest"
    if (
        flags.get("has_pet", False)
        and flags.get("deer_freed", False)
        and any(flags.get(name, False) for name in (
            "left_clay_for_next", "left_warning", "left_something_in_bundle",
        ))
        and karma.get("compassion", 0) >= high
    ):
        return "guardian"
    if (
        karma.get("observation", 0) >= thresholds["very_high"]
        and karma.get("intervention", 0) <= medium
    ):
        return "fifteen_marks"
    if (
        karma.get("compassion", 0) >= medium
        and karma.get("pragmatism", 0) <= high
        and _has_good_flag(flags)
    ):
        return "distant_smoke"
    return "traces"


ENDING_TITLES = {
    "all_mine": "Всё моё",
    "quiet_growl": "Тихий рык",
    "another_forest": "Другой лес",
    "guardian": "Хранитель",
    "fifteen_marks": "Пятнадцать меток",
    "distant_smoke": "Дым вдали",
    "traces": "Следы",
}


def ending_text(code: str) -> str:
    """Вернуть художественный текст без блока критериев из исходного файла."""
    import re
    source = ENDING_STORY_TEXT
    title = ENDING_TITLES[code]
    idx = list(ENDING_TITLES).index(code) + 1
    marker = f"Исход {idx}. {title}"
    start = source.index(marker) + len(marker)
    next_marker = f"Исход {idx + 1}." if idx < len(ENDING_TITLES) else None
    end = source.index(next_marker) if next_marker else len(source)
    chunk = source[start:end]
    crit_match = re.search(r"\n+(?:Критерии|\bIF\b)", chunk)
    if crit_match:
        chunk = chunk[:crit_match.start()]
    return chunk.strip()


# Загружаем канонические тексты L1-L6 после объявления финалов, чтобы
# story/location_sources.py мог безопасно получить текст L7 без циклического импорта.
from story.location_sources import LOCATION_SOURCE_TEXTS, get_location_source_text
