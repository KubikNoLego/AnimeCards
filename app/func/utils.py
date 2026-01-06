import random
from typing import Optional
from datetime import datetime, timedelta, timezone
import json
from html import escape

from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from db.models import Card, Profile, User, Verse
from db.requests import RedisRequests, get_user_collections_count
import redis.asyncio as redis

# Константы для генерации случайных карт
RARITIES = [1, 2, 3, 4, 5]
CHANCES = [55, 27, 12, 4.5, 1]
SHINY_CHANCE = 0.05

async def random_card(session: AsyncSession, pity: int):
    """Генерировать случайную карту на основе системы жалости.

    Args:
        session: Асинхронная сессия базы данных
        pity: Счетчик жалости (чем выше, тем меньше шансы)

    Returns:
        Случайно выбранный объект Card
    """
    # Выбор редкости: если есть `pity` — используем веса, иначе выдаём самую дорогую редкость (5)
    random_rarity = random.choices(RARITIES, CHANCES, k=1)[0] if pity > 0 else 5
    # Определяем, выпала ли shiny-версия
    is_shiny = random.random() < SHINY_CHANCE


    cards_result = await session.scalars(
        select(Card).where(
            Card.shiny == is_shiny,
            Card.can_drop == True,
            Card.rarity.has(id=random_rarity),
        )
    )
    cards = cards_result.all()

    if not cards:
        logger.error(f"Нет доступных карт для генерации: rarity={random_rarity}, shiny={is_shiny}")
        raise ValueError(f"Нет доступных карт с редкостью {random_rarity} и shiny={is_shiny}")

    daily_verse = await RedisRequests.daily_verse()

    if daily_verse:
        boosted_cards = []
        normal_cards = []

        for card in cards:
            if card.verse.id == daily_verse:
                boosted_cards.append(card)
            else:
                normal_cards.append(card)

        # Увеличиваем шанс на 25% для карт из ежедневной вселенной
        if boosted_cards:
            # Добавляем карты из ежедневной вселенной с увеличенным весом
            # Каждая карта добавляется 1.25 раза (оригинал + 25% шанс)
            weighted_cards = boosted_cards * 5 + normal_cards  # 5 раз по 25% = 125% шанс
            cards = weighted_cards

    chosen = random.choice(cards)
    return chosen

async def user_photo_link(message: Message) -> Optional[str]:
    """Получить file_id фото профиля пользователя.

    Args:
        message: Объект сообщения Telegram

    Returns:
        File ID фото профиля пользователя или None, если фото не существует
    """
    try:
        # Определяем чей профиль запрашивать: reply target имеет приоритет
        target_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id

        profile_photos = await message.bot.get_user_profile_photos(target_id, limit=1)

        # Проверяем, есть ли хоть одна фотография
        if profile_photos and len(profile_photos.photos) > 0:
            # Берём последний элемент в первом варианте (обычно наибольший размер)
            photo = profile_photos.photos[0][-1]
            file_id = photo.file_id
            return file_id
    except Exception as exc:
        # Логируем исключение с трассировкой для удобства отладки
        logger.exception(f"Ошибка при получении фото пользователя: {exc}")

    return None

def _load_messages() -> dict:
    """Вспомогательная функция: загружает JSON с сообщениями (кодировка utf-8)."""
    with open("app/messages.json", "r", encoding="utf-8") as f:
        return json.load(f)

@logger.catch
async def start_message_generator(start: bool):
    """Генерировать стартовое сообщение на основе статуса пользователя.

    Args:
        start: True если первый запуск, False если возвращающийся пользователь

    Returns:
        Форматированное стартовое сообщение
    """
    messages = _load_messages()
    key = "first_start" if start else "start"
    return messages[key]

@logger.catch
async def profile_tutorial():
    """Получить сообщение-руководство для профиля (шаг 1)."""
    messages = _load_messages()
    return messages["profile_tutorial"]

@logger.catch
async def profile_step2_tutorial():
    """Получить сообщение-руководство для профиля (шаг 2)."""
    messages = _load_messages()
    return messages["profile_tutorial2"]

@logger.catch
async def card_formatter(card: Card):
    """Форматировать информацию о карте для отображения.

    Args:
        card: Объект Card для форматирования

    Returns:
        Форматированная строка с информацией о карте
    """
    return f"""
📄 <b>{card.name}</b>
📚 Вселенная: {card.verse.name}
🎨 Редкость: {card.rarity.name}
💰 Ценность: {card.value} ¥
{"✨ Shiny" if card.shiny else ""}
"""

