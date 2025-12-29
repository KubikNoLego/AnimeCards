from aiogram import Router,F
from aiogram.filters import CommandStart,CommandObject
from aiogram.types import Message

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.filters.Private import Private
from app.func.userphoto import user_photo_link
from app.func.messageformater import start_message_generator
from app.keyboards import replykeyboard as kb
from db.models import User
from db.requests import create_or_update_user

router = Router()

@router.message(CommandStart(),Private())
async def _(message: Message, command: CommandObject,session: AsyncSession):
    user = await message.bot.get_chat(message.from_user.id)
    await create_or_update_user(user.id,
                                message.from_user.username,
                                user.full_name,
                                user.bio,
                                session
                            )
    db_user = await session.scalar(select(User).filter_by(id=user.id))
    message_text = await start_message_generator(db_user.start)
    await message.reply(message_text,reply_markup=await kb.main_kb())