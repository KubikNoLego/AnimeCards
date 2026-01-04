import random
from typing import Optional
from datetime import datetime, timedelta, timezone
import json
from html import escape

from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from db.models import Card, Profile, User

# Constants for random card generation
RARITIES = [1, 2, 3, 4, 5]
CHANCES = [55, 27, 12, 4.5, 1]
SHINY_CHANCE = 0.05

async def random_card(session: AsyncSession, pity: int):
    """Generate a random card based on pity system.

    Args:
        session: Async database session
        pity: Pity counter (higher means better chances)

    Returns:
        Randomly selected Card object
    """
    # Выбор редкости: если есть `pity` — используем веса, иначе выдаём самую обычную редкость (1)
    random_rarity = random.choices(RARITIES, CHANCES, k=1)[0] if pity > 0 else 1
    # Определяем, выпала ли shiny-версия
    is_shiny = random.random() < SHINY_CHANCE

    logger.info(f"Выбор карты: rarity={random_rarity}, shiny={is_shiny}, pity={pity}")

    cards_result = await session.scalars(
        select(Card).where(
            Card.shiny == is_shiny,
            Card.can_drop == True,
            Card.rarity.has(id=random_rarity),
        )
    )
    cards = cards_result.all()
    chosen = random.choice(cards)
    logger.info(f"Выдана карта id={getattr(chosen, 'id', None)} name={getattr(chosen, 'name', None)} shiny={chosen.shiny}")
    return chosen

async def user_photo_link(message: Message) -> Optional[str]:
    """Get user profile photo file_id.

    Args:
        message: Telegram message object

    Returns:
        File ID of user's profile photo, or None if no photo exists
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
            logger.info(f"Найдено фото для пользователя id={target_id}: file_id={file_id}")
            return file_id
        else:
            logger.info(f"У пользователя id={target_id} нет фото профиля")
    except Exception as exc:
        # Логируем исключение с трассировкой для удобства отладки
        logger.exception(f"Ошибка при получении фото пользователя: {exc}")

    return None

def _load_messages() -> dict:
    """Helper: загружает JSON с сообщениями (кодировка utf-8)."""
    with open("app/messages.json", "r", encoding="utf-8") as f:
        return json.load(f)

@logger.catch
async def start_message_generator(start: bool):
    """Generate start message based on user status.

    Args:
        start: True if first start, False if returning user

    Returns:
        Formatted start message
    """
    messages = _load_messages()
    key = "first_start" if start else "start"
    logger.info(f"Возвращаю стартовое сообщение: {key}")
    return messages[key]

@logger.catch
async def profile_tutorial():
    """Get profile tutorial message (step 1)."""
    messages = _load_messages()
    logger.info("Возвращаю сообщение-руководство для профиля (шаг 1)")
    return messages["profile_tutorial"]

@logger.catch
async def profile_step2_tutorial():
    """Get profile tutorial message (step 2)."""
    messages = _load_messages()
    logger.info("Возвращаю сообщение-руководство для профиля (шаг 2)")
    return messages["profile_tutorial2"]

@logger.catch
async def card_formatter(card: Card):
    """Format card information for display.

    Args:
        card: Card object to format

    Returns:
        Formatted card information string
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
    """Generate "not time yet" message with countdown.

    Args:
        openc: Last opening time

    Returns:
        Formatted message with time remaining
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

        logger.info(f"Осталось до следующего открытия: {formatted_time}")
        return messages["nottime"] % formatted_time
    except Exception as e:
        logger.error(f"Ошибка при генерации сообщения о времени: {e}")
        # Возвращаем сообщение по умолчанию, если что-то пошло не так
        return "<i>⏳ До следующего открытия осталось немного времени</i>"

@logger.catch
async def profile_creator(profile: Profile, place_on_top: int):
    """Create user profile display.

    Args:
        profile: User profile object
        place_on_top: User's ranking position

    Returns:
        Formatted profile information
    """
    messages = _load_messages()

    owner = profile.owner
    logger.info(f"Генерирую профиль для пользователя id={getattr(owner, 'id', None)}")
    return messages["profile"] % (
        escape(owner.name),
        profile.yens,
        place_on_top,
        len(owner.inventory),
        owner.joined.strftime("%d.%m.%Y"),
        escape(profile.describe),
    )

@logger.catch
async def not_user(name: str):
    """Generate "user not found" message.

    Args:
        name: Username that wasn't found

    Returns:
        Formatted error message
    """
    messages = _load_messages()
    logger.warning(f"Запрос для несуществующего пользователя: {name}")
    return messages["not_user"] % escape(name)
