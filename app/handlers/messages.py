# Стандартные библиотеки
from datetime import datetime, timedelta, timezone, timedelta
import math
from html import escape
import re
import os

# Создаем таймзону для Москвы (UTC+3)
MSK_TIMEZONE = timezone(timedelta(hours=3))

# Сторонние библиотеки
from aiogram import Router,F
from aiogram.types import Message,FSInputFile
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

# Локальные импорты
from app.StateGroups import ChangeDescribe,CreateClan
from app.filters import ProfileFilter, Private
from app.func import random_card, user_photo_link, Text, create_qr
from app.keyboards import profile_keyboard, shop_keyboard,create_clan,clan_invite_kb,clan_create
from db import Card, Clan, ClanMember, User,RedisRequests,DB

router = Router()


user_card_opens = []


@router.message(F.text == ".пригласить")
async def _(message: Message, session:AsyncSession,state:FSMContext):
    messages = Text()._load_messages()
    db = DB(session)
    sender = await db.get_user(message.from_user.id)

    # Проверка, является ли пользователь лидером клана
    if not sender.clan_member or sender.clan_member.clan.leader_id != sender.id:
        await message.reply(messages["not_clan_leader"])
        return

    # Проверка, что команда используется в групповом чате и как ответ на сообщение
    if message.chat.type == "private":
        await message.reply(messages["not_in_private_chat"])
        return

    if not message.reply_to_message:
        await message.reply(messages["not_in_private_chat"])
        return

    # Получаем пользователя, которого приглашаем
    user = await db.get_user(message.reply_to_message.from_user.id)
    if not user:
        await message.reply(messages["not_user"])
        return

    # Проверка, что пользователь не состоит в клане
    if user.clan_member:
        await message.reply(messages["user_already_in_clan"])
        return

    # Проверяем, не отправляли ли мы уже приглашение этому пользователю
    existing_invitation = await db.get_clan_invitation(sender.clan_member.clan.id, user.id)
    if existing_invitation:
        await message.reply(messages["clan_invite_already_sent"])
        return

    # Создаем приглашение в базе данных
    invitation = await db.create_clan_invitation(sender.clan_member.clan.id, sender.id, user.id)
    if not invitation:
        await message.reply(messages["clan_invite_already_sent"])
        return

    # Отправляем приглашение
    try:
        await message.reply(messages["clan_invite_success"])
        await message.bot.send_message(user.id,text=messages["clan_invite_prompt"] % sender.clan_member.clan.name,reply_markup= await clan_invite_kb(sender.clan_member.clan_id))
    except Exception as e:
        logger.error(f"Ошибка при отправке приглашения: {str(e)}", exc_info=True)
        await message.answer(messages["invite_send_error"])

@router.message(CreateClan.name)
async def _(message: Message, session:AsyncSession,state:FSMContext):
    messages = Text()._load_messages()
    clan = await session.scalar(select(Clan).filter_by(name = escape(message.text)))
    if len(message.text) <= 50 and not clan:
        await state.update_data(name=escape(message.text))
        await state.set_state(CreateClan.tag)
        await message.answer(messages["clan_tag_prompt"])
    else:
        await message.answer(messages["clan_name_too_long"] % len(message.text))

@router.message(CreateClan.tag)
async def _(message: Message, session:AsyncSession,state:FSMContext):
    messages = Text()._load_messages()
    clan = await session.scalar(select(Clan).filter_by(tag = escape(message.text)))
    if len(message.text) <= 5 and not clan:
        await state.update_data(tag=escape(message.text))
        await state.set_state(CreateClan.description)
        await message.answer(messages["clan_description_prompt"])
    else:
        await message.answer(messages["clan_tag_too_long"] % len(message.text))

@router.message(CreateClan.description)
async def _(message: Message, session:AsyncSession,state:FSMContext):
    messages = Text()._load_messages()
    if len(message.text) <= 255:
        await state.update_data(description = escape(message.text))
        data = await state.get_data()
        await state.set_state(CreateClan.accept)
        await message.answer(messages["clan_creation_confirmation"] % (data['name'], data['tag'], data['description']), reply_markup= await clan_create())
    else:
        await message.answer(messages["clan_description_too_long"] % len(message.text))

