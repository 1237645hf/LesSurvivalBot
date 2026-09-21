from game_state import GameState


def test_game_state_inventory_uses_unified_match_key():
    state = GameState()
    assert "Спички" in state.inventory
    assert "Спички 🔥" not in state.inventory
