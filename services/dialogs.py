"""
services/dialogs.py — Обработка текстовых диалоговых состояний (FSM).

Экспортирует:
    process_text_input(message, bot_ctx) — основной обработчик текстовых сообщений
        в состояниях story_state: WAITING_FOR_PET_NAME, WAITING_FOR_FUEL_COUNT,
        WAITING_FOR_DROP_QUANTITY.

Зависимости передаются через bot_ctx (словарь) чтобы избежать circular imports:
    bot_ctx["last_active_msg_id"]   — dict {uid: message_id}
    bot_ctx["safe_edit_message"]    — coroutine
    bot_ctx["safe_delete_message"]  — coroutine
    bot_ctx["update_or_send_message"] — coroutine
    bot_ctx["format_game_text"]     — функция
    bot_ctx["inventory_inline_kb"]  — клавиатура инвентаря
    bot_ctx["get_campfire_kb"]      — функция(game)
"""

import logging
from typing import Optional, Tuple, Dict, Any, List
from aiogram import types

from game_state import Game
from services.database import save_game


import re

_ALLOWED_NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁё0-9_]{1,20}$")


def _has_emoji(text: str) -> bool:
    """Проверить наличие эмодзи (символов вне ASCII + CJK + кириллица и основные диакритики)."""
    # Эмодзи занимают кодовые точки выше U+2600 и в специальных диапазонах
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return bool(emoji_pattern.search(text))


async def handle_waiting_for_character_name(
    uid: int,
    chat_id: int,
    text: str,
    message: types.Message,
    game: Game,
    bot_ctx: dict,
) -> bool:
    """Обработать ввод имени персонажа при старте новой игры. Возвращает True если обработано."""
    if game.story_state != "WAITING_FOR_CHARACTER_NAME":
        return False

    await bot_ctx["safe_delete_message"](chat_id, message.message_id)

    async def _reply_error(err_text: str):
        prompt = (
            "📛 Введи имя своего персонажа:\n"
            "• Только буквы, цифры, _\n"
            "• Пробелы запрещены (используй _ вместо пробела)\n"
            "• Эмодзи запрещены\n"
            "• Макс. 20 символов\n\n"
            f"❌ {err_text}"
        )
        msg_id = bot_ctx["last_active_msg_id"].get(uid)
        if msg_id:
            await bot_ctx["safe_edit_message"](chat_id, msg_id, prompt, None)
        else:
            await bot_ctx["update_or_send_message"](chat_id, uid, prompt, None)

    if not text or not text.strip():
        await _reply_error("Имя не может быть пустым.")
        return True

    name = text.strip()

    if " " in name:
        await _reply_error("Пробелы запрещены. Используй _ вместо пробела.")
        return True

    if _has_emoji(name):
        await _reply_error("Эмодзи в имени запрещены.")
        return True

    if len(name) > 20:
        await _reply_error(f"Слишком длинное имя ({len(name)} символов, макс. 20).")
        return True

    if not _ALLOWED_NAME_RE.match(name):
        await _reply_error("Разрешены только буквы (русские/латинские), цифры и _.")
        return True

    # Имя принято
    game.player_name = name
    game.character_name = name
    game.is_name_set = True
    game.story_state = None
    game.add_log(f"Имя персонажа: {name}. Удачи в лесу!")

    save_ok = True
    try:
        save_ok = bool(save_game(uid, game))
        from services.database import is_mongo_connected
        if not is_mongo_connected():
            logging.warning(f"Предупреждение: имя {name} сохранено в in-memory fallback (нет подключения к MongoDB).")
    except Exception as exc:
        save_ok = False
        logging.error(f"Критическая ошибка сохранения персонажа {name} ({uid}): {exc}", exc_info=True)

    from keyboards import get_main_kb
    warning_suffix = ""
    if not save_ok:
        warning_suffix = "\n\n⚠️ Внимание: не удалось сохранить персонажа в облачную базу данных! Прогресс может быть утерян при перезагрузке сервера."

    text_out = (
        f"Имя принято: {name}!\n\n"
        + game.get_ui()
        + warning_suffix
    )
    msg_id = bot_ctx["last_active_msg_id"].get(uid)
    if msg_id:
        await bot_ctx["safe_edit_message"](chat_id, msg_id, text_out, get_main_kb(game))
    else:
        await bot_ctx["update_or_send_message"](chat_id, uid, text_out, get_main_kb(game))

    return True


