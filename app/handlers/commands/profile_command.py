from html import escape

from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.messages import MText
from app.func import MSK_TIMEZONE, user_photo_link
from db import DB


router = Router()


@router.message(Command("profile"))
async def _(message: Message,session: AsyncSession):
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if user:
        place_on_top = await db.get_user_place_on_top(user)
        text = MText.get("profile").format(
            tag = "" if not user.clan_member else f"[{escape(
                user.clan_member.clan.tag)}]",
            name =  escape(user.name) + " 👑" if user.vip else escape(user.name),
            balance = user.balance,
            place = place_on_top,
            cards = len(user.inventory),
            date = user.profile.joined.astimezone(MSK_TIMEZONE).strftime("%d.%m.%Y")
        ) + (f"\n\n<i>«{user.profile.describe}»</i>"
            if user.profile.describe else "")

        profile_photo = await user_photo_link(message)
            
        if profile_photo:
            await message.reply_photo(photo=profile_photo,caption=text)
        else:
            await message.reply(text)
    else:
        await message.reply(MText.get("not_user").format(name = escape(user.name)))