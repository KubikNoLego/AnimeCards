from datetime import datetime, timedelta
import math
from typing import Callable

from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from loguru import logger

from app.database.requests import RedisRequests
from app.database import get_redis
from app.utils.consts import COOLDOWN, MSK_TIMEZONE
from app.utils.random_card import soft_pity

from ..database.models import Card, User


def format_buyed_card(card: Card) -> str:
    """Форматирует информацию о полученной карте."""
    template = "<b>{name}</b>\n\n🌐 Вселенная: <i>{verse}</i>\n🎨 Редкость: <b>{rarity}</b>\n💰 Ценность: <b>{value}</b> ¥{added}"


    text = template.format(name=card.name,
                        verse=card.verse_name,
                    rarity=card.rarity_name,
                    value=str(int(card.value)) + f" (-{int(card.value*0.2)})",
                    added = ("\n\n✨ Shiny" if card.shiny else ""))

    return text

def format_card(card: Card) -> str:
    """Форматирует информацию о карте."""
    template = "<b>{name}</b>\n\n🌐 Вселенная: <i>{verse}</i>\n🎨 Редкость: <b>{rarity}</b>\n💰 Ценность: <b>{value}</b> ¥{added}"


    text = template.format(name=card.name,
                        verse=card.verse_name,
                    rarity=card.rarity_name,
                    value=card.value,
                    added = ("\n\n✨ Shiny" if card.shiny else ""))

    return text

async def format_open_card(card: Card, user: User) -> str:
    """Форматирует информацию о открываемой карте с учетом бонусов."""
    template = "<b>{name}</b>\n\n🌐 Вселенная: <i>{verse}</i>\n🎨 Редкость: <b>{rarity}</b>\n💰 Ценность: <b>{value}</b> ¥{added}"

    redis = get_redis()
    redis_requests = RedisRequests(redis)
    
    vip_bonus = int(card.value * 0.1) if user.vip else 0
    daily_bonus = (int(card.value * 0.2) if (card.verse.id ==
                        await RedisRequests.daily_verse())
                        else 0)
    yens_boost = int(card.value * 0.3) if await redis_requests.yens_boosts(user.id) > 0 else 0
    yens_title = int(card.value * (user.profile.title.yen_boost/100)) if user.profile.title else 0

    bonus = vip_bonus + daily_bonus + yens_boost + yens_title

    value = (str(card.value) if not bonus
            else str(card.value)+f" (+{bonus})")

    text = template.format(name=card.name,
                        verse=card.verse_name,
                    rarity=card.rarity_name,
                    value=value,
                    added=(f"\n\n✨ Shiny\n\n🍀 Гарант на Хроно: {user.pity}/100"
                    if card.shiny
                    else f"\n\n🍀 Гарант на Хроно: {user.pity}/100"))

    return text

async def show_inventory_card(callback: CallbackQuery,
                            total_cards: int, card: Card, index: int,
                        keyboard: Callable[[int, int],
                                InlineKeyboardMarkup]) -> None:
    info = format_card(card) 

    keyboard = await keyboard(index + 1, total_cards)

    if card.icon.lower().endswith(".mp4"):
        media = InputMediaVideo(media=FSInputFile(
            path=f"app/icons/{card.verse.name}/{card.icon}"))
    else:
        media = InputMediaPhoto(media=FSInputFile(
                path=f"app/icons/{card.verse.name}/{card.icon}"))

    try:
        # Определяем тип медиа по расширению файла
        file_path = f"app/assets/cards/{card.verse.name}/{card.icon}"
        if card.icon.endswith('.mp4'):
            media = InputMediaVideo(media=FSInputFile(path=file_path))
        else:
            media = InputMediaPhoto(media=FSInputFile(path=file_path))
        
        await callback.message.edit_media(
            media=media,
            reply_markup=keyboard
        )
        await callback.message.edit_caption(
            caption=info,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.warning(f"Не удалось отредактировать сообщение: {e}")

def nottime(openc: datetime, buff: None | int = 0) -> str:
        """Генерировать сообщение "еще не время" с обратным отсчетом"""
        try:

            hour = COOLDOWN - (1 if datetime.now(MSK_TIMEZONE).weekday() >= 5 else 0)
            target_time = openc + timedelta(hours=hour)
            if buff:
                target_time -= timedelta(minutes=buff)

            time_left = target_time - datetime.now(MSK_TIMEZONE)
            total_seconds = int(time_left.total_seconds())

            if total_seconds < 0:
                formatted_time = "00:00"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                formatted_time = f"{hours:02d}:{minutes:02d}"

            return "<b>⏳ Подождите</b>\n\n<i>До следующего открытия осталось <b>{time}</b></i>\n\n<i>Попробуйте открыть карту позже.</i>".format(time=formatted_time)
        except Exception as e:
            # Возвращаем сообщение по умолчанию, если что-то пошло не так
            logger.exception(f"Nottime error: {e}")
            return "<i>⏳ До следующего открытия осталось немного времени</i>"