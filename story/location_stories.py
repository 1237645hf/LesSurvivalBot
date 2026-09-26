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
)
from modules.items import is_item_consumable, get_item_rank, get_item_type
from modules.combat import (
    start_battle,
    apply_action,
    get_battle_text as get_wolf_battle_text,
)

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
    text = None
    kb = None

    if data == "forest_start":
        game.story_state = "wolf_encounter"
        game.add_log("Ты слышишь рычание в кустах... Это волк!")
        text = (
            "Тёмный лес замер. Из густых кустов на тебя смотрят два горящих глаза.\n"
            "Волк делает шаг навстречу. В твоей руке сжимается факел."
        )
        kb = wolf_kb

    elif data == "wolf_leave":
        game.story_state = None
        game.karma["clever"] = game.karma.get("clever", 0) + 2
        game.add_log("Ты тихо отступил, не связываясь с волком.")
        text = game.get_ui() if hasattr(game, "get_ui") else "Ты отступил."
        kb = get_main_kb(game)

    elif data == "wolf_torch":
        has_torch = game.inventory.get("Факел", 0) > 0
        if has_torch:
            game.inventory["Факел"] -= 1
            game.story_state = "wolf_fled"
            game.add_log("Ты взмахнул факелом! Волк испугался и убежал.")
            text = (
                "Ты резко взмахиваешь факелом. Яркие искры брызжут в сторону зверя.\n"
                "Волк испуганно визжит и скрывается в чаще."
            )
            kb = peek_kb
        else:
            game.add_log("У тебя нет факела!")
            text = "У тебя нет горящего факела! Волк рычит сильнее."
            kb = wolf_kb

    return text, kb


def handle_story(data: str, game, uid: int):
    """Обработать общую стартовую сцену волка и котёнка."""
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
        kb = get_main_kb(game)

    elif data == "wolf_torch":
        has_torch_in_hand = (
            game.equipment.get("hand") == "Факел"
            or game.equipment.get("hands") == "Факел"
            or game.equipment.get("hand_left") == "Факел"
            or game.equipment.get("hand_right") == "Факел"
        )
        has_torch_in_inv = game.inventory.get("Факел", 0) > 0

        if not has_torch_in_hand and not has_torch_in_inv:
            game.add_log("У тебя нет факела!")
            text = game.get_ui()
            kb = get_main_kb(game)
            return text, kb

        if not has_torch_in_hand and has_torch_in_inv:
            game.inventory["Факел"] = max(0, game.inventory.get("Факел", 0) - 1)
            game.equipment["hand_left"] = "Факел"
            game.equipment["hand"] = "Факел"
            game.equipment["hands"] = "Факел"

        game.adjust_narrative_karma("intervention", 3)
        game.adjust_narrative_karma("compassion", -2)
        game.adjust_narrative_karma("pragmatism", 3)
        game.story_state = "after_fight"
        text = (
            "Ты поднимаешь факел повыше. Пламя трещит громче.\n"
            "Волк резко оборачивается, глаза вспыхивают жёлтым в свете огня.\n"
            "Секунду он смотрит на тебя — не нападает, но и не отступает.\n"
            "Тогда ты делаешь шаг вперёд и рычишь сам — низко, зло, по-человечески неумело.\n"
            "Факел вспыхивает ярче от рывка воздуха.\n"
            "Зверь подается назад и ты замахиваешься факелом.\n"
            "Ещё мгновение — и ты видишь как подпалённый волк убегает в темноту между деревьями, бросив свою яму.\n"
            "Остатки факела медленно догорают на земле возле тебя.\n\n"
            "Теперь перед тобой открытая яма под пнём."
        )
        kb = peek_kb

    elif data == "peek_den":
        game.story_state = "cat_choice"
        text = (
            "Ты опускаешься на колени, наклоняешься ближе.\n"
            "В слабом отсвете угасающих угольков факела, почти на самом дне ямы, блестят два огромных влажных глаза.\n"
            "Они смотрят на тебя с ужасом и надеждой одновременно.\n"
            "Маленький, грязный, дрожащий котёнок.\n"
            "Шерсть слиплась от сырости, одно ухо надорвано.\n"
            "Ты тихо протягиваешь руку.\n"
            "Он долго не решается. Потом осторожно, очень медленно обнюхивает твои пальцы.\n"
            "Ты чувствуешь холодный нос и слабое, прерывистое дыхание.\n\n"
            "Твои действия:"
        )
        kb = cat_kb

    elif data == "pet_leave":
        game.karma["gentle"] = max(0, game.karma.get("gentle", 0) - 5)
        game.adjust_narrative_karma("compassion", -3)
        game.story_state = None
        game.reset_nav()
        game.set_story_flag("l1_completed")
        game.story_flags["l1_completed_day"] = getattr(game, "day", 1)
        game.set_story_flag("left_kitten")
        text = (
            "Ты медленно убираешь руку.\n"
            "Котёнок смотрит тебе вслед, но не мяукает.\n"
            "Ты встаёшь, разворачиваешься и уходишь.\n"
            "За спиной остаётся только тишина леса и ощущение, что ты только что прошёл мимо чего-то важного."
        )
        kb = get_main_kb(game)

    elif data == "pet_take":
        game.set_story_flag("saved_kitten")
        game.set_story_flag("has_pet")
        game.set_story_flag("l1_completed")
        game.story_flags["l1_completed_day"] = getattr(game, "day", 1)
        game.adjust_narrative_karma("compassion", 2)
        game.story_state = "WAITING_FOR_PET_NAME"
        text = (
            "Ты осторожно опускаешь обе ладони в яму.\n"
            "Котёнок сначала отшатывается, потом сам делает маленький шаг навстречу.\n"
            "Через секунду он уже у тебя на руках — лёгкий, холодный, дрожащий всем телом.\n"
            "Ты прижимаешь его к груди, прикрывая полой куртки.\n\n"
            "Как ты его назовёшь?"
        )

    elif data == "story_next":
        game.story_state = None
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
    if loc_id != 1:
        return None, None

    # Триггер 1: Встреча со старым волком у пня (пролог L1)
    if torch_equipped:
        torch_count = getattr(game, "torch_research_count", 0) + 1
        game.torch_research_count = torch_count
        if (
            getattr(game, "day", 1) >= 3
            and torch_count >= 4
            and not game.is_story_flag_set("l1_started")
        ):
            return "forest_start", "🔦 Ты замечаешь странные следы и слышишь глухое рычание..."

    # Триггер 2: Обнаружение волчьего логова (L1.5)
    if (
        game.is_story_flag_set("l1_completed")
        and not getattr(game, "wolf_lair_unlocked", False)
        and not game.is_story_flag_set("l1_5_triggered")
    ):
        l1_day = game.story_flags.get("l1_completed_day", 1)
        if game.day >= l1_day + 4:
            game.l1_post_research_count = getattr(game, "l1_post_research_count", 0) + 1
            if game.l1_post_research_count >= 3:
                game.set_story_flag("l1_5_triggered")
                return "l1_5_start", None

    return None, None