async def handle_waiting_for_pet_name(
    uid: int,
    chat_id: int,
    text: str,
    message: types.Message,
    game: Game,
    bot_ctx: dict,
) -> bool:
    """Обработать ввод имени питомца. Возвращает True если состояние обработано."""
    if game.story_state != "WAITING_FOR_PET_NAME":
        return False
    await bot_ctx["safe_delete_message"](chat_id, message.message_id)

    async def _reply_pet_error(err_text: str):
        prompt = (
            "🐾 Введи кличку своего питомца:\n"
            "• Только буквы, цифры, _\n"
            "• Пробелы запрещены (используй _ вместо пробела)\n"
            "• Эмодзи запрещены\n"
            "• Макс. 20 символов\n\n"
            f"❌ {err_text}"
        )
        msg_id = bot_ctx["last_active_msg_id"].get(uid)
        if msg_id:
            await bot_ctx["safe_edit_message"](chat_id, msg_id, prompt, None)
        else:
            await bot_ctx["update_or_send_message"](chat_id, uid, prompt, None)

    if not text or not text.strip():
        await _reply_pet_error("Кличка не может быть пустой.")
        return True

    name = text.strip()

    if "\n" in name or "\r" in name:
        await _reply_pet_error("Переносы строк запрещены.")
        return True

    if " " in name:
        await _reply_pet_error("Пробелы запрещены. Используй _ вместо пробела.")
        return True

    if _has_emoji(name):
        await _reply_pet_error("Эмодзи в кличке питомца запрещены.")
        return True

    if len(name) > 20:
        await _reply_pet_error(f"Слишком длинная кличка ({len(name)} символов, макс. 20).")
        return True

    if not _ALLOWED_NAME_RE.match(name):
        await _reply_pet_error("Разрешены только буквы (русские/латинские), цифры и _.")
        return True

    game.companion_name = name
    game.equipment["pet"] = name
    if not game.is_story_flag_set("saved_kitten"):
        game.adjust_narrative_karma("compassion", 2)
    game.set_story_flag("saved_kitten")
    game.set_story_flag("has_pet")
    game.set_story_flag("l1_completed")
    if "l1_completed_day" not in game.story_flags:
        game.story_flags["l1_completed_day"] = getattr(game, "day", 1)
    game.story_state = None
    game.active_story_callback = None
    game.add_log(f"У вас появился питомец: {name}")

    final_text = (
        "Ты смотришь на маленькое существо у себя на руках.\n"
        f"«{name}», — произносишь ты вслух, и понимаешь что нашёл себе нового друга.\n"
        "Котёнок поднимает голову, будто услышал и запомнил.\n"
        "Уходя от пня, ты чувствуешь, как он начинает тихо, почти не слышно мурчать...\n\n"
        "Вибрация проходит сквозь твою грудь — слабая, но живая.\n"
        "Впервые за долгое время в этом лесу становится чуть теплее."
    )
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Дальше", callback_data="story_next")]
    ])

    msg_id = bot_ctx["last_active_msg_id"].get(uid)
    if msg_id:
        await bot_ctx["safe_edit_message"](
            chat_id, msg_id, bot_ctx["format_game_text"](final_text, game), kb
        )
    else:
        await bot_ctx["update_or_send_message"](chat_id, uid, final_text, kb)

    save_game(uid, game)
    return True


