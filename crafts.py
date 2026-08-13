from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import inventory_inline_kb, get_main_kb

def handle_craft(data, game, uid):
    text = None
    kb = None
    if data == "craft_Факел":
        # Используем Спички вместо "Спички " для совместимости
        spichki_key = "Спички " if "Спички " in game.inventory else "Спички 🔥"
        if game.inventory.get(spichki_key, 0) < 1 or game.inventory.get("Ветка", 0) < 1:
            return None, None  # Handled in main with answer
        game.inventory[spichki_key] -= 1
        game.inventory["Ветка"] -= 1
        game.inventory["Факел"] = game.inventory.get("Факел", 0) + 1
        game.add_log("Вы скрафтили факел.")
        text = game.get_inventory_text()
        kb = inventory_inline_kb
    elif data == "use_item_Факел":
        if game.inventory.get("Факел", 0) > 0:
            # Проверяем есть ли поле hand или equipment для рук
            hand_field = "hand" if "hand" in game.equipment else "hands"
            if game.equipment.get(hand_field) is None:
                game.inventory["Факел"] -= 1
                game.equipment[hand_field] = "Факел"
                game.add_log("Вы экипировали факел в руку.")
                text = game.get_ui()
                kb = get_main_kb(game)
            else:
                game.add_log("У вас уже что-то в руке.")
                text = game.get_ui()
                kb = get_main_kb(game)
        else:
            game.add_log("Нельзя экипировать факел сейчас.")
            text = game.get_ui()
            kb = get_main_kb(game)
    return text, kb
