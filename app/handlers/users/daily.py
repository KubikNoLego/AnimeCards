from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import Message,CallbackQuery, FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.requests import DB
from app.messages import MText


router = Router()


@router.message(Command("daily"))
async def _(message: Message, session: AsyncSession):
    verse = await DB(session).verse.get_daily_verse()
    await message.reply(MText.get("daily_verse").format(verse=verse.name))