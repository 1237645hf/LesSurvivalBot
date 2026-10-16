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
        game.story_state = None
        game.active_story_callback = None
        return game.get_ui(), get_main_kb(game)

    if data in ("furry_cave_start", "l6_ascent_step40"):
        unlock_warm_cave_shelter(game)
        if "warm_cave_reached_day" not in game.story_flags:
            game.story_flags["warm_cave_reached_day"] = getattr(game, "day", 1)
        game.story_state = "furry_cave_start"
        text = (
            "Ты протискиваешься сквозь низкий свод и выпрямляешься во весь рост. "
            "Ледяной сквозняк намертво стихает за каменным уступом, а вместе с ним навсегда смолкает морозный морок. "
            "Перед тобой просторный сухой грот, наполненный спасительным печным духом: по стенам развешаны плотные звериные шкуры, "
            "в каменном очаге тлеют жаркие угли, а под ногами пружинит толстый слой сухого мха. "
            "Воздух прогрет подземным теплом и смолой. Здесь безопасно и тихо — бесконечная битва со стужей высоты выиграна.\n\n"
            "Открыта постоянная база: Тёплая пещера!"
        )
        buttons = []
        if not game.is_story_flag_set("furry_cave_examined"):
            buttons.append([InlineKeyboardButton(text="🔍 Осмотреть пещеру", callback_data="furry_examine")])
        if not game.is_story_flag_set("furry_cave_warmed"):
            buttons.append([InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")])
        if not game.is_story_flag_set("furry_cave_slept"):
            buttons.append([InlineKeyboardButton(text="💤 Лечь отдохнуть", callback_data="furry_sleep")])
        buttons.append([InlineKeyboardButton(text="⛺ В лагерь", callback_data="furry_leave")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "furry_leave":
        if "warm_cave_reached_day" not in game.story_flags:
            game.story_flags["warm_cave_reached_day"] = getattr(game, "day", 1)
        game.set_story_flag("visited_furry_cave", True)
        game.story_state = None
        game.active_story_callback = None
        return game.get_ui(), get_main_kb(game)

    elif data == "furry_examine":
        if not game.is_story_flag_set("furry_examine_karma_given"):
            game.set_story_flag("furry_examine_karma_given", True)
            game.adjust_narrative_karma("observation", 1)
        game.story_state = "furry_examine"
        text = (
            "Ты неторопливо обходишь каменный грот, знакомясь со своим новым кровом. "
            "Стены сложены из плотного базальта без трещин, сквозняков здесь нет. "
            "На деревянных колышках вдоль стен сушатся старые звериные шкуры, на каменном выступе темнеют несколько костяных игл и обрезки сухожилий. "
            "В дальнем непродуваемом углу под скальным навесом лежит аккуратный свёрток из плотной кожи, перевязанный бечёвкой. "
            "Кто-то долго обустраивал эту стоянку, оставив полезные вещи для тех, кто осилит подъём."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Развернуть свёрток", callback_data="furry_bundle")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_cave_start")],
        ])

    elif data == "furry_bundle":
        game.story_state = "furry_bundle"
        if game.is_story_flag_set("furry_bundle_taken"):
            text = (
                "Свёрток уже абсолютно пуст: весь найденный здесь мех был аккуратно забран к походным вещам при первом осмотре. "
                "На шершавом базальтовом уступе лежат лишь оставленные берестяные выкройки да пара костяных швейных игл. "
                "Надпись «Бери, если нужно. Оставь, если сможешь» напоминает о неписаных законах горного приюта. "
                "Тратить время на повторные поиски бессмысленно — ценный припас уже у тебя, и пора возвращаться в грот."
            )
            buttons = []
            if not game.is_story_flag_set("left_something_in_bundle"):
                buttons.append([InlineKeyboardButton(text="🎁 Положить подарок взамен", callback_data="furry_leave_gift")])
            buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="furry_bundle_leave")])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        elif game.is_story_flag_set("furry_bundle_part_taken"):
            text = (
                "Ты снова развязываешь бечёвку свёртка. Внутри остался один добротный кусок выделанного меха и берестяные выкройки. "
                "На внутренней стороне шкуры темнеет нацарапанная углем надпись: «Бери, если нужно. Оставь, если сможешь». "
                "Часть припасов уже взята тобой, а остаток сбережён ради другого замерзающего путника. "
                "Ты можешь забрать последний кусок меха себе, оставить полезный дар взамен или аккуратно завязать свёрток обратно."
            )
            buttons = [
                [InlineKeyboardButton(text="🎒 Забрать остаток (+1)", callback_data="furry_take_remainder")],
            ]
            if not game.is_story_flag_set("left_something_in_bundle"):
                buttons.append([InlineKeyboardButton(text="🎁 Положить подарок взамен", callback_data="furry_leave_gift")])
            buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="furry_bundle_leave")])
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        elif game.is_story_flag_set("left_something_in_bundle"):
            text = (
                "Ты развязываешь кожаную бечёвку. Внутри аккуратно уложены куски меха, а рядом лежит оставленный тобой полезный припас. "
                "Никто не тревожил схрон с твоего последнего визита. Короткая надпись на шкуре напоминает о чести и законе гор: "
                "«Бери, если нужно. Оставь, если сможешь». Приятно видеть, что укрытие находится в полном порядке. "
                "Ты аккуратно заворачиваешь свёрток и укладываешь его обратно на каменный уступ под навесом."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_bundle_leave")],
            ])
        else:
            text = (
                "Ты распускаешь сухой узел кожаной бечёвки и раскрываешь свёрток. "
                "Внутри лежат три отличных куска мягкого выделанного меха, берестяные выкройки зимней одежды и полоска коры с короткой надписью, "
                "нацарапанной углем: «Бери, если нужно. Оставь, если сможешь». "
                "Этот схрон — спасительный запас для переживших смертельный мороз штолен. "
                "Ты можешь забрать мех на пошив тёплой брони, взять лишь часть ради других путников или положить свой припас в знак благодарности укрытию."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎒 Забрать весь мех (+3)", callback_data="furry_take_all")],
                [InlineKeyboardButton(text="✂️ Взять часть (+2)", callback_data="furry_take_part")],
                [InlineKeyboardButton(text="🎁 Оставить подарок взамен", callback_data="furry_leave_gift")],
                [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_bundle_leave")],
            ])

    elif data == "furry_take_all":
        game.set_story_flag("furry_cave_examined", True)
        if not game.is_story_flag_set("furry_bundle_taken") and not game.is_story_flag_set("furry_bundle_part_taken"):
            game.adjust_narrative_karma("pragmatism", 2)
            game.inventory["Мех"] = game.inventory.get("Мех", 0) + 3
            game.set_story_flag("furry_bundle_taken")
            game.add_log("Получено: Мех ×3")
            text = (
                "Трезвый расчёт берёт верх: в ледяных горах впереди предстоят тяжёлые испытания, и тёплый мех жизненно необходим для выживания. "
                "Ты аккуратно убираешь все три шкуры к своим походным вещам (+3 Мех). В свёртке остаются лишь берестяные шаблоны да пара костяных игл. "
                "Завязав кожаную обёртку и уложив её обратно на каменный уступ, ты чувствуешь уверенность в завтрашнем дне: "
                "теперь из этих шкур можно сшить добротную меховую защиту от самого лютого ветра."
            )
        else:
            text = (
                "Свёрток уже абсолютно пуст: весь найденный здесь мех был аккуратно забран к походным вещам при первом осмотре. "
                "На шершавом базальтовом уступе лежат лишь оставленные берестяные выкройки да пара костяных швейных игл. "
                "Надпись «Бери, если нужно. Оставь, если сможешь» напоминает о неписаных законах горного приюта. "
                "Тратить время на повторные поиски бессмысленно — ценный припас уже у тебя, и пора возвращаться в грот."
            )
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_cave_start")],
        ])

    elif data == "furry_take_part":
        game.set_story_flag("furry_cave_examined", True)
        if not game.is_story_flag_set("furry_bundle_taken") and not game.is_story_flag_set("furry_bundle_part_taken"):
            game.adjust_narrative_karma("compassion", 1)
            game.inventory["Мех"] = game.inventory.get("Мех", 0) + 2
            game.set_story_flag("furry_bundle_part_taken")
            game.add_log("Получено: Мех ×2")
            text = (
                "Ты достаёшь два куска выделанного меха, а третий бережно заворачиваешь обратно (+2 Мех). Берестяные выкройки остаются на месте. "
                "Неписаный закон стоянки соблюдён: ты берёшь достаточно для пошива самого необходимого, но сохраняешь спасительную долю тому, "
                "кто придёт в пещеру следом на исходе последних сил. Завязав бечёвку, ты возвращаешь свёрток на скальный уступ под навесом. "
                "На душе становится спокойно и чисто — человечность важнее слепой жадности."
            )
        else:
            text = (
                "Справедливая доля припасов уже взята из этого свёртка при прошлом осмотре. "
                "Оставшаяся часть лежит нетронутой ради того, кто придёт в пещеру следом за тобой на исходе последних сил. "
                "Нарушать собственное слово и отбирать чужой шанс на спасение не имеет никакого смысла. "
                "Ты аккуратно поправляешь узел на шкуре и спокойно отходишь от каменной ниши обратно к мягкому моховому ковру."
            )
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_cave_start")],
        ])

    elif data == "furry_take_remainder":
        game.set_story_flag("furry_cave_examined", True)
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
                "Свёрток уже абсолютно пуст: весь найденный здесь мех был аккуратно забран к походным вещам при первом осмотре. "
                "На шершавом базальтовом уступе лежат лишь оставленные берестяные выкройки да пара костяных швейных игл. "
                "Тратить драгоценное время на повторные поиски бессмысленно — здесь больше не осталось ничего полезного. "
                "Пора вернуться к согревающему пещерному очагу или как следует устроиться на ночлег."
            )
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_cave_start")],
        ])

    elif data == "furry_leave_gift":
        game.set_story_flag("furry_cave_examined", True)
        if not game.is_story_flag_set("left_something_in_bundle"):
            game.adjust_narrative_karma("compassion", 2)
            game.set_story_flag("left_something_in_bundle", True)
            gift_name = deduct_story_gift_item(game)
            gift_note = f" Внутрь свёртка аккуратно уложен припас: {gift_name}." if gift_name else " В свёрток бережно уложена щепоть сухого пещерного мха."
            text = (
                "Ты решаешь не брать чужой мех без крайней нужды или отблагодарить невидимого хозяина за убежище."
                f"{gift_note} Крепко затянув кожаную бечёвку, ты возвращаешь схрон на место под каменный выступ. "
                "Закон горного приюта соблюдён в полной мере: пещера сохранила припасы, и тепло этого маленького доброго дела согревает лучше любого костра."
            )
        else:
            text = (
                "Полезный припас уже оставлен в этом свёртке во время прошлого осмотра схрона. "
                "Твой припас надёжно укрыт под шкурой и дожидается того, кому он спасёт жизнь в морозную метель на краю гибели. "
                "Перегружать маленький схрон лишними вещами нет смысла — закон честной стоянки уже полностью соблюдён. "
                "Ты аккуратно поправляешь верёвку на свертке и спокойно отходишь от каменного уступа."
            )
        game.story_state = "furry_after_bundle"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_cave_start")],
        ])

    elif data == "furry_bundle_leave":
        game.set_story_flag("furry_cave_examined", True)
        return handle_location_6_furry_cave("furry_cave_start", game, uid)

    elif data == "furry_warm":
        game.set_story_flag("furry_cave_warmed", True)
        if not game.is_story_flag_set("furry_warm_karma_given"):
            game.set_story_flag("furry_warm_karma_given", True)
            game.adjust_narrative_karma("pragmatism", 1)
        game.story_state = "furry_warmed"
        text = (
            "Ты подходишь к каменному очагу, сложенному из тяжёлых базальтовых плит в центре пещеры. "
            "В глубине золы ещё алеют стойкие горячие угли. Ты подбрасываешь горсть сухого мха и мелких щепок: "
            "мох мгновенно вспыхивает ярким рыжим пламенем, весело потрескивая. Свод грота озаряется пляшущими отсветами, "
            "а к каменным стенам устремляется плотная волна сухого печного жара. Дым послушно утягивается в узкую расселину под потолком, не оставляя гари."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Посидеть у огня (+10 ХП)", callback_data="furry_fire_rest")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_cave_start")],
        ])

    elif data == "furry_fire_rest":
        game.set_story_flag("furry_cave_warmed", True)
        if not game.is_story_flag_set("furry_fire_rest_karma_given"):
            game.set_story_flag("furry_fire_rest_karma_given", True)
            game.adjust_narrative_karma("observation", 1)
            if hasattr(game, "heal"):
                game.heal(10)
            else:
                game.hp = min(getattr(game, "max_hp", 100), game.hp + 10)
        text = (
            "Ты садишься на тёплый камень прямо у очага, протягивая озябшие руки к живому пламени. "
            "Огонь мягко гудит, разгоняя остатки ледяной скованности в суставах и пальцах. Дышать легко и свободно: "
            "сухой жар наполняет уставшее тело глубоким покоем, а мерный треск углей убаюкивает напряжённые нервы. "
            "Силы возвращаются с каждым глубоким вдохом (+10 ХП). "
            "Поднявшись на ноги, ты чувствуешь, что смертельный холод пройденного подъёма окончательно отступил."
        )
        game.story_state = "furry_fire_rested"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_cave_start")],
        ])

    elif data == "furry_sleep":
        pet_text = ""
        if game.is_story_flag_set("has_pet"):
            text = (
                "Ты опускаешься на пышный пружинящий настил из сухого мха. Котёнок тут же выбирается из-под одежды за пазухой, "
                "топчется лапками по твоей груди и с громким урчанием сворачивается тёплым клубком у шеи. В пещере стоит сухая благодать. "
                "Ты закрываешь глаза и проваливаешься в глубокий целительный сон... Внезапный шорох выдёргивает тебя из дрёмы! "
                "В тусклом свете углей у самого лаза мелькает спина тёмной фигуры и тут же бесшумно растворяется в ночной тьме."
            )
        else:
            text = (
                "Ты опускаешься на толстый пружинящий настил из сухого пещерного мха. Камень под ним прогрет подземным дыханием горы, "
                "и сухая зелень держит ласковое тепло, словно перина. Ты закрываешь отяжелевшие веки и проваливаешься в глубокий сон, "
                "смывающий изнурительную усталость пройденного подъёма... Внезапный осторожный шорох заставляет резко распахнуть глаза! "
                "У выхода из грота на миг мелькает тёмный силуэт человека и тут же растворяется в ночной мгле."
            )
        game.story_state = "furry_awoken"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎒 Проверить вещи", callback_data="furry_loss")],
        ])

    elif data == "furry_loss":
        game.set_story_flag("furry_cave_slept", True)
        game.set_story_flag("something_was_taken", True)
        text = (
            "Ты вскакиваешь на ноги и торопливо проверяешь свои походные вещи. Всё цело, но из припасов исчезла малая часть еды. "
            "Однако рядом на камне обнаруживается неожиданная находка: аккуратный лоскут добротного меха, оставленный взамен взятого. "
            "Незнакомец не был врагом или грабителем — он зашёл погреться, взял немного припасов для выживания и расплатился по неписаному закону стоянки. "
            "Сердце бьётся ровно: пещера жива, а здешние путники чтут правила чести."
        )
        game.story_state = "furry_after_loss"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="furry_cave_start")],
        ])

    elif data == "furry_end":
        game.set_story_flag("visited_furry_cave", True)
        game.set_story_flag("l6_ridge_unlocked", True)
        game.story_state = None
        if hasattr(game, "reset_nav"):
            game.reset_nav()
        return game.get_ui(), get_main_kb(game)
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
            "Боль обжигает тело, но нависшая смертельная угроза полностью устранена: тропа расчищена, "
            "и каменный карниз теперь безопасен для дальнейшего подъёма."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step13_edge":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step13_choice", "pragmatism")
        game.story_state = "l6_step13_edge"
        text = (
            "Не тратя времени на расчистку обвала и долгие поиски, ты вплотную прижимаешься к холодной скале "
            "и быстро проскальзываешь по узкому наружному краю плиты над бездной. "
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
            "Широкая площадка упирается в отвесный каменный уступ, разделяющий ярусы пещеры. "
            "Прямо в скалу вмонтирован старый подъёмный механизм с массивным колесом и цепью. "
            "Над чернеющим провалом застыла перекошенная подвесная площадка для подъёма наверх. "
            "Вся конструкция скована льдом и занесена инеем, но металл удивительно крепок: "
            "кованые зубья не тронуты ржавчиной, а в узлах креплений виден точный расчёт строителей. "
            "Тропа обрывается, и этот механизм — единственный ключ к следующему ярусу."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Подойти к механизму", callback_data="l6_step15_detail")]
        ])

    elif data == "l6_step15_detail":
        game.story_state = "l6_step15_detail"
        text = (
            "Вблизи механизм открывает свои детали. Сбоку на ветру угрожающе раскачивается сорванная кованая цепь: "
            "от резких ударов тяжёлых звеньев она рискует сорвать висящую платформу в пропасть и наглухо перекрыть проход. "
            "На массивном колесе намертво заклинило тормоз, оббитый широкой полосой прочной выделанной кожи. "
            "Зубчатая передача цела, но нужно решить: потратить силы и закрепить цепь, срезать себе ценную кожу "
            "или внимательно изучить устройство механизма."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Изучить схему передач", callback_data="l6_step15_observe")],
            [InlineKeyboardButton(text="⛓️ Зафиксировать цепь", callback_data="l6_step15_cable")],
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
            "Тяжёлая цепь вырывается из замёрзших пальцев, но ты упрямо наваливаешься всем весом "
            "и заводишь сорванное звено в массивный стальной стопор на раме. Замок с сухим щелчком намертво фиксирует груз над бездной. "
            "Конструкция спасена от обрушения: платформа больше не сорвётся вниз, проход остаётся свободным, "
            "а прочная дубовая опора теперь служит надёжной защитой для безопасного подъёма на верхний ярус."
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
                "Материал отлично сохранился на морозе: прочный ремень сразу отправляется к твоим вещам. "
                "В условиях выживания практическая польза важнее чужих механизмов — хорошая кожа всегда пойдёт на починку обуви и одежды."
            )
        else:
            text = (
                "Ты подходишь к тормозному ободу ворота. Широкая полоса толстой выделанной кожи уже срезана с колодок во время твоего первого осмотра грузового подъёмника. "
                "На промёрзшей дубовой раме остались лишь шляпки медных заклёпок и глубокие задиры от старой цепи. "
                "Ничего полезного здесь больше не осталось — отличный кожаный ремень давно надёжно спрятан к твоим вещам. "
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
            "На каменных плитах видны следы давней беды: расколотый деревянный посох, сорванная осыпь "
            "и глубокая царапина на скользком уступе, уходящая прямо в бездну. Кто-то давно сорвался на этом обледенелом повороте. "
            "В глубокой расщелине у самой кромки обрыва застряла брошенная кожаная сумка. "
            "Этот опасный карниз над ледяной пустотой не прощает спешки."
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
            "Человек сорвался здесь очень давно — с тех пор снег и лёд сходили сотни раз, меняя рельеф карниза до неузнаваемости. "
            "Старая царапина на камне служит лишь немым предупреждением. "
            "Взгляд оценивает тропу в её нынешнем состоянии: прямо по центру перегиба снова блестит коварный гладкий натёк, "
            "но вплотную к шершавой каменной стене есть узкая сухая полоса. "
            "Прямо сейчас можно безопасно пройти именно там, аккуратно прижимаясь плечом к скале и надёжно ставя ноги на цепкий гранит."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step17_wall":
        game.adjust_narrative_karma("intervention", 1)
        game.set_story_flag("l6_step17_choice", "intervention")
        game.story_state = "l6_step17_wall"
        text = (
            "Ты находишь вдоль стены тяжёлые обломки породы и один за другим перетаскиваешь их к открытому обрыву. "
            "Точные удары намертво расклинивают камни в расщелинах, формируя сплошной надёжный бортик вдоль опасного закругления карниза. "
            "Пальцы стынут на ледяном ветру, мышцы ноют от тяжести, но опасный уступ теперь защищён: "
            "край бездны надёжно перекрыт крепкой кладкой, и теперь здесь можно проходить без постоянного страха сорваться вниз."
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
                "Еда замёрзла в камень, но остаётся вполне пригодной. Больше ничего нет — лишь закопчённый котелок на самом дне. "
                "Глядя в чернеющую под карнизом пропасть, откуда доносится глухой свист ветра, предстоит решить: "
                "забрать всё себе или, повинуясь внутреннему чувству равновесия и совести, оставить что-то взамен."
            )
        else:
            text = (
                "Ты снова заглядываешь в расстёгнутую сумку у обрыва. Внутри пусто: найденные ранее кусок меха и порция жареного мяса уже убраны к твоим вещам. "
                "На дне расщелины остаётся лишь помятый медный котелок со следами давней копоти. Холодный ветер заунывно гудит над кромкой карниза, напоминая о ледяной высоте. "
                "Здесь больше нечего искать — пора продолжать подъём по тропе или перевести дух в лагере."
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
                    "Пальцы проверяют походные запасы, но внутри пусто: нет ни вяленого мяса, ни сушёных ягод, ни сухарей — сумке нечего предложить взамен. "
                    "Холодный ветер с воем бьёт в грудь над краем обрыва. Чувство внутреннего равновесия и совесть требуют отдать что-то взамен взятого, но пустые руки бессильны. "
                    "Предстоит решить: забрать найденное без отдачи ради собственного выживания или оставить припасы нетронутыми и шагать дальше."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎒 Забрать всё и уйти", callback_data="l6_step17_take_all")],
                    [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")],
                ])
            else:
                game.adjust_narrative_karma("compassion", 1)
                game.set_story_flag("l6_step17_gift_left", True)
                text = (
                    f"Мех и порция мяса отправляются к твоим вещам, а на сухую бересту ложится припас ({item_given}) из твоих походных запасов. "
                    "Клапан сумки снова плотно застёгивается. Никто не знает, коснётся ли её ещё чья-то рука, но внутреннее чувство равновесия и чистая совесть стоят дороже лишнего куска. "
                    "Брать без отдачи в этих ледяных горах кажется дурным знаком. На душе становится спокойно и тепло, словно гора приняла эту честную плату."
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
                ])
        else:
            text = (
                "Припас уже оставлен в сумке на карнизе во время первого осмотра. Полезная еда надёжно прикрыта кожаным клапаном от колючей ледяной пыли. "
                "Внутренний долг перед собственной совестью исполнен, баланс сохранён. Задерживаться на пронизывающем сквозняке над чернеющей бездной больше незачем — "
                "пора возвращаться к подъёму по скалам или спокойно восстановить силы у тёплого лагерного костра."
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
            ])

    elif data == "l6_step17_take_all":
        game.set_story_flag("l6_step17_took_all", True)
        game.story_state = "l6_step17_take_all"
        text = (
            "Ты застёгиваешь опустевшую сумку у обрыва и поправляешь походную перевязь. "
            "Кусок меха и порция мяса надёжно спрятаны среди твоих вещей, а пустой медный котелок остаётся лежать в расщелине скалы. "
            "Суровый закон высоты прост: гора не прощает пустых сомнений тому, кто рискует жизнью над пропастью. "
            "Рассудок говорит, что выживание важнее условностей. Оставив опасный край карниза позади, ты делаешь вдох морозного воздуха и продолжаешь путь."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 20: Извилистые штольни и морозный морок
    elif data == "l6_step20_main":
        game.story_state = "l6_step20_main"
        text = (
            "Бесконечные каменные штольни упрямо кружат в толще горы, путая шаги и сбивая направление. "
            "Кажется, будто за это время можно дважды одолеть крутой перевал, но под ногами всё ещё лишь середина подъёма. "
            "Воздух здесь разреженный, сухой и обжигающе ледяной. "
            "Сквозняк, прорываясь сквозь трещины свода, звучит обманчивым ритмичным эхом: "
            "в свисте ветра чудятся чужие шаги за спиной, звон пряжек и тихий шёпот. Морозный морок испытывает рассудок на прочность."
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
            "Ты останавливаешься и закрываешь глаза, заставляя себя отрешённо вслушаться в темноту. "
            "Слух быстро наводит порядок: мнимый шёпот оказывается лишь глухим завыванием сквозняка в узких трещинах свода, "
            "а чужие шаги и звон пряжек — хрустом тонких ледяных игл и звоном мелких камешков, осыпающихся по склону. "
            "Никого позади нет, это лишь обман уставшего от мороза слуха. "
            "Наваждение рассеивается без следа, возвращая абсолютную ясность мысли и спокойный контроль."
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
                "Ты прижимаешь ладонь к груди, где под плотной одеждой за пазухой клубится спасительное живое тепло. "
                "Котёнок забился глубоко в складки ткани у самого сердца и тихо мурлычет, ощущая защиту. "
                "Это крошечное, упрямое биение жизни мгновенно выдёргивает сознание из ледяной паутины наваждения. "
                "Забота о беззащитном существе начисто выжигает навязчивый морок. "
                "Внутри разливается ясный покой: нельзя сдаваться и падать духом, пока рядом теплится эта жизнь."
            )
        else:
            text = (
                "Ты прижимаешь онемевшую ладонь к груди, вслушиваясь в собственное ровное, упрямое сердцебиение. "
                "Живая память о лагерном огне, вкус горячей похлёбки и простое тепло дыхания постепенно вытесняют навязчивый морок. "
                "Человек жив, пока внутри горит огонь воли, а рассудок держится за свет и тепло даже посреди мерзлоты. "
                "Ледяное наваждение бессильно тает в клубах пара, уступая место спокойной, согревающей уверенности в своих силах."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step20_pragmatism":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step20_choice", "pragmatism")
        game.story_state = "l6_step20_pragmatism"
        text = (
            "Ты стискиваешь зубы и делаешь тяжёлый шаг вперёд, наотрез отказываясь верить обманчивому эху. "
            "Пусть за спиной чудится скрип чужих подошв по гравию, в темноте мерещится приглушённый шёпот, "
            "а ветер доносит металлическое бренчание пряжек — рассудок остаётся твёрд. "
            "Ноги упрямо отсчитывают метр за метром по каменному полотну. "
            "Морок бессилен против непреклонной воли к выживанию: здесь нет ни призраков, ни преследователей, "
            "есть только ты, крутой подъём и морозная тропа к вершине."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ──────────────────────────────────────────────────────────────────────────
    # СЮЖЕТНЫЕ ОКНА ПОДЪЁМА (ИССЛЕДОВАНИЯ 21–25 ИЗ 40)
    # ──────────────────────────────────────────────────────────────────────────

    # ИССЛЕДОВАНИЕ 23: Шёпот из толщи скалы
    elif data == "l6_step23_main":
        game.story_state = "l6_step23_main"
        text = (
            "Узкая тропа жмётся к отвесной базальтовой стене, уходящей в ледяную тьму верхних гротов. "
            "Глухую тишину пещеры внезапно нарушает низкая, утробная вибрация, поднимающаяся откуда-то из самой толщи горы. "
            "Мелкие острые камешки под ногами начинают подпрыгивать и звенеть о плиты. "
            "От чёрной каменной стены исходит ровный, ритмичный гул, похожий на медленное биение сердца. "
            "Словно древняя гора пытается заговорить с идущим сквозь мороз человеком."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Прислушаться к скале", callback_data="l6_step23_detail")]
        ])

    elif data == "l6_step23_detail":
        game.story_state = "l6_step23_detail"
        text = (
            "Ты делаешь шаг ближе к холодной плите. Вблизи вибрация становится настолько плотной, что отдаётся тупой, ноющей болью в костях. "
            "Звук перестаёт быть просто эхом сквозняка: низкий резонанс камня пугающе складывается в подобие раскатистого голоса: "
            "«Куда ты идёшь?.. Гора не прощает тепла...». "
            "Каменная толща под пальцами мелко дрожит, осыпая тонкие ледяные пластинки. "
            "Недра пещеры испытывают решимость на прочность, требуя ответа на этот ледяной зов."
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
            "Ты без колебаний прижимаешь раскрытую ладонь к дрожащему базальту. "
            "Сквозь ледяной камень передаётся мощный подземный ритм, будто в недрах хребта ворочается древняя громада. "
            "«Я иду наверх. Меня ждёт тепло», — твёрдо звучит твой голос под сводами. "
            "Вибрация на мгновение замирает, а затем сменяется протяжным, глубоким вздохом сквозняка в расщелинах. "
            "Дрожь в скале постепенно утихает: гул стихает, уступая право продолжить путь к вершине."
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
                "Ты прижимаешь руку к груди, где под плотной одеждой за пазухой клубится тепло. "
                "Котёнок шевелится у самого сердца, осторожно высовывает мокрый нос и чутко принюхивается к воздуху. "
                "Вдруг малыш сердито фыркает на низкий гул из скалы и снова утыкается мордочкой в ладонь. "
                "Простое, живое тепло маленькой жизни мгновенно выдёргивает сознание из оцепенения. "
                "В ушах снова звучит лишь обычный свист ветра. Спутник тихо урчит, возвращая уверенность в каждом шаге."
            )
        else:
            text = (
                "Ты закрываешь глаза и делаешь глубокий медленный вдох, сосредотачиваясь на ровном стуке своего сердца. "
                "Живое тепло тела и железная выдержка вытесняют давящий морок. "
                "Рассудок трезво отделяет реальность от обмана: это лишь резонанс сильного ветра в полостях горы, звон ледяных сосулек и накопившаяся усталость. "
                "Наваждение рассыпается, уступая место звенящей ясности ума. "
                "Перед глазами снова лишь немая холодная стена и свободная тропа, зовущая дальше вверх."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step23_pragmatism":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step23_choice", "pragmatism")
        game.story_state = "l6_step23_pragmatism"
        text = (
            "Ты стискиваешь зубы и упрямо прибавляешь шаг, наотрез отказываясь обращать внимание на скальный гул. "
            "Пусть камень вибрирует как угодно — живой человек подчиняется лишь собственной воле и шагам. "
            "Ледяной сквозняк бьёт прямо в лицо, остужая лоб и окончательно выдувая призрачные звуки из головы. "
            "Дрожащий участок базальтовой стены быстро остаётся позади. "
            "Силы и дыхание сбережены, а трезвый практический расчёт позволяет уверенно идти вперёд без сомнений."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 25: Снежный баран в расщелине
    elif data == "l6_step25_main":
        game.story_state = "l6_step25_main"
        text = (
            "Подъём петляет между отвесными каменными уступами, засыпанными острым щебнем и ледяным крошевом. "
            "Внезапно из бокового разлома скалы доносится скрежет камня и частый, отчаянный стук копыт о породу. "
            "Звуки звучат панически и надрывно, резко разрывая тяжёлую тишину пещеры. "
            "Кто-то застрял в узком каменном тупике сразу за поворотом тропы, безуспешно пытаясь вырваться из холодной ловушки. "
            "Заиндевевший воздух дрожит от сдавленного хриплого дыхания зверя."
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
            "Ты скидываешь рукавицы, упираешься плечом в скол породы и наваливаешься на плиту всем весом тела. "
            "Каменная крошка со скрежетом сыплется под подошвами, мышцы напряжены до предела, но тяжёлая глыба неохотно подаётся в сторону на ширину ладони. "
            "Этого мига хватает: баран молниеносно выдёргивает ногу, вскакивает и замирает на уступе, бросив долгий взгляд. "
            "Мощным упругим прыжком зверь взлетает на карниз и скрывается наверху, показав следами копыт безопасный проход."
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
                "Ты достаёшь пучок сухого пещерного мха, а котёнок под одеждой за пазухой начинает тихо и ровно мурлыкать. "
                "Этот мирный живой звук творит чудо: дикий зверь перестаёт паниковать и осторожно тянется к корму прямо с ладони. "
                "Пока баран отвлечён, ты аккуратно просовываешь пальцы в щель, разворачиваешь сустав вдоль каменного паза и осторожно освобождаешь копыто. "
                "Зверь благодарно тычется тёплым носом в рукав и лёгким скачком уносится вверх, показывая тропу сквозь осыпь."
            )
        else:
            text = (
                "Ты достаёшь пучок сухого пещерного мха и спокойным, ровным голосом заговариваешь со зверем. "
                "Уловив отсутствие угрозы, баран тянется к корму и жадно пережёвывает волокна. "
                "Воспользовавшись моментом, ты опускаешься на колени, нащупываешь зажатое копыто и осторожным движением выводишь сустав сквозь широкую часть щели. "
                "Пленник спасён: облегчённо фыркнув, зверь вспрыгивает на карниз и устремляется в верхний коридор, оставляя за собой безопасные следы на камнях."
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
            "Галерея упирается в глухой завал: обвал наглухо перекрыл проход тяжёлыми каменными глыбами. "
            "На миг кажется, что тропа оборвалась и подъём окончен. Но у самого основания завала, в полосе тени у пола, "
            "чернеет узкая щель, откуда ощутимо тянет свежим сквозняком. А выше по стене виднеется неровный карниз, "
            "уходящий в обход завала под самым сводом. Преграда серьезна, но преодолима: нужно лишь выбрать верный и безопасный способ двигаться дальше."
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
            "Ты снимаешь с плеч поклажу, проталкиваешь вещи перед собой и на четвереньках протискиваешься в тёмный лаз под завалом. "
            "Холодный сквозняк овевает лицо, а камень вокруг гладкий, веками отшлифованный подземной водой. "
            "Несколько упорных толчков локтями и коленями — и тело протискивается сквозь каменный капкан наружу. "
            "Коридор впереди свободен и плавно уходит вверх. Трезвый расчёт и гибкость позволяют преодолеть завал за пару минут без лишней траты сил."
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
            "Ты упрямо упираешься плечом в край осевшей глыбы и наваливаешься на камень всем телом. "
            "Острые грани крошатся, сдирая ткань рукавиц. С глухим скрежетом плиту удаётся сдвинуть, "
            "но следом опасно оседает нависающий свод. Острый осколок базальта больно бьёт по руке (❤️ -5 HP). "
            "Приходится резко отпрянуть от сыплющейся пыли. Лаз с трудом расширен до прохода, "
            "но гора сурово напоминает: слепая грубая сила в этих штольнях всегда требует расплаты здоровьем."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step27_climb":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step27_choice", "observation")
        game.story_state = "l6_step27_climb"
        text = (
            "Ты поднимаешь взгляд и внимательно изучаешь трещины свода. На высоте двух человеческих ростов обнаруживается "
            "естественный каменный карниз, уходящий вглубь коридора прямо над завалом. "
            "Цепляясь за шероховатые выступы базальта, удаётся аккуратно взобраться наверх и обогнуть опасную осыпь по надёжной крепкой породе. "
            "Острые сколы требуют цепких пальцев и равновесия, но наблюдательность бережёт здоровье: путь на следующий ярус галереи открыт."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 30: Лик каменного исполина и дыхание недр
    elif data == "l6_step30_main":
        game.story_state = "l6_step30_main"
        text = (
            "Высота трёх четвертей подъёма распахивается огромным каменным гротом. Свод теряется в морозной темноте, "
            "а на дальней стене выступы породы образуют грубые очертания исполинского каменного лика. "
            "В воздухе снова нарастает низкий, плотный гул. Эхо, дрожащее в породе, звучит пугающе отчётливо: "
            "«Ты добираешься сюда, огонёк... Но выдержишь ли жар глубин?..». "
            "Из глубоких трещин у подножия стены поднимаются первые струи тёплого пара с запахом влажной земли."
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
            "«Я выдержу. Я иду за теплом», — ровно звучит твой голос под сводами пещеры. "
            "В ответ скалы отзываются низким, раскатистым рокотом, похожим на глухое эхо камнепада. "
            "«Иди же... последний рубеж впереди», — затихает дрожь, плавно растворяясь в толще породы. "
            "Воздух вокруг ощутимо теплеет, словно гора признала упорство одиночки и пропустила к своему сокровенному теплу."
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
                "Ты опускаешься на колени у парящей трещины и бережно достаёшь котёнка из-под одежды за пазухой. "
                "Малыш щурит сонные глаза, подставляет мордочку восходящему мягкому пару и громко мурлычет под каменными сводами. "
                "Пальцы тихо гладят его согретую спинку. Ледяной кошмар остаётся позади: тепло совсем близко, и вы оба дойдёте до цели. "
                "Силы возвращаются живой волной радости, смывая накопившуюся тяжесть и холод бесконечного подъёма."
            )
        else:
            text = (
                "Ты опускаешься к парящей расселине и подставляешь онемевшие ладони струям глубинного пара. "
                "Живое тепло медленно возвращает чувствительность пальцам и разливается по уставшему телу. "
                "Вдох горячего воздуха наполняет лёгкие настоящей силой, прогоняя сковавший кости холод. "
                "Ледяная мгла пещеры отступает: до спасительного порога Тёплой пещеры остаётся лишь один последний, "
                "решительный рывок сквозь верхние скальные коридоры."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step30_gear":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step30_choice", "pragmatism")
        game.story_state = "l6_step30_gear"
        text = (
            "Не отвлекаясь на обманчивый гул скал, ты встаёшь у края подъёма и методично проверяешь походное снаряжение. "
            "Замёрзшие ремни перевязаны, узлы поклажи подтянуты, дыхание выровнено. "
            "Впереди — последний, самый крутой отрезок пути к спасительному теплу. "
            "Холодный прагматизм и трезвый расчёт не оставляют места пустым сомнениям. "
            "Ты делаешь уверенный шаг в тёплый восходящий поток воздуха, полностью готовый преодолеть финальный рубеж."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 33: Тектонический разлом и старая переправа
    elif data == "l6_step33_main":
        game.story_state = "l6_step33_main"
        text = (
            "Путь преграждает глубокий тектонический разлом, рассекающий штольню от стены до стены. "
            "Внизу, в непроглядной ледяной черноте, глухо шумит невидимый подземный поток. "
            "Единственная переправа — две старые бревенчатые балки, потемневшие от сырости и скреплённые коваными скобами. "
            "В отвесную скалу рядом намертво вбит ржавый железный крюк с остатками истлевшей верёвки. "
            "Морозное дыхание чернеющей бездны требует взвешенного решения."
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
            "Ты опускаешься на корточки, пробуешь ногой скользкое промороженное дерево и, точно поймав равновесие, "
            "шаг за шагом переходишь над бездной. Балка едва слышно потрескивает под весом тела, но старая опора держит надёжно. "
            "Ледяной сквозняк снизу холодит лицо, за спиной остаётся чёрная пропасть, а впереди открывается продолжение скального коридора. "
            "Трезвая уверенность и точный расчёт движений позволяют преодолеть опасный разлом без лишней траты сил."
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
            "ты методично забиваешь их тяжёлым голышом под основание просевшей опоры переправы. "
            "Кованые скобы натягиваются со звоном, балка перестаёт вибрировать и встаёт в каменный распор намертво. "
            "Теперь мостик над чёрной бездной закреплён надёжно и не рухнет от неловкого шага. "
            "Спокойно перейдя на противоположный край разлома, ты продолжаешь подъём."
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
                "Внимательный поиск приносит плоды: в скрытом углублении за скальным выступом обнаруживается "
                "завёрнутый в сухую холстину коробок спичек (+1 Спички). Находка сразу отправляется к твоим походным запасам: "
                "в ледяных недрах огонь решает всё. Аккуратно перешагнув разлом по бревенчатому настилу, "
                "ты с полезной добычей уверенно продолжаешь подъём."
            )
        else:
            text = (
                "Ты снова внимательно осматриваешь трещину вокруг старого страховочного крюка. "
                "В каменной нише пусто: нетронутый коробок спичек уже был найден и надёжно убран к твоим походным вещам при первом осмотре. "
                "В глубокой расселине осталась лишь базальтовая крошка да бурая ржавчина от старого крепежа. "
                "Разлом благополучно преодолён по бревенчатому настилу, и задерживаться над бездной больше незачем — путь наверх свободен."
            )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 36: Пик ледяного морока
    elif data == "l6_step36_main":
        game.story_state = "l6_step36_main"
        text = (
            "Стужа переходит все мыслимые пределы, и из ледяных стен прямо в рассудок врывается настойчивый, давящий голос. "
            "Гора больше не молчит — мороз говорит с тобой каждым порывом сквозняка: «Остановись, огонёк... Зачем мучить плоть? "
            "Опусти руки, ложись на камень и усни. Отдай тепло, и холод станет покоем...». "
            "Воздух густеет от ледяной взвеси, виски ломит от стужи. Голос требует бросить всё и сдаться, "
            "суля избавление от боли взамен на жизнь. Морок испытывает волю на излом."
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
            "«Нет. Я не усну здесь, и моё тепло останется со мной», — твой хриплый шёпот разбивает наваждение. "
            "Ты заставляешь себя дышать мерно и глубоко, силой воли отгоняя ледяной дурман. "
            "Призрачный шёпот в стенах бессильно шипит и распадается на обычный свист ветра в щелях: «Ты упрям... но лёд ждёт ошибки...». "
            "Наваждение растворяется, виски отпускает тупая боль. "
            "Реальность возвращается кристально ясной: впереди виден пологий подъём, и трезвый рассудок ведёт тебя дальше."
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
                "Голос в темноте лукаво шепчет в правое ухо: «Сверни сюда, здесь чужой костёр, здесь тебя обогреют...». "
                "Ты настороженно шагаешь на этот зов в боковой коридор. Никакого костра здесь нет — морок пытался завести тебя в ледяной тупик. "
                "Но на дне глубокой расщелины скалы обнаруживается живучий пещерный мох (+1 Пещерный мох). "
                "Он не греет сам по себе, но отлично пойдёт на растопку настоящего огня. Спрятав сбор к припасам, ты отбрасываешь обман и возвращаешься на тропу."
            )
        else:
            text = (
                "Ты снова заглядываешь в боковой коридор, где морок недавно пытался заманить тебя призрачным огнём. "
                "Пучок сухого мха на растопку уже собран к твоим вещам, а каменная щель пуста. "
                "Голоса больше не звучат здесь — наваждение отступило перед холодным расчётом. "
                "На промороженном базальте остался лишь тёмный след. "
                "Задерживаться на сквозняке не имеет смысла: пора уверенно продолжать подъём по основному коридору к вершине."
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
                "«Брось всё... тебе не дойти...», — настойчиво гудит в ушах ледяной шёпот скал. "
                "Но в этот миг котёнок под одеждой за пазухой сердито фыркает, тычется мокрым носом в ладонь и выпускает коготки, "
                "указывая верный проход. Это живое тепло мгновенно перебивает морок. "
                "«Замолчи», — твёрдо думаешь ты, глядя в темноту, и призрачный голос испуганно затихает. "
                "Маленький спутник возвращает тебя в реальность, и ты уверенно шагаешь вперёд по свободной тропе."
            )
        else:
            text = (
                "«Брось всё... тебе не дойти...», — настойчиво гудит в ушах ледяной шёпот скал, пытаясь сбить с пути. "
                "Но ты прижимаешь онемевшую ладонь к груди и вслушиваешься в упрямый, размеренный стук своего сердца. "
                "Живая человеческая воля сильнее морока. «Я дойду», — звучит мысль громче любого наваждения. "
                "Призрачный голос бессильно тает в клубах пара твоего дыхания. Доверившись верному инстинкту, "
                "ты делаешь решительный шаг вперёд, где коридор распахивается чистым проходом наверх."
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
            "Ты опускаешь раскрытую ладонь на влажный тёплый базальт. Камень на ощупь горяч, как печная заслонка. "
            "Глубокий бас горы, терзавший рассудок в промороженных штольнях, звучит в последний раз — но теперь без угрозы: "
            "«Ты выдержал стужу и не поддался обману, человек... Проходи к огню». «Спасибо за дорогу», — тихо отвечаешь ты скале. "
            "Вибрация под ногами утихает, сменяясь ровным, умиротворённым теплом. Недра горы признали твою волю и распахнули проход."
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
            "Ты не тратишь драгоценные минуты на изучение пара и разговоры со скалами. Вдохнув сухой тёплый воздух полной грудью, "
            "ты решительно ускоряешь шаг, поправив походные вещи за плечами. С каждым метром идти становится легче: "
            "скованность в суставах проходит, а тепло наполняет озябшие мышцы новой энергией. "
            "Чёткий расчёт и несгибаемая воля ведут вперёд: финишная прямая бесконечного подъёма уже перед глазами."
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
                    "Ты опускаешься на колени и осторожно выпускаешь котёнка на подстилку. "
                    "Малыш с восторгом трётся о мягкие стебли, довольно мурлычет на всю пещеру и катается по пружинящему ковру, "
                    "согреваясь в сухом пещерном воздухе. Земля здесь тёплая от подземного пара, а плотный мох отлично удерживает этот уют. "
                    "Ты срываешь пучок сухого сбора про запас (+1 Пещерный мох): такой слой послужит отличной подстилкой в лагере или сухим трутом для розжига костра."
                )
            else:
                text = (
                    "Ты опускаешься на колени и проводишь ладонями по мягкому моховому ковру. "
                    "Тёплый воздух от близких трещин с паром нагревает каменный пол, а густая пружинящая зелень создаёт сухую и удобную подстилку. "
                    "Не веря долгожданному спасению от стужи, ты срываешь пышный пучок сухого мха себе в походные запасы (+1 Пещерный мох). "
                    "Этот сбор не лечит раны, но станет незаменимой мягкой подстилкой для сна или надёжным трутом для быстрого розжига костра."
                )
        else:
            if game.is_story_flag_set("has_pet"):
                text = (
                    "Ты снова опускаешься на мягкую подстилку у порога пещеры. "
                    "Запас сухого мха на растопку уже убран к твоим вещам, но котёнка невозможно оторвать от тёплого каменного пола. "
                    "Малыш с урчанием перекатывается по пружинящим стеблям, подставляя нагретому воздуху пушистый бок. "
                    "Опасности больше нет: сквозняки высоты остались позади, а впереди ждёт настоящий очаг. "
                    "Приятно видеть, как маленький спутник наконец-то отогрелся после бесконечной ледяной тропы."
                )
            else:
                text = (
                    "Ты снова касаешься руками пружинящего мохового настила у входа. "
                    "Запас сухого мха для костра и подстилки уже надёжно уложен к твоим вещам. "
                    "От прогретого паром пола веет приятным, долгожданным жаром, который окончательно возвращает подвижность пальцам. "
                    "Каменный порог Тёплой пещеры уже под ногами. "
                    "Бесконечная изнурительная борьба с промороженными штольнями завершена, и надёжное сухое укрытие встречает спасительным уютом."
                )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step39_lookback":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step39_choice", "observation")
        game.story_state = "l6_step39_lookback"
        text = (
            "Ты останавливаешься у лаза и оборачиваешься на пройденную бездну. Внизу клубятся синие тени промороженных штолен. "
            "Теперь весь этот путь обретает смысл: гора говорила с тобой голосом мороза, слабости и страха, требуя сдаться и уснуть на камнях на каждом крутом перегибе. "
            "Это была жестокая проверка воли, где холод пытался сломать рассудок раньше тела. "
            "Но диалог с бездной окончен твоей победой — ты не поверил призрачным голосам и дошёл до спасительного порога."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_ascent_step40":
        return handle_location_6_furry_cave("furry_cave_start", game, uid)

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
