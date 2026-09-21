"""Случайная проверка сюжетных обработчиков и финалов игры."""

from collections import Counter
import random
from typing import Callable

from aiogram.types import InlineKeyboardMarkup

from game_state import GameState
from keyboards import get_main_kb
from location_stories import (
    handle_location_1_forest_start,
    handle_location_2_ruchey,
    handle_location_3_slate_hollow,
    handle_location_4_hunters_glade,
    handle_location_5_slug_pit,
    handle_location_6_furry_cave,
    handle_location_7_sanctuary_peak,
    handle_story,
)


ROUNDS = 100
UID = 1


def validate_response(text, kb, callback: str) -> None:
    """Проверить минимальный контракт ответа callback-обработчика."""
    if not isinstance(text, str) or not text.strip():
        raise AssertionError(f"{callback!r}: обработчик вернул некорректный text")
    if not isinstance(kb, InlineKeyboardMarkup):
        raise AssertionError(f"{callback!r}: обработчик вернул некорректный kb")

    buttons = [button for row in kb.inline_keyboard for button in row]
    if not buttons:
        raise AssertionError(f"{callback!r}: клавиатура не содержит кнопок")
    if any(not button.callback_data for button in buttons):
        raise AssertionError(f"{callback!r}: найдена кнопка без callback_data")


def call_and_validate(handler: Callable, callback: str, game: GameState):
    """Вызвать обработчик и проверить результат, сохранив исходную ошибку."""
    text, kb = handler(callback, game, UID)
    validate_response(text, kb, callback)
    return text, kb


def simulate_round(rng: random.Random) -> tuple[str, GameState]:
    """Провести один путь от лесного старта до финала на вершине."""
    game = GameState()

    # Входная сцена леса и случайное безопасное решение без текстового ввода.
    call_and_validate(handle_location_1_forest_start, "forest_start", game)
    call_and_validate(handle_location_1_forest_start, "wolf_leave", game)
    call_and_validate(lambda data, state, uid: handle_story(data, state, uid), "story_next", game)

    locations = (
        (
            handle_location_2_ruchey,
            "river_ferocious",
            ("snake_flee", "snake_stab", "river_calm", "river_cool", "river_deep", "river_brave", "river_talk", "river_dance", "river_sacrifice"),
            "river_end",
        ),
        (
            handle_location_3_slate_hollow,
            "slate_hollow_start",
            ("slate_examine", "slate_climb", "slate_rest"),
            "slate_end",
        ),
        (
            handle_location_4_hunters_glade,
            "hunters_glade_start",
            ("hunters_trap", "hunters_blood", "hunters_animal_help", "hunters_fire"),
            "hunters_fire",
        ),
        (
            handle_location_5_slug_pit,
            "slug_pit_start",
            ("slug_mushroom", "slug_giant", "slug_slime", "slug_deep"),
            None,
        ),
        (
            handle_location_6_furry_cave,
            "furry_cave_start",
            ("furry_examine", "furry_warm", "furry_sleep"),
            "furry_end",
        ),
    )

    for handler, start, choices, finish in locations:
        call_and_validate(handler, start, game)
        call_and_validate(handler, rng.choice(choices), game)
        if finish is not None:
            call_and_validate(handler, finish, game)

    call_and_validate(handle_location_7_sanctuary_peak, "sanctuary_peak_start", game)
    ending_callback = rng.choice((
        "sanctuary_heroic",
        "sanctuary_gentle",
        "sanctuary_mysterious",
    ))
    call_and_validate(handle_location_7_sanctuary_peak, ending_callback, game)
    return f"{ending_callback}_end", game


def main() -> None:
    rng = random.Random()
    endings = Counter()
    karma_totals = Counter()
    successful = 0
    errors = []

    for round_number in range(1, ROUNDS + 1):
        try:
            ending, game = simulate_round(rng)
            endings[ending] += 1
            karma_totals.update(game.karma)
            successful += 1
        except Exception as exc:
            errors.append(f"прогон {round_number}: {type(exc).__name__}: {exc}")

    print(f"Успешные завершения без ошибок: {successful}/{ROUNDS}")
    print("Распределение концовок:")
    for ending in (
        "sanctuary_heroic_end",
        "sanctuary_gentle_end",
        "sanctuary_mysterious_end",
    ):
        count = endings[ending]
        percent = count / ROUNDS * 100
        print(f"  {ending}: {count} ({percent:.1f}%)")

    print("Средняя карма к концу игры:")
    for category in GameState().karma:
        average = karma_totals[category] / successful if successful else 0
        print(f"  {category}: {average:.2f}")

    if errors:
        print("Ошибки:")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()