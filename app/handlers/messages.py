from datetime import datetime, timedelta, timezone
from aiogram import Router,F
from aiogram.types import Message,FSInputFile

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.filters import ProfileFilter, Private
from app.func import (card_formatter, not_user, nottime, profile_creator,
                    profile_step2_tutorial, profile_tutorial, random_card, user_photo_link)
from db.models import User
from db.requests import get_user_place_on_top

router = Router()

@router.message(F.text == "🌐 Открыть карту", Private())
async def _(message: Message, session: AsyncSession):
    user = await session.scalar(
        select(User)
        .filter_by(id=message.from_user.id)
        .with_for_update()
    )

    # Нормализуем `last_open` на случай, если в БД хранится naive datetime
    last_open = user.last_open
    if last_open.tzinfo is None:
        # Предполагаем UTC для записей без timezone
        last_open = last_open.replace(tzinfo=timezone.utc)

    if last_open + timedelta(hours=3) <= datetime.now(timezone.utc):
        card = await random_card(session, user.pity)
        text = await card_formatter(card)
        await message.answer_photo(FSInputFile(path=f"app/{card.icon}"), caption=text)
        if card not in user.inventory:
            user.inventory.append(card)
        match user.pity:
            case _ if user.pity <= 0:
                user.pity = 100
            case _:
                user.pity -= 1
        user.last_open = datetime.now(timezone.utc)
        user.yens += card.value
        await session.commit()
        if user.start:
            tutorial = await profile_tutorial()
            await message.answer(tutorial)
    else:
        text = await nottime(user.last_open)
        if text is None:
            text = "<i>⏳ До следующего открытия осталось немного времени</i>"
        await message.reply(text)
    
@router.message(ProfileFilter())
async def _(message: Message, session: AsyncSession):
    
    is_reply = message.reply_to_message
    match is_reply:
        case None:
            user = await session.scalar(select(User).filter_by(
                                                    id=message.from_user.id))
            if user:
                place_on_top = await get_user_place_on_top(session,user)
                text = await profile_creator(user.profile,place_on_top)
                profile_photo = await user_photo_link(message)
                if profile_photo:
                    await message.reply_photo(photo=profile_photo,caption=text)
                else:
                    await message.reply(text)
                if user.start and message.text == "👤 Профиль":
                    tutorial = await profile_step2_tutorial()
                    await message.answer(tutorial)
                    user.start = False
                    await session.commit()
            else:
                text = await not_user(message.from_user.full_name)
                await message.reply(text)
        case _:
            user = await session.scalar(select(User).filter_by(
                                    id=message.reply_to_message.from_user.id))
            if user:
                place_on_top = await get_user_place_on_top(session,user)
                text = await profile_creator(user.profile,place_on_top)
                profile_photo = await user_photo_link(message)
                if profile_photo:
                    await message.reply_photo(photo=profile_photo,caption=text)
                else:
                    await message.reply(text)
            else:
                text = await not_user(
                    message.reply_to_message.from_user.full_name)
                await message.reply(text)
