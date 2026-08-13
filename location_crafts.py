"""
location_crafts.py — Локальные системы крафта для каждой локации.
Каждая локация имеет свои уникальные предметы-ключи и сет брони, крафтящийся из локальных ресурсов.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import get_main_kb, get_location_kb
from game_state import GameState


def handle_craft_location_2_ruchey(data, game, uid):
    """Крафт и использование предметов для Локации 2: Ручей с Змеями."""
    
    text = None
    kb = None
    
    if data == "craft_Slate_Plate":
        # Сланцевая пластина — ключ к крафту сет-браны
        if game.inventory.get("Спички", 0) < 1:
            return None, None
        game.inventory["Спички"] -= 1
        game.inventory["Сланцевая пластина"] = game.inventory.get("Сланцевая пластина", 0) + 1
        game.add_log("Вы скрафтили сланцевую пластину — основу для сет-браны!")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
        
    elif data == "use_item_Slate_Plate":
        # Экипировать сланцевую пластину на голову
        if game.inventory.get("Сланцевая пластина", 0) > 0 and game.equipment["head"] is None:
            game.inventory["Сланцевая пластина"] -= 1
            game.equipment["head"] = "Сланцевая пластина"
            game.add_log("Вы экипировали сланцевую пластину на голову.")
            text = game.get_ui()
            kb = get_location_kb(game, 2)  # Location 2 keyboard
        else:
            game.add_log("Сланцевая пластина уже экипирована!")
            text = game.get_ui()
            kb = get_location_kb(game, 2)
    
    elif data == "craft_Slate_Helmet":
        # Крафт шлема из сланца + воды
        if game.inventory.get("Сланцевая пластина", 0) < 1 or game.inventory.get("Вода", 0) < 1:
            return None, None
        game.inventory["Сланцевая пластина"] -= 1
        game.inventory["Вода"] -= 1
        game.inventory["Сланевый шлем"] = game.inventory.get("Сланевый шлем", 0) + 1
        game.add_log("Скрафтили Сланевый шлем! Теперь голова защищена.")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
        
    elif data == "use_item_Slate_Helmet":
        # Надеть шлем
        if game.inventory.get("Сланевый шлем", 0) > 0 and game.equipment["head"] is None:
            game.inventory["Сланевый шлем"] -= 1
            game.equipment["head"] = "Сланевый шлем"
            game.add_log("Шлем на голове. Защита от змеиных шипов!")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("Шлем уже на голове!")
            text = game.get_ui()
            kb = get_main_kb(game)
    
    elif data == "craft_Slate_Chest":
        # Крафт грудной брони из сланца + ветки
        if game.inventory.get("Сланцевая пластина", 0) < 1 or game.inventory.get("Ветка", 0) < 1:
            return None, None
        game.inventory["Сланцевая пластина"] -= 1
        game.inventory["Ветка"] -= 1
        game.inventory["Сланевая броня"] = game.inventory.get("Сланевая броня", 0) + 1
        game.add_log("Скрафтили Сланевую броню! Грудь защищена.")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
        
    elif data == "use_item_Slate_Chest":
        # Надеть броню
        if game.inventory.get("Сланевая броня", 0) > 0 and game.equipment["chest"] is None:
            game.inventory["Сланевая броня"] -= 1
            game.equipment["chest"] = "Сланевая броня"
            game.add_log("Броня на груди. Вы чувствуете себя неприступно!")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("Броня уже на груди!")
            text = game.get_ui()
            kb = get_main_kb(game)
    
    return text, kb


def handle_craft_location_3_slate_hollow(data, game, uid):
    """Крафт для Локации 3: Скромоная Лощина — глиняные слитки."""
    
    text = None
    kb = None
    
    if data == "craft_Slate_Slate":
        # Ключевой предмет локации
        if game.inventory.get("Глина", 0) < 1:
            return None, None
        game.inventory["Глина"] -= 1
        game.inventory["Сланцевой слиток"] = game.inventory.get("Сланцевой слиток", 0) + 1
        game.add_log("Вы нашли сланцевой слиток — сердце крафтов локации!")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
        
    elif data == "craft_Slate_Helmet_2":
        # Шлем из слитка + воды
        if game.inventory.get("Сланцевой слиток", 0) < 1 or game.inventory.get("Вода", 0) < 1:
            return None, None
        game.inventory["Сланцевой слиток"] -= 1
        game.inventory["Вода"] -= 1
        game.inventory["Сланевый шлем II"] = game.inventory.get("Сланевый шлем II", 0) + 1
        game.add_log("Скрафтили улучшенный шлем из сланца!")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
        
    elif data == "craft_Slate_Chest_2":
        # Грудь из слитка + еды
        if game.inventory.get("Сланцевой слиток", 0) < 1 or game.inventory.get("Еда", 0) < 1:
            return None, None
        game.inventory["Сланцевой слиток"] -= 1
        game.inventory["Еда"] -= 1
        game.inventory["Сланевая броня II"] = game.inventory.get("Сланевая броня II", 0) + 1
        game.add_log("Скрафтили улучшенную броню из сланца!")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
    
    return text, kb


def handle_craft_location_6_furry_cave(data, game, uid):
    """Крафт для Локации 6: Мохнатая Пещера — меховые шкуры."""
    
    text = None
    kb = None
    
    if data == "craft_Fur_Pelt":
        # Ключевой предмет локации
        if game.inventory.get("Мех", 0) < 1:
            return None, None
        game.inventory["Мех"] -= 1
        game.inventory["Меховой шкуры"] = game.inventory.get("Меховой шкуры", 0) + 1
        game.add_log("Вы нашли меховой шкур — уют для пещеры!")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
        
    elif data == "craft_Fur_Helmet":
        # Шлем из меха + воды
        if game.inventory.get("Меховой шкуры", 0) < 1 or game.inventory.get("Вода", 0) < 1:
            return None, None
        game.inventory["Меховой шкуры"] -= 1
        game.inventory["Вода"] -= 1
        game.inventory["Меховой шлем"] = game.inventory.get("Меховой шлем", 0) + 1
        game.add_log("Скрафтили Меховой шлем! Тепло и уютно.")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
        
    elif data == "craft_Fur_Chest":
        # Грудь из меха + ветки
        if game.inventory.get("Меховой шкуры", 0) < 1 or game.inventory.get("Ветка", 0) < 1:
            return None, None
        game.inventory["Меховой шкуры"] -= 1
        game.inventory["Ветка"] -= 1
        game.inventory["Меховая броня"] = game.inventory.get("Меховая броня", 0) + 1
        game.add_log("Скрафтили Меховую броню! Тепло и защищено.")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
    
    return text, kb


def handle_use_item(data, game, uid):
    """Общие функции для использования предметов."""
    
    text = None
    kb = None
    
    if data == "use_item_Slate_Plate":
        if game.inventory.get("Сланцевая пластина", 0) > 0 and game.equipment["head"] is None:
            game.inventory["Сланцевая пластина"] -= 1
            game.equipment["head"] = "Сланцевая пластина"
            game.add_log("Вы экипировали сланцевую пластину на голову.")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("Сланцевая пластина уже экипирована!")
            text = game.get_ui()
            kb = get_main_kb(game)
    
    elif data == "use_item_Slate_Helmet":
        if game.inventory.get("Сланевый шлем", 0) > 0 and game.equipment["head"] is None:
            game.inventory["Сланевый шлем"] -= 1
            game.equipment["head"] = "Сланевый шлем"
            game.add_log("Шлем на голове. Защита от змеиных шипов!")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("Шлем уже на голове!")
            text = game.get_ui()
            kb = get_main_kb(game)
            
    elif data == "use_item_Slate_Chest":
        if game.inventory.get("Сланевая броня", 0) > 0 and game.equipment["chest"] is None:
            game.inventory["Сланевая броня"] -= 1
            game.equipment["chest"] = "Сланевая броня"
            game.add_log("Броня на груди. Вы чувствуете себя неприступно!")
            text = game.get_ui()
            kb = get_main_kb(game)
        else:
            game.add_log("Броня уже на груди!")
            text = game.get_ui()
            kb = get_main_kb(game)
    
    return text, kb


# Export functions for easy importing
handle_craft = handle_craft_location_2_ruchey
handle_use_item = handle_use_item


# Make location-specific handlers available
handle_craft_location_3 = handle_craft_location_3_slate_hollow
handle_craft_location_6 = handle_craft_location_6_furry_cave


def handle_craft_location_4_hunters_glade(data, game, uid):
    """Крафт для Локации 4: Просека Охотников — охотничье снаряжение."""
    
    text = None
    kb = None
    
    if data == "craft_Hunter_Trap":
        # Охотничья ловушка из веток + кожи
        if game.inventory.get("Ветка", 0) < 2 or game.inventory.get("Кожа", 0) < 1:
            return None, None
        game.inventory["Ветка"] -= 2
        game.inventory["Кожа"] -= 1
        game.inventory["Охотничья ловушка"] = game.inventory.get("Охотничья ловушка", 0) + 1
        game.add_log("Скрафтили охотничью ловушку!")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
    
    return text, kb


def handle_craft_location_5_slug_pit(data, game, uid):
    """Крафт для Локации 5: Яр Слизней — грибные артефакты."""
    
    text = None
    kb = None
    
    if data == "craft_Mushroom_Cap":
        # Грибная шапка из слизи + грибов
        if game.inventory.get("Грибы", 0) < 1 or game.inventory.get("Слизь", 0) < 1:
            return None, None
        game.inventory["Грибы"] -= 1
        game.inventory["Слизь"] -= 1
        game.inventory["Грибная шапка"] = game.inventory.get("Грибная шапка", 0) + 1
        game.add_log("Скрафтили грибную шапку! Странный предмет...")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
    
    return text, kb


def handle_craft_location_7_sanctuary_peak(data, game, uid):
    """Крафт для Локации 7: Вершина Святилища — священные артефакты."""
    
    text = None
    kb = None
    
    if data == "craft_Sacred_Water":
        # Святая вода - конечный крафт
        if game.inventory.get("Вода", 0) < 1:
            return None, None
        # Святая вода крафтится только если игрок достиг святилища
        game.inventory["Вода"] -= 1
        game.inventory["Святая вода"] = game.inventory.get("Святая вода", 0) + 1
        game.add_log("Ты наполнил чашу святилища. Вода светится... святой!")
        text = game.get_inventory_text()
        kb = get_main_kb(game)
    
    return text, kb


# Aliases для удобства
handle_craft_location_4 = handle_craft_location_4_hunters_glade
handle_craft_location_5 = handle_craft_location_5_slug_pit
handle_craft_location_7 = handle_craft_location_7_sanctuary_peak