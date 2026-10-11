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


def handle_location_6_furry_cave(data, game, uid):
    """Обработать события на локации 'Мохнатая Пещера' (L6)."""
    text = None
    kb = None

    # При взаимодействии с Тёплой пещерой активируем шелтер и рецепты
    if data.startswith("furry_") or data in ("l6_ascent_step40", "l6_ascent_step30"):
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
            "Внутри — три хороших куска выделанного меха, выкройки тёплой одежды и короткая надпись,\n"
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

    # ──────────────────────────────────────────────────────────────────────────
    # СЮЖЕТНЫЕ ОКНА ПОДЪЁМА (ИССЛЕДОВАНИЯ 1–10 ИЗ 40)
    # ──────────────────────────────────────────────────────────────────────────

    # ИССЛЕДОВАНИЕ 2: Панорама и структура пещеры (Интерактивный хаб)
    elif data == "l6_step2_hub":
        game.story_state = "l6_step2_hub"
        text = (
            "Сланцевый зев горы сразу за зловонным Яром распахивается колоссальным, обжитым пространством. "
            "Стены покрыты слоем въевшейся копоти, пол вытесан широкими плитами, стёртыми до блеска подошвами. "
            "Даже следы едкой болотной жижи у порога не скрывают главного: здесь годами подолгу останавливались люди. "
            "По выбитым в полу желобам дождевые потоки с шумом уходят вглубь залы. Воздух сухой и морозный, но хранит запах старого жилья. "
            "Впереди открывается развилка древнего перевалочного узла."
        )
        buttons = []
        if not game.is_story_flag_set("l6_step2_water_seen"):
            buttons.append([InlineKeyboardButton(text="🌊 Осмотреть сток воды", callback_data="l6_step2_water")])
        if not game.is_story_flag_set("l6_step2_people_seen"):
            buttons.append([InlineKeyboardButton(text="🏛️ Осмотреть следы людей", callback_data="l6_step2_people")])
        if not game.is_story_flag_set("l6_step2_chasm_seen"):
            buttons.append([InlineKeyboardButton(text="🔍 Осмотреть разлом", callback_data="l6_step2_chasm")])
        buttons.append([InlineKeyboardButton(text="➡️ Начать подъём", callback_data="l6_ascent_continue")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    elif data == "l6_step2_water":
        game.set_story_flag("l6_step2_water_seen", True)
        game.story_state = "l6_step2_water"
        text = (
            "Глубокие каменные желоба приводят к краю колоссального естественного раскола. "
            "Вода с глухим шумом срывается в узкую расщелину, уходящую в ледяную бездну горы, откуда доносится далёкое эхо падающих струй. "
            "Поток уходит глубоко под землю, оставляя верхние каменные ярусы совершенно сухими. "
            "Внизу — лишь сырость и непроглядный мрак, туда пути нет. Дорога отсекает провал и уходит круто ввысь."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="l6_step2_hub")]
        ])

    elif data == "l6_step2_people":
        game.set_story_flag("l6_step2_people_seen", True)
        game.story_state = "l6_step2_people"
        text = (
            "При взгляде вверх открывается циклопический размах древней работы. "
            "Это не дикая расселина, а обустроенный перевалочный пункт. Вдоль широкого тракта видны массивные балки крепей, "
            "площадки для грузов и ряды круглых гнёзд под смоляные факелы. Слизни из яра сюда не лезут: от морозного сквозняка "
            "их студенистая плоть мгновенно коченеет. По этим ступеням регулярно поднимались люди с грузом."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="l6_step2_hub")]
        ])

    elif data == "l6_step2_chasm":
        game.set_story_flag("l6_step2_chasm_seen", True)
        game.story_state = "l6_step2_chasm"
        text = (
            "На широких террасах царит мёртвая тишина. Ни звука, ни следов недавнего костра, ни дозорных. "
            "Всё замерло, словно люди оставили этот пункт в один момент. Острый интерес сдавливает виски: "
            "что здесь произошло и куда ушли строители этих колоссальных залов? Ответ кроется только выше, "
            "куда упрямо ведёт выбитый в скале тракт. Нужно подниматься и собственными глазами выяснить правду."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="l6_step2_hub")]
        ])

    # ИССЛЕДОВАНИЕ 4: Развилка и шатающийся уступ
    elif data == "l6_step4_main":
        game.story_state = "l6_step4_main"
        text = (
            "Крутой подъём выводит на широкую площадку скального тракта. Крайняя плита над обрывом надломилась: "
            "под подошвой сланцевый уступ глухо скрежещет и опасно покачивается над бездной при каждом неосторожном шаге. "
            "Но у самой гранитной стены, под защитным каменным козырьком, взгляд натыкается на рукотворный схрон: "
            "под плоским куском сланца бережно уложен сухой кремень и пучок плотного пещерного мха. "
            "Кто-то намеренно оставил здесь запас для путников, поднимающихся сквозь стужу."
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
            "по которому можно уверенно ступать дальше без риска сорваться."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step4_inspect":
        if not game.is_story_flag_set("l6_step4_loot_taken"):
            game.set_story_flag("l6_step4_loot_taken", True)
            game.inventory["Кремень"] = game.inventory.get("Кремень", 0) + 1
            game.inventory["Пещерный мох"] = game.inventory.get("Пещерный мох", 0) + 1
            game.add_log("Получено: Кремень ×1, Пещерный мох ×1")
        game.story_state = "l6_step4_inspect"
        text = (
            "Пальцы выгребают кремень и сухой мох, убирая находку на самое дно походного мешка. Расщелина в скале остаётся абсолютно голой. "
            "Ты можешь положить что-то своё взамен для того, кто пойдёт следом и будет замерзать на этой тропе, "
            "или просто двинуться дальше со всей добычей — всё равно в этих мёртвых ледяных скалах никто не увидит твоего поступка "
            "и не осудит за жадность."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Положить из инвентаря", callback_data="l6_step4_leave_gift")],
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_step4_take_all")],
        ])

    elif data == "l6_step4_leave_gift":
        game.adjust_narrative_karma("compassion", 1)
        game.set_story_flag("l6_step4_gift_left", True)
        gifted_item = None
        for item in ["Жареное мясо", "Мясо", "Сушёное мясо", "Ягоды", "Лесная ягода", "Красная ягода", "Печёные ягоды", "Жареные грибы"]:
            if game.inventory.get(item, 0) > 0:
                game.inventory[item] -= 1
                if game.inventory[item] <= 0:
                    del game.inventory[item]
                gifted_item = item
                break
        game.story_state = "l6_step4_leave_gift"
        text = (
            "Кремень отправляется в карман куртки, а взамен на сухой камень аккуратно ложится сытная порция вяленого пайка из личных запасов. "
            "Расщелина снова надёжно прикрывается сланцевой плиткой от осыпи. Неписаный закон стоянки соблюдён: путник берёт лишь необходимое, "
            "оставляя следующему шанс выжить в морозном буране. От этого взвешенного поступка внутри разливается тихое спокойствие."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step4_take_all":
        if not game.is_story_flag_set("l6_step4_gift_left"):
            game.adjust_narrative_karma("pragmatism", 1)
            game.set_story_flag("l6_step4_took_all", True)
        game.story_state = None
        game.active_story_callback = None
        if hasattr(game, "reset_nav"):
            game.reset_nav()
        return game.get_ui(), get_main_kb(game)

    # ИССЛЕДОВАНИЕ 7: Пролом над бездной и стадо
    elif data in ("l6_step7_main", "l6_ascent_step7"):
        game.story_state = "l6_step7_main"
        text = (
            "Огромный зал распахивается широким боковым проломом. Сквозь разрыв в скале открывается вид на пройденный путь: "
            "далеко внизу серым морем простирается лес, за ним чернеет ручей и чаша Яра Слаймов под свинцовым пологом туч. "
            "Ледяной вихрь со свистом врывается в проход, обжигая лицо морозной крупой. Прямо на карнизе у обрыва стоят массивные горные бараны. "
            "Их свалявшаяся шерсть покрыта инеем. Они жуют серый лишайник и смотрят в упор. Они не боятся. Совсем. И это очень странно."
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
            "Выдержав долгую паузу, старый баран делает шаг назад к монолитной стене скалы, спокойно освобождая узкий проход мимо стада."
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
            "Напряжение в теле отступает, и дыхание выравнивается: спокойствие горного зверя придаёт уверенности продолжать путь дальше."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step7_scare":
        game.adjust_narrative_karma("intervention", 1)
        game.story_state = "l6_step7_scare"
        text = (
            "Удар посоха о камень выбивает сноп искр и гулкое эхо. Старый вожак резко прядает ушами, глухо стучит копытом по базальту "
            "и отступает к краю обрыва. Остальные бараны молча жмутся к монолиту, провожая пришельца настороженным взглядом. "
            "Проход очищен силой, но в воздухе повисает колючее напряжение: животные больше не доверяют и чутко следят за каждым движением."
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
                "Подъём сужается, превращаясь в узкую ледяную теснину. Морозный сквозняк здесь бьёт с такой яростной силой, что леденеет дыхание. "
                "Котёнок забился глубоко под куртку, прижавшись к самой груди, и мелко дрожит всем тельцем. "
                "Ты греешь его онемевшими пальцами и собственным дыханием или сам греешься о его спасительный тёплый комок — уже не разобрать. "
                "Ясно одно: здесь нельзя медлить. Нужно либо дойти до конца на одном дыхании, либо повернуть назад в лагерь и готовиться лучше."
            )
        else:
            text = (
                "Подъём сужается, превращаясь в продуваемую насквозь узкую ледяную теснину. Морозный шквал бьёт навстречу с такой силой, "
                "что стужа обжигает лёгкие до хрипоты, а пальцы в рукавицах теряют чувствительность. "
                "Одиночество в этой ледяной пасти давит на виски не меньше ветра. Мысль предельно ясна: здесь нельзя медлить. "
                "Этот ледяной тракт нужно либо одолеть до конца на одном дыхании, либо повернуть назад в лагерь, чтобы основательно утеплиться и подготовиться."
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
            "Прямо над ним в породу глубоко врезан наш главный символ: три ровные вертикальные полосы, перечёркнутые горизонтальной линией. "
            "Стоянка давно заброшена, но хранит следы долгого расчёта."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Осмотреть ларчик", callback_data="l6_step10_box")],
            [InlineKeyboardButton(text="🔍 Осмотреть за ларчиком", callback_data="l6_step10_behind")],
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")],
        ])

    elif data == "l6_step10_behind":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step10_behind_seen", True)
        game.story_state = "l6_step10_behind"
        text = (
            "Взгляд скользит мимо костяной шкатулки и цепляется за узкую трещину за обледенелым очагом. "
            "Там, под слоем прозрачного наста, виден аккуратно выбитый в камне счётчик шагов и стрелка в обход ледопада. "
            "Тот, кто обустраивал этот рубеж, берёг не только припасы, но и оставил точный ориентир для следующего подъёма. "
            "Внимание к скрытым деталям стоянки даёт ясное понимание пути без лишнего риска."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step10_box":
        if not game.is_story_flag_set("l6_step10_loot_taken"):
            game.set_story_flag("l6_step10_loot_taken", True)
            game.inventory["Древесный уголь"] = game.inventory.get("Древесный уголь", 0) + 1
            game.inventory["Бинт"] = game.inventory.get("Бинт", 0) + 1
            game.add_log("Получено: Древесный уголь ×1, Бинт ×1")
        game.story_state = "l6_step10_box"
        text = (
            "Крышка ларчика поддаётся, и ты забираешь плотный брусок сухого древесного угля и чистые походные бинты, "
            "пряча их в глубину мешка. Костяная шкатулка остаётся пустой. Ты можешь оставить что-то своё взамен для тех, "
            "кто выберется на этот продуваемый уступ на грани сил, или сразу уйти дальше со всей добычей — всё равно никто и никогда об этом не узнает."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Положить из инвентаря", callback_data="l6_step10_leave_gift")],
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_step10_take_all")],
        ])

    elif data == "l6_step10_leave_gift":
        game.adjust_narrative_karma("compassion", 1)
        game.set_story_flag("l6_step10_gift_left", True)
        gifted_item = None
        for item in ["Жареное мясо", "Мясо", "Сушёное мясо", "Ягоды", "Лесная ягода", "Красная ягода", "Печёные ягоды", "Жареные грибы"]:
            if game.inventory.get(item, 0) > 0:
                game.inventory[item] -= 1
                if game.inventory[item] <= 0:
                    del game.inventory[item]
                gifted_item = item
                break
        game.story_state = "l6_step10_leave_gift"
        text = (
            "Брусок древесного угля отправляется в карман куртки, а взамен на сухую ткань ложится сытная порция вяленого пайка из собственных запасов. "
            "Крышка ларчика плотно встаёт на место. Неписаный закон честной стоянки соблюдён: если кто-то выберется сюда на грани истощения, "
            "этот тайник спасёт ему жизнь. От осознания правильного выбора внутри разливается спокойное, согревающее чувство человечности."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step10_take_all":
        if not game.is_story_flag_set("l6_step10_gift_left"):
            game.adjust_narrative_karma("pragmatism", 1)
            game.set_story_flag("l6_step10_took_all", True)
        game.story_state = None
        game.active_story_callback = None
        if hasattr(game, "reset_nav"):
            game.reset_nav()
        return game.get_ui(), get_main_kb(game)

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
            "Чтобы продвинуться выше, приходится выбирать: тратить время на поиск скрытого обхода, "
            "рискнуть здоровьем и силой обрушить завал ради безопасного пути или быстро проскользнуть по самому краю без лишних остановок."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти скрытый обход", callback_data="l6_step13_observe")],
            [InlineKeyboardButton(text="🔨 Сбить опасные глыбы", callback_data="l6_step13_break")],
            [InlineKeyboardButton(text="🚶 Быстро пройти по кромке", callback_data="l6_step13_edge")],
        ])

    elif data == "l6_step13_observe":
        game.adjust_narrative_karma("observation", 1)
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
            from keyboards import get_death_kb, get_death_text
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
            "Не тратя времени на расчистку чужой дороги и долгие поиски, ты прижимаешься к скале и быстро проскальзываешь по узкому наружному краю плиты. "
            "За спиной с сухим треском осыпается ледяная крошка, но ноги уже выносят тело за опасную черту. "
            "Драгоценные силы и дыхание сбережены, а риск остался позади. Личный практический расчёт позволяет продвигаться к цели без лишних задержек."
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
            "Металлическая ковка барабана не тронута ржавчиной, а в узлах механизма ещё угадывается инженерный расчёт."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Подойти к механизму", callback_data="l6_step15_detail")]
        ])

    elif data == "l6_step15_detail":
        game.story_state = "l6_step15_detail"
        text = (
            "Вблизи становятся видны подробности заброшенного узла. "
            "Сбоку на раме раскачивается сорванный стальной трос: от порывов ветра он угрожающе бьётся о балки и может в любой момент сорвать клеть вниз, завалив проход. "
            "На барабане намертво заклинило тормозную колодку, оббитую широкой полосой толстой выделанной кожи. "
            "Сам же сложный механизм шестерней и противовесов цел, но требует внимательного изучения. Предстоит решить, что делать с находкой."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Изучить схему передач", callback_data="l6_step15_observe")],
            [InlineKeyboardButton(text="⛓️ Зафиксировать трос в пазу", callback_data="l6_step15_cable")],
            [InlineKeyboardButton(text="🎒 Срезать кожу с тормоза", callback_data="l6_step15_leather")],
        ])

    elif data == "l6_step15_observe":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step15_choice", "observation")
        game.story_state = "l6_step15_observe"
        text = (
            "Взгляд внимательно скользит по зубьям шестерней, противовесам и схеме натяжения тросов. "
            "Становится ясно, как устроена система балансировки: противовес позволял поднимать огромный вес без лишних усилий. "
            "Понимание инженерного замысла помогает отыскать скрытую боковую лестницу для рабочих, выбитую прямо в монолите скалы за барабаном. "
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
            "а прочная дубовая рама послужит надёжным упором для каждого, кто рискнёт подниматься следом."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step15_leather":
        game.adjust_narrative_karma("pragmatism", 1)
        game.set_story_flag("l6_step15_choice", "pragmatism")
        if not game.is_story_flag_set("l6_step15_loot_taken"):
            game.set_story_flag("l6_step15_loot_taken", True)
            game.inventory["Кожа"] = game.inventory.get("Кожа", 0) + 1
            game.add_log("Получено: Кожа ×1")
        game.story_state = "l6_step15_leather"
        text = (
            "Ты не тратишь время на починку мертвого механизма, а подходишь к тормозному ободу ворота. "
            "Острый нож аккуратно срезает широкую полосу толстой выделанной кожи, служившую обшивкой колодок (+1 Кожа). "
            "Материал отлично сохранился на морозе: прочный ремень сразу отправляется в рюкзак. "
            "В условиях выживания практическая польза важнее чужих механизмов — хорошая кожа всегда пойдёт на починку обуви и брони."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    # ИССЛЕДОВАНИЕ 17: Скользкий карниз и переходящая сумка
    elif data == "l6_step17_main":
        game.story_state = "l6_step17_main"
        text = (
            "Тропа выходит на продуваемый всеми ветрами открытый скальный карниз над пропастью. "
            "Здесь отчётливо видны следы давнего несчастного случая: расколотый деревянный посох, сорванные камни "
            "и глубокая царапина на скользком уступе, уходящая прямо в бездну. Кто-то оступился на обледенелом повороте. "
            "В каменной расщелине у самой кромки обрыва застряла брошенная кожаная сумка путника. "
            "Этот опасный карниз не прощает спешки и заставляет внимательно оценить каждый свой шаг."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Осмотреть сумку у обрыва", callback_data="l6_step17_bag")],
            [InlineKeyboardButton(text="👁️ Осмотреть место срыва", callback_data="l6_step17_observe")],
            [InlineKeyboardButton(text="🔨 Выложить каменный бортик", callback_data="l6_step17_wall")],
        ])

    elif data == "l6_step17_observe":
        game.adjust_narrative_karma("observation", 1)
        game.set_story_flag("l6_step17_choice", "observation")
        game.story_state = "l6_step17_observe"
        text = (
            "Взгляд методично изучает царапины на камне и границы наледи. "
            "Причина беды очевидна: тонкий, невидимый глазом слой прозрачного льда на самом перегибе карниза. "
            "Но если присмотреться к рельефу уступов, становится видна безопасная дуга обхода ближе к монолитной стене, "
            "где порода шероховатая и сухая. Наблюдательность позволяет точно запомнить опасный участок и впредь уверенно проходить поворот без риска сорваться."
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
        text = (
            "Пальцы отгибают промёрзший кожаный клапан. На застёжках видны чужие узлы: до тебя здесь уже бывали другие, превратив сумку в дорожный схрон. "
            "Внутри обнаруживается кусок плотного меха и завёрнутое в бересту жареное мясо. "
            "Ты достаёшь находку на свет — больше в карманах ничего нет. "
            "Можно оставить взамен часть своего пайка для тех, кто пойдёт следом, или убрать всё в рюкзак и продолжить путь без лишних сантиментов."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Положить из инвентаря", callback_data="l6_step17_leave_gift")],
            [InlineKeyboardButton(text="➡️ Забрать всё и уйти", callback_data="l6_step17_take_all")],
        ])

    elif data == "l6_step17_leave_gift":
        game.adjust_narrative_karma("compassion", 1)
        game.set_story_flag("l6_step17_gift_left", True)
        if not game.is_story_flag_set("l6_step17_loot_taken"):
            game.set_story_flag("l6_step17_loot_taken", True)
            game.inventory["Мех"] = game.inventory.get("Мех", 0) + 1
            game.inventory["Жареное мясо"] = game.inventory.get("Жареное мясо", 0) + 1
            game.add_log("Получено: Мех ×1, Жареное мясо ×1")
        gifted_item = None
        for item in ["Жареное мясо", "Мясо", "Сырое мясо", "Печёные ягоды", "Жареные грибы", "Ягоды", "Лесная ягода", "Красная ягода"]:
            if game.inventory.get(item, 0) > 0:
                game.inventory[item] -= 1
                if game.inventory[item] <= 0:
                    del game.inventory[item]
                gifted_item = item
                break
        game.story_state = "l6_step17_leave_gift"
        text = (
            "Мех и порция мяса отправляются в глубину мешка, а на сухую бересту взамен ложится сытный припас из собственных запасов. "
            "Клапан сумки снова плотно застёгивается. Схрон готов поддержать любого, кто выберется на этот опасный карниз на пределе сил. "
            "От соблюдения закона честной стоянки внутри разливается согревающее спокойствие: даже на краю пропасти удаётся сохранить человечность и заботу о других."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step17_take_all":
        if not game.is_story_flag_set("l6_step17_gift_left"):
            game.adjust_narrative_karma("pragmatism", 1)
            game.set_story_flag("l6_step17_took_all", True)
        if not game.is_story_flag_set("l6_step17_loot_taken"):
            game.set_story_flag("l6_step17_loot_taken", True)
            game.inventory["Мех"] = game.inventory.get("Мех", 0) + 1
            game.inventory["Жареное мясо"] = game.inventory.get("Жареное мясо", 0) + 1
            game.add_log("Получено: Мех ×1, Жареное мясо ×1")
        game.story_state = None
        game.active_story_callback = None
        if hasattr(game, "reset_nav"):
            game.reset_nav()
        return game.get_ui(), get_main_kb(game)

    # ИССЛЕДОВАНИЕ 20: Извилистые штольни и морозный морок
    elif data == "l6_step20_main":
        game.story_state = "l6_step20_main"
        text = (
            "По ощущениям и пройденным шагам сквозь эти бесконечные извилистые залы и каменные завалы можно было бы дважды подняться на вершину и спуститься обратно. "
            "Но петляющие ледяные штольни упрямо кружат в недрах горы, и под ногами лишь середина подъёма. "
            "Воздух здесь становится разреженным и обжигающе сухим. "
            "Сквозняк, прорываясь сквозь трещины свода, звучит глухим ритмичным гулом: в шуме ветра чудятся шаги за спиной, звон пряжек и сдавленный шёпот. "
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
            "Морок бессилен перед холодным анализом. Иллюзия рассеивается без следа, оставляя в ушах лишь ровный гул горного сквозняка и кристальную ясность ума."
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
            "Наваждение резко спадает, разбившись о глухую решимость дойти до конца."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data in ("l6_ascent_step40", "l6_ascent_step30"):
        unlock_warm_cave_shelter(game)
        game.story_state = "furry_cave_start"
        text = (
            "Сквозняк внезапно стихает. Протиснувшись сквозь ледяную щель, герой попадает в замкнутый грот: "
            "сухо, на стенах развешаны шкуры, пахнет дымом старого очага, под ногами мягкий мох. "
            "То самое спасительное убежище.\n\n"
            "Открыта постоянная база: Тёплая пещера!\n\n"
            "Что будешь делать?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Осмотреть пещеру", callback_data="furry_examine")],
            [InlineKeyboardButton(text="🔥 Подойти к очагу", callback_data="furry_warm")],
            [InlineKeyboardButton(text="💤 Сразу лечь отдохнуть", callback_data="furry_sleep")],
            [InlineKeyboardButton(text="🚶 Уйти", callback_data="furry_leave")],
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