async def handle_waiting_for_fuel_count(
    uid: int,
    chat_id: int,
    text: str,
    message: types.Message,
    game: Game,
    bot_ctx: dict,
) -> bool:
    """Обработать ввод количества топлива для костра. Возвращает True если состояние обработано."""
    if game.story_state != "WAITING_FOR_FUEL_COUNT":
        return False
    if not text:
        return True

    await bot_ctx["safe_delete_message"](chat_id, message.message_id)

    get_campfire_kb = bot_ctx["get_campfire_kb"]

    async def _reply_error(err_text: str):
        kb = get_campfire_kb(game)
        msg_id = bot_ctx["last_active_msg_id"].get(uid)
        if msg_id:
            await bot_ctx["safe_edit_message"](chat_id, msg_id, err_text, kb)
        else:
            await bot_ctx["update_or_send_message"](chat_id, uid, err_text, kb)
        save_game(uid, game)

    try:
        fuel_amount = int(text.strip())
        if fuel_amount <= 0:
            await _reply_error("⚠️ Введите число больше нуля!")
            return True
    except ValueError:
        await _reply_error("⚠️ Введите корректное положительное число!")
        return True

    fuel_type = game.story_flags.get("fuel_item", "sticks")
    inv = game.inventory
    needed_fire = max(0, game.campfire_max_durability - game.campfire_durability)
    if needed_fire <= 0:
        game.story_state = None
        game.story_flags.pop("fuel_item", None)
        await _reply_error(f"🔥 Костёр уже разгорелся до максимума ({game.campfire_max_durability}/{game.campfire_max_durability})!")
        return True

    if fuel_type == "bark":
        spent = (fuel_amount // 2) * 2
        if spent == 0:
            await _reply_error("⚠️ Нужно чётное число коры, минимум 2")
            return True
        bark_avail = inv.get("Кусок коры", 0) + inv.get("Кора", 0)
        if bark_avail < spent:
            spent = (bark_avail // 2) * 2
            if spent == 0:
                await _reply_error(f"⚠️ Недостаточно коры в инвентаре (доступно: {bark_avail} шт.). Нужно чётное число, минимум 2.")
                return True
        if spent > needed_fire * 2:
            spent = needed_fire * 2

        to_deduct = spent
        for k in ("Кусок коры", "Кора"):
            if to_deduct <= 0:
                break
            have = inv.get(k, 0)
            take = min(have, to_deduct)
            inv[k] -= take
            if inv[k] <= 0:
                del inv[k]
            to_deduct -= take

        fire_added = spent // 2
        game.campfire_durability += fire_added
        game.story_state = None
        game.story_flags.pop("fuel_item", None)
        game.nav_stack = ["main", "campfire"]
        game.add_log(f"🧱 Подкинуто: Кора ×{spent} (+{fire_added} 🔥). Огонь: {game.campfire_durability}/{game.campfire_max_durability}.")
        action_header = f"🧱 Подкинуто: Кора ×{spent} (+{fire_added} огня)"
    else:
        sticks_avail = inv.get("Ветка", 0) + inv.get("Палки", 0) + inv.get("Палка", 0)
        if sticks_avail <= 0:
            await _reply_error("⚠️ У вас нет палок/веток в инвентаре!")
            return True
        to_use = min(fuel_amount, sticks_avail, needed_fire)
        to_deduct = to_use
        for k in ("Ветка", "Палки", "Палка"):
            if to_deduct <= 0:
                break
            have = inv.get(k, 0)
            take = min(have, to_deduct)
            inv[k] -= take
            if inv[k] <= 0:
                del inv[k]
            to_deduct -= take

        game.campfire_durability += to_use
        game.story_state = None
        game.story_flags.pop("fuel_item", None)
        game.nav_stack = ["main", "campfire"]
        game.add_log(f"🪵 Подкинуто: Палки ×{to_use}. Огонь: {game.campfire_durability}/{game.campfire_max_durability}.")
        action_header = f"🪵 Подкинуто: Ветка ×{to_use} (+{to_use} огня)"

    from main import get_campfire_text
    result_text = get_campfire_text(game, action_header=action_header)
    kb = get_campfire_kb(game)
    msg_id = bot_ctx["last_active_msg_id"].get(uid)
    if msg_id:
        await bot_ctx["safe_edit_message"](chat_id, msg_id, result_text, kb)
    else:
        await bot_ctx["update_or_send_message"](chat_id, uid, result_text, kb)

    save_game(uid, game)
    return True


async def handle_waiting_for_drop_quantity(
    uid: int,
    chat_id: int,
    text: str,
    message: types.Message,
    game: Game,
    bot_ctx: dict,
) -> bool:
    """Обработать ввод количества предметов для выброса. Возвращает True если обработано."""
    if game.story_state != "WAITING_FOR_DROP_QUANTITY":
        return False
    if not text:
        return True

    await bot_ctx["safe_delete_message"](chat_id, message.message_id)

    inventory_inline_kb = bot_ctx["inventory_inline_kb"]

    item_name = game.story_flags.get("drop_item_name")
    if not item_name:
        game.story_state = None
        while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
            game.nav_stack.pop()
        kb = inventory_inline_kb
        msg_id = bot_ctx["last_active_msg_id"].get(uid)
        if msg_id:
            await bot_ctx["safe_edit_message"](chat_id, msg_id, game.get_inventory_text(), kb)
        else:
            await bot_ctx["update_or_send_message"](chat_id, uid, game.get_inventory_text(), kb)
        save_game(uid, game)
        return True

    current_count = game.inventory.get(item_name, 0)

    async def _reply_error(err_text: str):
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="drop_qty_cancel")]
        ])
        prompt = f"Введите количество «{item_name}» для выброса:\n(Доступно: {current_count} шт.)\n\n{err_text}"
        msg_id = bot_ctx["last_active_msg_id"].get(uid)
        if msg_id:
            await bot_ctx["safe_edit_message"](chat_id, msg_id, prompt, kb)
        else:
            await bot_ctx["update_or_send_message"](chat_id, uid, prompt, kb)
        save_game(uid, game)

    try:
        drop_amount = int(text)
        if drop_amount <= 0:
            await _reply_error("❌ Введите число больше нуля!")
            return True
    except ValueError:
        await _reply_error("❌ Введите корректное положительное число!")
        return True

    if current_count <= 0:
        game.story_state = None
        game.story_flags.pop("drop_item_name", None)
        while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
            game.nav_stack.pop()
        result_text = f"❌ У вас нет «{item_name}» в инвентаре!\n\n{game.get_inventory_text()}"
        msg_id = bot_ctx["last_active_msg_id"].get(uid)
        if msg_id:
            await bot_ctx["safe_edit_message"](chat_id, msg_id, result_text, inventory_inline_kb)
        else:
            await bot_ctx["update_or_send_message"](chat_id, uid, result_text, inventory_inline_kb)
        save_game(uid, game)
        return True

    if drop_amount > current_count:
        drop_amount = current_count

    while len(game.nav_stack) > 1 and game.nav_stack[-1] in ("drop", "drop_qty"):
        game.nav_stack.pop()

    game.inventory[item_name] -= drop_amount
    if game.inventory[item_name] <= 0:
        del game.inventory[item_name]
    game.add_log(f"🗑️ Выброшено: {item_name} ×{drop_amount}.")
    game.story_state = None
    game.story_flags.pop("drop_item_name", None)

    result_text = f"Удалено: {item_name} ×{drop_amount}.\n\n{game.get_inventory_text()}"
    msg_id = bot_ctx["last_active_msg_id"].get(uid)
    if msg_id:
        await bot_ctx["safe_edit_message"](chat_id, msg_id, result_text, inventory_inline_kb)
    else:
        await bot_ctx["update_or_send_message"](chat_id, uid, result_text, inventory_inline_kb)

    save_game(uid, game)
    return True


