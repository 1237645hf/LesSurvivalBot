# =============================================================================
# ЛОКАЦИЯ 1: Лесной старт (Лес)
# =============================================================================
#
# ПРАВИЛА ЭТОГО ФАЙЛА:
# 1. Здесь лежит ВСЁ, что относится ТОЛЬКО к Локации 1.
# 2. Никакого кода других локаций.
# 3. Общие хелперы импортируются только из story.common (пока можно оставить заглушку).
# 4. Не создавать отдельные .txt файлы.
#
# Структура:
#   1. Локальные константы (если есть)
#   2. Все handle_* функции этой локации
# =============================================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import (
    get_main_kb,
    wolf_kb,
    get_wolf_battle_kb,
    get_death_kb,
)
from game_state import get_death_text
from modules.items import (
    is_item_consumable,
    get_item_rank,
    get_item_type,
    get_item_emoji,
)
from modules.combat import (
    start_battle,
    apply_action,
    get_battle_text,
    get_battle_kb,
    get_battle_text as get_wolf_battle_text,
)


def handle_location_1_forest_start(data: str, game, uid: int):
    """Сюжетные разветвления для Локации 1: Лесной старт (котёнок, купол, волчье логово)."""
    if data.startswith("l1_dome"):
        return handle_l1_dome(data, game, uid)

    if (
        data.startswith("l1_5")
        or data.startswith("l1_6")
        or data.startswith("l1_7")
        or data.startswith("wolf_lair")
        or data.startswith("wolf_battle")
        or data in ("location_enter_1", "location_enter_2")
    ):
        return handle_l1_wolf_lair(data, game, uid)

    text = None
    kb = None

    if data in ("forest_start", "story_start", "wolf_start", "action_1"):
        game.story_state = "wolf_encounter"
        game.set_story_flag("l1_started")
        text = (
            "Ты идёшь между стволов деревьев и вдруг замираешь.\n"
            "Где-то совсем рядом — хриплое рычание, тяжёлое дыхание и отчаянное шипение.\n"
            "Очень осторожно, почти не дыша, ты раздвигаешь ветки и смотришь.\n"
            "Перед тобой — старый, истощённый волк. Через редкую шерсть на боках виднеются обтянутые кожей рёбра. Один глаз мутный, на теле — следы незатянувшихся ран.\n"
            "Он яростно копает лапами под старым пнём, совсем тебя не замечая.\n"
            "Факел в твоей руке потрескивает, бросая дрожащие тени на листья перед тобой.\n\n"
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

    if kb == get_main_kb(game) or data in ("wolf_leave", "pet_leave", "l1_2a_leave", "l1_2c_leave", "kitten_to_main", "story_next", "back") or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        if data in ("l1_3", "pet_take", "waiting_pet_name"):
            game.active_story_callback = "waiting_pet_name"
        else:
            game.active_story_callback = data

    return text, kb


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
        already_completed = game.is_story_flag_set("l1_dome_completed")
        if not already_completed and game.ap < 1:
            text = (
                "Ранец лежит прямо среди густого валежника, колючего терновника и вывороченных корней дуба.\n\n"
                "У тебя нет сил расчистить завал! Нужно отдохнуть и набраться сил."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Нет сил расчищать", callback_data="menu_main")],
            ])
            return text, kb

        if not already_completed:
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
        game.location = game.current_location
        game.story_state = None
        from story.location_stories import handle_location_2_ruchey
        text, kb = handle_location_2_ruchey("location_enter_2", game, uid)
        if not game.is_story_flag_set("l2_prologue_completed"):
            game.active_story_callback = "l2_1"

    elif data == "location_enter_1":
        game.reset_nav()
        game.current_location = "Лесной старт"
        game.add_log("Ты вернулся в Стартовый лес.")
        text = game.get_ui()
        kb = get_main_kb(game)

    elif data == "location_enter_2":
        game.reset_nav()
        game.current_location = "Ручей"
        game.location = game.current_location
        from story.location_stories import handle_location_2_ruchey
        text, kb = handle_location_2_ruchey("location_enter_2", game, uid)
        if not game.is_story_flag_set("l2_prologue_completed"):
            game.active_story_callback = "l2_1"

    if kb == get_main_kb(game) or data in ("l1_5_leave", "l1_7_finish", "location_enter_1", "back") or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        battle = getattr(game, "wolf_battle", None)
        if battle and getattr(game, "hp", 100) > 0 and battle.get("wolf_hp", 0) > 0:
            cur_enemy = battle.get("enemy_id", "old_wolf")
            game.active_story_callback = "boar_battle_screen" if cur_enemy == "ancient_boar" else "wolf_battle_screen"
        elif data in ("l1_7_inspect", "location_enter_2") and not game.is_story_flag_set("l2_prologue_completed"):
            game.active_story_callback = "l2_1"
        else:
            game.active_story_callback = data

    return text, kb
