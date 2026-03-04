from html import escape

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.messages import MText
from app.func import user_photo_link
from db import DB


router = Router()


@router.message(Command("profile"))
async def _(message: Message,session: AsyncSession):
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if user:
        text = await MText.user_profile(session, user.id)

        profile_photo = await user_photo_link(message)
            
        if profile_photo:
            await message.reply_photo(photo=profile_photo,caption=text)
        else:
            await message.reply(text)
    else:
        await message.reply(MText.get("not_user")
                            .format(name = escape(user.name)))