async def handle_waiting_for_cook_count(
    uid: int,
    chat_id: int,
    text: str,
    message: types.Message,
    game: Game,
    bot_ctx: dict,
) -> bool:
    """Обработать ввод количества порций для готовки на костре. Возвращает True если состояние обработано."""
    if game.story_state != "WAITING_FOR_COOK_COUNT":
        return False
    if not text:
        return True

    await bot_ctx["safe_delete_message"](chat_id, message.message_id)

    from modules.cooking import get_recipe_for_id, get_recipe_max_count, cook_portions, format_recipe_card
    from keyboards import get_campfire_recipe_view_kb, get_campfire_kb

    recipe_id = game.story_flags.get("cook_recipe_id")
    if not recipe_id or not get_recipe_for_id(recipe_id):
        game.story_state = None
        game.story_flags.pop("cook_recipe_id", None)
        game.nav_stack = ["main", "campfire"]
        from main import get_campfire_text
        text_out = get_campfire_text(game)
        kb = get_campfire_kb(game)
        msg_id = bot_ctx["last_active_msg_id"].get(uid)
        if msg_id:
            await bot_ctx["safe_edit_message"](chat_id, msg_id, text_out, kb)
        else:
            await bot_ctx["update_or_send_message"](chat_id, uid, text_out, kb)
        save_game(uid, game)
        return True

    recipe = get_recipe_for_id(recipe_id)
    max_count = get_recipe_max_count(game, recipe_id)

    async def _reply_error(err_text: str):
        kb = get_campfire_recipe_view_kb(recipe_id, max_count)
        prompt = f"⚠️ {err_text}\n\n{format_recipe_card(recipe_id, game)}"
        msg_id = bot_ctx["last_active_msg_id"].get(uid)
        if msg_id:
            await bot_ctx["safe_edit_message"](chat_id, msg_id, prompt, kb)
        else:
            await bot_ctx["update_or_send_message"](chat_id, uid, prompt, kb)

    try:
        qty = int(text.strip())
        if qty <= 0:
            await _reply_error("Введите число больше нуля!")
            return True
    except ValueError:
        await _reply_error("Введите корректное положительное число!")
        return True

    if max_count <= 0:
        await _reply_error("Недостаточно ингредиентов для приготовления!")
        return True

    to_cook = min(qty, max_count)
    cooked, msg = cook_portions(game, recipe_id, to_cook)
    if cooked <= 0:
        await _reply_error(msg)
        return True

    game.story_state = None
    game.story_flags.pop("cook_recipe_id", None)
    game.nav_stack = ["main", "campfire"]
    game.add_log(msg)

    from main import get_campfire_text
    header = f"✅ {msg}"
    text_out = get_campfire_text(game, action_header=header)
    kb = get_campfire_kb(game)

    msg_id = bot_ctx["last_active_msg_id"].get(uid)
    if msg_id:
        await bot_ctx["safe_edit_message"](chat_id, msg_id, text_out, kb)
    else:
        await bot_ctx["update_or_send_message"](chat_id, uid, text_out, kb)

    save_game(uid, game)
    return True