def is_story_callback(data: str) -> bool:
    """Проверяет, относится ли данный callback к сюжетным веткам L1 / L1.5-L1.7."""
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
            "story_next",
        )
        or data.startswith(("l1_5", "l1_6", "l1_7", "wolf_lair", "wolf_battle"))
    )


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
            "Нужно вернуться в лагерь и сделать оружие посерьёзнее обычных веток»."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏃 Тихо уйти в лагерь", callback_data="l1_5_leave")]
        ])

    elif data == "l1_5_leave":
        if hasattr(game, "unlock_craft"):
            game.unlock_craft("Крепкий посох")
        elif "Крепкий посох" not in getattr(game, "unlocked_crafts", []):
            game.unlocked_crafts = list(getattr(game, "unlocked_crafts", [])) + ["Крепкий посох"]
        game.locations_unlocked = True
        game.wolf_lair_unlocked = True
        game.wolf_lair_active = True
        game.story_state = None
        game.reset_nav()
        game.add_log("Ты вернулся в лагерь. Открыт крафт: 🪵 Крепкий посох. В меню «Локации» появилось Волчье логово.")
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "wolf_lair_enter":
        game.push_screen("wolf_lair")
        has_staff = game.equipment.get("hand_right") == "Крепкий посох"
        if not has_staff:
            text = (
                "Без надёжного оружия соваться в логово самоубийственно. "
                "Сначала нужно скрафтить и взять в руку крепкий посох."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back")]
            ])
        else:
            text = (
                "Сжимая в руке тяжёлый посох, ты стоишь у входа в пещеру. "
                "Зверь внутри глухо рычит, ожидая твоего шага."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Шагнуть в пещеру", callback_data="wolf_battle_start")],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="back")],
            ])

    elif data == "wolf_battle_start":
        return start_battle(game, "old_wolf")

    elif data in ("wolf_battle_attack", "wolf_battle_defend", "wolf_battle_flee"):
        return apply_action(data, game, "old_wolf")

    elif data == "l1_5_aftermath":
        has_pet = bool(game.equipment.get("pet")) or game.is_story_flag_set("has_pet")
        text = (
            "Тяжёлый удар посоха окончательно сбивает старого волка с ног. "
            "Зверь заваливается на бок и тяжело дышит. Он просто лежит на камнях и ждёт последнего удара."
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
            if count > 0 and is_item_consumable(item) and get_item_type(item) in ("food", "berry", "mushroom")
        ]
        consumables.sort(key=lambda it: (get_item_rank(it), it))
        if consumables:
            food_item = consumables[0]
            game.inventory[food_item] -= 1
            if game.inventory[food_item] <= 0:
                del game.inventory[food_item]
            text = (
                "Ты опускаешь посох, делаешь предупреждающий жест и не приближаешься, давая волку пространство.\n"
                "Свободной рукой ты достаёшь из рюкзака съестное и бросаешь к его лапам.\n"
                "Волк жадно заглатывает кусок и медленно отползает в темноту глубины норы. Путь открыт.\n"
                "──────────\n"
                f"Отдано: {food_item} ×1"
            )
        else:
            text = (
                "Ты опускаешь посох, делаешь предупреждающий жест и не приближаешься, давая волку пространство.\n"
                "У тебя нет с собой еды, но зверь видит, что ты не станешь его добивать.\n"
                "Волк с трудом поднимается и медленно отползает в темноту глубины норы. Путь открыт."
            )
        game.set_story_flag("spared_wolf")
        game.adjust_narrative_karma("compassion", 5)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Шагнуть в расщелину", callback_data="l1_6_passage")]
        ])

    elif data == "l1_5_kill":
        text = "Ты покидаешь пещеру с уверенностью, что на тебя этой ночью никто не нападёт."
        game.set_story_flag("killed_wolf")
        game.adjust_narrative_karma("pragmatism", 5)
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
            "Открыта новая глава: Ручей\n\n"
            "В меню «Локации» открыта новая локация."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 Осмотреться на новом месте", callback_data="l1_7_inspect")]
        ])

    elif data == "l1_7_inspect":
        game.reset_nav()
        game.current_location = "Ручей"
        game.story_state = None
        text, kb = handle_location_2_ruchey("river_ferocious", game, uid)

    elif data == "location_enter_1":
        game.reset_nav()
        game.current_location = "Лесной старт"
        game.add_log("Ты вернулся в Стартовый лес.")
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "location_enter_2":
        game.reset_nav()
        game.current_location = "Ручей"
        text, kb = handle_location_2_ruchey("river_ferocious", game, uid)

    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 2: РУЧЕЙ С ЗМЕЯМИ
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_2_ruchey(data, game, uid):
    """Обработать события на локации 'Ручей с Змеями'."""
    text = None
    kb = None
    
    if data == "river_ferocious":
        text = (
            "Ручей бурлит. Вода холодная, чистая, но в ней плещется что-то чешуйчатое.\n"
            "Ты наклоняешься к воде, зачерпываешь ведром — а оттуда с шипом вылетает змея!\n"
            "Где-то в кустах ещё одна змея поворачивается и смотрит на тебя.\n"
            "Ты задерживаешь дыхание — вода живёт своей жизнью. Что будешь делать?"
        )
        game.karma["clever"] = game.karma.get("clever", 0) + 2
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 1
        game.story_state = "river_encounter"
        kb = wolf_kb
        
    elif data == "snake_flee":
        game.adjust_narrative_karma("pragmatism", 2)
        game.set_story_flag("snake_interaction")
        game.set_story_flag("bag_obtained")
        text = (
            "Ты резко отпрыгиваешь, вода шлёпается в лужу.\n"
            "Змея, недовольная неудачным прыжком, скрывается в камышах.\n"
            "Ты достал ведро воды, но не без труда — вода была мутной, тёплой, живой.\n\n"
            "Собрано воды: " + str(game.inventory.get("Вода", 0) + 2)
        )
        game.inventory["Вода"] = game.inventory.get("Вода", 0) + 2
        game.add_log("Нашёл воду в змеином ручье.")
        game.story_state = "river_collect"
        kb = get_main_kb(game)
        
    elif data == "snake_stab":
        text = (
            "Змея не заметила твоего движения и устроила тебе сюрприз — укус в щиколотку!\n"
            "Она впрыскивает яд, прохладный, сладковатый, как амброзия.\n"
            "Ты падаешь в воду, охлаждая кожу, и чувствуешь, как жжение распространяется.\n"
            "Но вода спасает — она гасит огонь в крови.\n\n"
            "Жажда снизилась, но есть лёгкое отравление..."
        )
        # Урон 15 с учётом физиологии
        new_hp, damage_log = process_damage(game, raw_damage=15)
        game.hp = new_hp
        
        # Списание из Голода (базовая стоимость 10)
        hunger_cost = get_base_resource_cost(game, base_cost=10)
        game.hunger = max(1, game.hunger - hunger_cost)
        
        game.karma["brutal"] = game.karma.get("brutal", 0) + 1
        game.karma["gentle"] = game.karma.get("gentle", 0) - 1
        game.story_state = "snake_poisoned"
        kb = get_main_kb(game)
        
    elif data == "river_calm":
        game.adjust_narrative_karma("compassion", 1)
        game.adjust_narrative_karma("pragmatism", 2)
        game.set_story_flag("snake_interaction")
        text = (
            "Тишина. Вода плещется ровно, как будто это сердце леса.\n"
            "Ты медленно опускаешь ведро — вода холодная, прозрачная, без запаха.\n"
            "Змеи ушли, довольные своей добычей (или твоей добычей).\n\n"
            "Идеальная вода для жизни."
        )
        game.inventory["Вода"] = game.inventory.get("Вода", 0) + 3
        game.karma["gentle"] = game.karma.get("gentle", 0) + 2
        game.story_state = "river_collected"
        kb = get_main_kb(game)
        
    elif data == "river_cool":
        text = (
            "Вода обволакивает тебя, как ледяной поцелуй.\n"
            "Тебе становится прохладно, но приятно — жажда отступает, голова проясняется.\n"
            "Змеи прячутся в тени, наблюдая за тобой из-под кустов.\n\n"
            "Освежающая ванна в диком ручье."
        )
        # Жажда восстанавливается с учётом коэффициента
        thirst_restore = 25 * get_resource_multiplier(game, "thirst")
        game.thirst = min(100, game.thirst + thirst_restore)
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 1
        game.story_state = "river_cooldown"
        kb = get_main_kb(game)
        
    elif data == "river_deep":
        game.adjust_narrative_karma("observation", 3)
        game.set_story_flag("snake_interaction")
        text = (
            "Ты делаешь шаг вглубь — вода по колено, чистая, как слёза.\n"
            "Оттуда, из самого дна, на тебя смотрят два жёлтых глаза.\n"
            "Змея-глаз, змея-хозяин этого ручья?\n"
            "Она поднимается, создавая рябь, и ты понимаешь: здесь живёт что-то древнее."
        )
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 3
        game.add_log("Встреча с древним существом ручья.")
        game.story_state = "river_ancient"
        kb = wolf_kb
        
    elif data == "river_end":
        text = (
            "Ты выходишь на берег, подсушивая одежду.\n"
            "Вода теперь в инвентаре — она спасёт тебя, если жара станет невыносимой.\n"
            "Змеиный ручей позади, но его память останется с тобой."
        )
        game.story_state = None
        if hasattr(game, "reset_nav"):
            game.reset_nav()
        kb = get_main_kb(game)
    
    elif data == "river_brave":
        text = (
            "Ты решаешься на смелый поступок — бежишь к воде, несмотря на опасность.\n"
            "Змеи шипят, но не атакуют. Ты быстро наполняешь ведро и отступаешь.\n"
            "Твой героизм замечен — даже древний ручей уважает смелость.\n\n"
            "Вода горячая на ощупь, как будто от огня, но очень чистая."
        )
        game.inventory["Вода"] = game.inventory.get("Вода", 0) + 4
        game.karma["heroic"] = game.karma.get("heroic", 0) + 3
        game.karma["reckless"] = game.karma.get("reckless", 0) + 1
        game.story_state = "river_brave_end"
        kb = get_main_kb(game)
    
    elif data == "river_talk":
        game.adjust_narrative_karma("compassion", 2)
        game.set_story_flag("snake_interaction")
        text = (
            "Ты начинаешь говорить со змеями — рассказываешь им о себе, о лесе, о жизни.\n"
            "Чудо: они слушают. Не атакуют, просто слушают.\n"
            "После твоих слов они медленно расступаются, открывая путь к чистой воде.\n\n"
            "Ты понимаешь: в этом лесу всё живое, всё имеет дух."
        )
        game.inventory["Вода"] = game.inventory.get("Вода", 0) + 3
        game.karma["gentle"] = game.karma.get("gentle", 0) + 2
        game.karma["clever"] = game.karma.get("clever", 0) + 1
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 2
        game.story_state = "river_talked"
        kb = get_main_kb(game)
    
    elif data == "river_dance":
        text = (
            "Ты начинаешь танцевать у берега, подражая движениям змей.\n"
            "Хаотично, но с искренностью. Вода брызжет, звёзды отражаются в ней.\n"
            "Змеи притихли. Может быть, они восхищены? Или пугаются безумца?\n"
            "Неважно — ты собираешь воду, смеясь, как давно не смеялся.\n\n"
            "Этот момент безумия дарует тебе внутренний мир."
        )
        game.inventory["Вода"] = game.inventory.get("Вода", 0) + 2
        game.karma["reckless"] = game.karma.get("reckless", 0) + 2
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 1
        
        # Голод с учётом коэффициента
        hunger_mult = get_resource_multiplier(game, "hunger")
        game.hunger = max(1, game.hunger - 10 * hunger_mult)
        
        game.story_state = "river_danced"
        kb = get_main_kb(game)
    
    elif data == "river_sacrifice":
        text = (
            "Ты жертвуешь часть своей еды змеям — знак мира.\n"
            "Они рассматривают дар с интересом, затем поглощают его.\n"
            "И вдруг атмосфера меняется. Ручей становится спокойным, гостеприимным.\n\n"
            "Жертва принесена, перемирие заключено."
        )
        game.inventory["Еда"] = max(0, game.inventory.get("Еда", 0) - 1)
        game.inventory["Вода"] = game.inventory.get("Вода", 0) + 3
        game.karma["gentle"] = game.karma.get("gentle", 0) + 3
        game.karma["heroic"] = game.karma.get("heroic", 0) + 1
        game.story_state = "river_sacrificed"
        kb = get_main_kb(game)
        
    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 3: СКРОМНАЯ ЛОЩИНА
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_3_slate_hollow(data, game, uid):
    """Обработать события на локации 'Скромная Лощина'."""
    text = None
    kb = None
    
    if data == "slate_hollow_start":
        text = (
            "Ты перешагиваешь порог Скромной Лощины. Воздух здесь плотный, прохладный,\n"
            "запах влажного камня и древней глины. Стены выложены из тёмного сланца,\n"
            "отражая тусклый свет факела.\n\n"
            "Что будешь делать?"
        )
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 2
        game.story_state = "slate_encounter"
        kb = get_main_kb(game)
    
    elif data == "slate_examine":
        game.adjust_narrative_karma("observation", 3)
        text = (
            "Ты осматриваешь стены — сланец холодный на ощупь, с тонкими прожилками.\n"
            "Где-то в углу лежит глиняный слиток — основа для крафта новой брони.\n\n"
            "Сланцевая Лощина — место, где камень живёт своей жизнью."
        )
        game.karma["clever"] = game.karma.get("clever", 0) + 1
        game.story_state = "slate_exploring"
        kb = get_main_kb(game)
    
    elif data == "slate_climb":
        game.adjust_narrative_karma("intervention", 2)
        text = (
            "Ты взбираешься по ступеням, ведущим к верхней палате. Сланец скрипит под ногами,\n"
            "отдавая эхом в пустоту. Вверху — ещё больше глины, ещё больше возможностей.\n\n"
            "Поднимайся выше — там ждут новые открытия."
        )
        game.karma["heroic"] = game.karma.get("heroic", 0) + 1
        game.story_state = "slate_upper"
        kb = get_main_kb(game)
    
    elif data == "slate_rest":
        game.adjust_narrative_karma("compassion", 1)
        text = (
            "Ты накрываешься на свежем камне, давая телу отдохнуть. Прохладный сланец\n"
            "впитывает тепло, а ты чувствуешь, как напряжение спадает.\n\n"
            "Отдых в каменистой палате — редкое удовольствие."
        )
        game.karma["gentle"] = game.karma.get("gentle", 0) + 1
        game.story_state = "slate_resting"
        kb = get_main_kb(game)
    
    elif data == "slate_end":
        text = (
            "Ты покидаешь Лощину, оставляя за собой лишь воспоминания о холодном камне\n"
            "и глиняных слитках. Сланцевая броня теперь часть твоего арсенала."
        )
        game.story_state = None
        if hasattr(game, "reset_nav"):
            game.reset_nav()
        kb = get_main_kb(game)
    
    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 4: ПРОСЕКА ОХОТНИКОВ
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_4_hunters_glade(data, game, uid):
    """Обработать события на локации 'Просека Охотников'."""
    text = None
    kb = None
    
    if data == "hunters_glade_start":
        text = (
            "Просека охотников раскинулась перед тобой как гигантский стол.\n"
            "На земле — следы, множество следов. Волков. Оленей. Людей, которые пришли и ушли давно.\n"
            "В воздухе пахнет дымом и кровью, давнишней, старой.\n\n"
            "Что будешь делать?"
        )
        game.karma["reckless"] = game.karma.get("reckless", 0) + 1
        game.story_state = "hunters_encounter"
        kb = get_main_kb(game)
    
    elif data == "hunters_trap":
        game.adjust_narrative_karma("pragmatism", 2)
        text = (
            "Ты осматриваешь старые ловушки. Некоторые еще целы, готовы принять добычу.\n"
            "В одной из них — остатки мяса, высохшие, как кость.\n"
            "Ты осторожно срезаешь мясо и добавляешь его в ёмкость.\n\n"
            "Охотник охотит, даже если охотников давно нет."
        )
        game.inventory["Еда"] = game.inventory.get("Еда", 0) + 1
        game.karma["clever"] = game.karma.get("clever", 0) + 1
        game.karma["reckless"] = game.karma.get("reckless", 0) + 1
        game.story_state = "hunters_trapped"
        kb = get_main_kb(game)
    
    elif data == "hunters_blood":
        game.adjust_narrative_karma("observation", 3)
        text = (
            "Следы крови на земле. Свежей. Очень свежей.\n"
            "Волк или олень? Кто охотился, кого охотили?\n"
            "Ты следишь по крови — она ведёт в кусты, где ты находишь раненого оленя.\n\n"
            "Выбор: помочь или оставить?"
        )
        game.karma["gentle"] = game.karma.get("gentle", 0) + 1
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 1
        game.story_state = "hunters_blood_choice"
        kb = get_main_kb(game)
    
    elif data == "hunters_animal_help":
        game.adjust_narrative_karma("compassion", 3)
        game.set_story_flag("helped_deer")
        game.set_story_flag("deer_freed")
        game.set_story_flag("left_warning")
        text = (
            "Ты подходишь к оленю тихо, без угрозы. Его глаза полны боли.\n"
            "Ты перевязываешь рану тканью, даёшь воду.\n"
            "Олень медленно встаёт и уходит в лес, живой благодаря тебе.\n\n"
            "Одна жизнь спасена. Может быть, это важно."
        )
        # Вода с учётом коэффициента голода
        water_cost = 1 * get_resource_multiplier(game, "hunger")
        game.inventory["Вода"] = max(0, game.inventory.get("Вода", 0) - water_cost)
        game.karma["gentle"] = game.karma.get("gentle", 0) + 3
        game.karma["heroic"] = game.karma.get("heroic", 0) + 1
        game.story_state = "hunters_helped"
        kb = get_main_kb(game)
    
    elif data == "hunters_fire":
        game.adjust_narrative_karma("intervention", 2)
        text = (
            "В центре просеки — остатки охотничьего костра. Он давно потух, но угли ещё теплые.\n"
            "Рядом лежат охотничьи принадлежности, забытые или специально оставленные.\n"
            "Ты разжигаешь костер, и вскоре тепло согревает окрестности.\n\n"
            "Старый огонь охотников горит ещё раз."
        )
        game.karma["clever"] = game.karma.get("clever", 0) + 2
        game.karma["brutal"] = game.karma.get("brutal", 0) + 1
        
        # Жажда и Голод с учётом коэффициентов
        thirst_restore = 10 * get_resource_multiplier(game, "thirst")
        game.thirst = min(100, game.thirst + thirst_restore)
        
        hunger_mult = get_resource_multiplier(game, "hunger")
        game.hunger = max(1, game.hunger + 5 * hunger_mult)
        
        game.story_state = "hunters_fired"
        kb = get_main_kb(game)

    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 5: ЯР СЛИЗНЕЙ
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_5_slug_pit(data, game, uid):
    """Обработать события на локации 'Яр Слизней'."""
    text = None
    kb = None
    
    if data == "slug_pit_start":
        text = (
            "Яр Слизней — это не место для слабых духом.\n"
            "Земля здесь влажная, липкая, покрыта слизью от огромных существ.\n"
            "Грибы растут в странных местах, светятся в темноте фосфоресцирующим светом.\n"
            "Воздух пахнет гнилью и жизнью одновременно.\n\n"
            "Что будешь делать?"
        )
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 2
        game.karma["reckless"] = game.karma.get("reckless", 0) + 1
        game.story_state = "slug_encounter"
        kb = get_main_kb(game)
    
    elif data == "slug_mushroom":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("maximum_resources")
        text = (
            "Светящиеся грибы привлекают твоё внимание. Они пульсируют жизнью, как сердца.\n"
            "Ты осторожно срезаешь несколько грибов и добавляешь в сумку.\n"
            "Они светят слабо, но красиво, освещая путь в темноте яра.\n\n"
            "Природное волшебство, собранное своими руками."
        )
        game.inventory["Грибы"] = game.inventory.get("Грибы", 0) + 3
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 2
        game.story_state = "slug_mushroom_gathered"
        kb = get_main_kb(game)
    
    elif data == "slug_giant":
        game.adjust_narrative_karma("compassion", 1)
        game.set_story_flag("slug_interaction")
        text = (
            "Ты видишь её — гигантскую слизь, размером с человека.\n"
            "Она медленно скользит между грибов, оставляя блестящий след.\n"
            "Её глаза (если это глаза?) смотрят на тебя без враждебности, просто с интересом.\n"
            "Вы смотрите друг на друга, два существа из разных миров.\n\n"
            "Никто не движется. Никто не атакует."
        )
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 3
        game.karma["gentle"] = game.karma.get("gentle", 0) + 1
        game.story_state = "slug_met_giant"
        kb = get_main_kb(game)
    
    elif data == "slug_slime":
        text = (
            "На земле — старая слизь, засохшая, как янтарь.\n"
            "Ты осторожно собираешь её в контейнер. Она светит странным светом.\n"
            "Это слизь какого-то давно умершего существа? Или просто природный материал?\n\n"
            "В этом яре всё странно, всё полно тайн."
        )
        game.inventory["Слизь"] = game.inventory.get("Слизь", 0) + 2
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 1
        game.karma["reckless"] = game.karma.get("reckless", 0) + 1
        game.story_state = "slug_slime_collected"
        kb = get_main_kb(game)
    
    elif data == "slug_deep":
        game.adjust_narrative_karma("intervention", 2)
        game.adjust_narrative_karma("observation", 2)
        game.set_story_flag("slug_interaction")
        text = (
            "Ты решаешься спуститься глубже, в самую пучину яра.\n"
            "Здесь воздух становится тяжелее, плотнее. Слизь повсюду, как густая паутина.\n"
            "Ты находишь источник — гигантский кокон из слизи, внутри которого что-то движется.\n\n"
            "Рождение? Смерть? Трансформация?"
        )
        game.karma["reckless"] = game.karma.get("reckless", 0) + 2
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 2
        game.story_state = "slug_deep_seen"
        kb = get_main_kb(game)

    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 6: МОХНАТАЯ ПЕЩЕРА
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_6_furry_cave(data, game, uid):
    """Обработать события на локации 'Мохнатая Пещера'."""
    text = None
    kb = None
    
    if data == "furry_cave_start":
        text = (
            "Ты входишь в Мохнатую Пещеру. Воздух здесь тёплый, пахнет дымом, мехом\n"
            "и древними кострами. Стены покрыты слоями налёта, а пол — мягким мхом.\n\n"
            "Что будешь делать?"
        )
        game.karma["mysterious"] = game.karma.get("mysterious", 0) + 2
        game.story_state = "furry_encounter"
        kb = get_main_kb(game)
    
    elif data == "furry_examine":
        game.adjust_narrative_karma("observation", 2)
        text = (
            "Ты осматриваешь пещеру — меховые шкуры лежат тут и там, словно\n"
            "кто-то только что ушёл на охоту. В углу — старый каменный очаг,\n"
            "ещё тлеющий углём.\n\n"
            "Мохнатая Пещера — убежище для тех, кто ищет тепла."
        )
        game.karma["gentle"] = game.karma.get("gentle", 0) + 1
        game.story_state = "furry_exploring"
        kb = get_main_kb(game)
    
    elif data == "furry_warm":
        game.adjust_narrative_karma("pragmatism", 1)
        game.adjust_narrative_karma("intervention", 2)
        text = (
            "Ты раздуваешь огонь, и пещера наполняется уютом. Меховые шкуры\n"
            "обволакивают тебя, как мягкое одеяло. Жажда отступает, тело согревается.\n\n"
            "Тепло — редкий гость в этом лесу."
        )
        game.karma["brutal"] = game.karma.get("brutal", 0) + 1
        game.story_state = "furry_warmed"
        kb = get_main_kb(game)
    
    elif data == "furry_sleep":
        game.adjust_narrative_karma("compassion", 2)
        game.set_story_flag("something_was_taken")
        text = (
            "Ты укладываешься на мягкий мох, подложив меховую шкуру под голову.\n"
            "Сон приходит быстро — здесь тихо, тепло и безопасно.\n\n"
            "Ночь в пещере — лучший отдых для уставшего путника."
        )
        game.karma["gentle"] = game.karma.get("gentle", 0) + 2
        game.story_state = "furry_sleeping"
        kb = get_main_kb(game)
    
    elif data == "furry_end":
        text = (
            "Ты покидаешь Пещеру, оставляя за собой лишь воспоминания о тёплом мехе\n"
            "и каменном очаге. Меховые шкуры теперь часть твоего инвентаря."
        )
        game.story_state = None
        if hasattr(game, "reset_nav"):
            game.reset_nav()
        kb = get_main_kb(game)
    
    return text, kb


