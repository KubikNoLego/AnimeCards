#!/usr/bin/env python3

import os
import json
import re
from pathlib import Path

def get_rarity_mapping():
    """Возвращает маппинг старых названий редкостей на новые"""
    return {
        "common": "C",
        "uncommon": "B",
        "mythic": "S",
        "legend": "SR",
        "hrono": "SSR",
    }

def extract_rarity_from_icon(icon_name):
    """Извлекает редкость из имени иконки"""
    # Паттерн для извлечения редкости из имени файла
    # Поддерживаем любые расширения файлов
    match = re.search(r'card_.*?_(.+?)(?:\(shiny\))?\.[^.]+$', icon_name)
    if match:
        return match.group(1)
    return None

def check_card_icons():
    """Проверяет наличие иконок карт в папках"""

    # Загружаем данные о картах
    with open("cards.json", encoding="utf-8") as f:
        cards = json.load(f)

    rarity_mapping = get_rarity_mapping()
    base_path = Path("app/assets/cards")
    missing_icons = []
    found_icons = set()

    # Проверяем все карты
    for card in cards:
        verse_folder = card['verse_name']
        old_icon_name = card['icon']

        # Извлекаем редкость из старого имени иконки
        old_rarity = extract_rarity_from_icon(old_icon_name)
        if not old_rarity:
            print(f"Не удалось извлечь редкость из {old_icon_name}")
            continue

        # Получаем новую редкость
        new_rarity = rarity_mapping.get(old_rarity, old_rarity)

        # Формируем новое имя иконки
        if "shiny" in old_icon_name.lower():
            new_icon_name = old_icon_name.replace(f"_{old_rarity}(shiny)", f"_{new_rarity}(shiny)")
        else:
            # Заменяем только суффикс редкости, сохраняя расширение
            import os
            name_without_ext = os.path.splitext(old_icon_name)[0]
            ext = os.path.splitext(old_icon_name)[1]
            new_icon_name = name_without_ext.replace(f"_{old_rarity}", f"_{new_rarity}") + ext

        # Путь к иконке с новым суффиксом
        icon_path = base_path / verse_folder / new_icon_name

        # Проверяем существование файла с новым суффиксом
        if icon_path.exists():
            found_icons.add(str(icon_path))
        else:
            # Проверяем альтернативный вариант - файл без суффикса редкости
            # (для случаев, когда файлы были переименованы не полностью)
            import os
            name_without_rarity = os.path.splitext(new_icon_name)[0].replace(f"_{new_rarity}", "")
            alt_icon_name = name_without_rarity + os.path.splitext(new_icon_name)[1]
            alt_icon_path = base_path / verse_folder / alt_icon_name

            if alt_icon_path.exists():
                found_icons.add(str(alt_icon_path))
                print(f"Найден альтернативный файл: {alt_icon_path} (ожидалось: {new_icon_name})")
            else:
                # Проверяем в корневой папке cards (для файлов, перемещенных не в ту папку)
                root_icon_path = base_path / new_icon_name
                root_alt_icon_path = base_path / alt_icon_name

                if root_icon_path.exists():
                    found_icons.add(str(root_icon_path))
                    print(f"Найден в корневой папке: {root_icon_path} (ожидалось: {icon_path})")
                elif root_alt_icon_path.exists():
                    found_icons.add(str(root_alt_icon_path))
                    print(f"Найден альтернативный файл в корневой папке: {root_alt_icon_path} (ожидалось: {icon_path})")
                else:
                    missing_icons.append({
                        "verse": verse_folder,
                        "card_name": card['name'],
                        "old_icon": old_icon_name,
                        "expected_icon": new_icon_name,
                        "path": str(icon_path),
                        "alt_path": str(alt_icon_path),
                        "root_path": str(root_icon_path),
                        "root_alt_path": str(root_alt_icon_path)
                    })

    # Выводим результаты
    print(f"Проверено карт: {len(cards)}")
    print(f"Найдено иконок: {len(found_icons)}")
    print(f"Отсутствует иконок: {len(missing_icons)}")

    if missing_icons:
        print("\nОтсутствующие иконки:")
        for item in missing_icons[:20]:  # Показываем первые 20, чтобы не заполнять экран
            print(f"  {item['verse']} -> {item['card_name']}")
            print(f"    Старая иконка: {item['old_icon']}")
            print(f"    Ожидается: {item['expected_icon']}")
            print(f"    Путь: {item['path']}")
        if len(missing_icons) > 20:
            print(f"    ... и еще {len(missing_icons) - 20} иконок")
    else:
        print("\nВсе иконки найдены!")

    return len(missing_icons) == 0

if __name__ == "__main__":
    check_card_icons()