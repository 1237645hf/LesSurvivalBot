import random

def simulate_battle():
    random.seed(42)  # фиксируем сид для воспроизводимости реального боя
    
    # 1. Параметры героя
    player_max_hp = 133
    player_hp = 133
    player_def = 7
    dodge_chance = 40  # 35% кожаный сет + 5% костяной амулет охотника
    potion_available = True
    potion_healed = 70
    
    # 2. Имена и генерация 6 слизней (HP от 15 до 25)
    names = [
        "Едкий Прыгун", "Болотный Чавка", "Мутный Липун",
        "Янтарный Желвак", "Слизень-Шалун", "Бурый Пузырь"
    ]
    
    slimes = []
    for name in names:
        hp = random.randint(15, 25)
        slimes.append({"name": name, "hp": hp, "max_hp": hp, "alive": True})
        
    print("=" * 60)
    print("⚔️ СТАРТ БОЯ: СКОПЛЕНИЕ ИЗ 6 СЛИЗНЕЙ")
    print(f"Герой: {player_hp}/{player_max_hp} HP | Броня: {player_def} DEF | Уворот: {dodge_chance}%")
    print(f"Зелье в кармане поножей: Янтарное зелье (+{potion_healed} HP)")
    print("-" * 60)
    for i, s in enumerate(slimes, 1):
        print(f"  {i}. {s['name']}: {s['hp']}/{s['max_hp']} HP")
    print("=" * 60)
    
    round_num = 1
    total_dmg_taken = 0
    total_dodges = 0
    total_hits_taken = 0
    
    while any(s["alive"] for s in slimes) and player_hp > 0:
        print(f"\n▶ РАУНД {round_num}")
        
        # Проверка использования зелья из футляра при низком здоровье (<= 45 HP)
        if potion_available and player_hp <= 45:
            healed = min(player_max_hp - player_hp, potion_healed)
            player_hp += healed
            potion_available = False
            print(f"🍹 [ДЕЙСТВИЕ] Герой использует [Принять Янтарное зелье]! +{healed} HP (Стало: {player_hp}/{player_max_hp} HP)")
            print(f"   Сланцевый пузырёк падает в рюкзак, карман поножей пуст.")
        
        # 1. Атака героя по первому живому слизню
        target = next(s for s in slimes if s["alive"])
        player_dmg = random.randint(8, 10)
        target["hp"] -= player_dmg
        print(f"⚔️ Герой бьёт по [{target['name']}] на {player_dmg} урона! (Осталось: {max(0, target['hp'])}/{target['max_hp']} HP)")
        
        if target["hp"] <= 0:
            target["alive"] = False
            target["hp"] = 0
            print(f"💥 [{target['name']}] ЛОПАЕТСЯ С БРЫЗГАМИ СТУДНЯ! (💀)")
            
        # 2. Атака оставшихся живых слизней по герою
        alive_slimes = [s for s in slimes if s["alive"]]
        if not alive_slimes:
            print("Все слизни повержены!")
            break
            
        print(f"👾 Ответная атака слизней ({len(alive_slimes)} живых):")
        round_dmg = 0
        for s in alive_slimes:
            # Проверка уворота (40%)
            roll_dodge = random.randint(1, 100)
            if roll_dodge <= dodge_chance:
                total_dodges += 1
                print(f"   • [{s['name']}]: ПРОМАХ! Герой увернулся благодаря ловкости брони и амулету ({roll_dodge} <= {dodge_chance}%).")
            else:
                total_hits_taken += 1
                raw_dmg = random.randint(5, 15)
                actual_dmg = max(1, raw_dmg - player_def)
                round_dmg += actual_dmg
                player_hp -= actual_dmg
                print(f"   • [{s['name']}]: Ударил на {raw_dmg} ➔ Броня {player_def} DEF смягчила до {actual_dmg} HP.")
                
        total_dmg_taken += round_dmg
        status_icons = " ".join("🟢" if s["alive"] else "💀" for s in slimes)
        print(f"   Статус стаи: [ {status_icons} ]")
        print(f"   Здоровье героя к концу раунда: {player_hp}/{player_max_hp} HP (получено за раунд: {round_dmg} урона)")
        
        if player_hp <= 0:
            print("☠️ Герой погиб в бою!")
            return False
            
        round_num += 1
        
    print("\n" + "=" * 60)
    print("🏆 ПОБЕДА ГЕРОЯ!")
    print(f"Всего раундов: {round_num}")
    print(f"Итоговое здоровье героя: {player_hp}/{player_max_hp} HP")
    print(f"Суммарно получено урона: {total_dmg_taken} HP")
    print(f"Успешных уворотов героя: {total_dodges} (из {total_dodges + total_hits_taken} атак слизней)")
    print(f"Процент сработавших уворотов: {round(total_dodges / (total_dodges + total_hits_taken) * 100, 1)}%")
    print("-" * 60)
    
    # 3. Дроп янтарных ядер (50% шанс с каждого слизня)
    print("ТРОФЕИ С БОЯ (шанс 50% с каждого слизня):")
    cores_found = 0
    for s in slimes:
        if random.random() < 0.5:
            cores_found += 1
            print(f"   • [{s['name']}]: 🟠 Янтарное ядро извлечено целым!")
        else:
            print(f"   • [{s['name']}]: ядро разбилось от ударов")
            
    print(f"Итого добыто: Янтарное ядро ×{cores_found}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    simulate_battle()
