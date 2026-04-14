from datetime import datetime, timedelta
import math
from typing import Callable

from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from loguru import logger

from app.database.requests import RedisRequests
from app.utils.consts import MSK_TIMEZONE

from ..database.models import Card, User

def format_card(card: Card) -> str:
    template = "<b>{name}</b>\n\n🌐 Вселенная: <i>{verse}</i>\n🎨 Редкость: <b>{rarity}</b>\n💰 Ценность: <b>{value}</b> ¥"

    text = template.format(name=card.name,
                        verse=card.verse_name,
                    rarity=card.rarity_name,
                    value=card.value) + ("\n\n✨ Shiny" if card.shiny else "")
    
    return text
    
async def format_open_card(card: Card, user: User) -> str:
    template = "<b>{name}</b>\n\n🌐 Вселенная: <i>{verse}</i>\n🎨 Редкость: <b>{rarity}</b>\n💰 Ценность: <b>{value}</b> ¥"

    vip_bonus = int(card.value * 0.1) if user.vip else 0
    daily_bonus = (int(card.value * 0.2) if (card.verse.id ==
                        await RedisRequests.daily_verse())
                        else 0)
    bonus = vip_bonus + daily_bonus

    value = (str(card.value) if not bonus
            else str(card.value)+f" (+{bonus})")

    text = template.format(name=card.name,
                        verse=card.verse_name,
                    rarity=card.rarity_name,
                    value= value + 
                    (f"\n\n✨ Shiny\n\n🍀 Гарант на Хроно: {100-user.pity}/100"
                    if card.shiny 
                    else f"\n\n🍀 Гарант на Хроно: {100-user.pity}/100"))
    
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

def nottime(openc: datetime) -> str:
        """Генерировать сообщение "еще не время" с обратным отсчетом"""
        try:

            hour = 2 if datetime.now(MSK_TIMEZONE).weekday() >= 5 else 3
            target_time = openc + timedelta(hours=hour)

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
            return "<i>⏳ До следующего открытия осталось немного времени</i>"