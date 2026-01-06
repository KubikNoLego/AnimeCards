from datetime import datetime, timedelta, timezone
from html import escape
from aiogram import Router,F
from aiogram.types import Message,FSInputFile
from aiogram.fsm.context import FSMContext
import re


from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.StateGroups import ChangeDescribe
from app.filters import ProfileFilter, Private
from app.func import (card_formatter, not_user, nottime, profile_creator,
                    profile_step2_tutorial, profile_tutorial, random_card, user_photo_link, _load_messages)
from app.keyboards.utils import profile_keyboard, verse_filter_pagination_keyboard
from db.models import User, Verse
from db.requests import get_user_place_on_top, get_top_players_by_balance
from sqlalchemy import select

router = Router()


@router.message(ChangeDescribe.text)
async def _(message:Message, session: AsyncSession, state: FSMContext):
    messages = _load_messages()
    if len(message.text) > 70:
        await message.answer(messages["describe_too_long"] % len(message.text))
    else:
        user = await session.scalar(select(User).filter_by(id=message.from_user.id))
        user.profile.describe = escape(message.text)
        await session.commit()
        await message.answer(messages["describe_updated_success"] % escape(message.text))
        await state.set_state(None)

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

    hour = 2 if datetime.now(timezone.utc).weekday() >= 5 else 3

    if last_open + timedelta(hours=hour) <= datetime.now(timezone.utc):
        card = await random_card(session, user.pity)
        text = await card_formatter(card)
        await message.answer_photo(FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}"), caption=text)
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
    
@router.message(F.text == "🏆 Топ игроков", Private())
async def _(message: Message, session: AsyncSession):
    from app.func.utils import top_players_formatter

    user = await session.scalar(select(User).filter_by(id=message.from_user.id))
    if user:
        top_players = await get_top_players_by_balance(session)
        text = await top_players_formatter(top_players, user.id)
        await message.answer(text)
    else:
        text = await not_user(message.from_user.full_name)
        await message.reply(text)

@router.message(F.text.startswith(".профиль @"))
async def _(message: Message, session: AsyncSession):
    """Обработчик команды .профиль @username - показывает профиль пользователя по username"""
    try:
        # Извлекаем username из команды
        pattern = r'\.профиль @([a-zA-Z0-9_]+)'
        match = re.search(pattern, message.text)

        if not match:
            await message.reply("❌ Неправильный формат команды. Используйте: .профиль @username")
            return

        target_username = match.group(1)

        # Ищем пользователя по username
        user = await session.scalar(
            select(User)
            .filter_by(username=target_username)
        )

        if not user:
            await message.reply(f"❌ Пользователь с username @{target_username} не найден")
            return

        # Получаем информацию о профиле
        place_on_top = await get_user_place_on_top(session, user)
        text = await profile_creator(user.profile, place_on_top, session)

        # Получаем фото профиля целевого пользователя (не отправителя команды)
        target_profile_photo = None
        try:
            profile_photos = await message.bot.get_user_profile_photos(user.id, limit=1)
            if profile_photos and len(profile_photos.photos) > 0:
                photo = profile_photos.photos[0][-1]
                target_profile_photo = photo.file_id
        except Exception as photo_error:
            logger.error(f"Ошибка при получении фото пользователя {user.id}: {photo_error}")

        # Отправляем профиль
        if target_profile_photo:
            await message.reply_photo(photo=target_profile_photo, caption=text)
        else:
            await message.reply(text)

    except Exception as e:
        logger.error(f"Ошибка при обработке команды .профиль @username: {e}")
        await message.reply("❌ Произошла ошибка при получении профиля")

@router.message(ProfileFilter())
async def _(message: Message, session: AsyncSession):

    is_reply = message.reply_to_message
    match is_reply:
        case None:
            user = await session.scalar(select(User).filter_by(
                                                    id=message.from_user.id))
            if user:
                place_on_top = await get_user_place_on_top(session,user)
                text = await profile_creator(user.profile,place_on_top, session)
                profile_photo = await user_photo_link(message)
                keyboard = await profile_keyboard(user.profile.describe != "")
                if profile_photo:
                    await message.reply_photo(photo=profile_photo,caption=text,reply_markup=keyboard)
                else:
                    await message.reply(text,reply_markup=keyboard)
                if user.start:
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
                text = await profile_creator(user.profile,place_on_top, session)
                profile_photo = await user_photo_link(message)
                if profile_photo:
                    await message.reply_photo(photo=profile_photo,caption=text)
                else:
                    await message.reply(text)
            else:
                text = await not_user(
                    message.reply_to_message.from_user.full_name)
                await message.reply(text)