# ──────────────────────────────────────────────────────────────────────────────
# ЛОКАЦИЯ 7: ВЕРШИНА СВЯТИЛИЩА
# ──────────────────────────────────────────────────────────────────────────────

def handle_location_7_sanctuary_peak(data, game, uid):
    """Обработать события на локации 'Вершина Святилища'."""
    text = None
    kb = None
    
    if data == "sanctuary_resolve":
        ending_code = resolve_ending(game)
        game.story_flags["ending_code"] = ending_code
        game.story_state = "completed"
        text = f"{ENDING_TITLES[ending_code]}\n\n{ending_text(ending_code)}"
        kb = get_main_kb(game)
        return text, kb

    if data == "sanctuary_peak_start":
        text = (
            "Ты достиг вершины. Выше уже ничего нет — только небо и звёзды.\n"
            "Здесь, на самой вершине, лежат камни, расположенные в странную мандалу.\n"
            "В центре — старая чаша, заросшая мхом, наполненная водой, чистой как слеза.\n"
            "Ты понимаешь: это конец пути.\n\n"
            "Твоя карма подскажет, какая развязка тебя ждёт."
        )
        game.story_state = "sanctuary_choice"
        kb = get_main_kb(game)
        return text, kb
    
    elif data == "sanctuary_heroic":
        text = (
            "Ты наполняешь чашу водой из родника, что течёт с верхушки святилища.\n"
            "В этот момент небо вспыхивает золотом — ты видишь образ Героя, который ушёл здесь давно.\n"
            "Его голос в твоём сознании: 'Ты прошёл испытание. Лес отпускает тебя, герой.'\n\n"
            "Ты спускаешься со святилища, и лес отступает, открывая дорогу к дому."
        )
        game.story_state = "sanctuary_heroic_end"
        kb = get_main_kb(game)
        return text, kb
    
    elif data == "sanctuary_gentle":
        text = (
            "Ты нежно касаешься поверхности воды в чаше.\n"
            "Мир замирает. Ты видишь не врагов в лесу, а друзей, потерянных и вновь найденных.\n"
            "Лес не враг, а живое существо, нуждающееся в заботе.\n"
            "Ты осознаёшь: можно остаться здесь, стать хранителем этого места.\n\n"
            "Или вернуться в мир людей, изменённым, но целым."
        )
        game.story_state = "sanctuary_gentle_end"
        kb = get_main_kb(game)
        return text, kb
    
    elif data == "sanctuary_mysterious":
        text = (
            "Ты пьёшь воду из чаши.\n"
            "Видение охватывает тебя — ты видишь лес таким, каким он был тысячи лет назад.\n"
            "Видишь существа, которые здесь жили до людей, видишь магию, которая в земле.\n"
            "Ты больше не человек простой — ты хранитель древних знаний.\n\n"
            "Лес принял тебя как своего."
        )
        game.story_state = "sanctuary_mysterious_end"
        kb = get_main_kb(game)
        return text, kb
    
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

- **Вмешательство** — насколько герой активно вмешивается и рискует
- **Сострадание** — помощь другим, мягкость, оставление чего-то после себя
- **Прагматизм** — берёт полезное и уходит, минимизирует риск
- **Наблюдательность** — замечает детали, следы, предупреждения

Очки начисляются **по полному пути**, который прошёл игрок в локации.

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
    source = ENDING_STORY_TEXT
    title = ENDING_TITLES[code]
    marker = f"Исход {list(ENDING_TITLES).index(code) + 1}. {title}"
    start = source.index(marker) + len(marker)
    remainder = source[start:]
    end = remainder.find("\n\nКритерии:")
    return remainder[:end if end >= 0 else len(remainder)].strip()


# Загружаем канонические тексты L1-L6 после объявления финалов, чтобы
# story/location_sources.py мог безопасно получить текст L7 без циклического импорта.
from story.location_sources import LOCATION_SOURCE_TEXTS, get_location_source_text
