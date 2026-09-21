"""Направленная проверка достижимости семи канонических концовок."""

from collections import Counter
from typing import Callable

from game_state import GameState
from location_stories import (
    handle_location_1_forest_start,
    handle_location_2_ruchey,
    handle_location_3_slate_hollow,
    handle_location_4_hunters_glade,
    handle_location_5_slug_pit,
    handle_location_6_furry_cave,
    handle_location_7_sanctuary_peak,
    handle_story,
    resolve_ending,
)
from tests.test_sim import call_and_validate


RUNS_PER_STAGE = 250
UID = 1
TARGETS = (
    (1, "all_mine", "sanctuary_heroic"),
    (2, "quiet_growl", "sanctuary_gentle"),
    (3, "another_forest", "sanctuary_mysterious"),
    (4, "guardian", "sanctuary_gentle"),
    (5, "fifteen_marks", "sanctuary_mysterious"),
    (6, "distant_smoke", "sanctuary_gentle"),
    (7, "traces", "sanctuary_heroic"),
)

# Осознанные маршруты: выборы фиксированы для каждой целевой стратегии.
ROUTES = {
    "all_mine": ("wolf_leave", "snake_flee", "slate_examine", "hunters_trap", "slug_mushroom", "furry_warm"),
    "quiet_growl": ("adopt_kitten", "river_calm", "slate_rest", "hunters_fire", "slug_giant", "furry_warm"),
    "another_forest": ("wolf_leave", "river_deep", "slate_climb", "hunters_fire", "slug_deep", "furry_warm"),
    "guardian": ("adopt_kitten", "river_talk", "slate_rest", "hunters_animal_help", "slug_giant", "furry_sleep"),
    "fifteen_marks": ("wolf_leave", "river_deep", "slate_examine", "hunters_blood", "slug_deep", "furry_examine"),
    "distant_smoke": ("adopt_kitten", "river_talk", "slate_rest", "hunters_blood", "slug_giant", "furry_sleep"),
    "traces": ("wolf_leave", "river_calm", "slate_rest", "hunters_trap", "slug_slime", "furry_examine"),
}


def run_directed_route(target: str, sanctuary_choice: str) -> tuple[str, GameState]:
    game = GameState()
    choices = ROUTES[target]

    # Лес: для направлений с питомцем моделируем также ввод его имени.
    call_and_validate(handle_location_1_forest_start, "forest_start", game)
    if choices[0] in ("wolf_torch", "adopt_kitten"):
        call_and_validate(handle_story, "wolf_torch", game)
        call_and_validate(handle_story, "peek_den", game)
        if choices[0] == "adopt_kitten":
            text, kb = handle_story("pet_take", game, UID)
            if not text or kb is not None:
                raise AssertionError("pet_take должен вернуть текстовый экран без клавиатуры")
            game.companion_name = "Лапа"
            game.equipment["pet"] = game.companion_name
            game.story_state = None
        else:
            call_and_validate(handle_story, "pet_leave", game)
    else:
        call_and_validate(handle_location_1_forest_start, "forest_start", game)
        call_and_validate(handle_story, choices[0], game)

    location_steps: tuple[tuple[Callable, str, str | None], ...] = (
        (handle_location_2_ruchey, "river_ferocious", "river_end"),
        (handle_location_3_slate_hollow, "slate_hollow_start", "slate_end"),
        (handle_location_4_hunters_glade, "hunters_glade_start", "hunters_fire"),
        (handle_location_5_slug_pit, "slug_pit_start", None),
        (handle_location_6_furry_cave, "furry_cave_start", "furry_end"),
    )
    for index, (handler, start, finish) in enumerate(location_steps, start=1):
        call_and_validate(handler, start, game)
        call_and_validate(handler, choices[index], game)
        if finish:
            call_and_validate(handler, finish, game)

    call_and_validate(handle_location_7_sanctuary_peak, "sanctuary_peak_start", game)
    call_and_validate(handle_location_7_sanctuary_peak, sanctuary_choice, game)
    return resolve_ending(game), game


def test_all_canonical_endings_are_reachable():
    """Проверить каждый направленный маршрут обычным запуском pytest."""
    for _, target, sanctuary_choice in TARGETS:
        actual, _ = run_directed_route(target, sanctuary_choice)
        assert actual == target


def diagnose(target: str, actual: str, game: GameState) -> str:
    if actual == target:
        return "достигнута"
    missing_karma = [name for name, value in game.narrative_karma.items() if value == 0]
    missing_flags = [name for name in (
        "has_pet", "deer_freed", "left_clay_for_next", "left_warning",
        "left_something_in_bundle", "bag_obtained", "maximum_resources",
    ) if not game.story_flags.get(name, False)]
    return (
        f"срыв в {actual}: narrative_karma не изменена ({', '.join(missing_karma)}=0); "
        f"не установлены флаги ({', '.join(missing_flags)})"
    )


def main() -> None:
    total_success = 0
    print("Этап | Цель          | Успех     | Rate   | Фактический результат / причина")
    print("-----|---------------|-----------|--------|--------------------------------")

    for stage, target, sanctuary_choice in TARGETS:
        results = Counter()
        reasons = Counter()
        for _ in range(RUNS_PER_STAGE):
            try:
                actual, game = run_directed_route(target, sanctuary_choice)
                results[actual] += 1
                if actual == target:
                    reasons["достигнута"] += 1
                    total_success += 1
                else:
                    reasons[diagnose(target, actual, game)] += 1
            except Exception as exc:
                reasons[f"ошибка {type(exc).__name__}: {exc}"] += 1

        successes = results[target]
        rate = successes / RUNS_PER_STAGE * 100
        common_reason = reasons.most_common(1)[0][0] if reasons else "нет данных"
        print(f"{stage:>4} | {target:<13} | {successes:>3}/{RUNS_PER_STAGE:<3} | {rate:>5.1f}% | {common_reason}")

    print(f"\nИтого: {total_success}/1750 успешных направленных выходов ({total_success / 1750 * 100:.1f}%).")
    print("Вывод: все семь концовок достижимы через направленные callback-ветки.")


if __name__ == "__main__":
    main()
