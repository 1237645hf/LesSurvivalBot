import pytest
from game_state import GameState
from modules.finds import location_id_from_game, roll_find, LOCATION_FINDS
from story.location_stories import handle_story
from story.locations.loc5_slug_pit import handle_location_5_slug_pit


@pytest.mark.nav
def test_location_id_from_game_mapping_and_synchronization():
    """Проверяет маппинг строковых названий и корней в id и синхронизацию location_index."""
    game = GameState()
    
    # 1. Стартовый лес
    game.current_location = "Стартовый лес"
    assert location_id_from_game(game) == 1
    assert game.location_index == 0

    # 2. Ручей со змеями
    game.current_location = "Ручей со змеями"
    assert location_id_from_game(game) == 2
    assert game.location_index == 1

    # 3. Скромная лощина
    game.current_location = "Скромная лощина"
    assert location_id_from_game(game) == 3
    assert game.location_index == 2

    # 4. Просека охотников
    game.current_location = "Просека охотников"
    assert location_id_from_game(game) == 4
    assert game.location_index == 3

    # 5. Яр Слаймов
    game.current_location = "Яр Слаймов"
    assert location_id_from_game(game) == 5
    assert game.location_index == 4

    # 6. Мохнатая пещера
    game.current_location = "Мохнатая пещера"
    assert location_id_from_game(game) == 6
    assert game.location_index == 5

    # 7. Святилище
    game.current_location = "Святилище"
    assert location_id_from_game(game) == 7
    assert game.location_index == 6


@pytest.mark.nav
def test_location_id_from_game_root_variations():
    """Проверяет устойчивость к падежам и вариациям через корни слов."""
    game = GameState()

    game.current_location = "в темном лесу"
    assert location_id_from_game(game) == 1

    game.current_location = "возле ручья"
    assert location_id_from_game(game) == 2

    game.current_location = "в лощине"
    assert location_id_from_game(game) == 3

    game.current_location = "на просеке"
    assert location_id_from_game(game) == 4

    game.current_location = "Яр Слизней"
    assert location_id_from_game(game) == 5

    game.current_location = "пещера"
    assert location_id_from_game(game) == 6

    game.current_location = "на вершине святилища"
    assert location_id_from_game(game) == 7


@pytest.mark.mech
@pytest.mark.l2
def test_l2_finds_yield_l2_loot_not_l1():
    """
    Проверяет, что при нахождении на L2 (Ручей со змеями) поиск ресурсов
    выдаёт лут из таблицы L2 ('Красная ягода', 'Сланцевая пластина' и т.д.)
    и никогда не выдаёт эксклюзивные предметы L1 ('Лесная ягода', 'Лесной гриб', 'Мох').
    """
    game = GameState()
    game.current_location = "Ручей со змеями"

    loc_id = location_id_from_game(game)
    assert loc_id == 2
    assert game.location_index == 1

    l1_exclusive = {"Лесная ягода", "Лесной гриб", "Мох"}
    l2_possible = {entry["item"] for entry in LOCATION_FINDS[2]} | {"Кусок коры"}

    found_any_l2_specific = False

    for _ in range(50):
        items = roll_find(loc_id, game.inventory)
        for it in items:
            assert it not in l1_exclusive, f"Предмет L1 '{it}' выпал на L2!"
            assert it in l2_possible, f"Неожиданный предмет '{it}' на L2"
            if it in ("Красная ягода", "Сланцевая пластина"):
                found_any_l2_specific = True

    assert found_any_l2_specific, "Специфичный для L2 лут должен был выпасть хотя бы раз за 50 бросков"


@pytest.mark.nav
def test_story_transitions_synchronize_location_and_index():
    """Проверяет синхронную установку current_location, location_index и pre_story_location."""
    game = GameState()
    game.unlocked_locations = [
        "Стартовый лес", "Ручей со змеями", "Скромная лощина",
        "Просека охотников", "Яр Слаймов", "Мохнатая пещера", "Святилище"
    ]

    for loc_id in range(1, 8):
        cb = f"location_enter_{loc_id}"
        handle_story(cb, game, 100)
        assert game.location_index == loc_id - 1
        assert game.current_location == game.pre_story_location


@pytest.mark.nav
def test_pre_story_location_preserved_on_back_navigation():
    """Проверяет возврат в исходную локацию через handle_back_navigation."""
    from game_state import handle_back_navigation
    game = GameState()
    game.unlocked_locations = ["Стартовый лес", "Ручей со змеями"]
    game.current_location = "Ручей со змеями"
    game.location_index = 1

    # Симулируем переход в подменю при активном pre_story_location
    game.pre_story_location = "Ручей со змеями"
    game.push_screen("inventory")

    # Игрок нажимает Назад к лагерю
    text, kb = handle_back_navigation(game, 100)
    assert game.current_location == "Ручей со змеями"
    assert game.location_index == 1
    assert game.pre_story_location is None


@pytest.mark.nav
def test_l5_scout_leave_to_camp_preserves_location():
    """Проверяет, что выход из разведки L5 (до победы над боссом) не сбрасывает локацию в Стартовый лес."""
    game = GameState()
    game.unlocked_locations = ["Стартовый лес", "Ручей со змеями", "Яр Слаймов"]
    game.current_location = "Яр Слаймов"
    game.location_index = 4
    game.pre_story_location = "Яр Слаймов"

    text, kb = handle_location_5_slug_pit("l5_scout_leave_to_camp", game, 100)
    assert game.current_location == "Яр Слаймов"
    assert game.location_index == 4
    assert game.active_story_callback is None
    assert game.story_state is None