async def handle_waiting_for_tablet_note(
    uid: int,
    chat_id: int,
    text: str,
    message: types.Message,
    game: Game,
    bot_ctx: dict,
) -> bool:
    """Обработать ввод надписи на каменной плите (лимит 50 символов)."""
    if game.story_state != "WAITING_FOR_TABLET_NOTE":
        return False

    await bot_ctx["safe_delete_message"](chat_id, message.message_id)

    raw_text = message.text.strip() if message.text else ""
    if not raw_text:
        return True

    from keyboards import get_tablet_edit_kb

    # Проверка на длину надписи (ровно 50 символов)
    if len(raw_text) > 50:
        import html
        escaped_text = html.escape(raw_text)
        warn_text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>Слишком длинная надпись ({len(raw_text)}/50 символов)!</b>\n"
            "Каменная плита не вместит столько слов.\n\n"
            f"<code>{escaped_text}</code>\n\n"
            "👆 Нажми на текст в рамке выше, чтобы скопировать и сократить его до 50 символов.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        kb = get_tablet_edit_kb()
        msg_id = bot_ctx["last_active_msg_id"].get(uid)
        if msg_id:
            await bot_ctx["safe_edit_message"](chat_id, msg_id, warn_text, kb, parse_mode="HTML")
        else:
            await bot_ctx["update_or_send_message"](chat_id, uid, warn_text, kb, parse_mode="HTML")
        return True

    # Текст валиден (<= 50 символов) — формируем подпись автора
    player_name = getattr(game, "character_name", None) or getattr(game, "player_name", None) or "Безымянный"
    companion = getattr(game, "companion_name", None)
    has_pet = bool(companion) or game.is_story_flag_set("has_pet") or (game.equipment.get("pet") and game.equipment.get("pet") != "Пусто")
    if has_pet:
        pet_name = companion if companion else "Кот"
        author = f"Бродяга {player_name} и {pet_name}"
    else:
        author = f"Бродяга {player_name}"

    from services.database import save_tablet_note
    save_tablet_note(uid, author, raw_text)

    game.story_state = None
    game.add_log(f"📜 Ты высек на каменной плите: «{raw_text}»")
    save_game(uid, game)

    render_fn = bot_ctx.get("render_tablet_view")
    if render_fn:
        await render_fn(chat_id, uid, page=1, notice=f"✨ Твоя надпись успешно высечена на плите!\n«{raw_text}»\n— {author}")
    return True


