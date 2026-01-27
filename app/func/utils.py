# Стандартные библиотеки
import json
import math
import os
import random
import tempfile
from datetime import datetime, timedelta, timezone, timedelta
from html import escape
from typing import Optional

# Создаем таймзону для Москвы (UTC+3)
MSK_TIMEZONE = timezone(timedelta(hours=3))

# Сторонние библиотеки
import qrcode
from aiogram.types import FSInputFile, Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Локальные импорты
from db import Card, Clan, Profile, User, Verse,RedisRequests,DB

# Константы для генерации случайных карт
RARITIES = [1, 2, 3, 4, 5]
CHANCES = [55, 27, 12, 4.5, 1]
SHINY_CHANCE = 0.05

async def create_qr(link:str) -> FSInputFile:
    """Создаёт QR для реферальной ссылки"""
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )
    qr.add_data(link)

    # Создаем временный файл
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    try:
        # Генерируем изображение и сохраняем во временный файл
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(temp_file.name)
        return FSInputFile(temp_file.name)
    except Exception as e:
        # Удаляем временный файл в случае ошибки
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
        raise
async def random_card(session: AsyncSession, pity: int) -> Card:
    """Выбрать случайную карту"""
    # Выбор редкости: если есть `pity` — используем веса, иначе выдаём самую дорогую редкость (5)
    random_rarity = random.choices(RARITIES, CHANCES, k=1)[0] if pity > 0 else 5
    # Определяем, выпала ли shiny-версия
    is_shiny = random.random() < SHINY_CHANCE

    # Оптимизация: получаем daily_verse параллельно с запросом к базе данных
    daily_verse_task = RedisRequests.daily_verse()

    cards_result = await session.scalars(
        select(Card).where(
            Card.shiny == is_shiny,
            Card.can_drop == True,
            Card.rarity.has(id=random_rarity),
        )
    )
    cards = cards_result.all()

    if not cards:
        raise ValueError(f"Нет доступных карт с редкостью {random_rarity} и shiny={is_shiny}")

    daily_verse = await daily_verse_task

    # Оптимизация: используем list comprehension вместо циклов для разделения карт
    if daily_verse:
        boosted_cards = [card for card in cards if card.verse.id == daily_verse]
        normal_cards = [card for card in cards if card.verse.id != daily_verse]

        # Увеличиваем шанс на 25% для карт из ежедневной вселенной
        if boosted_cards:
            cards = random.choices(
                population=boosted_cards + normal_cards,
                weights=[1.25] * len(boosted_cards) + [1.0] * len(normal_cards),
                k=1
            )
            return cards[0]

    return random.choice(cards) if cards else None

async def user_photo_link(message: Message) -> Optional[str]:
    """Получить file_id фото профиля пользователя"""
    try:
        # Определяем чей профиль запрашивать: reply target имеет приоритет
        target_id = message.reply_to_message.from_user.id if message.reply_to_message and message.reply_to_message.from_user else message.from_user.id

        profile_photos = await message.bot.get_user_profile_photos(target_id, limit=1)

        # Проверяем, есть ли хоть одна фотография
        if profile_photos and len(profile_photos.photos) > 0:
            photo = profile_photos.photos[0][-1]
            file_id = photo.file_id
            return file_id
    except Exception as exc:
        # Логируем исключение с трассировкой для удобства отладки
        logger.exception(f"Ошибка при получении фото пользователя: {exc}")

    return None



