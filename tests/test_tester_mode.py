import pytest
from game_state import Game
from services.tester import (
    is_tester,
    enable_test_mode,
    apply_equipment_set,
    toggle_pet_status,
    get_tester_main_menu_kb,
    get_tester_loc_stories_kb,
    get_tester_combat_menu_kb,
    get_tester_sets_menu_kb,
    LOCATION_STORIES,
)
from services.database import save_game, MemoryPlayersCollection
import services.database as db
from keyboards import get_settings_kb, get_main_kb, get_inventory_kb
from crafts import can_craft, do_craft, get_craft_menu_kb


def test_tester_authorization():
    assert is_tester(906082819) is True
    assert is_tester(111222333444) is False


def test_enable_test_mode():
    game = Game()
    enable_test_mode(game)
    assert game.is_test_mode is True
    assert game.inventory.get("Спички") == 1000
    assert game.inventory.get("Сланцевый панцирь") == 1000
    assert game.locations_unlocked is True
    assert len(game.unlocked_locations) == 7
    assert game.hp == 100
    assert game.hunger == 100
    assert game.thirst == 100


def test_database_isolation():
    game = Game()
    enable_test_mode(game)
    # save_game should return True but not write to MongoDB or players_collection
    saved = save_game(906082819, game)
    assert saved is True


def test_pet_toggle():
    game = Game()
    assert game.is_story_flag_set("has_pet") is False
    # toggle on
    res = toggle_pet_status(game)
    assert res is True
    assert game.is_story_flag_set("has_pet") is True
    assert game.pet_name is not None
    # toggle off
    res2 = toggle_pet_status(game)
    assert res2 is False
    assert game.is_story_flag_set("has_pet") is False


def test_apply_sets():
    game = Game()
    title = apply_equipment_set(game, "slate")
    assert "Сланцевый" in title
    assert game.equipment.get("head") == "Сланцевая маска"
    assert game.equipment.get("body") == "Сланцевый панцирь"

    title2 = apply_equipment_set(game, "fur")
    assert "Меховой" in title2
    assert game.equipment.get("head") == "Меховой капюшон"


def test_crafts_in_test_mode():
    game = Game()
    enable_test_mode(game)
    # Can craft slate armor multiple times without restriction
    assert can_craft(game, "Сланцевый панцирь") is True
    # Do craft
    success, msg = do_craft(game, "Сланцевый панцирь")
    assert success is True
    # Can craft again!
    success2, msg2 = do_craft(game, "Сланцевый панцирь")
    assert success2 is True


def test_inventory_pagination():
    game = Game()
    enable_test_mode(game)
    total_pages = game.get_inventory_total_pages(per_page=15)
    assert total_pages > 1

    text_p0 = game.get_inventory_text(page=0, per_page=15)
    assert f"Стр. 1/{total_pages}" in text_p0

    text_p1 = game.get_inventory_text(page=1, per_page=15)
    assert f"Стр. 2/{total_pages}" in text_p1

    kb = get_inventory_kb(game, page=0)
    # check that pagination row exists in keyboard
    callbacks = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert any("inv_page_" in c for c in callbacks)


def test_keyboards_integration():
    game = Game()
    # settings kb for tester
    kb_tester = get_settings_kb(game, uid=906082819)
    cb_tester = [b.callback_data for row in kb_tester.inline_keyboard for b in row]
    assert "tester_toggle_mode" in cb_tester

    # settings kb for normal player
    kb_normal = get_settings_kb(game, uid=123)
    cb_normal = [b.callback_data for row in kb_normal.inline_keyboard for b in row]
    assert "tester_toggle_mode" not in cb_normal

    # main kb in test mode
    enable_test_mode(game)
    main_kb = get_main_kb(game)
    cb_main = [b.callback_data for row in main_kb.inline_keyboard for b in row]
    assert "tester_loc_stories" in cb_main
    assert "tester_main_menu" in cb_main
