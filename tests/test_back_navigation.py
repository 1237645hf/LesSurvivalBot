"""Регрессия: «Назад» / «В лагерь» и два режима (лагерь vs сюжетка)."""
import pytest
from game_state import GameState, handle_back_navigation
from keyboards import get_main_kb


def _camp_game(**kwargs) -> GameState:
    game = GameState()
    game.is_name_set = True
    game.character_name = "Выживший"
    game.player_name = "Выживший"
    for k, v in kwargs.items():
        setattr(game, k, v)
    return game


@pytest.mark.smoke
@pytest.mark.nav
def test_back_from_inventory_goes_to_camp_even_if_story_flag_left():
    """
    Баг: active_story_callback остался в сейве, игрок в лагере открыл инвентарь,
    «Назад» кидало обратно в сюжетку вместо главного экрана.
    """
    game = _camp_game(
        active_story_callback="l2_thorns_approach",
        nav_stack=["main", "inventory"],
    )

    text, kb = handle_back_navigation(game, uid=1)

    assert game.active_story_callback is None
    assert game.nav_stack == ["main"]
    assert kb is not None
    # Главный экран лагеря — не сюжетное окно терновника
    main_kb = get_main_kb(game)
    assert type(kb) is type(main_kb)
    # На главном есть действие исследования / инвентаря
    cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "action_2" in cbs or "action_1" in cbs


@pytest.mark.smoke
@pytest.mark.nav
def test_story_leave_camp_via_back_clears_story():
    """
    Кнопка «В лагерь» на сюжетке часто с callback_data="back".
    Должна реально выводить в лагерь и сбрасывать active_story_callback,
    а не зацикливать сцену.
    """
    game = _camp_game(
        active_story_callback="l2_thorns_approach",
        nav_stack=["main", "locations"],
    )

    text, kb = handle_back_navigation(game, uid=2)

    assert game.active_story_callback is None
    assert game.nav_stack == ["main"]
    assert text is not None
    assert kb is not None
    cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "action_2" in cbs or "action_1" in cbs


@pytest.mark.nav
def test_back_from_campfire_to_camp_clears_stale_story_flag():
    """Из костра «Назад» → лагерь, даже если в сейве висел старый сюжетный флаг."""
    game = _camp_game(
        active_story_callback="l4_1_entry",
        nav_stack=["main", "campfire"],
        campfire_active=True,
        campfire_durability=3,
    )

    text, kb = handle_back_navigation(game, uid=3)

    assert game.active_story_callback is None
    assert game.nav_stack == ["main"]
    assert kb is not None


@pytest.mark.nav
def test_back_inside_inventory_tree_stays_in_inventory():
    """
    «Назад» из подменю инвентаря (осмотр) должен вести в инвентарь,
    а не сразу в лагерь и не в сюжетку.
    """
    game = _camp_game(
        active_story_callback=None,
        nav_stack=["main", "inventory", "inspect"],
    )
    game.inventory["Спички"] = 2

    text, kb = handle_back_navigation(game, uid=4)

    assert game.active_story_callback is None
    assert game.nav_stack == ["main", "inventory"]
    assert kb is not None
    cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    # Типичные кнопки инвентаря
    assert "inv_inspect" in cbs or "inv_craft" in cbs or "back" in cbs


@pytest.mark.nav
def test_back_to_main_does_not_call_story_handler():
    """
    При выходе на main не должен подтягиваться старый сюжет
    (регресс ImportError/зацикливания через handle_story).
    """
    game = _camp_game(
        active_story_callback="location_enter_2",
        nav_stack=["main", "locations"],
    )

    text, kb = handle_back_navigation(game, uid=5)

    assert game.active_story_callback is None
    # Текст не обязан содержать маркеры сюжетки L2
    joined = (text or "").lower()
    assert "терновник" not in joined
    assert "проломиться" not in joined


@pytest.mark.nav
def test_get_craft_menu_kb_import_path_works_on_back_to_craft():
    """
    Регресс Render: get_craft_menu_kb импортировался из keyboards и падал.
    «Назад» на экран крафта должен отрабатывать без ImportError.
    """
    game = _camp_game(nav_stack=["main", "inventory", "craft", "recipes"])

    text, kb = handle_back_navigation(game, uid=6)

    assert game.nav_stack == ["main", "inventory", "craft"]
    assert kb is not None
    assert text is not None