@logger.catch
async def nottime(openc: datetime):
    """Генерировать сообщение "еще не время" с обратным отсчетом.

    Args:
        openc: Время последнего открытия

    Returns:
        Форматированное сообщение с оставшимся временем
    """
    try:
        messages = _load_messages()

        # Целевое время — открытие + 3 часа (локальная корректировка)
        target_time = openc + timedelta(hours=3)

        time_left = target_time - datetime.now(timezone.utc)
        total_seconds = int(time_left.total_seconds())

        if total_seconds < 0:
            formatted_time = "00:00"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            formatted_time = f"{hours:02d}:{minutes:02d}"

        return messages["nottime"] % formatted_time
    except Exception as e:
        logger.error(f"Ошибка при генерации сообщения о времени: {e}")
        # Возвращаем сообщение по умолчанию, если что-то пошло не так
        return "<i>⏳ До следующего открытия осталось немного времени</i>"

@logger.catch
async def profile_creator(profile: Profile, place_on_top: int, session: AsyncSession):
    """Создать отображение профиля пользователя.

    Args:
        profile: Объект профиля пользователя
        place_on_top: Позиция пользователя в рейтинге
        session: Асинхронная сессия базы данных

    Returns:
        Форматированная информация о профиле
    """
    messages = _load_messages()

    owner = profile.owner

    collections_count = await get_user_collections_count(session, owner)

    return messages["profile"] % (
        escape(owner.name),
        profile.yens,
        place_on_top,
        len(owner.inventory),
        collections_count,
        owner.joined.strftime("%d.%m.%Y"),
        f"«{escape(profile.describe)}»" if profile.describe != "" else "",
    )

@logger.catch
async def not_user(name: str):
    """Генерировать сообщение "пользователь не найден".

    Args:
        name: Имя пользователя, которое не было найдено

    Returns:
        Форматированное сообщение об ошибке
    """
    messages = _load_messages()
    logger.warning(f"Запрос для несуществующего пользователя: {name}")
    return messages["not_user"] % escape(name)

@logger.catch
async def top_players_formatter(top_players: list, current_user_id: int):
    """Форматировать список топ игроков по балансу.

    Args:
        top_players: Список пользователей (топ по балансу)
        current_user_id: ID текущего пользователя для выделения

    Returns:
        Форматированная строка с топом игроков и кликабельными ссылками на профили
    """
    messages = _load_messages()

    if not top_players:
        return "<i>🏆 Топ игроков пока пуст.</i>"

    header = "<b>🏆 Топ игроков по балансу</b>\n\n"
    players_text = []

    for i, player in enumerate(top_players, 1):
        place_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        highlight = "<b><i>" if player.id == current_user_id else ""
        end_highlight = "</i></b>" if player.id == current_user_id else ""

        # Создаем кликабельную ссылку на профиль пользователя
        player_link = f'<a href="tg://user?id={player.id}">{escape(player.name)}</a>'
        player_info = f"{place_emoji} {highlight}{player_link} — {player.yens} ¥{end_highlight}"
        players_text.append(player_info)

    return header + "\n".join(players_text)

async def check_and_update_daily_verse(session: AsyncSession):
    """Проверять и обновлять вселенную дня при смене дня.

    Использует TTL в Redis (24 часа) вместо хранения даты.
    Если ключ существует - вселенная актуальна.
    Если ключ не существует или истек - выбираем новую вселенную.

    Args:
        session: Асинхронная сессия базы данных

    Returns:
        True, если вселенная была обновлена, False в противном случае
    """
    try:
        redis_client = redis.from_url(config.REDIS_URL.get_secret_value())

        # Проверяем, существует ли текущая вселенная в Redis
        verse_data_json = await redis_client.get("daily_verse")

        if verse_data_json:
            # Вселенная существует и актуальна (TTL еще не истек)
            return False

        # Выбираем случайную вселенную
        result = await session.execute(select(Verse))
        verses = result.scalars().all()

        if not verses:
            logger.warning("В базе данных нет вселенных")
            return False

        new_verse = random.choice(verses)

        # Сохраняем новую вселенную в Redis с TTL 24 часа
        verse_data = {
            "id": new_verse.id,
            "name": new_verse.name
        }

        # Устанавливаем TTL на 24 часа (24*60*60 секунд)
        await redis_client.set("daily_verse", json.dumps(verse_data), ex=24*60*60)
        return True

    except Exception as exc:
        logger.exception(f"Ошибка при проверке и обновлении вселенной дня: {exc}")
        return False
