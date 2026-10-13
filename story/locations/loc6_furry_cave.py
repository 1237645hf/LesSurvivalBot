# =============================================================================
# ЛОКАЦИЯ 6: Мохнатая Пещера
# =============================================================================
#
# ПРАВИЛА ЭТОГО ФАЙЛА:
# 1. Здесь лежит ВСЁ, что относится ТОЛЬКО к Локации 6.
# 2. Никакого кода других локаций.
# 3. Общие хелперы импортируются только из story.common (пока можно оставить прямые импорты).
# 4. Не создавать отдельные .txt файлы.
#
# Структура:
#   1. Локальные константы (если есть)
#   2. Все handle_* функции этой локации
# =============================================================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import keyboards

def get_main_kb(*args, **kwargs):
    try:
        import story.location_stories as _ls
        if hasattr(_ls, 'get_main_kb'):
            return _ls.get_main_kb(*args, **kwargs)
    except Exception:
        pass
    return keyboards.get_main_kb(*args, **kwargs)


def unlock_warm_cave_shelter(game):
    """Активирует Тёплую пещеру, рецепты мехового сета и защиту."""
    game.set_story_flag("warm_cave_shelter", True)
    game.set_story_flag("fur_recipes_unlocked", True)
    unlocked = getattr(game, "unlocked_crafts", None)
    if unlocked is not None:
        for r in ("Меховой капюшон", "Меховой плащ-нагрудник", "Меховые поножи", "Меховые сапоги"):
            if r not in unlocked:
                unlocked.append(r)


def deduct_story_gift_item(game):
    """Списать 1 единицу подходящего припаса из инвентаря для сюжетного схрона / подарка взамен.

    Использует стандартный сюжетный инвентарь (modules/items.py), отдавая приоритет
    сытным припасам и еде без ручного перебора произвольных списков в коде экранов.
    """
    from modules.items import is_item_consumable, get_item_type

    # 1. Приоритетные готовые припасы выживания
    preferred = ("Жареное мясо", "Сухпай", "Мясо на коре", "Печёные ягоды", "Жареные грибы", "Сырое мясо")
    for it in preferred:
        if game.inventory.get(it, 0) > 0:
            game.inventory[it] -= 1
            if game.inventory[it] <= 0:
                del game.inventory[it]
            return it

    # 2. Любые другие съедобные припасы (ягоды, грибы, отвары) через реестр items.py
    for it, count in list(game.inventory.items()):
        if count > 0 and is_item_consumable(it):
            itype = get_item_type(it)
            if itype in ("food", "berry", "mushroom"):
                game.inventory[it] -= 1
                if game.inventory[it] <= 0:
                    del game.inventory[it]
                return it

    return None


