from datetime import datetime, timedelta, timezone
from aiogram import Router,F
from aiogram.types import Message,FSInputFile

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.filters.ProfileFilter import ProfileFilter
from app.filters.Private import Private
from app.func.messageformater import (card_formatter, not_user,
                                    nottime,profile_creator, profile_step2_tutorial, profile_tutorial)
from app.func.random_card import random_card
from app.func.userphoto import user_photo_link
from db.models import User
from db.requests import get_user_place_on_top

router = Router()

@router.message(F.text == "🌐 Открыть карту", Private())
async def _(message: Message, session: AsyncSession):
    logger.info(f"Обработка запроса открытия карты от user_id={message.from_user.id}")
    user = await session.scalar(
            select(User)
            .filter_by(id=message.from_user.id)
            .with_for_update())
    if user.last_open + timedelta(hours=3) <= datetime.now(timezone.utc):
        card = await random_card(session,user.guarant)
        if card is None:
            logger.error(f"Не удалось выбрать карту для user_id={message.from_user.id}")
            await message.reply("Произошла ошибка при выборе карты. Попробуйте позже.")
            return
        text = await card_formatter(card)
        # Если иконки нет или файл не найден, отправляем только подпись
        if not card.icon:
            logger.warning(f"У карты id={getattr(card,'id',None)} нет иконки, отправляю только текст")
            await message.answer(text)
        else:
            await message.answer_photo(FSInputFile(path=f"app/icons/{card.icon}"), caption=text)
        if card not in user.inventory: user.inventory.append(card)
        match user.guarant:
            case _ if user.guarant <= 0: user.guarant = 100
            case _: user.guarant -= 1
        user.last_open = datetime.now(timezone.utc)
        user.yens += card.value
        await session.commit()
        logger.info(f"Пользователь id={user.id} получил карту id={getattr(card,'id',None)}; yens={user.yens} guarant={user.guarant}")
        if user.start:
            tutorial = await profile_tutorial()
            await message.answer(tutorial)
    else:
        text = await nottime(user.last_open)
        await message.reply(text)
    
@router.message(ProfileFilter())
async def _(message: Message, session: AsyncSession):
    logger.info(f"Обработка профиля (ProfileFilter) от user_id={message.from_user.id})")
    is_reply = message.reply_to_message
    match is_reply:
        case None:
            user = await session.scalar(select(User).filter_by(
                                                    id=message.from_user.id))
            if user:
                if not user.profile:
                    logger.warning(f"У пользователя id={user.id} отсутствует профиль")
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
                if not user.profile:
                    logger.warning(f"У пользователя id={user.id} отсутствует профиль (reply target)")
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