async def process_text_input(
    uid: int,
    chat_id: int,
    text: str,
    message: types.Message,
    game: Game,
    bot_ctx: dict,
) -> bool:
    """
    Главная точка входа для диалоговых состояний.
    Пробует каждый обработчик по очереди.
    Возвращает True если одно из состояний было обработано.
    """
    handlers = [
        handle_waiting_for_character_name,
        handle_waiting_for_pet_name,
        handle_waiting_for_fuel_count,
        handle_waiting_for_drop_quantity,
        handle_waiting_for_cook_count,
        handle_waiting_for_tablet_note,
    ]
    for handler in handlers:
        try:
            if await handler(uid, chat_id, text, message, game, bot_ctx):
                return True
        except Exception as exc:
            logging.exception(f"Ошибка в диалог-обработчике {handler.__name__} для {uid}: {exc}")
    return False


# ──────────────────────────────────────────────────────────────────────────────
# ПРИВЕТСТВИЕ И СТАРТОВЫЙ ЭКРАН
# ──────────────────────────────────────────────────────────────────────────────
GUIDE_TEXT = (
    "Добро пожаловать в лес выживания!\n\n"
    "Краткий гайд:\n"
    "❤️ Здоровье\n"
    "🍖 Сытость\n"
    "💧 Жажда\n"
    "⚡ Действия на день\n\n"
    "Карма поможет выбраться.\n\n"
    "Попробуй выжить, друг мой..."
)


def format_start_character_text(game: Any) -> str:
    hero_name = getattr(game, "character_name", None) or "Выживший"
    day = getattr(game, "day", 1)
    hp = getattr(game, "hp", 100)
    hunger = getattr(game, "hunger", 100)
    thirst = getattr(game, "thirst", 100)
    ap = getattr(game, "ap", 0)
    return (
        "Ты медленно открываешь глаза среди вековых деревьев и холодного тумана. "
        "В голове пустота, в памяти — лишь неясные обрывки прошлого... Но тело помнит тропы этого леса.\n\n"
        f"👤 Выживший: **{hero_name}**\n"
        f"📅 День в лесу: **{day}**\n"
        f"❤️ Здоровье: **{hp}/100**\n"
        f"🍖 Сытость: **{hunger}/100**\n"
        f"💧 Жажда: **{thirst}/100**\n"
        f"⚡ Энергия: **{ap} AP**"
    )


def check_character_name_required(game: Any) -> Optional[str]:
    """Проверяет, требуется ли ввод имени персонажа перед продолжением игры."""
    if game is None:
        return None
    if getattr(game, "story_state", None) == "WAITING_FOR_CHARACTER_NAME" or not getattr(game, "is_name_set", False):
        return (
            "📛 Сначала введи имя своего персонажа:\n"
            "• Только буквы, цифры, _\n"
            "• Пробелы запрещены (используй _ вместо пробела)\n"
            "• Эмодзи запрещены\n"
            "• Макс. 20 символов"
        )
    return None


def is_session_callback(data: str) -> bool:
    """Проверяет, относится ли callback к старту/перезапуску игры."""
    return data in (
        "new_game",
        "start_new_game",
        "confirm_new_game",
        "start_new_game_confirmed",
        "cancel_new_game",
        "load_game",
    )


