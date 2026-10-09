# =============================================================================
# ЛОКАЦИЯ 4: Просека Охотников
# =============================================================================
#
# ПРАВИЛА ЭТОГО ФАЙЛА:
# 1. Здесь лежит ВСЁ, что относится ТОЛЬКО к Локации 4.
# 2. Никакого кода других локаций.
# 3. Общие хелперы импортируются только из story.common (пока можно оставить прямые импорты).
# 4. Не создавать отдельные .txt файлы.
#
# Структура:
#   1. Локальные константы (если есть)
#   2. Все handle_* функции этой локации
# =============================================================================

import random
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

from modules.combat.engine import _calc_player_damage
from game_state import get_death_text
from keyboards import get_death_kb


def _player_death(game, reason: str):
    """Штатный обработчик гибели персонажа на L4 со сбросом боевой сессии и FSM."""
    game.hp = 0
    game.slug_battle = None
    game.wolf_pack_battle = None
    game.story_state = None
    game.active_story_callback = None
    return get_death_text(game, reason, "Просека охотников"), get_death_kb()


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
        game.current_location = "Просека охотников"
        game.location_index = 3
        game.location = game.current_location
        game.pre_story_location = game.current_location
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Просека охотников" not in unlocked:
            unlocked.append("Просека охотников")
            game.unlocked_locations = unlocked

        if "l4_entered_day" not in game.story_flags:
            game.story_flags["l4_entered_day"] = getattr(game, "day", 1)

        # Если вся локация 4 полностью завершена (все 3 главы пройдены): мирная стоянка
        if game.is_story_flag_set("l4_fully_completed"):
            game.active_story_callback = None
            game.slug_battle = None
            game.wolf_pack_battle = None
            text = (
                "Ты выходишь на широкую Просеку Охотников.\n\n"
                "Просека теперь тиха и безопасна. Старые кострища укрыты опавшей хвоей, "
                "а на дозорном помосте тихо колышется сосновый навес. "
                "Впереди ждёт спуск к Яру Слаймов."
            )
            kb = get_main_kb(game)
            return text, kb

        # Если сюжетная ветка сейчас в процессе прохождения (есть story_state):
        if getattr(game, "story_state", None) and str(game.story_state).startswith("l4_"):
            return handle_location_4_hunters_glade(game.story_state, game, uid)

        # Если сюжет оленя уже завершён: спокойная стоянка между главами
        if game.is_story_flag_set("l4_completed"):
            game.active_story_callback = None
            game.slug_battle = None
            game.wolf_pack_battle = None
            text = (
                "Ты выходишь на широкую Просеку Охотников.\n\n"
                "Старые кострища укрыты опавшей хвоей. Костяные пластинки больше не трещат на ветру, "
                "а тропа свободна для исследования и установки охотничьих ловушек."
            )
            kb = get_main_kb(game)
            return text, kb

        # Если сюжет ещё не запущен (нужно пожить 2 ночи): спокойное обживание стоянки
        if not game.is_story_flag_set("l4_started"):
            game.active_story_callback = None
            game.slug_battle = None
            game.wolf_pack_battle = None
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
            game.hp = max(0, getattr(game, "hp", 100) - trap_dmg)
            game.add_log(f"⚠️ Ловушка на просеке: −{trap_dmg} HP.")
            if game.hp <= 0:
                return _player_death(game, "Неосторожный шаг привёл к срабатыванию смертоносной ловушки.")
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
            game.hp = max(0, getattr(game, "hp", 100) - deer_dmg)
            game.add_log(f"⚠️ Удар оленя: −{deer_dmg} HP.")
            game.adjust_narrative_karma("compassion", 1)
            if game.hp <= 0:
                return _player_death(game, "Отчаянный удар копыта раненого оленя оказался смертельным.")
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
        if not game.is_story_flag_set("l4_3b1_plates_karma"):
            game.set_story_flag("l4_3b1_plates_karma", True)
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
        if not game.is_story_flag_set("l4_3b2_shake_karma"):
            game.set_story_flag("l4_3b2_shake_karma", True)
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
            game.adjust_narrative_karma("compassion", 3)
        game.set_story_flag("deer_freed", True)
        game.set_story_flag("helped_deer", True)

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
        if not game.is_story_flag_set("l4_3c_ignore_karma"):
            game.set_story_flag("l4_3c_ignore_karma", True)
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
        if not game.is_story_flag_set("l4_left_warning_karma"):
            game.set_story_flag("l4_left_warning_karma", True)
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
                game.slug_battle = None
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
                game.hp = max(0, game.hp - 5)
                if game.hp <= 0:
                    return _player_death(game, "Едкая слизь прожгла одежду и растворила плоть.")
                b["last_log"] = "💥 Удар посохом: −11 HP. Кислотный сок шипит и растворяет оболочку!\n⚠️ Слизень прыгает на тебя: −5 HP (игнор брони)."
        else:
            b["slug_hp"] = max(1, min(30, b.get("slug_hp", 30) - 1 + 1))
            game.hp = max(0, game.hp - 5)
            if game.hp <= 0:
                return _player_death(game, "Едкая слизь прожгла одежду и растворила плоть.")
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
        game.hp = max(0, game.hp - 5)
        if game.hp <= 0:
            return _player_death(game, "Едкая слизь прожгла оборону и растворила плоть.")
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
        game.hp = max(0, game.hp - 5)
        if game.hp <= 0:
            return _player_death(game, "Слизень атаковал тебя, пока ты отвлёкся на осмотр гриба.")
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
        game.hp = max(0, game.hp - dmg)
        if game.hp <= 0:
            return _player_death(game, "Слизень атаковал тебя, пока ты экспериментировал с грибом.")
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

        game.hp = max(0, game.hp - 5)
        if game.hp <= 0:
            return _player_death(game, "Слизень атаковал тебя, пока ты покрывал древко соком гриба.")
        b["last_log"] = "🧪 Бирюзовый сок с шипением разъедает грязь и покрывает древко пенящейся коркой!\n⚠️ Слизень прыгает на тебя: −5 HP (игнор брони)."
        game.slug_battle = b
        return _render_slug_battle(game)

    # Экран 4: Чёрный след на камне
    elif data == "l4_ch1_4_stone_mark":
        game.slug_battle = None
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
        game.slug_battle = None
        game.story_state = None
        game.set_story_flag("l4_ch1_cliff_completed", True)
        game.story_flags["l4_ch2_sleeps"] = game.story_flags.get("l4_sleep_count", 0)
        game.story_flags["l4_ch2_day"] = getattr(game, "day", 1)
        text = (
            "Ты отходишь от гиблой кромки. Сейчас скинуть броню ты не готов: в лесу полно волков, "
            "и доспех дарит чувство защиты и уверенность в завтрашнем дне.\n\n"
            "Но для спуска в этот овраг потребуется защита из прочной кожи, которая не боится кислоты и не тянет ко дну. "
            "С этими мыслями ты возвращаешься в лагерь.\n"
            "──────────\n"
            "Яр Слаймов (Опасно, прохода нет)"
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

        game.hp = max(0, game.hp - total_wolf_dmg)
        if game.hp <= 0:
            return _player_death(game, "Молодая стая волков растерзала тебя на просеке.")
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

        game.hp = max(0, game.hp - total_wolf_dmg)
        if game.hp <= 0:
            return _player_death(game, "Молодая стая волков сломила твою оборону и растерзала тебя.")
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
        game.wolf_pack_battle = None
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
        has_branch = game.inventory.get("Ветка", 0) >= 1
        has_leather = game.inventory.get("Кожа", 0) >= 1
        buttons = []
        if has_branch and has_leather:
            buttons.append([InlineKeyboardButton(text="Поднять доспех сюда", callback_data="l4_ch3_2a_lift")])
        else:
            missing = []
            if not has_branch:
                missing.append("1 ветка")
            if not has_leather:
                missing.append("1 кожа")
            buttons.append([InlineKeyboardButton(text=f"🔒 Поднять доспех (нет: {', '.join(missing)})", callback_data="l4_ch3_2_fate_no_res")])
        buttons.append([InlineKeyboardButton(text="Не поднимать, осмотреться", callback_data="l4_ch3_3_table")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Предупреждение о нехватке ресурсов для люльки
    elif data == "l4_ch3_2_fate_no_res":
        missing = []
        if game.inventory.get("Ветка", 0) < 1:
            missing.append("1 ветка")
        if game.inventory.get("Кожа", 0) < 1:
            missing.append("1 кожа")
        miss_str = ", ".join(missing) if missing else "материалы"
        text = (
            f"⚠️ Не хватает материалов для подъёма доспеха: необходимо {miss_str}.\n\n"
            "Сланцевые пластины слишком тяжелы, чтобы поднимать их голыми руками по старому канату без люльки. "
            "Придётся осмотреть помост налегке."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Не поднимать, осмотреться", callback_data="l4_ch3_3_table")],
            [InlineKeyboardButton(text="« Назад к выбору", callback_data="l4_ch3_2_fate")],
        ])

    # Экран 2а: Схрон на помосте (ветка люльки)
    elif data == "l4_ch3_2a_lift":
        if game.inventory.get("Ветка", 0) < 1 or game.inventory.get("Кожа", 0) < 1:
            return handle_location_4_hunters_glade("l4_ch3_2_fate_no_res", game, uid)
        game.story_state = "l4_ch3_2a_lift"
        game.set_story_flag("l4_armor_lifted", True)
        if not game.is_story_flag_set("l4_ch3_2a_lift_karma"):
            game.set_story_flag("l4_ch3_2a_lift_karma", True)
            game.adjust_narrative_karma("intervention", 2)
        game.inventory["Ветка"] -= 1
        if game.inventory["Ветка"] <= 0:
            del game.inventory["Ветка"]
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
        if not game.is_story_flag_set("l4_ch3_4_upgrade_karma"):
            game.set_story_flag("l4_ch3_4_upgrade_karma", True)
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
        if not game.is_story_flag_set("l4_ch3_5a_tree_karma"):
            game.set_story_flag("l4_ch3_5a_tree_karma", True)
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
        game.slug_battle = None
        game.wolf_pack_battle = None
        game.story_state = None
        game.set_story_flag("l4_fully_completed", True)
        if not game.is_story_flag_set("l4_schema_received"):
            game.set_story_flag("l4_schema_received", True)
            game.inventory["Схема кожаной брони"] = game.inventory.get("Схема кожаной брони", 0) + 1
            game.add_log("В рюкзак добавлена схема кожаной брони.")
        unlocked = getattr(game, "unlocked_locations", []) or []
        if "Яр Слаймов" not in unlocked:
            unlocked.append("Яр Слаймов")
            game.unlocked_locations = unlocked
        text = (
            "Ты стоишь на опушке перед спуском в овраг, глядя на заходящее солнце. На душе смешались светлая грусть "
            "и тихая надежда наконец-то выбраться из этого заколдованного круга.\n\n"
            "Сланцевая броня осталась позади — верный страж, спасший тебя от волков. Тебя наполняет уверенность, "
            "что только сшив новый кожаный доспех, ты сможешь спуститься к оврагу, к едкой бездне Яра Слаймов. "
            "Просека Охотников пройдена. Твой путь лежит дальше."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏕 В лагерь", callback_data="back")]
        ])

    # Управление active_story_callback
    terminators = ("l4_8_final", "l4_9_exit", "l4_ch1_5_doubt", "l4_ch2_4_lesson", "l4_ch3_6_epilogue", "back")
    if data in terminators or getattr(game, "hp", 100) <= 0:
        game.active_story_callback = None
    elif text is not None:
        game.active_story_callback = "l4_1_entry" if data in ("hunters_glade_start", "location_enter_4") else data

    return text, kb
