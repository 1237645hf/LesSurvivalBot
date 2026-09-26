"""
tests/test_bmw_and_stream_items.py — Тесты слота спины, пакета «BMW» и сюжетных предметов Ручья:
1. Пакет «BMW» — только подпись в UI, не предмет:
   - У нового персонажа слот Спина = «⚪ Пакет «BMW»», equipment['back'] is None.
   - Никаких «Пакет «BMW»» / «Пакет BMW» нет в ITEMS и inventory.
2. Смена экипировки слота Спина:
   - При надетом рюкзаке в UI отображается рюкзак.
   - При снятии (equipment['back'] = None) снова показывается «⚪ Пакет «BMW»».
3. Реестр предметов ITEMS (модуль modules/items.py):
   - «Рюкзак с красной заплаткой» (tool, can_use=False, stackable=False).
   - «Плоская металлическая коробочка» (quest, can_use=True, stackable=False, note).
   - «Записка с наброском местности» (quest, can_use=True, stackable=False).
4. Эмодзи и действия в карточке:
   - Канонические эмодзи 🎒, 🗃️, 📜.
   - Кнопка «🎒 Надеть на спину» в карточке рюкзака.
   - Экипировка через handle_craft('use_item_Рюкзак с красной заплаткой').
"""

import pytest
from game_state import GameState
from modules.items import (
    ITEMS,
    ITEM_EMOJIS,
    get_item_emoji,
    format_item_card,
    is_item_consumable,
)
from keyboards import get_item_card_actions_kb
from crafts import handle_craft


def test_bmw_package_is_ui_only_not_an_item():
    """Тест 1: Пакет «BMW» отображается в слоте спины по умолчанию, но не является предметом."""
    game = GameState()
    game.player_name = "Бродяга"

    # 1. Проверяем слот спины в состоянии персонажа
    assert game.equipment.get("back") is None

    # 2. Проверяем отсутствие в ITEMS и inventory
    assert "Пакет «BMW»" not in ITEMS
    assert "Пакет BMW" not in ITEMS
    assert "Пакет «BMW»" not in game.inventory
    assert "Пакет BMW" not in game.inventory

    # 3. В интерфейсе экрана персонажа слот спины отображает «⚪ Пакет «BMW»»
    char_text = game.get_character_text()
    assert "🎒 Спина:\n⚪ Пакет «BMW»" in char_text


def test_back_slot_equip_and_unequip_backpack():
    """Тест 2: Надеть рюкзак -> отображается рюкзак. Снять -> возвращается «⚪ Пакет «BMW»»."""
    game = GameState()

    # По умолчанию пустой слот -> Пакет «BMW»
    assert "⚪ Пакет «BMW»" in game.get_character_text()

    # Надеваем рюкзак
    game.equipment["back"] = "Рюкзак с красной заплаткой"
    text_equipped = game.get_character_text()
    assert "🎒 Спина:\nРюкзак с красной заплаткой" in text_equipped
    assert "⚪ Пакет «BMW»" not in text_equipped

    # Снимаем рюкзак (слот снова None) -> снова Пакет «BMW»
    game.equipment["back"] = None
    text_unequipped = game.get_character_text()
    assert "🎒 Спина:\n⚪ Пакет «BMW»" in text_unequipped


def test_stream_items_registry_canonical_data():
    """Тест 3: Три предмета в ITEMS с каноническими описаниями и свойствами."""
    assert "Рюкзак с красной заплаткой" in ITEMS
    assert "Плоская металлическая коробочка" in ITEMS
    assert "Записка с наброском местности" in ITEMS

    # Рюкзак с красной заплаткой
    bp = ITEMS["Рюкзак с красной заплаткой"]
    assert bp["type"] == "tool"
    assert bp["can_use"] is False
    assert bp["stackable"] is False
    assert bp["note"] == "Можно надеть на спину."
    assert bp["description"] == (
        "Небольшой выцветший рюкзак, вытащенный из ручья. На боку красная заплатка. "
        "Ткань ещё крепкая, застёжки тугие — хабар не высыпется даже если бежать без оглядки."
    )

    # Плоская металлическая коробочка
    box = ITEMS["Плоская металлическая коробочка"]
    assert box["type"] == "quest"
    assert box["can_use"] is True
    assert box["stackable"] is False
    assert box["note"] == "Лежала во внутреннем кармане рюкзака, под заплаткой."
    assert box["description"] == (
        "Тонкая коробочка из тусклого металла с плотной защёлкой. "
        "Внутри сухо, хотя вещь долго пробыла в воде."
    )

    # Записка с наброском местности
    note = ITEMS["Записка с наброском местности"]
    assert note["type"] == "quest"
    assert note["can_use"] is True
    assert note["stackable"] is False
    assert note["description"] == (
        "Сухой лист со схемой переправы и припиской: "
        "«Ручей переходить выше поваленной берёзы. В низине после темноты виден огонь. Я туда не ходил»."
    )


def test_stream_items_emojis_and_cards():
    """Тест 4: Канонические эмодзи и карточки предметов."""
    assert get_item_emoji("Рюкзак с красной заплаткой") == "🎒"
    assert get_item_emoji("Плоская металлическая коробочка") == "🗃️"
    assert get_item_emoji("Записка с наброском местности") == "📜"

    # Квестовые предметы не расходуются и не дают кнопок съесть/выпить
    assert is_item_consumable("Плоская металлическая коробочка") is False
    assert is_item_consumable("Записка с наброском местности") is False
    assert is_item_consumable("Рюкзак с красной заплаткой") is False

    # Карточка рюкзака содержит кнопку надеть на спину
    kb = get_item_card_actions_kb("Рюкзак с красной заплаткой")
    btn_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    btn_cbs = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "🎒 Надеть на спину" in btn_texts
    assert "use_item_Рюкзак с красной заплаткой" in btn_cbs

    # Карточки коробочки и записки не содержат кнопки съесть/применить
    kb_box = get_item_card_actions_kb("Плоская металлическая коробочка")
    btn_box_texts = [btn.text for row in kb_box.inline_keyboard for btn in row]
    assert not any("Съесть" in t for t in btn_box_texts)

    kb_note = get_item_card_actions_kb("Записка с наброском местности")
    btn_note_texts = [btn.text for row in kb_note.inline_keyboard for btn in row]
    assert not any("Съесть" in t for t in btn_note_texts)

    # Проверка карточки рюкзака
    card_bp = format_item_card("Рюкзак с красной заплаткой")
    assert "🎒 Рюкзак с красной заплаткой" in card_bp
    assert "Небольшой выцветший рюкзак" in card_bp


def test_equip_backpack_via_handle_craft():
    """Тест 5: Экипировка рюкзака через handle_craft."""
    game = GameState()
    game.inventory["Рюкзак с красной заплаткой"] = 1
    game.equipment["back"] = None

    text, kb = handle_craft("use_item_Рюкзак с красной заплаткой", game, 1001)

    assert game.equipment.get("back") == "Рюкзак с красной заплаткой"
    assert game.inventory.get("Рюкзак с красной заплаткой", 0) == 0
    assert any("Вы надели рюкзак с красной заплаткой на спину." in log for log in game.event_log)
    assert "Рюкзак с красной заплаткой" in game.get_character_text()