@router.message(F.text == "🛡️ Клан",Private())
async def _(message:Message, session:AsyncSession, state:FSMContext):
    db = DB(session)

    user = await db.get_user(message.from_user.id)
    
    messages = Text()._load_messages()
    if user and user.clan_member:
        clan = await db.get_clan(user.clan_member.clan_id)
        member = user.clan_member

        # Собираем информацию о клане
        clan_info = f"""🏰 <b>{clan.name}</b> [{clan.tag}]
👥 Участников: {len(clan.members)}
💰 Баланс клана: {clan.balance} ¥
📅 Создан: {clan.created_at.strftime('%d.%m.%Y %H:%M')}
👑 Лидер: {clan.leader.name if clan.leader else 'Неизвестно'}

📝 <b>Ваш статус:</b>
👤 Роль: {'👑 Лидер' if member.is_leader else '👥 Участник'}
💎 Вклад: {member.contribution} ¥
📅 Присоединился: {member.joined_at.strftime('%d.%m.%Y %H:%M')}

📋 <b>Описание клана:</b>
{clan.description if clan.description else 'Нет описания'}
"""
        
        await message.reply(clan_info)
    else:
        await message.reply(messages["not_in_clan"], reply_markup= None if not user.vip else await create_clan())

@router.message(F.text == "🛒 Магазин",Private())
async def _(message:Message,session:AsyncSession):
    items = await RedisRequests.daily_items()
    messages = Text()._load_messages()
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if items:
        try:
            items = items.decode("utf-8").split(",")
            cards = []

            for item_id in items:
                if item_id.strip():  # Проверяем, что ID не пустой
                    card = await session.scalar(select(Card).filter_by(id=int(item_id.strip())))
                    if card:
                        # Применяем 70% надбавку к цене карточки
                        card.value = int(card.value * 1.7)
                        cards.append(card)

            if cards:
                # Создаем клавиатуру с товарами
                keyboard = await shop_keyboard(cards if user.vip else cards[0:3])
                await message.answer(messages["daily_shop"], reply_markup=keyboard)
            else:
                await message.answer(messages['shop_empty'])
        except Exception as e:
            logger.error(f"Ошибка при обработке магазина: {str(e)}", exc_info=True)
            await message.answer(messages['shop_empty'])
    else:
        await message.answer(messages['shop_empty'])
        

@router.message(F.text == "🔗 Реферальная ссылка")
async def _(message: Message, session: AsyncSession):
    """Обработчик кнопки реферальной ссылки."""
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if user:
        total_reward = 0
        for i in user.referrals:
            total_reward += i.referrer_reward
        # Создаем реферальную ссылку
        bot_info = await message.bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start=r_{user.id}"

        stats_message = f"""
🔗 <b>Ваша реферальная ссылка:</b>
<code>{referral_link}</code>

📊 <b>Статистика рефералов:</b>
👥 Приглашено друзей: {len(user.referrals)}
💰 Получено йен: {total_reward}

💡 <i>Приглашайте друзей и получайте бонусы от {"50 до 300" if not user.vip else "150 до 700"} йен за каждого!</i>
"""
        try:
            qr_file = await create_qr(referral_link)
            try:
                await message.reply_photo(qr_file, caption=stats_message, parse_mode="HTML")
            finally:
                # Удаляем временный файл в любом случае
                if hasattr(qr_file, 'path') and os.path.exists(qr_file.path):
                    os.unlink(qr_file.path)
        except Exception as e:
            # logger.error(f"Ошибка при генерации QR-кода: {e}")
            messages = Text()._load_messages()
            await message.reply(messages["qr_error"])
    else:
        messages = Text()._load_messages()
        await message.reply(messages["not_registered"])


@router.message(ChangeDescribe.text)
async def _(message:Message, session: AsyncSession, state: FSMContext):
    messages = Text()._load_messages()
    if len(message.text) > 70:
        await message.answer(messages["describe_too_long"] % len(message.text))
    else:
        db = DB(session)
        user = await db.get_user(message.from_user.id)
        user.profile.describe = escape(message.text)
        await session.commit()
        await message.answer(messages["describe_updated_success"] % escape(message.text))
        await state.set_state(None)

