from game_state import GameState
from keyboards import get_main_kb


def test_status_bar_is_compact_and_has_day_label():
    game = GameState()
    game.hp = 100
    game.hunger = 20
    game.thirst = 50
    game.ap = 5
    game.weather = "clear"
    game.day = 1

    ui = game.get_ui()

    assert "❤️100|🍖20|💧50|⚡5|☀️День 1" in ui
    assert " ❤️ " not in ui


def test_status_bar_removes_day_label_when_it_exceeds_width():
    game = GameState(display_mode="phone", max_line_length=29)
    game.hp = 100
    game.hunger = 20
    game.thirst = 50
    game.ap = 5
    game.weather = "clear"
    game.day = 1

    status = game.get_status_bar(game.max_line_length)

    assert status == "❤️100|🍖20|💧50|⚡5|☀️1"
    assert "День" not in status


def test_collect_water_button_only_in_rainy_weather():
    game = GameState()
    game.weather = "clear"
    assert not any(
        button.callback_data == "action_collect_water"
        for row in get_main_kb(game).inline_keyboard
        for button in row
    )

    game.weather = "rain"
    assert any(
        button.callback_data == "action_collect_water"
        for row in get_main_kb(game).inline_keyboard
        for button in row
    )

    game.weather = "storm"
    assert any(
        button.callback_data == "action_collect_water"
        for row in get_main_kb(game).inline_keyboard
        for button in row
    )


def test_weather_roll_returns_supported_types():
    game = GameState()
    weather = game.roll_weather_for_new_day()
    assert weather in {"clear", "cloudy", "rain", "storm"}
