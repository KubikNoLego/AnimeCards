from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.messages import MText
from db import DB,RedisRequests


router = Router()


@router.message(Command("daily"))
async def _(message: Message, session: AsyncSession):
    try:
        # Получаем ID текущей ежедневной вселенной из Redis
        verse_id = await RedisRequests.daily_verse()

        if not verse_id:
            await message.reply(MText.get("daily_verse_error"))
            return
        # Получаем информацию о вселенной из базы данных
        db = DB(session)
        verse = await db.get_verse(verse_id)

        if verse:
            # Форматируем сообщение с информацией о ежедневной вселенной
            text = MText.get("daily_verse").format(verse=verse.name)
            await message.reply(text)
        else:
            await message.reply(MText.get("daily_verse_error"))
    except Exception as e:
        logger.error(f"Ошибка при получении ежедневной вселенной: {str(e)}")
        await message.reply(MText.get("daily_verse_error"))