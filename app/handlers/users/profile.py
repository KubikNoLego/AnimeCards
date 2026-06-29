import re
from html import escape

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.ProfileService import ProfileService
from app.keyboards import profile_keyboard
from app.messages import MText
from app.states import ChangeDescribe
from app.filters import ProfileFilter
from app.database import DB, User


router = Router()


@router.message(Command("profile"))
async def _(message: Message,session: AsyncSession):
    db = DB(session)
    user = await db.user.get_user(message.from_user.id)
    if message.reply_to_message:
        return
    if user:
        text = await ProfileService.generate_profile(session, user.id)

        profile_photo = await ProfileService.user_photo_link(message.bot, message.from_user.id)
            
        if profile_photo:
            await message.reply_photo(photo=profile_photo,caption=text)
        else:
            await message.reply(text)
    else:
        await message.reply(MText.get("not_user")
                            .format(name = escape(message.from_user.full_name)))

@router.message(Command("профиль", prefix='.'))
async def _(message: Message, session: AsyncSession, command: CommandObject):
    try:
        
        if command.args:
            user = await session.scalar(select(User)
                                        .filter_by(username=command.args
                                                .replace('@', '')))
        elif message.reply_to_message:
            user = await session.scalar(select(User)
                                        .filter_by(id=message.reply_to_message
                                                .from_user.id))
        else:
            return
        
        text = await ProfileService.generate_profile(session,user.id)
        target_profile_photo = await ProfileService.user_photo_link(message.bot,user.id)

        if target_profile_photo:
            await message.reply_photo(photo=target_profile_photo, caption=text)
        else:
            await message.reply(text)

    except Exception as e:
        await message.reply(MText.get("profile_error"))

@router.message(ProfileFilter())
async def _(message: Message, session: AsyncSession):
    db = DB(session)
    user = await db.user.get_user(message.from_user.id)

    if not user:
        name = message.from_user.full_name

        await message.reply(
            MText.get("not_user").format(name=escape(name)))
        return
    
    text, photo = (await ProfileService.generate_profile(session,user.id),
                await ProfileService.user_photo_link(message.bot,user.id))
    
    keyboard = await profile_keyboard(user.vip)

    if photo:
        return await message.reply_photo(
            photo=photo,
            caption=text,
            reply_markup=keyboard
        )

    return await message.reply(
        text,
        reply_markup=keyboard
    )