@router.message(F.text == "🌐 Открыть карту", Private())
async def _(message: Message, session: AsyncSession):

    if message.from_user.id in user_card_opens:
        await message.reply("⏳ Подождите, карта уже открывается!")
        return
    try:
        user_card_opens.append(message.from_user.id)
        db = DB(session)
        user = await db.get_user(message.from_user.id)

        # Нормализуем `last_open` на случай, если в БД хранится naive datetime
        last_open = user.last_open
        free_open = user.free_open > 0
        if last_open.tzinfo is None:
            # Предполагаем MSK для записей без timezone
            last_open = last_open.replace(tzinfo=MSK_TIMEZONE)

        hour = 2 if datetime.now(MSK_TIMEZONE).weekday() >= 5 else 3

        if (last_open + timedelta(hours=hour) <= datetime.now(MSK_TIMEZONE)) or free_open:
            card = await random_card(session, user.pity)
            text = await Text().card_formatter(card, user)
            await message.answer_photo(FSInputFile(path=f"app/icons/{card.verse.name}/{card.icon}"), caption=text)
            if card not in user.inventory:
                user.inventory.append(card)
            match user.pity:
                case _ if user.pity <= 0:
                    user.pity = 100
                case _:
                    user.pity -= 1
            if free_open: 
                user.free_open -= 1
            else: 
                user.last_open = datetime.now(MSK_TIMEZONE)
            added_sum = int(card.value + (math.ceil(card.value * 0.1) if user.vip else 0))
            user.yens += added_sum
            user.clan_member.contribution += int(added_sum*0.3)
            user.clan_member.clan.balance += int(added_sum*0.3)
            await session.commit()
            if user.start:
                tutorial = await Text().profile_tutorial()
                await message.answer(tutorial)
        else:
            text = await Text().nottime(user.last_open)
            if text is None:
                text = "<i>⏳ До следующего открытия осталось немного времени</i>"
            await message.reply(text)
    finally:
        user_card_opens.remove(message.from_user.id)
    
@router.message(F.text == "🏆 Топ игроков", Private())
async def _(message: Message, session: AsyncSession):
    db = DB(session)
    user = await db.get_user(message.from_user.id)
    if user:
        # Получаем топ игроков по балансу (10 человек)
        top_players_balance = await db.get_top_players_by_balance()
        text_balance = await Text().top_players_formatter(top_players_balance, user.id)

        # Отправляем только топ по балансу
        await message.answer(text_balance)
    else:
        text = await Text().not_user(message.from_user.full_name)
        await message.reply(text)


@router.message(F.text.startswith(".профиль @"))
async def _(message: Message, session: AsyncSession):
    """Обработчик команды .профиль @username - показывает профиль пользователя по username"""
    try:
        # Извлекаем username из команды
        pattern = r'\.профиль @([a-zA-Z0-9_]+)'
        match = re.search(pattern, message.text)

        if not match:
            messages = Text()._load_messages()
            await message.reply(messages["invalid_profile_command"])
            return

        target_username = match.group(1)

        # Ищем пользователя по username
        user = await session.scalar(
            select(User)
            .filter_by(username=target_username)
        )

        if not user:
            messages = Text()._load_messages()
            await message.reply(messages["user_not_found"].format(target_username=target_username))
            return

        db = DB(session)
        # Получаем информацию о профиле
        place_on_top = await db.get_user_place_on_top(user)
        text = await Text.profile_creator(user.clan_member.clan if user.clan_member else None,user.clan_member.clan,user.profile, place_on_top, session)

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
        messages = Text()._load_messages()
        await message.reply(messages["profile_error"])

@router.message(ProfileFilter())
async def _(message: Message, session: AsyncSession):
    db = DB(session)
    is_reply = message.reply_to_message
    match is_reply:
        case None:
            user = await db.get_user(message.from_user.id)
            if user:
                place_on_top = await db.get_user_place_on_top(user)
                text = await Text().profile_creator(user.clan_member.clan if user.clan_member else None,user.profile,place_on_top, session)
                profile_photo = await user_photo_link(message)
                keyboard = await profile_keyboard(user.profile.describe != "")
                if profile_photo:
                    await message.reply_photo(photo=profile_photo,caption=text,reply_markup=keyboard)
                else:
                    await message.reply(text,reply_markup=keyboard)
                if user.start:
                    tutorial = await Text().profile_step2_tutorial()
                    await message.answer(tutorial)
                    user.start = False
                    await session.commit()
            else:
                text = await Text().not_user(message.from_user.full_name)
                await message.reply(text)
        case _:
            user = await db.get_user(message.reply_to_message.from_user.id)
            if user:
                place_on_top = await db.get_user_place_on_top(user)
                text = await Text().profile_creator(user.clan_member.clan if user.clan_member else None,user.profile,place_on_top, session)
                profile_photo = await user_photo_link(message)
                if profile_photo:
                    await message.reply_photo(photo=profile_photo,caption=text)
                else:
                    await message.reply(text)
            else:
                text = await Text().not_user(
                    message.reply_to_message.from_user.full_name)
                await message.reply(text)
