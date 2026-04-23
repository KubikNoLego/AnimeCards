import re
from html import escape

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.profile import change_visible_for_profile, user_photo_link
from app.keyboards import profile_keyboard
from app.messages import MText
from app.services.user_stat import user_profile
from app.states import ChangeDescribe
from app.filters import ProfileFilter
from app.database import DB, User


router = Router()


@router.callback_query(F.data == "change_visible")
async def _(callback: CallbackQuery,session: AsyncSession):
    await callback.message.answer(await change_visible_for_profile(session,
                                                        callback.from_user.id))
    await callback.message.delete()


@router.message(Command("profile"))
async def _(message: Message,session: AsyncSession):
    db = DB(session)
    user = await db.user.get_user(message.from_user.id)
    if message.reply_to_message:
        return
    if user:
        text = await user_profile(session, user.id)

        profile_photo = await user_photo_link(message, message.from_user.id)
            
        if profile_photo:
            await message.reply_photo(photo=profile_photo,caption=text)
        else:
            await message.reply(text)
    else:
        await message.reply(MText.get("not_user")
                            .format(name = escape(message.from_user.full_name)))

@router.message(ChangeDescribe.text)
async def _(message:Message, session: AsyncSession, state: FSMContext):
    if len(message.text) > 255:
        await message.answer(MText.get("describe_too_long").format(
            desc = len(message.text)))
    else:
        db = DB(session)
        user = await db.user.get_user(message.from_user.id)
        user.profile.describe = escape(message.text.strip().replace('\n', ''))
        await session.commit()
        await message.answer(MText.get("describe_updated_success")
                .format(desc=escape(message.text.strip().replace('\n', ''))))
        await state.set_state(None)

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
        
        text = await user_profile(session,user.id)
        target_profile_photo = await user_photo_link(message.bot,user.id)

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
    
    text, photo = (await user_profile(session,user.id),
                await user_photo_link(message.bot,user.id))
    
    keyboard = await profile_keyboard(user.profile.describe != "", user.vip,
                                    user.profile.visible)

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