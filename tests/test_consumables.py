import pytest
from main import Game, use_consumable


def test_use_consumable_water():
    """Вода: проверяем списание и рост жажды."""
    game = Game()
    game.thirst = 25
    game.inventory = {'Вода': 5}
    use_consumable('Вода', game)
    assert game.thirst > 25
    assert game.inventory.get('Вода', 0) < 5


def test_use_consumable_food():
    """Еда: проверяем списание и рост голода."""
    game = Game()
    game.hunger = 20
    game.inventory = {'Еда': 3}
    use_consumable('Еда', game)
    assert game.hunger > 20
    assert game.inventory['Еда'] == 2


def test_use_consumable_potion():
    """Зелья: проверяем восстановление HP."""
    game = Game()
    game.hp = 50
    game.inventory = {'Зелье здоровья': 2}
    use_consumable('Зелье здоровья', game)
    assert game.hp == 75
    assert game.inventory['Зелье здоровья'] == 1


def test_use_consumable_berry_and_mushroom():
    """Ягода и Гриб: проверяем базовое списание."""
    game = Game()
    game.hunger = 20
    game.inventory = {'Ягода': 1, 'Гриб': 1}
    
    use_consumable('Ягода', game)
    assert game.hunger > 20
    assert 'Ягода' not in game.inventory

    use_consumable('Гриб', game)
    assert 'Гриб' not in game.inventory