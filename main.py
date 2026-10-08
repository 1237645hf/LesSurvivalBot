import asyncio
import logging
import os
import time
import random
from typing import Optional, Dict, List, Any
from textwrap import wrap
from pathlib import Path
from aiohttp import web, ClientSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from pymongo import MongoClient

from game_math import (
    process_damage,
    get_resource_multiplier,
    get_base_resource_cost,
    get_thirst_base_cost,
    calculate_ap_by_hp,
)
from game_state import (
    GameState,
    Game,
    get_death_text,
    PARENT_SCREEN,
    CANONICAL_STACKS,
    get_settings_text,
    handle_back_navigation,
    resolve_back_screen,
)
from modules.hints import get_active_hints
from modules.traps import (
    HUNTABLE_ANIMALS,
    TRAP_CHANCE_BY_LOCATION,
    place_trap,
    remove_trap,
    activate_trap,
    get_trap_for_location,
    get_trap_description,
    get_trap_loot,
    get_active_traps,
    roll_trap_roll,
    process_trap_rollover,
    apply_trap_loot_to_inventory,
    traps_unlocked,
    is_traps_callback,
    handle_traps_callback,
)
from modules.finds import (
    roll_find,
    apply_finds_to_inventory,
    location_id_from_game,
    LOCATION_EMOJIS,
    is_explore_callback,
    handle_explore_callback,
)
from modules.cooking import (
    COOKING_RECIPES,
    cook_item,
    list_recipes,
    format_recipe_card,
    get_recipe_max_count,
    cook_portions,
    get_campfire_text,
    is_campfire_callback,
    handle_campfire_callback,
)
from modules.items import (
    get_item_effects,
    get_item_negative_effects,
    is_item_consumable,
    format_item_card,
    get_item_rank_marker,
    get_item_display_name,
    ITEM_DESCRIPTIONS,
    get_usable_items,
    use_consumable,
    is_inventory_callback,
    handle_inventory_callback,
)
from services.dialogs import (
    GUIDE_TEXT,
    format_start_character_text,
    format_tablet_notes_text,
    check_character_name_required,
    is_session_callback,
    handle_session_callback,
    is_tablet_callback,
    handle_tablet_callback,
)

# Готовка: единый источник — modules/cooking.py (еда.txt). CAMPFIRE_RECIPES удалён.


def format_resource_log_text(deltas: dict) -> str:
    """Собрать строку лога строго по ФАКТИЧЕСКИМ дельтам из consume_action/light_campfire.

    Пример вывода: «Голод -2, Жажда -1» или «Голод -1, HP -3 (голодание)».
    """
    parts = []
    if deltas.get("delta_hunger"):
        parts.append(f"Голод {deltas['delta_hunger']:+d}")
    if deltas.get("delta_thirst"):
        parts.append(f"Жажда {deltas['delta_thirst']:+d}")
    hp_delta = deltas.get("delta_hp", 0)
    if hp_delta:
        hp_reasons = []
        if deltas.get("hunger_damage_to_hp"):
            hp_reasons.append("голодание")
        if deltas.get("thirst_damage_to_hp"):
            hp_reasons.append("обезвоживание")
        reason = f" ({', '.join(hp_reasons)})" if hp_reasons else ""
        parts.append(f"HP {hp_delta:+d}{reason}")
    return ", ".join(parts)


# Предметы, для которых при находке назначается случайное количество (1-3)
_STICK_ITEMS = {"Ветка", "Палка", "Палки"}


def _randomize_stick_count(found_list: list) -> list:
    """Увеличить количество веток/палок в результате roll_find до случайного 1-3.

    Остальные предметы остаются с количеством 1 (как всегда).
    Возвращает новый список с дублированными записями (каждая запись = 1 предмет).
    """
    result = []
    for item in found_list:
        if item in _STICK_ITEMS:
            count = random.randint(1, 3)
            result.extend([item] * count)
        else:
            result.append(item)
    return result




