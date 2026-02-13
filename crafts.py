from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import inventory_inline_kb  # Import for back kb

def handle_craft(data, game, uid):
    text = None
    kb = None
    if data == "craft_Факел":
        if game.inventory.get("Спички 🔥", 0) < 1 or game.inventory.get("Ветка", 0) < 1:
            return None, None  # Handled in main with answer
        game.inventory["Спички 🔥"] -= 1
        game.inventory["Ветка"] -= 1
        game.inventory["Факел"] = game.inventory.get("Факел", 0) + 1
        game.add_log("Вы скрафтили факел.")
        game.add_log("Для крафта факела вам пришлось использовать носок с левой ноги.")
        text = game.get_inventory_text()
        kb = inventory_inline_kb
    elif data == "use_item_Факел":
        if game.inventory.get("Факел", 0) > 0 and game.equipment["hand"] is None:
            game.inventory["Факел"] -= 1
            game.equipment["hand"] = "Факел"
            game.add_log("Вы экипировали факел в руку.")
            text = game.get_ui()
            kb = get_main_kb(game)  # Assuming get_main_kb is imported or available
        else:
            game.add_log("Нельзя экипировать факел сейчас.")
            text = game.get_ui()
            kb = get_main_kb(game)
    return text, kb
