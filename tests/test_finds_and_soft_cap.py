"""
tests/test_finds_and_soft_cap.py — Тесты баланса лута, soft cap и пустых находок.
"""

import pytest
from game_state import GameState
from modules.finds import (
    LOCATION_FINDS,
    BONUS_FINDS,
    RESOURCE_SOFT_CAPS,
    EMPTY_FIND_PHRASES,
    BERRY_MUSHROOM_NAMES,
    roll_find,
    apply_finds_to_inventory,
    _apply_soft_cap,
    _roll_table,
)


def test_location_finds_tables_weights_and_names():
    """Проверка точного соответствия таблиц L1–L7 по предметам и весам (сумма 100)."""
    expected = {
        1: {"Ветка": 35, "Лесная ягода": 20, "Лесной гриб": 20, "Камень": 15, "Мох": 10},
        2: {"Ветка": 40, "Красная ягода": 25, "Камень": 25, "Сланцевая пластина": 10},
        3: {"Сланец": 30, "Ветка": 25, "Фиолетовая ягода": 20, "Дикий гриб": 20, "Сухой мох": 5},
        4: {"Ветка": 40, "Лесная ягода": 20, "Лесной гриб": 20, "Кость": 10, "Кожа": 10},
        5: {"Слизь": 35, "Ветка": 30, "Болотная ягода": 20, "Болотный гриб": 10, "Светящийся гриб": 5},
        6: {"Ветка": 35, "Пещерный гриб": 25, "Камень": 25, "Пещерный мох": 15},
        7: {"Ветка": 25, "Камень": 25, "Горная ягода": 20, "Горный гриб": 20, "Горный лишайник": 10},
    }

    for loc_id, items_dict in expected.items():
        assert loc_id in LOCATION_FINDS, f"Локация {loc_id} отсутствует в LOCATION_FINDS"
        table = LOCATION_FINDS[loc_id]
        actual_weights = {entry["item"]: entry["chance"] for entry in table}
        assert actual_weights == items_dict, f"Несовпадение весов на L{loc_id}: {actual_weights} != {items_dict}"
        total_weight = sum(actual_weights.values())
        assert total_weight == 100, f"Сумма весов на L{loc_id} равна {total_weight}, ожидалось 100"


def test_berry_and_mushroom_drop_quantity():
    """Ягода/гриб выпадают в количестве ровно 1 или 2 шт."""
    single_berry_table = [{"item": "Лесная ягода", "chance": 100}]
    results = [_roll_table(single_berry_table) for _ in range(50)]
    counts = [len(r) for r in results]
    assert all(c in (1, 2) for c in counts)
    assert 1 in counts and 2 in counts

    single_mushroom_table = [{"item": "Пещерный гриб", "chance": 100}]
    results_m = [_roll_table(single_mushroom_table) for _ in range(50)]
    counts_m = [len(r) for r in results_m]
    assert all(c in (1, 2) for c in counts_m)
    assert 1 in counts_m and 2 in counts_m


def test_soft_cap_batch_filtering():
    """Soft cap фильтрует пакет ресурса целиком (не поштучно) и снижает шанс при высоком have."""
    # Пакет из двух грибов: либо остаются оба, либо отбрасываются оба
    raw = ["Лесной гриб", "Лесной гриб"]
    # have = 65 (hard cap 60), p = 0.10
    filtered_results = [_apply_soft_cap(list(raw), {"Лесной гриб": 65}) for _ in range(50)]
    for res in filtered_results:
        assert len(res) in (0, 2), "Пакет не должен дробиться поштучно!"

    # При have >= hard (65) шанс 0.10: большинство должно быть отброшено
    kept_count_hard = sum(1 for res in filtered_results if len(res) == 2)
    assert 0 <= kept_count_hard <= 20  # в среднем ~5 из 50

    # При have < soft (10 грибов при soft=40, hard=60), p = 1.0 (всегда 100% успех)
    filtered_low = [_apply_soft_cap(list(raw), {"Лесной гриб": 10}) for _ in range(50)]
    assert all(len(res) == 2 for res in filtered_low)

    # При inventory=None: всегда p = 1.0
    filtered_none = [_apply_soft_cap(list(raw), None) for _ in range(50)]
    assert all(len(res) == 2 for res in filtered_none)


def test_empty_find_phrases():
    """При пустом списке лута возвращается одна из 5 канонических фраз."""
    game = GameState()
    expected_phrases = {
        "Ничего не нашёл.",
        "В этот раз не повезло.",
        "Всё обыскал, но пусто.",
        "Пусто.",
        "Повезёт в следующий раз.",
    }
    assert set(EMPTY_FIND_PHRASES) == expected_phrases

    results = {apply_finds_to_inventory(game, []) for _ in range(100)}
    assert results.issubset(expected_phrases)
    assert len(results) > 1  # возвращается не одна фиксированная фраза, а случайные из набора


def test_roll_find_integration_with_inventory():
    """Все вызовы roll_find с inventory и без inventory работают стабильно."""
    game = GameState()
    game.inventory = {
        "Ветка": 100,
        "Камень": 50,
        "Лесная ягода": 80,
    }

    for loc in range(1, 8):
        drops = roll_find(loc, game.inventory)
        assert isinstance(drops, list)
        msg = apply_finds_to_inventory(game, drops)
        assert isinstance(msg, str)
        assert len(msg) > 0