def load_env_file(path: str = ".env"):
    """Загрузить переменные из .env, если они ещё не заданы в окружении."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file()

from keyboards import (
    get_main_kb,
    get_locations_kb,
    get_settings_kb,
    get_use_item_kb,
    get_drop_item_kb,
    get_drop_quantity_kb,
    get_campfire_kb,
    get_campfire_fuel_kb,
    get_campfire_recipes_kb,
    get_campfire_recipe_kb,
    get_campfire_light_confirm_kb,
    get_bottle_actions_kb,
    get_inspect_menu_kb,
    get_item_card_actions_kb,
    get_campfire_recipe_view_kb,
    get_inventory_kb,
    inventory_inline_kb,
    character_inline_kb,
    get_fuel_quantity_kb,
    get_start_resume_kb,
    get_confirm_new_game_kb,
    get_start_new_game_kb,
    get_death_kb,
    get_tablet_notes_kb,
    get_tablet_edit_kb,
    get_trap_buttons_kb,
)
from crafts import (
    is_craft_callback,
    handle_craft,
    do_craft,
    can_craft,
    craft_mark,
    CRAFT_RECIPES,
    get_craft_menu_text,
    get_craft_menu_kb,
)
from story.location_stories import (
    handle_story,
    check_forest_research_story_trigger,
    is_story_callback,
    handle_location_2_ruchey,
    handle_location_3_slate_hollow,
    handle_location_4_hunters_glade,
    handle_location_5_slug_pit,
    start_slug_pack_battle,
    handle_location_6_furry_cave,
    handle_location_7_sanctuary_peak,
    ending_text,
    resolve_ending,
    ENDING_TITLES,
)
# ──────────────────────────────────────────────────────────────────────────────
# НАСТРОЙКИ
# ──────────────────────────────────────────────────────────────────────────────
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не найден!")

MONGO_URI = os.getenv("MONGO_URI") or "mongodb://localhost:27017/test"

logging.basicConfig(level=logging.INFO)
logging.info("Бот запускается в режиме Telegram polling")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Глобальные словари для трекинга состояний (запросы, сообщения, блокировки)
last_request_time = {}
last_active_msg_id = {}
user_locks: Dict[int, asyncio.Lock] = {}

def get_user_lock(uid: int) -> asyncio.Lock:
    """Получить per-user asyncio.Lock для защиты от race condition при параллельных кликах."""
    if uid not in user_locks:
        user_locks[uid] = asyncio.Lock()
    return user_locks[uid]

# Регистрация системных команд Telegram для синей кнопки Menu
# set_my_commands вызывается в run_bot() с await

# ──────────────────────────────────────────────────────────────────────────────
# БАЗА ДАННЫХ
# ──────────────────────────────────────────────────────────────────────────────
from services.database import (
    players_collection,
    load_game,
    save_game,
    games,
    MemoryPlayersCollection,
    get_tablet_notes,
    save_tablet_note,
)


def get_callback_answer(callback):
    data = callback.data or ""
    game = games.get(callback.from_user.id)
    if data == "inv_inspect" and (
        not game
        or (
            not any(count > 0 for count in game.inventory.values())
            and not getattr(game, "clean_bottles_charges", [])
        )
    ):
        return "Инвентарь пуст", True
    if data in ("inv_use", "inv_drop") and (
        not game or not any(count > 0 for count in game.inventory.values())
    ):
        return ("Нечего использовать" if data == "inv_use" else "Нечего выкидывать"), True
    if data == "inv_use" and not get_usable_items(game):
        return "Нечего использовать", True
    return None, False


# ──────────────────────────────────────────────────────────────────────────────
# КАМЕННАЯ ПЛИТА (ЗАПИСИ ВЫЖИВШИХ)
# ──────────────────────────────────────────────────────────────────────────────
async def render_tablet_view(chat_id: int, uid: int, page: int = 1, bot_ctx: Optional[dict] = None, notice: Optional[str] = None):
    game = games.get(uid)
    if game:
        game.story_state = None
        game.nav_stack = ["main", "tablet_notes"]
    all_notes = get_tablet_notes()
    text, total_pages = format_tablet_notes_text(all_notes, page=page, page_size=5, notice=notice)
    kb = get_tablet_notes_kb(page, total_pages)

    if bot_ctx:
        msg_id = bot_ctx["last_active_msg_id"].get(uid)
        if msg_id:
            await bot_ctx["safe_edit_message"](chat_id, msg_id, text, kb)
        else:
            await bot_ctx["update_or_send_message"](chat_id, uid, text, kb)
    else:
        await update_or_send_message(chat_id, uid, text, kb)
    if game:
        save_game(uid, game)


# ──────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ С RETRY ПРИ FLOOD
# ──────────────────────────────────────────────────────────────────────────────
async def safe_delete_message(chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest as exc:
        logging.warning(f"Не удалось удалить {message_id}: {exc}")
    except Exception as exc:
        logging.exception(f"Ошибка удаления сообщения {message_id}: {exc}")


async def safe_delete_messages(chat_id: int, message_ids: List[int]):
    """Пакетное удаление сообщений через Telegram Bot API deleteMessages.

    - Принимает список реальных message_ids (до 100 за один сетевой запрос).
    - Обернут в try/except TelegramBadRequest (сообщения старше 48ч или уже удалённые).
    - Обрабатывает TelegramRetryAfter (FloodWait).
    """
    valid_ids = [mid for mid in set(message_ids) if isinstance(mid, int)]
    if not valid_ids:
        return

    # Telegram API метод deleteMessages принимает пачку до 100 ID за 1 сетевой запрос
    for i in range(0, len(valid_ids), 100):
        chunk = valid_ids[i:i + 100]
        if not chunk:
            continue
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=chunk)
        except TelegramBadRequest as exc:
            logging.warning(f"Не удалось пакетно удалить сообщения {chunk}: {exc}")
        except TelegramRetryAfter as exc:
            logging.warning(f"Flood control при delete_messages: ждём {exc.retry_after} сек")
            try:
                await asyncio.sleep(exc.retry_after + 0.5)
                await bot.delete_messages(chat_id=chat_id, message_ids=chunk)
            except Exception as retry_exc:
                logging.warning(f"Ошибка повторного delete_messages: {retry_exc}")
        except Exception as exc:
            logging.exception(f"Неожиданная ошибка delete_messages {chunk}: {exc}")


async def track_message_to_delete(state: FSMContext, message_id: int):
    """Сохранить реальный message_id в FSM-состояние для последующего пакетного удаления."""
    try:
        data = await state.get_data()
        msg_ids = list(data.get("messages_to_delete", []))
        if message_id not in msg_ids:
            msg_ids.append(message_id)
            await state.update_data(messages_to_delete=msg_ids)
    except Exception as exc:
        logging.warning(f"Ошибка сохранения message_id в состояние: {exc}")


async def clear_tracked_messages(
    chat_id: int,
    state: FSMContext,
    extra_ids: Optional[List[int]] = None,
    protected_ids: Optional[List[int]] = None,
):
    """Пакетно удалить сохраненные в состоянии сообщения через delete_messages (1 сетевой запрос).

    После удаления список сохранённых ID в состоянии очищается.
    """
    try:
        data = await state.get_data()
        ids_to_delete = list(data.get("messages_to_delete", []))
    except Exception as exc:
        logging.warning(f"Ошибка чтения messages_to_delete из состояния: {exc}")
        ids_to_delete = []

    if extra_ids:
        for mid in extra_ids:
            if isinstance(mid, int) and mid not in ids_to_delete:
                ids_to_delete.append(mid)

    if protected_ids:
        ids_to_delete = [mid for mid in ids_to_delete if mid not in protected_ids]

    if ids_to_delete:
        await safe_delete_messages(chat_id=chat_id, message_ids=ids_to_delete)
        try:
            await state.update_data(messages_to_delete=[])
        except Exception as exc:
            logging.warning(f"Ошибка сброса messages_to_delete в состоянии: {exc}")


async def safe_edit_message(chat_id: int, msg_id: int, text: str, reply_markup=None, parse_mode: Optional[str] = None):
    try:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except TelegramRetryAfter as exc:
        logging.warning(f"Flood control: ждём {exc.retry_after} сек перед повтором edit")
        try:
            await asyncio.sleep(exc.retry_after + 0.5)
            await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        except TelegramBadRequest as exc2:
            logging.warning(f"Не удалось отредактировать после retry {msg_id}: {exc2}")
            await safe_delete_message(chat_id, msg_id)
            return False
        except Exception as exc2:
            logging.exception(f"Ошибка повторного edit {msg_id}: {exc2}")
            return False
    except TelegramBadRequest as exc:
        logging.warning(f"Не удалось отредактировать {msg_id}: {exc}")
        await safe_delete_message(chat_id, msg_id)
        return False
    except Exception as exc:
        logging.exception(f"Неожиданная ошибка edit {msg_id}: {exc}")
        return False


async def update_or_send_message(
    chat_id: int,
    uid: int,
    text: str,
    reply_markup=None,
    parse_mode: Optional[str] = None,
    current_msg_id: Optional[int] = None,
):
    game = games.get(uid)
    text = format_game_text(text, game)
    now = time.time()
    last_action = getattr(game, "last_action_time", None) if game else None
    header_id = getattr(game, "header_message_id", None) if game else None
    active_msg_id = last_active_msg_id.get(uid)

    # Условие пересоздания: прошло более 5 минут (300 сек) или нет привязки к активному окну
    time_expired = (last_action is None) or ((now - last_action) > 300)
    no_active_binding = (active_msg_id is None) or (header_id is None)
    need_recreate = time_expired or no_active_binding

    if need_recreate:
        # 1. Собрать гарантированные ID
        guaranteed_ids = set()
        if game:
            if getattr(game, "last_message_id", None):
                guaranteed_ids.add(game.last_message_id)
            if getattr(game, "header_message_id", None):
                guaranteed_ids.add(game.header_message_id)
        if active_msg_id:
            guaranteed_ids.add(active_msg_id)
        if current_msg_id:
            guaranteed_ids.add(current_msg_id)

        # 2. Определить опорный ID (curr_id) и собрать список до 100 сообщений (известные ID + предыдущие)
        curr_id = (
            current_msg_id
            or active_msg_id
            or (getattr(game, "last_message_id", None) if game else None)
            or (max(guaranteed_ids) if guaranteed_ids else None)
        )

        candidate_ids = list(guaranteed_ids)
        if curr_id:
            for mid in range(curr_id, max(1, curr_id - 100), -1):
                if mid not in guaranteed_ids:
                    candidate_ids.append(mid)
                if len(candidate_ids) >= 100:
                    break

        # 3. Попытка удалить сразу пачкой до 100 сообщений за 1 сетевой запрос
        batch_success = False
        if candidate_ids:
            try:
                await bot.delete_messages(chat_id=chat_id, message_ids=candidate_ids)
                batch_success = True
            except TelegramRetryAfter as exc:
                logging.warning(f"Flood control при delete_messages (100): ждём {exc.retry_after} сек")
                try:
                    await asyncio.sleep(exc.retry_after + 0.5)
                    await bot.delete_messages(chat_id=chat_id, message_ids=candidate_ids)
                    batch_success = True
                except Exception:
                    pass
            except Exception as exc:
                logging.debug(f"Пакетное удаление 100 сообщений не удалось ({exc}), переходим на fallback...")

        # 4. Fallback: если пакетный запрос не удался — сначала удаляем известные ID, затем остальные
        if not batch_success and candidate_ids:
            # Сначала гарантированно удаляем известные сообщения бота
            for gid in guaranteed_ids:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=gid)
                except Exception:
                    pass
            # Затем перебором остальные сообщения с защитой от Flood Control
            for mid in candidate_ids:
                if mid in guaranteed_ids:
                    continue
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=mid)
                except TelegramRetryAfter as exc:
                    logging.warning(f"Flood control при fallback удалении: останавливаем перебор (ждём {exc.retry_after} сек)")
                    break
                except Exception:
                    continue

        # 3. Сразу после очистки отправить чистую шапку
        try:
            rm_msg = await bot.send_message(
                chat_id,
                "🌲 LesSurvivalBot",
                reply_markup=ReplyKeyboardRemove(),
            )
            if game:
                game.header_message_id = rm_msg.message_id
        except Exception as exc:
            logging.exception(f"Ошибка отправки новой шапки: {exc}")

        # Следом отправь актуальное игровое окно через send_message
        try:
            msg = await bot.send_message(
                chat_id,
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            last_active_msg_id[uid] = msg.message_id
            if game:
                game.last_message_id = msg.message_id
                game.last_action_time = time.time()
                save_game(uid, game)
            return msg.message_id
        except TelegramRetryAfter as exc:
            logging.warning(f"Flood control send_message: ждём {exc.retry_after} сек")
            try:
                await asyncio.sleep(exc.retry_after + 0.5)
                msg = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
                last_active_msg_id[uid] = msg.message_id
                if game:
                    game.last_message_id = msg.message_id
                    game.last_action_time = time.time()
                    save_game(uid, game)
                return msg.message_id
            except Exception as exc2:
                logging.exception(f"Ошибка send_message после retry: {exc2}")
                return None
        except Exception as exc:
            logging.exception(f"Ошибка send_message: {exc}")
            return None

    # В штатном режиме: второе игровое окно непрерывно редактируется через safe_edit_message
    msg_id = active_msg_id
    if msg_id:
        edited = await safe_edit_message(chat_id, msg_id, text, reply_markup, parse_mode=parse_mode)
        if edited:
            if game:
                game.last_message_id = msg_id
                game.last_action_time = time.time()
                save_game(uid, game)
            return msg_id
        last_active_msg_id.pop(uid, None)

    # Fallback если редактирование не удалось
    try:
        msg = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        last_active_msg_id[uid] = msg.message_id
        if game:
            game.last_message_id = msg.message_id
            game.last_action_time = time.time()
            save_game(uid, game)
        return msg.message_id
    except TelegramRetryAfter as exc:
        logging.warning(f"Flood control send_message: ждём {exc.retry_after} сек")
        try:
            await asyncio.sleep(exc.retry_after + 0.5)
            msg = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
            last_active_msg_id[uid] = msg.message_id
            if game:
                game.last_message_id = msg.message_id
                game.last_action_time = time.time()
                save_game(uid, game)
            return msg.message_id
        except Exception as exc2:
            logging.exception(f"Ошибка send_message после retry: {exc2}")
            return None
    except Exception as exc:
        logging.exception(f"Неожиданная ошибка send_message: {exc}")
        return None


def format_game_text(text: str, game=None) -> str:
    """Полный текст сообщения без обрезки и искажения строк."""
    return text


def is_in_active_story(game: Optional[Game]) -> bool:
    """Проверить, находится ли игрок на сюжетном экране с выборами или в бою."""
    if not game:
        return False
    if getattr(game, "hp", 100) <= 0:
        return False
    if getattr(game, "active_story_callback", None):
        return True
    if getattr(game, "story_state", None) in ("WAITING_FOR_PET_NAME", "wolf_battle", "boar_battle", "slime_battle"):
        return True
    return False


async def restore_active_story_screen(chat_id: int, uid: int, game: Game) -> bool:
    """Перевывести текущее сюжетное окно, защитив состояние от сброса и не давая командам сломать сюжет."""
    if getattr(game, "story_state", None) == "WAITING_FOR_PET_NAME" or getattr(game, "active_story_callback", None) in ("pet_take", "waiting_pet_name"):
        has_named_pet = game.is_story_flag_set("has_pet") and bool(
            game.equipment.get("pet") or (getattr(game, "companion_name", "") not in (None, "", "Кот", "Котёнок"))
        )
        if not has_named_pet:
            res_text, res_kb = handle_story("waiting_pet_name", game, uid)
            if res_text is not None:
                await update_or_send_message(chat_id, uid, res_text, res_kb)
                return True

    cb = getattr(game, "active_story_callback", None)
    if cb:
        if cb.startswith("l2_") or cb.startswith("river_") or cb.startswith("snake_"):
            res_text, res_kb = handle_location_2_ruchey(cb, game, uid)
        elif cb.startswith("l3_") or cb.startswith("slate_") or cb.startswith("boar_"):
            res_text, res_kb = handle_location_3_slate_hollow(cb, game, uid)
        elif cb.startswith("l4_") or cb.startswith("hunters_") or cb.startswith("glade_"):
            res_text, res_kb = handle_location_4_hunters_glade(cb, game, uid)
        elif cb.startswith("l5_") or cb.startswith("slug_") or cb.startswith("pit_") or cb.startswith("slime_battle"):
            res_text, res_kb = handle_location_5_slug_pit(cb, game, uid)
        elif cb.startswith("l6_") or cb.startswith("furry_") or cb.startswith("cave_"):
            res_text, res_kb = handle_location_6_furry_cave(cb, game, uid)
        elif cb.startswith("l7_") or cb.startswith("sanctuary_"):
            res_text, res_kb = handle_location_7_sanctuary_peak(cb, game, uid)
        else:
            res_text, res_kb = handle_story(cb, game, uid)

        if res_text is not None:
            await update_or_send_message(chat_id, uid, res_text, res_kb)
            return True
    return False


def _ensure_game(uid: int):
    """Достать игру из памяти или Mongo и восстановить active_msg_id при необходимости."""
    game = games.get(uid)
    if game is None:
        game = load_game(uid)
        if game is not None:
            games[uid] = game
    if game and getattr(game, "last_message_id", None) and uid not in last_active_msg_id:
        last_active_msg_id[uid] = game.last_message_id
    return game


# ──────────────────────────────────────────────────────────────────────────────
# ХЕНДЛЕРЫ
# ──────────────────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: Optional[FSMContext] = None):
    uid = message.from_user.id
    chat_id = message.chat.id
    logging.info(f"[START] Получен /start от {uid}")

    user_lock = get_user_lock(uid)
    try:
        await asyncio.wait_for(user_lock.acquire(), timeout=3.0)
    except asyncio.TimeoutError:
        logging.warning(f"Таймаут ожидания user_lock в cmd_start для {uid}")
        return

    try:
        game = _ensure_game(uid)
        # Если игрок находится внутри сюжета — блокируем команду, удаляем её и перевыводим сюжетное окно
        if is_in_active_story(game):
            await safe_delete_message(chat_id, message.message_id)
            await restore_active_story_screen(chat_id, uid, game)
            return

        if state is None:
            state = dp.fsm.get_context(bot=bot, chat_id=chat_id, user_id=uid)

        # Безопасная пакетная очистка реальных ID за один запрос delete_messages:
        # 1. Сохранённые ранее сообщения из FSM-состояния (messages_to_delete)
        # 2. Сообщение самой команды /start
        # 3. Предыдущий активный экран игры (last_active_msg_id), если перезапуск
        extra_ids = [message.message_id]
        old_active_msg = last_active_msg_id.pop(uid, None)
        if old_active_msg:
            extra_ids.append(old_active_msg)
        if game and getattr(game, "last_message_id", None) and game.last_message_id not in extra_ids:
            extra_ids.append(game.last_message_id)

        protected_ids = []
        if game and getattr(game, "header_message_id", None):
            protected_ids.append(game.header_message_id)

        await clear_tracked_messages(chat_id=chat_id, state=state, extra_ids=extra_ids, protected_ids=protected_ids)

        loaded = load_game(uid)
        if loaded and getattr(loaded, "is_name_set", False):
            hero_name = loaded.character_name or "Выживший"
            text = format_start_character_text(loaded)
            kb = get_start_resume_kb(hero_name)
        else:
            text = GUIDE_TEXT
            kb = get_start_new_game_kb()

        # Нижняя Reply-клавиатура полностью отключена — сбрасываем кэш у клиента.
        # Шапка "🌲 LesSurvivalBot" гарантированно отправляется/обновляется в update_or_send_message (защита от дублей)
        if game and not getattr(game, "header_message_id", None) and loaded and getattr(loaded, "header_message_id", None):
            game.header_message_id = loaded.header_message_id
        await update_or_send_message(chat_id, uid, text, kb, current_msg_id=message.message_id)
    finally:
        user_lock.release()


@dp.message(Command("main", "menu", "home"))
async def cmd_main(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    await safe_delete_message(chat_id, message.message_id)

    user_lock = get_user_lock(uid)
    try:
        await asyncio.wait_for(user_lock.acquire(), timeout=3.0)
    except asyncio.TimeoutError:
        logging.warning(f"Таймаут ожидания user_lock в cmd_main для {uid}")
        return

    try:
        game = _ensure_game(uid)
        if not game:
            await message.answer("Сначала /start")
            return
        if is_in_active_story(game):
            await restore_active_story_screen(chat_id, uid, game)
            return
        if getattr(game, "hp", 100) <= 0:
            game.hp = 0
            game.active_story_callback = None
            save_game(uid, game)
            await update_or_send_message(chat_id, uid, get_death_text(game), get_death_kb())
            return
        prompt = check_character_name_required(game)
        if prompt:
            await update_or_send_message(chat_id, uid, prompt, None)
            return
        game.nav_stack = ["main"]
        await update_or_send_message(chat_id, uid, game.get_ui(), get_main_kb(game))
        save_game(uid, game)
    finally:
        user_lock.release()



@dp.message(Command("inventory", "inv"))
async def cmd_inventory(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    await safe_delete_message(chat_id, message.message_id)

    user_lock = get_user_lock(uid)
    try:
        await asyncio.wait_for(user_lock.acquire(), timeout=3.0)
    except asyncio.TimeoutError:
        logging.warning(f"Таймаут ожидания user_lock в cmd_inventory для {uid}")
        return

    try:
        game = _ensure_game(uid)
        if not game:
            await message.answer("Сначала /start")
            return
        if is_in_active_story(game):
            await restore_active_story_screen(chat_id, uid, game)
            return
        if getattr(game, "hp", 100) <= 0:
            game.hp = 0
            game.active_story_callback = None
            save_game(uid, game)
            await update_or_send_message(chat_id, uid, get_death_text(game), get_death_kb())
            return
        prompt = check_character_name_required(game)
        if prompt:
            await update_or_send_message(chat_id, uid, prompt, None)
            return
        game.nav_stack = ["main", "inventory"]
        await update_or_send_message(chat_id, uid, game.get_inventory_text(), inventory_inline_kb)
        save_game(uid, game)
    finally:
        user_lock.release()



@dp.message(Command("character", "char", "hero"))
async def cmd_character(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    await safe_delete_message(chat_id, message.message_id)

    user_lock = get_user_lock(uid)
    try:
        await asyncio.wait_for(user_lock.acquire(), timeout=3.0)
    except asyncio.TimeoutError:
        logging.warning(f"Таймаут ожидания user_lock в cmd_character для {uid}")
        return

    try:
        game = _ensure_game(uid)
        if not game:
            await message.answer("Сначала /start")
            return
        if is_in_active_story(game):
            await restore_active_story_screen(chat_id, uid, game)
            return
        if getattr(game, "hp", 100) <= 0:
            game.hp = 0
            game.active_story_callback = None
            save_game(uid, game)
            await update_or_send_message(chat_id, uid, get_death_text(game), get_death_kb())
            return
        prompt = check_character_name_required(game)
        if prompt:
            await update_or_send_message(chat_id, uid, prompt, None)
            return
        game.nav_stack = ["main", "inventory", "character"]
        await update_or_send_message(chat_id, uid, game.get_character_text(), character_inline_kb)
        save_game(uid, game)
    finally:
        user_lock.release()


@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id
    await safe_delete_message(chat_id, message.message_id)

    user_lock = get_user_lock(uid)
    try:
        await asyncio.wait_for(user_lock.acquire(), timeout=3.0)
    except asyncio.TimeoutError:
        logging.warning(f"Таймаут ожидания user_lock в cmd_settings для {uid}")
        return

    try:
        game = _ensure_game(uid)
        if not game:
            await message.answer("Сначала /start")
            return
        if is_in_active_story(game):
            await restore_active_story_screen(chat_id, uid, game)
            return
        if getattr(game, "hp", 100) <= 0:
            game.hp = 0
            game.active_story_callback = None
            save_game(uid, game)
            await update_or_send_message(chat_id, uid, get_death_text(game), get_death_kb())
            return
        prompt = check_character_name_required(game)
        if prompt:
            await update_or_send_message(chat_id, uid, prompt, None)
            return
        game.push_screen("settings")

        await update_or_send_message(chat_id, uid, get_settings_text(game), get_settings_kb(game))
        save_game(uid, game)
    finally:
        user_lock.release()

def handle_sleep_action(game: Any) -> tuple[str, Any]:
    """Обрабатывает сон персонажа, смену дня, проверки смерти и ловушек."""
    game.sleep_and_turn_day()
    cur_loc = str(getattr(game, "current_location", "") or "")
    if "Просека" in cur_loc:
        if not hasattr(game, "story_flags") or game.story_flags is None:
            game.story_flags = {}
        game.story_flags["l4_sleep_count"] = game.story_flags.get("l4_sleep_count", 0) + 1
    if game.hp <= 0:
        game.hp = 0
        game.active_story_callback = None
        return get_death_text(game, "Критическое истощение от голода и жажды во сне (−10 HP).", getattr(game, "current_location", None)), get_death_kb()
    trap_msgs = []
    # Утро: 40% пуста, 20% ломается, 40% добыча по таблице локации
    for event in process_trap_rollover(game):
        loc_id = event.get("location_id")
        if event.get("broken"):
            msg = f"Ловушка на локации {loc_id}: сломалась, добычи нет."
            game.add_log(msg)
            trap_msgs.append(msg)
            continue
        if event.get("empty"):
            msg = f"Ловушка на локации {loc_id}: пуста, ничего не попалось."
            game.add_log(msg)
            trap_msgs.append(msg)
            continue
        animal = event.get("animal")
        loot = event.get("loot") or {}
        if loot:
            apply_trap_loot_to_inventory(game, loot)
            loot_txt = ", ".join(f"{k}×{v}" for k, v in loot.items())
            msg = f"Ловушка на локации {loc_id}: {animal} (+{loot_txt})"
            game.add_log(msg)
            trap_msgs.append(msg)
        elif animal:
            msg = f"Ловушка на локации {loc_id}: {animal}"
            game.add_log(msg)
            trap_msgs.append(msg)
        trap = getattr(game, "traps", {}).get(loc_id)
        if trap:
            trap["pending_animal"] = None
            trap["pending_loot"] = None
    if trap_msgs:
        text = game.get_ui() + "\n" + "\n".join(trap_msgs)
    else:
        text = game.get_ui()
    kb = get_main_kb(game)
    return text, kb


@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    chat_id = callback.message.chat.id
    data = callback.data or ""

    # При любом нажатии инлайн-кнопки сразу связываем активное окно с этим сообщением.
    # Если бот перезапустился, первое же нажатие восстанавливает Single-Message контекст.
    if callback.message:
        last_active_msg_id[uid] = callback.message.message_id

    user_lock = get_user_lock(uid)
    if user_lock.locked():
        try:
            await callback.answer()
        except Exception:
            pass
        return

    await user_lock.acquire()
    try:
        now = time.time()
        last = last_request_time.get(uid, 0)
        if now - last < 0.35:
            await callback.answer()
            return
        last_request_time[uid] = now

        ans = get_callback_answer(callback)
        if ans and ans[0]:
            await callback.answer(str(ans[0]), show_alert=bool(ans[1]) if len(ans) > 1 else False)
        else:
            await callback.answer()

        logging.info(f"[CALLBACK] {data} от {uid}")
        game = _ensure_game(uid)
        if game and callback.message:
            game.last_message_id = callback.message.message_id

        if is_session_callback(data):
            text, kb = handle_session_callback(data, game, uid, games)
            await update_or_send_message(chat_id, uid, text, kb)
            return

        if game is None:
            await update_or_send_message(
                chat_id,
                uid,
                "Сессия не найдена. Нажми /start",
                get_start_new_game_kb(),
            )
            return

        prompt = check_character_name_required(game)
        if prompt:
            await update_or_send_message(chat_id, uid, prompt, None)
            return

        if getattr(game, "hp", 100) <= 0:
            game.hp = 0
            game.active_story_callback = None
            save_game(uid, game)
            text = get_death_text(game)
            kb = get_death_kb()
            await update_or_send_message(chat_id, uid, text, kb)
            return

        text = None
        kb = None

        if data == "noop":
            await callback.answer()
            return

        elif data in ("menu_character", "inv_character", "character_screen"):
            game.push_screen("character")
            text = game.get_character_text()
            kb = character_inline_kb

        elif data == "locations_menu":
            game.push_screen("locations")
            text = "Куда направиться?"
            kb = get_locations_kb(game)

        elif data == "location_enter_1":
            game.current_location = "Стартовый лес"
            game.reset_nav()
            game.add_log("Ты вернулся в Стартовый лес.")
            text = game.get_ui()
            kb = get_main_kb(game)

        elif is_tablet_callback(data):
            text, kb = handle_tablet_callback(data, game, uid)

        elif is_traps_callback(data):
            text, kb = handle_traps_callback(data, game, uid)

        elif is_inventory_callback(data):
            text, kb = await handle_inventory_callback(data, game, uid, callback)

        elif is_campfire_callback(data):
            text, kb = await handle_campfire_callback(data, game, uid, callback)

        elif is_craft_callback(data):
            text, kb = handle_craft(data, game, uid)

        elif is_explore_callback(data):
            text, kb = await handle_explore_callback(data, game, uid, callback)

        elif data in ("back", "back_to_inv", "inv_back"):
            text, kb = handle_back_navigation(game, uid)

        elif is_story_callback(data):
            text, kb = handle_story(data, game, uid)

        elif data in ("action_sleep", "action_4"):
            text, kb = handle_sleep_action(game)

        elif data == "menu_main":
            game.active_story_callback = None
            text = game.get_ui()
            kb = get_main_kb(game)

        elif data == "karma_escape":
            narrative = getattr(game, "narrative_karma", {})
            karma_ok = bool(narrative) and all(v > 0 for v in narrative.values())
            if karma_ok:
                game.add_log("Карма идеальна — ты сбежал из леса!")
                game.story_state = "karma_escape"
            else:
                game.add_log("Карма не идеальна — остаёшься в лесу.")
                game.story_state = "karma_stuck"
            text = game.get_ui()
            kb = get_main_kb(game)

        if text is not None:
            game.record_route(data)
            await update_or_send_message(chat_id, uid, text, kb)
            save_game(uid, game)

        try:
            await callback.answer()
        except Exception:
            pass
    except Exception as exc:
        logging.exception(f"Ошибка callback {data if 'data' in locals() else 'unknown'} для {uid}: {exc}")
        try:
            await callback.answer("Ошибка обработки кнопки. Попробуй ещё раз или /start", show_alert=True)
        except Exception as e:
            pass
    finally:
        user_lock.release()

@dp.message(F.text & ~F.text.startswith("/"))
async def process_text_message(message: Message):
    uid = message.from_user.id
    chat_id = message.chat.id

    # P8: Любой входящий текст от пользователя сразу удаляется для чистоты чата (одно окно),
    # не дожидаясь освобождения блокировки сессии.
    await safe_delete_message(chat_id, message.message_id)

    raw_text = message.text.strip() if message.text else ""
    text = raw_text[:80] if raw_text else ""
    # Если пришло сообщение от старой кэшированной Reply-панели — принудительно удаляем её у клиента
    # и перенаправляем в соответствующую команду ДО взятия user_lock (предотвращение deadlock)
    old_reply_buttons = (
        "🚀 Начать / Старт", "🏠 Главное меню / Перезапуск", "🏠 Главное меню",
        "📊 Статус", "🏠 Главный экран", "🎒 Инвентарь", "👤 Персонаж", "⚙️ Настройки"
    )
    if text in old_reply_buttons:
        try:
            await message.answer("Нижняя панель отключена. Управление ведётся через кнопки сообщений.", reply_markup=ReplyKeyboardRemove())
        except Exception:
            pass
        if text in ("🚀 Начать / Старт", "🏠 Главное меню / Перезапуск", "🏠 Главное меню"):
            await cmd_start(message)
            return
        if text in ("📊 Статус", "🏠 Главный экран"):
            await cmd_main(message)
            return
        if text in ("🎒 Инвентарь",):
            await cmd_inventory(message)
            return
        if text in ("👤 Персонаж",):
            await cmd_character(message)
            return
        if text in ("⚙️ Настройки",):
            await cmd_settings(message)
            return

    # Ожидание блокировки сессии с таймаутом 3.0 секунды (защита от зависаний и deadlock)
    user_lock = get_user_lock(uid)
    try:
        await asyncio.wait_for(user_lock.acquire(), timeout=3.0)
    except asyncio.TimeoutError:
        logging.warning(f"Таймаут ожидания user_lock в process_text_message для {uid}")
        return

    try:
        game = _ensure_game(uid)
        if not game:
            return

        # Делегируем диалоговые FSM-состояния в services/dialogs.py
        from services.dialogs import process_text_input
        bot_ctx = {
            "last_active_msg_id": last_active_msg_id,
            "safe_edit_message": safe_edit_message,
            "safe_delete_message": safe_delete_message,
            "safe_delete_messages": safe_delete_messages,
            "clear_tracked_messages": clear_tracked_messages,
            "update_or_send_message": update_or_send_message,
            "format_game_text": format_game_text,
            "inventory_inline_kb": inventory_inline_kb,
            "get_campfire_kb": get_campfire_kb,
            "render_tablet_view": render_tablet_view,
        }
        handled = await process_text_input(uid, chat_id, text, message, game, bot_ctx)
        if not handled:
            # Если текст не распознан диалогами и игрок в сюжетке — освежаем сюжетное окно
            if is_in_active_story(game):
                await restore_active_story_screen(chat_id, uid, game)

    except Exception as exc:
        logging.exception(f"Ошибка process_text_message для {uid}: {exc}")
    finally:
        user_lock.release()



# ──────────────────────────────────────────────────────────────────────────────
# РЎР•Р Р’Р•Р  Р РџРРќР“
# ──────────────────────────────────────────────────────────────────────────────
from services.server import keep_alive_pinger, start_health_check_server, PING_URLS


async def run_bot():
    """Запустить polling и гарантированно закрыть внешние ресурсы при остановке."""
    await start_health_check_server()
    
    # Запуск пинга в отдельном task — чтобы не мешал запуску бота
    pinger_task = asyncio.create_task(keep_alive_pinger(300))
    
    try:
        # Даем серверу "отдохнуть" перед установкой команд
        logging.info("Сервер запущен — даем ему 10 секунд на 'разогрев'...")
        await asyncio.sleep(10)
        logging.info("Запускаем команды бота...")
        # Обертываем команды в try/except — aiogram может ронять Unauthorized на уже запущонном боте
        try:
            await bot.set_my_commands([
                types.BotCommand(command="start", description="Начать выживание"),
                types.BotCommand(command="main", description="Главный экран"),
                types.BotCommand(command="inventory", description="Инвентарь"),
                types.BotCommand(command="character", description="Персонаж"),
                types.BotCommand(command="settings", description="Настройки"),
            ])
            await bot.delete_webhook(drop_pending_updates=False)
            logging.info("Команды установлены — запускаем polling...")
            await dp.start_polling(bot)
        except Exception as cmd_err:
            logging.error(f"Ошибка при настройке команд: {cmd_err}")
            # Продолжаем polling — он сам обработает команды
            await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка в основном потоке бота: {e}")
        # Перезапускаем пинг, если бот упал
        if pinger_task.done() and not pinger_task.cancelled():
            logging.warning("Пингер завершил работу — перезапускаем его...")
            pinger_task = asyncio.create_task(keep_alive_pinger(300))
    finally:
        from services.database import mongo_client
        if mongo_client is not None:
            mongo_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_bot())
