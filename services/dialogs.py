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


    from keyboards import get_main_kb
    text_out = (
        f"Имя принято: {name}!\n\n"
        + game.get_ui()
    )
    msg_id = bot_ctx["last_active_msg_id"].get(uid)
    if msg_id:
        await bot_ctx["safe_edit_message"](chat_id, msg_id, text_out, get_main_kb(game))
    else:
        await bot_ctx["update_or_send_message"](chat_id, uid, text_out, get_main_kb(game))

    save_game(uid, game)
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
    if not text:
        return True

    await bot_ctx["safe_delete_message"](chat_id, message.message_id)

    game.companion_name = text
    game.equipment["pet"] = text
    game.set_story_flag("saved_kitten")
    game.set_story_flag("has_pet")
    game.karma["gentle"] = game.karma.get("gentle", 0) + 5
    game.adjust_narrative_karma("compassion", 2)
    game.story_state = None
    game.add_log(f"У вас появился питомец: {text} (+5 кармы)")

    final_text = (
        "Ты смотришь на маленькое существо у себя на руках.\n"
        f"«{text}», — произносишь ты вслух, и понимаешь что нашёл себе нового друга.\n"
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
        game.add_log(f"🧱 Подкинуто: Кора ×{spent} (+{fire_added} 🔥). Огонь: {game.campfire_durability}/{game.campfire_max_durability}.")
        result_text = f"🧱 Подкинуто {spent} шт. коры (+{fire_added} к огню). Огонь: {game.campfire_durability}/{game.campfire_max_durability}."
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
        game.add_log(f"🪵 Подкинуто: Палки ×{to_use}. Огонь: {game.campfire_durability}/{game.campfire_max_durability}.")
        result_text = f"🪵 Добавлено {to_use} палок/веток. Огонь: {game.campfire_durability}/{game.campfire_max_durability}."

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
    game.add_log(f"Выкинуто: {item_name} ×{drop_amount}")
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
    ]
    for handler in handlers:
        try:
            if await handler(uid, chat_id, text, message, game, bot_ctx):
                return True
        except Exception as exc:
            logging.exception(f"Ошибка в диалог-обработчике {handler.__name__} для {uid}: {exc}")
    return False

