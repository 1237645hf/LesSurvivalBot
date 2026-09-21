from game_state import GameState
from location_stories import (
    ENDING_STORY_TEXT,
    LOCATION_SOURCE_TEXTS,
    ending_text,
    get_location_source_text,
    resolve_ending,
)


def test_story_sources_are_available_without_text_normalization():
    assert set(LOCATION_SOURCE_TEXTS) == set(range(1, 8))
    assert get_location_source_text(1) == LOCATION_SOURCE_TEXTS[1]
    assert get_location_source_text(7) == LOCATION_SOURCE_TEXTS[7]
    assert ending_text("guardian").startswith("Ты поднимаешься на вершину")


def test_state_round_trip_preserves_flags_and_compact_route():
    state = GameState()
    state.set_story_flag("deer_freed")
    state.record_route("hunters_free_deer")

    restored = GameState.from_document(state.to_document())

    assert restored.story_flags == {"deer_freed": True}
    assert restored.compact_route == ["hunters_free_deer"]


def test_guardian_has_priority_over_distant_smoke():
    state = GameState(
        narrative_karma={
            "intervention": 8,
            "compassion": 8,
            "pragmatism": 4,
            "observation": 4,
        },
        story_flags={
            "has_pet": True,
            "deer_freed": True,
            "left_warning": True,
        },
    )

    assert resolve_ending(state) == "guardian"


def test_fifteen_marks_is_selected_at_observation_threshold():
    state = GameState(
        narrative_karma={
            "intervention": 4,
            "compassion": 0,
            "pragmatism": 0,
            "observation": 12,
        },
    )

    assert resolve_ending(state) == "fifteen_marks"