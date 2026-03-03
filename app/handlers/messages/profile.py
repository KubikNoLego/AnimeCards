import re
from html import escape

from aiogram import Router,F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.func import user_photo_link
from app.keyboards import profile_keyboard
from app.messages import MText
from app.StateGroups import ChangeDescribe
from app.func import MSK_TIMEZONE
from app.filters import ProfileFilter
from db import DB, User


router = Router()


@router.message(ChangeDescribe.text)
async def _(message:Message, session: AsyncSession, state: FSMContext):
    if len(message.text) > 70:
        await message.answer(MText.get("describe_too_long").format(
            desc = len(message.text)))
    else:
        db = DB(session)
        user = await db.get_user(message.from_user.id)
        user.profile.describe = escape(message.text.strip())
        await session.commit()
        await message.answer(MText.get("describe_updated_success").format(desc= escape(message.text.strip())))
        await state.set_state(None)

@router.message(F.text.startswith(".профиль @"))
async def _(message: Message, session: AsyncSession):
    """Обработчик команды .профиль @username - показывает профиль пользователя по username"""
    try:
        # Извлекаем username из команды
        pattern = r'\.профиль @([a-zA-Z0-9_]+)'
        match = re.search(pattern, message.text)

        if not match:
            await message.reply(MText.get("invalid_profile_command"))
            return

        target_username = match.group(1)

        # Ищем пользователя по username
        user = await session.scalar(
            select(User)
            .filter_by(username=target_username)
        )

        if not user:
            await message.reply(MText.get("user_not_found_short"))
            return

        db = DB(session)
        # Получаем информацию о профиле
        place_on_top = await db.get_user_place_on_top(user)
        text = MText.get("profile").format(
            tag = "" if not user.clan_member else f"[{escape(user.clan_member.clan.tag)}]",
            name =  escape(user.name) + " 👑" if user.vip else escape(user.name),
            balance = user.balance,
            place = place_on_top,
            cards = len(user.inventory),
            date = user.profile.joined.astimezone(MSK_TIMEZONE).strftime("%d.%m.%Y")
        ) + (f"\n\n<i>«{user.profile.describe}»</i>" if user.profile.describe else "")
        target_profile_photo = None
        try:
            profile_photos = await message.bot.get_user_profile_photos(user.id, limit=1)
            if profile_photos and len(profile_photos.photos) > 0:
                photo = profile_photos.photos[0][-1]
                target_profile_photo = photo.file_id
        except Exception as photo_error:
            logger.error(f"Ошибка при получении фото пользователя {user.id}: {photo_error}")

        if target_profile_photo:
            await message.reply_photo(photo=target_profile_photo, caption=text)
        else:
            await message.reply(text)

    except Exception as e:
        await message.reply(MText.get("profile_error"))

@router.message(ProfileFilter())
async def _(message: Message, session: AsyncSession):
    db = DB(session)
    is_reply = message.reply_to_message
    match is_reply:
        case None:
            user = await db.get_user(message.from_user.id)
            if user:
                place_on_top = await db.get_user_place_on_top(user)
                text = MText.get("profile").format(
                    tag = "" if not user.clan_member else f"[{escape(user.clan_member.clan.tag)}]",
                    name =  escape(user.name) + " 👑" if user.vip else escape(user.name),
                    balance = user.balance,
                    place = place_on_top,
                    cards = len(user.inventory),
                    date = user.profile.joined.astimezone(MSK_TIMEZONE).strftime("%d.%m.%Y")
        ) + (f"\n\n<i>«{user.profile.describe}»</i>" if user.profile.describe else "")
                profile_photo = await user_photo_link(message)
                keyboard = await profile_keyboard(user.profile.describe != "")
                if profile_photo:
                    await message.reply_photo(photo=profile_photo,caption=text,reply_markup= (keyboard if message.chat.type == "private" else None))
                else:
                    await message.reply(text,reply_markup=(keyboard if message.chat.type == "private" else None))
            else:
                text = MText.get("not_user").format(name=escape(message.from_user.full_name))
                await message.reply(text)
        case _:
            user = await db.get_user(message.reply_to_message.from_user.id)
            if user:
                place_on_top = await db.get_user_place_on_top(user)
                text = MText.get("profile").format(
                    tag = "" if not user.clan_member else f"[{escape(user.clan_member.clan.tag)}]",
                    name =  escape(user.name) + " 👑" if user.vip else escape(user.name),
                    balance = user.balance,
                    place = place_on_top,
                    cards = len(user.inventory),
                    date = user.profile.joined.astimezone(MSK_TIMEZONE).strftime("%d.%m.%Y")
        ) + (f"\n\n<i>«{user.profile.describe}»</i>" if user.profile.describe else "")
                profile_photo = await user_photo_link(message)
                if profile_photo:
                    await message.reply_photo(photo=profile_photo,caption=text)
                else:
                    await message.reply(text)
            else:
                text = MText.get("not_user").format(name=
                                message.reply_to_message.from_user.full_name)
                await message.reply(text)
