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
            "Сланцевый зев горы распахивается широким, гулким пространством. "
            "Стены покрыты слоем въевшейся копоти, пол вытесан тяжёлыми плитами, стёртыми до блеска подошвами. "
            "Даже следы едкой болотной жижи у порога не скрывают очевидного: здесь годами подолгу останавливались люди. "
            "По выбитым в полу желобам дождевые потоки с шумом уходят вглубь залы. Воздух сухой и морозный, но хранит едва уловимый запах жилья. "
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
            "При взгляде вверх открывается суровый размах старой работы. "
            "Это не дикая расселина, а надёжно обустроенный перевалочный пункт. Вдоль широкого тракта видны массивные балки крепей, "
            "площадки для грузов и ряды круглых гнёзд под смоляные факелы. Слизни из яра сюда не лезут: от морозного сквозняка "
            "их студенистая плоть мгновенно коченеет. По этим каменным ступеням регулярно поднимались люди с тяжёлым грузом."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Назад", callback_data="l6_step2_hub")]
        ])

    elif data == "l6_step2_chasm":
        game.set_story_flag("l6_step2_chasm_seen", True)
        game.story_state = "l6_step2_chasm"
        text = (
            "На широких террасах царит мёртвая тишина. Ни звука, ни следов недавнего костра, ни дозорных. "
            "Всё замерло, словно люди оставили этот пункт в один момент. Острый холод сдавливает виски: "
            "что здесь произошло и куда ушли строители этих каменных залов? Ответ кроется только выше, "
            "куда упрямо ведёт выбитый в скале тракт. Нужно подниматься и собственными глазами выяснить правду о вершине."
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
            "Но у самой гранитной стены, под каменным козырьком, взгляд натыкается на рукотворный схрон: "
            "под плоским куском сланца бережно уложен кремень и пучок сухого пещерного мха. "
            "Кто-то оставил здесь запас для путников, поднимающихся сквозь стужу."
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
        if not game.is_story_flag_set("l6_step4_loot_taken"):
            game.set_story_flag("l6_step4_loot_taken", True)
            game.inventory["Кремень"] = game.inventory.get("Кремень", 0) + 1
            game.inventory["Пещерный мох"] = game.inventory.get("Пещерный мох", 0) + 1
            game.add_log("Получено: Кремень ×1, Пещерный мох ×1")
        game.story_state = "l6_step4_inspect"
        text = (
            "Пальцы выгребают кремень и сухой пещерный мох, убирая находку на самое дно походного мешка. Расщелина в скале остаётся абсолютно голой. "
            "Ты можешь положить что-то своё взамен для того, кто пойдёт следом и будет замерзать на этой тропе, "
            "или просто двинуться дальше со всей добычей — всё равно в этих мёртвых ледяных скалах никто не увидит твоего поступка "
            "и не осудит за расчётливый шаг."
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
            "оставляя следующему шанс выжить в морозном буране. От этого спокойного поступка внутри разливается тихое, согревающее тепло."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Идти дальше", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step4_take_all":
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
            "Напряжение в теле отступает, и дыхание выравнивается: спокойствие горного зверя придаёт уверенности продолжать трудный путь сквозь ледяные залы."
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
                "Подъём сужается, превращаясь в узкую ледяную теснину. Морозный сквозняк здесь бьёт с такой яростной силой, что леденеет дыхание. "
                "Котёнок забился глубоко под куртку, прижавшись к самой груди, и мелко дрожит всем тельцем. "
                "Ты греешь его онемевшими пальцами и собственным дыханием или сам греешься о его спасительный тёплый комок — уже не разобрать. "
                "Ясно одно: здесь нельзя медлить. Нужно либо одолеть тракт, либо повернуть назад в лагерь."
            )
        else:
            text = (
                "Подъём сужается, превращаясь в продуваемую насквозь узкую ледяную теснину. Морозный шквал бьёт навстречу с такой силой, "
                "что стужа обжигает лёгкие до хрипоты, а пальцы в рукавицах теряют чувствительность. "
                "Одиночество в этой ледяной пасти давит на виски не меньше ветра. Мысль предельно ясна: здесь нельзя медлить. "
                "Этот ледяной тракт нужно либо одолеть до конца, либо повернуть назад в лагерь, чтобы основательно подготовиться."
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
            "Прямо над ним в породу глубоко врезан наш главный знак: три ровные вертикальные полосы, перечёркнутые чертой. "
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
        if not game.is_story_flag_set("l6_step10_loot_taken"):
            game.set_story_flag("l6_step10_loot_taken", True)
            game.inventory["Древесный уголь"] = game.inventory.get("Древесный уголь", 0) + 1
            game.inventory["Бинт"] = game.inventory.get("Бинт", 0) + 1
            game.add_log("Получено: Древесный уголь ×1, Бинт ×1")
        game.story_state = "l6_step10_box"
        text = (
            "Крышка ларчика поддаётся с сухим треском. Внутри лежат брусок сухого древесного угля и чистые походные бинты, "
            "аккуратно завёрнутые в промасленную ткань. Ты забираешь находку в рюкзак. "
            "Рядом в золе лежит сломанная игла и обрывок ремня: тот, кто ночевал здесь, перевязывал глубокую рану перед тем, как двинуться дальше во тьму. "
            "Холод сохранил его вещи в полной неприкосновенности. Пора продолжать подъём."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
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
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
        ])

    elif data == "l6_step10_take_all":
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
        if not game.is_story_flag_set("l6_step15_loot_taken"):
            game.set_story_flag("l6_step15_loot_taken", True)
            game.inventory["Кожа"] = game.inventory.get("Кожа", 0) + 1
            game.add_log("Получено: Кожа ×1")
        game.story_state = "l6_step15_leather"
        text = (
            "Ты не тратишь время на починку мертвого механизма, а подходишь к тормозному ободу ворота. "
            "Острый нож аккуратно срезает широкую полосу толстой выделанной кожи, служившую обшивкой колодок (+1 Кожа). "
            "Материал отлично сохранился на морозе: прочный ремень сразу отправляется в рюкзак. "
            "В условиях выживания практическая польза важнее чужих механизмов — хорошая кожа всегда пойдёт на починку обуви и одежды."
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
            "Пальцы отгибают промёрзший кожаный клапан. Внутри сумки обнаруживается кусок плотного меха и завёрнутое в бересту жареное мясо (+1 Мех, +1 Жареное мясо). "
            "Еда замёрзла в камень, но пригодна в пищу. Больше в карманах ничего нет — лишь пустой медный котелок. "
            "Глядя в чернеющую под карнизом пропасть, откуда доносится глухой свист ветра, ты прячешь находку в рюкзак. "
            "Гора забрала одного, но отдала его припасы другому."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⛺ Вернуться в лагерь", callback_data="l6_ascent_continue")]
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
            from keyboards import get_death_kb, get_death_text
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
        if not game.is_story_flag_set("l6_step33_loot_taken"):
            game.set_story_flag("l6_step33_loot_taken", True)
            game.inventory["Кремень"] = game.inventory.get("Кремень", 0) + 1
            game.add_log("Получено: Кремень ×1")
        game.story_state = "l6_step33_search"
        text = (
            "Ты подходишь к стене и внимательно осматриваешь трещину вокруг старого страховочного крюка. "
            "Тщательный поиск приносит плоды: в скрытом углублении за скальным выступом обнаруживается завернутый в грубую холстину отличный осколок минерала (+1 Кремень). "
            "Находка сразу отправляется в рюкзак: в горах огонь решает всё. Аккуратно перешагнув разлом по настилу, ты с полезной добычей продолжаешь восхождение."
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
        if not game.is_story_flag_set("l6_step36_loot_taken"):
            game.set_story_flag("l6_step36_loot_taken", True)
            game.inventory["Пещерный мох"] = game.inventory.get("Пещерный мох", 0) + 1
            game.add_log("Получено: Пещерный мох ×1")
        game.story_state = "l6_step36_investigate"
        text = (
            "Ты упрямо направляешься к источнику потрескивающего звука в боковом ответвлении. "
            "Раздвинув звенящие ледяные сосульки, ты обнаруживаешь не костёр, а удивительное природное чудо: "
            "сквозь промороженную корку скалы пробивается живой зеленоватый нарост (+1 Пещерный мох). "
            "Нежное растение источает едва заметное тепло. Заботливо убрав мох в мешок, ты возвращаешься на основной путь с ценной находкой."
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
        if not game.is_story_flag_set("l6_step39_loot_taken"):
            game.set_story_flag("l6_step39_loot_taken", True)
            game.inventory["Пещерный мох"] = game.inventory.get("Пещерный мох", 0) + 1
            game.add_log("Получено: Пещерный мох ×1")
        game.story_state = "l6_step39_moss"
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

    elif data in ("l6_ascent_step40", "l6_ascent_step30"):
        unlock_warm_cave_shelter(game)
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