def handle_session_callback(
    data: str,
    game: Any,
    uid: int,
    games_dict: Optional[dict] = None,
) -> Tuple[Optional[str], Optional[Any]]:
    """Обрабатывает callback-и старта новой игры, подтверждения, отмены и загрузки.

    Все импорты клавиатур и зависимостей выполняются локально внутри функции.
    """
    from services.database import load_game, save_game
    from keyboards import (
        get_confirm_new_game_kb,
        get_start_new_game_kb,
        get_start_resume_kb,
    )

    if data in ("new_game", "start_new_game"):
        existing = load_game(uid)
        if existing is None and games_dict is not None:
            existing = games_dict.get(uid)
        elif existing is None and game:
            existing = game
        if existing is not None and getattr(existing, "is_name_set", False):
            hero_name = existing.character_name or "Выживший"
            day = getattr(existing, "day", 1)
            text = (
                "⚠️ **Внимание!** Вы собираетесь начать с чистого листа.\n"
                f"Персонаж **{hero_name}** ({day}-й день) и весь накопленный инвентарь будут безвозвратно удалены!\n\n"
                "Вы уверены?"
            )
            kb = get_confirm_new_game_kb()
            return text, kb

        new_game = Game()
        if games_dict is not None:
            games_dict[uid] = new_game
        new_game.story_state = "WAITING_FOR_CHARACTER_NAME"
        save_game(uid, new_game)
        text = (
            "📛 Введи имя своего персонажа:\n"
            "• Только буквы, цифры, _\n"
            "• Пробелы запрещены (используй _ вместо пробела)\n"
            "• Эмодзи запрещены\n"
            "• Макс. 20 символов"
        )
        return text, None

    elif data == "confirm_new_game":
        existing = load_game(uid)
        if existing is None and games_dict is not None:
            existing = games_dict.get(uid)
        elif existing is None and game:
            existing = game
        hero_name = (existing.character_name if existing else None) or "Выживший"
        day = getattr(existing, "day", 1) if existing else 1
        text = (
            "⚠️ **Внимание!** Вы собираетесь начать с чистого листа.\n"
            f"Персонаж **{hero_name}** ({day}-й день) и весь накопленный инвентарь будут безвозвратно удалены!\n\n"
            "Вы уверены?"
        )
        kb = get_confirm_new_game_kb()
        return text, kb

    elif data == "start_new_game_confirmed":
        new_game = Game()
        if games_dict is not None:
            games_dict[uid] = new_game
        new_game.story_state = "WAITING_FOR_CHARACTER_NAME"
        save_game(uid, new_game)
        text = (
            "📛 Введи имя своего персонажа:\n"
            "• Только буквы, цифры, _\n"
            "• Пробелы запрещены (используй _ вместо пробела)\n"
            "• Эмодзи запрещены\n"
            "• Макс. 20 символов"
        )
        return text, None

    elif data == "cancel_new_game":
        existing = load_game(uid)
        if existing is None and games_dict is not None:
            existing = games_dict.get(uid)
        elif existing is None and game:
            existing = game
        if existing and getattr(existing, "is_name_set", False):
            hero_name = existing.character_name or "Выживший"
            text = format_start_character_text(existing)
            kb = get_start_resume_kb(hero_name)
        else:
            text = GUIDE_TEXT
            kb = get_start_new_game_kb()
        return text, kb

    elif data == "load_game":
        loaded = load_game(uid)
        if loaded is None and games_dict is not None:
            loaded = games_dict.get(uid)
        if loaded is None:
            text = "Сохранение не найдено. Начните новую игру!"
            kb = get_start_new_game_kb()
            return text, kb

        if loaded.story_state == "WAITING_FOR_CHARACTER_NAME" or not getattr(loaded, "is_name_set", False):
            text = (
                "📛 Введи имя своего персонажа:\n"
                "• Только буквы, цифры, _\n"
                "• Пробелы запрещены (используй _ вместо пробела)\n"
                "• Эмодзи запрещены\n"
                "• Макс. 20 символов"
            )
            return text, None

        if games_dict is not None:
            games_dict[uid] = loaded

        if getattr(loaded, "hp", 100) <= 0:
            loaded.hp = 0
            loaded.active_story_callback = None
            save_game(uid, loaded)
            from game_state import get_death_text
            from keyboards import get_death_kb
            text = get_death_text(loaded)
            kb = get_death_kb()
            return text, kb

        from story.location_stories import handle_story
        if getattr(loaded, "story_state", None) == "WAITING_FOR_PET_NAME" or getattr(loaded, "active_story_callback", None) in ("pet_take", "waiting_pet_name"):
            has_named_pet = loaded.is_story_flag_set("has_pet") and bool(
                loaded.equipment.get("pet") or (getattr(loaded, "companion_name", "") not in (None, "", "Кот", "Котёнок"))
            )
            if has_named_pet:
                loaded.active_story_callback = None
                loaded.story_state = None
                save_game(uid, loaded)
            else:
                res_text, res_kb = handle_story("waiting_pet_name", loaded, uid)
                if res_text is not None:
                    save_game(uid, loaded)
                    return res_text, res_kb

        if getattr(loaded, "active_story_callback", None):
            cb = loaded.active_story_callback
            res_text, res_kb = handle_story(cb, loaded, uid)
            if res_text is not None:
                save_game(uid, loaded)
                return res_text, res_kb

        from keyboards import get_main_kb
        text = loaded.get_ui()
        kb = get_main_kb(loaded)
        return text, kb

    return None, None


