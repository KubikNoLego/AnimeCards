#!/usr/bin/env python3
"""
Скрипт для создания карт в базе данных AnimeCards.

Обрабатывает карты из папки app/icons/MiSide ❤️, запрашивает у пользователя
необходимую информацию и создает записи в базе данных.
"""

import os
import re
import shutil
import random
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from db.models import Base, Card, Rarity, Verse
from configR import config

# Соответствие редкостей и их диапазоны стоимости
RARITY_VALUE_RANGES = {
    "common": (1, 10),
    "uncommon": (10, 50),
    "legend": (50, 200),
    "mythic": (200, 500),
    "horono": (500, 1000),
    "hrono": (500, 1000)  # Добавляем соответствие для hrono
}

# Соответствие английских названий редкостей и русских
RARITY_NAMES = {
    "common": "Обычный",
    "uncommon": "Редкий",
    "legend": "Легендарный",
    "mythic": "Мифический",
    "hrono": "Хроно", #hrono -> правильно
}

async def get_or_create_rarity(session: AsyncSession, rarity_name: str) -> Rarity:
    """Получает или создает редкость в базе данных."""
    # Приводим к нижнему регистру для сравнения
    rarity_name = rarity_name.lower()

    # Получаем русское название редкости
    rarity_russian_name = RARITY_NAMES.get(rarity_name, rarity_name)

    # Проверяем, существует ли уже такая редкость
    result = await session.execute(select(Rarity).filter_by(name=rarity_russian_name))
    rarity = result.scalar_one_or_none()

    if rarity is None:
        rarity = Rarity(name=rarity_russian_name)
        session.add(rarity)
        await session.commit()
        print(f"Создана новая редкость: {rarity_russian_name}")

    return rarity

async def get_existing_verses(session: AsyncSession) -> list[str]:
    """Возвращает список существующих вселенных."""
    result = await session.execute(select(Verse))
    verses = result.scalars().all()
    return [verse.name for verse in verses]

async def get_or_create_verse(session: AsyncSession, verse_name: str) -> Verse:
    """Получает или создает вселенную в базе данных."""
    # Проверяем, существует ли уже такая вселенная
    result = await session.execute(select(Verse).filter_by(name=verse_name))
    verse = result.scalar_one_or_none()

    if verse is None:
        verse = Verse(name=verse_name)
        session.add(verse)
        await session.commit()
        print(f"Создана новая вселенная: {verse_name}")

    return verse

def parse_card_filename(filename: str) -> Tuple[str, str, bool]:
    """
    Разбирает название файла карты.

    Возвращает кортеж: (raw_name, rarity, is_shiny)
    """
    # Удаляем расширение файла
    basename = os.path.splitext(filename)[0]

    # Разбираем по шаблону card_<name>_<rarity> или card_<name>_<rarity>(shiny)
    pattern = r'^card_(.+?)_(.+?)(?:\(shiny\))?$'
    match = re.match(pattern, basename)

    if not match:
        raise ValueError(f"Некорректное название файла: {filename}")

    raw_name = match.group(1)
    rarity = match.group(2).lower()  # Приводим к нижнему регистру
    is_shiny = 'shiny' in basename.lower()

    return raw_name, rarity, is_shiny

def get_user_input(prompt: str, default: Optional[str] = None) -> str:
    """Запрашивает ввод у пользователя с возможностью значения по умолчанию."""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ").strip()

def select_from_list(items: list[str], prompt: str) -> str:
    """Предлагает пользователю выбрать из пронумерованного списка или ввести новое значение."""
    if not items:
        return get_user_input(prompt)

    print(f"\n{prompt}:")
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")

    print(f"{len(items) + 1}. Ввести новое название")

    while True:
        choice = input(f"Выберите номер (1-{len(items) + 1}): ").strip()
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(items):
                return items[choice_num - 1]
            elif choice_num == len(items) + 1:
                return get_user_input("Введите новое название")
            else:
                print(f"Пожалуйста, введите число от 1 до {len(items) + 1}")
        except ValueError:
            print("Пожалуйста, введите корректное число")

def get_card_value(rarity: str, is_shiny: bool = False) -> int:
    """Возвращает случайную стоимость карты на основе редкости."""
    if rarity not in RARITY_VALUE_RANGES:
        raise ValueError(f"Неизвестная редкость: {rarity}")

    min_val, max_val = RARITY_VALUE_RANGES[rarity]
    # Выбираем случайное значение из диапазона
    base_value = random.randint(min_val, max_val)

    # Для шайни карт увеличиваем стоимость на 20%
    if is_shiny:
        base_value = int(base_value * 1.2)

    return base_value

async def check_normal_card_exists(session: AsyncSession, card_name: str, verse_name: str) -> bool:
    """
    Проверяет, существует ли обычная версия карты (не шайни).

    Возвращает True, если обычная версия существует.
    """
    result = await session.execute(
        select(Card)
        .filter_by(name=card_name, verse_name=verse_name, shiny=False)
    )
    return result.scalar_one_or_none() is not None