def handle_location_6_furry_cave(data, game, uid):
    """Обработать события на локации 'Мохнатая Пещера' (L6)."""
    text = None
    kb = None

    # При взаимодействии с Тёплой пещерой активируем шелтер и рецепты
    if data.startswith("furry_") or data == "l6_ascent_step40":
        unlock_warm_cave_shelter(game)

    if data == "location_enter_6":
        game.current_location = "Мохнатая пещера"
        game.location_index = 5
        game.location = game.current_location
        game.pre_story_location = game.current_location
        if game.is_story_flag_set("warm_cave_shelter"):
            data = "furry_cave_start"
        else:
            game.story_state = None
            game.active_story_callback = None
            return game.get_ui(), get_main_kb(game)

    if data == "furry_cave_start":
        unlock_warm_cave_shelter(game)
        game.story_state = "furry_cave_start"
        text = (
            "Ты входишь в Мохнатую Пещеру. Воздух здесь тёплый, пахнет дымом, мехом "
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
            "Ты стоишь ещё мгновение на пороге, вдыхая тёплый воздух. "
            "Потом разворачиваешься и выходишь. "
            "Снаружи снова сыро и холодно."
        )
        game.story_state = None
        kb = get_main_kb(game)

    elif data == "furry_examine":
        if not game.is_story_flag_set("furry_cave_examined"):
            game.set_story_flag("furry_cave_examined", True)
            game.adjust_narrative_karma("observation", 1)
        game.story_state = "furry_examine"
        text = (
            "Ты медленно обходишь просторный грот. Шкуры на стенах разной свежести. "
            "В дальнем углу, под нависшим каменным выступом, лежит аккуратный свёрток из плотной шкуры, "
            "перевязанный бечёвкой. Рядом на каменном уступе темнеют несколько костяных игл и мелкие обрезки меха.\n\n"
            "Кто-то регулярно поддерживал здесь порядок."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Развернуть свёрток", callback_data="furry_bundle")],
            [InlineKeyboardButton(text="✋ Не трогать свёрток", callback_data="furry_bundle_leave")],
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_cave_start")],
        ])

    elif data == "furry_bundle":
        game.story_state = "furry_bundle"
        if game.is_story_flag_set("furry_bundle_taken"):
            text = (
                "Ты снова развязываешь тонкую бечёвку свёртка. Внутри совершенно пусто — лишь сухая шершавая мездра шкуры и нацарапанная углем надпись: "
                "«Бери, если нужно. Оставь, если сможешь». Весь найденный здесь мех уже перекочевал в твой походный мешок без остатка. "
                "В прохладном дальнем углу под каменным навесом больше ничего нет, кроме брошенных деревянных игл и мелких обрезков нитей. "
                "Пора возвращаться к тёплому очагу или готовиться ко сну."
            )
            buttons = []
            if not game.is_story_flag_set("left_something_in_bundle"):
                buttons.append([InlineKeyboardButton(text="🎁 Положить подарок взамен", callback_data="furry_leave_gift")])
            buttons.append([InlineKeyboardButton(text="✋ Отойти от свёртка", callback_data="furry_bundle_leave")])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        elif game.is_story_flag_set("furry_bundle_part_taken"):
            text = (
                "Ты развязываешь бечёвку свёртка. Внутри остался один добротный кусок выделанного меха и берестяные выкройки. "
                "На шкуре всё так же темнеет нацарапанная углем надпись: «Бери, если нужно. Оставь, если сможешь». "
                "Взята лишь часть припасов ради другого замерзающего путника. "
                "Ты можешь забрать оставшийся мех в рюкзак, оставить что-то взамен или аккуратно завернуть свёрток обратно и отойти к огню."
            )
            buttons = [
                [InlineKeyboardButton(text="🎒 Забрать остаток (+1)", callback_data="furry_take_remainder")],
            ]
            if not game.is_story_flag_set("left_something_in_bundle"):
                buttons.append([InlineKeyboardButton(text="🎁 Положить подарок взамен", callback_data="furry_leave_gift")])
            buttons.append([InlineKeyboardButton(text="✋ Оставить всё как есть", callback_data="furry_bundle_leave")])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        elif game.is_story_flag_set("left_something_in_bundle"):
            text = (
                "Ты развязываешь бечёвку. Внутри аккуратно уложены три куска меха, а рядом лежит оставленный тобой припас. "
                "Никто не тревожил свёрток с твоего последнего визита. Надпись на внутренней стороне шкуры напоминает о неписаном законе гор: "
                "«Бери, если нужно. Оставь, если сможешь». Приятно видеть, что схрон в полном порядке. "
                "Ты аккуратно заворачиваешь свёрток и укладываешь его обратно на каменный уступ."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✋ Оставить всё как есть", callback_data="furry_bundle_leave")],
            ])
        else:
            text = (
                "Ты развязываешь тонкую бечёвку свёртка. Внутри лежат три отличных куска плотного выделанного меха, "
                "берестяные выкройки тёплой одежды и короткая надпись, нацарапанная углем на шкуре: "
                "«Бери, если нужно. Оставь, если сможешь». Схрон явно оставлен для выживания тех, кто одолел подъём сквозь ледяные гроты. "
                "Предстоит решить, сколько припасов взять себе, а сколько сберечь для следующих путников."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎒 Забрать весь мех (+3)", callback_data="furry_take_all")],
                [InlineKeyboardButton(text="✂️ Взять часть (+2)", callback_data="furry_take_part")],
                [InlineKeyboardButton(text="🎁 Положить подарок взамен", callback_data="furry_leave_gift")],
                [InlineKeyboardButton(text="✋ Оставить всё как есть", callback_data="furry_bundle_leave")],
            ])

    elif data == "furry_take_all":
        if not game.is_story_flag_set("furry_bundle_taken") and not game.is_story_flag_set("furry_bundle_part_taken"):
            game.adjust_narrative_karma("pragmatism", 2)
            game.inventory["Мех"] = game.inventory.get("Мех", 0) + 3
            game.set_story_flag("furry_bundle_taken")
            game.add_log("Получено: Мех ×3")
            text = (
                "Ты аккуратно убираешь весь выделанный мех на самое дно походного мешка (+3 Мех). "
                "Внутри свёртка больше ничего не остаётся, кроме старых берестяных выкроек. "
                "Трезвый прагматизм подсказывает, что в морозных горах ценен каждый тёплый лоскут, и лишних припасов здесь просто не бывает. "
                "Завязав пустую шкуру и оставив её на скальном уступе, ты с полезной добычей возвращаешься в центр просторной тёплой пещеры."
            )
        else:
            text = (
                "Свёрток уже абсолютно пуст: весь найденный здесь мех был забран в рюкзак во время прошлого осмотра схрона. "
                "На шершавом базальте лежат лишь оставленные берестяные выкройки да пара костяных швейных игл. "
                "Тратить драгоценное время на повторные поиски бессмысленно — здесь больше не осталось ничего полезного. "
                "Пора вернуться к согревающему пещерному очагу или как следует устроиться на ночлег."
            )
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Лечь отдохнуть", callback_data="furry_sleep")],
        ])

    elif data == "furry_take_part":
        if not game.is_story_flag_set("furry_bundle_taken") and not game.is_story_flag_set("furry_bundle_part_taken"):
            game.adjust_narrative_karma("compassion", 1)
            game.inventory["Мех"] = game.inventory.get("Мех", 0) + 2
            game.set_story_flag("furry_bundle_part_taken")
            game.add_log("Получено: Мех ×2")
            text = (
                "Ты забираешь два куска выделанного меха, а третий бережно оставляешь на месте (+2 Мех). "
                "Берестяные выкройки аккуратно уложены рядом на плоский камень. "
                "Забота о тех, кто может прийти следом на пределе сил, приносит тихое душевное спокойствие. "
                "Ты аккуратно заворачиваешь свёрток бечёвкой, сохранив спасительный припас для чужого выживания в метель, "
                "и спокойно возвращаешься к мерно потрескивающему каменному очагу."
            )
        else:
            text = (
                "Справедливая доля припасов уже взята из этого свёртка при прошлом осмотре. "
                "Оставшаяся часть лежит нетронутой ради того, кто придёт в пещеру следом за тобой на исходе последних сил. "
                "Нарушать собственное слово и отбирать чужой шанс на спасение не имеет никакого смысла. "
                "Ты аккуратно поправляешь узел на шкуре и спокойно отходишь от каменной ниши обратно к мягкому моховому ковру у согревающего огня."
            )
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Лечь отдохнуть", callback_data="furry_sleep")],
        ])

    elif data == "furry_take_remainder":
        if game.is_story_flag_set("furry_bundle_part_taken") and not game.is_story_flag_set("furry_bundle_taken"):
            game.inventory["Мех"] = game.inventory.get("Мех", 0) + 1
            game.set_story_flag("furry_bundle_taken")
            game.add_log("Получено: Мех ×1")
            text = (
                "Ты достаёшь из свёртка последний оставшийся кусок выделанного меха и надёжно убираешь его к остальным походным вещам (+1 Мех). "
                "Теперь схрон окончательно опустел, сохранив лишь берестяные шаблоны одежды. "
                "В суровых условиях выживания практическая необходимость взяла верх над благородством. "
                "Завязав пустую шкуру, ты возвращаешься к спасительному печному очагу передохнуть перед новой вылазкой."
            )
        else:
            text = (
                "Свёрток уже абсолютно пуст: весь найденный здесь мех был забран в рюкзак во время прошлого осмотра схрона. "
                "На шершавом базальте лежат лишь оставленные берестяные выкройки да пара костяных швейных игл. "
                "Тратить драгоценное время на повторные поиски бессмысленно — здесь больше не осталось ничего полезного. "
                "Пора вернуться к согревающему пещерному очагу или как следует устроиться на ночлег."
            )
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Лечь отдохнуть", callback_data="furry_sleep")],
        ])

    elif data == "furry_leave_gift":
        if not game.is_story_flag_set("left_something_in_bundle"):
            game.adjust_narrative_karma("compassion", 2)
            game.set_story_flag("left_something_in_bundle", True)
            gift_name = deduct_story_gift_item(game)
            gift_note = f" Внутрь свёртка аккуратно уложен припас: {gift_name}." if gift_name else " В свёрток бережно уложена щепоть сухого пещерного мха."
            text = (
                "Ты решаешь не трогать чужой мех без нужды, а вместо этого оставить полезный подарок взамен."
                f"{gift_note} Узел на кожаном свёртке снова крепко завязан и возвращён на холодный каменный уступ. "
                "Закон пещерного убежища строго соблюдён: путник не грабит чужое, а поддерживает жизнь в укрытии. "
                "От этого благородного поступка внутри разливается согревающее спокойствие."
            )
        else:
            text = (
                "Полезный припас уже оставлен в этом свёртке во время прошлого осмотра схрона. "
                "Твой припас надёжно укрыт под шкурой и дожидается того, кому он спасёт жизнь в морозную метель на краю гибели. "
                "Перегружать маленький схрон лишними вещами нет смысла — закон честной стоянки уже полностью соблюдён. "
                "Ты аккуратно поправляешь верёвку на свертке и спокойно отходишь от каменного уступа к согревающему очагу."
            )
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Лечь отдохнуть", callback_data="furry_sleep")],
        ])

    elif data == "furry_bundle_leave":
        text = (
            "Ты аккуратно затягиваешь бечёвку на свёртке и оставляешь его в покое на каменном уступе. "
            "В чужом убежище важно соблюдать порядок и не трогать найденные вещи без крайней нужды. "
            "Отойдя от прохладного угла пещеры, ты направляешься обратно к сухому очагу, где веет спасительным печным теплом."
        )
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Лечь отдохнуть", callback_data="furry_sleep")],
        ])

    elif data == "furry_warm":
        game.adjust_narrative_karma("pragmatism", 1)
        game.story_state = "furry_warmed"
        text = (
            "Ты подходишь к тлеющим уголькам. "
            "Подбрасываешь немного сухого мха. Пламя неохотно, но поднимается. "
            "Пещеру наполняет сухое, ровное тепло. "
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
            "Ты садишься ближе к теплу. Некоторое время просто смотришь на огонь "
            "и слушаешь, как он тихо потрескивает. "
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
                f"\n\n{pet_name} выбирается из-под одежды, топчется кругами на твоей груди "
                "и устраивается тёплым клубком. Он мурлычет совсем тихо, почти неслышно."
            )
        text = (
            "Ты ложишься на густой мох. Он пружинит под спиной. "
            f"В пещере тепло и почти тихо.{pet_text}\n\n"
            "Ты закрываешь глаза...\n\n"
            "Ты просыпаешься резко от тихого, настороженного звука! "
            "У выхода из пещеры мелькает чья-то спина. Тёмная фигура на мгновение "
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
            "Ты быстро проверяешь вещи. Всё на месте… почти. "
            "Пропала лишь мелкая часть припасов.\n\n"
            "Рядом со свёртком теперь лежит маленький кусок меха — будто в обмен. "
            "Становится ясно: кто-то заходил сюда во время твоего сна. Взял немного и оставил мех взамен."
        )
        game.story_state = "furry_after_loss"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚪 Выйти из пещеры", callback_data="furry_end")],
        ])

    elif data == "furry_end":
        game.set_story_flag("visited_furry_cave", True)
        game.set_story_flag("l6_ridge_unlocked", True)
        text = (
            "Ты ещё раз окидываешь взглядом просторное укрытие. "
            "Тепло очага, сухой мох и крепкие шкуры дали спасительную передышку. "
            "Поправив походный мешок, ты решительно шагаешь к выходу наружу. "
            "Снаружи тебя встречает ледяной перевал Верхнего хребта: "
            "ветер воет над обрывами, а из глубины скал доносится глухой, настораживающий скрежет. "
            "Чтобы пробиться к вершине, предстоит преодолеть главный рубеж горы."
        )
        game.story_state = None
        if hasattr(game, "reset_nav"):
            game.reset_nav()
        kb = get_main_kb(game)

    # ──────────────────────────────────────────────────────────────────────────
    # СЮЖЕТНЫЕ ОКНА ПОДЪЁМА (ИССЛЕДОВАНИЯ 1–10 ИЗ 40)
    # ──────────────────────────────────────────────────────────────────────────

    # ИССЛЕДОВАНИЕ 2: Панорама и структура пещеры (Интерактивный хаб)
    elif data == "l6_step2_hub":
        game.story_state = "l6_step2_hub"
        text = (
            "Сланцевый зев горы уходит в ледяную глубь. Плиты под ногами укрыты пылью и инеем. "
            "От входа пещера делится надвое. Слева зияет чернеющий провал: туда с грохотом сбрасывается "
            "гниль, мусор и ядовитые стоки из Яра Слаймов — там пути нет, лишь гибель в нечистотах. "
            "Но взгляд приковывает верхний подъём. Прямо над каменными ступенями в базальт глубоко врезан "
            "заветный знак: три горизонтальные полосы и вертикальная черта. А высоко над сводом сквозь тьму "
            "мерцает отблеск и тянет струёй чистого воздуха. Это единственный путь наверх, где кроется разгадка знака."
        )
        buttons = []
        if not game.is_story_flag_set("l6_step2_water_seen"):
            buttons.append([InlineKeyboardButton(text="🌊 Осмотреть сток воды", callback_data="l6_step2_water")])
        if not game.is_story_flag_set("l6_step2_people_seen"):
            buttons.append([InlineKeyboardButton(text="🏛️ Осмотреть следы людей", callback_data="l6_step2_people")])
        if not game.is_story_flag_set("l6_step2_chasm_seen"):
            buttons.append([InlineKeyboardButton(text="🔍 Осмотреть разлом", callback_data="l6_step2_chasm")])
        buttons.append([InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l6_step2_water":
        game.set_story_flag("l6_step2_water_seen", True)
        game.story_state = "l6_step2_water"
        text = (
            "Глубокие каменные желоба приводят к краю глубокого природного раскола. "
            "Вода с глухим шумом срывается в узкую расщелину, уходящую в ледяную бездну горы, откуда доносится далёкое эхо падающих струй. "
            "Поток уходит глубоко под землю, оставляя верхние каменные ярусы совершенно сухими. "
            "Внизу — лишь сырость и непроглядный мрак, туда пути нет. Дорога огибает провал и уходит круто ввысь, в серые скалы."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="l6_step2_hub")]
        ])

    elif data == "l6_step2_people":
        game.set_story_flag("l6_step2_people_seen", True)
        game.story_state = "l6_step2_people"
        text = (
            "Ты подходишь к ступеням и стираешь иней со стены. Под копотью открывается ответ: "
            "на базальте рядом со знаком выбиты путевые зарубки и стрела ввысь. Здесь никто не отступал назад — "
            "все насечки ведут к вершине хребта. Люди упрямо уходили наверх, спасаясь от ядовитой низины, "
            "и оставили эту дорогу как надёжный маршрут. Сомнений нет: спасение и разгадка лежат только через верхние гроты."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="l6_step2_hub")]
        ])

    elif data == "l6_step2_chasm":
        game.set_story_flag("l6_step2_chasm_seen", True)
        game.story_state = "l6_step2_chasm"
        text = (
            "В мёртвой морозной тишине взгляд устремляется ввысь сквозь пролом свода. Далеко наверху, "
            "в ледяной мгле, угадывается скальный рубеж. Но главное — прямо над входом в верхний коридор "
            "на плите высечен исполинский знак: три полосы и вертикальная черта со стрелой вверх. "
            "Древний след ведёт прямо к разгадке тайн этих мёртвых земель. Туда необходимо подняться любой ценой."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="l6_step2_hub")]
        ])

    # ИССЛЕДОВАНИЕ 4: Развилка и шатающийся уступ
    elif data == "l6_step4_main":
        game.story_state = "l6_step4_main"
        text = (
            "Крутой подъём выводит на обледенелый скальный карниз. Крайняя плита над пропастью надломилась: "
            "под подошвой камень глухо скрежещет и опасно вибрирует над чернеющей бездной при каждом осторожном шаге. "
            "Одно неверное движение — и обломок рухнет в пустоту. Но у самой отвесной стены, под каменным козырьком, "
            "взгляд натыкается на рукотворный схрон: под плоским куском сланца бережно уложен коробок спичек "
            "и пучок сухого пещерного мха. Кто-то давно оставил здесь спасительный запас среди смертоносной стужи."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Осмотреть нишу", callback_data="l6_step4_inspect")],
            [InlineKeyboardButton(text="🔨 Вбить клин под плиту", callback_data="l6_step4_wedge")],
            [InlineKeyboardButton(text="➡️ Не трогать и идти", callback_data="l6_ascent_continue")],
        ])

    elif data == "l6_step4_wedge":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step4_wedged", True)
        game.story_state = "l6_step4_wedge"
        text = (
            "Под руку попадается увесистый обломок базальта. Точный и сильный удар намертво вбивает каменный клин "
            "под основание шатающейся сланцевой плиты. Ступень намертво заклинивает, камень перестаёт вибрировать над чернеющим обрывом. "
            "На работу уходит часть дыхания и сил, но теперь на опасном повороте остаётся надёжный упор, "
            "по которому можно уверенно ступать дальше без риска сорваться в ледяную пропасть."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step4_inspect":
        game.story_state = "l6_step4_inspect"
        if not game.is_story_flag_set("l6_step4_loot_taken"):
            game.set_story_flag("l6_step4_loot_taken", True)
            game.inventory["Спички"] = game.inventory.get("Спички", 0) + 1
            game.inventory["Пещерный мох"] = game.inventory.get("Пещерный мох", 0) + 1
            game.add_log("Получено: Спички ×1, Пещерный мох ×1")
            text = (
                "Пальцы выгребают из расщелины коробок спичек и сухой пещерный мох, пряча находку к остальным вещам. "
                "Ниша под камнем остаётся совершенно пустой. В этих безлюдных ледяных скалах нет ни единой живой души, "
                "и некому упрекнуть тебя за расчётливый шаг. Но внутри шевелится глухое предчувствие: гора словно требует невидимого баланса. "
                "Взять чужое тепло и ничего не отдать взамен кажется опасным нарушением равновесия. Можно заглушить сомнения "
                "и двинуться дальше со всей добычей, либо положить свой припас ради внутреннего покоя."
            )
        else:
            text = (
                "Ты снова заглядываешь в скальную нишу под нависающей сланцевой плиткой. Схрон уже пуст: найденные ранее спички "
                "и сухой пещерный мох давно спрятаны к твоим вещам. На холодном дне расщелины осталась лишь мелкая базальтовая пыль "
                "да следы старого инея. Ты всё ещё можешь положить сюда что-то из своего пайка ради душевного спокойствия "
                "либо без задержек продолжить подъём по скользкому ледяному карнизу."
            )
        buttons = []
        if not game.is_story_flag_set("l6_step4_gift_left"):
            buttons.append([InlineKeyboardButton(text="🎁 Положить из инвентаря", callback_data="l6_step4_leave_gift")])
        buttons.append([InlineKeyboardButton(text="🎒 Забрать всё и уйти", callback_data="l6_step4_take_all")])
        buttons.append([InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l6_step4_leave_gift":
        game.story_state = "l6_step4_leave_gift"
        if not game.is_story_flag_set("l6_step4_gift_left"):
            item_given = deduct_story_gift_item(game)
            if item_given is None:
                text = (
                    "Ты открываешь походный мешок, чтобы оставить припас взамен найденных вещей, но пальцы натыкаются лишь на пустые свёртки. "
                    "В инвентаре нет ни куска сытного мяса, ни сухарей, ни сушёных ягод — отдать в схрон попросту нечего. "
                    "Гора не принимает пустых обещаний, а делиться тем, чего нет, невозможно. "
                    "Приходится либо забрать найденное на свой страх и риск, либо оставить всё на месте и продолжить путь."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎒 Забрать всё и уйти", callback_data="l6_step4_take_all")],
                    [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")],
                ])
            else:
                game.adjust_narrative_karma("compassion", 1)
                game.set_story_flag("l6_step4_gift_left", True)
                text = (
                    f"Коробок спичек отправляется в карман куртки, а взамен на сухой камень аккуратно ложится припас ({item_given}) из твоего рюкзака. "
                    "Расщелина снова надёжно прикрывается сланцевой плиткой от каменной осыпи. Неписаный закон стоянки соблюдён: путник берёт лишь необходимое, "
                    "оставляя следующему шанс выжить в морозном буране. От этого спокойного поступка внутри разливается тихое, согревающее тепло."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
                ])
        else:
            text = (
                "Ты уже оставил сытную часть своего походного пайка на сухой сланцевой плитке в этой каменной нише. "
                "Твой припас надёжно укрыт от осыпи и ледяного бурана, дожидаясь того, кто пойдёт следом сквозь морозные перевалы на пределе сил. "
                "Неписаный закон честной стоянки соблюдён сполна: задерживаться у пустого схрона больше не имеет смысла. "
                "Пора двигаться дальше по карнизу, пока ветер не усилился."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
            ])

    elif data == "l6_step4_take_all":
        game.set_story_flag("l6_step4_took_all", True)
        game.story_state = "l6_step4_take_all"
        text = (
            "Ты решаешь не задерживаться на опасном повороте скального тракта над пропастью. "
            "Забрав найденные в нише спички и сухой мох, ты плотно затягиваешь клапан походного мешка и оставляешь опустевший схрон позади. "
            "В суровых ледяных горах каждый путник в первую очередь обязан заботиться о собственной жизни, и осуждать за трезвый расчёт здесь попросту некому. "
            "Пронизывающий морозный ветер подгоняет в спину, требуя не терять концентрации и продолжать путь."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 7: Пролом над бездной и стадо
    elif data in ("l6_step7_main", "l6_ascent_step7"):
        game.story_state = "l6_step7_main"
        text = (
            "Скальный коридор распахивается широким боковым проломом. Сквозь разрыв в породе открывается вид на пройденный путь: "
            "далеко внизу серым морем простирается лес, за ним чернеет ручей и чаша Яра Слаймов под свинцовым пологом туч. "
            "Ледяной вихрь со свистом врывается в проход, обжигая лицо морозной крупой. Прямо на карнизе у обрыва стоят массивные горные бараны. "
            "Их свалявшаяся шерсть покрыта инеем. Они жуют серый лишайник и смотрят в упор. Они не боятся. Совсем."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👁️ Замереть перед вожаком", callback_data="l6_step7_observe")],
            [InlineKeyboardButton(text="✋ Протянуть пучок мха", callback_data="l6_step7_moss")],
            [InlineKeyboardButton(text="⚔️ Согнать стадо посохом", callback_data="l6_step7_scare")],
        ])

    elif data == "l6_step7_observe":
        game.adjust_narrative_karma("observation", 1)
        game.story_state = "l6_step7_observe"
        text = (
            "Зверь не отводит круглых немигающих глаз, продолжая неспешно жевать горький лишайник. В его поведении нет ни дикого ужаса "
            "перед человеком, ни агрессии. Вожак держится так, словно шаги двуногих на этой тропе — явление давно привычное. "
            "Выдержав долгую паузу, старый баран делает шаг назад к монолитной стене скалы, спокойно освобождая узкий проход мимо стада. "
            "Внимательное терпение окупается миром."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step7_moss":
        game.adjust_narrative_karma("compassion", 1)
        game.story_state = "l6_step7_moss"
        for m in ("Пещерный мох", "Сухой мох", "Мох"):
            if game.inventory.get(m, 0) > 0:
                game.inventory[m] -= 1
                if game.inventory[m] <= 0:
                    del game.inventory[m]
                break
        text = (
            "Баран медленно тянется к ладони, шумно втягивая ноздрями морозный воздух. Густой тёплый пар обдаёт онемевшие пальцы, "
            "и зверь аккуратно забирает сухие волокна мха мягкими губами. В этой промёрзшей пустоте живое тепло рядом кажется чудом. "
            "Напряжение в теле отступает, и дыхание выравнивается: спокойствие горного зверя придаёт уверенности продолжать трудный путь сквозь ледяные гроты."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step7_scare":
        game.adjust_narrative_karma("intervention", 1)
        game.story_state = "l6_step7_scare"
        text = (
            "Удар посоха о камень выбивает сноп искр и гулкое эхо. Старый вожак резко прядает ушами, глухо стучит копытом по базальту "
            "и отступает к краю обрыва. Остальные бараны молча жмутся к отвесной каменной стене, провожая пришельца настороженным взглядом. "
            "Проход очищен силой, но в воздухе повисает колючее напряжение: животные больше не доверяют и чутко следят за каждым твоим шагом вдоль нависшего карниза."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 8: Дыхание стужи и спутник
    elif data == "l6_step8_main":
        game.story_state = "l6_step8_main"
        has_pet = game.is_story_flag_set("has_pet")
        if has_pet:
            text = (
                "Подъём сужается, превращаясь в узкую ледяную теснину. Морозный сквозняк бьёт с такой яростной силой, что леденеет дыхание. "
                "Котёнок забился глубоко под одежду за пазухой, туда, где тепло, прижавшись к самой груди, и мелко дрожит всем тельцем. "
                "Ты греешь его онемевшими пальцами и собственным дыханием или сам греешься о его спасительный тёплый комок — уже не разобрать. "
                "Ясно одно: здесь нельзя медлить. Этот ледяной подъём нужно одолеть до конца."
            )
        else:
            text = (
                "Подъём сужается, превращаясь в продуваемую насквозь узкую ледяную теснину. Морозный шквал бьёт навстречу с такой силой, "
                "что стужа обжигает лёгкие до хрипоты, а пальцы в рукавицах теряют чувствительность. "
                "Одиночество в этой ледяной пасти давит на виски не меньше ветра. Мысль предельно ясна: здесь нельзя медлить. "
                "Этот ледяной подъём нужно либо одолеть до конца, либо повернуть назад в лагерь, чтобы основательно подготовиться."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 10: Вмёрзшая стоянка у очага
    elif data == "l6_step10_main":
        game.story_state = "l6_step10_main"
        text = (
            "Под нависшей гранитной плитой ледяной сквозняк затихает. Здесь обнаруживается старый привал: "
            "под наплывом прозрачного льда темнеет очаг, где обугленные поленья выложены аккуратным колодцем от ветра. "
            "В скальной нише стоит потемневший от времени костяной ларчик с припасами. "
            "Прямо над ним в породу глубоко врезан знакомый символ: три горизонтальные полосы, перечёркнутые чертой. "
            "Стоянка заброшена, но хранит следы долгого расчёта."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Осмотреть ларчик", callback_data="l6_step10_box")],
            [InlineKeyboardButton(text="🔍 Осмотреть за ларчиком", callback_data="l6_step10_behind")],
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")],
        ])

    elif data == "l6_step10_behind":
        game.set_story_flag("l6_step10_behind_seen", True)
        game.story_state = "l6_step10_behind"
        text = (
            "Взгляд скользит мимо костяной шкатулки и цепляется за узкую трещину за обледенелым очагом. "
            "Там, под слоем прозрачного наста, виден аккуратно выбитый в камне счётчик шагов и стрелка в обход ледопада. "
            "Тот, кто обустраивал этот рубеж, берёг не только припасы, но и оставил точный ориентир для следующего подъёма. "
            "Внимание к скрытым деталям стоянки даёт ясное понимание пути без лишнего риска сорваться на опасных уступах."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step10_box":
        game.story_state = "l6_step10_box"
        if not game.is_story_flag_set("l6_step10_loot_taken"):
            game.set_story_flag("l6_step10_loot_taken", True)
            game.inventory["Древесный уголь"] = game.inventory.get("Древесный уголь", 0) + 1
            game.inventory["Зелье здоровья"] = game.inventory.get("Зелье здоровья", 0) + 1
            game.add_log("Получено: Древесный уголь ×1, Зелье здоровья ×1")
            text = (
                "Крышка ларчика поддаётся с сухим треском. Внутри лежат брусок сухого древесного угля и склянка с зельем здоровья, "
                "аккуратно завёрнутая в промасленную ткань. Рядом в остывшей золе видны сломанная игла и обрывок кожаного ремня: "
                "тот, кто ночевал здесь, перевязывал глубокую рану перед тем, как шагнуть во тьму штолен. "
                "Холод сберёг вещи в полной неприкосновенности. Ты можешь забрать найденное себе или оставить часть своих припасов взамен."
            )
        else:
            text = (
                "Ты открываешь потемневшую крышку костяного ларчика. Внутри пусто: сухой древесный уголь и склянка с зельем здоровья "
                "уже давно перекочевали в твой инвентарь при первом осмотре стоянки. В углах шкатулки осталась лишь труха от истлевшей ткани да старая копоть. "
                "Больше ничего полезного заброшенный привал предложить не может — следы стоянки изучены, и задерживаться на ледяном сквозняке больше нет никакого смысла."
            )
        buttons = []
        if not game.is_story_flag_set("l6_step10_gift_left"):
            buttons.append([InlineKeyboardButton(text="🎁 Оставить припас взамен", callback_data="l6_step10_leave_gift")])
        buttons.append([InlineKeyboardButton(text="🎒 Забрать всё и уйти", callback_data="l6_step10_take_all")])
        buttons.append([InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l6_step10_leave_gift":
        game.story_state = "l6_step10_leave_gift"
        if not game.is_story_flag_set("l6_step10_gift_left"):
            item_given = deduct_story_gift_item(game)
            if item_given is None:
                text = (
                    "Ты распахиваешь клапаны походного мешка, надеясь оставить что-то в костяном ларчике взамен угля и снадобья, но запасы еды на исходе. "
                    "В рюкзаке не находится ни куска вяленого мяса, ни сухарей, ни других съедобных припасов. "
                    "Оставить тайник с пустыми руками или обмануть закон гор нельзя. "
                    "Приходится сделать выбор: забрать найденное без подарка или отступить назад к тропе, сохранив схрон нетронутым."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎒 Забрать всё и уйти", callback_data="l6_step10_take_all")],
                    [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")],
                ])
            else:
                game.adjust_narrative_karma("compassion", 1)
                game.set_story_flag("l6_step10_gift_left", True)
                text = (
                    f"Брусок древесного угля отправляется в карман куртки, а взамен на сухую ткань бережно ложится припас ({item_given}) из твоих походных запасов. "
                    "Крышка ларчика со щелчком плотно встаёт на место. Неписаный закон стоянки соблюдён: если кто-то выберется сюда на грани истощения, "
                    "этот тайник спасёт ему жизнь среди холода. От осознания правильного выбора внутри разливается спокойное, согревающее тепло человечности."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
                ])
        else:
            text = (
                "Ты уже оставил полезный припас в костяном ларчике на этой заброшенной стоянке. "
                "Твой дар аккуратно завёрнут в сухую ткань и надёжно укрыт от морозного сквозняка, дожидаясь замерзающего путника. "
                "Неписаный закон честной горной стоянки уже полностью соблюдён сполна, и перегружать маленькую шкатулку больше нет никакого смысла. "
                "Пора продолжать путь наверх сквозь ледяные штольни или вернуться в лагерь."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
            ])

    elif data == "l6_step10_take_all":
        game.set_story_flag("l6_step10_took_all", True)
        game.story_state = "l6_step10_take_all"
        text = (
            "Ты захлопываешь пустую костяную шкатулку и поднимаешься на ноги у заброшенного очага. "
            "Забрав сухой древесный уголь и зелье здоровья, ты ничего не оставляешь взамен: в морозных штольнях выживает тот, кто расчётливо копит ресурсы для собственного спасения. "
            "Прошлое этого привала остаётся погребённым под вековым льдом, а тебе предстоит двигаться дальше. "
            "Задержавшись на мгновение, чтобы перевести дыхание, ты продолжаешь трудный подъём."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ──────────────────────────────────────────────────────────────────────────
    # СЮЖЕТНЫЕ ОКНА ПОДЪЁМА (ИССЛЕДОВАНИЯ 11–20 ИЗ 40)
    # ──────────────────────────────────────────────────────────────────────────

    # ИССЛЕДОВАНИЕ 13: Расколотая арка и камнепад
    elif data == "l6_step13_main":
        game.story_state = "l6_step13_main"
        text = (
            "Подъём упирается в опасный перешеек: сверху над каменной тропой нависает расколотая ледяная арка. "
            "От вибрации ветра с неё то и дело срываются тяжёлые острые глыбы, разбиваясь о плиты над чернеющим обрывом. "
            "Проход завален ледяным крошевом, а трещины в своде ползут всё шире. "
            "Чтобы продвинуться выше, приходится выбирать: искать скрытый обход по скале, "
            "сбить нависшие глыбы посохом или быстро проскользнуть по самому краю без лишней задержки."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти скрытый обход", callback_data="l6_step13_observe")],
            [InlineKeyboardButton(text="🔨 Сбить опасные глыбы", callback_data="l6_step13_break")],
            [InlineKeyboardButton(text="🚶 Быстро пройти по кромке", callback_data="l6_step13_edge")],
        ])

    elif data == "l6_step13_observe":
        game.set_story_flag("l6_step13_choice", "observation")
        game.story_state = "l6_step13_observe"
        text = (
            "Ты опускаешься на колени и внимательно изучаешь слои породы в обход осыпи. "
            "Взгляд находит надёжный каменный карниз в монолитном базальте, скрытый за слоем инея. "
            "Неспешный расчёт оправдывает себя: удаётся безопасно обогнуть аварийную арку по крепкому монолиту, "
            "не потревожив ни единого висящего ледяного обломка. Хладнокровие экономит здоровье, а впереди снова открывается широкий подъём."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step13_break":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step13_choice", "intervention")
        game.story_state = "l6_step13_break"
        game.hp -= 10
        if game.hp <= 0:
            game.hp = 0
            game.story_state = None
            game.active_story_callback = None
            from keyboards import get_death_kb
            from game_state import get_death_text
            text = get_death_text(game, "Смертельный обвал ледяных глыб в гротах Мохнатой пещеры.", "Мохнатая пещера")
            return text, get_death_kb()
        text = (
            "Ты крепко перехватываешь посох и наносишь акцентированный удар в основание трещины. "
            "Ледяная арка с оглушительным грохотом рушится в пропасть, открывая чистый коридор. "
            "Один из осколков рикошетит от скалы и глубоко рассекает плечо сквозь рукав (❤️ -10 HP). "
            "Боль обжигает тело, но угроза полностью устранена: тропа расчищена, и никто из идущих следом больше не пострадает на этом гибельном перешейке."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step13_edge":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step13_choice", "pragmatism")
        game.story_state = "l6_step13_edge"
        text = (
            "Не тратя времени на расчистку чужой дороги и долгие поиски, ты вплотную прижимаешься к холодной скале и быстро проскальзываешь по узкому наружному краю плиты над бездной. "
            "За спиной с сухим треском осыпается ледяная крошка, но ноги уже выносят тело за опасную черту. "
            "Драгоценные силы и дыхание сбережены, а смертельный риск остался позади. Трезвый расчёт позволяет продвигаться к цели без лишних остановок."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 15: Заброшенный грузовой подъёмник
    elif data == "l6_step15_main":
        game.story_state = "l6_step15_main"
        text = (
            "Широкая терраса упирается в отвесный каменный уступ, разделяющий ярусы пещеры. "
            "В скалу намертво врублена мощная бревенчатая рама грузового подъёмника с массивным дубовым воротом. "
            "Сквозь морозную мглу над чернеющим обрывом застыла перекошенная грузовая клеть. "
            "Вся конструкция скована льдом и занесена инеем, но выглядит удивительно прочной. "
            "Металлическая ковка барабана не тронута ржавчиной, а в узлах ещё угадывается расчёт."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Подойти к механизму", callback_data="l6_step15_detail")]
        ])

    elif data == "l6_step15_detail":
        game.story_state = "l6_step15_detail"
        text = (
            "Вблизи механизм выглядит ещё внушительнее. "
            "Сбоку на раме раскачивается сорванный стальной трос: от порывов ветра он угрожающе бьётся о балки и может в любой момент сорвать клеть вниз, завалив проход. "
            "На барабане намертво заклинило тормозную колодку, оббитую широкой полосой толстой выделанной кожи. "
            "Сам же сложный узел шестерней цел, но требует решения: потратить силы на трос, снять кожу или просто изучить схему."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Изучить схему передач", callback_data="l6_step15_observe")],
            [InlineKeyboardButton(text="⛓️ Зафиксировать трос", callback_data="l6_step15_cable")],
            [InlineKeyboardButton(text="🎒 Срезать кожу с тормоза", callback_data="l6_step15_leather")],
        ])

    elif data == "l6_step15_observe":
        game.set_story_flag("l6_step15_choice", "observation")
        game.story_state = "l6_step15_observe"
        text = (
            "Взгляд внимательно скользит по зубьям шестерней, противовесам и схеме натяжения тросов. "
            "Становится ясно, как устроена система: противовес позволял поднимать огромный вес без лишних усилий. "
            "Понимание замысла строителей помогает отыскать скрытую боковую лестницу для рабочих, выбитую прямо в монолите скалы за барабаном. "
            "Это даёт безопасный путь наверх в обход обледенелых ступеней."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step15_cable":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step15_choice", "intervention")
        game.story_state = "l6_step15_cable"
        text = (
            "Тяжёлый трос вырывается из замёрзших пальцев, но ты упрямо наваливаешься всем весом и заводишь сорванное кольцо в массивный стальной стопор на раме. "
            "Замок с сухим щелчком намертво фиксирует груз над бездной. "
            "Конструкция спасена от неминуемого обрушения: клеть больше не сорвётся вниз, нижний проход останется чистым, "
            "а прочная дубовая рама послужит надёжным упором для каждого, кто рискнёт идти следом."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step15_leather":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step15_choice", "pragmatism")
        game.story_state = "l6_step15_leather"
        if not game.is_story_flag_set("l6_step15_loot_taken"):
            game.set_story_flag("l6_step15_loot_taken", True)
            game.inventory["Кожа"] = game.inventory.get("Кожа", 0) + 1
            game.add_log("Получено: Кожа ×1")
            text = (
                "Ты не тратишь время на починку мертвого механизма, а подходишь к тормозному ободу ворота. "
                "Острый нож аккуратно срезает широкую полосу толстой выделанной кожи, служившую обшивкой колодок (+1 Кожа). "
                "Материал отлично сохранился на морозе: прочный ремень сразу отправляется в рюкзак. "
                "В условиях выживания практическая польза важнее чужих механизмов — хорошая кожа всегда пойдёт на починку обуви и одежды."
            )
        else:
            text = (
                "Ты подходишь к тормозному ободу ворота. Широкая полоса толстой выделанной кожи уже срезана с колодок во время твоего первого осмотра грузового подъёмника. "
                "На промёрзшей дубовой раме остались лишь шляпки медных заклёпок и глубокие задиры от старого троса. "
                "Ничего полезного здесь больше не осталось — отличный кожаный ремень давно надёжно убран в твой рюкзак. "
                "Пора продолжать подъём по вырубленной в скале лестнице."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 17: Скользкий карниз и переходящая сумка
    elif data == "l6_step17_main":
        game.story_state = "l6_step17_main"
        text = (
            "Тропа выходит на продуваемый всеми ветрами открытый скальный карниз над пропастью. "
            "Здесь отчётливо видны следы давней трагедии: расколотый деревянный посох, сорванные камни "
            "и глубокая царапина на скользком уступе, уходящая прямо в бездну. Кто-то оступился на обледенелом повороте. "
            "В каменной расщелине у самой кромки обрыва застряла брошенная кожаная сумка путника. "
            "Этот опасный карниз не прощает ни малейшей спешки."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎒 Осмотреть сумку у обрыва", callback_data="l6_step17_bag")],
            [InlineKeyboardButton(text="👁️ Осмотреть место срыва", callback_data="l6_step17_observe")],
            [InlineKeyboardButton(text="🔨 Выложить каменный бортик", callback_data="l6_step17_wall")],
        ])

    elif data == "l6_step17_observe":
        game.set_story_flag("l6_step17_choice", "observation")
        game.story_state = "l6_step17_observe"
        text = (
            "Взгляд методично изучает царапины на камне и границы наледи. "
            "Причина беды очевидна: тонкий, невидимый глазом слой прозрачного льда на самом перегибе карниза. "
            "Но если присмотреться к рельефу уступов, становится видна безопасная дуга обхода ближе к монолитной стене, "
            "где порода шероховатая и сухая. Наблюдательность позволяет точно запомнить опасный участок и впредь уверенно проходить поворот без риска."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step17_wall":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step17_choice", "intervention")
        game.story_state = "l6_step17_wall"
        text = (
            "Ты находишь вдоль стены тяжёлые обломки базальта и один за другим перетаскиваешь их к открытому обрыву. "
            "Сильные удары клиньями намертво утрамбовывают камни в расщелины, формируя сплошной защитный бортик вдоль опасного закругления. "
            "Мышцы ноют от усталости, но гибельный поворот карниза больше не слеп: "
            "теперь край бездны надёжно отсечён каменной кладкой, которая спасёт от падения каждого, кто пойдёт этой тропой."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step17_bag":
        game.story_state = "l6_step17_bag"
        if not game.is_story_flag_set("l6_step17_loot_taken"):
            game.set_story_flag("l6_step17_loot_taken", True)
            game.inventory["Мех"] = game.inventory.get("Мех", 0) + 1
            game.inventory["Жареное мясо"] = game.inventory.get("Жареное мясо", 0) + 1
            game.add_log("Получено: Мех ×1, Жареное мясо ×1")
            text = (
                "Пальцы отгибают промёрзший кожаный клапан. Внутри сумки обнаруживаются кусок плотного меха и завёрнутое в бересту жареное мясо. "
                "Еда замёрзла в камень, но остаётся полностью пригодной в пищу. Больше в карманах ничего нет — лишь пустой закопчённый медный котелок на самом дне. "
                "Глядя в чернеющую под карнизом пропасть, откуда доносится глухой свист ветра, предстоит решить: "
                "забрать чужие припасы себе или сберечь закон честной стоянки и оставить что-то взамен."
            )
        else:
            text = (
                "Ты снова заглядываешь в расстёгнутую сумку у обрыва. Внутри абсолютно пусто: найденные ранее кусок меха и порция жареного мяса уже убраны в твой рюкзак. "
                "На дне расщелины остался лишь помятый медный котелок со следами давней копоти. Холодный ветер заунывно гудит над кромкой карниза, подгоняя двигаться дальше. "
                "Здесь больше нечего искать — пора возвращаться к штурму перевала или перевести дух в лагере."
            )
        buttons = []
        if not game.is_story_flag_set("l6_step17_gift_left"):
            buttons.append([InlineKeyboardButton(text="🎁 Оставить припас взамен", callback_data="l6_step17_leave_gift")])
        buttons.append([InlineKeyboardButton(text="🎒 Забрать всё и уйти", callback_data="l6_step17_take_all")])
        buttons.append([InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l6_step17_leave_gift":
        game.story_state = "l6_step17_leave_gift"
        if not game.is_story_flag_set("l6_step17_gift_left"):
            item_given = deduct_story_gift_item(game)
            if item_given is None:
                text = (
                    "Ты расстёгиваешь карманы рюкзака, чтобы положить припас взамен найденных в сумке вещей, но внутри пусто. "
                    "В твоих запасах нет ни куска сытного мяса, ни сушёных ягод, ни даже сухарей — схрону нечего предложить. "
                    "Пустой жест не согреет того, кто выйдет к этому обрыву сквозь метель. "
                    "Предстоит решить: забрать найденное без отдачи или оставить сумку нетронутой и продолжить подъём по тропе."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎒 Забрать всё и уйти", callback_data="l6_step17_take_all")],
                    [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")],
                ])
            else:
                game.adjust_narrative_karma("compassion", 1)
                game.set_story_flag("l6_step17_gift_left", True)
                text = (
                    f"Мех и порция мяса отправляются в глубину мешка, а на сухую бересту взамен ложится полезный припас ({item_given}) из твоего рюкзака. "
                    "Клапан сумки снова плотно застёгивается. Схрон готов поддержать любого, кто выберется на этот опасный карниз на пределе сил. "
                    "От соблюдения закона честной стоянки внутри разливается согревающее спокойствие: даже на краю пропасти удаётся сохранить человечность."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
                ])
        else:
            text = (
                "Ты уже оставил сытный припас в сумке на карнизе во время своего первого осмотра. Замёрзшая еда надёжно прикрыта кожаным клапаном от ледяного бурана "
                "и дожидается следующего путника. Неписаный закон честной горной стоянки уже соблюдён сполна, и задерживаться на пронизывающем сквозняке над чернеющей бездной больше нет смысла. "
                "Пора возвращаться к подъёму или спокойно восстановить силы в лагере."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
            ])

    elif data == "l6_step17_take_all":
        game.set_story_flag("l6_step17_took_all", True)
        game.story_state = "l6_step17_take_all"
        text = (
            "Ты застёгиваешь опустевшую сумку у обрыва и плотнее перехватываешь лямки рюкзака. "
            "Кусок меха и порция мяса надёжно спрятаны в вещах, а пустой медный котелок остаётся лежать в расщелине скалы. "
            "Суровый закон высоты прост: гора не прощает излишней сентиментальности тем, кто рискует жизнью над пропастью. "
            "Оставив опасный край карниза позади, ты делаешь глубокий вдох морозного воздуха и готовишься к следующему отрезку пути."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 20: Извилистые штольни и морозный морок
    elif data == "l6_step20_main":
        game.story_state = "l6_step20_main"
        text = (
            "По ощущениям и шагам сквозь эти бесконечные штольни можно было дважды подняться на вершину и спуститься обратно. "
            "Но петляющие ледяные проходы упрямо кружат в недрах горы, и под ногами лишь середина подъёма. "
            "Воздух здесь разреженный и обжигающе сухой. "
            "Сквозняк, прорываясь сквозь трещины свода, звучит ритмичным гулом: в шуме ветра чудятся шаги за спиной, звон пряжек и сдавленный шёпот. "
            "Ледяной морок испытывает рассудок на прочность."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👂 Вслушаться в гул ветра", callback_data="l6_step20_observe")],
            [InlineKeyboardButton(text="❤️ Согреть мысли о тепле", callback_data="l6_step20_compassion")],
            [InlineKeyboardButton(text="🚶 Не обращать внимания", callback_data="l6_step20_pragmatism")],
        ])

    elif data == "l6_step20_observe":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step20_choice", "observation")
        game.story_state = "l6_step20_observe"
        text = (
            "Ты останавливаешься и закрываешь глаза, отрешённо разбирая структуру звуков. "
            "Голоса и шаги распадаются на простую физику: свист воздуха в каменных трубах, дребезжание тонких ледяных пластин и глухой рокот обвала в нижних штольнях. "
            "Морок бессилен перед холодным анализом. Иллюзия рассеивается без следа, оставляя в ушах лишь ровный гул горного сквозняка и кристальную, спокойную ясность трезвого ума."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step20_compassion":
        game.adjust_narrative_karma("compassion", 1)
        game.set_story_flag("l6_step20_choice", "compassion")
        game.story_state = "l6_step20_compassion"
        if game.is_story_flag_set("has_pet"):
            text = (
                "Ты прижимаешь ладонь к груди под курткой, где клубится спасительное живое тепло. "
                "Котёнок тихо шевелится у самого сердца и сонно мурлычет, уткнувшись носом в шерстяную ткань. "
                "Это крошечное биение жизни мгновенно выдёргивает сознание из ледяной паутины. "
                "Забота о том, кто полностью зависит от тебя, выжигает навязчивый морок без остатка. "
                "Внутри разливается ясный покой: здесь нельзя падать духом, пока это маленькое тепло рядом."
            )
        else:
            text = (
                "Ты прижимаешь онемевшую ладонь к груди, вслушиваясь в собственное ровное, упрямое сердцебиение. "
                "Память о живом костровом тепле лагеря и спокойное осознание своего пути вытесняют навязчивые слуховые призраки. "
                "Человечность и тихое сострадание к тем, кто тоже мёрзнет в этих бесконечных горах, оказываются сильнее ледяного наваждения. "
                "Морок бессильно тает в клубах пара, а внутри разливается согревающая уверенность."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step20_pragmatism":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step20_choice", "pragmatism")
        game.story_state = "l6_step20_pragmatism"
        text = (
            "Ты стискиваешь челюсти и делаешь резкий шаг вперёд, наотрез отказываясь вслушиваться в бессмысленные звуки. "
            "Ноги упрямо отсчитывают метр за метром по гранитному полотну. "
            "Галлюцинации бессильны против непреклонной воли выжить: нет ни прошлого, ни духов, есть лишь крутой подъём и цель впереди. "
            "Наваждение резко спадает, разбившись о глухую решимость дойти до конца сквозь ледяную мглу."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ──────────────────────────────────────────────────────────────────────────
    # СЮЖЕТНЫЕ ОКНА ПОДЪЁМА (ИССЛЕДОВАНИЯ 21–25 ИЗ 40)
    # ──────────────────────────────────────────────────────────────────────────

    # ИССЛЕДОВАНИЕ 23: Шёпот из толщи монолита
    elif data == "l6_step23_main":
        game.story_state = "l6_step23_main"
        text = (
            "Узкая тропа жмётся к отвесной базальтовой стене, уходящей в ледяную тьму верхних гротов. "
            "Глухую тишину пещеры внезапно нарушает низкая, утробная вибрация, поднимающаяся откуда-то из самой толщи горы. "
            "Мелкие острые камешки под ногами начинают мелко подпрыгивать и звенеть о плиты. "
            "От чёрного монолита исходит ровный, ритмичный гул, похожий на медленное биение сердца. "
            "Словно древний камень пытается заговорить с идущим сквозь мороз человеком."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Прислушаться к скале", callback_data="l6_step23_detail")]
        ])

    elif data == "l6_step23_detail":
        game.story_state = "l6_step23_detail"
        text = (
            "Ты делаешь шаг ближе к холодной плите. Вблизи вибрация становится настолько плотной, что отдаётся тупой, ноющей болью в костях. "
            "Звук перестаёт быть просто эхом сквозняка: он складывается в глухой, раскатистый бас, исходящий из самой породы: "
            "«Куда ты идёшь, хрупкая плоть?.. Гора не прощает тепла...». "
            "Каменная толща под ладонью содрогается, сбрасывая тонкие пластинки натёчного льда. "
            "Это не обман слуха: недра пещеры испытывают решимость путника, требуя прямого ответа на свой зов."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✋ Прижать ладонь к скале", callback_data="l6_step23_intervene")],
            [InlineKeyboardButton(text="🧠 Собрать волю в кулак", callback_data="l6_step23_mind")],
            [InlineKeyboardButton(text="🚶 Упрямо идти мимо", callback_data="l6_step23_pragmatism")],
        ])

    elif data == "l6_step23_intervene":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step23_choice", "intervention")
        game.story_state = "l6_step23_intervene"
        text = (
            "Ты без колебаний опускаешь раскрытую ладонь на дрожащий базальт. "
            "Сквозь стужу камня передаётся мощный ритм, будто в недрах хребта медленно ворочается тяжёлое каменное тело. "
            "«Я иду наверх. Меня ждёт тепло», — твёрдо звучит твой голос под сводами. "
            "Вибрация на мгновение замирает, а затем сменяется протяжным, глубоким вздохом сквозняка в расщелинах. "
            "Дрожь в монолите постепенно утихает: гора услышала ответ и неохотно признала право дерзкого одиночки продолжить подъём."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step23_mind":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step23_choice", "observation")
        game.story_state = "l6_step23_mind"
        if game.is_story_flag_set("has_pet"):
            text = (
                "Ты прижимаешь руку к груди под курткой. Котёнок тихо шевелится у сердца, осторожно высовывает мокрый нос и чутко принюхивается к дрожащей щели. "
                "Вдруг малыш упрямо фыркает на призрачный голос из скалы и утыкается мордочкой в ладонь. "
                "Это простое, чистое тепло маленькой жизни выдёргивает сознание из морока. "
                "В ушах снова звучит лишь свист сквозняка и шорох осыпи. Спутник тихо урчит под тканью, возвращая телу ясную собранность и уверенность в каждом шаге."
            )
        else:
            text = (
                "Ты плотно зажмуриваешься и делаешь медленный вдох, сосредотачиваясь на ровном стуке своего сердца. "
                "Живое тепло тела и железная внутренняя дисциплина вытесняют давящий холод чужого шепота. "
                "Рассудок раскладывает морок на простую физику: свист воздуха в полостях, звон сосулек и усталость от высоты. "
                "Наваждение рассыпается, уступая место звенящей ясности ума. "
                "Перед тобой лишь безмолвная холодная стена и свободная тропа, зовущая дальше вверх."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step23_pragmatism":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step23_choice", "pragmatism")
        game.story_state = "l6_step23_pragmatism"
        text = (
            "Ты стискиваешь зубы и упрямо прибавляешь шаг, наотрез отказываясь вступать в диалог со скальным наваждением. "
            "Пусть гора бормочет что угодно — живой человек подчиняется лишь собственной воле и шагам. "
            "Ледяной сквозняк бьёт прямо в лицо, остужая лоб и окончательно выдувая призрачный шепот из головы. "
            "Дрожащий участок базальтовой стены быстро остаётся за спиной. "
            "Драгоценное дыхание сбережено, а трезвый практический расчёт позволяет продвигаться к цели без лишних сомнений и страха."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 25: Снежный баран в расщелине
    elif data == "l6_step25_main":
        game.story_state = "l6_step25_main"
        text = (
            "Подъём петляет между отвесными каменными уступами, засыпанными острым щебнем и ледяным крошевом. "
            "Внезапно из бокового разлома скалы доносится глухой металлический скрежет и частый, отчаянный стук копыт о породу. "
            "Звуки звучат панически и надрывно, резко разрывая тяжёлую тишину пещеры. "
            "Кто-то застрял в узком каменном тупике сразу за поворотом тропы, безуспешно пытаясь вырваться на свободу из холодной ловушки. "
            "Заиндевевший воздух дрожит от сдавленного дыхания невидимого пленника."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Подойти к расщелине", callback_data="l6_step25_detail")]
        ])

    elif data == "l6_step25_detail":
        game.story_state = "l6_step25_detail"
        text = (
            "Ты осторожно заглядываешь за поворот скального разлома. В глубине тесного кармана бьётся молодой снежный баран: его задняя нога намертво заклинена между двумя рухнувшими базальтовыми плитами. "
            "Каждая попытка вырваться лишь глубже сдирает шкуру о шершавый камень, а бока зверя тяжело вздымаются от леденящей боли и усталости. "
            "Заметив человека, баран замирает и в ужасе прижимает рога, обречённо ожидая верной гибели. Время не ждёт: нужно решить, как поступить с попавшим в беду зверем."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤝 Сдвинуть камень плечом", callback_data="l6_step25_intervene")],
            [InlineKeyboardButton(text="🌿 Успокоить и вынуть ногу", callback_data="l6_step25_compassion")],
            [InlineKeyboardButton(text="🚶 Не тратить силы и уйти", callback_data="l6_step25_pragmatism")],
        ])

    elif data == "l6_step25_intervene":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step25_choice", "intervention")
        game.story_state = "l6_step25_intervene"
        text = (
            "Ты скидываешь рукавицы, упираешься плечом в скол гранита и наваливаешься на плиту всем весом тела. "
            "Каменная крошка со свистом сыплется под сапогами, жилы на шее вздуваются, но тяжёлая глыба с глухим скрежетом подаётся в сторону на несколько вершков. "
            "Этого мига хватает: баран молниеносно выдёргивает уцелевшую ногу, вскакивает на ноги и замирает на уступе, бросив долгий, поражённый взгляд. "
            "Мощным упругим прыжком зверь взлетает на карниз и исчезает наверху, показав следами копыт чистую тропу."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step25_compassion":
        game.adjust_narrative_karma("compassion", 1)
        game.set_story_flag("l6_step25_choice", "compassion")
        game.story_state = "l6_step25_compassion"
        if game.is_story_flag_set("has_pet"):
            text = (
                "Ты достаёшь пучок сухого пещерного мха, а котёнок у груди начинает тихо и убаюкивающе мурлыкать. "
                "Этот мирный, домашний звук творит чудо: дикий зверь перестаёт биться и осторожно слизывает корм прямо с твоей ладони. "
                "Пока баран отвлечён, ты аккуратно просовываешь пальцы в расщелину, разворачиваешь сустав вдоль естественного паза и мягко освобождаешь ногу без единой трещины в кости. "
                "Зверь благодарно тычется тёплым носом в рукав и лёгким галопом уносится вверх, ведя за собой сквозь осыпь."
            )
        else:
            text = (
                "Ты достаёшь пучок сухого пещерного мха и негромким, спокойным голосом начинаешь заговаривать со зверем. "
                "Уловив отсутствие угрозы, баран тянется к корму и жадно пережёвывает сухие волокна. "
                "Воспользовавшись его доверием, ты опускаешься на колени, нащупываешь зажатое копыто и точным, бережным движением выводишь сустав сквозь широкую часть щели. "
                "Пленник спасён: облегчённо фыркнув, баран легко вспрыгивает на карниз и уверенно устремляется в верхний коридор, оставляя за собой безопасный след."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step25_pragmatism":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step25_choice", "pragmatism")
        game.story_state = "l6_step25_pragmatism"
        text = (
            "Ты отводишь глаза от дрожащего пленника и молча делаешь шаг назад. "
            "Законы дикой ледяной горы суровы: холод неизбежно отбирает слабых, а растрата последних сил перед штурмом верхних ярусов грозит собственной гибелью. "
            "За спиной затихает сдавленная возня копыт о базальт. "
            "Подъём продолжается в суровом безмолвии: трезвый прагматизм и экономия энергии помогают выжить там, где любая лишняя жалость оборачивается замерзанием на вечном леднике. "
            "Путь ведёт только вперёд."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 27: Каменный завал в штольне
    elif data == "l6_step27_main":
        game.story_state = "l6_step27_main"
        text = (
            "Галерея упирается в глухой завал: недавний обвал наглухо перекрыл проход тяжёлыми базальтовыми глыбами. "
            "На миг кажется, что тропа потеряна и подъём окончен. Но у основания завала, в полосе тени у пола, чернеет узкая щель, "
            "откуда ощутимо тянет свежим сквозняком. На высоте человеческого роста вдоль стены также виднеется неровный карниз, "
            "уходящий в обход завала. Преграда серьезна, но преодолима: нужно лишь выбрать верный способ двигаться дальше."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🕳️ Пролезть в щель у пола", callback_data="l6_step27_crawl")],
            [InlineKeyboardButton(text="🔨 Разобрать завал руками", callback_data="l6_step27_clear")],
            [InlineKeyboardButton(text="🧗 Обойти обвал по верху", callback_data="l6_step27_climb")],
        ])

    elif data == "l6_step27_crawl":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step27_choice", "pragmatism")
        game.story_state = "l6_step27_crawl"
        text = (
            "Ты сбрасываешь лямки рюкзака, толкаешь вещи перед собой и на четвереньках протискиваешься в тёмный лаз под завалом. "
            "Холодный сквозняк овевает лицо, а порода вокруг оказывается гладкой, веками промытой древней водой. "
            "Несколько упорных толчков локтями — и тело выскальзывает по ту сторону каменной пробки. "
            "Коридор свободен и уходит вверх. Трезвый расчёт и гибкость позволили преодолеть препятствие за пару минут без лишней траты сил."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step27_clear":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step27_choice", "intervention")
        game.story_state = "l6_step27_clear"
        game.hp -= 5
        if game.hp <= 0:
            game.hp = 0
            game.story_state = None
            game.active_story_callback = None
            from keyboards import get_death_kb
            from game_state import get_death_text
            text = get_death_text(game, "Обвал каменной осыпи в заваленной штольне Мохнатой пещеры.", "Мохнатая пещера")
            return text, get_death_kb()
        text = (
            "Ты упрямо упираешься плечом в край осевшей глыбы и наваливаешься всем весом. "
            "Каменные грани крошатся, сдирая кожу сквозь рукавицы. С протяжным скрежетом плиту удаётся расшатать, "
            "но следом опасно оседает верхний свод. Осколок базальта больно бьёт по предплечью (❤️ -5 HP). "
            "Приходится резко отпрянуть назад. Проход с трудом расширен, но гора ясно напоминает: грубая сила здесь требует немалой осторожности."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step27_climb":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step27_choice", "observation")
        game.story_state = "l6_step27_climb"
        text = (
            "Ты поднимаешь взгляд и внимательно изучаешь трещины свода. "
            "На высоте двух человеческих ростов замечается естественный карниз, уходящий вглубь скалы над обвалом. "
            "Цепляясь за шероховатые выступы базальта, удаётся аккуратно взобраться наверх и обогнуть завал по монолитной породе. "
            "Острые сколы требуют предельной концентрации, но наблюдательность экономит здоровье: путь на следующий ярус открыт."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 30: Лик каменного исполина и дыхание недр
    elif data == "l6_step30_main":
        game.story_state = "l6_step30_main"
        text = (
            "Высота трёх четвертей подъёма распахивается грандиозным залом. Свод теряется во мраке, "
            "а на дальней стене выступы базальта образуют грубые черты исполинского каменного лика. "
            "В воздухе снова разливается низкий, вибрирующий гул. Голос, звучащий прямо в камне, теперь глубок и отчётлив: "
            "«Ты дошёл сюда, огонёк... Но выдержишь ли пламя глубин?..». "
            "Из трещин у подножия лика поднимаются первые струи тёплого пара, несущие долгожданный запах земли."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗣️ Ответить каменному эху", callback_data="l6_step30_speak")],
            [InlineKeyboardButton(text="♨️ Отогреть руки у пара", callback_data="l6_step30_steam")],
            [InlineKeyboardButton(text="🎒 Проверить вещи и идти", callback_data="l6_step30_gear")],
        ])

    elif data == "l6_step30_speak":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_golem_greeted", True)
        game.set_story_flag("l6_step30_choice", "intervention")
        game.story_state = "l6_step30_speak"
        text = (
            "Ты делаешь твёрдый шаг вперёд и смотришь прямо в тёмные провалы каменного лика. "
            "«Я выдержу. Я иду за теплом», — ровно звучит твой голос под сводами зала. "
            "В ответ скалы отзываются низким, раскатистым рокотом, похожим на сдержанный смех. "
            "«Иди же... последний рубеж впереди», — гудит эхо, и дрожь плавно растворяется в породе. "
            "Воздух вокруг теплеет, словно пещера признала твоё право подняться к её сокровенному сердцу."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step30_steam":
        game.adjust_narrative_karma("compassion", 1)
        game.set_story_flag("l6_step30_choice", "compassion")
        game.story_state = "l6_step30_steam"
        if game.is_story_flag_set("has_pet"):
            text = (
                "Ты опускаешься на колени у парящей трещины и бережно достаёшь котёнка из-под куртки. "
                "Малыш щурит сонные глаза, подставляет мордочку восходящему мягкому пару и громко мурлычет на весь зал. "
                "Ты тихо гладишь его согретую спинку. Пережитый ледяной кошмар остался позади: тепло близко, и вы оба дойдёте до конца. "
                "Силы возвращаются волной чистой радости, смывая накопившуюся усталость бесконечного подъёма."
            )
        else:
            text = (
                "Ты опускаешься к парящей расселине и подставляешь онемевшие ладони струям глубинного пара. "
                "Живое тепло медленно возвращает чувствительность пальцам и разливается по замёрзшему телу. "
                "Воспоминания о костре и надежда на спасение оживают с новой силой. Ледяная мгла пещеры больше не властна над тобой: "
                "до порога Тёплой пещеры остаётся лишь один, последний решительный рывок сквозь верхние каменные галереи."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step30_gear":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step30_choice", "pragmatism")
        game.story_state = "l6_step30_gear"
        text = (
            "Не отвлекаясь на мистический шёпот скал, ты встаёшь у края подъёма и тщательно проверяешь снаряжение. "
            "Замёрзшие ремни перетянуты, пряжки рюкзака проверены, дыхание выровнено. Впереди — последний, самый крутой отрезок пути к теплу. "
            "Холодный прагматизм и трезвый расчёт не оставляют места суевериям. "
            "Ты делаешь уверенный шаг в тёплый восходящий поток, полностью готовый преодолеть финальный горный рубеж."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 33: Тектонический разлом и старая переправа
    elif data == "l6_step33_main":
        game.story_state = "l6_step33_main"
        text = (
            "Путь преграждает глубокий тектонический разлом, рассекающий штольню от стены до стены. "
            "Внизу, в непроглядной черноте, глухо шумит невидимый ледяной поток. Единственная переправа — две старые бревенчатые балки, "
            "потемневшие от сырости и скреплённые коваными скобами. В монолитную скалу рядом намертво вбит ржавый кованый крюк с остатками истлевшей пеньковой верёвки. "
            "Морозное дыхание бездны требует взвешенного решения."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🪵 Перейти по бревну шагом", callback_data="l6_step33_cross")],
            [InlineKeyboardButton(text="🔨 Укрепить опору балки", callback_data="l6_step33_brace")],
            [InlineKeyboardButton(text="🔍 Осмотреть нишу у крюка", callback_data="l6_step33_search")],
        ])

    elif data == "l6_step33_cross":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step33_choice", "pragmatism")
        game.story_state = "l6_step33_cross"
        text = (
            "Ты опускаешься на корточки, проверяешь ногой скользкое дерево и, поймав равновесие, плавно переходишь над бездной. "
            "Балка едва слышно потрескивает под весом тела, но держит надёжно. За спиной остаётся чёрная пропасть, а впереди открывается продолжение галереи. "
            "Ни секунды не потеряно на лишние хлопоты: трезвая уверенность и точный расчёт шагов позволяют двигаться дальше без риска."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step33_brace":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step33_choice", "intervention")
        game.story_state = "l6_step33_brace"
        text = (
            "Ты не спешишь сразу ступать на шаткие брёвна. Отыскав среди свежей осыпи плоские базальтовые клинья, "
            "ты методично забиваешь их тяжёлым камнем под основание просевшей опоры переправы. "
            "Стальные скобы натягиваются со звоном, балка перестаёт вибрировать и встаёт в распор намертво. "
            "Теперь мостик над пропастью безопасен не только для тебя, но и для любого, кто пойдёт следом. Перейдя на ту сторону, ты уверенно продолжаешь подъём."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step33_search":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step33_choice", "observation")
        game.story_state = "l6_step33_search"
        if not game.is_story_flag_set("l6_step33_loot_taken"):
            game.set_story_flag("l6_step33_loot_taken", True)
            game.inventory["Спички"] = game.inventory.get("Спички", 0) + 1
            game.add_log("Получено: Спички ×1")
            text = (
                "Ты подходишь к стене и внимательно осматриваешь трещину вокруг старого страховочного крюка. "
                "Тщательный поиск приносит плоды: в скрытом углублении за скальным выступом обнаруживается завернутый в грубую холстину нетронутый коробок спичек (+1 Спички). "
                "Находка сразу отправляется в рюкзак: в горах огонь решает всё. Аккуратно перешагнув разлом по настилу, ты с полезной добычей продолжаешь восхождение."
            )
        else:
            text = (
                "Ты снова внимательно осматриваешь трещину вокруг старого страховочного крюка. "
                "В каменной нише пусто: нетронутый коробок спичек уже был извлечён и надёжно убран в твой походный рюкзак при первом осмотре. "
                "В глубокой расселине осталась лишь базальтовая крошка да сухая ржавчина от старого крепежа. "
                "Разлом благополучно преодолён по настилу, и задерживаться над бездной больше незачем — путь наверх открыт."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 36: Пик ледяного морока
    elif data == "l6_step36_main":
        game.story_state = "l6_step36_main"
        text = (
            "Мороз достигает жестокого предела: воздух кажется густым и белесым от ледяной пыли. "
            "На ресницах и воротнике намёрзла толстая корка, каждый вдох отдаётся покалыванием в лёгких. "
            "Морозный морок сгущается вокруг: в переливах инея мерещатся силуэты ушедших людей, а в шуме сквозняка слышится потрескивание далёкого костра. "
            "Чувства притупляются от усталости, но впереди — последний порог перед теплом."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Рассеять морок дыханием", callback_data="l6_step36_focus")],
            [InlineKeyboardButton(text="🔥 Проверить источник звука", callback_data="l6_step36_investigate")],
            [InlineKeyboardButton(text="🐾 Прислушаться к чутью", callback_data="l6_step36_instinct")],
        ])

    elif data == "l6_step36_focus":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step36_choice", "pragmatism")
        game.story_state = "l6_step36_focus"
        text = (
            "Ты закрываешь глаза и заставляешь себя дышать ровно и глубоко, отгоняя наваждения железным усилием воли. "
            "Никаких призрачных костров здесь нет — лишь безмолвный базальт, холод и мерный скрип собственных шагов. Морозное наваждение рассеивается без следа. "
            "Реальность возвращается кристально ясной: впереди виден надёжный пологий подъём, уходящий в темноту. "
            "Холодный прагматизм и выдержка позволяют сохранить рассудок и уверенно идти дальше."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step36_investigate":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step36_choice", "intervention")
        game.story_state = "l6_step36_investigate"
        if not game.is_story_flag_set("l6_step36_loot_taken"):
            game.set_story_flag("l6_step36_loot_taken", True)
            game.inventory["Пещерный мох"] = game.inventory.get("Пещерный мох", 0) + 1
            game.add_log("Получено: Пещерный мох ×1")
            text = (
                "Ты упрямо направляешься к источнику потрескивающего звука в боковом ответвлении. "
                "Раздвинув звенящие ледяные сосульки, ты обнаруживаешь не костёр, а удивительное природное чудо: "
                "сквозь промороженную корку скалы пробивается живой зеленоватый нарост (+1 Пещерный мох). "
                "Нежное растение источает едва заметное тепло. Заботливо убрав мох в мешок, ты возвращаешься на основной путь с ценной находкой."
            )
        else:
            text = (
                "Ты повторно подходишь к ледяной расщелине в боковом ответвлении штольни. "
                "Редкий живой нарост пещерного мха уже был аккуратно собран и убран в твой походный мешок при первом исследовании. "
                "На промёрзшей базальтовой породе остался лишь тонкий влажный след, защищённый от стужи. "
                "Больше здесь ничего нет — ценный природный припас добыт, и пора уверенно продолжать восхождение по основному каменному тракту."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step36_instinct":
        game.adjust_narrative_karma("compassion", 1)
        game.set_story_flag("l6_step36_choice", "compassion")
        game.story_state = "l6_step36_instinct"
        if game.is_story_flag_set("has_pet"):
            text = (
                "Котёнок внутри тёплой куртки внезапно оживляется, тычется мокрым носом в шею и настойчиво скребёт лапкой, "
                "указывая мордочкой строго в правый рукав пещеры. Его чистое доверие и живое биение сердца мгновенно развеивают давящий ледяной туман в голове. "
                "Доверившись верному чутью маленького спутника, ты уверенно шагаешь вперёд: "
                "обманчивая пелена морока исчезает, открывая свободный и ясный проход наверх."
            )
        else:
            text = (
                "Ты прижимаешь онемевшие ладони к груди и делаешь размеренный глубокий вдох, прислушиваясь к упрямому биению собственного сердца. "
                "Живое человеческое тепло побеждает обманчивую тишину ледяного склепа. Доверившись чистому инстинкту выживания, "
                "ты делаешь решительный шаг вперёд сквозь белесую морозную пелену. "
                "Наваждение рассеивается, а коридор распахивается широким и безопасным выходом на следующий ярус."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 38: Дыхание горы (геотермальное тепло)
    elif data == "l6_step38_main":
        game.story_state = "l6_step38_main"
        text = (
            "Воздух в штольне разительно меняется: ледяное дыхание высоты отступает, уступая место густому, влажному теплу. "
            "Ледяная корка на базальтовых стенах сменяется бисером крупной росы. Из глубоких расселин в полу с тихим шипением поднимаются устойчивые струи геотермального пара. "
            "Земля под ногами мерно и глубоко содрогается, словно каменный исполин выдыхает жар из самого сердца горы. До спасительного убежища остаются считанные десятки метров."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✋ Коснуться тёплой скалы", callback_data="l6_step38_touch")],
            [InlineKeyboardButton(text="👁️ Изучить русло пара", callback_data="l6_step38_observe")],
            [InlineKeyboardButton(text="🚶 Ускорить шаг к теплу", callback_data="l6_step38_rush")],
        ])

    elif data == "l6_step38_touch":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step38_choice", "intervention")
        game.story_state = "l6_step38_touch"
        text = (
            "Ты опускаешь раскрытую ладонь на влажный базальт. Скала больше не обжигает пальцы холодом — камень на ощупь тёплый, как печная заслонка. "
            "Под ладонью отчётливо чувствуется мощная пульсация подземного очага. «Спасибо за дорогу», — тихо слетает с твоих губ во тьму. "
            "Вибрация под ногами на миг замирает и отзывается глухим, дружелюбным рокотом. Гора окончательно признала твоё упорство и распахнула свои недра."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step38_observe":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step38_choice", "observation")
        game.story_state = "l6_step38_observe"
        text = (
            "Ты внимательно изучаешь направление восходящих паровых струй и полосы осевшей влаги на своде. "
            "Пар устойчиво утягивается в узкий извилистый карман впереди, унося за собой сырость и сквозняк. "
            "Проследив естественную тягу воздуха, ты безошибочно находишь кратчайший и самый сухой проход сквозь нагромождение валунов. "
            "Опыт следопыта и хладнокровное наблюдение безошибочно выводят тебя прямо к порогу убежища."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step38_rush":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step38_choice", "pragmatism")
        game.story_state = "l6_step38_rush"
        text = (
            "Ты не тратишь драгоценные минуты на изучение пара и ритуалы со скалами. Вдохнув целебный тёплый воздух полной грудью, "
            "ты решительно ускоряешь шаг, плотнее перехватывая лямки рюкзака. С каждым метром идти становится легче: "
            "скованность в суставах проходит, а тепло наполняет озябшие мышцы новой энергией. "
            "Чёткий прагматизм и воля ведут вперёд: финишная прямая бесконечного подъёма уже перед глазами."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 39: Порог Мохнатой пещеры (Преддверие убежища)
    elif data == "l6_step39_main":
        game.story_state = "l6_step39_main"
        text = (
            "Последний изгиб штольни выводит к невысокому каменному лазу. Здесь мороз окончательно сдаётся: в лицо веет настоящим, сухим печным теплом. "
            "До слуха доносится едва различимый шелест и треск старых углей, а в воздухе отчётливо пахнет дымом, сухим берестяным дегтем и прелым лесным мхом. "
            "Пол усеян мягким ковром из густого рыжего мха, на котором приятно пружинит подошва. Перед тобой — самый порог Тёплой пещеры."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌿 Собрать мягкий мох", callback_data="l6_step39_moss")],
            [InlineKeyboardButton(text="🧭 Оглянуться на путь назад", callback_data="l6_step39_lookback")],
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")],
        ])

    elif data == "l6_step39_moss":
        game.adjust_narrative_karma("compassion", 1)
        game.set_story_flag("l6_step39_choice", "compassion")
        game.story_state = "l6_step39_moss"
        if not game.is_story_flag_set("l6_step39_loot_taken"):
            game.set_story_flag("l6_step39_loot_taken", True)
            game.inventory["Пещерный мох"] = game.inventory.get("Пещерный мох", 0) + 1
            game.add_log("Получено: Пещерный мох ×1")
            if game.is_story_flag_set("has_pet"):
                text = (
                    "Ты опускаешься на колени на мягкий тёплый мох и аккуратно выпускаешь котёнка на подстилку. "
                    "Малыш с восторгом трётся щекой о рыжие стебли, мурлычет на всю пещеру и катается по тёплой зелени, опьянённый спасительным уютом. "
                    "Ты осторожно срываешь пучок сухого целебного сбора про запас (+1 Пещерный мох). "
                    "Сердце переполняет глубокое сострадание и благодарность за то, что вы оба выжили в этом ледяном аду."
                )
            else:
                text = (
                    "Ты опускаешься на колени на мягкий тёплый моховой ковёр и касаешься его ладонями. "
                    "Упругая зелень пружинит под пальцами, отдавая накопленное нутряное тепло. Не веря своему спасению, "
                    "ты осторожно срываешь пышный пучок сухого целебного сбора себе в запас (+1 Пещерный мох). "
                    "Чувство глубокого покоя и благодарности недрам разливается внутри: бесконечная битва со смертельным морозом высоты наконец-то завершена."
                )
        else:
            if game.is_story_flag_set("has_pet"):
                text = (
                    "Ты снова опускаешься на мягкий моховой ковёр у порога пещеры. "
                    "Целебный сбор сухого мха про запас уже убран в твой рюкзак, но котёнка просто невозможно оторвать от спасительного уюта. "
                    "Маленький рыжий котёнок с неизменным восторгом катается по зелени и громко мурлычет, подставляя тёплое брюшко мягким стеблям. "
                    "Убежище уже перед вами: до спасительного порога остаётся лишь шаг, и холодная тьма пройденного пути больше не имеет над вами власти."
                )
            else:
                text = (
                    "Ты снова касаешься ладонями густого мохового ковра у входа в пещеру. "
                    "Запас целебного мха уже надёжно уложен в твой походный мешок. Тёплая пружинящая зелень отдаёт накопленный жар недр, окончательно согревая онемевшие пальцы. "
                    "До спасительного очага остаётся лишь один шаг сквозь каменный лаз. "
                    "Долгая и опасная битва с ледяной горой осталась позади — надёжный кров ждёт прямо впереди."
                )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step39_lookback":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step39_choice", "observation")
        game.story_state = "l6_step39_lookback"
        text = (
            "Ты останавливаешься у самого входа и на миг оборачиваешься назад. "
            "Далеко внизу, сквозь ледяную мглу пройденных гротов, мерцают синеватые тени преодолённых обвалов, карнизов над бездной и морозных лабиринтов. "
            "Сорок тяжелейших шагов борьбы за каждый вздох остались позади. Острый взгляд следопыта вбирает эту картину победы разума над стихией. "
            "Ты готов переступить порог и навсегда обрести надёжный кров."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_ascent_step40":
        game.story_state = "furry_cave_start"
        text = (
            "Ты протискиваешься сквозь низкий свод и выпрямляешься во весь рост. "
            "Ледяной сквозняк намертво стихает за каменным уступом. Перед тобой просторный, сухой грот: "
            "по стенам развешаны плотные звериные шкуры, в каменном очаге тлеют жаркие угли, пахнет дымом и нагретой смолой, "
            "а под ногами стелется толстый ковёр из мягкого мха. Здесь безопасно, сухо и по-настоящему тепло.\n\n"
            "Открыта постоянная база: Тёплая пещера!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Осмотреть пещеру", callback_data="furry_examine")],
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Сразу лечь отдохнуть", callback_data="furry_sleep")],
            [InlineKeyboardButton(text="🚶 Уйти", callback_data="furry_leave")],
        ])

    # ──────────────────────────────────────────────────────────────────────────
    # ВТОРАЯ ФАЗА L6: ВЕРХНИЙ ПЕРЕВАЛ И КАМЕННЫЙ ИСПОЛИН (ПРЕГРАДА)
    # ──────────────────────────────────────────────────────────────────────────

    # ШАГ 1 НА ПЕРЕВАЛЕ: Выход на открытый продуваемый гребень
    elif data == "l6_ridge_step1":
        game.story_state = "l6_ridge_step1"
        game.set_story_flag("l6_ridge_step1_seen", True)
        text = (
            "Ты оставляешь тепло пещеры позади и выходишь на открытый продуваемый гребень. "
            "Ветер здесь не свистит, а тяжело ревёт, швыряя в лицо сухую ледяную крупу. "
            "Воздух обжигает лёгкие при каждом вдохе, а скалы покрыты плотным сизым настом. "
            "Впереди среди серого тумана проступают колоссальные базальтовые зубья. "
            "Идти приходится против урагана, наваливаясь всем телом на посох. "
            "Впереди над бездной высится узкий скальный проход, ведущий к самому верхнему рубежу хребта."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧗 Лезть сквозь буран", callback_data="l6_ridge_step2")],
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")],
        ])

    # ШАГ 2 НА ПЕРЕВАЛЕ: Следы исполина на базальте
    elif data == "l6_ridge_step2":
        game.story_state = "l6_ridge_step2"
        game.set_story_flag("l6_ridge_step2_seen", True)
        text = (
            "Под ногами среди битого льда обнажаются гладкие каменные плиты. "
            "На их поверхности отчётливо видны глубокие вмятины: пятипалые следы циклопической ширины, "
            "вдавленные в монолитный базальт, словно в мягкую глину. Рядом лежит расколотый пополам вековой валун со следами мощного удара. "
            "Это не игра замерзающего воображения и не морозный морок, мучивший тебя в гротах. "
            "По этой тропе действительно шагало нечто нечеловеческое, чья масса и сила превосходят скалы."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Изучить раскол", callback_data="l6_ridge_step3")],
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")],
        ])

    # ШАГ 3 НА ПЕРЕВАЛЕ: Дрожь горы и Голос
    elif data == "l6_ridge_step3":
        game.story_state = "l6_ridge_step3"
        game.set_story_flag("l6_ridge_step3_seen", True)
        text = (
            "Внезапно под ногами пробегает мелкая дрожь. Скальный монолит отзывается глухим, низким гулом, "
            "словно внутри хребта ворочается древний механизм. Тук. Пауза. Тук-тук. Звук повторяется, вибрируя в костях и зубах. "
            "Это тот самый ритм, что мерещился в горячечном бреду среди ледяных гротов, когда холод туманил рассудок. "
            "Теперь сомнений нет: гора говорит с тобой наяву. "
            "Эхо скрежещет в вышине, складываясь в тяжелые, как жернова, раскаты немого предупреждения."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Шагнуть к вратам", callback_data="l6_ridge_step4")],
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")],
        ])

    # ШАГ 4 НА ПЕРЕВАЛЕ: Черная расщелина и Пробуждение Каменного Гиганта
    elif data == "l6_ridge_step4":
        game.story_state = "l6_ridge_step4"
        game.set_story_flag("l6_ridge_step4_seen", True)
        text = (
            "Тропа упирается в Черную расщелину — единственный пролом, сквозь который можно подняться на вершину. "
            "Но проход наглухо перекрыт серой базальтовой скалой. Внезапно монолит оживает. "
            "Ледяная корка с треском осыпается вниз, открывая широкие каменные плечи и массивную голову. "
            "Древний Каменный Исполин медленно поднимается во весь рост, заслоняя свинцовое небо. "
            "Его ледяные глаза вспыхивают тусклым светом, а голос звучит как обвал: «Ты дошёл, путник. Зачем ты здесь?»"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Принять бой", callback_data="l6_giant_fight")],
            [InlineKeyboardButton(text="🎁 Поклониться и дать дар", callback_data="l6_giant_gift")],
            [InlineKeyboardButton(text="🧗 Обойти по кромке бездны", callback_data="l6_giant_edge")],
        ])

    # ВЫБОР 1: БИТВА С КАМЕННЫМ ИСПОЛИНОМ (Сила и ярость)
    elif data == "l6_giant_fight":
        game.story_state = "l6_giant_fight"
        game.adjust_narrative_karma("intervention", 2)
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_giant_choice", "fight")
        game.hp -= 18
        if game.hp <= 0:
            game.hp = 0
            game.story_state = None
            game.active_story_callback = None
            from keyboards import get_death_kb
            from game_state import get_death_text
            text = get_death_text(game, "Смертельный удар базальтовой десницы Каменного Исполина.", "Мохнатая пещера")
            return text, get_death_kb()

        text = (
            "Ты перехватываешь оружие обеими руками и бросаешься вперёд. Исполин со скрежетом обрушивает каменную десницу, "
            "дробя плиты у твоих ног. Волна ледяных осколков сечёт тело сквозь мех, сбивая дыхание (❤️ -18 HP). "
            "Превозмогая резкую боль, ты уходишь перекатом под замах и наносишь сокрушительный удар в ледяную трещину на его колене. "
            "Базальт раскалывается с оглушительным звоном. "
            "Исполин тяжело оседает назад, признавая твою яростную человеческую волю к жизни."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Пройти сквозь пролом", callback_data="l6_giant_victory")],
        ])

    # ВЫБОР 2: ИСПЫТАНИЕ ДУХА И ДАР (Сострадание и жертва)
    elif data == "l6_giant_gift":
        game.story_state = "l6_giant_gift"
        game.adjust_narrative_karma("compassion", 2)
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_giant_choice", "gift")
        item_given = deduct_story_gift_item(game)
        if item_given:
            text = (
                f"Ты опускаешь оружие и делаешь шаг вперёд с открытыми ладонями. Достав из рюкзака честный припас ({item_given}), "
                "ты бережно укладываешь его на обледенелый камень к подножию колосса. "
                "Исполин медленно склоняет массивную голову, вглядываясь в твою душу. Ветер стихает. "
                "Гора узнаёт того, кто не грабил без разбора, а делился скудным теплом с живым миром. "
                "Каменные длани со скрежетом размыкаются в стороны, безмолвно освобождая путь наверх для истинного хранителя."
            )
        else:
            game.hp -= 10
            if game.hp <= 0:
                game.hp = 0
                game.story_state = None
                game.active_story_callback = None
                from keyboards import get_death_kb
                from game_state import get_death_text
                text = get_death_text(game, "Ледяное дыхание стража хребта угасило последние жизненные силы.", "Мохнатая пещера")
                return text, get_death_kb()
            text = (
                "Ты опускаешь руки и склоняешь голову перед древним стражем. В мешке нет еды, но в сердце нет страха. "
                "Исполин выдыхает ледяное облако прямо в лицо, испытывая твою стойкость. "
                "Мороз пробирает до костей, вытягивая последние жизненные силы (❤️ -10 HP), но ты не отступаешь ни на шаг. "
                "Увидев несокрушимое смирение и волю, колосс медленно отводит каменную десницу от прохода. "
                "Гора принимает эту жертву: ты заслужил право подняться к вершине чистым и испытанным."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Пройти сквозь пролом", callback_data="l6_giant_victory")],
        ])

    # ВЫБОР 3: ОБХОД ПО КРОМКЕ БЕЗДНЫ (Ловкость и предел выносливости)
    elif data == "l6_giant_edge":
        game.story_state = "l6_giant_edge"
        game.adjust_narrative_karma("observation", 2)
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_giant_choice", "edge")
        game.hp -= 15
        if game.hp <= 0:
            game.hp = 0
            game.story_state = None
            game.active_story_callback = None
            from keyboards import get_death_kb
            from game_state import get_death_text
            text = get_death_text(game, "Падение с ледяного карниза в бездну Верхнего перевала.", "Мохнатая пещера")
            return text, get_death_kb()

        text = (
            "Ты решаешь не тревожить древнее создание и устремляешься к наружному карнизу над пропастью. "
            "Карниз крошится под ногами, подошвы скользят по насту. Яростный порыв ветра срывает тебя с уступа — "
            "пальцы впиваются в острый скол базальта, сдирая кожу сквозь рукавицы (❤️ -15 HP). "
            "Мускулы горят от напряжения, бездна дышит могильным холодом в спину. "
            "Собрав последние силы, ты подтягиваешься и переваливаешься за спину дремлющего великана. Расчёт и риск оправдали себя."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Выйти на гребень", callback_data="l6_giant_victory")],
        ])

    # ФИНАЛ ПРЕГРАДЫ: Триумф и разблокировка Святилища
    elif data == "l6_giant_victory":
        game.set_story_flag("l6_giant_defeated", True)
        game.set_story_flag("l6_completed", True)
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Святилище" not in unlocked and "святилище" not in [x.lower() for x in unlocked]:
            unlocked.append("Святилище")
            game.unlocked_locations = unlocked
            game.add_log("Великая преграда пала! Открыт путь на вершину: Святилище!")

        text = (
            "Черная расщелина остаётся позади. Ты выходишь на широкий, залитый бледным светом скальный гребень, "
            "где морозный туман наконец расступается. Прямо перед тобой к небесам уходит величественный пик Святилища. "
            "Великая преграда пала: гора больше не держит тебя во льдах, признав твоё право на развязку. "
            "Ты делаешь глубокий вдох чистейшего горного воздуха, чувствуя, как внутри разливается твёрдость духа.\n\n"
            "Путь на вершину открыт: Святилище ждёт!"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏛️ Взойти в Святилище", callback_data="location_enter_7")],
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")],
        ])

    elif data == "l6_ascent_continue":
        game.story_state = None
        game.active_story_callback = None
        if hasattr(game, "reset_nav"):
            game.reset_nav()
        return game.get_ui(), get_main_kb(game)

    if kb == get_main_kb(game) or data in ("furry_end", "furry_leave", "back", "l6_ascent_continue") or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        game.active_story_callback = data

    return text, kb
