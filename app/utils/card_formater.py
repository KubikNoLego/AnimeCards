import math
from typing import Callable

from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from loguru import logger

from ..database.models import Card, User

async def format_card(card: Card) -> str:
    template = "<b>{name}</b>\n\n🌐 Вселенная: <i>{verse}</i>\n🎨 Редкость: <b>{rarity}</b>\n💰 Ценность: <b>{value}</b> ¥"

    text = template.format(name=card.name,
                        verse=card.verse_name,
                    rarity=card.rarity_name,
                    value=card.value) + ("\n\n✨ Shiny" if card.shiny else "")
    
    return text
    
async def format_open_card(card: Card, user: User) -> str:
    template = "<b>{name}</b>\n\n🌐 Вселенная: <i>{verse}</i>\n🎨 Редкость: <b>{rarity}</b>\n💰 Ценность: <b>{value}</b> ¥"

    text = template.format(name=card.name,
                        verse=card.verse_name,
                    rarity=card.rarity_name,
                    value=card.value
                    if not user.vip
                    else str(card.value)+f" (+{math.ceil(card.value * 0.1)})") + (f"\n\n✨ Shiny\n\n🍀 Гарант на Хроно: {100-user.pity}/100" if card.shiny else f"\n\n🍀 Гарант на Хроно: {100-user.pity}/100")
    
    return text

async def show_inventory_card(callback: CallbackQuery,
                            total_cards: int, card: Card, index: int,
                        keyboard: Callable[[int, int],
                                InlineKeyboardMarkup]) -> None:
    info = await format_card(card) 

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