async def process_card_file(session: AsyncSession, filename: str, source_dir: Path, target_base_dir: Path):
    """Обрабатывает один файл карты."""
    print(f"\nОбработка файла: {filename}")

    try:
        # Разбираем название файла
        raw_name, rarity, is_shiny = parse_card_filename(filename)
        print(f"Сырое название: {raw_name}")
        print(f"Редкость: {rarity} ({RARITY_NAMES.get(rarity, 'Неизвестно')})")
        print(f"Шайни: {'Да' if is_shiny else 'Нет'}")

        # Запрашиваем правильное название карты
        card_name = get_user_input("Введите правильное название карты", raw_name.replace('_', ' ').title())

        # Получаем список существующих вселенных
        existing_verses = await get_existing_verses(session)

        # Запрашиваем название вселенной
        if existing_verses:
            verse_name = select_from_list(existing_verses, "Выберите вселенную")
        else:
            verse_name = get_user_input("Введите название вселенной")

        # Для шайни карт проверяем наличие обычной версии
        if is_shiny:
            normal_exists = await check_normal_card_exists(session, card_name, verse_name)
            if not normal_exists:
                print(f"Ошибка: Нельзя добавить шайни версию карты '{card_name}', так как обычная версия не существует!")
                return False

        # Запрашиваем стоимость карты
        auto_value = get_card_value(rarity, is_shiny)
        value_input = get_user_input(f"Введите стоимость карты (авто: {auto_value})", str(auto_value))
        try:
            value = int(value_input)
        except ValueError:
            print(f"Некорректное значение стоимости, используется автоматическое: {auto_value}")
            value = auto_value

        # Запрашиваем, может ли карта выпадать
        can_drop_input = get_user_input("Может ли эта карта выпадать? (y/n)", "y")
        can_drop = can_drop_input.lower() in ('y', 'yes', 'да')

        # Получаем или создаем редкость
        rarity_obj = await get_or_create_rarity(session, rarity)

        # Получаем или создаем вселенную
        verse_obj = await get_or_create_verse(session, verse_name)

        # Создаем карту
        card = Card(
            name=card_name,
            verse_name=verse_obj.name,
            rarity_name=RARITY_NAMES.get(rarity, rarity),  # Сохраняем русское название редкости
            value=value,
            icon=filename,
            shiny=is_shiny,
            can_drop=can_drop
        )

        session.add(card)
        await session.commit()
        print(f"Карта '{card_name}' успешно создана в базе данных!")

        # Перемещаем файл карты в папку вселенной
        verse_dir = target_base_dir / verse_name
        verse_dir.mkdir(exist_ok=True)

        source_path = source_dir / filename
        target_path = verse_dir / filename

        shutil.copy2(source_path, target_path)
        print(f"Карта перемещена в: {target_path}")

        # Удаляем карту из NotUsable после успешного создания
        os.remove(source_path)
        print(f"Карта удалена из: {source_path}")

        return True

    except Exception as e:
        print(f"Ошибка при обработке файла {filename}: {e}")
        await session.rollback()
        return False

async def main():
    """Основная функция скрипта."""
    # Инициализируем подключение к базе данных
    engine = create_async_engine(config.DB_URL.get_secret_value())
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Создаем таблицы в базе данных
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    print("Таблицы базы данных успешно созданы.")

    # Пути к папкам
    source_dir = Path("app/icons/NotUsable")
    target_base_dir = Path("app/icons")

    # Проверяем, что папка с картами существует
    if not source_dir.exists():
        print(f"Ошибка: Папка {source_dir} не существует!")
        return

    # Получаем список файлов карт
    card_files = [f for f in source_dir.iterdir() if f.is_file() and f.name.startswith('card_')]
    card_files.sort()

    if not card_files:
        print("В папке нет файлов карт!")
        return

    print(f"Найдено {len(card_files)} карт для обработки.")

    # Разделяем карты на обычные и шайни
    normal_cards = []
    shiny_cards = []

    for card_file in card_files:
        try:
            _, _, is_shiny = parse_card_filename(card_file.name)
            if is_shiny:
                shiny_cards.append(card_file)
            else:
                normal_cards.append(card_file)
        except ValueError:
            print(f"Пропущена карта с некорректным названием: {card_file.name}")

    # Обрабатываем сначала обычные карты, затем шайни
    async with async_session() as session:
        # Обрабатываем обычные карты
        for card_file in normal_cards:
            success = await process_card_file(session, card_file.name, source_dir, target_base_dir)
            if not success:
                print(f"Пропущена карта: {card_file.name}")

        # Обрабатываем шайни карты
        for card_file in shiny_cards:
            success = await process_card_file(session, card_file.name, source_dir, target_base_dir)
            if not success:
                print(f"Пропущена карта: {card_file.name}")

    print("\nОбработка завершена!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