# ──────────────────────────────────────────────────────────────────────────────
# КАМЕННАЯ ПЛИТА (ЗАПИСИ ВЫЖИВШИХ)
# ──────────────────────────────────────────────────────────────────────────────
def format_tablet_notes_text(
    notes: list, page: int = 1, page_size: int = 5, notice: Optional[str] = None
) -> Tuple[str, int]:
    """Форматирует страницу записей каменной плиты."""
    total_notes = len(notes)
    total_pages = max(1, (total_notes + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start = (page - 1) * page_size
    page_notes = notes[start:start + page_size]

    lines = []
    if notice:
        lines.append(f"{notice}\n")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("📜 КАМЕННАЯ ПЛИТА У ПЕЧИ")
    lines.append("━━━━━━━━━━━━━━━━━━━━\n")
    lines.append("На гладкой поверхности сланца высечены слова тех, кто проходил здесь до тебя:\n")

    for i, note in enumerate(page_notes, start=start + 1):
        txt = note.get("text", "")
        author = note.get("author", "Бродяга (неизвестен)")
        lines.append(f"{i}. «{txt}»\n   — {author}\n")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📖 Страница {page} из {total_pages}")

    return "\n".join(lines), total_pages


def is_tablet_callback(data: str) -> bool:
    """Проверяет, относится ли callback к каменной плите."""
    return data in ("tablet_notes_view", "tablet_notes_edit") or data.startswith("tablet_page:")


def handle_tablet_callback(
    data: str,
    game: Any,
    uid: int,
) -> Tuple[Optional[str], Optional[Any]]:
    """Обрабатывает просмотр, пагинацию и переход к редактированию надписи на каменной плите.

    Все импорты клавиатур и зависимостей выполняются локально внутри функции.
    """
    from keyboards import get_tablet_notes_kb, get_tablet_edit_kb
    from services.database import get_tablet_notes

    if data == "tablet_notes_view":
        if game:
            game.story_state = None
            game.nav_stack = ["main", "tablet_notes"]
        all_notes = get_tablet_notes()
        text, total_pages = format_tablet_notes_text(all_notes, page=1, page_size=5)
        kb = get_tablet_notes_kb(1, total_pages)
        return text, kb

    elif data.startswith("tablet_page:"):
        parts = data.split(":")
        p = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        if game:
            game.story_state = None
            game.nav_stack = ["main", "tablet_notes"]
        all_notes = get_tablet_notes()
        text, total_pages = format_tablet_notes_text(all_notes, page=p, page_size=5)
        kb = get_tablet_notes_kb(p, total_pages)
        return text, kb

    elif data == "tablet_notes_edit":
        if game:
            game.story_state = "WAITING_FOR_TABLET_NOTE"
        edit_text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✏️ НАДПИСЬ НА КАМЕННОЙ ПЛИТЕ\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Напиши в чат короткое послание, которое увидят другие выжившие.\n\n"
            "⚠️ Ограничение: не более 50 символов!\n\n"
            "(Напиши текст сообщением в чат или нажми «Отмена»)\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        kb = get_tablet_edit_kb()
        return edit_text, kb

    return None, None


