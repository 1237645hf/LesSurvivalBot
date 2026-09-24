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
        fuel_amount = int(text)
        if fuel_amount <= 0:
            await _reply_error("❌ Введите число больше нуля!")
            return True
    except ValueError:
        await _reply_error("❌ Введите корректное положительное число!")
        return True

    branches = game.inventory.get("Ветка", 0)
    if branches <= 0:
        await _reply_error("❌ У вас нет столько веток! Доступно: 0")
        return True

    needed = game.campfire_max_durability - game.campfire_durability
    if fuel_amount > needed:
        fuel_amount = needed

    game.inventory["Ветка"] -= fuel_amount
    if game.inventory["Ветка"] <= 0:
        del game.inventory["Ветка"]
    game.campfire_durability += fuel_amount
    game.story_state = None

    result_text = f"🪵 Добавлено {fuel_amount} ветки. Прочность: {game.campfire_durability}/{game.campfire_max_durability}."
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
