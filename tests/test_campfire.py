"""
Тесты механики костра (campfire) для game_state.py.
Проверяет: розжиг, списание прочности, игнор действий без AP, потухание.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_state import GameState


def run_campfire_tests():
    """Запуск серии микро-тестов костра."""
    
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 70)
    print("🔥 ТЕСТЫ МЕХАНИКИ КОСТРА 🔥")
    print("=" * 70)
    print()
    
    # --- ТЕСТ 1: РОЗЖИГ КОСТРА ---
    print("1️⃣  ТЕСТ РОЗЖИГА КОСТРА (light_campfire)")
    print("-" * 50)
    
    player = GameState()
    player.ap = 5  # Даем 5 AP для розжига
    # В стартовом инвентаре есть Спички: 3, розжиг спичками стоит 1 AP и 1 спичку
    
    print(f"   До: AP={player.ap}, Спички={player.inventory.get('Спички', 0)}, Костёр активен: {player.campfire_active}, "
          f"Прочность: {player.campfire_durability}/{player.campfire_max_durability}")
    
    result = player.light_campfire()
    
    print(f"   Результат: {result}")
    print(f"   После: AP={player.ap}, Спички={player.inventory.get('Спички', 0)}, Костёр активен: {player.campfire_active}, "
          f"Прочность: {player.campfire_durability}/{player.campfire_max_durability}")
    
    # Проверки (со спичками: тратится 1 AP и 1 спичка)
    checks = [
        ("AP потрачено ровно 1 (спичками)", player.ap == 4),
        ("Спичек осталось 2", player.inventory.get("Спички") == 2),
        ("Костёр активен", player.campfire_active == True),

        ("Прочность = 10", player.campfire_durability == 10),
        ("Макс. прочность = 10", player.campfire_max_durability == 10),
        ("Лог записан", len(player.event_log) > 1),
    ]
    
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"      {status} {name}")
    
    print()
    
    # --- ТЕСТ 2: СПИСАНИЕ ПРОЧНОСТИ ПРИ AP_COST > 0 ---
    print("2️⃣  ТЕСТ СПИСАНИЯ ПРОЧНОСТИ (consume_action, ap_cost=1)")
    print("-" * 50)
    
    result = player.consume_action(action_type="default", ap_cost=1)
    
    print(f"   Результат: {result}")
    print(f"   После: AP={player.ap}, Прочность: {player.campfire_durability}")
    
    checks = [
        ("AP списано до 3", player.ap == 3),
        ("Прочность 9/10", player.campfire_durability == 9),
        ("Костёр всё ещё горит", player.campfire_active == True),
    ]
    
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"      {status} {name}")
    
    print()
    
    # --- ТЕСТ 3: ИГНОРИРОВАНИЕ ДЕЙСТВИЙ БЕЗ AP (AP_COST == 0) ---
    print("3️⃣  ТЕСТ ИГНОРИРОВАНИЯ (consume_action, ap_cost=0)")
    print("-" * 50)
    
    # Восстанавливаем AP до 3
    player.ap = 3
    
    result = player.consume_action(action_type="no_ap_cost", ap_cost=0)
    
    print(f"   Результат: {result}")
    print(f"   После: AP={player.ap}, Прочность: {player.campfire_durability}")
    
    checks = [
        ("AP не изменилось", player.ap == 3),
        ("Прочность осталась 9", player.campfire_durability == 9),
        ("Костёр горит", player.campfire_active == True),
    ]
    
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"      {status} {name}")
    
    print()
    
    # --- ТЕСТ 4: ПОТУХАНИЕ ПРИ 0 ПРОЧНОСТИ ---
    print("4️⃣  ТЕСТ ПОТУХАНИЯ ПРИ 0 ПРОЧНОСТИ")
    print("-" * 50)
    
    # Устанавливаем прочность 1 и совершаем действие с ap_cost=1
    player.campfire_durability = 1
    player.ap = 2
    
    print(f"   До: Прочность={player.campfire_durability}, Активен: {player.campfire_active}")
    
    result = player.consume_action(action_type="default", ap_cost=1)
    
    print(f"   Результат: {result}")
    print(f"   После: Активен: {player.campfire_active}, Лог: {player.event_log[-1]}")
    
    checks = [
        ("Костёр потух", player.campfire_active == False),
        ("Лог содержит 'Костёр погас'", "Костёр погас" in player.event_log[-1]),
    ]
    
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"      {status} {name}")
    
    print()
    
    # --- ТЕСТ 5: СТАТУС В UI (get_main_kb) ---
    print("5️⃣  ТЕСТ СТАТУСА В UI (get_main_kb)")
    print("-" * 50)
    from keyboards import get_main_kb
    
    # Восстанавливаем состояние
    player.campfire_durability = 9
    player.campfire_active = True
    
    kb_hot = get_main_kb(player)
    btn_texts_hot = [btn.text for row in kb_hot.inline_keyboard for btn in row]
    print(f"   Горящий костёр кнопки: {btn_texts_hot}")
    
    # Потушим костёр
    player.campfire_active = False
    kb_cold = get_main_kb(player)
    btn_texts_cold = [btn.text for row in kb_cold.inline_keyboard for btn in row]
    print(f"   Потухший костёр кнопки: {btn_texts_cold}")
    
    checks = [
        ("Горящий: есть кнопка '🔥 Костёр 9/10'", any("🔥 Костёр 9/10" in t for t in btn_texts_hot)),
        ("Потухший: нет кнопки костра на главном", not any("🔥 Костёр" in t for t in btn_texts_cold)),
    ]
    
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"      {status} {name}")
    
    print()
    
    # --- ИТОГОВЫЙ ОТЧЕТ ---
    print("=" * 70)
    print("📊 ИТОГОВЫЙ ОТЧЕТ ПО ТЕСТАМ КОСТРА")
    print("=" * 70)
    
    all_checks = checks + [
        ("AP не отрицательный", player.ap >= 0),
        ("Прочность не отрицательная", player.campfire_durability >= 0),
    ]
    
    total_passed = sum(1 for _, passed in all_checks if passed)
    total_checks = len(all_checks)
    
    print(f"   Пройдено: {total_passed}/{total_checks} проверок")
    
    if total_passed == total_checks:
        print("   🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    else:
        print("   ⚠️  Есть небольшие недочёты.")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    run_campfire_tests()
