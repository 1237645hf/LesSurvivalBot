# =============================================================================
# ЛОКАЦИЯ 3: Скромная Лощина
# =============================================================================
#
# ПРАВИЛА ЭТОГО ФАЙЛА:
# 1. Здесь лежит ВСЁ, что относится ТОЛЬКО к Локации 3.
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

from modules.combat import (
    start_battle,
    apply_action,
    get_battle_text,
    get_battle_kb,
)
from game_state import get_death_text
from keyboards import get_death_kb


def _player_death(game, reason: str):
    """Штатный обработчик гибели персонажа на L3 со сбросом боя и сюжетного FSM."""
    game.hp = 0
    game.wolf_battle = None
    game.story_state = None
    game.active_story_callback = None
    return get_death_text(game, reason, "Скромная лощина"), get_death_kb()


def handle_location_3_slate_hollow(data: str, game, uid: int):
    """Сюжетная линия Локации 3: Скромная Лощина, убежище у сланцевой печи и каменная плита."""
    text = None
    kb = None

    if data in ("location_enter_boar",):
        game.reset_nav()
        game.current_location = "Скромная лощина"
        game.location_index = 2
        game.location = game.current_location
        game.pre_story_location = game.current_location
        return handle_location_3_slate_hollow("l3_8_ridge", game, uid)

    if data in ("location_enter_3", "slate_hollow_start"):
        game.reset_nav()
        game.current_location = "Скромная лощина"
        game.location_index = 2
        game.location = game.current_location
        game.pre_story_location = game.current_location
        if game.is_story_flag_set("l3_shelter_unlocked"):
            game.campfire_max_durability = 30
            if hasattr(game, "campfires") and isinstance(game.campfires, dict):
                cur_d = getattr(game, "campfire_durability", 0)
                game.campfires["loc_3"] = {
                    "durability": cur_d,
                    "max_durability": 30,
                }
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
        if not game.is_story_flag_set("l3_writings_read"):
            game.set_story_flag("l3_writings_read", True)
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
        if not game.is_story_flag_set("l3_slate_ingot_taken"):
            game.set_story_flag("l3_slate_ingot_taken", True)
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
        if not game.is_story_flag_set("l3_clay_taken"):
            game.set_story_flag("l3_clay_taken", True)
            flask = int(getattr(game, "flask_water", 0) or 0)
            if flask >= 2:
                game.flask_water = max(0, flask - 2)
            elif game.inventory.get("Вода", 0) >= 2:
                game.inventory["Вода"] -= 2
                if game.inventory["Вода"] <= 0:
                    del game.inventory["Вода"]
            elif game.inventory.get("Бутылка воды", 0) >= 1:
                game.inventory["Бутылка воды"] -= 1
                if game.inventory["Бутылка воды"] <= 0:
                    del game.inventory["Бутылка воды"]
                game.inventory["Пустая бутылка"] = game.inventory.get("Пустая бутылка", 0) + 1
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
        if not game.is_story_flag_set("left_clay_for_next"):
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
        if not game.is_story_flag_set("l3_warning_left"):
            game.set_story_flag("l3_warning_left", True)
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
        game.campfire_max_durability = 30
        game.campfire_durability = max(int(getattr(game, "campfire_durability", 0) or 0), 15)
        if not hasattr(game, "campfires") or not isinstance(game.campfires, dict):
            game.campfires = {}
        game.campfires["loc_3"] = {
            "durability": game.campfire_durability,
            "max_durability": 30,
        }
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
        game.campfire_max_durability = 30
        game.campfire_durability = max(int(getattr(game, "campfire_durability", 0) or 0), 15)
        if not hasattr(game, "campfires") or not isinstance(game.campfires, dict):
            game.campfires = {}
        game.campfires["loc_3"] = {
            "durability": game.campfire_durability,
            "max_durability": 30,
        }
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
        game.hp = getattr(game, "hp", 100) - damage
        game.add_log(f"💥 Секач сбил тебя тараном! −{damage} HP.")
        if game.hp <= 0:
            return _player_death(game, f"Матёрый Секач сбил тебя мощным тараном и растоптал на каменных плитах (−{damage} HP).")
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
        game.hp = getattr(game, "hp", 100) - damage
        game.add_log(f"⚠️ Срыв с узкой тропы! −{damage} HP.")
        if game.hp <= 0:
            return _player_death(game, f"Срыв с узкой тропы над ущельем Скромной Лощины оказался смертельным (−{damage} HP).")
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
            game.adjust_narrative_karma("compassion", -1)
            game.adjust_narrative_karma("pragmatism", 3)
            game.adjust_narrative_karma("intervention", 3)
            game.set_story_flag("boar_killed", True)
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
        if not game.is_story_flag_set("l3_boar_looted"):
            game.set_story_flag("l3_boar_looted", True)
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
        game.hp = getattr(game, "hp", 100) - cliff_dmg
        game.add_log(f"⚠️ Острые щепки тропы: −{cliff_dmg} HP.")
        if game.hp <= 0:
            return _player_death(game, f"Острые сланцевые осколки на тропе над солонцом нанесли смертельные раны (−{cliff_dmg} HP).")
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
        game.hp = getattr(game, "hp", 100) - slip_dmg
        game.add_log(f"⚠️ Срыв на узкой тропе: −{slip_dmg} HP.")
        if game.hp <= 0:
            return _player_death(game, f"Обвал скального уступа над ущельем Скромной Лощины стал роковым (−{slip_dmg} HP).")
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
        if not game.is_story_flag_set("l3_cache_taken"):
            game.set_story_flag("l3_cache_taken", True)
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
        if not game.is_story_flag_set("l3_13_kind_done"):
            game.set_story_flag("l3_13_kind_done", True)
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
        if not game.is_story_flag_set("l3_13_greed_done"):
            game.set_story_flag("l3_13_greed_done", True)
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
        if "Просека охотников" not in unlocked:
            unlocked.append("Просека охотников")
            game.unlocked_locations = unlocked
        game.add_log("🗺️ Открыта новая локация: Просека охотников.")
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
        if not game.is_story_flag_set("slate_examine_karma"):
            game.set_story_flag("slate_examine_karma", True)
            game.adjust_narrative_karma("observation", 3)
        text = (
            "Ты осматриваешь стены — сланец холодный на ощупь, с тонкими прожилками.\n"
            "Сланцевая Лощина — место, где камень живёт своей жизнью."
        )
        kb = get_main_kb(game)
    elif data == "slate_climb":
        if not game.is_story_flag_set("slate_climb_karma"):
            game.set_story_flag("slate_climb_karma", True)
            game.adjust_narrative_karma("intervention", 2)
        text = "Ты взбираешься по ступеням, ведущим к верхней палате."
        kb = get_main_kb(game)
    elif data == "slate_rest":
        if not game.is_story_flag_set("slate_rest_karma"):
            game.set_story_flag("slate_rest_karma", True)
            game.adjust_narrative_karma("compassion", 1)
        text = "Ты отдыхаешь на прохладном сланце."
        kb = get_main_kb(game)
    elif data == "slate_end":
        game.story_state = None
        kb = get_main_kb(game)

    terminal_callbacks = {
        "l3_6_finalize",
        "l3_11a_win",
        "l3_13_kind",
        "l3_13_greed",
        "l3_flee_to_camp",
        "slate_examine",
        "slate_climb",
        "slate_rest",
        "slate_end",
        "back",
    }
    is_main_menu = (
        kb == get_main_kb(game)
        or data in terminal_callbacks
        or getattr(game, "hp", 100) <= 0
    )
    if is_main_menu:
        game.active_story_callback = None
        if getattr(game, "hp", 100) <= 0 or data in ("l3_6_finalize", "slate_end", "back", "slate_examine", "slate_climb", "slate_rest") or (data in ("location_enter_3", "slate_hollow_start") and game.is_story_flag_set("l3_ridge_completed")):
            game.story_state = None
    elif text is not None:
        game.active_story_callback = data

    return text, kb
